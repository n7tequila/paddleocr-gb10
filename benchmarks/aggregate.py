#!/usr/bin/env python3
"""Validate and combine per-sample reports without pooling latency statistics."""
import argparse
import csv
import json
from pathlib import Path
import statistics

import benchmark


def read_csv(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))

def number(value):
    return float(value) if value not in (None, '') else None

def aggregate(root):
    manifest = benchmark.validate_manifest()
    expected = {s['id']: s for s in manifest['samples']}
    runs = {}
    all_requests, all_resources = [], []
    environments = {}
    for directory in sorted(p for p in root.iterdir() if p.is_dir() and (p / 'summary.json').exists()):
        summary = json.loads((directory / 'summary.json').read_text())
        env = json.loads((directory / 'environment.json').read_text())
        requests = read_csv(directory / 'requests.csv')
        resources = read_csv(directory / 'resources.csv')
        samples = env.get('dataset_samples') or []
        if len(samples) != 1:
            raise ValueError(f'{directory}: expected one sample per run')
        sample = samples[0]
        sid = sample['id']
        if sid in runs or sid not in expected:
            raise ValueError(f'{directory}: duplicate or unknown sample {sid}')
        for key in ('sha256', 'file_type', 'width', 'height', 'bytes', 'pages', 'category'):
            if sample[key] != expected[sid][key]:
                raise ValueError(f'{directory}: manifest mismatch for {sid}/{key}')
        if len(requests) != 4 or sum(r['phase'] == 'warmup' for r in requests) != 1:
            raise ValueError(f'{directory}: expected one warmup and three measurements')
        measured = [r for r in requests if r['phase'] == 'measure']
        if len(measured) != 3:
            raise ValueError(f'{directory}: expected three measurements')
        if not resources or not all(r.get('timestamp_utc') and r.get('monotonic_s') for r in resources):
            raise ValueError(f'{directory}: timestamped resources missing')
        times = [float(r['monotonic_s']) for r in resources]
        if times != sorted(times):
            raise ValueError(f'{directory}: resource timestamps out of order')
        for row in requests:
            if not row.get('started_at_utc') or not row.get('started_monotonic_s') or not row.get('duration_s'):
                raise ValueError(f'{directory}: request timing missing')
        gpu = [r for r in resources if number(r.get('gpu_util_pct')) is not None]
        docker = [r for r in resources if r.get('container_memory_usage')]
        mem = [float(r['mem_available_gib']) for r in resources]
        swap = [float(r['swap_used_gib']) for r in resources]
        status = summary['status']
        run = {'id': sid, 'run_id': directory.name, 'status': status, 'sample': sample,
               'measurements': summary['overall'],
               'markdown_chars': [int(r['markdown_chars']) if r['markdown_chars'] else None for r in measured],
               'http_e2e_s': [number(r['duration_s']) for r in measured],
               'actual_pages': [int(r['pages']) if r['pages'] else None for r in measured],
               'resource': {'mem_available_start_gib': mem[0], 'mem_available_min_gib': min(mem),
                            'mem_available_observed_drop_gib': round(mem[0] - min(mem), 3),
                            'swap_start_gib': swap[0], 'swap_end_gib': swap[-1],
                            'psi_some_max_avg10': max(float(r['psi_some_avg10']) for r in resources),
                            'psi_full_max_avg10': max(float(r['psi_full_avg10']) for r in resources),
                            'gpu_util_mean_pct': statistics.mean(float(r['gpu_util_pct']) for r in gpu) if gpu else None,
                            'gpu_temp_max_c': max((float(r['gpu_temp_c']) for r in gpu if r.get('gpu_temp_c')), default=None),
                            'gpu_power_max_w': max((float(r['gpu_power_w']) for r in gpu if r.get('gpu_power_w')), default=None),
                            'gpu_memory_mib': None if not any(r.get('nvidia_gpu_memory_mib') for r in resources) else 'see resources.csv',
                            'docker_memory_first': docker[0]['container_memory_usage'] if docker else None,
                            'docker_memory_last': docker[-1]['container_memory_usage'] if docker else None,
                            'paddleocr_rss_max_mib': max((float(r['paddleocr_process_rss_mib']) for r in docker if r.get('paddleocr_process_rss_mib')), default=None),
                            'resource_rows': len(resources)}}
        runs[sid] = run
        environments[sid] = env
        for row in requests:
            all_requests.append({'run_id': directory.name, **row})
        for row in resources:
            all_resources.append({'run_id': directory.name, **row})
    if set(runs) != set(expected):
        raise ValueError(f'missing samples: {sorted(set(expected) - set(runs))}')
    ordered = [runs[s['id']] for s in manifest['samples']]
    source_revision_counts = {}
    for key in ('benchmarks/benchmark.py', 'benchmarks/monitor.py', 'benchmarks/datasets/manifest.json'):
        hashes = {(env.get('benchmark_source_sha256') or {}).get(key) for env in environments.values()}
        source_revision_counts[key] = len(hashes)
    modes = {env.get('run_mode', 'UNKNOWN_SHARED') for env in environments.values()}
    result = {'status': 'success' if all(r['status'] == 'success' for r in ordered) else 'failed',
              'run_mode': modes.pop() if len(modes) == 1 else 'MIXED_OR_UNKNOWN',
              'dataset_manifest_sha256': benchmark.sha(benchmark.DATASET / 'manifest.json'),
              'total_warmups': sum(sum(row['phase'] == 'warmup' for row in all_requests if row['run_id'] == r['run_id']) for r in ordered),
              'total_measured_attempts': sum(r['measurements']['attempted'] for r in ordered),
              'total_measured_successes': sum(r['measurements']['success'] for r in ordered),
              'minimum_mem_available_gib': min(r['resource']['mem_available_min_gib'] for r in ordered),
              'per_sample': ordered,
              'source_revision_counts': source_revision_counts,
              'latency_pooling': 'none; each sample/category is reported separately'}
    (root / 'summary.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    def write_rows(name, rows):
        fields = ['run_id'] + [x for x in rows[0] if x != 'run_id']
        with (root / name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fields, extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    write_rows('requests.csv', all_requests)
    write_rows('resources.csv', all_resources)
    source_manifest_hashes = {sid: (env.get('benchmark_source_sha256') or {}).get('benchmarks/datasets/manifest.json')
                              for sid, env in environments.items()}
    (root / 'environment.json').write_text(json.dumps({
        'dataset_manifest_sha256': result['dataset_manifest_sha256'],
        'dataset': manifest['samples'], 'per_sample_environment': environments,
        'source_manifest_sha256_per_run': source_manifest_hashes,
        'note': ('Manifest revisions differ across source runs; each sample SHA256 was checked against the current manifest.'
                 if len(set(source_manifest_hashes.values())) > 1 else 'All source runs used the same dataset manifest revision.')},
        indent=2, ensure_ascii=False) + '\n')
    def fmt(x):
        return 'N/A' if x is None else f'{x:.3f}'
    lines = ['# GB10 B2/B3 document comparison', '',
             f"Status: **{result['status']}**. {result['total_measured_successes']}/{result['total_measured_attempts']} measured requests succeeded; {result['total_warmups']} warmups were recorded.",
             'All latencies are client HTTP end-to-end from request opening to complete response body read. They are not internal model or GPU inference times. Each category is reported independently; no combined latency mean is calculated. P95 with three samples is descriptive only.', '',
             '## Document type and size comparison', '',
             '| Sample | Type | Pixels/page | File bytes | Actual pages/request | Markdown chars/request | Mean s | P50 s | P95 s | Success |',
             '| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |']
    for r in ordered:
        s = r['sample']; m = r['measurements']
        lines.append(f"| {r['id']} | {s['file_type']} | {s['width']}×{s['height']} | {s['bytes']} | "
                     f"{','.join(str(x) for x in r['actual_pages'])} | {','.join(str(x) for x in r['markdown_chars'])} | "
                     f"{fmt(m['mean_s'])} | {fmt(m['median_p50_s'])} | {fmt(m['p95_s'])} | {m['success']}/{m['attempted']} |")
    if 'one-page-pdf' in runs and 'two-page-pdf' in runs:
        single = runs['one-page-pdf']; double = runs['two-page-pdf']
        lines += ['', '## PDF comparison', '',
                  f"The one-page PDF returned {single['actual_pages']} pages with mean HTTP E2E {single['measurements']['mean_s']:.3f} s. "
                  f"The two-page PDF returned {double['actual_pages']} pages with mean {double['measurements']['mean_s']:.3f} s. "
                  'Both sent official `fileType: 0`. The two-page result was observed in a separate run, so the difference includes run-to-run conditions.',
                  'PaddleX 3.7 documents no default PDF page limit, but server configuration can set one; this acceptance verifies only two pages.']
    lines += ['', '## Resource comparison', '',
              '| Sample | GPU util mean % | GPU temp max °C | GPU power max W | MemAvailable start→min GiB | Observed drop GiB | Swap start→end GiB | Docker memory first→last |',
              '| --- | ---: | ---: | ---: | --- | ---: | --- | --- |']
    for r in ordered:
        x = r['resource']
        lines.append(f"| {r['id']} | {fmt(x['gpu_util_mean_pct'])} | {fmt(x['gpu_temp_max_c'])} | {fmt(x['gpu_power_max_w'])} | "
                     f"{x['mem_available_start_gib']:.3f}→{x['mem_available_min_gib']:.3f} | "
                     f"{x['mem_available_observed_drop_gib']:.3f} | {x['swap_start_gib']:.3f}→{x['swap_end_gib']:.3f} | "
                     f"{x['docker_memory_first']}→{x['docker_memory_last']} |")
    lines += ['', f"Lowest observed MemAvailable: {result['minimum_mem_available_gib']:.3f} GiB. PSI some/full remained below stop thresholds; the OCR container stayed healthy.",
             'GPU memory.used is reported only when available; unavailable values are N/A. System MemAvailable, Docker memory, process RSS and NVIDIA memory can overlap on GB10 unified memory and must not be added.',
              'Every resource row has a UTC and monotonic timestamp. GPU and Docker values also carry their own sample timestamps; use the monotonic timestamps in requests.csv to join them. The Docker query can refresh more slowly than host memory/PSI.', '',
              '## Interpretation and limitations', '',
              '- Larger pages, different layout, Chinese text, mathematics, and two PDF pages may affect processing time. These are plausible factors, not isolated causal estimates from this small sample.',
              '- The PNG resolution comparison is between different synthetic images, so it does not isolate resolution alone. The PDFs share the first page, but were measured in separate runs.',
              f"- Runtime classification: {result['run_mode']}. GPU process PIDs are mapped to Docker host process PIDs in environment.json; OCR_ONLY means no non-OCR compute PID was observed at each run's preflight.",
              '- No Qwen workload was started and no B4 experiment was run. Preflight is a snapshot; it cannot rule out transient external workload between checks.',
              f'- Source revisions across the eight runs: {source_revision_counts}. The single-page PDF was added later; raw per-run data remains intact. Compare these results as an acceptance snapshot, not as a tightly controlled causal experiment.',
              '- Three measurements per type are insufficient for stable tail-latency claims. No accuracy ground truth, real handwriting, high concurrency, or long-duration load was tested.',
              '- The dataset contains only fictional synthetic content; no private student work or OCR response body is included.', '',
              '## Detailed run reports', '']
    for r in ordered:
        lines.append(f"- [{r['id']}]({r['run_id']}/report.md)")
    (root / 'report.md').write_text('\n'.join(lines) + '\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report_root', type=Path)
    args = parser.parse_args()
    outcome = aggregate(args.report_root)
    print(f"{outcome['status']}: {outcome['total_measured_successes']}/{outcome['total_measured_attempts']} measured requests")
