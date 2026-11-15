"""Contracts of optional measurements; not assertions on machine speed."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'tools' / 'benchmark_memory.py'
spec = importlib.util.spec_from_file_location('benchmark_memory_tool', path)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'), 'Test di procfs valido solo su Linux')
    def test_real_benchmark_interrogates_only_own_process(self):
        output = io.StringIO()
        with patch('psutil.process_iter', side_effect=AssertionError('enumerazione processi vietata')):
            with contextlib.redirect_stdout(output):
                benchmark.measure_self_linux(1)
        result = output.getvalue()
        if 'non disponibile' in result or 'incompleto' in result:
            self.skipTest('procfs non leggibile nel runner; nessuna misura inventata')
        self.assertIn('nessun altro processo interrogato', result)
        self.assertIn('smaps_rollup', result)
        self.assertIn('mappature processo smaps', result)
        self.assertNotIn(str(Path.home()), result)

    def test_synthetic_fixture_does_not_read_processes(self):
        with patch('psutil.process_iter', side_effect=AssertionError('enumerazione processi vietata')):
            processes = benchmark.make_processes(20)
            regions = benchmark.make_regions(20)
        self.assertEqual(len(processes), 20)
        self.assertEqual(len(regions), 20)
        self.assertTrue(all(p.name.startswith('process-') for p in processes))
        self.assertTrue(all(r.path.startswith('/synthetic/') for r in regions))


if __name__ == '__main__':
    unittest.main()
