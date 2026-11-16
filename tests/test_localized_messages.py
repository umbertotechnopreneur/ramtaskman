"""Regression coverage for localized diagnostics and their storage boundaries."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from ramtaskman.capture_io import CaptureFormatError, load_capture, save_capture
from ramtaskman.capture_models import CaptureSnapshot
from ramtaskman.i18n import LANGUAGES, translate
from ramtaskman.messages import LocalizedMessage, error_text, localize, message
from ramtaskman.models import ProcessMemory, Snapshot, SystemMemory
from ramtaskman.report import to_dict


class LocalizedMessageTests(unittest.TestCase):
    def test_nested_diagnostics_are_translated_in_all_ten_languages(self):
        denied = {
            'it': 'accesso negato', 'en': 'access denied', 'zh': '访问被拒绝',
            'ko': '접근 거부', 'fr': 'accès refusé', 'vi': 'truy cập bị từ chối',
            'es': 'acceso denegado', 'pt': 'acesso negado',
            'de': 'Zugriff verweigert', 'ja': 'アクセス拒否',
        }
        self.assertEqual(set(LANGUAGES), set(denied))
        reason = message('tech_deferred_backoff', reason=message('tech_denied'))
        diagnostic = message('region_read_failed', type='OSError', reason=reason)

        self.assertIsInstance(diagnostic, str)
        self.assertEqual(str(diagnostic), localize(diagnostic, 'it'))
        for language in LANGUAGES:
            with self.subTest(language=language):
                expected_reason = translate(language, 'tech_deferred_backoff', reason=denied[language])
                self.assertEqual(localize(diagnostic, language), translate(
                    language, 'region_read_failed', type='OSError', reason=expected_reason))

    def test_raw_text_and_interpolated_data_are_never_translated(self):
        raw = 'OS detail: /demo/[red]tool[/red]/{reason} · accesso negato'
        diagnostic = message('tech_unsupported_system', platform=raw)
        # Even a literal copy of a known Italian diagnostic is external text.
        captured = str(message('tech_rollup_denied'))
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(localize(raw, language), raw)
                self.assertEqual(localize(captured, language), captured)
                self.assertIn(raw, localize(diagnostic, language))

    def test_error_text_preserves_only_single_structured_argument(self):
        diagnostic = message('tech_rollup_denied')
        self.assertIs(error_text(RuntimeError(diagnostic)), diagnostic)
        for error in (OSError('synthetic OS detail'), RuntimeError(),
                      RuntimeError(diagnostic, 'extra detail')):
            with self.subTest(arguments=error.args):
                self.assertEqual(error_text(error), str(error))
                self.assertNotIsInstance(error_text(error), LocalizedMessage)

    def test_deepcopy_and_asdict_preserve_nested_diagnostics_without_changing_json(self):
        diagnostic = message('tech_deferred_backoff', reason=message('tech_denied'))
        system = SystemMemory(4096, 2048, 1024, None, None, 0, 0, notes=[diagnostic])
        process = ProcessMemory(100, 1.0, 'synthetic-tool', 1000, '/demo/tool',
                                rss=0, pss=None, uss=0, reason=diagnostic)
        snapshot = Snapshot(1700000000.0, system, [process], unsupported={'pss': diagnostic})

        cloned = deepcopy(diagnostic)
        data = asdict(snapshot)
        for preserved in (cloned, data['processes'][0]['reason'], data['system']['notes'][0],
                          data['unsupported']['pss']):
            self.assertIsInstance(preserved, LocalizedMessage)
            self.assertEqual(preserved.key, diagnostic.key)
            self.assertIsInstance(preserved.values['reason'], LocalizedMessage)
            self.assertEqual(localize(preserved, 'fr'), localize(diagnostic, 'fr'))
        self.assertIsNot(cloned, diagnostic)
        self.assertIsNot(cloned.values['reason'], diagnostic.values['reason'])
        with self.assertRaises(TypeError):
            cloned.values['reason'] = 'replacement'

        serialized = json.loads(json.dumps(to_dict(snapshot), ensure_ascii=False))
        self.assertEqual(serialized['processes'][0]['reason'], str(diagnostic))
        self.assertEqual(serialized['system']['notes'], [str(diagnostic)])
        self.assertEqual(serialized['unsupported']['pss'], str(diagnostic))
        self.assertIsNone(serialized['processes'][0]['pss'])
        self.assertEqual(serialized['processes'][0]['uss'], 0)


class LocalizedCaptureDiagnosticTests(unittest.TestCase):
    def load_failure(self, contents):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.rtm.json'
            path.write_text(contents, encoding='utf-8')
            with self.assertRaises(CaptureFormatError) as raised:
                load_capture(path)
        diagnostic = error_text(raised.exception)
        self.assertIsInstance(diagnostic, LocalizedMessage)
        return diagnostic

    def test_duplicate_json_key_keeps_key_placeholder_literal_in_all_languages(self):
        key = 'synthetic[{reason}] /demo/key'
        contents = '{' + json.dumps(key) + ': 1, ' + json.dumps(key) + ': 2}'
        diagnostic = self.load_failure(contents)
        self.assertEqual(diagnostic.key, 'capture_duplicate_json_key')
        self.assertEqual(diagnostic.values['key'], key)
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(localize(diagnostic, language),
                                 translate(language, 'capture_duplicate_json_key', key=key))

    def test_nested_capture_labels_translate_while_schema_field_names_stay_literal(self):
        document = {
            'format': 'ramtaskman.capture', 'schema_version': 1, 'producer_version': 'synthetic',
            'current_capture_id': 'synthetic', 'baseline_capture_id': None, 'captures': [{}],
        }
        diagnostic = self.load_failure(json.dumps(document))
        self.assertEqual(diagnostic.key, 'capture_missing_fields')
        self.assertIsInstance(diagnostic.values['name'], LocalizedMessage)
        self.assertEqual(diagnostic.values['name'].key, 'capture_label_capture')
        fields = diagnostic.values['fields']
        self.assertIn('capture_id', fields)
        self.assertIn('metric_definitions', fields)
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(localize(diagnostic, language), translate(
                    language, 'capture_missing_fields',
                    name=translate(language, 'capture_label_capture'), fields=fields))

    def test_json_parse_error_detail_and_nonfinite_value_keep_their_original_text(self):
        malformed = self.load_failure('{')
        self.assertEqual(malformed.key, 'capture_invalid_json')
        detail = malformed.values['reason']
        self.assertIsInstance(detail, str)
        self.assertNotIsInstance(detail, LocalizedMessage)
        nonfinite = self.load_failure('{"synthetic": NaN}')
        self.assertEqual(nonfinite.key, 'capture_non_finite')
        self.assertEqual(nonfinite.values['value'], 'NaN')
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertIn(detail, localize(malformed, language))
                self.assertEqual(localize(nonfinite, language),
                                 translate(language, 'capture_non_finite', value='NaN'))

    def test_saved_capture_diagnostic_remains_captured_text_after_reload(self):
        diagnostic = message('tech_deferred_backoff', reason=message('tech_denied'))
        capture = CaptureSnapshot(
            pid=100, started_at=1.0, name='synthetic-tool', taken=1700000000.0,
            regions=(), sample_ms=2.0, reason=diagnostic, complete=False,
            capture_id='synthetic', collection_session_id='synthetic-session', sequence=1,
            platform='linux', backend_id='synthetic-provider', issues=(diagnostic,),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.rtm.json'
            save_capture(path, capture)
            loaded = load_capture(path).current
        self.assertIs(type(loaded.reason), str)
        self.assertEqual(loaded.issues, (str(diagnostic),))
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(localize(loaded.reason, language), str(diagnostic))
                self.assertEqual(localize(loaded.issues[0], language), str(diagnostic))
