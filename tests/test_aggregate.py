import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks'))
import aggregate
import benchmark

class AggregateTests(unittest.TestCase):
    def test_separate_categories_and_five_file_report(self):
        samples = benchmark.validate_manifest()['samples'][:2]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, sample in enumerate(samples):
                folder = root / f'run-{index}'
                folder.mkdir()
                (folder / 'summary.json').write_text(json.dumps({'status': 'success', 'overall': {
                    'attempted': 3, 'success': 3, 'mean_s': index + 1.0,
                    'median_p50_s': index + 1.0, 'p95_s': index + 1.2}}))
                (folder / 'environment.json').write_text(json.dumps({'dataset_samples': [sample]}))
                requests = [{'phase': phase, 'started_at_utc': '2026-11-10T00:00:00Z',
                             'started_monotonic_s': str(i), 'duration_s': '1.0', 'status': 'success',
                             'pages': '1', 'markdown_chars': '10'}
                            for i, phase in enumerate(['warmup', 'measure', 'measure', 'measure'])]
                resources = [{'timestamp_utc': '2026-11-10T00:00:00Z', 'monotonic_s': '1.0',
                              'mem_available_gib': '20', 'swap_used_gib': '0',
                              'psi_some_avg10': '0', 'psi_full_avg10': '0',
                              'gpu_util_pct': '10', 'gpu_temp_c': '40', 'gpu_power_w': '20',
                              'container_state': 'running/healthy', 'container_memory_usage': '1GiB / 120GiB',
                              'paddleocr_process_rss_mib': '100'}]
                for name, rows in [('requests.csv', requests), ('resources.csv', resources)]:
                    with (folder / name).open('w', newline='') as f:
                        writer = csv.DictWriter(f, rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
            with patch.object(aggregate.benchmark, 'validate_manifest', return_value={'samples': samples}):
                result = aggregate.aggregate(root)
            self.assertEqual(result['total_measured_successes'], 6)
            self.assertEqual([x['measurements']['mean_s'] for x in result['per_sample']], [1.0, 2.0])
            self.assertNotIn('mean_s', result)
            self.assertEqual({p.name for p in root.iterdir() if p.is_file()},
                {'summary.json', 'requests.csv', 'resources.csv', 'environment.json', 'report.md'})
            with (root / 'requests.csv').open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 8)

if __name__ == '__main__':
    unittest.main()
