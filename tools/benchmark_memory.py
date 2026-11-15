"""Local synthetic model/UI benchmarks; writes no process names or capture files.

Example: uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000
Use --ui for an additional Textual DataTable mount/render measurement.
This is a measurement tool, not a timing assertion in the test suite.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import platform
import statistics
import sys
import time
import tracemalloc

import psutil

from ramtaskman.models import ProcessMemory, Snapshot, SystemMemory
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.comparison import compare_captures
from ramtaskman.region_map import region_cells
from ramtaskman.region_screen import filter_regions, RegionScreen
from ramtaskman.regions import MemoryRegion, RegionSnapshot


def make_regions(count: int) -> list[MemoryRegion]:
    return [MemoryRegion(i * 0x20000, i * 0x20000 + 0x10000, 'rw-p',
                         path=f'/synthetic/mapping-{i % 100}.bin', category='file',
                         rss=None if i % 20 == 0 else (i % 16) * 4096,
                         pss=None if i % 20 == 0 else (i % 12) * 4096,
                         uss=None if i % 20 == 0 else (i % 8) * 4096,
                         swap=(i % 4) * 4096,
                         breakdown={'shared_clean': 0, 'shared_dirty': 0})
            for i in range(count)]


def make_processes(count: int) -> list[ProcessMemory]:
    return [ProcessMemory(i + 1, i + 100., f'process-{i}', 1000,
                          f'/synthetic/executable-{i % 100}', rss=4096 * (i % 100),
                          pss=None if i % 20 == 0 else 4096 * (i % 75),
                          uss=4096 * (i % 50), swap=0)
            for i in range(count)]


def timed(label, operation, repeat):
    operation()  # warm up once
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, int((len(ordered) - 1) * .95 + .5))]
    print(f'  {label}: mediana {statistics.median(samples):.2f} ms; p95 {p95:.2f} ms; n={repeat}')


def measure_self_linux(repeat: int) -> None:
    """Measure only this benchmark process; never enumerate other processes.

    Includes psutil identity validation in the relevant phase. The numbers are
    not an end-to-end scan of the host and must not be multiplied by process
    counts as a prediction; state and permissions differ among processes.
    """
    if not sys.platform.startswith('linux'):
        print('  Misure reali sul proprio processo: non disponibili fuori da Linux.')
        return
    from ramtaskman.backends.linux import LinuxBackend
    from ramtaskman.regions import LinuxRegionReader

    backend = LinuxBackend()
    reader = LinuxRegionReader()
    own = psutil.Process()
    # Explicitly validate availability before reporting timings: a fast failed
    # read must not be confused with a successful benchmark result.
    identity = backend.read_identity(own)
    if identity is None:
        print('  Identità del processo di prova non disponibile.')
        return
    sample = backend.read_metrics(own, identity)
    if sample is None or sample.pss is None:
        print('  smaps_rollup del processo di prova non disponibile: misure reali non eseguite.')
        return
    regions = reader.read(identity)
    if not regions.complete:
        print(f'  smaps del processo di prova incompleto: {regions.reason}; misure reali non eseguite.')
        return
    print(f'Processo di prova corrente: {len(regions.regions)} regioni; nessun altro processo interrogato')
    before = own.memory_info().rss
    before_cpu = own.cpu_times()
    before_fds = own.num_fds() if hasattr(own, 'num_fds') else None

    def identity_read():
        if backend.read_identity(psutil.Process()) is None:
            raise RuntimeError('Identità del processo di prova non disponibile')

    def rollup_read():
        # read_metrics mutates the row: a fresh blank copy avoids accepting a
        # stale PSS if a later procfs read fails or loses permission.
        blank = replace(identity, rss=None, pss=None, uss=None, swap=None,
                        swap_pss=None, reason=None, breakdown={})
        result = backend.read_metrics(psutil.Process(), blank)
        if result is None or result.pss is None:
            raise RuntimeError('smaps_rollup del processo di prova non disponibile')

    def region_read():
        result = reader.read(identity)
        if not result.complete:
            raise RuntimeError(f'smaps del processo di prova incompleto: {result.reason}')

    timed('identità processo (inclusi metadati cgroup)', identity_read, repeat)
    timed('contatori processo smaps_rollup', rollup_read, repeat)
    timed('mappature processo smaps', region_read, repeat)
    after_cpu = own.cpu_times()
    after_fds = own.num_fds() if hasattr(own, 'num_fds') else None
    print(f'  RSS del benchmark: prima {before / (1 << 20):.2f} MiB; '
          f'dopo {own.memory_info().rss / (1 << 20):.2f} MiB')
    print(f'  CPU benchmark: {(after_cpu.user + after_cpu.system - before_cpu.user - before_cpu.system) * 1000:.2f} ms; '
          f'fd prima/dopo: {before_fds if before_fds is not None else "n/a"}/{after_fds if after_fds is not None else "n/a"}')


async def ui_measure(regions, repeat):
    from ramtaskman.app import RamTaskManager
    from ramtaskman.region_screen import RegionScreen
    from textual.widgets import Input

    proc = ProcessMemory(1, 1., 'synthetic', 1000, '/synthetic/demo')
    class Reader:
        def read(self, process, cancelled=None):
            return RegionSnapshot(process.pid, process.started_at, process.name, time.time(), regions,
                                  executable_identity=process.executable)
    samples = []
    search_samples = []
    search_counts = []
    render_samples = []
    comparison_start_samples = []
    comparison_done_samples = []
    for _ in range(repeat + 1):
        app = RamTaskManager(live=False, region_reader=Reader())
        async with app.run_test(size=(160, 48)) as pilot:
            start = time.perf_counter()
            app.push_screen(RegionScreen(proc, 'linux', Reader()))
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            samples.append((time.perf_counter() - start) * 1000)
            screen = app.screen
            redraws = [0]
            render_times = []
            original = screen.render_regions
            def counted():
                redraws[0] += 1
                start_render = time.perf_counter()
                try:
                    original()
                finally:
                    render_times.append((time.perf_counter() - start_render) * 1000)
            screen.render_regions = counted
            await pilot.press('slash')
            search = screen.query_one('#region-search', Input)
            start = time.perf_counter()
            for query in ('m', 'ma', 'map'):
                search.value = query
                await pilot.pause(.02)
            await pilot.pause(.2)
            search_samples.append((time.perf_counter() - start) * 1000)
            search_counts.append(redraws[0])
            render_samples.extend(render_times if len(samples) > 1 else [])
            await pilot.press('escape')
            screen.baseline = screen.current_capture
            start = time.perf_counter()
            screen.action_compare()
            comparison_start_samples.append((time.perf_counter() - start) * 1000)
            await app.workers.wait_for_complete()
            await pilot.pause()
            comparison_done_samples.append((time.perf_counter() - start) * 1000)
    samples = samples[1:]
    print(f'  UI mount+render incl. pilot: mediana {statistics.median(samples):.2f} ms; n={repeat}')
    print(f'  UI tre variazioni rapide: ridisegni {search_counts[1:]}; '
          f'mediana {statistics.median(search_samples[1:]):.2f} ms incl. pause; n={repeat}')
    if render_samples:
        print(f'  UI render_regions sincrono: mediana {statistics.median(render_samples):.2f} ms; '
              f'massimo {max(render_samples):.2f} ms; n={len(render_samples)}; escluso paint del terminale')
    print(f'  UI avvio confronto: mediana {statistics.median(comparison_start_samples[1:]):.2f} ms; '
          f'massimo {max(comparison_start_samples[1:]):.2f} ms; n={repeat}; escluso paint')
    print(f'  UI confronto completato: mediana {statistics.median(comparison_done_samples[1:]):.2f} ms; '
          f'n={repeat}; include worker, render e pause pilot')


def main():
    parser = argparse.ArgumentParser(description='Benchmark locale su dati sintetici.')
    parser.add_argument('--sizes', type=int, nargs='+', default=[100, 1000, 10000])
    parser.add_argument('--repeat', type=int, default=5)
    parser.add_argument('--ui', action='store_true')
    parser.add_argument('--self-linux', action='store_true',
                        help='misura identity, rollup e regioni solo del processo di benchmark su Linux')
    args = parser.parse_args()
    if args.repeat < 1 or any(n < 1 or n > 32768 for n in args.sizes):
        parser.error('Usare 1–32768 elementi e almeno una ripetizione.')
    print(f'Python {platform.python_version()} · {platform.system()} {platform.machine()} · dati sintetici')
    if args.self_linux:
        measure_self_linux(args.repeat)
    for count in args.sizes:
        print(f'{count} processi / {count} regioni')
        tracemalloc.start()
        regions, processes = make_regions(count), make_processes(count)
        system = SystemMemory(16 << 30, 8 << 30, 4 << 30, None, None, None, None)
        snapshot = Snapshot(time.time(), system, processes)
        print(f'  memoria Python fixture: {tracemalloc.get_traced_memory()[0] / (1 << 20):.2f} MiB')
        tracemalloc.stop()
        timed('raggruppamento', lambda: snapshot.applications, args.repeat)
        timed('ricerca regioni', lambda: filter_regions(regions, 'mapping-3', 'all', 'all'), args.repeat)
        timed('ordinamento RSS', lambda: sorted(regions, key=lambda r: (r.rss is None, -(r.rss or 0))), args.repeat)
        timed('mappa virtuale 160 colonne', lambda: region_cells(regions, 'virtual', 160), args.repeat)
        raw = RegionSnapshot(1, 1., 'synthetic', time.time(), regions, executable_identity='/synthetic/demo')
        baseline = freeze_snapshot(raw, collection_session_id='synthetic', sequence=1, executable_identity='/synthetic/demo')
        current = freeze_snapshot(raw, collection_session_id='synthetic', sequence=2, executable_identity='/synthetic/demo')
        proc = ProcessMemory(1, 1., 'synthetic', 1000, '/synthetic/demo')
        screen = RegionScreen(proc, 'linux', offline_capture=current, offline_baseline=baseline)
        timed('confronto A/B ricalcolato', lambda: compare_captures(baseline, current), args.repeat)
        screen._comparison_inputs = (baseline, current)
        screen._comparison_result = compare_captures(baseline, current)
        timed('confronto A/B riusato', screen.comparison_for_current, args.repeat)
        if args.ui:
            asyncio.run(ui_measure(regions, args.repeat))


if __name__ == '__main__':
    main()
