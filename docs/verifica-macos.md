# macOS region verification notes

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

**Status:** this indicative procedure is retained for external contributors who
have a Mac. It has not been run on a Mac and is not maintained as an internal
verification procedure. The diagnostic tool was prepared on Linux without compiling
against a macOS SDK; mocked tests do not establish the Mac ABI.
The macOS region map is not implemented. These instructions are a starting point
to check on the contributor's system, not a commitment in the internal roadmap.

## Preparation

For a possible external contribution, use a Mac with a C compiler and macOS SDK
already installed; testing the helper's own process does not require administrator
privileges. Python >=3.11 and `uv` are also needed for the application's test suite.
The Mach diagnostic can run with standard Python, without additional Python libraries.

From the project root, copied to an authorized destination:

```bash
sw_vers
uname -m
python3 --version
cc --version
```

Record the macOS version/build, architecture, Python version and compiler version/SDK.
An ARM64 test does not automatically verify x86_64, or vice versa. If the compiler
or SDK is unavailable, stop the test and record the reason: do not install them
automatically or change system configuration. Do not use `sudo`, disable SIP,
change entitlements or end sessions.

## Mach probe: the test process only

```bash
python3 tools/verify_macos_regions.py
```

The wrapper compiles `tools/macos_region_probe.c` using **local SDK headers**:
the macOS compiler determines types and structure layouts without duplicating
the Mach ABI in ctypes. The compiler and its temporary files use a temporary
directory under the project's `captures/`, which is then removed. If `captures/`
points outside the project, the wrapper stops. It does not access the network,
mapped files or process contents: it only uses the helper's `mach_task_self()`.

The helper creates its own synthetic 8 MiB anonymous mapping, queries the region,
writes one byte per page **within its own test mapping**, queries it again,
enumerates its own regions three times and calls `munmap`. It does not use
`task_for_pid` or inspect other processes. Output is not automatically saved.
The JSON includes no addresses, PIDs, process names or mapped paths; it includes
the kernel version, architecture and Python version. Always review output before sharing it.

The probe limits each enumeration to 100,000 calls and 32 submap levels. A 30-second
timeout stops the test process; compilation has a 60-second timeout. Compilation
errors, unexpected values and reached limits are reported rather than presented
as complete measurements. No timeout promises to interrupt a single kernel call instantly.

### Interpreting the result

| Field | Check |
|---|---|
| `probe_exit_code` | 0 means the probe completed the stated checks; 1 indicates a probe error. The wrapper may exit with 2 if it cannot run. |
| `page_bytes`, `allocation_bytes` | System-reported page size and the requested 8 MiB. |
| `before_kr`, `after_kr` | 0 means the test-region query succeeded; otherwise the associated counter is null. |
| `before_resident_pages`, `after_resident_pages` | Native Mach field for the **reported region**, before/after touching the mapping. |
| `before_region_bytes`, `after_region_bytes` | Kernel-reported region size, to interpret alongside the counters. |
| `enumerations` | Three samples: leaves, submaps, calls, maximum depth, virtual total, final code and `limited`. |
| `cpu_seconds` | Helper CPU time for the three scans, not wall-clock latency or a benchmark of the whole application. |
| `rss_before_native`, `rss_after_native` | The helper's native `ru_maxrss`: the system's historical maximum, not an instantaneous RSS delta. |
| `munmap_ok` | The test mapping was released. |

The system may merge or split mappings: the returned region can contain more memory
than the individual allocation. The `pages_resident` delta is therefore not guaranteed
to be exactly 8 MiB/page size, and the difference between scans is not atomic.
Pages may change between readings. An increase consistent with touching pages is
an observation to record, not proof that the field equals Linux PSS or USS.
In `enumerations`, an expected complete result has `limited: false`, at least one
leaf and final code 1 or 3; other codes are errors and the wrapper exits with a
nonzero code. Compare sums only after verifying semantics and the absence of overlaps.

To check errors and repeatability, run the command several times, recording each
run's program result, counts and Mach codes. Investigate suspicious sustained
growth before concluding that there is a leak: the helper restarts on every run.
The probe acquires no additional task ports or Mach rights to release; the self
port is borrowed and every created mapping is released. A provider proposed by
external contributors would also require repeated tests **within the same process**
and suitable native tools to check port/handle leaks. This work is outside internal verification.

## Application and replay

An external contributor who chooses to evaluate the project on a Mac may use
these indicative commands; they are not part of CI or internal verification:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once --language en
./run.sh --json
./run.sh --language en
```

The first uv run may need network access for declared dependencies. Do not copy
the Linux `.venv`: create the environment on the destination machine. The current
macOS UI shows available general counters, but the region map is still reported
as unimplemented. Check startup, exit, 160×48 and 80×24, search, filters and the
meaning of the fallback. Do not share live `--json` output without reviewing
names, users and paths. For replay, use only synthetic files or a capture explicitly
chosen by the user; `--open file.rtm.json` must stay offline and `r` must not start
sampling the saved PID.

## Limits to assess only in a possible external contribution

- This probe does not verify reading a **child process** or denial for a protected
  process: it obtains no external task ports. That would require a separate test
  with an explicitly started and controlled child, and an authorized error test
  without forcing privileges. If the system denies access, record the code and
  context as a limitation; do not attempt to bypass it.
- The relationship between resident, private, compressed, reusable and footprint
  counters and ramtaskman's metrics needs verification with Apple sources and
  equivalent tools; PSS must not be estimated from ref_count.
- A possible external macOS provider would require native tests for task access,
  version and architecture differences, submaps and stability under cancellation.
- `test_verify_macos_probe.py` checks the wrapper and C flow with headers **mocked
  on Linux**. It does not demonstrate SDK compilation, the ABI or macOS measurements.

References: [Mach region structures, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/vm_region.h),
[mach_vm interfaces, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/mach_vm.defs),
[kern_return codes, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/kern_return.h).
