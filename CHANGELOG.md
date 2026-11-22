> **File name** `CHANGELOG.md`<br>
> **Full path** `E:\ramtaskman\CHANGELOG.md`<br>
> **Relative to the repository root** `CHANGELOG.md`

# Changelog

> Development and verification: Linux and Windows. macOS is experimental,
> untested and unvalidated by the project because we have no Mac available.

## 0.1.1

- Added a Windows x64 MSI for the current user, with a Start menu shortcut and
  `ramtaskman` on the user `PATH`. Uninstall removes the shortcut and `PATH` entry.
- Kept the Windows and Linux x64 portable ZIPs and Debian amd64 package.
- Added seven-day support diagnostics in About and localized the RAM valuation
  options and error messages.
- Stabilized the A/B comparison close test on Windows.

## 0.1.0 — November 17, 2026

- First native x64 portable ZIPs for Linux and Windows, plus a Debian amd64
  package. Python/dependencies and their notices are included, with SHA-256
  checksums. Release publication waits for the test matrix and bundle checks.

- README badges, VibeWare footer and manifesto link; clearer introduction to
  per-app RAM cost estimates using a price supplied by the user.
- English as the main README and public documentation language; the Italian
  README remains available through the language selector.
- Documentation reorganized with an index, contribution guide and third-party
  notices; reuse and redistribution encouraged under MIT, retaining credits.
- Source archive includes guides, images, tools, tests and lockfile; MIT and
  notices are also included in the wheel, without changing runtime dependencies.
- New cover and synthetic gallery with updated captures, A/B comparisons and
  ten languages; optional PNG rendering reproducible through the lockfile.
- Operational handoff separated from history; localized READMEs aligned with
  local RAM valuation options and the F1 About screen.
- RAM-focused terminal adaptation of gputaskman, with system and process counters
  and application grouping; upstream attribution and license in the README.
- Linux: OS category bar, PSS/RSS details and region map with filters, search,
  zoom and A/B comparison. Windows: experimental virtual ranges. macOS:
  general counters, without a region provider.
- Offline capture saving and replay, with explicit missing data.
- Optional sampling budget, paginated tables and local benchmarks.
- Windows verification procedures and macOS guidance for external contributors;
  macOS excluded from internal verification and CI.
- Local verification of isolated distributions and cross-platform CI configuration;
  no PyPI release.
- Names and executables read from native metadata, avoiding psutil's implicit
  command-line and executable-path fallbacks.
- READMEs and app text in ten languages, selected with `--language`: dashboard,
  details, regions, help, footer, CLI and backend/capture diagnostics. Identifiers,
  OS details and previously saved text retain their original form. Local Linux
  checks cover the CLI, multilingual UI, serialization and distribution;
  translations still require native-speaker review.

The README and development plan record measurement, compatibility and verification
status and limitations. Version 0.1.0 is experimental.

> **File name** `CHANGELOG.md`<br>
> **Full path** `E:\ramtaskman\CHANGELOG.md`<br>
> **Relative to the repository root** `CHANGELOG.md`
