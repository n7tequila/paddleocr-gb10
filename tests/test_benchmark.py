import io
from contextlib import redirect_stderr
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks'))
import benchmark
import monitor
import coexist

class FakeResponse:
    status = 200
    def __init__(self, body):
        self.body = io.BytesIO(json.dumps(body).encode())
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self):
        return self.body.read()

class BenchmarkTests(unittest.TestCase):
    def test_arguments_and_guard(self):
        args = benchmark.parse_args(['--requests', '2', '--warmup', '0'])
        self.assertEqual((args.requests, args.concurrency, args.api_url), (2, 1, 'http://127.0.0.1:8080'))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                benchmark.parse_args(['--concurrency', '2'])
            with self.assertRaises(SystemExit):
                benchmark.parse_args(['--timeout', '0'])
            with self.assertRaises(SystemExit):
                coexist.parse_args(['--mode', 'active', '--qwen-api-url', 'http://127.0.0.1:9999/v1',
                                    '--qwen-model', 'example'])

    def test_statistics_separate_success_and_failure(self):
        rows = [{'phase': 'measure', 'status': status, 'duration_s': sec, 'pages': pages}
                for status, sec, pages in [('success', 1.0, 1), ('success', 3.0, 2), ('failed', 4.0, 0)]]
        result = benchmark.stats(rows, 10)
        self.assertEqual(result['mean_s'], 2.0)
        self.assertEqual(result['median_p50_s'], 2.0)
        self.assertAlmostEqual(result['p90_s'], 2.8)
        self.assertAlmostEqual(result['p95_s'], 2.9)
        self.assertEqual(result['pages_per_s'], .3)
        self.assertEqual(result['success_rate'], 2 / 3)
        self.assertTrue(result['p95_descriptive_only'])

    def test_b1_throughput_excludes_warmup_but_includes_request_gaps(self):
        # Synthetic timestamps mirror the observed B1 timing pattern; no report artifact is required in CI.
        rows = [
            {'phase': 'warmup', 'category': 'english_print', 'status': 'success', 'duration_s': .8, 'pages': 1,
             'started_monotonic_s': 8.0},
            {'phase': 'measure', 'category': 'english_print', 'status': 'success', 'duration_s': .76, 'pages': 1,
             'started_monotonic_s': 10.0},
            {'phase': 'measure', 'category': 'english_print', 'status': 'success', 'duration_s': .77, 'pages': 1,
             'started_monotonic_s': 12.0},
            {'phase': 'measure', 'category': 'english_print', 'status': 'failed', 'duration_s': .9, 'pages': None,
             'started_monotonic_s': 14.0},
        ]
        args = benchmark.parse_args(['--requests', '3', '--warmup', '1'])
        sample = benchmark.validate_manifest()['samples'][0]
        with tempfile.TemporaryDirectory() as temp:
            result = benchmark.write_reports(Path(temp), args, [sample], rows,
                [{'mem_available_gib': 20}], 'failed', None, 99, {'git_commit': 'mock'})
        self.assertAlmostEqual(result['measurement_window_s'], 4.9)
        self.assertEqual(result['run_elapsed_s'], 99)
        self.assertAlmostEqual(result['overall']['pages_per_s'], 2 / 4.9)
        self.assertAlmostEqual(result['overall']['mean_s'], .765)
        self.assertEqual(result['overall']['success_rate'], 2 / 3)

    def test_manifest_and_pdf_metadata(self):
        manifest = benchmark.validate_manifest()
        self.assertEqual(len(manifest['samples']), 8)
        pdf = next(s for s in manifest['samples'] if s['id'] == 'two-page-pdf')
        self.assertEqual(pdf['pages'], 2)
        args = benchmark.parse_args(['--scenario', 'documents', '--sample-id', 'two-page-pdf'])
        _, selected = benchmark.select_samples(args, manifest)
        self.assertEqual([s['id'] for s in selected], ['two-page-pdf'])

    def test_mock_official_http_request_and_bytes(self):
        sample = benchmark.validate_manifest()['samples'][0].copy()
        sample['path'] = str(benchmark.DATASET / sample['path'])
        body = {'errorCode': 0, 'result': {'layoutParsingResults': [
            {'markdown': {'text': 'Hello'}, 'prunedResult': {}}]}}
        with patch.object(benchmark.probe.OPENER, 'open', return_value=FakeResponse(body)) as opened:
            row = benchmark.one_request(1, 'measure', sample, 'http://127.0.0.1:8080', 30)
        self.assertEqual(row['status'], 'success')
        self.assertEqual((row['http_status'], row['error_code'], row['pages'], row['markdown_chars']), (200, 0, 1, 5))
        self.assertGreater(row['request_bytes'], sample['bytes'])
        self.assertGreater(row['response_bytes'], 0)
        self.assertEqual(opened.call_args.args[0].full_url, 'http://127.0.0.1:8080/layout-parsing')

    def test_http_timer_excludes_payload_preparation_and_json_parse(self):
        sample = benchmark.validate_manifest()['samples'][0].copy()
        sample['path'] = str(benchmark.DATASET / sample['path'])
        body = {'errorCode': 0, 'result': {'layoutParsingResults': [
            {'markdown': {'text': 'OK'}, 'prunedResult': {}}]}}
        response = FakeResponse(body)
        original_read = Path.read_bytes
        original_loads = json.loads
        state = {'read': False, 'parsed': False, 'clock_calls': 0}
        def read(path):
            data = original_read(path)
            state['read'] = True
            return data
        def clock():
            self.assertTrue(state['read'])
            self.assertFalse(state['parsed'])
            state['clock_calls'] += 1
            return 10.0 if state['clock_calls'] == 1 else 10.5
        def parse(data):
            state['parsed'] = True
            return original_loads(data)
        with patch.object(Path, 'read_bytes', read), \
             patch.object(benchmark.time, 'monotonic', clock), \
             patch.object(benchmark.json, 'loads', parse), \
             patch.object(benchmark.probe.OPENER, 'open', return_value=response):
            row = benchmark.one_request(1, 'measure', sample, 'http://127.0.0.1:8080', 30)
        self.assertEqual(row['duration_s'], .5)
        self.assertEqual(state['clock_calls'], 2)
        self.assertEqual(row['status'], 'success')

    def test_report_structure_and_memory_gate(self):
        self.assertIsNotNone(monitor.protection_reason({'mem_available_gib': 11, 'psi_some_avg10': 0, 'psi_full_avg10': 0}, initial=True))
        self.assertIsNotNone(monitor.protection_reason({'mem_available_gib': 20, 'psi_some_avg10': 5, 'psi_full_avg10': 0}))
        self.assertIsNotNone(monitor.protection_reason({'mem_available_gib': 20, 'psi_some_avg10': 0, 'psi_full_avg10': 1}))
        args = benchmark.parse_args(['--warmup', '0', '--requests', '1'])
        sample = benchmark.validate_manifest()['samples'][0]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            row = {'phase': 'measure', 'status': 'success', 'duration_s': 1.0, 'pages': 1,
                   'category': sample['category'], 'started_monotonic_s': 1.0}
            summary = benchmark.write_reports(out, args, [sample], [row],
                [{'mem_available_gib': 20}], 'success', None, 1.0, {'git_commit': 'mock'})
            self.assertEqual(summary['status'], 'success')
            self.assertEqual({p.name for p in out.iterdir()},
                {'summary.json', 'requests.csv', 'resources.csv', 'report.md', 'environment.json'})
            self.assertIn('client-measured HTTP end-to-end', (out / 'report.md').read_text())

    def test_low_memory_aborts_before_health_or_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            args = benchmark.parse_args(['--requests', '1', '--warmup', '0', '--output-dir', temp])
            low = lambda: {'timestamp_utc': 'mock', 'monotonic_s': 1.0,
                           'mem_available_gib': 11.9, 'swap_used_gib': 0,
                           'psi_some_avg10': 0, 'psi_full_avg10': 0}
            with patch.object(benchmark, 'environment', return_value={'git_commit': 'mock'}), \
                 patch.object(benchmark.probe, 'health') as health, \
                 patch.object(benchmark, 'one_request') as request:
                summary, out = benchmark.execute(args, request_fn=request, sampler=low)
            self.assertEqual(summary['status'], 'memory_protection_aborted')
            self.assertEqual(summary['unrun_measurements'], 1)
            health.assert_not_called()
            request.assert_not_called()
            self.assertTrue((out / 'report.md').exists())

if __name__ == '__main__':
    unittest.main()
