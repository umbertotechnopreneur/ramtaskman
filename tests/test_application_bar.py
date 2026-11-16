from dataclasses import replace
from types import SimpleNamespace
import unittest

from textual.widgets import DataTable, Static

from ramtaskman.application_bar import application_uss_bar, process_uss_bar
from ramtaskman.app import RamTaskManager
from ramtaskman.models import LinuxSystemMemory, ProcessMemory
from ramtaskman.region_map import RegionMap
from ramtaskman.region_screen import RegionScreen
from test_memory import fixture
from test_region_ui import region_fixture


class ApplicationBarTests(unittest.TestCase):
    def test_top_ten_and_other_complete_apps_preserve_denominator(self):
        snap = fixture()
        snap.processes = [ProcessMemory(i, 1, f'app{i}', 1000, f'/demo/app{i}', uss=i * 1024)
                          for i in range(1, 14)]
        bar = application_uss_bar(snap)
        self.assertTrue(bar.valid)
        self.assertEqual(len(bar.parts), 11)
        self.assertEqual(bar.parts[0].value, 13 * 1024)
        self.assertEqual(bar.parts[-1].value, 6 * 1024)
        self.assertEqual(bar.total, sum(i * 1024 for i in range(1, 14)))
        self.assertEqual(len({p.color for p in bar.parts}), 11)
        for width in (20, 74, 154, 314):
            self.assertEqual(bar.render(width).cell_len, width)

    def test_partial_groups_are_excluded_entirely(self):
        snap = fixture()
        snap.processes[1].uss = None
        bar = application_uss_bar(snap)
        self.assertEqual(bar.total, 400 << 20)
        self.assertEqual(len(bar.parts), 1)
        self.assertIn('1/3 app', bar.note)
        snap.enumeration_complete = False
        self.assertIsNone(application_uss_bar(snap).total)

    def test_zero_differs_from_unknown_and_names_are_literal(self):
        snap = fixture()
        snap.processes = [ProcessMemory(1, 1, '[bold]demo', 1000, None, uss=0)]
        bar = application_uss_bar(snap)
        self.assertTrue(bar.valid)
        self.assertEqual(bar.total, 0)
        self.assertIn('[bold]demo', bar.legend().plain)
        snap.processes[0].uss = None
        self.assertIsNone(application_uss_bar(snap).total)

    def test_process_bar_uses_current_identity_and_ram_scale(self):
        snap = fixture()
        process = replace(snap.processes[0])
        bar = process_uss_bar(snap, process)
        self.assertEqual(bar.total, snap.system.total)
        self.assertEqual(bar.parts[0].value, process.uss)
        snap.processes[0].started_at += 1
        self.assertIsNone(process_uss_bar(snap, process).total)


class ApplicationBarUITests(unittest.IsolatedAsyncioTestCase):
    async def test_linux_details_and_region_context_at_both_sizes(self):
        class Reader:
            capabilities = SimpleNamespace(platform='linux')
            def read(self, process, cancelled=None):
                return region_fixture(process)
        app = RamTaskManager(live=False, slim=False)
        async with app.run_test(size=(160, 48)) as pilot:
            snap = fixture()
            snap.system.linux_details = LinuxSystemMemory(commit_total=5 << 30, commit_limit=20 << 30)
            app.apply(snap)
            await pilot.pause()
            def texts():
                return '\n'.join(row.plain for row in app.query_one('#device', Static).content.renderables
                                 if hasattr(row, 'plain'))
            self.assertIn('Commit Linux 5.00 GiB / limite 20.00 GiB', texts())
            snap.system.linux_details = LinuxSystemMemory()
            app.apply(snap)
            await pilot.pause()
            self.assertIn('Commit Linux n/a / limite n/a', texts())
            self.assertIn('Contatori meminfo non disponibili: Committed_AS, CommitLimit', texts())
            screen = RegionScreen(snap.processes[0], 'linux', Reader())
            app.push_screen(screen)
            await pilot.pause()
            self.assertEqual(screen.mode, 'resident')
            def process_bar():
                return next(r for r in screen.query_one('#region-memory', Static).content.renderables
                            if getattr(r, 'metric', None) == 'USS PID / RAM')
            self.assertEqual(process_bar().parts[0].value, 400 << 20)
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertGreaterEqual(screen.query_one('#region-table', DataTable).size.height, 4)
            app.show_error('errore di prova')
            await pilot.pause()
            self.assertIn('non disponibile', str(screen.query_one('#region-memory', Static).content))

    async def test_dashboard_resize_filter_and_error(self):
        app = RamTaskManager(live=False, slim=False)
        async with app.run_test(size=(160, 48)) as pilot:
            app.apply(fixture())
            await pilot.pause()
            def bars():
                return [r for r in app.query_one('#device', Static).content.renderables
                        if getattr(r, 'metric', None) == 'USS app']
            self.assertEqual(bars()[0].total, 900 << 20)
            await pilot.press('slash')
            await pilot.press(*'editor')
            await pilot.pause()
            self.assertEqual(bars()[0].total, 900 << 20)
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
            app.show_error('test')
            await pilot.pause()
            self.assertIn('non disponibile', str(app.query_one('#device', Static).content))

    async def test_windows_regions_show_virtual_addresses_and_live_memory(self):
        class Reader:
            capabilities = SimpleNamespace(platform='windows')
            def read(self, process, cancelled=None):
                snap = region_fixture(process)
                snap.platform = 'windows'
                for row in snap.regions:
                    row.rss = row.pss = row.uss = None
                return snap
        app = RamTaskManager(live=False)
        async with app.run_test(size=(160, 48)) as pilot:
            snap = fixture()
            snap.platform = 'windows'
            snap.system.segments = {}
            app.apply(snap)
            screen = RegionScreen(snap.processes[0], 'windows', Reader())
            app.push_screen(screen)
            await pilot.pause()
            self.assertEqual(screen.mode, 'virtual')
            self.assertEqual(screen.SORTS[screen.sort_index], 'start')
            self.assertIn('0x400000', str(screen.query_one('#region-map-title', Static).content))
            self.assertNotIn('n/a', screen.query_one('#region-map', RegionMap).render().plain)
            def process_bars():
                return [r for r in screen.query_one('#region-memory', Static).content.renderables
                        if getattr(r, 'metric', None) == 'USS PID / RAM']
            self.assertEqual(process_bars()[0].parts[0].value, 400 << 20)
            snap.processes[0].uss = 300 << 20
            screen.render_memory_context()
            self.assertEqual(process_bars()[0].parts[0].value, 300 << 20)
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertGreaterEqual(screen.query_one('#region-table', DataTable).size.height, 4)
            app.snap = None
            screen.render_memory_context()
            self.assertIn('non disponibile', str(screen.query_one('#region-memory', Static).content))
