# ramtaskman user guide

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

A **RAM task manager for Linux and Windows**, with an experimental macOS backend,
written in Python and Textual. It adapts the layout, widgets, colors and shortcuts
of [Scott Hanselman's gputaskman](https://github.com/shanselman/gputaskman), with a
collector dedicated to application memory, **PSS, USS, RSS, swap and SwapPSS**.

This is the first working version and remains experimental. The terminal interface
uses Full diagnostics → System → Charts → table → inspector → footer panels,
as in gputaskman. Metrics and labels are adapted to RAM; this is not a
pixel-for-pixel copy of every GPU state.

## Start the app

Requires Python >=3.11 and `uv`. Linux requires `/proc` and `smaps_rollup`.
On Windows, use Windows Terminal. External macOS contributors can consult the
[unverified guidance](verifica-macos.md). The minimum version is declared in
pyproject.toml; Python 3.14 is not required on Windows or macOS.
The development machine uses Python 3.14.4.

Linux:

```bash
./run.sh --language en
./run.sh --once --language en
./run.sh --json
./run.sh --processes --interval 2 --language en
```

Windows, from PowerShell or Command Prompt:

```powershell
.\run.cmd --language en
.\run.cmd --once --language en
.\run.cmd --json
```

`run.sh` and `run.cmd` can be launched from any directory. The environment and
dependency cache stay inside the project (`.venv` and `.uv-cache`, excluded from Git).
The first run installs the dependencies pinned in `uv.lock` and requires network access.
The launchers do not download Python automatically. To select an interpreter
already installed, use `UV_PYTHON=python3.13 ./run.sh`; in PowerShell, set
`$env:UV_PYTHON = "3.13"` before running `.\run.cmd`. Do not share `.venv` between
operating systems: recreate it locally after copying the project.
The UI uses no GPU, cloud APIs, external services or telemetry.

Alternatively, from the repository root:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv sync --locked
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked ramtaskman --language en
```

This project is not published on PyPI: do not use `pip install ramtaskman` to obtain
this copy. Elevated privileges are not required; protected processes remain
partially visible.

## Interface and report language

`--language` selects Italian (`it`, the default), English (`en`), Simplified
Chinese (`zh`), Korean (`ko`), French (`fr`), Vietnamese (`vi`), Spanish (`es`),
Portuguese (`pt`), German (`de`) or Japanese (`ja`). It applies to the dashboard,
details, regions, footer, help, application messages and text report:

```bash
./run.sh --language it
./run.sh --language fr --help
./run.sh --language ko --once
```

On Windows, use the same options with `.\run.cmd`. CLI options, counter symbols
and the JSON schema keep their identifiers. Names, paths and details returned by
the OS remain literal. Captures preserve reasons as recorded text: reopening them
in another language translates the interface, not that data. Translations were
prepared with AI assistance and need native-speaker review.
Local Linux checks with Python 3.14.4 covered CLI, synthetic UI at 160×48 and 80×24,
builds, isolated installation and replay. Native Windows CI checks have also passed;
manual testing on a personal Windows PC is still pending. macOS is untested and unvalidated.

## Platform support

| Feature | Linux | Windows | macOS |
|---|---|---|---|
| Textual UI, applications/processes, charts, JSON | Implemented | Implemented | Experimental code, unverified |
| System RAM and RSS | procfs / psutil | psutil / working set | psutil |
| USS | Private_Clean + Private_Dirty | psutil, private resident memory | psutil, private memory |
| PSS | smaps_rollup | n/a | n/a |
| Per-process Swap and SwapPSS | smaps_rollup | n/a | n/a |
| System swap | meminfo | pagefile through psutil | psutil |
| Linux cache, slab, PSI | Available | n/a | n/a |
| Process regions and navigable map | smaps on demand | Virtual ranges only, experimental | Not implemented |
| Verification performed | Local tests and checks | Native CI passed; manual personal-PC check pending | Untested and unvalidated; no Mac available |

Initial sorting uses USS on Windows/macOS and PSS on Linux. The same UI keeps
unsupported columns at n/a and explains the limitation. Current CI covers Ubuntu
and Windows with Python 3.11, 3.13 and 3.14; all six jobs passed at the recorded
checkpoint. macOS is excluded from the matrix and internal verification.
Consult GitHub Actions for subsequent results.

`psutil` handles native APIs; this implementation does not need pywin32 or WMI.
psutil does not expose PSS on Windows/macOS. Windows private commit/PagefileUsage
is neither private resident RAM nor a process's actual swap use.
Sources: [psutil 7.2](https://psutil.io/7.2/#psutil.Process.memory_full_info),
[Microsoft PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex).

## Controls

| Key | Action |
|---|---|
| ↑ / ↓ | Select a row |
| Enter on an application | Show only processes in that group |
| Enter on a process / r | Open the region map; on an application, r first shows its processes |
| Esc | Return from processes to applications; clear filters when search controls have focus |
| g | Toggle applications / all processes |
| s | Sort by PSS, USS, RSS, Swap, SwapPSS or name |
| c / Charts selector | Switch charts |
| a | All / top 30 in the current sort order |
| m | Slim / Full diagnostics |
| / | Search name, executable path or exact PID |
| f | Open user and memory-state filters |
| d | Memory details for the selected group or process |
| p | Pause / resume |
| ? | Explain metrics |
| F1 | About, author and original credits; Esc returns to monitoring |
| q | Quit the program |

Quitting the program does not close the desktop session.
The interface starts in Slim mode; press `m` for Full diagnostics.
The dashboard and inspector scroll in small terminals; the table scrolls horizontally.

## RAM value and monthly allocation

Enter today's price for your RAM to see a simple estimate of each app's share
of that hardware cost. You can update the price whenever you want to compare
usage against a different purchase price or current quote.

```bash
./run.sh --language en --ram-price 320 --ram-currency EUR
./run.sh --language en --ram-price 320 --ram-currency EUR --ram-months 36
./run.sh --json --ram-price 320 --ram-months 36
```

You supply the price of all RAM in the machine: there is no automatic price lookup
or network request. Capacity defaults to RAM visible to the operating system,
which may be lower than the nominal installed capacity. For a nominal 32 GiB kit,
you can specify `--ram-capacity-gib 32`.

Value = price × attributable bytes / capacity. `--ram-months` divides this value
by the chosen number of months. This allocates hardware cost; it is not a bill,
energy consumption or guaranteed savings. The current allocation is not a monthly average.

Linux uses PSS, which apportions shared pages. Windows uses USS, so only private
resident memory is valued; shared memory is excluded. There is no RSS fallback.
Incomplete or unmeasurable groups remain n/a (`null` in JSON). Do not add application
values to those of their member processes or to system memory. Cache, kernel
memory and inaccessible processes are not arbitrarily attributed to Windows or
other applications. Samples are sequential, not atomic.

The value column follows current measurements during monitoring; the inspector
identifies the metric used. JSON adds `ram_valuation` only when requested.

Press **F1** for About: VibeWare, Umberto Giacobbi, website, thanks to Scott Hanselman
and references to the MIT provenance. Esc closes About without stopping monitoring.

## System RAM bar

The RAM row extends to the right edge of its panel, showing proportional colored
segments. Labels appear inside segments when space allows; the legend lists all
categories and values, including those smaller than one terminal cell.

On Linux, the bar describes usable RAM reported in `MemTotal`:

| Segment | Counter |
|---|---|
| Anonymous | AnonPages |
| File cache | Cached − Shmem |
| Shared/tmpfs | Shmem |
| Buffers | Buffers |
| Reclaimable slab | SReclaimable |
| Unreclaimable slab | SUnreclaim |
| Other | Calculated remainder: MemTotal minus the other segments |
| Free | MemFree |

The segments sum to `MemTotal`. Other is memory not classified by the chosen
counters, not a kernel-only measurement. `MemTotal` is not necessarily all installed
physical RAM: some hardware/kernel reservations are excluded from the usable total.
Do not add `Slab`, `Mapped`, PSS/RSS or process clean/dirty counters again: they
overlap categories already represented.

**Available** remains a separate indicator: it includes reclaimable memory,
including some cache. **Net used** is `total − available`, the same indicator as
the RAM chart; it is not the sum of all non-free categories. Readings are sequential.
If fields are missing or a sample is inconsistent, the reason is shown and the
simpler used/available bar is used. This is also the current Windows/macOS fallback;
no categories are invented. Inconsistent values are not normalized to fit the total.

This is a **map of consumption by OS category**, not a physical-address layout.
On Linux, Full diagnostics also shows the cache value used in the chart, slab,
and `Committed_AS` / `CommitLimit` from `meminfo`. Cache and slab overlap the bar's
categories. Commit is committed virtual memory, not resident RAM or swap. Its
limit depends on overcommit configuration and is not always enforced. Missing
fields remain n/a. Linux reclaimable/unreclaimable slab categories are not
Windows paged/nonpaged kernel pools.

On Windows, Full diagnostics adds system cache, paged and nonpaged kernel pools,
current commit, commit limit and peak since boot through
[GetPerformanceInfo](https://learn.microsoft.com/windows/win32/api/psapi/ns-psapi-performance_information).
Cache includes standby and system working set and overlaps available memory.
Paged pool measures an allocation, not only resident pages. Commit is a virtual
memory commitment, not resident RAM or swap. These views are not additional bar
segments to sum. Readings are sequential; on error, details become n/a with a
reason and are retried at the next sample.

For a process, `d` shows the aggregate breakdown and `r` opens the Linux `smaps`
region map: virtual addresses, files, permissions and residency. Virtual addresses
are not contiguous physical positions in RAM.
Sources: [Linux procfs](https://docs.kernel.org/filesystems/proc.html#meminfo),
[meminfo source](https://github.com/torvalds/linux/blob/master/fs/proc/meminfo.c).

## What the numbers mean and their limitations

In Full diagnostics, below system RAM, the **application USS** bar shows the top
10 applications with complete USS readings using numbered segments and a colored
legend; other complete applications share one segment. Its scale is the sum of
USS for complete applications in the sample, not total or used RAM. Partial groups
are excluded with explicit coverage. The bar follows the table's grouping and
describes the full sample even with search, filters or drilldown active. Block
positions are not physical RAM ranges. Applications with identical names may be
separate groups; numbers and the legend identify their segments.

- **PSS:** private memory plus a proportional share of shared memory.
- **USS:** `Private_Clean + Private_Dirty` from Linux `smaps_rollup`.
- **RSS:** resident memory, including shared pages. Summing it may double-count them.
- **Swap:** the `Swap` field in `smaps_rollup`; excludes shmem swap and may count
  shared pages more than once. **SwapPSS** proportionally apportions accounted shared swap.
- **RAM used:** `total - available`; on Linux, `MemTotal - MemAvailable`. It is not
  the sum of PSS/RSS. On macOS, available follows psutil (free + inactive), not
  Activity Monitor's Memory Pressure. On Windows, psutil free and available coincide.
- **Cache:** `Cached + Buffers + SReclaimable - Shmem`, floored at zero, in the
  history chart. It overlaps available memory. The RAM bar represents file cache,
  buffers and reclaimable slab separately, without adding this total a second time.
- **Slab:** kernel memory from `meminfo`, not all kernel consumption.
- **PSI some:** percentage of time with at least one task waiting for memory,
  averaged over 10 seconds. It is not the percentage of occupied RAM.
- **n/a / null:** unavailable reading; zero is reserved for a measured zero.
  A group's total is unknown if even one value for that metric is missing.
  `Readings` shows group PSS and USS coverage. The dashboard displays **partial visible sums**.
- HugeTLB pages are not included in the ordinary counters shown here.

**Application:** on Linux, the systemd application instance is used when explicitly
identified by the user's cgroup (`app-*.scope` or `app-*.service` under `app.slice`).
Helpers with different executables in the same instance are grouped together;
different instances and users remain separate. Entire sessions and generic services
are not aggregated. The displayed name comes from the systemd identity, decoding
escaping where applicable. The full instance path remains available in the inspector
and JSON.

Without an explicit identity, including on Windows/macOS, grouping uses
`(user, executable)` or `(user, name)` when the path is missing: this is a declared
fallback. User means UID on Unix and domain/name on Windows. An unknown owner
keeps the process separate. The fallback can still combine multiple Python programs
using the same executable. The inspector and JSON `grouping` field identify the
criterion (`cgroup`, `executable`, `name`).
Convention source: [systemd Desktop Integration](https://systemd.io/DESKTOP_ENVIRONMENTS/).

## Search and filters

Press `/` to open the search bar. Search is a literal, case-insensitive substring
match on application name, process names and executable paths. A digits-only query
instead finds an **exact PID**. It does not use regular expressions. Enter returns
focus to the table while keeping the query. Typing in the field does not trigger shortcuts.

Press `f` to open the selectors:

- **User:** everyone or a collected UID/account.
- **With swap:** at least one process has measured swap greater than zero; n/a does not match.
- **Partial data:** a reading is missing among the metrics supported by the OS.
  Unsupported PSS/swap on Windows/macOS do not by themselves mark every row as partial.

Search, user and memory-state criteria combine. Filtering runs **before** the
Top 30 limit. In application view it selects whole groups: all processes remain
in their totals even if only one helper matches. In process view it selects
individual processes within the current context. Filters survive entering an
application with Enter and returning with Esc. Reset, or Esc with focus in the
controls, clears all filters. Esc from the application table also clears them when
the bar is open. Charts and dashboard continue to describe the whole system.
The bar reports displayed, matching and total rows, including an explicit no-results state.

## Detailed memory breakdown

Select an application or process and press **d**. The scrollable window shows:

- **PSS bar:** anonymous, file and shmem, proportional to total PSS.
- **RSS bar:** private clean/dirty and shared clean/dirty, proportional to total RSS.
- **Separate Swap and SwapPSS:** neither is included in resident RAM bars.
- **Anonymous, file and shmem PSS:** proportional breakdown by page type.
- **Private clean/dirty:** the two USS components.
- **Shared clean/dirty:** shared resident pages; groups may count these more than once.
- **Anonymous, LazyFree and AnonHugePages:** other views of anonymous, reclaimable and THP pages.

These details come from the same Linux `smaps_rollup` read; they add no scan of
individual mappings. They are **overlapping views**, not components to sum together.
A missing field remains n/a with reading coverage: a partial total is not presented
as complete. On Windows/macOS, details show the available general counters and n/a
for the Linux breakdown. The window pins its sample when opened; close and reopen
it to update. Esc or d closes it. Main sampling continues.
Source: [Linux kernel procfs documentation](https://docs.kernel.org/filesystems/proc.html).

Bars use the full available width and keep sub-cell components in the legend.
Consistency is checked per process before aggregating an application, so opposite
errors cannot cancel out. RSS requires an exact sum. procfs truncates the three
PSS counters separately to kB: a remainder of 0, 1 or 2 KiB per process is explicitly
shown as **procfs rounding**, without rescaling components. Other inconsistencies
produce n/a with a reason.
Source: [Linux kernel, __show_smap](https://github.com/torvalds/linux/blob/v6.17/fs/proc/task_mmu.c).

## Linux region map

In live mode, the top card repeats the system RAM bar and shows the selected PID's
USS share on a total-RAM scale. The remainder includes available RAM; it is not
just other applications' consumption. These counters follow the current RAM sample,
with explicit age, separately from on-demand region reads. The card is not shown
in offline replay. On Windows the map starts with virtual addresses in ascending
order; boundaries and the selected range appear at the top, with an exclusive end
and holes excluded from the scale. Positions in the consumption bar are not
physical addresses. The view describes one PID, not all helpers in its group.

Select an application, press Enter to choose one of its processes, then **r** or
**Enter** on that process. Each PID has a distinct virtual address space; maps
for processes in a group are not combined. The view preserves the terminal UI's
panels, borders, colors and table. The experimental Windows provider shows virtual
ranges without per-region resident counters. The feature is not available on macOS.
The Windows provider has simulated tests and native Windows CI checks; manual
checks on a personal Windows PC remain pending.

Press **v** to switch between two map modes:

- **Resident RAM, RSS:** block widths are proportional to resident memory in the
  displayed regions. Shared pages may appear in multiple mappings.
- **Virtual space:** widths follow region virtual sizes, ordered by ascending
  address. Holes are excluded from the scale; visible transitions are marked `│`.
  This is not a representation of physical frames.

Colors distinguish executables, libraries, files, recognized heap/stack mappings,
anonymous memory, shmem and special regions. Type describes mapping origin using
declared heuristics: a file mapping can also contain private pages modified through
copy-on-write. Anonymous memory is not automatically called heap or identified as
application objects.

The table shows addresses, type, virtual size, RSS, PSS, USS, swap, permissions and
name. The lower panel adds offset, inode, clean/dirty, SwapPSS, anonymous pages,
THP, HugeTLB and VmFlags. THP is already included in ordinary counters; HugeTLB
remains separate. Bar and table selection are synchronized. Regions smaller than
one cell remain selectable in the table.

| Key in the map | Action |
|---|---|
| ↑ / ↓, or click the bar | Select a region |
| v | Toggle RSS / virtual space |
| s | Sort table by RSS, PSS, virtual size or address; map stays in virtual order |
| / | Search name/path, type, permissions or a hexadecimal `0x…` address inside a region |
| f | Filter type and state: resident, with swap, with shared RSS pages |
| Enter in search | Return focus to the table |
| z / Enter on the table | Zoom to the region with up to two neighbors on each side; repeat to exit |
| Tab, then ↑ / ↓ / PgDn | Focus and scroll the details panel |
| r | Read a new process sample |
| b / Ctrl+B | Pin sample A / remove A |
| c | Toggle current view / A→B comparison |
| Ctrl+S / Ctrl+O | Save / open a local capture |
| Esc | Clear open filters, then leave zoom, then return to processes |
| q | Close the map and return to processes |

Search and filters combine; the map and its total describe the displayed regions,
including while zoomed. Updates are **on demand**, at opening or with `r`; general
sampling continues to use `smaps_rollup`. The panel shows time, age, duration and
completeness. Loading a new sample or encountering an error does not leave old
values displayed as current.

Scanning is limited to 32 MiB of metadata, 32,768 regions and 3 seconds, checked
between reads. Cancellation and timing are cooperative: they do not interrupt a
procfs call already in progress. Reaching a limit retains only completed regions
and marks the sample partial. Denied access, process exit, PID reuse or malformed
data produce explicit reasons. There is no automatic privilege elevation.

Each process is identified by PID and creation time, preventing reuse of a selection
for a new process with the same PID. Reads are sequential, not atomic; global and
per-process totals are not artificially forced to match. UID, namespaces and procfs
permissions may limit the data. The UI exposes missing readings without automatic
elevation. It does not read `/proc/PID/mem`, cmdline, environment or application contents.

The worker samples in the background and waits `--interval` seconds **after** each
scan; the effective period includes `sample_ms`. Default: 2 seconds. Charts keep
60 samples, not necessarily 60 seconds. CPU is n/a on the first reading.

## A/B comparison and captures

In the map, press **b** to pin A, perform the action you want to observe, then **r**
to collect B. Press **c** to compare; `v` switches metrics and `s` switches change
sorting. Reorganized ranges or incomplete samples do not produce invented deltas.
A remains pinned even if B is unavailable. Reads are sequential: observed growth
alone does not prove a memory leak.

Use **Ctrl+S** to save to an explicitly chosen path; **Ctrl+O** opens a saved reading.
Files can contain process names and paths: inspect them before sharing.
To open from the terminal without starting live collection:

```bash
./run.sh --language en --open capture.rtm.json
./run.sh --language en --compare before.rtm.json after.rtm.json
```

`--compare` requires one sample per file; `--open` also accepts a file containing
A and B. Comparison requires compatible collection sessions, process identities
and definitions. An identical range does not prove the same allocation remained.
The format is described in the [capture schema](schema-capture.md).

The optional `--max-measurements N` budget limits expensive process reads per cycle,
rotating among processes. Deferred readings remain n/a; attempts and deferrals
are visible. This budget does not impose a time limit on OS calls. By default,
all processes continue to be collected.

With a budget, `--measurement-backoff` temporarily defers repeatedly denied or slow
reads (at least 250 ms). Deferral lasts at most eight cycles; reads then rejoin
rotation and are retried when the budget allows. The row explains the deferral,
and counters remain n/a. With `--selected-priority`, available only in the live UI,
a selected PID gets at most one slot per cycle; with budget 1, it receives priority
only once every three cycles, leaving room for rotation. Selecting a group does
not prioritize a PID. Both options are disabled by default.

## Structure

```text
src/ramtaskman/
  cli.py        → Collector.sample()
  collector.py  → backend selection, sampling and coverage
  backends/     → Linux procfs; Windows/macOS psutil
  models.py     → ProcessMemory, ApplicationMemory, SystemMemory, Snapshot
  grouping.py   → systemd application identities from cgroups
  filters.py    → search and filters without changing aggregates
  detail.py     → granular breakdown with coverage and explanations
  memory_bars.py → PSS/RSS bars with explicit denominators and reasons
  memory_segments.py → Linux global accounting without overlap
  ram_bar.py    → full-width proportional RAM bar and legend
  regions.py    → smaps parser and bounded reads of the selected process
  region_map.py → RSS/virtual map with region selection
  region_screen.py → explorer: search, filters, zoom and on-demand refresh
  report.py     → one-shot table and JSON schema_version=1
  app.py        → Textual, workers, tables, navigation and charts
  app.tcss      → CSS copied from the original UI
  widgets.py    → original spark and stacked_bar
 tests/         → accounting, CLI and UI with hardware-independent fixtures
 tools/         → synthetic screenshot capture
 docs/          → architecture, provenance and agent handoff
```

## Verification

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once
./run.sh --json
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/capture_screenshots.py
UV_CACHE_DIR="$PWD/.uv-cache" uv build
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/verify_distribution.py
```

SVGs in `captures/` use **synthetic data**, not measurements of the PC, and are
excluded from Git. Live JSON contains names, UIDs and executable paths: review it
before sharing. Captures are not saved automatically.

Historical checkpoint: **171 tests** ran locally with Python 3.14.4, with 170 passing
and one native Windows test skipped on Linux. Wheel/sdist builds, installed-distribution
verification and Linux sampling succeeded. At that checkpoint, Windows/macOS contracts
were simulated rather than measured on hardware. Later recorded results include
native Windows CI and six passing Ubuntu/Windows jobs; manual checks on a personal
Windows PC remain pending. macOS remains experimental, untested and unvalidated,
outside internal verification.

The UI was captured and visually checked with synthetic fixtures, including filters,
memory details and regions. The suite covers bar accounting, smaps parsing and limits,
PID identity, filters, selection/zoom, map refresh and errors, UI at 160×48 and 80×24,
and main sampling continuing while the map is open. Packages include the new modules
and CSS, excluding caches and local captures.

## Provenance and further reading

- [Documentation index](README.md)
- [Contributing](../CONTRIBUTING.md)
- [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [Gallery and synthetic image reproduction](images/README.md)
- [Manual checks pending on a personal Windows PC](verifica-windows.md)
- [Unverified macOS guidance for external contributors](verifica-macos.md)
- [Platform counter audit](audit-contatori-piattaforma.md)
- [Local benchmarks and measurement limitations](benchmark.md)
- [Detailed development plan and progress log — Italian](piano-sviluppo.md)
- [Provenance, license and reused code](upstream.md)
- [Architecture and invariants](architecture.md)
- [Agent handoff — Italian](handoff.md)
- [Agent instructions — Italian](../AGENTS.md)
- [Verified lessons](../lessons.md)

MIT license; Scott Hanselman's original copyright is retained in [LICENSE](../LICENSE).
The original Git history is preserved. This is an independent derivative project,
not an official Scott Hanselman release.
