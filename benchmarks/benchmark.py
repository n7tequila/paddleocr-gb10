#!/usr/bin/env python3
"""Reproducible client-side HTTP benchmark for official PaddleX Serving."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import statistics
import struct
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from api import probe
sys.path.insert(0, str(Path(__file__).resolve().parent))
import monitor

DATASET = Path(__file__).resolve().parent / 'datasets'
REPORTS = Path(__file__).resolve().parent / 'reports'
REQUEST_FIELDS = ('index', 'phase', 'sample_id', 'category', 'started_at_utc', 'started_monotonic_s',
                  'ended_at_utc', 'duration_s', 'http_status', 'error_code', 'markdown_chars',
                  'pages', 'request_bytes', 'response_bytes', 'timed_out', 'status', 'error')
RESOURCE_FIELDS = ('timestamp_utc', 'monotonic_s', 'mem_available_gib', 'swap_used_gib',
                   'psi_some_avg10', 'psi_full_avg10', 'gpu_util_pct', 'gpu_power_w', 'gpu_temp_c',
                   'nvidia_gpu_memory_mib', 'gpu_sampled_at_utc', 'gpu_sampled_monotonic_s',
                   'container_state', 'container_memory_usage', 'container_sampled_at_utc',
                   'container_sampled_monotonic_s',
                   'paddleocr_process_rss_mib', 'process_rss_mib')

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api-url', default=os.environ.get('PADDLEOCR_API_URL', 'http://127.0.0.1:8080'))
    p.add_argument('--images', type=Path, help='PNG/JPEG/PDF file or directory; private data stays local')
    p.add_argument('--requests', type=int, default=5)
    p.add_argument('--warmup', type=int, default=1)
    p.add_argument('--concurrency', type=int, default=1)
    p.add_argument('--allow-concurrency', action='store_true', help='explicitly authorize concurrency above 1')
    p.add_argument('--timeout', type=float, default=300)
    p.add_argument('--output-dir', type=Path, default=REPORTS)
    p.add_argument('--scenario', default='basic', help='scenario name or JSON path')
    p.add_argument('--sample-id', action='append', help='select one or more public manifest IDs from the scenario')
    p.add_argument('--require-ocr-only', action='store_true', help='abort before inference unless all observed GPU compute processes belong to PaddleOCR')
    p.add_argument('--sample-interval', type=float, default=0.5)
    args = p.parse_args(argv)
    if args.requests < 1 or args.warmup < 0 or args.timeout <= 0 or args.concurrency < 1:
        p.error('requests/concurrency/timeout must be positive and warmup nonnegative')
    if args.concurrency > 1 and not args.allow_concurrency:
        p.error('concurrency > 1 requires --allow-concurrency')
    if not 0.5 <= args.sample_interval <= 1.0:
        p.error('sample interval must be 0.5–1.0 seconds')
    args.api_url = probe.base_url(args.api_url)
    return args

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dimensions(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == '.png':
        data = path.read_bytes()[:24]
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'bad PNG: {path}')
        return (*struct.unpack('>II', data[16:24]), 1)
    if suffix in ('.jpg', '.jpeg'):
        try:
            from PIL import Image
            with Image.open(path) as im:
                return (*im.size, 1)
        except ImportError as exc:
            raise ValueError('JPEG metadata needs Pillow') from exc
    if suffix == '.pdf':
        data = path.read_bytes()
        if not data.startswith(b'%PDF-'):
            raise ValueError(f'bad PDF: {path}')
        pages = len(re.findall(rb'/Type\s*/Page\b', data))
        if pages < 1:
            raise ValueError(f'PDF page count unavailable: {path}')
        return (None, None, pages)
    raise ValueError(f'unsupported file: {path}')

def validate_manifest(path=DATASET / 'manifest.json'):
    manifest = json.loads(Path(path).read_text())
    assert manifest['schema_version'] == 1
    seen = set()
    for item in manifest['samples']:
        assert item['id'] not in seen
        seen.add(item['id'])
        for key in ('id', 'path', 'file_type', 'file_type_code', 'width', 'height', 'bytes',
                    'pages', 'category', 'sha256', 'source', 'license'):
            assert key in item, (item.get('id'), key)
        file = Path(path).parent / item['path']
        assert file.is_file() and file.stat().st_size == item['bytes'], file
        assert sha(file) == item['sha256'], file
        width, height, pages = dimensions(file)
        assert pages == item['pages']
        if width is not None:
            assert (width, height) == (item['width'], item['height'])
        assert item['file_type_code'] == (0 if file.suffix.lower() == '.pdf' else 1)
    return manifest

def scenario_data(name):
    path = Path(name)
    if not path.is_file():
        path = Path(__file__).resolve().parent / 'scenarios' / f'{name}.json'
    return json.loads(path.read_text())

def select_samples(args, manifest):
    scenario = scenario_data(args.scenario)
    known = {s['id']: s for s in manifest['samples']}
    if args.images:
        image_path = args.images.expanduser().resolve()
        files = sorted(p for p in image_path.iterdir() if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.pdf')) if image_path.is_dir() else [image_path]
        samples = []
        for path in files:
            if not path.is_file():
                raise ValueError(f'image missing: {path}')
            width, height, pages = dimensions(path)
            samples.append({'id': path.stem, 'path': str(path), 'file_type': path.suffix.lower().lstrip('.'),
                            'file_type_code': 0 if path.suffix.lower() == '.pdf' else 1,
                            'width': width, 'height': height, 'pages': pages, 'bytes': path.stat().st_size,
                            'category': 'private_' + path.suffix.lower().lstrip('.'), 'sha256': sha(path),
                            'source': 'user supplied; local only', 'license': 'user supplied; do not publish'})
    else:
        selected_ids = args.sample_id or scenario['sample_ids']
        if any(sid not in scenario['sample_ids'] for sid in selected_ids):
            raise ValueError('--sample-id must belong to the selected scenario')
        samples = [dict(known[sid]) for sid in selected_ids]
        for s in samples:
            s['path'] = str(DATASET / s['path'])
    if not samples:
        raise ValueError('no supported images found')
    return scenario, samples

def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)

def stats(rows, wall_seconds=None):
    done = [r for r in rows if r['phase'] == 'measure']
    ok = [r for r in done if r['status'] == 'success']
    values = [r['duration_s'] for r in ok]
    return {'attempted': len(done), 'success': len(ok), 'failed': sum(r['status'] == 'failed' for r in done),
            'timeout': sum(r['status'] == 'timeout' for r in done),
            'success_rate': len(ok) / len(done) if done else None,
            'mean_s': statistics.mean(values) if values else None,
            'median_p50_s': statistics.median(values) if values else None,
            'p90_s': percentile(values, .90), 'p95_s': percentile(values, .95),
            'min_s': min(values) if values else None, 'max_s': max(values) if values else None,
            'stddev_s': statistics.pstdev(values) if values else None,
            'pages': sum(r['pages'] or 0 for r in ok),
            'pages_per_s': sum(r['pages'] or 0 for r in ok) / wall_seconds if wall_seconds and wall_seconds > 0 else None,
            'p95_descriptive_only': len(values) < 100}

def one_request(index, phase, sample, api_url, timeout):
    # Prepare the payload before the HTTP timer; this cost is not transport latency.
    raw_file = Path(sample['path']).read_bytes()
    payload = {'file': base64.b64encode(raw_file).decode('ascii'),
               'fileType': sample['file_type_code'], 'visualize': False}
    data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    started = monitor.utc_now()
    start = time.monotonic()
    row = {'index': index, 'phase': phase, 'sample_id': sample['id'], 'category': sample['category'],
           'started_at_utc': started, 'started_monotonic_s': start, 'ended_at_utc': None,
           'duration_s': None, 'http_status': None, 'error_code': None, 'markdown_chars': None,
           'pages': None, 'request_bytes': len(data), 'response_bytes': None,
           'timed_out': False, 'status': 'failed', 'error': None}
    request = Request(api_url + '/layout-parsing', data=data, method='POST',
                      headers={'Content-Type': 'application/json'})
    try:
        try:
            response = probe.OPENER.open(request, timeout=timeout)
        except HTTPError as exc:
            response = exc
        with response:
            row['http_status'] = response.status
            raw = response.read()
        row['ended_at_utc'] = monitor.utc_now()
        row['duration_s'] = round(time.monotonic() - start, 6)
        row['response_bytes'] = len(raw)
        body = json.loads(raw)
        row['error_code'] = body.get('errorCode') if isinstance(body, dict) else None
        pages = body.get('result', {}).get('layoutParsingResults') if isinstance(body, dict) else None
        if row['http_status'] != 200 or row['error_code'] != 0:
            raise ValueError(f"HTTP {row['http_status']}, errorCode {row['error_code']}")
        if not isinstance(pages, list) or len(pages) != sample['pages']:
            raise ValueError(f"expected {sample['pages']} pages, got {len(pages) if isinstance(pages, list) else 'invalid'}")
        chars = 0
        for page in pages:
            markdown = page.get('markdown', {}).get('text') if isinstance(page, dict) else None
            if not isinstance(markdown, str) or not markdown.strip():
                raise ValueError('empty/missing Markdown')
            chars += len(markdown)
        row.update(status='success', pages=len(pages), markdown_chars=chars)
    except (TimeoutError, socket.timeout) as exc:
        row.update(status='timeout', timed_out=True, error=str(exc))
    except URLError as exc:
        reason = exc.reason
        timed_out = isinstance(reason, (TimeoutError, socket.timeout))
        row.update(status='timeout' if timed_out else 'failed', timed_out=timed_out, error=str(exc))
    except Exception as exc:
        row['error'] = f'{type(exc).__name__}: {exc}'[:500]
    finally:
        if row['duration_s'] is None:
            row['ended_at_utc'] = monitor.utc_now()
            row['duration_s'] = round(time.monotonic() - start, 6)
    return row

def invoke_request(request_fn, index, phase, sample, api_url, timeout):
    started = monitor.utc_now()
    start = time.monotonic()
    try:
        return request_fn(index, phase, sample, api_url, timeout)
    except Exception as exc:
        return {'index': index, 'phase': phase, 'sample_id': sample['id'],
                'category': sample['category'], 'started_at_utc': started,
                'started_monotonic_s': start, 'ended_at_utc': monitor.utc_now(),
                'duration_s': round(time.monotonic() - start, 6), 'http_status': None,
                'error_code': None, 'markdown_chars': None, 'pages': None,
                'request_bytes': None, 'response_bytes': None, 'timed_out': False,
                'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'[:500]}

def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def runtime_inventory():
    """Map active NVIDIA compute PIDs to container process lists; never infer from names alone."""
    container_raw = command(['docker', 'ps', '--format',
                             '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.State}}\t{{.Status}}'])
    containers = []
    pid_owners = {}
    if container_raw is not None:
        for line in container_raw.splitlines():
            fields = line.split('\t', 4)
            if len(fields) != 5:
                continue
            cid, name, image, state, status = fields
            containers.append({'id': cid, 'name': name, 'image': image,
                               'state': state, 'status': status})
            top = command(['docker', 'top', name, '-eo', 'pid,comm'])
            if top:
                for proc_line in top.splitlines()[1:]:
                    columns = proc_line.split(None, 1)
                    if len(columns) == 2 and columns[0].isdigit():
                        pid_owners[int(columns[0])] = {'container_id': cid,
                                                       'container_name': name,
                                                       'process': columns[1]}
    raw_gpu = command(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                       '--format=csv,noheader,nounits'])
    gpu_processes = []
    gpu_query_ok = raw_gpu is not None
    if raw_gpu:
        for line in raw_gpu.splitlines():
            columns = [part.strip() for part in line.split(',', 2)]
            if len(columns) != 3 or not columns[0].isdigit():
                gpu_query_ok = False
                continue
            pid = int(columns[0])
            owner = pid_owners.get(pid)
            gpu_processes.append({'pid': pid, 'process_name': columns[1],
                                  'gpu_memory_mib': columns[2],
                                  'owner': owner or {'type': 'unmapped_host_or_container_process'}})
    ocr_pids = {pid for pid, owner in pid_owners.items()
                if owner['container_name'] == 'paddleocr-gb10'}
    non_ocr = [proc for proc in gpu_processes if proc['pid'] not in ocr_pids]
    if not gpu_query_ok or container_raw is None:
        mode, reason = 'UNKNOWN_SHARED', 'Could not enumerate Docker containers or NVIDIA compute processes'
    elif not non_ocr:
        mode, reason = 'OCR_ONLY', 'All observed GPU compute processes belong to the PaddleOCR container, or no compute process was present'
    else:
        util_raw = command(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'])
        utils = []
        if util_raw:
            try:
                utils = [float(value.strip().split()[0]) for value in util_raw.splitlines()]
            except ValueError:
                utils = []
        if utils and all(value == 0 for value in utils):
            mode, reason = 'SHARED_IDLE', 'Non-OCR GPU compute processes exist; all GPUs reported zero utilization at the preflight snapshot'
        else:
            mode, reason = 'UNKNOWN_SHARED', 'Non-OCR GPU compute processes exist and were not verified idle'
    return {'run_mode': mode, 'run_mode_reason': reason,
            'docker_inventory_available': container_raw is not None,
            'gpu_process_query_available': gpu_query_ok,
            'containers': containers, 'gpu_compute_processes': gpu_processes,
            'unmapped_gpu_processes': non_ocr,
            'gpu_utilization_snapshot_pct': utils if non_ocr and 'utils' in locals() else None,
            'pid_mapping_method': 'nvidia-smi compute PIDs matched against docker top host PIDs'}

def environment(args, samples):
    ocr_state = command(['docker', 'inspect', '--format', '{{.State.Status}}', 'paddleocr-gb10'])
    ocr_health = command(['docker', 'inspect', '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}', 'paddleocr-gb10'])
    image = command(['docker', 'inspect', '--format', '{{.Image}}', 'paddleocr-gb10'])
    digests = command(['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', image]) if image else None
    packages = command(['docker', 'exec', 'paddleocr-gb10', 'python', '-c',
                        "import importlib.metadata as m,json; print(json.dumps({x:m.version(x) for x in ('paddlepaddle-gpu','paddleocr','paddlex')}))"])
    gpu = command(['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'])
    cuda = command(['nvidia-smi'])
    inventory = runtime_inventory()
    source_files = [Path(__file__), Path(monitor.__file__), DATASET / 'manifest.json']
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_files}
    git_dirty = command(['git', 'status', '--porcelain=v1', '-uall'])
    return {'timestamp_utc': monitor.utc_now(), 'cpu_architecture': platform.machine(),
            'gpu_name_driver': gpu, 'cuda_driver_report': cuda[:1000] if cuda else None,
            'packages': json.loads(packages) if packages else None,
            'docker_image_id': image, 'docker_repo_digests': json.loads(digests) if digests else None,
            'git_commit': command(['git', 'rev-parse', 'HEAD']), 'api_url': args.api_url,
            'git_worktree_dirty': bool(git_dirty), 'benchmark_source_sha256': source_hashes,
            **inventory,
            'paddleocr_container_state': ocr_state,
            'paddleocr_container_health': ocr_health,
            'coexistence_note': ('No non-OCR GPU compute PID was observed at preflight.'
                                 if inventory['run_mode'] == 'OCR_ONLY' else
                                 'GPU process ownership/activity is shared or unknown; do not describe this run as an OCR-only baseline.'),
            'parameters': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            'dataset_sha256': {s['id']: s['sha256'] for s in samples},
            'dataset_samples': [{key: s.get(key) for key in ('id', 'file_type', 'width', 'height',
                                                            'bytes', 'pages', 'category', 'sha256')}
                                for s in samples],
            'memory_note': 'GB10 unified memory: MemAvailable, Docker memory, process RSS, and NVIDIA memory can overlap; never add them.'}

def write_csv(path, fields, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

def write_reports(out, args, samples, rows, samples_resource, status, reason, elapsed, env):
    measured = [r for r in rows if r['phase'] == 'measure']
    categories = sorted({s['category'] for s in samples})
    measurement_window = (max(r['started_monotonic_s'] + r['duration_s'] for r in measured)
                          - min(r['started_monotonic_s'] for r in measured)) if measured else None
    by_category = {c: stats([r for r in measured if r['category'] == c], measurement_window) for c in categories}
    def values(key):
        return [float(s[key]) for s in samples_resource if s.get(key) not in (None, '')]
    resource_overview = {
        'gpu_util_mean_pct': statistics.mean(values('gpu_util_pct')) if values('gpu_util_pct') else None,
        'gpu_power_max_w': max(values('gpu_power_w'), default=None),
        'gpu_temp_max_c': max(values('gpu_temp_c'), default=None),
        'psi_some_max_avg10': max(values('psi_some_avg10'), default=None),
        'psi_full_max_avg10': max(values('psi_full_avg10'), default=None),
        'paddleocr_process_rss_max_mib': max(values('paddleocr_process_rss_mib'), default=None),
    }
    summary = {'status': status, 'reason': reason, 'client_http_end_to_end': True,
               'requested_measurements': args.requests, 'completed_measurements': len(measured),
               'warmup_attempted': sum(r['phase'] == 'warmup' for r in rows),
               'run_elapsed_s': elapsed,
               'overall': stats(measured, measurement_window), 'by_category': by_category,
               'measurement_window_s': measurement_window,
               'minimum_mem_available_gib': min((s['mem_available_gib'] for s in samples_resource), default=None),
               'resource_overview': resource_overview,
               'protection_triggered': status == 'memory_protection_aborted',
               'unrun_measurements': max(0, args.requests - len(measured)),
               'p95_note': 'P95 is descriptive for fewer than 100 successes; it is not a stable tail latency estimate.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    write_csv(out / 'requests.csv', REQUEST_FIELDS, rows)
    write_csv(out / 'resources.csv', RESOURCE_FIELDS, samples_resource)
    (out / 'environment.json').write_text(json.dumps(env, indent=2, ensure_ascii=False) + '\n')
    lines = ['# GB10 OCR benchmark', '', f"Status: **{status}**" + (f' — {reason}' if reason else ''), '',
             'Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.',
             'P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.', '',
             f"Measured requests: {len(measured)}/{args.requests}; warmups: {summary['warmup_attempted']}; concurrency: {args.concurrency}.",
             f"Run elapsed time (resource preflight through monitor shutdown, excluding environment discovery and report writing): {elapsed:.3f} s.",
             f"Measured-request window (first measured start to last measured completion): {measurement_window} s.",
             f"Minimum observed MemAvailable: {summary['minimum_mem_available_gib']} GiB.",
             f"Observed mean GPU utilization: {resource_overview['gpu_util_mean_pct']}%; "
             f"maximum memory PSI some/full avg10: {resource_overview['psi_some_max_avg10']}%/{resource_overview['psi_full_max_avg10']}%.",
             f"Co-resident containers at run start: {env.get('co_resident_containers', 'N/A')}.",
             env.get('coexistence_note', 'Container presence does not establish whether another model was generating.'), '',
             '| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    def fmt(x):
        return 'N/A' if x is None else f'{x:.3f}'
    for category, s in by_category.items():
        lines.append(f"| {category} | {s['success']}/{s['attempted']} | {fmt(s['mean_s'])} | {fmt(s['median_p50_s'])} | {fmt(s['p90_s'])} | {fmt(s['p95_s'])} | {fmt(s['min_s'])} | {fmt(s['max_s'])} | {fmt(s['stddev_s'])} | {fmt(s['pages_per_s'])} |")
    lines += ['', f"Overall success rate: {fmt(summary['overall']['success_rate'])}; completed pages: {summary['overall']['pages']}.",
              'Pages/s uses the measured-request window from the first start to the last completion.',
              'Categories remain separate; the overall count is not a combined latency comparison.', '',
              'See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.',
              'On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.',
              'Sampling cannot prevent an instantaneous out-of-memory event.', '']
    if env.get('dataset_samples'):
        lines += ['## Dataset', '', '| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |',
                  '| --- | --- | --- | ---: | ---: | --- |']
        for item in env['dataset_samples']:
            lines.append(f"| {item['id']} | {item['file_type']} | {item['width']}×{item['height']} | "
                         f"{item['bytes']} | {item['pages']} | `{item['sha256']}` |")
        lines.append('')
    (out / 'report.md').write_text('\n'.join(lines))
    return summary

def execute(args, request_fn=one_request, sampler=monitor.sample):
    manifest = validate_manifest()
    scenario, selected = select_samples(args, manifest)
    out = args.output_dir.expanduser().resolve() / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, exist_ok=False)
    env = environment(args, selected)
    env['scenario'] = scenario
    rows = []
    status, reason = 'not_run', None
    started = time.monotonic()
    telemetry = monitor.Monitor(args.sample_interval, sampler=sampler)
    try:
        initial = sampler()
        reason = monitor.protection_reason(initial, initial=True)
        if args.require_ocr_only and (env.get('run_mode') != 'OCR_ONLY' or
                                      env.get('paddleocr_container_state') != 'running' or
                                      env.get('paddleocr_container_health') != 'healthy'):
            status, reason = 'not_run', (f"OCR_ONLY and healthy PaddleOCR preflight required; observed "
                                         f"mode={env.get('run_mode')}, container="
                                         f"{env.get('paddleocr_container_state')}/{env.get('paddleocr_container_health')}")
            telemetry.samples.append(initial)
        elif reason:
            status = 'memory_protection_aborted'
            telemetry.samples.append(initial)
        else:
            probe.health(args.api_url, timeout=min(args.timeout, 10))
            with telemetry:
                tasks = [('warmup', i, selected[i % len(selected)]) for i in range(args.warmup)]
                tasks += [('measure', i + 1, selected[i % len(selected)]) for i in range(args.requests)]
                if args.concurrency == 1:
                    for phase, index, sample in tasks:
                        reason = telemetry.reason or monitor.protection_reason(sampler())
                        if reason:
                            status = 'memory_protection_aborted'
                            break
                        row = invoke_request(request_fn, index, phase, sample, args.api_url, args.timeout)
                        rows.append(row)
                        print(f"{phase} {index} {sample['id']}: {row['status']} {row['duration_s']:.3f}s", flush=True)
                else:
                    # Warmups must finish before measured requests are submitted.
                    for phase, index, sample in tasks[:args.warmup]:
                        reason = telemetry.reason or monitor.protection_reason(sampler())
                        if reason:
                            telemetry.reason = reason
                            telemetry.protection.set()
                            break
                        rows.append(invoke_request(request_fn, index, phase, sample, args.api_url, args.timeout))
                    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                        pending = set()
                        todo = iter(tasks[args.warmup:])
                        exhausted = False
                        while pending or not exhausted:
                            while len(pending) < args.concurrency and not exhausted and not telemetry.protection.is_set():
                                try:
                                    phase, index, sample = next(todo)
                                except StopIteration:
                                    exhausted = True
                                    break
                                reason = monitor.protection_reason(sampler())
                                if reason:
                                    telemetry.reason = reason
                                    telemetry.protection.set()
                                    break
                                pending.add(pool.submit(invoke_request, request_fn, index, phase, sample, args.api_url, args.timeout))
                            if not pending:
                                break
                            done, pending = wait(pending, return_when=FIRST_COMPLETED)
                            rows.extend(f.result() for f in done)
                        if telemetry.protection.is_set():
                            status = 'memory_protection_aborted'
                if telemetry.protection.is_set():
                    status, reason = 'memory_protection_aborted', telemetry.reason
                if status != 'memory_protection_aborted':
                    if len([r for r in rows if r['phase'] == 'measure']) == args.requests and all(r['status'] == 'success' for r in rows):
                        status, reason = 'success', None
                    elif any(r['status'] == 'timeout' for r in rows):
                        status, reason = 'timeout', 'one or more requests timed out'
                    else:
                        status, reason = 'failed', 'one or more requests failed'
                else:
                    reason = telemetry.reason or reason
    except KeyboardInterrupt:
        status, reason = 'user_cancelled', 'interrupted by user'
    except Exception as exc:
        status, reason = 'failed', f'{type(exc).__name__}: {exc}'
    rows.sort(key=lambda r: r['started_monotonic_s'])
    summary = write_reports(out, args, selected, rows, telemetry.samples, status, reason,
                            time.monotonic() - started, env)
    print(f"{status}: {out}", flush=True)
    return summary, out

def main(argv=None):
    summary, _ = execute(parse_args(argv))
    return 0 if summary['status'] == 'success' else 1

if __name__ == '__main__':
    raise SystemExit(main())
