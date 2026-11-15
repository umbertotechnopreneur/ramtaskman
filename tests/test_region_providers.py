"""Provider contracts on synthetic data; not a substitute for native OS tests."""
import ctypes
import unittest
from unittest.mock import patch

import psutil

from ramtaskman.models import ProcessMemory
from ramtaskman.region_provider import LinuxProvider, UnsupportedProvider, make_region_provider
from ramtaskman.regions import RegionSnapshot
from ramtaskman.backends.windows_regions import (WindowsRegionProvider, WinRegion,
                                                  _MemoryBasicInformation64)


def process():
    return ProcessMemory(100, 1.5, 'demo', 1000, '/demo/app')


class FakeAPI:
    def __init__(self):
        self.closed = []
        self.queries = []
        self.regions = [WinRegion(0, 0x1000, 0x10000, 0, 0),
                        WinRegion(0x1000, 0x2000, 0x1000, 4, 0x20000),
                        WinRegion(0x3000, 0x1000, 0x2000, 999, 0x40000)]

    def limits(self):
        return 0, 0x3fff, 0x1000

    def open(self, pid):
        return 'handle'

    def close(self, handle):
        self.closed.append(handle)

    def query(self, handle, address):
        self.queries.append(address)
        return next(r for r in self.regions if r.start <= address < r.start + r.size)


class ProviderTests(unittest.TestCase):
    def test_factory_capabilities_and_unsupported_explanation(self):
        self.assertIsInstance(make_region_provider('linux'), LinuxProvider)
        win = make_region_provider('win32')
        self.assertTrue(win.capabilities.virtual)
        self.assertFalse(win.capabilities.rss)
        self.assertFalse(win.capabilities.pss)
        mac = make_region_provider('darwin')
        self.assertIsInstance(mac, UnsupportedProvider)
        snap = mac.read(process())
        self.assertFalse(snap.complete)
        self.assertIn('macos', snap.reason)
        self.assertEqual(snap.regions, [])

    def test_linux_provider_delegates_without_changing_snapshot(self):
        snap = RegionSnapshot(100, 1.5, 'demo', 10)
        class Reader:
            def read(self, proc, cancelled):
                self.proc, self.cancelled = proc, cancelled
                return snap
        reader = Reader()
        result = LinuxProvider(reader).read(process())
        self.assertIs(result, snap)
        self.assertEqual(reader.proc.pid, 100)

    def test_64bit_structure_sizes_are_explicit(self):
        self.assertEqual(ctypes.sizeof(_MemoryBasicInformation64), 48)
        self.assertEqual(_MemoryBasicInformation64.RegionSize.offset, 24)
        self.assertEqual(_MemoryBasicInformation64.State.offset, 32)

    @patch('ramtaskman.backends.windows_regions._verify')
    def test_windows_enumerates_virtual_not_resident_and_closes_handle(self, verify):
        verify.return_value = 'c:\\demo\\app.exe'
        api = FakeAPI()
        snap = WindowsRegionProvider(api).read(process())
        self.assertTrue(snap.complete)
        self.assertEqual(api.queries, [0, 0x1000, 0x3000])
        self.assertEqual(api.closed, ['handle'])
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(len(snap.regions), 2)  # MEM_FREE is a gap, not allocated RAM
        self.assertEqual(snap.executable_identity, 'c:\\demo\\app.exe')
        commit, reserve = snap.regions
        self.assertEqual(commit.size, 0x2000)
        self.assertEqual(commit.permissions, 'READWRITE')
        self.assertIn('MEM_COMMIT', commit.path)
        self.assertEqual(reserve.permissions, 'n/a')  # Protect is undefined for reserve
        self.assertTrue(all(getattr(r, m) is None for r in snap.regions
                            for m in ('rss', 'pss', 'uss', 'swap', 'swap_pss')))
        self.assertIsNone(snap.total('rss'))

    @patch('ramtaskman.backends.windows_regions._verify')
    def test_cancellation_and_budget_mark_partial_with_handle_closed(self, verify):
        api = FakeAPI()
        snap = WindowsRegionProvider(api, max_queries=2).read(process())
        self.assertFalse(snap.complete)
        self.assertEqual(len(snap.regions), 1)
        self.assertIn('Limite', snap.reason)
        self.assertEqual(api.closed, ['handle'])
        api = FakeAPI()
        checks = iter([False, False, True])
        snap = WindowsRegionProvider(api).read(process(), lambda: next(checks))
        self.assertFalse(snap.complete)
        self.assertIn('annullata', snap.reason)
        self.assertEqual(api.closed, ['handle'])

    @patch('ramtaskman.backends.windows_regions._verify')
    def test_identity_change_and_query_error_never_keep_stale_regions(self, verify):
        api = FakeAPI()
        verify.side_effect = [None, ProcessLookupError()]
        snap = WindowsRegionProvider(api).read(process())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.assertEqual(api.closed, ['handle'])
        api = FakeAPI()
        verify.side_effect = ['c:\\demo\\a.exe', 'c:\\demo\\b.exe']
        snap = WindowsRegionProvider(api).read(process())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.assertEqual(api.closed, ['handle'])
        api = FakeAPI()
        verify.side_effect = None
        api.regions[1] = WinRegion(0x1000, 0, 0x1000, 4, 0x20000)
        # Force bad query instead of FakeAPI lookup failing itself.
        api.query = lambda h, a: WinRegion(0, 0, 0x1000, 4, 0x20000)
        snap = WindowsRegionProvider(api).read(process())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.assertIn('non valido', snap.reason)
        self.assertEqual(api.closed, ['handle'])

    @patch('ramtaskman.backends.windows_regions._verify', side_effect=psutil.AccessDenied(100))
    def test_denied_permission_is_explicit(self, verify):
        snap = WindowsRegionProvider(FakeAPI()).read(process())
        self.assertFalse(snap.complete)
        self.assertIn('accesso negato', snap.reason)


if __name__ == '__main__':
    unittest.main()
