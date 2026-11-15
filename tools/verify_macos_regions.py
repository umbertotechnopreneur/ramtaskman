"""Build and run a self-only Mach probe using the local macOS SDK.

The executable is short-lived and created below the project, then removed.
No attached target process, task_for_pid or live application memory is accessed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools' / 'macos_region_probe.c'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Verifica macOS Mach sul solo processo di prova.')
    parser.add_argument('--cc', default='cc', help='compilatore C locale con SDK macOS (default: cc)')
    args = parser.parse_args(argv)
    if sys.platform != 'darwin':
        print('Verifica non eseguita: richiede macOS e un SDK C nativo.', file=sys.stderr)
        return 2
    cc = shutil.which(args.cc)
    if cc is None:
        print('Verifica non eseguita: compilatore C/SDK non trovato.', file=sys.stderr)
        return 2
    scratch = ROOT / 'captures'
    scratch.mkdir(exist_ok=True)
    if not scratch.is_dir() or scratch.resolve().parent != ROOT.resolve():
        print('Verifica non eseguita: captures deve essere una directory locale del progetto.', file=sys.stderr)
        return 2
    try:
        with tempfile.TemporaryDirectory(prefix='macos-probe-', dir=scratch) as temp:
            local = Path(temp)
            # Keep compiler temporary files and module cache on the authorized project disk.
            env = os.environ.copy()
            env['TMPDIR'] = str(local)
            env['CLANG_MODULE_CACHE_PATH'] = str(local / 'clang-cache')
            binary = local / 'macos-region-probe'
            build = subprocess.run([cc, '-std=c11', '-D_DARWIN_C_SOURCE', '-O2', '-Wall', '-Wextra',
                                    str(SOURCE), '-o', str(binary)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   timeout=60, env=env, check=False)
            if build.returncode:
                print('Compilazione probe non riuscita; verifica SDK e compilatore locali.', file=sys.stderr)
                print(build.stderr[-4000:], file=sys.stderr)
                return 2
            result = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=30, env=env, check=False)
            try:
                data = json.loads(result.stdout)
            except (ValueError, UnicodeError):
                print('Il probe non ha restituito JSON valido.', file=sys.stderr)
                print(result.stderr[-4000:], file=sys.stderr)
                return 1
            if not isinstance(data, dict) or data.get('probe') != 'macos-self-region':
                print('Risposta del probe non riconosciuta.', file=sys.stderr)
                return 1
            # Results contain no virtual addresses, process names, mapped paths or process IDs.
            data['os'] = platform.system()
            data['os_release'] = platform.release()
            data['architecture'] = platform.machine()
            data['python'] = platform.python_version()
            data['probe_exit_code'] = result.returncode
            print(json.dumps(data, ensure_ascii=False, indent=2))
            if result.stderr:
                print(result.stderr[-4000:], file=sys.stderr)
            return 0 if result.returncode == 0 else 1
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f'Verifica non eseguita o interrotta: {type(error).__name__}: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
