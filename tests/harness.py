#!/usr/bin/env python3
"""Independent L1-L6 checks with one JSON report per invocation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from api import probe
from release import check as release_check
from stability import resources

LAYERS = ("static", "environment", "gpu", "api", "stability", "release", "all")
IMAGE = os.environ.get("PADDLEOCR_IMAGE", "paddleocr-gb10:0.2.0")
API_URL = os.environ.get("PADDLEOCR_API_URL", "http://127.0.0.1:8080")
REPORT_ROOT = ROOT / "tests/reports"
FIXTURE = ROOT / "tests/fixtures/ocr-smoke.png"


class Skip(Exception):
    pass


def env_float(name, default):
    value = float(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def command(args, *, input_text=None, timeout=60):
    result = subprocess.run(args, cwd=ROOT, input=input_text, text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args)} failed ({result.returncode}): "
                           f"{(result.stderr or result.stdout)[-1500:]}")
    return result.stdout.strip()


class Report:
    def __init__(self, layer):
        stamp = datetime.now(timezone.utc)
        self.directory = REPORT_ROOT / stamp.strftime("%Y%m%dT%H%M%SZ")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / f"{layer}.json"
        self.data = {"project": "paddleocr-gb10", "image": IMAGE,
                     "timestamp": stamp.isoformat(), "layer": layer,
                     "tests": [], "summary": {"passed": 0, "failed": 0, "skipped": 0}}

    def add(self, name, function):
        start = time.monotonic()
        try:
            detail = function() or {}
            status, reason = "PASS", ""
        except Skip as exc:
            detail, status, reason = {}, "SKIP", str(exc)
        except Exception as exc:
            detail, status, reason = {}, "FAIL", f"{type(exc).__name__}: {exc}"
        item = {"name": name, "status": status, "duration_s": round(time.monotonic()-start, 3)}
        if reason:
            item["reason"] = reason
        if detail:
            item["details"] = detail
        self.data["tests"].append(item)
        self.data["summary"][{"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}[status]] += 1
        print(f"{status:4} {name}" + (f": {reason}" if reason else ""), flush=True)
        self.save()
        return status

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n")


def static_checks(report):
    report.add("shell syntax", lambda: {
        "files": len([command(["bash", "-n", str(p)]) for p in ROOT.rglob("*.sh")
                      if ".git" not in p.parts and "reports" not in p.parts])})
    report.add("Python syntax and tracked artifact safety", lambda: command([sys.executable, "tests/static_check.py"]))
    report.add("Docker source references", lambda: command([sys.executable, "tests/docker_static_check.py"]))
    report.add("Compose config", lambda: command(["docker", "compose", "--env-file", "docker/.env.example",
                                                  "-f", "docker/compose.yaml", "config", "--quiet"]))
    report.add("ignore rules", check_ignores)
    report.add("README commands and links", check_readmes)
    report.add("git diff whitespace", lambda: command(["git", "diff", "--check"]))


def check_ignores():
    paths = ("docker/.env", "docker/api-smoke-result.json", "docker/Dockerfile.backup.20261110",
             "tests/reports/example.json", "models/model.bin", "wheels/test.whl", "credentials.json")
    for path in paths:
        command(["git", "check-ignore", "-q", path])
    result = subprocess.run(["git", "check-ignore", "-q", "docker/.env.example"], cwd=ROOT)
    assert result.returncode == 1, "docker/.env.example must stay trackable"
    dockerignore = (ROOT / "docker/.dockerignore").read_text()
    for pattern in ("**/.env", "**/models", "**/wheels", "**/build"):
        assert pattern in dockerignore, f".dockerignore lacks {pattern}"
    return {"ignored_paths": list(paths)}


def check_readmes():
    for name in ("README.md", "README.zh-CN.md"):
        source = (ROOT / name).read_text()
        for path in ("docker/compose.yaml", "docker/.env.example", "docker/test-official-api.py",
                     "tests/run-tests.sh"):
            assert path in source and (ROOT / path).exists(), f"{name}: missing command target {path}"
        for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", source):
            target = target.split()[0].split("#")[0]
            if target and not target.startswith(("http:", "https:", "mailto:")):
                assert (ROOT / target).exists(), f"{name}: broken link {target}"
    return {"readmes": ["README.md", "README.zh-CN.md"]}


def image_available():
    try:
        command(["docker", "image", "inspect", IMAGE], timeout=20)
    except Exception as exc:
        raise Skip(f"Local image unavailable; no pull attempted: {exc}") from exc


def docker_python(script, gpu=False):
    image_available()
    args = ["docker", "run", "--rm", "-i", "--pull", "never", "--network", "none"]
    if gpu:
        args += ["--gpus", "all"]
    args += ["--entrypoint", "python", IMAGE, "-"]
    output = command(args, input_text=script, timeout=120)
    try:
        return json.loads(output.splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"Image check produced no final JSON record: {output[-1000:]}") from exc


def environment_checks(report):
    report.add("existing image package and metadata check", lambda: docker_python(
        (ROOT / "tests/environment/check.py").read_text()))


def gpu_checks(report):
    def run():
        if os.environ.get("PADDLEOCR_ALLOW_GPU_TEST") != "1":
            raise Skip("Set PADDLEOCR_ALLOW_GPU_TEST=1 to authorize a tiny GPU calculation")
        s = resources.snapshot()
        if s["mem_available_gib"] < env_float("PADDLEOCR_GPU_MIN_GIB", 8):
            raise Skip(f"GPU memory gate: {s['mem_available_gib']} GiB available")
        result = docker_python((ROOT / "tests/gpu/check.py").read_text(), gpu=True)
        result["host_before"] = s
        return result
    report.add("GB10 tiny CUDA matrix calculation", run)


def memory_gate():
    before = resources.snapshot()
    minimum = env_float("PADDLEOCR_MIN_MEM_GIB", 12)
    max_psi = env_float("PADDLEOCR_MAX_PSI_AVG10", 10)
    if not resources.safe_to_start(before, minimum, max_psi):
        raise Skip(f"Inference gate: {before}; require >= {minimum} GiB and PSI <= {max_psi}%")
    return before, max_psi


def run_inference(report, label, require_start=True):
    def check():
        if require_start:
            before, max_psi = memory_gate()
        else:
            before = resources.snapshot()
            max_psi = env_float("PADDLEOCR_MAX_PSI_AVG10", 10)
            if not resources.safe_to_continue(before, env_float("PADDLEOCR_STOP_MEM_GIB", 8), max_psi):
                raise RuntimeError(f"Resource stop threshold reached before next request: {before}")
        path = report.directory / f"{label}-response.json"
        def save_response(status, body, elapsed):
            path.write_text(json.dumps({"http_status": status, "elapsed_s": round(elapsed, 3),
                                        "response": body}, ensure_ascii=False, indent=2) + "\n")
        monitor = resources.Monitor()
        try:
            with monitor:
                result = probe.infer(API_URL, FIXTURE,
                                     timeout=env_float("PADDLEOCR_API_TIMEOUT", 300),
                                     on_response=save_response)
        finally:
            if monitor.samples:
                (report.directory / f"{label}-memory.json").write_text(json.dumps(
                    {"before": before, **monitor.summary()}, indent=2) + "\n")
        summary = monitor.summary()
        result["memory"] = {"before": before, **summary}
        result.pop("response")
        result["response_file"] = str(path)
        if summary["min_mem_available_gib"] < env_float("PADDLEOCR_STOP_MEM_GIB", 8) or max(
                summary["max_psi_some_avg10"], summary["max_psi_full_avg10"]) > max_psi:
            raise RuntimeError(f"Memory/PSI stop threshold crossed during request: {summary}; response saved to {path}")
        return result
    return check


def api_checks(report):
    report.add("official GET /health", lambda: probe.health(API_URL))
    report.add("official POST /layout-parsing contract", run_inference(report, "api"))


def container_health():
    raw = command(["docker", "inspect", "--format", "{{json .State.Health}}", "paddleocr-gb10"])
    state = json.loads(raw)
    assert state is not None, "Running container has no Docker healthcheck; apply Compose config first"
    return state.get("Status")


def stability_checks(report):
    if os.environ.get("PADDLEOCR_ALLOW_STABILITY_TEST") != "1":
        report.add("stability authorization", lambda: (_ for _ in ()).throw(Skip(
            "Set PADDLEOCR_ALLOW_STABILITY_TEST=1 to authorize serial OCR requests")))
        return

    def ready():
        memory_gate()
        deadline = time.monotonic() + 180
        seen = []
        while time.monotonic() < deadline:
            status = container_health()
            seen.append(status)
            if status == "healthy":
                probe.health(API_URL)
                return {"states": seen, "transition_observed": "starting" in seen}
            if status != "starting":
                raise AssertionError(f"Container health is {status}; states={seen}")
            time.sleep(5)
        raise AssertionError(f"Container did not become healthy: {seen}")

    if report.add("Docker health and HTTP health", ready) != "PASS":
        return
    transition_observed = report.data["tests"][-1]["details"]["transition_observed"]
    def transition_check():
        if not transition_observed:
            raise Skip("Container was already healthy; observing startup would require a restart")
        return {"observed": True}
    report.add("starting to healthy transition", transition_check)
    for index in range(1, 4):
        def serial_check(index=index):
            current = resources.snapshot()
            if not resources.safe_to_continue(current, env_float("PADDLEOCR_STOP_MEM_GIB", 8),
                                              env_float("PADDLEOCR_MAX_PSI_AVG10", 10)):
                raise RuntimeError(f"Resource stop threshold reached before request {index}: {current}")
            return run_inference(report, f"stability-{index}", require_start=False)()
        if report.add(f"serial OCR request {index}/3", serial_check) != "PASS":
            return
    invalid_cases = (("missing file", {"fileType": 1}),
                     ("invalid Base64", {"file": "!!!not-base64!!!", "fileType": 1}),
                     ("invalid fileType", {"file": "AAAA", "fileType": 999}))
    for label, payload in invalid_cases:
        def check_invalid(payload=payload):
            current = resources.snapshot()
            if not resources.safe_to_continue(current, env_float("PADDLEOCR_STOP_MEM_GIB", 8),
                                              env_float("PADDLEOCR_MAX_PSI_AVG10", 10)):
                raise RuntimeError(f"Resource stop threshold reached before invalid request: {current}")
            return probe.invalid_request(API_URL, payload)
        if report.add(label, check_invalid) != "PASS":
            return
        report.add(f"health after {label}", lambda: probe.health(API_URL))
    report.add("Docker still healthy", lambda: {"status": container_health()} if container_health() == "healthy"
               else (_ for _ in ()).throw(AssertionError("Container no longer healthy")))


def release_checks(report):
    report.add("anonymous GHCR manifest and linux/arm64", release_check.check_ghcr)
    report.add("GitHub v0.2.0 Release assets and SHA256SUMS", release_check.check_release)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("layer", choices=LAYERS)
    args = parser.parse_args()
    report = Report(args.layer)
    try:
        selected = ("static", "environment", "release") if args.layer == "all" else (args.layer,)
        for layer in selected:
            {"static": static_checks, "environment": environment_checks, "gpu": gpu_checks,
             "api": api_checks, "stability": stability_checks, "release": release_checks}[layer](report)
    except Exception as exc:
        report.add("harness error", lambda: (_ for _ in ()).throw(exc))
        traceback.print_exc()
    report.save()
    print(f"Summary: {report.data['summary']} | {report.path}")
    return 1 if report.data["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
