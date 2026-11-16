import asyncio
import threading
import unittest
from unittest.mock import patch

from ramtaskman.app import RamTaskManager
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.comparison import ComparisonCancelled, compare_captures
from ramtaskman.regions import MemoryRegion, RegionSnapshot
from ramtaskman.region_screen import RegionScreen
from test_memory import fixture
from test_region_ui import region_fixture
from ui_helpers import open_selected_process_regions


class ComparisonCancellationTests(unittest.TestCase):
    def test_cancelled_computation_does_not_return_partial_comparison(self):
        proc = fixture().processes[0]
        a = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=1,
                            executable_identity=proc.executable)
        b = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=2,
                            executable_identity=proc.executable)
        with self.assertRaises(ComparisonCancelled):
            compare_captures(a, b, cancelled=lambda: True)
        self.assertTrue(compare_captures(a, b).compatible)

    def test_cancel_large_comparison_after_validation_before_completing(self):
        proc = fixture().processes[0]
        rows = [MemoryRegion(i * 4096, (i + 1) * 4096, rss=i, pss=i, uss=i, swap=0)
                for i in range(1024)]
        raw = RegionSnapshot(proc.pid, proc.started_at, proc.name, 100., rows)
        a = freeze_snapshot(raw, collection_session_id='session', sequence=1, executable_identity=proc.executable)
        b = freeze_snapshot(raw, collection_session_id='session', sequence=2, executable_identity=proc.executable)
        calls = [0]
        def cancelled():
            calls[0] += 1
            return calls[0] >= 11  # two validation passes succeeded, then processing stops
        with self.assertRaises(ComparisonCancelled):
            compare_captures(a, b, cancelled=cancelled)
        self.assertGreaterEqual(calls[0], 11)


class ComparisonWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_capture_freezes_in_worker_thread(self):
        import ramtaskman.region_screen as module
        from test_region_ui import FakeReader
        ui_thread = threading.get_ident()
        freeze_threads = []
        original = module.freeze_snapshot
        def instrumented(*args, **kwargs):
            freeze_threads.append(threading.get_ident())
            return original(*args, **kwargs)
        app = RamTaskManager(live=False, region_reader=FakeReader())
        with patch.object(module, 'freeze_snapshot', side_effect=instrumented):
            async with app.run_test(size=(80, 24)) as pilot:
                await open_selected_process_regions(app, pilot, fixture())
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertEqual(len(freeze_threads), 1)
                self.assertNotEqual(freeze_threads[0], ui_thread)
                self.assertIs(app.screen.snapshot, app.screen.current_capture)

    async def test_cancelled_worker_never_applies_old_result_and_does_not_cancel_app_worker(self):
        proc = fixture().processes[0]
        a = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=1,
                            executable_identity=proc.executable)
        b = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=2,
                            executable_identity=proc.executable)
        first_started = threading.Event()
        first_cancelled = threading.Event()
        lock = threading.Lock()
        calls = []

        def slow_first(left, right, cancelled=None):
            with lock:
                calls.append((left, right))
                first = len(calls) == 1
            if first:
                first_started.set()
                while not cancelled():
                    first_cancelled.wait(.01)
                first_cancelled.set()
                raise ComparisonCancelled()
            return compare_captures(left, right, cancelled=cancelled)

        app = RamTaskManager(live=False)
        with patch('ramtaskman.region_screen.compare_captures', side_effect=slow_first):
            async with app.run_test(size=(80, 24)) as pilot:
                app.apply(fixture())
                main_worker = app.run_worker(asyncio.sleep(30), group='principal-test')
                screen = RegionScreen(proc, 'linux', offline_capture=b, offline_baseline=a)
                app.push_screen(screen)
                await pilot.pause()
                self.assertTrue(first_started.is_set())
                self.assertIn('in corso', str(screen.query_one('#region-map-title').content))
                # A becomes the old B while the old A→B comparison is still running.
                screen.action_baseline()
                await pilot.pause(.5)
                self.assertTrue(first_cancelled.is_set())
                self.assertIs(screen.baseline, b)
                self.assertIs(screen._comparison_result.before, b)
                self.assertIs(screen._comparison_result.after, b)
                self.assertEqual(screen._comparison_result.totals['rss'], 0)
                await pilot.press('escape')
                await pilot.pause()
                self.assertIsNone(screen._comparison_pending)
                self.assertFalse(main_worker.is_cancelled)
                main_worker.cancel()

    async def test_close_while_old_worker_returns_result_does_not_reopen_or_apply(self):
        proc = fixture().processes[0]
        a = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=1,
                            executable_identity=proc.executable)
        b = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=2,
                            executable_identity=proc.executable)
        started, release = threading.Event(), threading.Event()

        def slow_uninterruptible(left, right, cancelled=None):
            started.set()
            release.wait(2)  # models a call that cannot be interrupted in flight
            return compare_captures(left, right)

        app = RamTaskManager(live=False)
        with patch('ramtaskman.region_screen.compare_captures', side_effect=slow_uninterruptible):
            async with app.run_test(size=(80, 24)) as pilot:
                app.apply(fixture())
                screen = RegionScreen(proc, 'linux', offline_capture=b, offline_baseline=a)
                app.push_screen(screen)
                try:
                    await pilot.pause()
                    self.assertTrue(started.is_set())
                    await pilot.press('escape')
                    release.set()
                    await pilot.pause(.3)
                    self.assertIsNot(app.screen, screen)
                    self.assertIsNone(screen._comparison_result)
                    self.assertTrue(app.is_running)
                finally:
                    release.set()

    async def test_offline_transient_error_can_be_retried_explicitly(self):
        proc = fixture().processes[0]
        a = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=1,
                            executable_identity=proc.executable)
        b = freeze_snapshot(region_fixture(proc), collection_session_id='session', sequence=2,
                            executable_identity=proc.executable)
        calls = [0]
        def fail_once(left, right, cancelled=None):
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError('errore transitorio')
            return compare_captures(left, right, cancelled=cancelled)
        app = RamTaskManager(live=False)
        with patch('ramtaskman.region_screen.compare_captures', side_effect=fail_once):
            async with app.run_test(size=(80, 24)) as pilot:
                app.apply(fixture())
                screen = RegionScreen(proc, 'linux', offline_capture=b, offline_baseline=a)
                app.push_screen(screen)
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIn('non disponibile', str(screen.query_one('#region-map-title').content))
                screen.render_regions()
                await pilot.pause()
                self.assertEqual(calls[0], 1)  # no implicit retry loop
                await pilot.press('c', 'c')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertEqual(calls[0], 2)
                self.assertTrue(screen._comparison_result.compatible)

    async def test_escape_from_old_zoom_keeps_comparison_visible(self):
        from ramtaskman.delta_bar import DeltaBar
        from ramtaskman.region_map import RegionMap
        from textual.widgets import DataTable
        from test_comparison_ui import Reader
        app = RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(80, 24)) as pilot:
            await open_selected_process_regions(app, pilot, fixture())
            await app.workers.wait_for_complete()
            await pilot.pause()
            screen = app.screen
            await pilot.press('z', 'b', 'r')
            await app.workers.wait_for_complete()
            await pilot.press('c')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIsNotNone(screen.zoom_key)
            await pilot.press('escape')
            await pilot.pause()
            self.assertTrue(screen.comparison_mode)
            self.assertIsNone(screen.zoom_key)
            self.assertFalse(screen.query_one('#region-map', RegionMap).display)
            self.assertTrue(screen.query_one('#delta-bar', DeltaBar).display)
            self.assertGreater(screen.query_one('#region-table', DataTable).row_count, 0)


if __name__ == '__main__':
    unittest.main()
