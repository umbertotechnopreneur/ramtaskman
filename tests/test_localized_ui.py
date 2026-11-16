"""Exercise locale boundaries with synthetic data and real Textual footers."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from textual.widgets import Button, DataTable, Footer, Input, Markdown, Static

from ramtaskman.app import HelpScreen, MemoryDetailScreen, RamTaskManager
from ramtaskman.capture_dialog import CaptureOpenScreen, CaptureSaveScreen
from ramtaskman.capture_io import CaptureFormatError
from ramtaskman.i18n import LANGUAGES, load_help, translate
from ramtaskman.messages import message
from ramtaskman.region_screen import RegionScreen
from ramtaskman.replay import ReplayApp
from test_capture_io import fixture as capture_fixture
from test_memory import fixture as memory_fixture
from test_region_ui import FakeReader


SIZES = ((160, 48), (80, 24))
DASHBOARD_BINDINGS = {
    'quit': 'footer_quit', 'cycle_sort': 'footer_sort',
    'cycle_chart': 'footer_chart', 'toggle_all': 'footer_all_top',
    'toggle_group': 'footer_apps_pids', 'toggle_monitoring': 'footer_slim_full',
    'pause': 'footer_pause', 'help': 'footer_help', 'search': 'footer_search',
    'filters': 'footer_filter', 'detail': 'footer_detail', 'regions': 'footer_regions',
    'command_palette': 'footer_palette',
}
REGION_BINDINGS = {
    'back': 'footer_back', 'close': 'footer_close',
    'refresh_regions': 'footer_refresh', 'mode': 'footer_mode',
    'sort': 'footer_sort', 'zoom': 'footer_zoom', 'search': 'footer_search',
    'filters': 'footer_filter', 'baseline': 'footer_baseline',
    'clear_baseline': 'footer_clear_baseline', 'compare': 'footer_compare',
    'save_capture': 'save', 'open_capture': 'open',
    'previous_page': 'footer_previous_page', 'next_page': 'footer_next_page',
}


def binding_state(node):
    """Keep immutable evidence of Textual's original action metadata."""
    return tuple(
        (key, tuple((binding.action, binding.description, binding.tooltip,
                     binding.show, binding.priority) for binding in bindings))
        for key, bindings in node._bindings.key_to_bindings.items()
    )


def plain_content(widget):
    """Read literal Text paragraphs without terminal wrapping or markup parsing."""
    content = widget.content
    if hasattr(content, 'renderables'):
        return '\n'.join(item.plain for item in content.renderables if hasattr(item, 'plain'))
    return content.plain if hasattr(content, 'plain') else str(content)


