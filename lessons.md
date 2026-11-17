# Verified lessons

> Development and verification cover Linux and Windows. macOS is experimental,
> untested and unvalidated by the project because we do not have a Mac. Historical
> experiments documented elsewhere do not validate the platform.

## Unreadable memory does not mean zero

The local scan without elevated privileges found many processes whose smaps_rollup
could not be accessed. The UI must preserve n/a and display coverage. A group total
with a missing member is not complete: `test_incomplete_group_does_not_claim_complete_total`
checks this contract.

## Cache and available memory overlap

MemAvailable includes reclaimable memory. It is not a segment in the OS category bar:
use MemFree for free RAM and Cached − Shmem to separate file cache from shmem.
Do not add Slab to its SReclaimable/SUnreclaim children. Categories plus the residual
must add up to MemTotal; inconsistent samples carry an explicit reason and fall
back to used/available. Checks are in test_system_segments.py and test_memory.py.

## Windows commit is neither swap nor private resident RAM

The psutil 7.2.2 source distinguishes RSS/working set and USS from private/pagefile/commit.
The Windows backend uses memory_full_info().uss and leaves per-process PSS/swap
as None; test_windows_uss_is_not_commit_and_swap_is_not_pagefile protects this distinction.
Reference: Microsoft's PROCESS_MEMORY_COUNTERS_EX documentation, linked from the
[counter audit](docs/audit-contatori-piattaforma.md).

## Searching for a helper must preserve the application's total

Building aggregates before filtering prevents a search for a PID or helper from
making its usage appear to be the application's total. Filters select whole groups;
in the drilldown, they select processes. Filter and UI tests check this distinction.

## Instance identity is more precise than the program name

An explicit systemd application cgroup may contain helpers with different executables.
The full path identifies the instance; its display name may match other instances.
Do not aggregate solely by label, across the whole session or across different UIDs.
The parser and tests in grouping.py/test_grouping.py check these boundaries.

## Textual workers belong to the application's manager

`screen.workers` is the global manager, not a manager isolated to the screen.
To stop an on-demand read, use `cancel_node(screen)`: `cancel_all()` would also
interrupt the main monitor. The closing test in test_region_ui.py checks that
the application's worker stays active while the region worker receives cancellation.
For keyboard-scrollable details, use a VerticalScroll: making a plain Static
focusable does not make it scrollable.

## Localize presentation without rewriting data

Application messages preserve their keys and parameters until they reach the UI.
Tests check nesting, deep copying through `dataclasses.asdict` and canonical JSON;
names, paths, OS details and text reopened from captures remain literal.
Textual checks in all ten languages verify the rendered footer and ensure that
a later application does not change previous applications' bindings. State assertions
must follow the selected catalog while continuing to verify stale-data rejection
and partial coverage when wording changes.

## Check dependency fallbacks too

The absence of explicit `cmdline()` calls in the project is not enough: psutil 7's
public name and executable APIs may use it as a fallback. The native metadata
adapter isolates this internal dependency, with explicit missing values when
it is unavailable. Tests forbid public getters and executable-file probes;
public caches are not used as fresh proof of identity.
