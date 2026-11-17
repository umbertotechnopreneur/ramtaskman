# Counter and grouping audit

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

Status on November 16, 2026: source analysis of psutil 7.2.2, pinned in `uv.lock`,
performed on Linux. **This historical analysis is not a native test.** Native
Windows CI checks subsequently passed: six Ubuntu/Windows jobs with Python 3.11,
3.13 and 3.14. Manual checks on a personal Windows PC remain pending. The macOS
column describes only the experimental backend source.

| Item | Windows, current psutil backend | macOS, current psutil backend |
|---|---|---|
| Total/available | `virtual_memory()` uses total/available physical memory; free equals available. | `virtual_memory()` uses available = inactive + free, according to psutil source. |
| RSS | Working set exposed by `memory_info()`. | RSS exposed by `memory_info()`. |
| USS | `memory_full_info()` queries psutil's native private-resident-memory counter. | `memory_full_info()` uses psutil's native private-memory counter. |
| PSS | Not exposed by this backend. | Not exposed by this backend. |
| Per-process swap | Not exposed; pagefile/private commit is not treated as disk swap. | Not exposed by this backend. |
| System swap | psutil combines commit limit, physical RAM and pagefile performance counters; this is a psutil indicator, not process commit or a direct count of every page on disk. | psutil uses `swap_mem()`; semantics are described by source, without Mac validation. |
| Global partition | Used/available fallback. | Used/available fallback. |
| Applications | Account + executable/name fallback. | UID + executable/name fallback. |

Primary references: [psutil Windows source](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/_pswindows.py),
[psutil macOS source](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/_psosx.py),
[PROCESS_MEMORY_COUNTERS_EX documentation](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex).
The installed source and lockfile determine the version actually in use.
For Windows, complete the manual checks in the [dedicated procedure](verifica-windows.md).
The [macOS procedure](verifica-macos.md) is guidance for external contributors only.

Identity based on name or executable is heuristic: a shared interpreter or launcher
can group distinct programs together. A bundle ID or package ID may describe a
product, but alone does not establish the identity of an instance and its helpers.
Until reliable metadata and multiple-user/instance cases are verified on real
hardware, we retain the declared fallback without speculative aggregation.

Do not treat the fields in these columns as disjoint partitions without establishing
that they cover the same domain and do not overlap. Native tests and comparison
with equivalent counters remain necessary before claiming platform parity.
No such parity is claimed for macOS, and verifying it is outside internal work.
