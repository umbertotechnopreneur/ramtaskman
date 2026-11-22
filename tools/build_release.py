"""Build and verify native x64 bundles, ZIPs, an MSI and a Debian package. No publication."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, timeout=600, **kwargs)


def smoke(executable, version):
    # A separate directory with spaces proves the bundle is independent of cwd/source.
    with tempfile.TemporaryDirectory(prefix='ramtaskman bundle check ') as folder:
        for args in (['--version'], ['--language', 'en', '--help'], ['--once', '--max-measurements', '2'],
                     ['--json', '--max-measurements', '2', '--ram-price', '320'], ['--verify-bundle']):
            result = subprocess.run([str(executable), *args], cwd=folder, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=180)
            if result.returncode:
                # Do not echo the live process report into public CI logs.
                if args == ['--verify-bundle']:
                    print(result.stderr, file=sys.stderr)
                raise RuntimeError(f'Bundle check failed: {args} (exit {result.returncode})')
            if args == ['--version']:
                assert result.stdout.strip() == version
            if '--json' in args:
                report = json.loads(result.stdout)
                assert report['measurement_attempted'] <= 2 and 'ram_valuation' in report


def collect_licenses(bundle):
    destination = bundle / 'licenses'
    destination.mkdir()
    for dist in metadata.distributions():
        # Preserve the supplied notices of every package in the build environment.
        name = dist.metadata['Name']
        for file in dist.files or []:
            if any('license' in p.lower() or 'copying' in p.lower() or p.lower() == 'authors'
                   for p in file.parts) and file.suffix.lower() not in ('.py', '.pyc'):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = destination / name / Path(*file.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    python_license = next((p for p in (Path(sys.base_prefix) / 'LICENSE.txt',
                                      Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt') if p.is_file()), None)
    if python_license is None:
        raise RuntimeError('Bundled Python license not found')
    shutil.copyfile(python_license, destination / 'PYTHON_LICENSE.txt')
    shutil.copyfile(ROOT / 'docs/images/VIBEWARE_LICENSE.txt', destination / 'VIBEWARE_LICENSE.txt')


def build():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--msi', action='store_true', help='also build an unsigned Windows MSI with WiX 5')
    parser.add_argument('--deb', action='store_true', help='also build Debian amd64 package on Linux')
    args = parser.parse_args()
    if platform.machine().lower() not in ('amd64', 'x86_64') or sys.platform not in ('linux', 'win32'):
        raise RuntimeError('Release builds currently require native x64 Linux or Windows')
    if args.deb and sys.platform != 'linux':
        parser.error('--deb requires Linux')
    if args.msi and sys.platform != 'win32':
        parser.error('--msi requires Windows')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    system = 'windows' if os.name == 'nt' else 'linux'
    work = ROOT / 'build/release' / system
    output = ROOT / 'dist/release'
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ | {'PYINSTALLER_CONFIG_DIR': str(work / 'cache')}
    icon_args = ['--icon', ROOT / 'assets/ramtaskman.ico'] if system == 'windows' else []
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--noupx', *icon_args,
         '--name', 'ramtaskman', '--distpath', work / 'dist', '--workpath', work / 'work',
         '--specpath', work, '--collect-all', 'ramtaskman', '--collect-all', 'textual',
         '--recursive-copy-metadata', 'ramtaskman', ROOT / 'tools/release_entry.py'], cwd=ROOT, env=env)
    bundle = work / 'dist/ramtaskman'
    executable = bundle / ('ramtaskman.exe' if os.name == 'nt' else 'ramtaskman')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md'):
        shutil.copyfile(ROOT / name, bundle / name)
    shutil.copyfile(ROOT / 'packaging/PORTABLE.md', bundle / 'START_HERE.md')
    collect_licenses(bundle)
    shutil.copyfile(ROOT / 'assets/ramtaskman.png', bundle / 'ramtaskman.png')
    archive = output / f'ramtaskman-{version}-{system}-x64-portable.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo.from_file(path, Path('ramtaskman') / path.relative_to(bundle))
                info.external_attr = (0o100755 if path == executable else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, path.read_bytes())
    # Verify the exact bytes users will extract, rather than just the build tree.
    with tempfile.TemporaryDirectory(prefix='ramtaskman extracted ') as directory:
        with zipfile.ZipFile(archive) as source:
            source.extractall(directory)
            if os.name != 'nt':
                for info in source.infolist():
                    Path(directory, info.filename).chmod(info.external_attr >> 16 & 0o777)
        smoke(Path(directory) / 'ramtaskman' / executable.name, version)
    if args.msi:
        msi = output / f'ramtaskman-{version}-windows-x64.msi'
        run(['wix', 'build', '-arch', 'x64', '-d', f'Version={version}',
             '-d', f'BundleDir={bundle.resolve()}',
             '-d', f'IconFile={(ROOT / "assets/ramtaskman.ico").resolve()}',
             '-pdb', work / msi.with_suffix('.wixpdb').name, '-o', msi,
             ROOT / 'packaging/windows.wxs'], cwd=ROOT)
    if args.deb:
        debian_temp = tempfile.TemporaryDirectory(prefix='ramtaskman deb stage ')
        stage = Path(debian_temp.name) / 'package'
        shutil.copytree(bundle, stage / 'opt/ramtaskman')
        binaries = stage / 'usr/bin'
        binaries.mkdir(parents=True)
        (binaries / 'ramtaskman').symlink_to('/opt/ramtaskman/ramtaskman')
        (binaries / 'rtm').symlink_to('/opt/ramtaskman/ramtaskman')
        icons = stage / 'usr/share/icons/hicolor/256x256/apps'
        icons.mkdir(parents=True)
        shutil.copyfile(ROOT / 'assets/ramtaskman-256.png', icons / 'ramtaskman.png')
        desktop = stage / 'usr/share/applications'
        desktop.mkdir(parents=True)
        shutil.copyfile(ROOT / 'packaging/ramtaskman.desktop', desktop / 'ramtaskman.desktop')
        control = stage / 'DEBIAN'
        control.mkdir()
        installed_size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file() and not p.is_symlink()) // 1024
        (control / 'control').write_text(
            f'Package: ramtaskman\nVersion: {version}\nSection: utils\nPriority: optional\n'
            f'Architecture: amd64\nInstalled-Size: {installed_size}\n'
            'Maintainer: Umberto Giacobbi <umberto.giacobbi@gmail.com>\n'
            'Depends: libc6 (>= 2.35), libgcc-s1, zlib1g\n'
            'Homepage: https://github.com/umbertotechnopreneur/ramtaskman\n'
            'Description: Terminal RAM monitor with process and application accounting\n'
            ' Self-contained Python/Textual monitor for RSS, PSS, USS and swap.\n', encoding='utf-8')
        docs = stage / 'usr/share/doc/ramtaskman'
        docs.mkdir(parents=True)
        shutil.copyfile(ROOT / 'LICENSE', docs / 'copyright')
        # Portable filesystems can report mode 777 for every file. Normalize in
        # the temporary staging filesystem before asking dpkg-deb to package it.
        for path in stage.rglob('*'):
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() or path == stage / 'opt/ramtaskman/ramtaskman' else 0o644)
        stage.chmod(0o755)
        run(['dpkg-deb', '--root-owner-group', '--build', stage, output / f'ramtaskman_{version}_amd64.deb'])
        debian_temp.cleanup()
    for path in sorted(output.iterdir()):
        if path.suffix in ('.zip', '.deb', '.msi'):
            path.with_name(path.name + '.sha256').write_text(
                hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n', encoding='ascii')
    print(f'Native {system} release built and verified: {output.relative_to(ROOT)}')


if __name__ == '__main__':
    build()
