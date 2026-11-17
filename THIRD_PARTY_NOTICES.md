# Third-party notices and components

ramtaskman is distributed under the [MIT license](LICENSE). This document records
provenance and dependencies; it does not replace their respective license texts.
Python package versions are pinned in `uv.lock`; update this list when they change.

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

## Reused code: GPU Taskman

- **Project:** [gputaskman](https://github.com/shanselman/gputaskman), Scott Hanselman.
- **Source:** commit `7486bfa0a35e032298534d9c408ff8ad96d9768a`, version 0.4.1.
- **Original copyright:** Copyright (c) 2026 Scott Hanselman.
- **License:** MIT, retained in full in `LICENSE`.
- **Reuse:** Textual styling in `app.tcss`, the `spark` and `stacked_bar` helpers
  in `widgets.py`, and the adapted UI structure in `app.py`.

The [provenance note](docs/upstream.md) details the adaptation and historical
reference, so you can trace the reused code. ramtaskman has its own development
and maintenance. No NVIDIA dependencies are included.

## Application dependencies

These are separately installed packages with their own copyright and license
notices. The ramtaskman wheel does not embed their code. Portable ZIPs and Debian packages
do bundle Python and these dependencies, with their supplied notices in `licenses/`. If you distribute a
complete environment, also retain the license texts supplied by each package.

| Component | Locked version | License | Role |
|---|---|---|---|
| [psutil](https://github.com/giampaolo/psutil) | 7.2.2 | BSD-3-Clause | Process counters and metadata |
| [Textual](https://github.com/Textualize/textual) | 8.2.8 | MIT | Terminal interface |
| [Rich](https://github.com/Textualize/rich) | 15.0.0 | MIT | Rendering and SVG captures |
| [Pygments](https://github.com/pygments/pygments) | 2.21.0 | BSD-2-Clause | Syntax highlighting |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | 4.2.0 | MIT | Markdown rendering |
| [mdit-py-plugins](https://github.com/executablebooks/mdit-py-plugins) | 0.6.1 | MIT | Markdown extensions |
| [mdurl](https://github.com/executablebooks/mdurl) | 0.1.2 | MIT | Markdown URLs |
| [linkify-it-py](https://github.com/tsutsu3/linkify-it-py) | 2.2.0 | MIT | Link recognition |
| [platformdirs](https://github.com/tox-dev/platformdirs) | 4.14.3 | MIT | Application paths used by dependencies |
| [typing-extensions](https://github.com/python/typing_extensions) | 4.16.0 | PSF-2.0 | Type annotation support |

psutil and Textual are direct dependencies; the others are transitive.
The [uv_build](https://github.com/astral-sh/uv) build backend is distributed under
MIT or Apache-2.0. It is a build tool, not an application dependency.

## Images and fonts

Application screenshots are generated from the app with synthetic data and SVG
compositions produced by the project's scripts. They contain no real process
lists, external photographs or memory contents. The UI's derivation from GPU
Taskman remains credited in these captures.

The **VibeWare logo** in `docs/images/vibeware-logo.png` is the original participation
mark by Umberto Giacobbi, copied unchanged from `Branding/vibeware-logo.png` in
[VibeWare](https://github.com/umbertotechnopreneur/VibeWare), via the local AgentInbox
asset. Copyright (c) 2026 Umberto Giacobbi, MIT; its notice is retained in
[VIBEWARE_LICENSE.txt](docs/images/VIBEWARE_LICENSE.txt). The logo opens the
[manifesto](https://umbertogiacobbi.biz/vibeware/manifesto).

- [resvg-py](https://github.com/baseplate-admin/resvg-py), version 0.5.0, MIT:
  optional PNG renderer in the `images` group; uses [resvg](https://github.com/linebender/resvg),
  distributed under MIT or Apache-2.0. It is not required to run ramtaskman.
- [DejaVu Fonts](https://dejavu-fonts.github.io/License.html): Bitstream Vera license
  with public-domain DejaVu changes; used for Latin text in images.
- [Noto CJK](https://github.com/notofonts/noto-cjk), SIL Open Font License 1.1:
  used for CJK glyphs in multilingual images.

The scripts use locally installed fonts; font files are not embedded in the
repository or PNGs. Earlier PNGs were generated with CairoSVG and Pillow.
The current procedure and image provenance are documented in the
[gallery](docs/images/README.md).

## Reuse and redistribution

You may copy, modify and redistribute the project's code and documentation,
including commercially, under MIT. Retain the copyright and permission notice
in copies or substantial portions of the software. Preserve the notices for
third-party components actually included in your distribution.
The software is provided without warranty, as stated in `LICENSE`.

## Portable packaging

[PyInstaller](https://pyinstaller.org/), pinned in the optional `release` group,
builds self-contained native folders. It is GPL-2.0-or-later with the PyInstaller
bootloader exception permitting distribution of bundled applications under their
own license; its notice is included with the portable packages. Python retains
its PSF license and bundled notices in `licenses/PYTHON_LICENSE.txt`.
The packaging environment's supplied license files are copied into `licenses/`;
this does not change ramtaskman's original MIT license.
