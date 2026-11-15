"""Verifica del flusso senza chiamare API Windows; non prova l'ABI nativa."""
import importlib.util
import io
import ctypes
from contextlib import redirect_stderr
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('verify_windows_regions',
                                             Path(__file__).parents[1] / 'tools' / 'verify_windows_regions.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeAPI:
    def __init__(self):
        self.state = 'MEM_FREE'
        self.calls = []
        self.fail_at = None
        self.flags = 0

    def page_size(self): return 4096
    def reserve(self, size):
        self.calls.append('reserve'); self.state = 'MEM_RESERVE'; return 0x10000
    def commit(self, address, size):
        self.calls.append('commit'); self.state = 'MEM_COMMIT'
        if self.fail_at == 'commit': raise OSError('commit negato')
    def touch(self, address, size, page_size):
        self.calls.append('touch'); self.flags = 1
    def release(self, address):
        self.calls.append('release'); self.state = 'MEM_FREE'; self.flags = 0
    def query_region(self, address):
        return {'state': self.state, 'start': hex(address)}
    def query_pages(self, addresses):
        self.calls.append(('query', len(addresses)))
        if self.fail_at == 'query': raise OSError('query negata')
        return [self.flags] * len(addresses)


class WindowsProbeTests(unittest.TestCase):
    def test_four_stages_and_release_only_own_allocation(self):
        api = FakeAPI()
        result = probe.run_probe(api, size=4096*2)
        stages = result['stages']
        self.assertEqual([stages[k]['region']['state'] for k in ('reserved','committed','touched','released')],
                         ['MEM_RESERVE','MEM_COMMIT','MEM_COMMIT','MEM_FREE'])
        self.assertEqual(stages['touched']['pages']['valid_bit_1'], 2)
        self.assertEqual(stages['reserved']['pages']['valid_bit_0'], 2)
        self.assertEqual(api.calls.count('release'), 1)
        self.assertNotIn('rss', stages['touched']['pages'])

    def test_release_runs_when_commit_fails(self):
        api = FakeAPI(); api.fail_at = 'commit'
        with self.assertRaises(OSError): probe.run_probe(api, size=4096)
        self.assertEqual(api.calls.count('release'), 1)

    def test_failed_batch_is_unknown_and_proceeds_to_release(self):
        api = FakeAPI(); api.fail_at = 'query'
        result = probe.run_probe(api, size=4096)
        for row in result['stages'].values():
            self.assertFalse(row['pages']['complete'])
            self.assertIsNone(row['pages']['valid_bit_1'])
            self.assertEqual(row['pages']['pages_queried'], 0)
        self.assertEqual(api.calls.count('release'), 1)

    def test_page_batches_are_bounded_and_partial_is_not_total(self):
        api = FakeAPI()
        first = api.query_pages
        def fail_after_first(addresses):
            if len([c for c in api.calls if isinstance(c, tuple)]) == 1:
                raise OSError('secondo batch negato')
            return first(addresses)
        api.query_pages = fail_after_first
        result = probe.sample_pages(api, 0x10000, 4096*257, 4096)
        self.assertEqual(result['pages_queried'], 256)
        self.assertIsNone(result['valid_bit_0'])
        self.assertFalse(result['complete'])

    def test_invalid_parameters_and_native_guard(self):
        api = FakeAPI()
        for size, hold in ((0, 0), (4097, 0), (4096, 301)):
            with self.assertRaises(ValueError): probe.run_probe(api, size=size, hold_seconds=hold)
        with patch.object(probe.sys, 'platform', 'linux'):
            with self.assertRaises(RuntimeError): probe.NativeAPI()
        self.assertEqual(api.calls, [])

    def test_hold_emits_pid_without_touching_other_processes(self):
        api = FakeAPI()
        with patch.object(probe.time, 'sleep') as sleep, redirect_stderr(io.StringIO()) as output:
            probe.run_probe(api, size=4096, hold_seconds=1)
        sleep.assert_called_once_with(1)
        self.assertIn('PID ', output.getvalue())


@unittest.skipUnless(sys.platform == 'win32' and ctypes.sizeof(ctypes.c_void_p) == 8,
                     'richiede Python Windows a 64 bit; nessuna prova nativa su questo sistema')
class WindowsProbeNativeTests(unittest.TestCase):
    def test_current_process_reserve_commit_touch_and_release(self):
        result = probe.run_probe(probe.NativeAPI())
        stages = result['stages']
        self.assertEqual(stages['reserved']['region']['state'], 'MEM_RESERVE')
        self.assertEqual(stages['committed']['region']['state'], 'MEM_COMMIT')
        self.assertEqual(stages['touched']['region']['state'], 'MEM_COMMIT')
        self.assertTrue(stages['touched']['pages']['complete'], stages['touched']['pages']['reason'])
        if result['provider']['complete']:
            self.assertTrue(result['provider']['region_found'])
            self.assertIsNone(result['provider']['rss'])


if __name__ == '__main__':
    unittest.main()
