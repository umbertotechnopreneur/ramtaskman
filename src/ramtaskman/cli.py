"""Cross-platform CLI: terminal UI, one-shot report or JSON."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence

from rich.console import Console
from rich.text import Text

from . import __version__
from .collector import Collector
from .i18n import LANGUAGES, translate
from .messages import error_text, localize
from .models import Snapshot
from .valuation import RamPrice, price_report, value_text
from .report import size, table, to_dict


class LocalizedHelpFormatter(argparse.HelpFormatter):
    """Translate argparse's own headings without changing global gettext state."""

    def __init__(self, prog: str, *, language: str) -> None:
        super().__init__(prog)
        self.language = language

    def add_usage(self, usage, actions, groups, prefix=None) -> None:
        if prefix is None:
            prefix = translate(self.language, 'cli_usage') + ': '
        super().add_usage(usage, actions, groups, prefix)

    def start_section(self, heading) -> None:
        headings = {'positional arguments': 'cli_positionals', 'options': 'cli_options',
                    'optional arguments': 'cli_options'}
        if heading in headings:
            heading = translate(self.language, headings[heading])
        super().start_section(heading)


class LocalizedArgumentParser(argparse.ArgumentParser):
    """Localize the parser-generated errors used by this command's options."""

    def __init__(self, *, language: str, **kwargs) -> None:
        self.language = language
        super().__init__(formatter_class=lambda prog: LocalizedHelpFormatter(prog, language=language),
                         add_help=False, allow_abbrev=False, **kwargs)

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _check_value(self, action, value) -> None:
        # Preserve choice values as data; only the surrounding sentence changes.
        if action.choices is not None and value not in action.choices:
            choices = ', '.join(repr(choice) for choice in action.choices)
            raise argparse.ArgumentError(action, self.tr('cli_invalid_choice', value=repr(value), choices=choices))

    def _error_message(self, message: str) -> str:
        argument = re.fullmatch(r'argument (.+?): (.*)', message, re.DOTALL)
        if argument:
            return self.tr('cli_argument_error', argument=argument[1], message=self._error_message(argument[2]))

        exact = {'expected one argument': 'cli_expected_one',
                 'expected at least one argument': 'cli_expected_at_least_one'}
        if message in exact:
            return self.tr(exact[message])

        patterns = (
            (r'expected (\d+) arguments', 'cli_expected_count', 'count'),
            (r'unrecognized arguments: (.*)', 'cli_unrecognized', 'arguments'),
            (r'not allowed with argument (.*)', 'cli_not_allowed', 'argument'),
            (r'ignored explicit argument (.*)', 'cli_ignored_value', 'value'),
            (r'the following arguments are required: (.*)', 'cli_required', 'arguments'),
            (r'one of the arguments (.*) is required', 'cli_one_required', 'arguments'),
        )
        for pattern, key, field in patterns:
            match = re.fullmatch(pattern, message, re.DOTALL)
            if match:
                return self.tr(key, **{field: match[1]})
        # Already localized validation messages and unknown upstream diagnostics
        # are preserved literally rather than guessed or translated as user data.
        return message

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, self.tr('cli_error', prog=self.prog, message=self._error_message(message)) + '\n')


def interval(value: str, language: str = 'it') -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(translate(language, 'cli_invalid_interval')) from error
    if not math.isfinite(parsed) or parsed < 0.25:
        raise argparse.ArgumentTypeError(translate(language, 'cli_invalid_interval'))
    return parsed


def positive_integer(value: str, language: str = 'it') -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(translate(language, 'cli_positive_integer')) from error
    if result < 1:
        raise argparse.ArgumentTypeError(translate(language, 'cli_positive_integer'))
    return result


def _language_from_arguments(arguments: Sequence[str]) -> str:
    """Read language before processing help, regardless of option ordering."""
    selector = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    selector.add_argument('--language', default='it')
    try:
        selected, _ = selector.parse_known_args(arguments)
    except argparse.ArgumentError:
        # The main parser reports an incomplete --language option normally.
        return 'it'
    return selected.language if selected.language in LANGUAGES else 'it'


