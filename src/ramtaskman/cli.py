"""Cross-platform CLI: terminal UI, one-shot report or JSON."""
import argparse
import json
import math
import sys

from rich.console import Console

from . import __version__
from .collector import Collector
from .report import size, table, to_dict


def interval(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.25:
        raise argparse.ArgumentTypeError('intervallo minimo: 0.25 secondi, valore finito')
    return parsed


def positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('serve un numero intero positivo') from error
    if result < 1:
        raise argparse.ArgumentTypeError('serve un numero intero positivo')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='RAM task manager per Linux, Windows e macOS · Python + Textual')
    parser.add_argument('--version', action='version', version=__version__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--once', action='store_true', help='stampa una rilevazione e termina')
    output.add_argument('--json', action='store_true', help='stampa una rilevazione JSON e termina')
    output.add_argument('--open', metavar='FILE', help='apri una rilevazione salvata senza campionamento live')
    output.add_argument('--compare', nargs=2, metavar=('A', 'B'), help='confronta due file, ciascuno con una rilevazione')
    parser.add_argument('--interval', type=interval, default=2.0, help='pausa tra rilevazioni (default: 2 s)')
    parser.add_argument('--processes', action='store_true', help='apri la UI sui singoli processi')
    parser.add_argument('--max-measurements', type=positive_integer, default=None,
                        help='budget opzionale: numero massimo di processi misurati per ciclo')
    args = parser.parse_args()
    if (args.open or args.compare) and args.max_measurements is not None:
        parser.error('--max-measurements è utilizzabile solo nel monitoraggio live')
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
                        raise CaptureFormatError('--compare richiede un campione per file; usa --open per un confronto salvato')
                    baseline, current = first.current, second.current
            except (CaptureFormatError, OSError) as error:
                print(f'ramtaskman: acquisizione non valida: {error}', file=sys.stderr)
                return 1
            from .replay import ReplayApp
            ReplayApp(current, baseline).run()
            return 0
        collector = Collector(max_measurements=args.max_measurements)
        if args.once or args.json:
            snap = collector.sample()
            if args.json:
                print(json.dumps(to_dict(snap), ensure_ascii=False, indent=2))
            else:
                console = Console()
                console.print(f'RAM {size(snap.system.used)} / {size(snap.system.total)} · '
                              f'disponibile {size(snap.system.available)} · swap {size(snap.system.swap_used)}')
                console.print(table(snap))
                console.print(f'PSS leggibile: {snap.measured}/{len(snap.processes)} processi · '
                              f'identità non raccolte/terminati: {snap.skipped} · {snap.sample_ms:.0f} ms')
                if snap.measurement_attempted is not None:
                    console.print(f'Budget: {snap.measurement_attempted} misure tentate · '
                                  f'{snap.measurement_deferred} rinviate · '
                                  f'identità {"complete" if snap.enumeration_complete else "incomplete"}')
                console.print('Totali incompleti = n/a. RSS e Swap possono contare pagine condivise più volte.')
                if snap.unsupported:
                    console.print('Backend: RSS / USS disponibili; PSS e swap per processo non esposte da psutil.')
                for note in snap.system.notes:
                    console.print(note)
        else:
            from .app import RamTaskManager
            RamTaskManager(collector, args.interval, args.processes).run()
    except (RuntimeError, OSError, KeyError) as error:
        print(f'ramtaskman: {error}', file=sys.stderr)
        return 1
    return 0
