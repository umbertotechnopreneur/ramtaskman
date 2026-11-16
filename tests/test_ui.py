import unittest

from textual.widgets import DataTable, Select, Static

from ramtaskman.app import HelpScreen, RamTaskManager
from test_memory import fixture


class UITests(unittest.IsolatedAsyncioTestCase):
    async def test_views_drilldown_sort_and_selection_survive_refresh(self):
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            table = app.query_one('#procs', DataTable)
            self.assertEqual(table.row_count, 3)
            original = app.selected_key
            app.apply(fixture())
            await pilot.pause()
            self.assertEqual(app.selected_key, original)
            await pilot.press('enter')
            await pilot.pause()
            self.assertTrue(app.process_view)
            self.assertEqual(table.row_count, 2)
            await pilot.press('escape')
            await pilot.pause()
            self.assertFalse(app.process_view)
            self.assertEqual(table.row_count, 3)
            await pilot.press('g', 's')
            await pilot.pause()
            self.assertTrue(app.process_view)
            self.assertEqual(table.row_count, 4)
            self.assertEqual(app.sort_idx, 1)

    async def test_pause_charts_help_and_slim(self):
        app = RamTaskManager(live=False)
        self.assertTrue(app.monitoring)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            await pilot.press('p')
            count = len(app.histories['RAM'])
            app.apply(fixture())
            self.assertEqual(len(app.histories['RAM']), count)
            await pilot.press('p', 'c', 'm')
            await pilot.pause()
            self.assertFalse(app.paused)
            self.assertFalse(app.monitoring)
            self.assertEqual(app.query_one('#chart-mode', Select).value, 0)
            await pilot.press('question_mark')
            await pilot.pause()
            self.assertIsInstance(app.screen, HelpScreen)
            await pilot.press('escape')
            await pilot.pause()
            self.assertNotIsInstance(app.screen, HelpScreen)

    async def test_narrow_terminal_keeps_processes_and_footer(self):
        app = RamTaskManager(live=False)
        async with app.run_test(size=(80, 24)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            table = app.query_one('#procs', DataTable)
            self.assertGreaterEqual(table.size.height, 4)
            self.assertEqual(table.row_count, 3)
            await pilot.press('g')
            await pilot.pause()
            self.assertEqual(table.row_count, 4)

    async def test_failure_clears_stale_values_then_recovers(self):
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            app.show_error('procfs unavailable')
            await pilot.pause()
            self.assertIsNone(app.snap)
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 0)
            self.assertIsNone(app.histories['RAM'][-1])
            app.apply(fixture())
            await pilot.pause()
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 3)

    async def test_windows_snapshot_defaults_to_uss_without_pss_or_swap(self):
        from ramtaskman.backends.psutil_backend import PsutilBackend
        snap = fixture()
        snap.platform = 'windows'
        snap.system.segments = {}
        snap.source = 'Windows psutil (synthetic)'
        snap.unsupported = PsutilBackend('windows').unsupported
        snap.system.cache = snap.system.slab = snap.system.pressure_percent = None
        snap.system.swap_used = snap.system.swap_total = None
        for row in snap.processes:
            row.pss = row.swap = row.swap_pss = None
        app = RamTaskManager(live=False)
        async with app.run_test(size=(80, 24)) as pilot:
            app.apply(snap)
            await pilot.pause()
            self.assertEqual(app.SORTS[app.sort_idx], 'uss')
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 3)
            self.assertIsNone(app.histories['Swap'][-1])
            self.assertIsNone(app.histories['PSS visible'][-1])
            self.assertIsNotNone(app.histories['USS visible'][-1])

    async def test_search_by_helper_and_pid_preserves_entire_group(self):
        from textual.widgets import Input
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            await pilot.press('slash')
            await pilot.press(*'browser-worker')
            await pilot.pause()
            self.assertIsInstance(app.focused, Input)
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            self.assertEqual(next(iter(app.rows.values())).total('pss'), 800 << 20)
            await pilot.press('enter', 'enter')
            await pilot.pause()
            # The group remains whole, but the process view shows only the matching helper.
            self.assertTrue(app.process_view)
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            self.assertEqual(next(iter(app.rows.values())).pid, 101)
            await pilot.press('escape')
            await pilot.pause()
            self.assertFalse(app.process_view)
            self.assertEqual(app.row_filter.query, 'browser-worker')
            await pilot.press('slash')
            app.query_one('#search', Input).value = '100'
            await pilot.pause()
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            self.assertEqual(len(next(iter(app.rows.values())).processes), 2)
            await pilot.press('escape')
            await pilot.pause()
            self.assertFalse(app.row_filter.active)
            self.assertFalse(app.query_one('#filters').display)
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 3)

    async def test_filters_empty_result_reset_and_user_survives_refresh(self):
        from textual.widgets import Input
        app = RamTaskManager(live=False)
        async with app.run_test(size=(80, 24)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            await pilot.press('f')
            app.query_one('#user-filter', Select).value = 'uid:1000'
            app.query_one('#memory-filter', Select).value = 'swap'
            await pilot.pause()
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
            snap = fixture()
            snap.processes = [snap.processes[-1]]
            app.apply(snap)
            await pilot.pause()
            self.assertEqual(app.row_filter.owner, 'uid:1000')
            self.assertEqual(app.query_one('#user-filter', Select).value, 'uid:1000')
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 0)
            self.assertIsNone(app.selected_key)
            await pilot.press('slash')
            app.query_one('#search', Input).value = 'qsacgfpm?'
            await pilot.pause()
            self.assertTrue(app.is_running)
            self.assertFalse(app.paused)
            self.assertFalse(app.process_view)
            await pilot.press('escape')
            await pilot.pause()
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            self.assertFalse(app.row_filter.active)

    async def test_filter_before_top_limit_and_selection_stable_on_refresh(self):
        from ramtaskman.models import ProcessMemory
        from textual.widgets import Input
        snap = fixture()
        snap.processes += [ProcessMemory(1000+i, 100+i, f'worker-{i}', 1000, f'/demo/worker-{i}',
                                        rss=1, pss=1, uss=1, swap=0, swap_pss=0) for i in range(40)]
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(snap)
            await pilot.pause()
            await pilot.press('slash')
            app.query_one('#search', Input).value = 'worker-39'
            await pilot.pause()
            self.assertEqual(app.query_one('#procs', DataTable).row_count, 1)
            selected = app.selected_key
            app.apply(snap)
            await pilot.pause()
            self.assertEqual(app.selected_key, selected)
            self.assertEqual(next(iter(app.rows.values())).name, 'worker-39')

    async def test_detail_modal_has_group_totals_and_survives_background_refresh(self):
        from ramtaskman.app import MemoryDetailScreen
        snap = fixture()
        snap.processes[0].breakdown = {'pss_anon': 100, 'pss_file': 0}
        snap.processes[1].breakdown = {'pss_anon': 200}
        app = RamTaskManager(live=False)
        async with app.run_test(size=(80, 24)) as pilot:
            app.apply(snap)
            await pilot.pause()
            await pilot.press('d')
            await pilot.pause()
            self.assertIsInstance(app.screen, MemoryDetailScreen)
            self.assertGreater(app.screen.query_one(Static).size.height, 0)
            app.apply(fixture())
            await pilot.pause()
            self.assertIsInstance(app.screen, MemoryDetailScreen)
            await pilot.press('escape')
            await pilot.pause()
            self.assertNotIsInstance(app.screen, MemoryDetailScreen)
            await pilot.press('enter', 'd')
            await pilot.pause()
            self.assertIsInstance(app.screen, MemoryDetailScreen)
            await pilot.press('d')
            await pilot.pause()
            self.assertNotIsInstance(app.screen, MemoryDetailScreen)

    async def test_full_width_ram_bar_resizes_and_unknown_partition_has_reason(self):
        from ramtaskman.ram_bar import SystemRamBar
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            snap = fixture()
            app.apply(snap)
            await pilot.pause()
            content = app.query_one('#device', Static).content
            self.assertTrue(any(isinstance(row, SystemRamBar) and row.detailed for row in content.renderables))
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
            snap.system.segments = {}
            snap.system.segments_reason = 'campione non coerente'
            app.apply(snap)
            await pilot.pause()
            content = app.query_one('#device', Static).content
            texts = [row.plain for row in content.renderables if hasattr(row, 'plain')]
            self.assertTrue(any('campione non coerente' in text for text in texts))
