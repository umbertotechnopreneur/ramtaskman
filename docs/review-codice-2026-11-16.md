# Code review — November 16, 2026

> Development and verification cover Linux and Windows. macOS is experimental,
> untested and unvalidated by the project because we do not have a Mac.
> Historical macOS attempts do not change this policy.

Local review of collectors, models, aggregation, platform counters, region reading,
comparison, captures and replay, the Textual interface, launchers, distribution
checks and CI. Native checks performed during this review were on Linux; code
inspection and mocks do not replace Windows/macOS hardware checks.

## Fixes made

- Distribution verification now reuses the caller's cache and prepares dependencies
  from the lockfile with `uv sync --offline --no-install-project` before installing
  and checking the wheel. The previous `uv pip install --offline` failed with a
  freshly populated cache because index metadata was missing. The case was reproduced
  and verified with an isolated cache and environment inside the project.
- CI no longer cancels the other systems after the first matrix failure.
- Capture saving enforces the limit during JSON encoding, before creating or
  replacing files, avoiding an allocation proportional to a document far beyond
  the permitted limit.
- On Windows/macOS, a successful `memory_full_info` reading clears a previous RSS
  error that no longer applies; if both readings fail, it preserves both reasons.
  The hardware equivalents remained to be verified at this checkpoint.
- Unix executable names preserve valid backslashes in filenames; Windows names
  continue to follow Windows rules, including in mocked tests.
- Bars and maps calculate margins in terminal cells, so double-width characters
  do not expand the drawing beyond the available width.
- The region map immediately clears stale RAM context after a main-sampling error
  and updates it when a new sample arrives.
- Search and category legends use labels in the selected language. Unknown category
  names from captures remain literal.
- Separate UTF-8 catalogs for each language replace very long positional rows.
  Tests check keys and placeholders, and wheel verification checks that catalogs
  are included. Unused imports were removed and several contracts and steps in
  sampling and saving functions were clarified.

## Remaining work

1. **Localization verification.** Later checkpoints extend the catalogs to screens
   and application messages, including footers, CLI and diagnostics. The contract
   separates keys and parameters from presentation while preserving arbitrary
   data and operating-system details. Subsequent local verification covers layout,
   bindings, CLI errors, serialization and resource inclusion on Linux with
   Python 3.14.4. Translations still need native-speaker review.
2. **Performance with very large workloads.** Comparison runs in a worker, but
   filtering, sorting and parts of region-table rendering are still synchronous.
   Measurements and limits are in [benchmark.md](benchmark.md); moving more work
   to workers would require cancellation and stale-result handling.
3. **Screen responsibilities.** `RegionScreen` combines asynchronous reading,
   filtering, pagination, comparison, rendering and saving. Pure presentation
   functions and asynchronous operations should be separated in small increments,
   preserving tests for selection, generations and worker shutdown.
4. **Validation on maintained systems.** All six Linux and Windows jobs with Python
   3.11, 3.13 and 3.14 passed, including native Windows checks on the runners.
   Manual checks on a Windows PC remain separate from CI. macOS is excluded from
   internal verification at the user's request and because no hardware is available.

The isolated Ruff check for syntax and name/import errors (`F,E9`) passed.
A scan using the host's Ruff configuration also reported many style rules and
executable permissions on the portable filesystem. No indiscriminate automatic
fixes were applied, and those findings were not treated as bugs.

The Linux suite ran 193 tests with three native Windows tests skipped; additional
checks for localized details and bar widths then passed separately. Synthetic
captures were regenerated; `--once`, `--json`, build, wheel installation and replay
were checked in an isolated environment backed by a fresh cache. No new GitHub
Actions result was obtained for these local changes.

## Subsequent checkpoint without tests

At the user's request, the next increment was prepared and published as a checkpoint
without running new tests, lint, builds, captures or application launches. The
results above apply to the earlier work. Help files became Markdown resources
for all ten languages; OS diagnostics and further detail/comparison text use
the catalogs. The platform-counter helper reduces the main dashboard method;
table rows use explicit variables for values, coverage and identity. Those latest
changes still needed subsequent verification. The commits contain `[skip ci]`.

The last increment completes footer descriptions and application text for the
CLI, `--once` report, inspector, collectors, providers, comparison and captures
in all ten languages. Structured messages retain Italian text compatible with
the model and JSON, and are translated at the UI boundary; OS details and reasons
already recorded in files remain unchanged. No new tests, lint, builds, captures
or application launches were run for that increment either.

## Subsequently authorized verification

The user then requested tests. Twenty-two tests were added for the CLI, structured
diagnostics and UI in all ten languages. Two assertions in the previous suite
expected old wording: they were updated to catalog messages while preserving
checks for discarded data and partial samples. Targeted runs passed without
requiring application-code changes. The Linux launcher, synthetic captures,
build, isolated installation, replay and Ruff `F,E9` check also succeeded.
Details and the overall result are in the
[archived handoff](history/2026-11-16.md#verifica-richiesta-dopo-il-checkpoint-multilingua) (Italian).
