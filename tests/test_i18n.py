import string
import unittest

from textual.widgets import DataTable, Input, Static

from ramtaskman.app import RamTaskManager
from ramtaskman.i18n import CATALOG, LANGUAGES, translate
from test_memory import fixture


class TranslationTests(unittest.TestCase):
    def test_every_language_has_same_keys_and_format_fields(self):
        formatter = string.Formatter()
        def fields(value):
            return {name for _, name, _, _ in formatter.parse(value) if name is not None}
        base = CATALOG['it']
        self.assertEqual(set(CATALOG), set(LANGUAGES))
        for lang, catalog in CATALOG.items():
            self.assertEqual(catalog.keys(), base.keys(), lang)
            for key, text in catalog.items():
                self.assertTrue(text, (lang, key))
                self.assertEqual(fields(text), fields(base[key]), (lang, key))


class TranslationUITests(unittest.IsolatedAsyncioTestCase):
    async def test_localized_dashboard_and_filters_at_both_sizes(self):
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                app = RamTaskManager(live=False, language=lang)
                async with app.run_test(size=(160, 48)) as pilot:
                    app.apply(fixture())
                    await pilot.pause()
                    panel = app.query_one('#device', Static)
                    self.assertEqual(str(panel.border_title), translate(lang, 'slim'))
                    self.assertIn(translate(lang, 'system_ram'), panel.content.renderables[0].plain)
                    await pilot.resize_terminal(80, 24)
                    await pilot.pause()
                    self.assertGreaterEqual(app.query_one('#procs', DataTable).size.height, 4)
                    await pilot.press('slash')
                    await pilot.pause()
                    self.assertEqual(app.query_one('#search', Input).placeholder, translate(lang, 'search'))
                    await pilot.press('escape')
                    await pilot.pause()
