import json
from contextlib import redirect_stderr
import io
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks'))
import coexist

class StreamResponse:
    def __init__(self):
        self.headers = {'x-cache': 'MISS'}
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close()
    def close(self):
        self.closed = True
    def __iter__(self):
        yield b'data: ' + json.dumps({'choices': [{'delta': {'content': 'Hello'}}]}).encode() + b'\n'
        yield b'data: ' + json.dumps({'choices': [], 'usage': {'completion_tokens': 2}}).encode() + b'\n'
        yield b'data: [DONE]\n'

class CoexistMockTests(unittest.TestCase):
    def test_stream_records_server_usage_ttft_and_full_duration(self):
        response = StreamResponse()
        opener = Mock()
        opener.open.return_value = response
        output, ready = {}, threading.Event()
        with patch.object(coexist, 'build_opener', return_value=opener):
            coexist.qwen_stream('http://127.0.0.1:9999/v1', 'mock-model', 'fixed prompt', 32, output, ready)
        self.assertTrue(ready.is_set())
        self.assertEqual(output['status'], 'success')
        self.assertEqual(output['cache_header'], 'MISS')
        self.assertEqual(output['output_tokens'], 2)
        self.assertEqual(output['token_method'], 'server_usage')
        self.assertGreaterEqual(output['request_duration_s'], output['ttft_s'])
        self.assertGreaterEqual(output['output_tokens_per_s'], 0)
        self.assertTrue(response.closed)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:9999/v1/chat/completions')
        self.assertEqual(json.loads(request.data)['model'], 'mock-model')

    def test_cancel_closes_only_request_and_prevents_new_call(self):
        cancel, ready, output = threading.Event(), threading.Event(), {}
        response = StreamResponse()
        thread = Mock()
        output['_response'] = response
        coexist.cancel_qwen(cancel, output, thread)
        self.assertTrue(cancel.is_set())
        self.assertTrue(response.closed)
        thread.join.assert_called_once_with(timeout=2)
        with patch.object(coexist, 'build_opener') as opener:
            coexist.qwen_stream('http://127.0.0.1:9999/v1', 'mock-model', 'fixed prompt',
                                32, output, ready, cancel)
            opener.assert_not_called()
        self.assertEqual(output['status'], 'user_cancelled')

    def test_explicit_gate_and_serial_only(self):
        extra, args = coexist.parse_args(['--allow-coexist-load', '--mode', 'active',
            '--qwen-api-url', 'http://127.0.0.1:9999/v1', '--qwen-model', 'mock-model',
            '--requests', '1', '--warmup', '0'])
        self.assertEqual(extra.qwen_model, 'mock-model')
        self.assertEqual(args.concurrency, 1)
        self.assertEqual(args.scenario, 'coexist')
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                coexist.parse_args(['--allow-coexist-load', '--mode', 'active',
                    '--qwen-api-url', 'http://127.0.0.1:9999/v1', '--qwen-model', 'mock-model',
                    '--concurrency', '2', '--allow-concurrency'])

if __name__ == '__main__':
    unittest.main()