class LocalizedUITests(unittest.IsolatedAsyncioTestCase):
    def assert_binding(self, screen, action, key, language):
        before = binding_state(screen)
        bindings = [active.binding for active in screen.active_bindings.values()
                    if active.binding.action.rsplit('.', 1)[-1] == action]
        self.assertTrue(bindings, action)
        for binding in bindings:
            self.assertEqual(binding.description, translate(language, key))
        self.assertEqual(binding_state(screen), before)

    def assert_footer(self, screen, expected, language, size):
        footer = screen.query_one(Footer)
        self.assertEqual(footer.size.height, 1)
        self.assertEqual(footer.region.y, size[1] - 1)
        self.assertEqual(footer.size.width, size[0])
        keys = {item.action.rsplit('.', 1)[-1]: item for item in footer.query('FooterKey')}
        for action, key in expected.items():
            self.assertIn(action, keys)
            item = keys[action]
            self.assertEqual(item.description, translate(language, key))
            self.assertIn(translate(language, key), item.render().plain)
            self.assert_binding(screen, action, key, language)

    async def test_dashboard_footer_diagnostics_and_modals_in_ten_languages(self):
        originals = []
        for language in LANGUAGES:
            with self.subTest(language=language):
                snapshot = memory_fixture()
                snapshot.system.segments = {}
                snapshot.system.segments_reason = message('tech_partition_missing', fields='MemFree')
                snapshot.system.notes = [message('tech_global_swap_unavailable')]
                snapshot.processes[0].reason = message(
                    'tech_reasons_join', first=message('tech_rss_denied'),
                    second=message('tech_uss_denied'))
                app = RamTaskManager(live=False, processes=True, language=language)
                originals.append((app, binding_state(app)))
                async with app.run_test(size=SIZES[0]) as pilot:
                    app.apply(snapshot)
                    await pilot.pause()
                    for size in SIZES:
                        await pilot.resize_terminal(*size)
                        await pilot.pause()
                        self.assert_footer(app.screen, DASHBOARD_BINDINGS, language, size)
                        self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
                        self.assertIn(translate(language, 'tech_partition_missing', fields='MemFree'),
                                      plain_content(app.query_one('#device', Static)))
                        self.assertIn(translate(language, 'tech_global_swap_unavailable'),
                                      plain_content(app.query_one('#system', Static)))
                        reason = translate(language, 'tech_reasons_join',
                                           first=translate(language, 'tech_rss_denied'),
                                           second=translate(language, 'tech_uss_denied'))
                        self.assertIn(reason, plain_content(app.query_one('#inspector', Static)))

                    # Closing a modal must restore the owning dashboard's language.
                    await pilot.press('d')
                    await pilot.pause()
                    self.assertIsInstance(app.screen, MemoryDetailScreen)
                    self.assertIn(translate(language, 'detail_title'),
                                  plain_content(app.screen.query_one(Static)))
                    self.assert_binding(app.screen, 'pop_screen', 'footer_close', language)
                    await pilot.resize_terminal(*SIZES[0])
                    await pilot.pause()
                    self.assert_binding(app.screen, 'pop_screen', 'footer_close', language)
                    await pilot.press('escape', 'question_mark')
                    await pilot.pause()
                    self.assertIsInstance(app.screen, HelpScreen)
                    self.assertEqual(app.screen.query_one(Markdown)._markdown, load_help(language))
                    self.assert_binding(app.screen, 'pop_screen', 'footer_close', language)
                    await pilot.resize_terminal(*SIZES[1])
                    await pilot.pause()
                    self.assert_binding(app.screen, 'pop_screen', 'footer_close', language)
                    await pilot.press('escape')
                    await pilot.pause()
                    self.assert_footer(app.screen, DASHBOARD_BINDINGS, language, SIZES[1])

                    # A structured failure clears stale readings and translates nested text.
                    failure = message('error_with_type', type='OSError', reason=message('tech_page_size'))
                    app.show_error(failure)
                    await pilot.pause()
                    expected = translate(language, 'sample_error', reason=translate(
                        language, 'error_with_type', type='OSError',
                        reason=translate(language, 'tech_page_size')))
                    self.assertEqual(plain_content(app.query_one('#device', Static)), expected)
                    self.assertEqual(app.query_one('#procs', DataTable).row_count, 0)
                    app.apply(snapshot)
                    await pilot.pause()
                    self.assertEqual(app.query_one('#procs', DataTable).row_count, 4)

                # Later app instances must not rewrite earlier apps' binding maps.
                for earlier, original in originals:
                    self.assertEqual(binding_state(earlier), original)

    async def test_region_footer_and_worker_errors_in_ten_languages(self):
        class Reader(FakeReader):
            failure = None

            def read(self, process, cancelled=None):
                if self.failure is not None:
                    raise self.failure
                return super().read(process, cancelled)

        originals = []
        for language in LANGUAGES:
            with self.subTest(language=language):
                reader = Reader()
                app = RamTaskManager(live=False, processes=True,
                                     region_reader=reader, language=language)
                originals.append((app, binding_state(app)))
                async with app.run_test(size=SIZES[0]) as pilot:
                    app.apply(memory_fixture())
                    await pilot.pause()
                    await pilot.press('r')
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    screen = app.screen
                    self.assertIsInstance(screen, RegionScreen)
                    originals.append((screen, binding_state(screen)))
                    for size in SIZES:
                        await pilot.resize_terminal(*size)
                        await pilot.pause()
                        self.assert_footer(screen, REGION_BINDINGS, language, size)
                        self.assertEqual(screen.query_one('#region-search', Input).placeholder,
                                         translate(language, 'region_search'))
                        self.assertEqual(screen.query_one('#region-table', DataTable).row_count, 4)
                        self.assertGreaterEqual(screen.query_one('#region-table', DataTable).size.height, 4)

                    reader.failure = ValueError(message('tech_smaps_size_mismatch'))
                    await pilot.press('r')
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    expected = translate(language, 'region_read_failed', type='ValueError',
                                         reason=translate(language, 'tech_smaps_size_mismatch'))
                    self.assertIn(expected, plain_content(screen.query_one('#region-summary', Static)))
                    self.assertEqual(screen.query_one('#region-table', DataTable).row_count, 0)
                    self.assertFalse(screen.snapshot.complete)
                    self.assertEqual(str(screen.snapshot.reason), translate(
                        'it', 'region_read_failed', type='ValueError',
                        reason=translate('it', 'tech_smaps_size_mismatch')))
                for earlier, original in originals:
                    self.assertEqual(binding_state(earlier), original)

    async def test_replay_capture_dialogs_and_literal_os_errors_in_ten_languages(self):
        captured_reason = '[red]Captured detail /demo/測定.rtm.json'
        for language in LANGUAGES:
            with self.subTest(language=language):
                capture = replace(capture_fixture(), complete=False,
                                  reason=captured_reason, issues=(captured_reason,))
                app = ReplayApp(capture, language=language)
                # Offline tests fail immediately if any live provider is constructed.
                with patch('ramtaskman.region_screen.make_region_provider', side_effect=AssertionError('live provider')):
                    async with app.run_test(size=SIZES[0]) as pilot:
                        await pilot.pause()
                        self.assertEqual(app.title, translate(language, 'replay_title'))
                        screen = app.screen
                        for size in SIZES:
                            await pilot.resize_terminal(*size)
                            await pilot.pause()
                            self.assert_footer(screen, REGION_BINDINGS, language, size)
                            self.assertTrue(screen.offline)
                            self.assertIsNone(screen.provider)
                            self.assertIn(captured_reason,
                                          plain_content(screen.query_one('#region-summary', Static)))
                            await pilot.press('ctrl+s')
                            await pilot.pause()
                            self.assertIsInstance(app.screen, CaptureSaveScreen)
                            self.assert_binding(app.screen, 'cancel', 'cancel', language)
                            self.assertEqual(str(app.screen.query_one('#capture-save', Button).label),
                                             translate(language, 'save'))
                            self.assertEqual(app.screen.query_one('#capture-path', Input).placeholder,
                                             translate(language, 'capture_path'))
                            error = CaptureFormatError(message('capture_invalid_json', reason=message(
                                'capture_duplicate_json_key', key='capture_id')))
                            expected = translate(language, 'capture_invalid_json', reason=translate(
                                language, 'capture_duplicate_json_key', key='capture_id'))
                            app.screen.query_one('#capture-path', Input).value = 'synthetic.rtm.json'
                            with patch('ramtaskman.capture_dialog.save_capture', side_effect=error):
                                await pilot.press('enter')
                                await app.workers.wait_for_complete()
                                await pilot.pause()
                            self.assertEqual(plain_content(app.screen.query_one('#capture-error', Static)), expected)
                            await pilot.press('escape', 'ctrl+o')
                            await pilot.pause()
                            self.assertIsInstance(app.screen, CaptureOpenScreen)
                            self.assert_binding(app.screen, 'cancel', 'cancel', language)
                            self.assertEqual(str(app.screen.query_one('#capture-open', Button).label),
                                             translate(language, 'open'))
                            app.screen.query_one('#capture-open-path', Input).value = 'synthetic.rtm.json'
                            # OS diagnostics and captured text remain literal, including markup-like text.
                            os_reason = '[magenta]OS detail Ω /demo/測定.rtm.json'
                            open_error = error if size == SIZES[0] else OSError(os_reason)
                            with patch('ramtaskman.capture_dialog.load_capture', side_effect=open_error):
                                await pilot.press('enter')
                                await app.workers.wait_for_complete()
                                await pilot.pause()
                            self.assertEqual(plain_content(app.screen.query_one('#capture-open-error', Static)),
                                             expected if size == SIZES[0] else os_reason)
                            await pilot.press('escape')
                            await pilot.pause()
                            self.assertIs(app.screen, screen)
                            self.assert_footer(screen, REGION_BINDINGS, language, size)
