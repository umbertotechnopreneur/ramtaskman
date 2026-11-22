> **File name** `PORTABLE.md`<br>
> **Full path** `E:\ramtaskman\packaging\PORTABLE.md`<br>
> **Relative to the repository root** `packaging/PORTABLE.md`

# Start ramtaskman

These x64 packages include Python and the application dependencies. They need
no separate Python, uv or .NET installation. ARM64 packages are unavailable.

## Windows ZIP

Extract the entire ZIP, keep `_internal` beside `ramtaskman.exe`, and open
Windows Terminal or PowerShell in the extracted `ramtaskman` folder:

```powershell
.\ramtaskman.exe --language en
.\ramtaskman.exe --language en --ram-price 320 --ram-currency EUR
```

Built on Windows x64. Use Windows 10 or later. The executable is unsigned;
Windows may ask whether you want to run it.

## Windows MSI

The unsigned x64 MSI installs for the current user under
`%LOCALAPPDATA%\Ram Taskman`. It adds a Start menu shortcut and updates the user
`PATH`. Open a new terminal from the Start menu after installation. Double-click
the MSI to use the basic Windows Installer progress window. To install silently,
run this from a regular PowerShell session:

```powershell
msiexec /i .\ramtaskman-<version>-windows-x64.msi /qn /norestart
```

Uninstall it from Installed apps or with `msiexec /x <msi-path> /qn /norestart`.
Removal deletes the shortcut and the installer’s entry in the user `PATH`.
Windows may warn that the package is unsigned. An MSI with a higher three-part
version upgrades an existing per-user installation. If you installed an older
per-machine MSI from CI, uninstall that build before installing the per-user MSI.

## Linux ZIP

Extract the entire ZIP and keep `_internal` beside `ramtaskman`. In a terminal:

```bash
chmod +x ramtaskman
./ramtaskman --language en
```

Built on Ubuntu 22.04 x64; requires glibc 2.35 or newer, such as Debian 12+ or
Ubuntu 22.04+. Linux needs `/proc` and `smaps_rollup`. Alpine/musl is not supported.
The executable directory must allow execution. No administrator access is needed.

## Debian package

On Debian 12+ or Ubuntu 22.04+ amd64:

```bash
sudo apt install ./ramtaskman_0.1.1_amd64.deb
ramtaskman --language en
```

The app lives in `/opt/ramtaskman`; `ramtaskman` and `rtm` are available on PATH.
Remove it with `sudo apt remove ramtaskman`. Installation never starts the app,
changes the desktop session or enables a background service.

## Useful options

`--once` prints one report; `--json` prints structured data. `--language en` selects
English; ten interface languages are included. Enter your own RAM price with
`--ram-price`, optionally using `--ram-months` to spread the hardware value over
months. Prices are not fetched automatically.

`--verify-bundle` checks the bundled interface and offline replay using synthetic
data; it does not read the computer's process list.

CI builds the Windows MSI, both portable ZIPs and the Debian package on branch
pushes and pull requests; they are retained as workflow artifacts. A matching
version tag publishes verified assets. Local package builds are optional.

This release is experimental. Automated tests cover Linux and Windows. macOS is experimental,
untested and unvalidated by this project and has no release package.

MIT and original Scott Hanselman credits are preserved in `LICENSE` and
`THIRD_PARTY_NOTICES.md`. Bundled components retain their own notices in `licenses/`.

> **File name** `PORTABLE.md`<br>
> **Full path** `E:\ramtaskman\packaging\PORTABLE.md`<br>
> **Relative to the repository root** `packaging/PORTABLE.md`
