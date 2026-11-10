"""Non-invasive host/container telemetry for GB10 benchmark runs."""
import json
from pathlib import Path
import subprocess
import threading
from datetime import datetime, timezone
import time

GIB = 1024 ** 3

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def run_text(args, timeout=2):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def host_memory():
    rows = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            rows[key] = int(value.split()[0]) * 1024
    psi = {}
    for line in Path('/proc/pressure/memory').read_text().splitlines():
        fields = line.split()
        psi[fields[0]] = float(next(x.split('=')[1] for x in fields[1:] if x.startswith('avg10=')))
    return {'mem_available_gib': round(rows['MemAvailable'] / GIB, 3),
            'swap_used_gib': round((rows['SwapTotal'] - rows['SwapFree']) / GIB, 3),
            'psi_some_avg10': psi['some'], 'psi_full_avg10': psi['full']}

def protection_reason(sample, initial=False):
    if sample['mem_available_gib'] < (12 if initial else 8):
        return f"MemAvailable {sample['mem_available_gib']} GiB below {'12' if initial else '8'} GiB"
    if sample['psi_some_avg10'] >= 5:
        return f"memory PSI some avg10 {sample['psi_some_avg10']}% >= 5%"
    if sample['psi_full_avg10'] >= 1:
        return f"memory PSI full avg10 {sample['psi_full_avg10']}% >= 1%"
    return None

def container_metrics(name='paddleocr-gb10'):
    raw = run_text(['docker', 'inspect', '--format', '{{json .State}}', name])
    state = None
    if raw:
        try:
            data = json.loads(raw)
            state = f"{data.get('Status', 'unknown')}/{(data.get('Health') or {}).get('Status', 'none')}"
        except ValueError:
            pass
    stats = run_text(['docker', 'stats', '--no-stream', '--format', '{{json .}}', name], timeout=3)
    memory = None
    if stats:
        try:
            memory = json.loads(stats).get('MemUsage')
        except ValueError:
            pass
    process_rss_mib = None
    top = run_text(['docker', 'top', name, '-eo', 'pid,ppid,rss,comm'])
    if top:
        values = []
        for line in top.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[-1] in ('paddlex', 'python', 'python3'):
                try:
                    values.append(int(fields[2]) / 1024)
                except ValueError:
                    pass
        if values:
            process_rss_mib = round(max(values), 2)
    return state, memory, process_rss_mib

def gpu_metrics():
    raw = run_text(['nvidia-smi', '--query-gpu=utilization.gpu,power.draw,temperature.gpu,memory.used',
                    '--format=csv,noheader,nounits'], timeout=3)
    if not raw:
        return {'gpu_util_pct': None, 'gpu_power_w': None, 'gpu_temp_c': None, 'nvidia_gpu_memory_mib': None}
    parts = [x.strip() for x in raw.splitlines()[0].split(',')]
    values = []
    for x in parts[:4]:
        try:
            values.append(float(x))
        except ValueError:
            values.append(None)
    values.extend([None] * (4 - len(values)))
    return dict(zip(('gpu_util_pct', 'gpu_power_w', 'gpu_temp_c', 'nvidia_gpu_memory_mib'), values))

def host_sample():
    point = {'timestamp_utc': utc_now(), 'monotonic_s': time.monotonic(), **host_memory()}
    point['process_rss_mib'] = None
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                point['process_rss_mib'] = round(int(line.split()[1]) / 1024, 2)
                break
    except OSError:
        pass
    return point

def external_sample():
    point = gpu_snapshot()
    point.update(container_snapshot())
    return point

def gpu_snapshot():
    point = gpu_metrics()
    point['gpu_sampled_at_utc'] = utc_now()
    point['gpu_sampled_monotonic_s'] = time.monotonic()
    return point

def container_snapshot():
    state, memory, rss = container_metrics()
    point = {'container_state': state, 'container_memory_usage': memory,
             'paddleocr_process_rss_mib': rss}
    point['container_sampled_at_utc'] = utc_now()
    point['container_sampled_monotonic_s'] = time.monotonic()
    return point

def sample():
    return {**host_sample(), **external_sample()}

class Monitor:
    def __init__(self, interval=1.0, sampler=sample):
        if not 0.5 <= interval <= 1.0:
            raise ValueError('sample interval must be 0.5–1.0 seconds')
        self.interval, self.sampler = interval, sampler
        self.samples = []
        self.stop = threading.Event()
        self.protection = threading.Event()
        self.reason = None
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.gpu_thread = threading.Thread(target=self._gpu_loop, daemon=True)
        self.container_thread = threading.Thread(target=self._container_loop, daemon=True)
        self.gpu = {}
        self.container = {}

    def _gpu_loop(self):
        while not self.stop.is_set():
            self.gpu = gpu_snapshot()
            self.stop.wait(self.interval)

    def _container_loop(self):
        while not self.stop.is_set():
            self.container = container_snapshot()
            self.stop.wait(self.interval)

    def _take(self):
        try:
            point = {**host_sample(), **self.gpu, **self.container} if self.sampler is sample else self.sampler()
            self.samples.append(point)
            reason = protection_reason(point)
            if reason and not self.reason:
                self.reason = reason
                self.protection.set()
        except Exception as exc:
            if not self.reason:
                self.reason = f'telemetry unavailable: {exc}'
                self.protection.set()

    def _loop(self):
        while not self.stop.wait(self.interval):
            self._take()

    def __enter__(self):
        if self.sampler is sample:
            self.gpu_thread.start()
            self.container_thread.start()
        self._take()
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self._take()
        self.thread.join(timeout=5)
        if self.sampler is sample:
            self.gpu_thread.join(timeout=5)
            self.container_thread.join(timeout=5)
