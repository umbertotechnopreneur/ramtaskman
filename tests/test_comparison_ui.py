import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from textual.widgets import DataTable, Input, Select, Static
from ramtaskman.app import RamTaskManager
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.region_screen import RegionScreen
from ramtaskman.regions import RegionSnapshot
from test_memory import fixture
from test_region_ui import region_fixture


class Reader:
    def __init__(self):
        self.calls = 0
        self.failure = False

    def read(self, process, cancelled=None):
        self.calls += 1
        if self.failure:
            return RegionSnapshot(process.pid, process.started_at, process.name, time.time(),
                                  reason='accesso negato', complete=False)
        snap = region_fixture(process)
        snap.regions[2].inode = 7
        if self.calls > 1:
            snap.regions[1].rss += 30 << 20
            snap.regions[2].rss -= 4 << 20
        return snap


class ComparisonUI(unittest.IsolatedAsyncioTestCase):
    async def open_region(self, app, pilot):
        app.apply(fixture())
        await pilot.press('enter', 'enter')
        await app.workers.wait_for_complete()
        await pilot.pause()
        return app.screen

    async def test_baseline_refresh_comparison_sort_filter_error_and_reset(self):
        reader = Reader()
        app = RamTaskManager(live=False, region_reader=reader)
        async with app.run_test(size=(80, 24)) as pilot:
            screen = await self.open_region(app, pilot)
            self.assertIsInstance(screen, RegionScreen)
            await pilot.press('b')
            self.assertIsNotNone(screen.baseline)
            self.assertEqual(screen.baseline.regions[1].rss, 128 << 20)
            await pilot.press('r')
            await app.workers.wait_for_complete()
            await pilot.press('c')
            await pilot.pause()
            self.assertTrue(screen.comparison_mode)
            self.assertEqual(screen.baseline.regions[1].rss, 128 << 20)
            self.assertEqual(screen.current_capture.regions[1].rss, 158 << 20)
            from ramtaskman.delta_bar import DeltaBar
            bar = screen.query_one('#delta-bar', DeltaBar)
            self.assertTrue(bar.display)
            self.assertEqual(bar.delta, 26 << 20)
            self.assertEqual(bar.scale, 164 << 20)
            table = screen.query_one('#region-table', DataTable)
            self.assertGreaterEqual(table.size.height, 4)
            self.assertEqual(table.row_count, 4)
            self.assertEqual(next(iter(screen.comparison_rows.values())).delta('rss'), 30 << 20)
            await pilot.press('s')
            await pilot.pause()
            self.assertEqual(next(iter(screen.comparison_rows.values())).delta('rss'), -(4 << 20))
            await pilot.press('v')
            self.assertEqual(screen.comparison_metric, 'pss')
            await pilot.press('slash', *'bcv')
            self.assertEqual(screen.query_one('#region-search', Input).value, 'bcv')
            self.assertTrue(screen.comparison_mode)
            await pilot.press('escape', 'f')
            screen.query_one('#comparison-state', Select).value = 'same_interval'
            await pilot.pause()
            self.assertEqual(table.row_count, 3)
            screen.query_one('#comparison-state', Select).value = 'backing_unverified'
            await pilot.pause()
            self.assertEqual(table.row_count, 1)
            await pilot.press('escape')
            reader.failure = True
            await pilot.press('r')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(table.row_count, 0)  # failed identity: no inferred disappearances
            self.assertEqual(screen.baseline.regions[1].rss, 128 << 20)
            self.assertIn('accesso negato', screen.snapshot.reason)
            self.assertIn('n/a', str(screen.query_one('#region-map-title', Static).content))
            await pilot.press('ctrl+b')
            await pilot.pause()
            self.assertFalse(screen.comparison_mode)
            self.assertIsNone(screen.baseline)
            self.assertEqual(table.row_count, 0)

    async def test_offline_never_refreshes_and_no_baseline_overwrite_on_failure(self):
        snap = fixture()
        proc = snap.processes[0]
        current = freeze_snapshot(region_fixture(proc), collection_session_id='synthetic', sequence=2)
        baseline = freeze_snapshot(region_fixture(proc), collection_session_id='synthetic', sequence=1)
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(snap)
            screen = RegionScreen(proc, 'linux', offline_capture=current, offline_baseline=baseline)
            app.push_screen(screen)
            await pilot.pause()
            self.assertTrue(screen.offline)
            self.assertTrue(screen.comparison_mode)
            await pilot.press('r', 'v')
            await pilot.pause()
            self.assertIs(screen.current_capture, current)
            self.assertIs(screen.baseline, baseline)
            self.assertEqual(screen.comparison_metric, 'pss')
            await pilot.press('c')
            await pilot.pause()
            self.assertEqual(screen.query_one('#region-table', DataTable).row_count, 4)

    async def test_distinct_process_sessions_are_app_wide(self):
        app = RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(160, 48)) as pilot:
            screen = await self.open_region(app, pilot)
            first = screen.current_capture
            await pilot.press('escape')
            await pilot.press('enter')
            await app.workers.wait_for_complete()
            await pilot.pause()
            second = app.screen.current_capture
            self.assertEqual(first.collection_session_id, second.collection_session_id)
            self.assertGreater(second.sequence, first.sequence)

    async def test_immutable_comparison_is_cached_until_snapshot_changes(self):
        import ramtaskman.region_screen as module
        reader = Reader()
        app = RamTaskManager(live=False, region_reader=reader)
        with patch.object(module, 'compare_captures', wraps=module.compare_captures) as compare:
            async with app.run_test(size=(80, 24)) as pilot:
                screen = await self.open_region(app, pilot)
                await pilot.press('b', 'r')
                await app.workers.wait_for_complete()
                await pilot.press('c')
                await pilot.pause()
                self.assertEqual(compare.call_count, 1)
                await pilot.press('s', 'v', 'slash')
                screen.query_one('#region-search', Input).value = 'heap'
                await pilot.pause()
                self.assertEqual(compare.call_count, 1)
                await pilot.press('escape', 'r')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertEqual(compare.call_count, 2)

    async def test_untrusted_table_content_is_literal_not_rich_markup(self):
        from textual.coordinate import Coordinate
        from rich.text import Text
        proc = fixture().processes[0]
        sample = region_fixture(proc)
        sample.regions[0].category = '[red]evil[/red]'
        sample.regions[0].permissions = '[bold]rw[/bold]'
        sample.regions[0].path = '[blink]file[/blink]'
        capture = freeze_snapshot(sample, collection_session_id='test', sequence=1)
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            screen = RegionScreen(proc, 'linux', offline_capture=capture)
            app.push_screen(screen)
            await pilot.pause()
            table = screen.query_one('#region-table', DataTable)
            row = list(screen.rows).index(sample.regions[0].key)
            for col, expected in ((1, '[red]evil[/red]'), (7, '[bold]rw[/bold]'), (8, '[blink]file[/blink]')):
                value = table.get_cell_at(Coordinate(row, col))
                self.assertIsInstance(value, Text)
                self.assertEqual(value.plain, expected)

    async def test_search_debounces_and_enter_applies_immediately(self):
        reader = Reader()
        app = RamTaskManager(live=False, region_reader=reader)
        async with app.run_test(size=(160, 48)) as pilot:
            screen = await self.open_region(app, pilot)
            await pilot.press('slash')
            search = screen.query_one('#region-search', Input)
            table = screen.query_one('#region-table', DataTable)
            with patch.object(screen, 'render_regions', wraps=screen.render_regions) as render, \
                    patch.object(screen, 'set_timer') as set_timer:
                search.value = 'h'
                await pilot.pause()
                search.value = 'he'
                await pilot.pause()
                search.value = 'heap'
                await pilot.pause()
                self.assertEqual(render.call_count, 0)
                self.assertEqual(set_timer.call_count, 3)
                set_timer.return_value.stop.assert_called()
                # Simulate the final timer firing; no wall-clock timing assumptions.
                set_timer.call_args.args[1]()
                self.assertEqual(render.call_count, 1)
                self.assertEqual(table.row_count, 1)
                search.value = 'browser'
                await pilot.pause()
                await pilot.press('enter')
                self.assertEqual(table.row_count, 1)
                self.assertEqual(next(iter(screen.rows.values())).category, 'executable')
                self.assertEqual(render.call_count, 2)

    async def test_search_pending_selection_and_escape_cannot_apply_stale_row(self):
        app = RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(160, 48)) as pilot:
            screen = await self.open_region(app, pilot)
            await pilot.press('slash')
            with patch.object(screen, 'set_timer') as set_timer:
                screen.query_one('#region-search', Input).value = 'heap'
                await pilot.pause()
                self.assertIsNotNone(screen._search_timer)
                # Activating a row while a filter is pending refreshes first, not stale zoom.
                table = screen.query_one('#region-table', DataTable)
                table.focus()
                await pilot.press('enter')
                self.assertIsNone(screen.zoom_key)
                self.assertEqual(next(iter(screen.rows.values())).category, 'heap')
                set_timer.return_value.stop.assert_called()
                await pilot.press('slash')
                screen.query_one('#region-search', Input).value = 'nothing'
                await pilot.pause()
                self.assertIsNotNone(screen._search_timer)
                await pilot.press('escape')
                await pilot.pause()
                self.assertEqual(table.row_count, 4)
                self.assertIsNone(screen._search_timer)

if __name__ == '__main__':
    unittest.main()
