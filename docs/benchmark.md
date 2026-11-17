# Local memory benchmark

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

This document describes reproducible measurements, not guaranteed performance
requirements. The tool uses only the standard library and dependencies already
installed in the project.

## Running the benchmark

From the repository root, for synthetic transformations:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000 32768 --repeat 5
```

To include the 160×48 Textual UI and Linux readings **of the benchmark process only**:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000 32768 --repeat 5 --self-linux --ui
```

`--self-linux` does not enumerate other processes or print PIDs, names, paths or
computer details. It measures identity metadata, `smaps_rollup` and `smaps` for
the benchmark process without reading memory contents or mapped files. On other
systems, this section is reported as unavailable. `--ui` uses only synthetic
processes, paths and regions with the Textual harness; it writes no captures or
screenshots. Dependencies and cache remain in the project, following the launchers.

Each operation runs once for warm-up, then `--repeat` times. Tables show the median,
high percentile and sample count when available. Percentiles from small samples
are very sensitive to a single value: five observations are not enough to estimate
a statistically robust tail. Record CPU, operating system, Python and application
versions separately before comparisons; do not include private paths or process
names in a shared report.

Individual UI method timings include Python processing and row creation; they
**exclude actual terminal painting**. Measurements using `pilot` include harness
pauses and waits, so they are not equivalent to real keyboard latency. Measuring
perceived latency also requires manual checks in a real terminal.

## Results from November 16, 2026

Linux x86_64, Python 3.14.4, psutil 7.2.2, Textual 8.2.8; five repetitions after
warm-up, simulated 160×48 terminal. These are observations on the machine used
at that time, not predictions for other systems.

### Native readings of the test process only

The process had 138 regions in the first sample. Times are median / high percentile:

| Stage | Time |
|---|---:|
| Identity and cgroup metadata | 0.25 / 0.26 ms |
| `smaps_rollup` counters | 0.71 / 0.72 ms |
| Reading `smaps` regions | 7.81 / 7.93 ms |

Benchmark RSS before/after the sequence: 39.11 / 39.32 MiB; total CPU consumed:
50 ms at the system's timing resolution; file descriptors before/after: 4/4.
Operations include the measured methods' identity checks: they are not independent
kernel counters. The `smaps` scan is sequential and may change while being read.
Do not multiply these times by the computer's process count to estimate a full
scan: permissions, page counts and process sizes vary.

### Model and UI with synthetic data

| Processes / regions | Python fixture memory | Grouping median | Filter median | A/B diff median / p95 | `render_regions` median / maximum |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.09 MiB | 0.27 ms | 0.05 ms | 0.34 / 0.36 ms | 4.92 / 5.75 ms |
| 1,000 | 1.10 MiB | 1.56 ms | 0.56 ms | 3.26 / 3.26 ms | 11.93 / 15.03 ms |
| 10,000 | 11.29 MiB | 15.71 ms | 5.98 ms | 43.36 / 89.11 ms | 29.35 / 34.68 ms |
| 32,768 | 37.15 MiB | 51.76 ms | 19.46 ms | 171.47 / 242.03 ms | 70.88 / 73.82 ms |

The last column measures synchronous `render_regions` after a search, with a
250-row paginated table; it excludes painting. At 32,768 regions it exceeds the
initial indicative 50 ms target. The diff is cached while A/B remain unchanged;
the initial computation was subsequently moved to a cancellable worker.
Full UI opening times with `pilot` were 488 / 528 / 570 / 868 ms for the four sizes.
Three rapid text changes produced one redraw per repetition; the total wait
includes debounce and test-imposed pauses.

### Starting the background comparison

A second synthetic test, with three repetitions and 32,768 regions, compared two
variants **both computing in a worker**. Before a fixed description was supplied
to Textual, starting the action took a median of 153.17 ms: the decorator built a
text representation of both complete captures on the UI thread. With the fixed
description, the median was 1.61 ms and the maximum 1.80 ms. Time until the result
became visible, including the harness and pauses, was 563.48 and 359.60 ms respectively.
These few repetitions do not establish real terminal latency or guarantee that
the UI always stays responsive while Python code runs in the worker. The GIL is shared.

The comparison engine checks cancellation during validation, region processing
and totals; in-memory construction/sorting cannot be interrupted mid-operation.
If the user closes the view or changes the sample, the worker may finish an operation
already in progress, but its stale result is discarded using generations and
snapshot identities. Partial results are not displayed.

## Localized search: a focused check

November 16, 2026, Linux x86_64, Python 3.14.4: using `tools/benchmark_memory.py`,
synthetic fixtures with 1,000 regions and three repetitions, median search time
was 0.76 ms before and 0.52 ms after preparing translated labels once per filter.
These are a few local measurements subject to noise; they do not demonstrate a
general improvement or measure terminal painting.

## Limits and remaining work

- No realistic measurement across all processes on the computer was performed:
  the native test covers only the benchmark process.
- RSS before/after and file descriptor counts provide only two points; they do
  not establish the absence of growth in a long session. That requires many
  controlled cycles with time series.
- Synthetic workloads do not reproduce a real browser's distribution, permissions,
  large pages or timings. Latencies on the owner's Windows terminal remain
  unmeasured; macOS measurements are outside internal verification.
- Besides the diff, filtering, sorting and `render_regions` at 32,768 regions can
  still occupy the UI thread. Moving them into cancellable work requires generation
  and selection tests, plus further measurements. Pagination alone does not
  guarantee completion within 50 ms.
- Cooperative cancellation does not interrupt a syscall or sort already in progress.
- The project still lacks measurements of painting, perceived latency, resizing
  and closing on Linux/Windows under varying load; F4 remains open. Ubuntu/Windows
  CI results do not replace these interactive measurements.
