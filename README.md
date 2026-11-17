# ramtaskman

[![CI](https://github.com/umbertotechnopreneur/ramtaskman/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/umbertotechnopreneur/ramtaskman/actions/workflows/ci.yml)
![Platform: Windows and Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-0078D4)
[![License: MIT](https://img.shields.io/badge/license-MIT-2EA44F)](LICENSE)

[English](README.md) · [Italiano](docs/i18n/README.it.md) · [中文（简体）](docs/i18n/README.zh.md) · [한국어](docs/i18n/README.ko.md) · [Français](docs/i18n/README.fr.md) · [Tiếng Việt](docs/i18n/README.vi.md) · [Español](docs/i18n/README.es.md) · [Português](docs/i18n/README.pt.md) · [Deutsch](docs/i18n/README.de.md) · [日本語](docs/i18n/README.ja.md)

### See where your RAM goes, right from the terminal.

**ramtaskman** is an experimental memory monitor developed and tested on Linux and
Windows. It grew from a desire to understand RAM across different systems without
having to reach for complicated tools. It is a **[VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto)** project: a personal
idea born from curiosity and research, developed into a useful everyday tool.

**Put a price on each app's RAM usage.** Enter today's price for your RAM to
see a simple estimate of each app's share of that hardware cost.

There's also an experimental macOS backend. We don't have a Mac, so we haven't
tested or validated it. Our own testing and CI cover Linux and Windows.

[Get started](#get-started) · [User guide](docs/guida.md) · [Documentation](docs/README.md) · [Contribute](CONTRIBUTING.md) · [MIT](LICENSE)

![ramtaskman dashboard and applications with synthetic demonstration data](docs/images/cover.png)

*Textual running on Linux: an excerpt of the dashboard and table with synthetic
data. The surrounding frame is a graphic composition; macOS remains experimental
and unvalidated.*

## Get started

[Windows portable ZIP](https://github.com/umbertotechnopreneur/ramtaskman/releases/download/v0.1.0/ramtaskman-0.1.0-windows-x64-portable.zip) · [Linux portable ZIP](https://github.com/umbertotechnopreneur/ramtaskman/releases/download/v0.1.0/ramtaskman-0.1.0-linux-x64-portable.zip) · [Debian .deb](https://github.com/umbertotechnopreneur/ramtaskman/releases/download/v0.1.0/ramtaskman_0.1.0_amd64.deb) · [Latest release](https://github.com/umbertotechnopreneur/ramtaskman/releases/latest)

**Portable packages include Python and dependencies.** Extract the full ZIP and
run `ramtaskman.exe --language en` on Windows or `./ramtaskman --language en` on
Linux. The x64 Linux packages require glibc 2.35+ (Debian 12+ / Ubuntu 22.04+).
For Debian, use `sudo apt install ./ramtaskman_0.1.0_amd64.deb`.
See the [package instructions](packaging/PORTABLE.md) for details and checksums in
the release downloads. The Windows executable is unsigned.

Prefer running from source? Follow the steps below.

Requires **Python 3.11 or later** and [uv](https://docs.astral.sh/uv/). Linux requires
`/proc` and `smaps_rollup`. The launchers keep the environment and cache inside the
project directory; the first run needs network access to install dependencies.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh --language en
```

On Windows, open **Windows Terminal** in the project directory and run:

```powershell
.\run.cmd --language en
```

For one sample or JSON output, use `./run.sh --once --language en` or
`./run.sh --json` on Linux, or `.\run.cmd --once --language en` and
`.\run.cmd --json` on Windows. The Unix commands also remain available for the
experimental, untested macOS backend. The project is not published on PyPI.
Do not share a `.venv` between operating systems; recreate it locally after moving
the project to a different system or path.

The app supports ten languages. `--language` selects the interface, footer, help,
CLI and human-readable `--once` report language; without this option, the current
default is Italian. Available codes: `it`, `en`, `zh` (Simplified Chinese), `ko`,
`fr`, `vi`, `es`, `pt`, `de`, `ja`. For example, use `./run.sh --language zh --once`
or `.\run.cmd --language ko`. App-generated technical messages are translated too.
Identifiers and the JSON schema remain stable; OS details and text stored in
captures retain their original language.

Local verification covers Linux with Python 3.14.4: synthetic UI at 160×48 and
80×24, CLI, builds, isolated installation and replay. Native Windows checks run
in CI; manual testing on a personal Windows PC is still pending. macOS is excluded
from project verification. Translations still need native-speaker review.

**Useful keys:** `m` switches modes, `g` toggles applications/processes, `/` searches,
`f` filters, `d` opens details, `r` opens regions, `?` explains metrics and `q` quits.
The [user guide](docs/guida.md) covers all controls.

## What you can do

1. **See RAM at a glance.** System memory bar, available memory, cache and history
   charts in a terminal UI, with Slim and Full diagnostics modes.
2. **Explore applications and processes.** Switch between groups and individual
   PIDs, sort available metrics and check measurement coverage.
3. **Understand the metrics.** Inspect RSS and USS; on Linux, also PSS, swap and
   SwapPSS, with component details and reasons for missing values.
4. **Find what you need.** Search by name, executable or PID and filter by user,
   swap use or partial data.
5. **Browse memory regions.** Explore process mappings, virtual addresses and
   residency on Linux; the Windows virtual-address view is experimental.
6. **Compare and save captures.** Pin sample A, collect B and compare changes;
   save and reopen captures locally, including offline.
7. **Estimate each app's RAM cost.** Use a current RAM price you enter to turn
   memory usage into a share of hardware cost, optionally spread over months.

## Explore memory

Full diagnostics separates system RAM from the USS of applications with complete
readings. The region map shows counters and virtual addresses; A/B comparisons
help identify changes between two captures.

![Full diagnostics panel showing system RAM and USS for applications with complete readings](docs/images/full-diagnostics.png)

*An excerpt of the actual diagnostics panel with synthetic data. Areas represent
memory consumption, not physical addresses; process readings may be incomplete.*

[Full view](docs/images/overview.png) · [Regions](docs/images/regions-resident.png) · [A/B comparison](docs/images/regions-comparison.png) · [Ten languages](docs/images/multilingual.png)

The [gallery](docs/images/README.md) includes every image, its provenance and the
commands to regenerate it. Process names, paths and numbers are synthetic, not
measurements of the development computer.

## RAM value and monthly allocation

```bash
./run.sh --language en --ram-price 320 --ram-currency EUR
./run.sh --language en --ram-price 320 --ram-currency EUR --ram-months 36
./run.sh --json --ram-price 320 --ram-months 36
```

You supply the price of all RAM in the machine: there is no automatic price lookup
or network request. Capacity defaults to RAM visible to the operating system,
which may be lower than the nominal installed capacity. For a nominal 32 GiB kit,
you can specify `--ram-capacity-gib 32`.

Value = price × attributable bytes / capacity. `--ram-months` divides this value
by the chosen number of months. This allocates hardware cost; it is not a bill,
energy consumption or guaranteed savings. The current allocation is not a monthly average.

Linux uses PSS, which apportions shared pages. Windows uses USS, so only private
resident memory is valued; shared memory is excluded. There is no RSS fallback.
Incomplete or unmeasurable groups remain n/a (`null` in JSON). Do not add application
values to those of their member processes or to system memory. Cache, kernel
memory and inaccessible processes are not arbitrarily attributed to Windows or
other applications. Samples are sequential, not atomic.

The value column follows current measurements during monitoring; the inspector
identifies the metric used. JSON adds `ram_valuation` only when requested.

Press **F1** for About: VibeWare, Umberto Giacobbi, website, thanks to Scott Hanselman
and references to the MIT provenance. Esc closes About without stopping monitoring.

## Understanding the readings

This is still an experimental project. Measurements are taken one after another,
so they won't all describe the same instant. Permissions can limit what we can
see, and application grouping is a best effort. Missing readings appear as **n/a**.

| | Linux | Windows | macOS (experimental, untested) |
|---|---|---|---|
| System RAM, RSS and USS | Available | Available | Backend present, unvalidated |
| PSS and per-process swap | Available when readable | n/a | n/a |
| Region map | `smaps`, on demand | Virtual ranges, experimental | Not yet available |
| Project verification | Local suite and checks | Suite and native CI checks | Out of scope: no Mac available |

PSS is not total system RAM usage; RSS may count shared pages more than once.
Cache and available memory overlap. Per-process swap is not inferred from commit.
Bars represent consumption shares, not physical addresses. Further details and
limitations are in the [guide](docs/guida.md) and [counter audit](docs/audit-contatori-piattaforma.md).

## Use, modify, share

You can use, copy, modify and redistribute ramtaskman, including commercially,
under the [MIT license](LICENSE). Preserve the copyright and permission notice
in copies or substantial portions of the software. The software is provided
without warranty, as stated in the license.

Corrections, translations, reports and improvements are welcome:
[how to contribute](CONTRIBUTING.md). For dependencies and reused code, see the
[third-party notices](THIRD_PARTY_NOTICES.md).

## Inspiration and thanks

**Thank you to [Scott Hanselman](https://github.com/shanselman) and
[GPU Taskman](https://github.com/shanselman/gputaskman)**: its terminal interface
and project inspired ramtaskman. This is an independent RAM-focused adaptation
that reuses parts of the original UI. The [provenance notes](docs/upstream.md)
explain where those parts came from and how they were adapted.

Distributed under the [MIT license](LICENSE), with the original copyright retained.

Translations were prepared with AI assistance. Corrections from translators and
native speakers are welcome.

---

### This is VibeWare · [Manifesto](https://umbertogiacobbi.biz/vibeware/manifesto)

I created ramtaskman with AI assistance, building on Scott Hanselman's GPU Taskman.
I define its purpose, guide the implementation, and take responsibility for checking
functionality, performance, and security. VibeWare is my initiative for building
useful software openly with AI; I ask you to judge the result and the evidence behind it.

To learn what VibeWare means and why I created it, read the
[VibeWare manifesto](https://umbertogiacobbi.biz/vibeware/manifesto).

[ramtaskman on GitHub](https://github.com/umbertotechnopreneur/ramtaskman) · [VibeWare on GitHub](https://github.com/umbertotechnopreneur/VibeWare) · [umbertogiacobbi.biz](https://umbertogiacobbi.biz)

*You are welcome to explore, adapt and share ramtaskman under the MIT license,
keeping the original credits — my contribution to the developer community.*

[Terms](https://umbertogiacobbi.biz/terms/) · [Privacy](https://umbertogiacobbi.biz/privacy/)

<p align="right">
  <a href="https://umbertogiacobbi.biz/vibeware/manifesto">
    <img src="docs/images/vibeware-logo.png" alt="VibeWare — read the manifesto" width="160">
  </a><br>
  <strong>VibeWare</strong><br>
  <em>Human intent, AI execution, and plenty of tokens</em>
</p>