def _parser(language: str) -> LocalizedArgumentParser:
    parser = LocalizedArgumentParser(language=language, description=translate(language, 'cli_description'))
    tr = parser.tr
    parser.add_argument('-h', '--help', action='help', help=tr('cli_help_help'))
    parser.add_argument('--version', action='version', version=__version__, help=tr('cli_help_version'))
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--once', action='store_true', help=tr('cli_help_once'))
    output.add_argument('--json', action='store_true', help=tr('cli_help_json'))
    output.add_argument('--open', metavar='FILE', help=tr('cli_help_open'))
    output.add_argument('--compare', nargs=2, metavar=('A', 'B'), help=tr('cli_help_compare'))
    parser.add_argument('--interval', type=lambda value: interval(value, language), default=2.0,
                        help=tr('cli_help_interval'))
    parser.add_argument('--processes', action='store_true', help=tr('cli_help_processes'))
    parser.add_argument('--language', choices=LANGUAGES, default=language, metavar='LANG', help=tr('cli_help_language'))
    parser.add_argument('--max-measurements', type=lambda value: positive_integer(value, language), default=None,
                        help=tr('cli_help_budget'))
    parser.add_argument('--selected-priority', action='store_true', help=tr('cli_help_priority'))
    parser.add_argument('--measurement-backoff', action='store_true', help=tr('cli_help_backoff'))
    parser.add_argument('--ram-price', type=float, help='Total price of installed RAM (not a live quote)')
    parser.add_argument('--ram-currency', default='EUR', help='Three-letter uppercase currency code')
    parser.add_argument('--ram-months', type=int, help='Optional months over which to allocate hardware value')
    parser.add_argument('--ram-capacity-gib', type=float, help='Optional nominal installed capacity; defaults to OS-visible RAM')
    return parser


def _print_sample(snap: Snapshot, language: str) -> None:
    """Render human output literally; machine JSON is kept in its stable schema."""
    def tr(key: str, **values: object) -> str:
        return translate(language, key, **values)

    console = Console()
    memory = snap.system
    console.print(Text(tr('cli_sample_memory', used=size(memory.used), total=size(memory.total),
                          available=size(memory.available), swap=size(memory.swap_used))))
    console.print(table(snap, language))
    console.print(Text(tr('cli_sample_coverage', measured=snap.measured, total=len(snap.processes),
                          skipped=snap.skipped, duration=f'{snap.sample_ms:.0f}')))
    if snap.measurement_attempted is not None:
        identity = tr('identity_complete' if snap.enumeration_complete else 'identity_incomplete')
        console.print(Text(tr('budget_status', attempted=snap.measurement_attempted,
                              deferred=snap.measurement_deferred, identity=identity)))
    console.print(Text(tr('cli_sample_warning')))
    if snap.unsupported:
        console.print(Text(tr('cli_sample_backend')))
    for note in memory.notes:
        console.print(Text(localize(note, language)))


def main() -> int:
    arguments = sys.argv[1:]
    language = _language_from_arguments(arguments)
    parser = _parser(language)
    args = parser.parse_args(arguments)
    tr = parser.tr
    price = None
    if args.ram_price is not None:
        try:
            price = RamPrice(args.ram_price, args.ram_currency, args.ram_months, args.ram_capacity_gib)
        except ValueError as error:
            parser.error(str(error))
    elif args.ram_months is not None or args.ram_capacity_gib is not None or args.ram_currency != 'EUR':
        parser.error('--ram-price is required for RAM valuation options')
    if price and (args.open or args.compare):
        parser.error('RAM valuation requires a live system sample, not a region capture')
    if (args.selected_priority or args.measurement_backoff) and args.max_measurements is None:
        parser.error(tr('cli_policy_requires_budget'))
    if args.selected_priority and (args.once or args.json or args.open or args.compare):
        parser.error(tr('cli_priority_requires_live'))
    if (args.open or args.compare) and args.max_measurements is not None:
        parser.error(tr('cli_budget_requires_live'))
    try:
        if args.open or args.compare:
            from .capture_io import CaptureFormatError, load_capture
            try:
                if args.open:
                    saved = load_capture(args.open)
                    current, baseline = saved.current, saved.baseline
                else:
                    first, second = (load_capture(path) for path in args.compare)
                    if first.baseline is not None or second.baseline is not None:
                        raise CaptureFormatError(tr('cli_compare_single'))
                    baseline, current = first.current, second.current
            except (CaptureFormatError, OSError) as error:
                reason = localize(error_text(error), language)
                print('ramtaskman: ' + tr('cli_invalid_capture', reason=reason), file=sys.stderr)
                return 1
            from .replay import ReplayApp
            ReplayApp(current, baseline, language=language).run()
            return 0
        collector = Collector(max_measurements=args.max_measurements,
                              selected_priority=args.selected_priority,
                              measurement_backoff=args.measurement_backoff)
        if args.once or args.json:
            snap = collector.sample()
            if args.json:
                data = to_dict(snap)
                if price:
                    data['ram_valuation'] = price_report(snap, price)
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                _print_sample(snap, language)
                if price:
                    console = Console()
                    console.print(Text(tr('ram_value_note')))
                    for row in snap.applications:
                        console.print(Text(row.name + ': ' + value_text(row, snap, price)))
        else:
            from .app import RamTaskManager
            RamTaskManager(collector, args.interval, args.processes, language=language, ram_price=price).run()
    except (RuntimeError, OSError, KeyError) as error:
        print('ramtaskman: ' + localize(error_text(error), language), file=sys.stderr)
        return 1
    return 0
