> **File name** `RELEASE_NOTES.md`<br>
> **Full path** `E:\ramtaskman\packaging\RELEASE_NOTES.md`<br>
> **Relative to the repository root** `packaging/RELEASE_NOTES.md`

**ramtaskman 0.1.1** adds a per-user Windows installer. The Linux and Windows
packages include Python and the app dependencies. No .NET installation is needed.
Native packages target x64.

- **Windows x64 ZIP:** extract the full folder and run `ramtaskman.exe` in Windows Terminal. No Python or uv required. Unsigned executable.
- **Windows x64 MSI** installs for the current user under `%LOCALAPPDATA%\Ram Taskman`, adds a Start menu shortcut and updates the user `PATH`. Open a new terminal after installing. The MSI is unsigned. For a silent install, run `msiexec /i ramtaskman-0.1.1-windows-x64.msi /qn /norestart`. If you previously installed a per-machine CI build, remove it first.
- **Linux x64 ZIP:** extract the full folder and run `./ramtaskman`. Requires glibc 2.35+ (Debian 12+ / Ubuntu 22.04+); use `chmod +x ramtaskman` if your extractor drops executable permissions.
- **Debian amd64 `.deb`:** install with `sudo apt install ./ramtaskman_<version>_amd64.deb`, then run `ramtaskman` or `rtm`.

Use `--language en` for English. Includes ten languages, system RAM/history,
application grouping, RSS/PSS/USS where available, regions, A/B comparison and
offline captures. Enter a RAM price with `--ram-price` to see each app's share
of hardware cost. There is no automatic price feed.

All archives include Python/dependency notices and original MIT credits. Thank
you to Scott Hanselman and GPU Taskman for the original UI and inspiration.
[VibeWare manifesto](https://umbertogiacobbi.biz/vibeware/manifesto).

The release workflow runs the Linux/Windows test matrix, verifies the extracted
ZIPs, checks the installed Debian package, and verifies installation, user `PATH`,
the Start menu shortcut and removal of the Windows MSI.
This version is experimental; missing readings appear as `n/a`. macOS
remains experimental, untested and unvalidated, with no package or CI job.

Per-file SHA-256 checksums accompany the downloads. Source wheel and source
archive are also attached for contributors.

> **File name** `RELEASE_NOTES.md`<br>
> **Full path** `E:\ramtaskman\packaging\RELEASE_NOTES.md`<br>
> **Relative to the repository root** `packaging/RELEASE_NOTES.md`
