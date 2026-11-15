"""Local synthetic model/UI benchmarks; writes no process names or capture files.

Example: uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000
Use --ui for an additional Textual DataTable mount/render measurement.
This is a measurement tool, not a timing assertion in the test suite.
"""
from __future__ import annotations

import argparse
import asyncio
import platform
import statistics
import time
import tracemalloc

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


async def ui_measure(regions, repeat):
    from ramtaskman.app import RamTaskManager
    from ramtaskman.region_screen import RegionScreen
    from textual.widgets import Input

    proc = ProcessMemory(1, 1., 'synthetic', 1000, '/synthetic/demo')
    class Reader:
        def read(self, process, cancelled=None):
            return RegionSnapshot(process.pid, process.started_at, process.name, time.time(), regions)
    samples = []
    search_samples = []
    search_counts = []
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
            original = screen.render_regions
            def counted():
                redraws[0] += 1
                original()
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
    samples = samples[1:]
    print(f'  UI mount+render incl. pilot: mediana {statistics.median(samples):.2f} ms; n={repeat}')
    print(f'  UI tre variazioni rapide: ridisegni {search_counts[1:]}; '
          f'mediana {statistics.median(search_samples[1:]):.2f} ms incl. pause; n={repeat}')


def main():
    parser = argparse.ArgumentParser(description='Benchmark locale su dati sintetici.')
    parser.add_argument('--sizes', type=int, nargs='+', default=[100, 1000, 10000])
    parser.add_argument('--repeat', type=int, default=5)
    parser.add_argument('--ui', action='store_true')
    args = parser.parse_args()
    if args.repeat < 1 or any(n < 1 or n > 32768 for n in args.sizes):
        parser.error('Usare 1–32768 elementi e almeno una ripetizione.')
    print(f'Python {platform.python_version()} · {platform.system()} {platform.machine()} · dati sintetici')
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
        timed('confronto A/B riusato', screen.comparison_for_current, args.repeat)
        if args.ui:
            asyncio.run(ui_measure(regions, args.repeat))


if __name__ == '__main__':
    main()
