import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.app import App
from textual.widgets import Input, Static

from ramtaskman.capture_dialog import CaptureOpenScreen, CaptureSaveScreen
from ramtaskman.capture_io import load_capture, save_capture
from ramtaskman.replay import ReplayApp
from test_capture_io import fixture


class DialogApp(App):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.result = None

    def on_mount(self):
        self.push_screen(self.dialog, callback=self.record)

    def record(self, result):
        self.result = result


class CaptureDialogTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_then_confirm_overwrite_and_open(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'esempio.rtm.json'
            path.write_text('original')
            app = DialogApp(CaptureSaveScreen(fixture()))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                app.screen.query_one('#capture-path', Input).value = str(path)
                await pilot.press('enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertEqual(path.read_text(), 'original')
                self.assertTrue(app.screen.query_one('#capture-overwrite').display)
                app.screen.query_one('#capture-overwrite').press()
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertTrue(app.result)
                self.assertEqual(load_capture(path).current.pid, 100)
            app = DialogApp(CaptureOpenScreen())
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                app.screen.query_one('#capture-open-path', Input).value = str(path)
                await pilot.press('enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertEqual(app.result.current.pid, 100)

    async def test_open_invalid_file_retains_dialog(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'broken.rtm.json'
            path.write_text('non json')
            app = DialogApp(CaptureOpenScreen())
            async with app.run_test(size=(80, 24)) as pilot:
                app.screen.query_one('#capture-open-path', Input).value = str(path)
                await pilot.press('enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIsInstance(app.screen, CaptureOpenScreen)
                self.assertIn('JSON', str(app.screen.query_one('#capture-open-error', Static).content))

    async def test_replay_has_no_provider_even_after_refresh(self):
        from ramtaskman.region_screen import RegionScreen
        a, b = fixture(1, 'a'), fixture(2, 'b')
        with patch('ramtaskman.region_screen.make_region_provider', side_effect=AssertionError('live')):
            app = ReplayApp(b, a)
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                self.assertIsInstance(app.screen, RegionScreen)
                self.assertTrue(app.screen.offline)
                self.assertIsNone(app.screen.provider)
                await pilot.press('r')
                await pilot.pause()
                self.assertIs(app.screen.current_capture, b)
                await pilot.press('q')
                await pilot.pause()

    async def test_region_shortcuts_save_then_open_offline(self):
        from ramtaskman.app import RamTaskManager
        from ramtaskman.region_screen import RegionScreen
        from test_memory import fixture as main_fixture
        from test_region_ui import FakeReader

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'misura.rtm.json'
            app = RamTaskManager(live=False, region_reader=FakeReader())
            async with app.run_test(size=(160, 48)) as pilot:
                app.apply(main_fixture())
                await pilot.press('enter', 'enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertIsInstance(app.screen, RegionScreen)
                await pilot.press('ctrl+s')
                await pilot.pause()
                self.assertIsInstance(app.screen, CaptureSaveScreen)
                app.screen.query_one('#capture-path', Input).value = str(path)
                await pilot.press('enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertTrue(path.exists())
                self.assertIsInstance(app.screen, RegionScreen)
                await pilot.press('ctrl+o')
                await pilot.pause()
                self.assertIsInstance(app.screen, CaptureOpenScreen)
                app.screen.query_one('#capture-open-path', Input).value = str(path)
                await pilot.press('enter')
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertTrue(app.screen.offline)
                self.assertEqual(app.screen.current_capture.pid, 100)


if __name__ == '__main__':
    unittest.main()
