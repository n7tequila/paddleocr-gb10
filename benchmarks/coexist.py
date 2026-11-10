#!/usr/bin/env python3
"""Optional Qwen/OCR comparison helper; never invoked by CI or B1 defaults."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler

import benchmark
import monitor

PROMPT = 'Summarize the purpose of reproducible OCR benchmarks in two short paragraphs.'

def qwen_stream(url, model, prompt, max_tokens, output, started, cancel=None):
    cancel = cancel or threading.Event()
    if cancel.is_set():
        output['status'] = 'user_cancelled'
        started.set()
        return
    data = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                       'max_tokens': max_tokens, 'stream': True,
                       'stream_options': {'include_usage': True}}).encode()
    request = Request(url.rstrip('/') + '/chat/completions', data=data,
                      headers={'Content-Type': 'application/json'}, method='POST')
    start = time.monotonic()
    output['started_monotonic_s'] = start
    text_parts = []
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=120) as response:
            output['_response'] = response
            output['cache_header'] = response.headers.get('x-cache')
            for line in response:
                if cancel.is_set():
                    break
                if not line.startswith(b'data: '):
                    continue
                raw = line[6:].strip()
                if raw == b'[DONE]':
                    break
                event = json.loads(raw)
                if event.get('usage'):
                    output['server_usage'] = event['usage']
                choices = event.get('choices') or []
                content = (choices[0].get('delta') or {}).get('content') if choices else None
                if content:
                    if not started.is_set():
                        output['ttft_s'] = time.monotonic() - start
                        started.set()
                    text_parts.append(content)
        output['status'] = 'user_cancelled' if cancel.is_set() else 'success'
    except Exception as exc:
        output['status'] = 'user_cancelled' if cancel.is_set() else 'failed'
        output['error'] = f'{type(exc).__name__}: {exc}'[:300]
        started.set()
    finally:
        elapsed = time.monotonic() - start
        output['ended_monotonic_s'] = start + elapsed
        usage = output.get('server_usage') or {}
        tokens = usage.get('completion_tokens')
        output['token_method'] = 'server_usage' if tokens is not None else 'estimated_characters_divided_by_4'
        if tokens is None:
            tokens = len(''.join(text_parts)) / 4
        output['output_tokens'] = tokens
        output['output_tokens_per_s'] = tokens / max(elapsed - output.get('ttft_s', 0), 0.001)
        output['generation_duration_s'] = elapsed
        output['request_duration_s'] = elapsed
        output['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
        output.pop('_response', None)

def cancel_qwen(cancel, output, thread):
    """Close only this HTTP request; never touch the Qwen service/container."""
    cancel.set()
    response = output.get('_response')
    if response is not None:
        try:
            response.close()
        except OSError:
            pass
    thread.join(timeout=2)

def parse_args(argv=None):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--allow-coexist-load', action='store_true')
    p.add_argument('--mode', choices=('baseline', 'idle', 'active'), required=True)
    p.add_argument('--qwen-api-url', required=True, help='host-accessible OpenAI-compatible API base URL')
    p.add_argument('--qwen-model', required=True)
    p.add_argument('--qwen-prompt-file', type=Path)
    p.add_argument('--qwen-max-tokens', type=int, default=128)
    p.add_argument('--qwen-cache-state', choices=('enabled', 'disabled', 'unknown'), default='unknown')
    extra, remaining = p.parse_known_args(argv)
    if not extra.allow_coexist_load:
        p.error('B4 requires --allow-coexist-load')
    if extra.qwen_max_tokens < 1 or extra.qwen_max_tokens > 256:
        p.error('qwen-max-tokens must be 1–256; no long-context load')
    args = benchmark.parse_args(remaining + ['--scenario', 'coexist'])
    if args.concurrency != 1:
        p.error('B4 supports serial OCR only')
    return extra, args

def main(argv=None):
    extra, args = parse_args(argv)
    prompt = extra.qwen_prompt_file.read_text() if extra.qwen_prompt_file else PROMPT
    qwen_rows = []
    if extra.mode == 'active':
        def request_fn(index, phase, sample, api_url, timeout):
            pre = monitor.host_memory()
            reason = monitor.protection_reason(pre, initial=True)
            if reason:
                raise RuntimeError('B4 resource gate before Qwen: ' + reason)
            result = {'index': index, 'phase': phase, 'mode': extra.mode,
                      'cache_state_declared': extra.qwen_cache_state}
            ready = threading.Event()
            cancel = threading.Event()
            thread = threading.Thread(target=qwen_stream,
                args=(extra.qwen_api_url, extra.qwen_model, prompt, extra.qwen_max_tokens, result, ready, cancel), daemon=True)
            thread.start()
            try:
                if not ready.wait(30):
                    result['status'] = 'failed'
                    result['error'] = 'Qwen did not begin generation within 30 seconds'
                    qwen_rows.append(result)
                    cancel_qwen(cancel, result, thread)
                    raise RuntimeError(result['error'])
                if result.get('status') == 'failed':
                    qwen_rows.append(result)
                    cancel_qwen(cancel, result, thread)
                    raise RuntimeError('Qwen generation failed: ' + result.get('error', 'unknown'))
                if not thread.is_alive():
                    result['status'] = 'non_overlapping'
                    result['error'] = 'Qwen generation finished before OCR began'
                    qwen_rows.append(result)
                    raise RuntimeError(result['error'])
                row = benchmark.one_request(index, phase, sample, api_url, timeout)
                thread.join(timeout=120)
                if thread.is_alive():
                    result['status'] = 'timeout'
                    result['error'] = 'Qwen generation exceeded join timeout'
                    cancel_qwen(cancel, result, thread)
            except KeyboardInterrupt:
                cancel_qwen(cancel, result, thread)
                raise
            result['overlap_s'] = max(0.0, min(row['started_monotonic_s'] + row['duration_s'],
                                                 result.get('ended_monotonic_s', time.monotonic()))
                                       - max(row['started_monotonic_s'], result['started_monotonic_s']))
            if result['overlap_s'] <= 0:
                result['status'] = 'non_overlapping'
                result['error'] = 'No Qwen/OCR time overlap'
            qwen_rows.append(result)
            return row
    else:
        request_fn = benchmark.one_request
    summary, out = benchmark.execute(args, request_fn=request_fn)
    with (out / 'qwen.csv').open('w', newline='') as f:
        fields = ('index', 'phase', 'mode', 'status', 'ttft_s', 'output_tokens',
                  'output_tokens_per_s', 'token_method', 'generation_duration_s', 'request_duration_s',
                  'overlap_s', 'prompt_sha256', 'cache_state_declared', 'cache_header', 'error')
        writer = csv.DictWriter(f, fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(qwen_rows)
    with (out / 'environment.json').open() as f:
        env = json.load(f)
    env['coexist'] = {'mode': extra.mode, 'qwen_api_url': extra.qwen_api_url,
                      'qwen_model': extra.qwen_model, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                      'max_tokens': extra.qwen_max_tokens, 'prefix_cache_state': extra.qwen_cache_state,
                      'qwen_metrics_note': 'server usage preferred; fallback output characters/4 is an estimate'}
    (out / 'environment.json').write_text(json.dumps(env, indent=2) + '\n')
    with (out / 'report.md').open('a') as f:
        f.write(f'\n## Qwen coexistence mode: {extra.mode}\n\n')
        f.write(f"Qwen model: `{extra.qwen_model}`; declared prefix cache: `{extra.qwen_cache_state}`. "
                'Use the same OCR dataset SHA256 and Qwen prompt SHA256 across A/B/C runs.\n\n')
        if qwen_rows:
            f.write('| Request | Qwen status | TTFT s | Request duration s | Output tokens/s | Token method | OCR overlap s |\n')
            f.write('| ---: | --- | ---: | ---: | ---: | --- | ---: |\n')
            for item in qwen_rows:
                f.write(f"| {item['index']} | {item.get('status', 'N/A')} | "
                        f"{item.get('ttft_s', 'N/A')} | {item.get('request_duration_s', 'N/A')} | "
                        f"{item.get('output_tokens_per_s', 'N/A')} | "
                        f"{item.get('token_method', 'N/A')} | {item.get('overlap_s', 'N/A')} |\n")
        else:
            f.write('Qwen generation metrics: N/A for this mode.\n')
    if extra.mode == 'active' and summary['status'] == 'success' and (
            len(qwen_rows) != args.requests + args.warmup or
            any(r.get('status') != 'success' for r in qwen_rows)):
        summary['status'] = 'failed'
        summary['reason'] = 'Qwen generation failed or did not overlap OCR for every request'
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        with (out / 'report.md').open('a') as f:
            f.write('\nB4 result: failed — Qwen generation failed or did not overlap every OCR request.\n')
    return 0 if summary['status'] == 'success' else 1

if __name__ == '__main__':
    raise SystemExit(main())
