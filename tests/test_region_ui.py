import asyncio
from dataclasses import replace
import threading
import time
import unittest

from textual.widgets import DataTable, Input, Select, Static

from ramtaskman.app import RamTaskManager
from ramtaskman.region_map import RegionMap, region_cells
from ramtaskman.region_screen import RegionScreen, filter_regions
from ramtaskman.regions import MemoryRegion, RegionSnapshot
from test_memory import fixture


def region_fixture(process=None):
    process = process or fixture().processes[0]
    rows = [
        MemoryRegion(0x400000, 0x800000, 'r-xp', path='/demo/browser', category='executable',
                     rss=2<<20, pss=1<<20, uss=0, swap=0, swap_pss=0,
                     breakdown={'private_clean': 0, 'private_dirty': 0, 'shared_clean': 2<<20, 'shared_dirty': 0}),
        MemoryRegion(0x10000000, 0x20000000, 'rw-p', path='[heap]', category='heap',
                     rss=128<<20, pss=128<<20, uss=128<<20, swap=32<<20, swap_pss=32<<20,
                     breakdown={'private_clean': 0, 'private_dirty': 128<<20, 'shared_clean': 0, 'shared_dirty': 0}),
        MemoryRegion(0x7000000000, 0x7010000000, 'r--p', path='/demo/large file.bin', category='file',
                     rss=8<<20, pss=4<<20, uss=0, swap=0, swap_pss=0,
                     breakdown={'private_clean': 0, 'private_dirty': 0, 'shared_clean': 8<<20, 'shared_dirty': 0}),
        MemoryRegion(0x8000000000, 0x8040000000, 'rw-p', category='anonymous',
                     rss=0, pss=0, uss=0, swap=0, swap_pss=0,
                     breakdown={'private_clean': 0, 'private_dirty': 0, 'shared_clean': 0, 'shared_dirty': 0}),
    ]
    return RegionSnapshot(process.pid, process.started_at, process.name, time.time(), rows,
                          sample_ms=12, executable_identity=process.executable)


class FakeReader:
    def __init__(self):
        self.calls = 0

    def read(self, process, cancelled=None):
        self.calls += 1
        return region_fixture(process)


class RegionMapTests(unittest.TestCase):
    def test_rss_and_virtual_use_distinct_scales_and_explicit_holes(self):
        rows = region_fixture().regions
        resident = region_cells(rows, 'resident', 100)
        virtual = region_cells(rows, 'virtual', 100)
        self.assertEqual(len(resident), 100)
        self.assertGreater(resident.count(rows[1].key), 90)
        self.assertNotIn(rows[3].key, resident)  # measured zero does not consume RAM
        self.assertGreater(virtual.count(rows[3].key), 60)
        self.assertIn(None, virtual)  # compressed holes have explicit separators
        self.assertEqual(region_cells(rows, 'resident', 0), [])

    def test_missing_rss_is_not_silently_omitted(self):
        rows = region_fixture().regions
        rows[0].rss = None
        self.assertEqual(region_cells(rows, 'resident', 80), [])
        self.assertEqual(len(region_cells(rows, 'virtual', 80)), 80)

    def test_filter_address_inside_region_and_shared_vs_mapping_permissions(self):
        rows = region_fixture().regions
        self.assertEqual(filter_regions(rows, '0x10001000', 'all', 'all'), [rows[1]])
        self.assertEqual(filter_regions(rows, 'LARGE FILE', 'file', 'resident'), [rows[2]])
        self.assertEqual(filter_regions(rows, '', 'all', 'swap'), [rows[1]])
        self.assertEqual(filter_regions(rows, '', 'all', 'shared'), [rows[0], rows[2]])
        rows[2].breakdown['shared_dirty'] = None
        self.assertEqual(filter_regions(rows, '', 'file', 'shared'), [])


