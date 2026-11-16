import ctypes
from dataclasses import asdict
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from textual.widgets import DataTable, Static

from ramtaskman.app import RamTaskManager
from ramtaskman.backends.psutil_backend import PsutilBackend
from ramtaskman.backends.windows_system import (
    PerformanceInformation, decode_performance_info, read_windows_system,
)
from ramtaskman.models import WindowsSystemMemory
from test_memory import fixture


class WindowsSystemTests(unittest.TestCase):
    def test_native_page_units_and_zero_are_preserved(self):
        info = PerformanceInformation()
        info.PageSize = 4096
        info.SystemCache = 17
        info.CommitTotal = 30
        info.CommitLimit = 50
        info.CommitPeak = 40
        info.KernelPaged = 7
        result = decode_performance_info(info)
        self.assertEqual(result.system_cache, 17 * 4096)
        self.assertEqual(result.commit_total, 30 * 4096)
        self.assertEqual(result.commit_limit, 50 * 4096)
        self.assertEqual(result.kernel_nonpaged, 0)
        info.PageSize = 0
        with self.assertRaises(ValueError):
            decode_performance_info(info)

    def test_failure_keeps_ram_and_next_sample_recovers(self):
        failure = WindowsSystemMemory(reason='lettura negata')
        good = WindowsSystemMemory(system_cache=500, commit_total=800, commit_limit=2000)
        with patch('psutil.virtual_memory', return_value=SimpleNamespace(total=1000, available=600, free=600)), \
             patch('psutil.swap_memory', return_value=SimpleNamespace(total=2000, used=10)), \
             patch('ramtaskman.backends.windows_system.read_windows_system', side_effect=[good, failure, good]):
            backend = PsutilBackend('windows')
            first, failed, recovered = [backend.read_system() for _ in range(3)]
        self.assertEqual(first.windows_details.system_cache, 500)
        self.assertEqual(failed.used, 400)
        self.assertIsNone(asdict(failed)['windows_details']['system_cache'])
        self.assertEqual(failed.windows_details.reason, 'lettura negata')
        self.assertEqual(recovered.windows_details.system_cache, 500)
        self.assertEqual(recovered.segments, {})
        self.assertIsNone(recovered.cache)  # Windows cache has different semantics from the Linux chart.

    @unittest.skipUnless(sys.platform == 'win32', 'API nativa Windows')
    def test_live_documented_api(self):
        details = read_windows_system()
        self.assertIsNone(details.reason)
        self.assertGreater(details.commit_limit, 0)
        self.assertLessEqual(details.commit_total, details.commit_limit)
        self.assertGreaterEqual(details.kernel_nonpaged, 0)

    @unittest.skipUnless(sys.platform == 'win32', 'API nativa Windows')
    def test_api_error_reports_unknown_counters(self):
        with patch('ctypes.WinDLL', side_effect=OSError('test indisponibile')):
            details = read_windows_system()
        self.assertIsNone(details.commit_total)
        self.assertIn('test indisponibile', details.reason)


class WindowsSystemUITests(unittest.IsolatedAsyncioTestCase):
    async def test_details_resize_and_failure_replace_old_values(self):
        app = RamTaskManager(live=False, slim=False)
        async with app.run_test(size=(160, 48)) as pilot:
            snap = fixture()
            snap.platform = 'windows'
            snap.system.segments = {}
            snap.system.windows_details = WindowsSystemMemory(system_cache=2 << 30, commit_total=5 << 30,
                                                               commit_limit=20 << 30)
            app.apply(snap)
            await pilot.pause()
            def texts():
                return '\n'.join(row.plain for row in app.query_one('#device', Static).content.renderables
                                 if hasattr(row, 'plain'))
            self.assertIn('Cache di sistema 2.00 GiB', texts())
            self.assertIn('Commit 5.00 GiB / 20.00 GiB', texts())
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
            snap.system.windows_details = WindowsSystemMemory(reason='lettura fallita')
            app.apply(snap)
            await pilot.pause()
            self.assertIn('Cache di sistema n/a', texts())
            self.assertNotIn('2.00 GiB', texts())
            self.assertIn('lettura fallita', texts())
