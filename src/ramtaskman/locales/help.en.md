# ramtaskman · understanding the numbers

We develop and test on Linux and Windows. The macOS backend is experimental: we do not test or validate it because we do not have a Mac available. Any macOS verification remains an external contribution; the project's CI does not include macOS.

The visual structure of gputaskman, adapted to memory on Linux, Windows and macOS.

| Field | Meaning |
|---|---|
| PSS | Private RAM plus a proportional share of shared pages |
| USS | Private_Clean + Private_Dirty: private resident pages |
| RSS | Resident pages, including shared pages; adding values may count them more than once |
| Swap | Swap from smaps_rollup, excluding shmem swap; shared pages may be counted more than once |
| SwapPSS | Proportional share of shared swap accounted for by smaps_rollup |
| RAM used | MemTotal − MemAvailable; this is not the sum of processes |
| Cache | Cached + Buffers + SReclaimable − Shmem; overlaps available memory |
| PSI some | Percentage of time with at least one task waiting for memory, averaged over 10 s |

**RAM bar:** fills the available width and partitions Linux OS counters into anonymous memory, file cache (Cached − Shmem), shared/tmpfs, buffers, reclaimable/non-reclaimable slab, other (a calculated residual), and free memory. These are accounting categories; their order does not represent physical addresses. Available memory is a separate indicator that includes reclaimable cache, so it is not another segment. Process clean/dirty and PSS details stay in **d**, because they overlap global counters. If fields are missing or the sample is inconsistent, the bar shows used/available memory and explains why the breakdown is absent. The legend also lists categories smaller than one character.

**App USS bar:** shows the top 10 apps with complete USS and the remaining complete apps. Its scale is the USS sum of complete apps in this sample, not total RAM. Numbers and colors refer to the legend. Partial groups are excluded and coverage is stated. Grouping follows the table; segments are not physical addresses.

**Windows/macOS:** USS and RSS come from psutil. Per-process PSS, Swap and SwapPSS are not exposed and remain n/a. Windows private commit/pagefile is NOT swap on disk. On macOS, RAM used is psutil total − available, not Activity Monitor's Memory Pressure.

**Application:** on Linux, an explicit systemd cgroup identifies an app instance, including helpers with different executables. Different users and instances remain separate. Without that identity, including on Windows/macOS, grouping uses user + executable, or user + name as a heuristic when the path cannot be read. The inspector shows the method.

**Search and filters:** press **/** to search by name, executable or exact PID; **f** selects user and memory state (**with swap** or **partial data**). Filters combine. An app matches when one of its processes matches the search or memory state, but its total retains all members. Filters remain when entering the process view. They apply before Top 30; charts and dashboard describe the whole system. **Enter** in search returns to the table. **Esc** in controls or **Reset** clears filters; **Esc** in the process table returns to apps while retaining them. Partial data considers only counters supported by the system; unknown swap does not mean used swap.

**d** opens RAM details for the group or process: anonymous/file/shmem PSS, private and shared clean/dirty, anonymous pages, LazyFree and THP. These are Linux-only fields, n/a elsewhere. Rows are overlapping views and must not all be added together. Details fix the sample when opened; close and reopen to refresh. **Esc** or **d** closes details.

**r** or **Enter** on a process opens the Linux region map. On an app, **r** first shows its PIDs: every process has its own virtual space. The bars in **d** partition PSS and RSS separately; swap stays outside resident RAM.

In the map, **v** switches RSS/virtual addresses, **s** sorts, **/** searches files or an address 0x…, **f** filters type/state, **z** or **Enter** zooms to the selected region's neighborhood, **r** refreshes, and **Esc** clears filters/leaves zoom/goes back. The map follows virtual addresses, not physical frames. Gaps are excluded from the virtual scale and marked with │; regions smaller than one character remain in the table. Type describes the mapping's origin, not its contents: a file mapping can contain private CoW pages; only recognized heaps/stacks are labeled as such. Samples are on demand and show age, duration and read limits. Windows has experimental virtual ranges only; macOS has no region map.

In regions, **b** fixes A, **r** collects B and **c** opens comparison. In comparison, **v** changes metric, **s** changes order, **f** filters state and **Ctrl+B** removes A. **Ctrl+S** saves samples; **Ctrl+O** opens a file offline. Files contain metadata and may include personal paths. Missing data and restructured regions remain n/a; the same interval does not prove the same allocation or a memory leak.

**n/a is not zero.** An app total is n/a if even one value is missing. Readings shows PSS/USS coverage. Dashboard visible totals are partial sums of available readings and do not represent all system RAM. Reads are not atomic: processes can change during sampling. Other users, sandboxes and procfs permissions may prevent reads. There is no automatic privilege elevation. HugeTLB is excluded from the ordinary RSS/PSS/USS counters shown here.

The program reads metadata, not /proc/PID/mem, cmdline, environment or app contents.

**g** apps/processes · **Enter** selected app's processes · **Esc** back to apps

**s** sort · **c** chart · **a** all/top 30 · **m** compact/full

**/** search · **f** filters · **d** details · **r** regions · **p** pause · **?** help · **q** quit

Charts show the last 60 samples, percentages on a 0–100 scale. Blank space means missing data. The interval is a pause after sampling; actual elapsed time also includes the scan.
