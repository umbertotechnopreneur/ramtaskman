# Contributing to ramtaskman

Corrections, translations, reproducible bug reports and documentation improvements
are welcome. You can use, modify and redistribute the project, including
commercially, under the [MIT license](LICENSE), preserving the required notices.
Retain the original credits and read the [third-party notices](THIRD_PARTY_NOTICES.md).

We develop and test ramtaskman on Linux and Windows. There's also an experimental
macOS backend, but we don't have a Mac, so we haven't tested or validated it.
Our CI covers Linux and Windows; the macOS notes are there for contributors who have a Mac.

## Choose a contribution

- **Bug reports:** include the version or commit, operating system, Python version,
  terminal dimensions, steps to reproduce, expected result and observed result.
  Use a synthetic example; avoid process lists, personal paths and real captures.
- **Translations:** catalogs and `help.<language>.md` files live in
  `src/ramtaskman/locales/`; localized READMEs live in `docs/i18n/`. English is the
  public documentation language, with the canonical README at the repository root.
  Preserve keys, parameters in braces, CLI options and metric names. AI-assisted
  translations need native-speaker review: identify the language you actually reviewed.
- **Code:** favor small changes with a clear problem and verifiable behavior.
  For larger changes, describe the proposal in an issue first.
- **Images:** follow the [gallery procedure](docs/images/README.md).
  Use only the app with synthetic data, and disclose any crops.

## Set up the environment

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
./run.sh --language en
```

On Windows, in Windows Terminal:

```powershell
.\run.cmd --language en
```

The launchers keep `.venv` and `.uv-cache` in the project. The first run needs
network access for dependencies. Do not share `.venv` between systems or paths.
Do not move data or caches to other disks without the computer user's agreement.

## Preserve these contracts

Read the [architecture](docs/architecture.md), [lessons](lessons.md) and
[AGENTS](AGENTS.md). `AGENTS.md` contains operational instructions for agents in
Italian; this page is the starting point for human contributors.

- Missing data: `None` in the model, `null` in JSON and `n/a` in the UI. Never invent zeros.
- RSS, PSS, USS, swap and commit are not interchangeable. Do not estimate PSS or USS from RSS.
- Preserve PID + create_time identity, coverage, error reasons and rejection of stale data.
- Do not read memory contents, cmdline, environ or private files; do not terminate processes.
- Sample outside the UI thread. Keep Python/Textual and the separation between data and presentation.
- Respect pause and manual stops. Do not log the user out, reboot or shut down the computer.

## Verify a change

Run relevant tests for functional code; run the suite before proposing a broad
change. For text-only corrections, check content and links: new application tests
are unnecessary.

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
UV_CACHE_DIR="$PWD/.uv-cache" uv build
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/verify_distribution.py
```

PowerShell equivalent:

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv run --locked python -m unittest discover -s tests -v
uv build
uv run --locked python tools/verify_distribution.py
```

For collectors and the CLI, also check `./run.sh --once` and `./run.sh --json`
(on Windows, `.\run.cmd`), without attaching private data to the issue or PR.
For the UI, use `run_test`, call `await pilot.pause()` before assertions, and
check 160×48 and 80×24. Use the gallery's synthetic captures for images.

CI is configured for Linux and Windows with Python 3.11, 3.13 and 3.14.
Always distinguish simulated tests, native CI checks and manual hardware checks.
Report only what you ran, including skips and limitations. Do not add macOS to CI.

## Propose a change

Describe the problem, result and verification in the pull request. Link the issue,
if applicable, and add synthetic screenshots for visual changes. Update the
relevant feature documentation and flag translations that still need alignment.
Do not include caches, virtual environments, credentials or personal captures.

Contributions to the project's code and documentation are proposed under MIT.
When adding third-party material, identify its source and license and retain the
applicable notices: the project license does not replace dependency licenses.
Preparing a change locally does not publish it or create a release.

`uv build` produces an installation wheel and a source archive containing guides,
images, tools, tests and the lockfile. Both include MIT and third-party notices.
The configuration uses [uv build backend inclusion rules](https://docs.astral.sh/uv/concepts/build-backend/#file-inclusion-and-exclusion);
caches and local captures remain excluded. A PyPI release is not required to
share the source under the license terms.
