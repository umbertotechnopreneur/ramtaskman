import time
import unittest
from textual.widgets import DataTable, Input, Static
from ramtaskman.app import RamTaskManager
from ramtaskman.region_screen import RegionScreen
from ramtaskman.region_map import RegionMap, region_cells
from ramtaskman.regions import MemoryRegion, RegionSnapshot
from ramtaskman.report import size
from test_memory import fixture

class Reader:
    def read(self, process, cancelled=None):
        regions=[MemoryRegion(i*4096, (i+1)*4096, path=f'[anon:{i}]', rss=i+1, pss=i+1, uss=i+1, swap=0)
                 for i in range(610)]
        return RegionSnapshot(process.pid, process.started_at, process.name, time.time(), regions,
                              executable_identity=process.executable)

class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_navigation_refresh_filters_and_map_click_keep_full_map(self):
        app=RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(160,48)) as pilot:
            app.apply(fixture())
            await pilot.press('enter','enter')
            await app.workers.wait_for_complete()
            await pilot.pause()
            screen=app.screen
            self.assertIsInstance(screen, RegionScreen)
            table=screen.query_one('#region-table', DataTable)
            self.assertEqual(table.row_count,250)
            self.assertEqual(len(screen.rows),610)
            self.assertEqual(len(screen.query_one('#region-map',RegionMap).regions),610)
            total=sum(r.rss for r in screen.rows.values())
            self.assertIn(size(total), str(screen.query_one('#region-map-title',Static).content))
            await pilot.press('ctrl+right')
            await pilot.pause()
            self.assertEqual(screen.page,1)
            self.assertEqual(table.row_count,250)
            selected=screen.selected
            await pilot.press('r')
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(screen.page,1)
            self.assertEqual(screen.selected,selected)
            self.assertEqual(len(screen.query_one('#region-map',RegionMap).regions),610)
            await pilot.press('ctrl+right')
            await pilot.pause()
            self.assertEqual(screen.page,2)
            self.assertEqual(table.row_count,110)
            await pilot.press('ctrl+u')
            await pilot.pause()
            self.assertEqual(screen.page,1)
            await pilot.press('ctrl+d')
            await pilot.pause()
            self.assertEqual(screen.page,2)
            await pilot.resize_terminal(80,24)
            await pilot.pause()
            self.assertEqual(screen.page,2)
            self.assertGreaterEqual(table.size.height,4)
            await pilot.resize_terminal(160,48)
            await pilot.pause()
            strip=screen.query_one('#region-map',RegionMap)
            cells=region_cells(list(screen.rows.values()), 'resident', strip.content_size.width)
            target=next(key for key in cells if key is not None and key not in screen.page_keys)
            await pilot.click('#region-map',offset=(cells.index(target),0))
            await pilot.pause()
            self.assertEqual(screen.selected,target)
            self.assertIn(target,screen.page_keys)
            await pilot.press('slash')
            screen.query_one('#region-search',Input).value='anon:3]'
            await pilot.press('enter')
            await pilot.pause()
            self.assertEqual(screen.page,0)
            self.assertEqual(table.row_count,1)
            self.assertEqual(len(screen.rows),1)

    async def test_comparison_pages_preserve_overall_delta(self):
        app=RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(80,24)) as pilot:
            app.apply(fixture())
            await pilot.press('enter','enter')
            await app.workers.wait_for_complete()
            await pilot.press('b','r')
            await app.workers.wait_for_complete()
            await pilot.press('c')
            await pilot.pause()
            screen=app.screen
            title=str(screen.query_one('#region-map-title',Static).content)
            self.assertEqual(len(screen.comparison_rows),610)
            await pilot.press('ctrl+right')
            await pilot.pause()
            self.assertEqual(screen.page,1)
            self.assertEqual(screen.query_one('#region-table',DataTable).row_count,250)
            self.assertEqual(str(screen.query_one('#region-map-title',Static).content),title)
            self.assertEqual(len(screen.comparison_rows),610)

if __name__=='__main__': unittest.main()
