> **File:** `RELEASE_NOTES.md`<br>
> **Repository copy:** [GitHub](https://github.com/umbertotechnopreneur/ramtaskman/blob/main/packaging/RELEASE_NOTES.md)<br>
> **Relative path** (repository root): `packaging/RELEASE_NOTES.md`

Release of **ramtaskman**, the terminal RAM monitor for Linux and Windows.

- **Windows x64 ZIP:** extract the full folder and run `ramtaskman.exe` in Windows Terminal. No Python or uv required. Unsigned executable.
- **Windows x64 MSI:** unsigned, installs for all users and adds a Start menu shortcut. For silent installation, run `msiexec /i ramtaskman-<version>-windows-x64.msi /qn /norestart` as administrator.
- **Linux x64 ZIP:** extract the full folder and run `./ramtaskman`. Requires glibc 2.35+ (Debian 12+ / Ubuntu 22.04+); use `chmod +x ramtaskman` if your extractor drops executable permissions.
- **Debian amd64 `.deb`:** install with `sudo apt install ./ramtaskman_<version>_amd64.deb`, then run `ramtaskman` or `rtm`.

Use `--language en` for English. Includes ten languages, system RAM/history,
application grouping, RSS/PSS/USS where available, regions, A/B comparison and
offline captures. Enter a RAM price with `--ram-price` to see each app's share
of hardware cost. There is no automatic price feed.

All archives include Python/dependency notices and original MIT credits. Thank
you to Scott Hanselman and GPU Taskman for the original UI and inspiration.
[VibeWare manifesto](https://umbertogiacobbi.biz/vibeware/manifesto).

The release workflow runs the Linux/Windows test matrix, tests CLI and synthetic
UI/offline replay from extracted bundles, and installs/checks/removes the Debian
package on Ubuntu and the MSI on Windows. Manual testing on the owner's Windows PC is still pending.
This version is experimental; missing readings appear as `n/a`. macOS
remains experimental, untested and unvalidated, with no package or CI job.

Per-file SHA-256 checksums accompany the downloads. Source wheel and source
archive are also attached for contributors.

> **File:** `RELEASE_NOTES.md`<br>
> **Repository copy:** [GitHub](https://github.com/umbertotechnopreneur/ramtaskman/blob/main/packaging/RELEASE_NOTES.md)<br>
> **Relative path** (repository root): `packaging/RELEASE_NOTES.md`
