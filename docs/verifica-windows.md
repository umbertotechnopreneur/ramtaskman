> **File name** `verifica-windows.md`<br>
> **Full path** `E:\ramtaskman\docs\verifica-windows.md`<br>
> **Relative to the repository root** `docs/verifica-windows.md`

# Native Windows verification

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

Automated native Windows checks passed in CI at the checkpoint recorded in the
[handoff](handoff.md#evidenze-e-riferimenti). The `VirtualQueryEx` provider is experimental:
it displays virtual ranges, not per-region RSS. The test uses only a controlled
allocation created by its own Python process. It does not require elevated privileges,
read other processes' memory bytes, or change system settings or the desktop session.

## Prerequisites

- Windows 10 or later, 64-bit Python >=3.11, `uv` and a copy of the project.
- PowerShell or Windows Terminal. UI checks require a terminal with color and
  resizing support.
- On a checkout shared with Linux, set `UV_PROJECT_ENVIRONMENT` to `.venv-windows`.
  The Windows launcher and the direct `uv run` commands then use the same
  Windows environment within the repository.
- The test process requires no restart, disabled protections, driver installation
  or administrator privileges.

## Verify the per-user MSI

Use a Windows x64 test account with no Ram Taskman installation. The script runs
the installer silently and removes it after verifying the installed command,
Start menu shortcut and user `PATH`. It also checks that other `PATH` entries
and the machine `PATH` are preserved.

```powershell
./tools/verify_windows_msi.ps1 -Msi ./dist/release/ramtaskman-0.1.1-windows-x64.msi -Version 0.1.1
```

For an upgrade test, pass `-PreviousMsi` with a separately built lower-version
per-user MSI and `-PreviousVersion` with its version. This repeats the checks
after Windows Installer replaces the previous product. A previous per-machine
CI installation should be removed before installing the per-user package.

## Verify from source

Set the environment and cache in each PowerShell terminal used for source checks.
From the repository root, run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) '.venv-windows'
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
$env:UV_PYTHON_DOWNLOADS = 'never'
uv run --locked python -m unittest discover -s tests -p test_localized_cli.py -v
uv run --locked python -m unittest discover -s tests -v
.\run.cmd --version
.\run.cmd --once --language en
.\run.cmd --json
```

Record the Windows version/build, system and interpreter architecture, and Python,
psutil and Textual versions. Do not copy private names or paths into public reports.
Check that RSS represents the working set and USS counts private resident memory.
Per-process PSS and swap should appear as `n/a` in the UI and `null` in JSON.

## Controlled allocation test

Use the PowerShell environment configured above and run from the repository root:

```powershell
uv run --locked python tools\verify_windows_regions.py
```

The command prints JSON **only to the terminal**, with the system version,
architecture, page size, four stages and provider result. To observe the same
allocation in the UI during the test:

```powershell
uv run --locked python tools\verify_windows_regions.py --hold-seconds 60
```

The temporary PID is printed before the wait. In a second terminal with the same
project environment, run
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

> **File name** `verifica-windows.md`<br>
> **Full path** `E:\ramtaskman\docs\verifica-windows.md`<br>
> **Relative to the repository root** `docs/verifica-windows.md`