class RegionUITests(unittest.IsolatedAsyncioTestCase):
    async def open_regions(self, app, pilot):
        app.apply(fixture())
        await pilot.pause()
        await pilot.press('enter', 'enter')
        await app.workers.wait_for_complete()
        await pilot.pause()
        self.assertIsInstance(app.screen, RegionScreen)
        return app.screen

    async def test_drilldown_modes_search_filters_zoom_and_return(self):
        reader = FakeReader()
        app = RamTaskManager(live=False, region_reader=reader)
        async with app.run_test(size=(160, 48)) as pilot:
            screen = await self.open_regions(app, pilot)
            table = screen.query_one('#region-table', DataTable)
            self.assertEqual(table.row_count, 4)
            self.assertEqual(reader.calls, 1)
            selected = screen.selected
            await pilot.press('v', 's', 'z')
            await pilot.pause()
            self.assertEqual(screen.mode, 'virtual')
            self.assertEqual(screen.selected, selected)
            self.assertEqual(screen.zoom_key, selected)
            # Main snapshots continue and don't replace the fixed region sample.
            app.apply(fixture())
            self.assertIs(app.screen, screen)
            await pilot.press('escape', 'slash')
            screen.query_one('#region-search', Input).value = '0x10001000'
            await pilot.press('enter')
            await pilot.pause()
            self.assertEqual(table.row_count, 1)
            self.assertEqual(screen.rows[screen.selected].category, 'heap')
            await pilot.press('escape', 'f')
            screen.query_one('#region-kind', Select).value = 'file'
            screen.query_one('#region-state', Select).value = 'swap'
            await pilot.pause()
            self.assertEqual(table.row_count, 0)
            self.assertIsNone(screen.selected)
            await pilot.press('escape', 'r')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(reader.calls, 2)
            self.assertEqual(table.row_count, 4)
            table.move_cursor(row=2, animate=False)
            await pilot.pause()
            selected = screen.selected
            await pilot.press('z', 'r')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(screen.selected, selected)
            self.assertEqual(screen.zoom_key, selected)
            await pilot.press('escape')  # Leave zoom before returning to the PID list.
            await pilot.press('escape')
            await pilot.pause()
            self.assertNotIsInstance(app.screen, RegionScreen)
            self.assertTrue(app.process_view)

    async def test_narrow_layout_input_shortcuts_map_click_and_resize(self):
        app = RamTaskManager(live=False, region_reader=FakeReader())
        async with app.run_test(size=(80, 24)) as pilot:
            screen = await self.open_regions(app, pilot)
            table = screen.query_one('#region-table', DataTable)
            self.assertGreaterEqual(table.size.height, 4)
            await pilot.press('tab')
            self.assertEqual(app.focused.id, 'region-inspector')
            await pilot.press('end')
            await pilot.pause()
            self.assertGreater(screen.query_one('#region-inspector').scroll_y, 0)
            await pilot.press('slash', *'qrvfsz')
            await pilot.pause()
            self.assertIs(app.screen, screen)
            self.assertEqual(screen.mode, 'resident')
            self.assertEqual(screen.sort_index, 0)
            self.assertEqual(screen.query_one('#region-search', Input).value, 'qrvfsz')
            await pilot.press('escape')
            await pilot.resize_terminal(160, 48)
            await pilot.pause()
            strip = screen.query_one('#region-map', RegionMap)
            cells = region_cells(list(screen.rows.values()), 'resident', strip.content_size.width)
            key = next(k for k in cells if k != screen.selected)
            await pilot.click('#region-map', offset=(cells.index(key), 0))
            await pilot.pause()
            self.assertEqual(screen.selected, key)

    async def test_failure_clears_old_data_ignores_stale_result_and_identity_mismatch(self):
        app = RamTaskManager(live=False, region_reader=FakeReader())
        async with app.run_test(size=(80, 24)) as pilot:
            screen = await self.open_regions(app, pilot)
            old_request = screen.request_id
            failed = RegionSnapshot(100, 10, 'browser', time.time(), reason='accesso negato', complete=False)
            screen.accept_snapshot(old_request, failed)
            await pilot.pause()
            self.assertEqual(screen.query_one('#region-table', DataTable).row_count, 0)
            screen.accept_snapshot(old_request-1, region_fixture())
            self.assertEqual(screen.rows, {})
            screen.accept_snapshot(old_request, replace(region_fixture(), started_at=999))
            self.assertEqual(screen.rows, {})
            self.assertIn('Identità', screen.snapshot.reason)
            screen.accept_snapshot(old_request, replace(region_fixture(), complete=False, reason='Limite'))
            await pilot.pause()
            self.assertEqual(len(screen.rows), 4)
            self.assertIn('incompleta', str(screen.query_one('#region-count', Static).content))

    async def test_closing_cancels_only_region_worker_and_keeps_app_worker(self):
        started, stopped = threading.Event(), threading.Event()
        class SlowReader:
            def read(self, process, cancelled=None):
                started.set()
                while not cancelled():
                    stopped.wait(.01)
                stopped.set()
                return region_fixture(process)
        app = RamTaskManager(live=False, region_reader=SlowReader())
        async with app.run_test(size=(80, 24)) as pilot:
            keep_running = app.run_worker(asyncio.sleep(30), group='main-test')
            app.apply(fixture())
            await pilot.press('enter', 'enter')
            await pilot.pause()
            self.assertTrue(started.is_set())
            await pilot.press('escape')
            await pilot.pause()
            self.assertFalse(keep_running.is_cancelled)
            self.assertTrue(stopped.is_set())
            self.assertNotIsInstance(app.screen, RegionScreen)
            keep_running.cancel()

    async def test_unsupported_platform_does_not_read_linux(self):
        reader = FakeReader()
        app = RamTaskManager(live=False, region_reader=reader)
        async with app.run_test(size=(80, 24)) as pilot:
            snap = fixture()
            snap.platform = 'macos'
            app.apply(snap)
            await pilot.press('enter', 'r')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIsInstance(app.screen, RegionScreen)
            self.assertIn('macos', app.screen.snapshot.reason)
            self.assertEqual(reader.calls, 0)


if __name__ == '__main__':
    unittest.main()
