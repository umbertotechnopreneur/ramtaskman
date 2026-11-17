# Provenance

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

- Repository: <https://github.com/shanselman/gputaskman>
- Source commit: `7486bfa0a35e032298534d9c408ff8ad96d9768a`
- Version declared in the source: 0.4.1
- Acquired: November 16, 2026
- Original author: Scott Hanselman
- License: MIT, retained in full in [LICENSE](../LICENSE).

Dependencies and image tools are listed in the [third-party notices](../THIRD_PARTY_NOTICES.md).
See [CONTRIBUTING](../CONTRIBUTING.md) for how to propose changes.

The repository was cloned with its complete history. RAM development is on the
`codex/ramtaskman-foundation` branch. The `upstream` remote identifies only the
public source; pushing to it is disabled.

## What was reused

- `src/ramtaskman/app.tcss`: the `GpuTaskManager` CSS block copied from the source.
- `src/ramtaskman/widgets.py`: the `spark` and `stacked_bar` functions copied from the source.
- `src/ramtaskman/app.py`: the same Textual panel composition, striped table,
  inspector, footer and help screen; charts adapted from the original grid.
- The `src/`, `tests/`, `tools/`, `docs/`, `pyproject.toml`, `uv.lock` and CI
  organization was retained, with Linux/Windows RAM backends and an experimental
  macOS backend. Current CI checks Ubuntu and Windows with Python 3.11, 3.13 and 3.14.

GPU collectors, runtime/model scanners, automatic releases and GPU/Nix packaging
were removed from the RAM version. No NVIDIA dependencies remain. The RAM
collector, models, reports and tests are specific to the new project.

The original source remains accessible in Git without keeping another active copy:

```bash
git show 7486bfa0a35e032298534d9c408ff8ad96d9768a:src/gputaskman/app.py
```

The UI retains the structure and styling with adapted content. A pixel-for-pixel
replica of every GPU view has neither been verified nor planned for the different
RAM metrics.
