"""Host memory safeguards for serial inference tests."""
from pathlib import Path
import threading

GIB = 1024 ** 3


def snapshot():
    meminfo = Path("/proc/meminfo").read_text()
    available_kib = next(int(line.split()[1]) for line in meminfo.splitlines()
                         if line.startswith("MemAvailable:"))
    psi = Path("/proc/pressure/memory").read_text()
    values = {}
    for line in psi.splitlines():
        parts = line.split()
        values[parts[0]] = float(next(x.split("=")[1] for x in parts[1:] if x.startswith("avg10=")))
    return {"mem_available_gib": round(available_kib * 1024 / GIB, 3),
            "psi_some_avg10": values["some"], "psi_full_avg10": values["full"]}


def safe_to_start(s, start_gib=12.0, max_psi=10.0):
    return s["mem_available_gib"] >= start_gib and max(s["psi_some_avg10"], s["psi_full_avg10"]) <= max_psi


def safe_to_continue(s, stop_gib=8.0, max_psi=10.0):
    return s["mem_available_gib"] >= stop_gib and max(s["psi_some_avg10"], s["psi_full_avg10"]) <= max_psi


class Monitor:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.samples = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop_event.wait(self.interval):
            self.samples.append(snapshot())

    def __enter__(self):
        self.samples.append(snapshot())
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.samples.append(snapshot())

    def summary(self):
        return {"samples": len(self.samples),
                "min_mem_available_gib": min(x["mem_available_gib"] for x in self.samples),
                "max_psi_some_avg10": max(x["psi_some_avg10"] for x in self.samples),
                "max_psi_full_avg10": max(x["psi_full_avg10"] for x in self.samples)}
