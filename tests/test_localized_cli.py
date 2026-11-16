"""Exercise CLI language selection without inspecting live processes."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from rich.console import Console

from ramtaskman import cli
from ramtaskman.i18n import LANGUAGES, translate
from ramtaskman.messages import message
from ramtaskman.models import ProcessMemory, Snapshot, SystemMemory


def synthetic_snapshot():
    system = SystemMemory(16 << 20, 12 << 20, 8 << 20, None, None, 0, 0,
                          notes=[message('tech_global_swap_unavailable'),
                                 'Synthetic OS detail: /demo/[red]raw[/red]/{reason}'])
    rows = [
        ProcessMemory(100, 1.0, 'synthetic [red]tool[/red] {reason}', 1000, None,
                      rss=1024, pss=None, uss=0, reason=message('tech_rollup_denied')),
        ProcessMemory(101, 2.0, 'synthetic-helper', 1000, '/demo/synthetic-helper',
                      rss=0, pss=0, uss=0, swap=0, swap_pss=0),
    ]
    return Snapshot(1700000000.0, system, rows, sample_ms=12.0, skipped=1,
                    platform='macos', source='synthetic-provider',
                    unsupported={'pss': message('tech_pss_unsupported')},
                    measurement_attempted=2, measurement_deferred=1)


class LocalizedCLITests(unittest.TestCase):
    def invoke(self, arguments, *, snapshot=None, collector_error=None):
        """Run only the command dispatcher; any unexpected live sampling fails."""
        stdout, stderr = StringIO(), StringIO()
        if snapshot is None and collector_error is None:
            collector = Mock(side_effect=AssertionError('unexpected live collection'))
        else:
            collector = Mock()
            collector.return_value.sample.return_value = snapshot
            collector.return_value.sample.side_effect = collector_error
        with patch.object(sys, 'argv', ['ramtaskman', *arguments]), \
             patch.object(cli, 'Collector', collector), \
             patch.object(cli, 'Console', side_effect=lambda: Console(
                 file=stdout, width=320, force_terminal=False, color_system=None)), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = cli.main()
            except SystemExit as error:
                code = error.code
        return code, stdout.getvalue(), stderr.getvalue(), collector

    def test_help_honors_language_even_after_help_in_all_ten_languages(self):
        self.assertEqual(len(LANGUAGES), 10)
        for language in LANGUAGES:
            for arguments in (['--help', '--language', language],
                              ['--language=' + language, '-h']):
                with self.subTest(language=language, arguments=arguments):
                    code, stdout, stderr, collector = self.invoke(arguments)
                    self.assertEqual(code, 0)
                    self.assertEqual(stderr, '')
                    self.assertTrue(stdout.startswith(translate(language, 'cli_usage') + ':'))
                    self.assertIn(translate(language, 'cli_options') + ':', stdout)
                    unwrapped = ' '.join(stdout.split())
                    for key in ('cli_description', 'cli_help_once', 'cli_help_language'):
                        self.assertIn(' '.join(translate(language, key).split()), unwrapped)
                    collector.assert_not_called()

    def test_invalid_intervals_are_localized_before_collection(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                code, stdout, stderr, collector = self.invoke(
                    ['--interval=0', '--language', language, '--once'])
                self.assertEqual(code, 2)
                self.assertEqual(stdout, '')
                reason = translate(language, 'cli_argument_error', argument='--interval',
                                   message=translate(language, 'cli_invalid_interval'))
                self.assertIn(reason, stderr)
                self.assertTrue(stderr.startswith(translate(language, 'cli_usage') + ':'))
                collector.assert_not_called()

    def test_invalid_measurement_budgets_are_localized_before_collection(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                code, _, stderr, collector = self.invoke(
                    ['--max-measurements=0', '--language', language])
                self.assertEqual(code, 2)
                self.assertIn(translate(language, 'cli_positive_integer'), stderr)
                collector.assert_not_called()

    def test_nonfinite_malformed_and_boundary_numbers(self):
        cases = (
            ('--interval', ('0.249', '-1', 'nan', 'inf', '-inf', 'synthetic-invalid'), 'cli_invalid_interval'),
            ('--max-measurements', ('-1', '1.5', 'nan', 'synthetic-invalid'), 'cli_positive_integer'),
        )
        for option, values, key in cases:
            for value in values:
                with self.subTest(option=option, value=value):
                    code, _, stderr, collector = self.invoke(
                        [option + '=' + value, '--language', 'en'])
                    self.assertEqual(code, 2)
                    self.assertIn(translate('en', key), stderr)
                    collector.assert_not_called()
        code, _, stderr, collector = self.invoke(
            ['--once', '--interval=0.25', '--max-measurements=1', '--language=en'],
            snapshot=synthetic_snapshot())
        self.assertEqual(code, 0)
        self.assertEqual(stderr, '')
        collector.assert_called_once_with(max_measurements=1, selected_priority=False,
                                          measurement_backoff=False)

    def test_invalid_choice_uses_selected_language_but_keeps_choice_identifiers(self):
        choices = ', '.join(repr(language) for language in LANGUAGES)
        for language in LANGUAGES:
            with self.subTest(language=language):
                code, _, stderr, collector = self.invoke(
                    ['--language', 'synthetic-invalid', '--language', language])
                self.assertEqual(code, 2)
                self.assertIn(translate(language, 'cli_invalid_choice',
                                        value=repr('synthetic-invalid'), choices=choices), stderr)
                collector.assert_not_called()
        code, _, stderr, _ = self.invoke(['--language', 'synthetic-invalid'])
        self.assertEqual(code, 2)
        self.assertIn(translate('it', 'cli_invalid_choice',
                                value=repr('synthetic-invalid'), choices=choices), stderr)

    def test_parser_generated_errors_are_localized(self):
        cases = (
            (['--interval'], 'cli_expected_one', {}),
            (['--compare', 'synthetic-a'], 'cli_expected_count', {'count': '2'}),
            (['--once', '--json'], 'cli_not_allowed', {'argument': '--once'}),
            (['--once=synthetic'], 'cli_ignored_value', {'value': repr('synthetic')}),
            (['--synthetic-unknown'], 'cli_unrecognized', {'arguments': '--synthetic-unknown'}),
            (['--lang=fr'], 'cli_unrecognized', {'arguments': '--lang=fr'}),
        )
        for language in LANGUAGES:
            for arguments, key, values in cases:
                with self.subTest(language=language, arguments=arguments):
                    # Keep the incomplete --compare last so this case isolates
                    # its missing capture-file value from language selection.
                    arguments_with_language = (['--language', language, *arguments]
                        if arguments[0] == '--compare' else [*arguments, '--language', language])
                    code, _, stderr, collector = self.invoke(arguments_with_language)
                    self.assertEqual(code, 2)
                    self.assertIn(translate(language, key, **values), stderr)
                    self.assertTrue(stderr.startswith(translate(language, 'cli_usage') + ':'))
                    collector.assert_not_called()

    def test_policy_errors_are_localized_before_collection(self):
        cases = (
            (['--selected-priority'], 'cli_policy_requires_budget'),
            (['--measurement-backoff'], 'cli_policy_requires_budget'),
            (['--once', '--selected-priority', '--max-measurements', '1'], 'cli_priority_requires_live'),
            (['--open', 'synthetic.rtm.json', '--max-measurements', '1'], 'cli_budget_requires_live'),
        )
        for language in LANGUAGES:
            for arguments, key in cases:
                with self.subTest(language=language, arguments=arguments):
                    code, _, stderr, collector = self.invoke([*arguments, '--language', language])
                    self.assertEqual(code, 2)
                    self.assertIn(translate(language, key), stderr)
                    collector.assert_not_called()

    def test_once_report_translates_labels_and_diagnostics_but_preserves_data(self):
        snapshot = synthetic_snapshot()
        for language in LANGUAGES:
            with self.subTest(language=language):
                code, stdout, stderr, collector = self.invoke(
                    ['--once', '--language', language], snapshot=snapshot)
                self.assertEqual(code, 0)
                self.assertEqual(stderr, '')
                for key in ('report_application', 'report_group', 'cli_sample_warning',
                            'cli_sample_backend', 'tech_global_swap_unavailable', 'group_name',
                            'group_executable'):
                    self.assertIn(translate(language, key), stdout)
                self.assertIn(translate(language, 'budget_status', attempted=2, deferred=1,
                                        identity=translate(language, 'identity_complete')), stdout)
                self.assertIn(translate(language, 'cli_sample_coverage', measured=1, total=2,
                                        skipped=1, duration='12'), stdout)
                self.assertIn(snapshot.processes[0].name, stdout)
                self.assertIn(snapshot.system.notes[1], stdout)
                self.assertIn('n/a', stdout)
                self.assertIn('0 B', stdout)
                collector.return_value.sample.assert_called_once_with()

    def test_json_is_identical_across_languages_and_retains_nulls_and_identifiers(self):
        snapshot = synthetic_snapshot()
        baseline = None
        for language in LANGUAGES:
            with self.subTest(language=language):
                code, stdout, stderr, collector = self.invoke(
                    ['--json', '--language', language], snapshot=snapshot)
                self.assertEqual(code, 0)
                self.assertEqual(stderr, '')
                if baseline is None:
                    baseline = stdout
                self.assertEqual(stdout, baseline)
                document = json.loads(stdout)
                self.assertEqual(document['schema_version'], 1)
                self.assertEqual(document['source'], 'synthetic-provider')
                self.assertEqual(document['processes'][0]['name'], snapshot.processes[0].name)
                self.assertEqual(document['processes'][0]['reason'], str(message('tech_rollup_denied')))
                self.assertIsNone(document['processes'][0]['pss'])
                self.assertEqual(document['processes'][1]['pss'], 0)
                self.assertIsNone(document['applications'][0]['pss'])
                self.assertEqual(document['system']['used'], 4 << 20)
                self.assertEqual(document['coverage']['pss'], 1)
                collector.return_value.sample.assert_called_once_with()

    def test_collector_errors_translate_structured_messages_and_preserve_os_details(self):
        detail = 'synthetic-platform/[red]literal[/red]/{reason}'
        for language in LANGUAGES:
            with self.subTest(language=language):
                diagnostic = message('tech_unsupported_system', platform=detail)
                code, stdout, stderr, _ = self.invoke(
                    ['--once', '--language', language], collector_error=RuntimeError(diagnostic))
                self.assertEqual(code, 1)
                self.assertEqual(stdout, '')
                self.assertEqual(stderr, 'ramtaskman: ' + translate(
                    language, 'tech_unsupported_system', platform=detail) + '\n')
                code, _, stderr, _ = self.invoke(
                    ['--once', '--language', language], collector_error=OSError(detail))
                self.assertEqual(code, 1)
                self.assertEqual(stderr, 'ramtaskman: ' + detail + '\n')

    def test_invalid_capture_is_localized_without_constructing_live_collector(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.rtm.json'
            key = 'synthetic[{reason}]'
            path.write_text('{"' + key + '": 1, "' + key + '": 2}', encoding='utf-8')
            for language in LANGUAGES:
                with self.subTest(language=language):
                    code, stdout, stderr, collector = self.invoke(
                        ['--open', str(path), '--language', language])
                    reason = translate(language, 'capture_duplicate_json_key', key=key)
                    self.assertEqual(code, 1)
                    self.assertEqual(stdout, '')
                    self.assertEqual(stderr, 'ramtaskman: ' + translate(
                        language, 'cli_invalid_capture', reason=reason) + '\n')
                    collector.assert_not_called()
