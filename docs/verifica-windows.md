# Native Windows region verification

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

Automated native Windows checks have passed in CI; the latest Ubuntu/Windows matrix
with Python 3.11, 3.13 and 3.14 has six passing jobs. The manual procedure on the
owner's Windows PC is **still pending**. The `VirtualQueryEx` provider is experimental:
it displays virtual ranges, not per-region RSS. The test uses only a controlled
allocation created by its own Python process. It does not require elevated privileges,
read other processes' memory bytes, or change system settings or the desktop session.

## Prerequisites

- Windows 10 or later, 64-bit Python >=3.11, `uv` and a copy of the project.
- PowerShell or Windows Terminal. UI checks require a terminal with color and
  resizing support.
- Do not share `.venv` between Linux and Windows: recreate the project environment
  as described in the [README](../README.md). The launchers keep the cache in the project.
- The test process requires no restart, disabled protections, driver installation
  or administrator privileges.

Check that Python, uv and the project directory are available. From the repository root:

```powershell
.\run.cmd --version
.\run.cmd --once --language en
.\run.cmd --json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Record the Windows version/build, system and interpreter architecture, and Python,
psutil and Textual versions. Do not copy private names or paths into public reports.
Mocked tests do not replace the native readings in the next step.

## Controlled allocation test

Run from the repository root in PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run --locked python tools\verify_windows_regions.py
```

The command prints JSON **only to the terminal**, with the system version,
architecture, page size, four stages and provider result. To observe the same
allocation in the UI during the test:

```powershell
uv run --locked python tools\verify_windows_regions.py --hold-seconds 60
```

The temporary PID is printed before the wait. In a second terminal, run
`.\run.cmd --processes --language en`, search for that PID with `/`, select it and
press Enter to open the map. Return to the first terminal's output when the test
ends. The maximum selectable duration is 300 seconds; the test frees its allocation
before exiting. The virtual address in the JSON is only for matching the test
process's row and may change between runs.

The expected stages are:

| Stage | Operation | What to check |
|---|---|---|
| `reserved` | Reserve 8 MiB in the test process | `VirtualQueryEx` reports `MEM_RESERVE`; a reservation is not resident RAM. |
| `committed` | Commit the range | The region reports `MEM_COMMIT`; commitment does not prove that pages are resident. |
| `touched` | Write one byte to each page of the test allocation | Compare the observed bits with the previous stage; the provider should find a region containing the address. |
| `released` | Free the range | Observe the new state; the map may have changed in the meantime. |

For `QueryWorkingSetEx`, the JSON reports **requested pages**, pages actually
queried, and counts of `Valid` bits set to 1/0 only if every batch succeeded.
If a batch fails, the aggregate counters become `null` with a reason: `null` is
not zero. A failed check does not replace diagnosis of the error code.

The `Valid` bit is not labelled RSS or USS. `QueryWorkingSetEx` can also query
addresses outside the ordinary working set, including AWE and large pages;
observations from this test with ordinary pages do not automatically establish
semantics for all processes or page types. The provider still reports per-region
RSS as `null`. Sources: [VirtualAlloc](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc),
[VirtualQueryEx](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex),
[QueryWorkingSetEx](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-queryworkingsetex),
[PSAPI_WORKING_SET_EX_BLOCK](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-psapi_working_set_ex_block).

A `provider.region_found = false` result may indicate a partial scan or an error
and must be read alongside `provider.complete` and `provider.reason`; it does not
mean a zero-sized allocation. The test process collects only its own data.

## Additional UI cases

1. **Accessible process:** open the test PID's map. Check that ranges are ordered,
   state and protection are readable, and per-region RSS, PSS, USS and swap remain `n/a`.
2. **Exited process:** start a new test process, select it, let it exit and press
   `r`. A reason must appear, without presenting the old sample as current.
   Do not terminate unrelated processes.
3. **Access denied:** if a process is inaccessible to the current user, only check
   opening its map and the access-denied message. Do not elevate privileges to
   turn this case into a success, and do not save private data.
4. **Terminal and return:** check 160×48 and 80×24, search, pagination, zoom,
   closing the view and the main monitor's next update.
5. **Offline capture:** open a synthetic `.rtm.json` file from Linux with `--open`,
   then press `r`: the file must stay offline, without querying its saved PID.
   See the [capture schema](schema-capture.md).

When comparing general counters with a Windows tool, compare working set with
working set and private resident memory with an equivalent measurement.
Private commit/PagefileUsage is neither on-disk swap nor USS. Record timing
differences: readings from the two programs are not atomic.

## Recording manual test results

Use **passed / failed / not run**, with a separate entry for each item. Do not
publish raw output: it contains virtual addresses and may contain other local
information. Share only a reviewed summary. The following log is for the owner's
Windows PC; it neither replaces nor summarizes automated CI results.

| Item | Result | Details |
|---|---|---|
| Windows/build, architecture, Python version | not run | |
| Test suite and general commands | not run | |
| Reserve/commit/touch/release states | not run | |
| `Valid`/coverage and error cases | not run | |
| Provider finds the controlled range | not run | |
| Exited process / access denied | not run | |
| UI, resize and monitor after closing | not run | |
| Offline replay | not run | |
| Large pages/AWE and 32/64 bit | not run | Not automatically covered by the ordinary test. |

If the test exposes an error, report the stage, exception and version. Do not
claim RSS/working-set equivalence or cross-bitness support until demonstrated.
