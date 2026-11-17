"""Exercise bundled resources and synthetic Textual views without live collection."""
import time
from unittest.mock import patch

from textual.widgets import DataTable
from ramtaskman.app import RamTaskManager, AboutScreen
from ramtaskman.i18n import LANGUAGES, load_help
from ramtaskman.models import ProcessMemory, Snapshot, SystemMemory
from ramtaskman.valuation import RamPrice
from ramtaskman.regions import MemoryRegion, RegionSnapshot
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.replay import ReplayApp


async def verify():
    sample = Snapshot(time.time(), SystemMemory(8 << 30, 4 << 30, 2 << 30, None, None, 0, 0),
                      [ProcessMemory(42, 1.0, 'demo', 1000, '/demo/app',
                                     rss=128 << 20, pss=96 << 20, uss=64 << 20)])
    with patch('ramtaskman.cli.Collector', side_effect=AssertionError('live collection')):
        for language in LANGUAGES:
            assert load_help(language)
            app = RamTaskManager(live=False, language=language, ram_price=RamPrice(320))
            async with app.run_test(size=(160, 48)) as pilot:
                app.apply(sample)
                await pilot.pause()
                assert app.query_one('#procs', DataTable).row_count == 1
                await pilot.press('f1')
                await pilot.pause()
                assert isinstance(app.screen, AboutScreen)
                await pilot.press('escape', 'question_mark')
                await pilot.pause()
                await pilot.press('escape')
                await pilot.resize_terminal(80, 24)
                await pilot.pause()
                assert app.query_one('#procs', DataTable).size.height >= 4
        region = RegionSnapshot(42, 1.0, 'demo', time.time(),
                                [MemoryRegion(0x1000, 0x2000, rss=0, pss=None)])
        capture = freeze_snapshot(region, collection_session_id='bundle-test', sequence=1,
                                  executable_identity='/demo/app')
        with patch('ramtaskman.region_screen.make_region_provider', side_effect=AssertionError('live provider')):
            app = ReplayApp(capture)
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                assert app.screen.offline
                await pilot.press('r', 'q')
                await pilot.pause()
    print('Bundle verified: 10 languages, help, About, 160x48/80x24 and offline replay.')
