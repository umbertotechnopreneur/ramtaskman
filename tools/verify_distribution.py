"""Verifica locale della distribuzione; nessun upload e soli dati sintetici nel replay.

Da repository: UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/verify_distribution.py
Richiede che `uv build` sia già stato eseguito e che le dipendenze siano nella cache uv.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('app.tcss', 'capture_io.py', 'capture_models.py', 'comparison.py',
            'delta_bar.py', 'region_provider.py', 'region_screen.py', 'replay.py',
            'backends/windows_regions.py')
FORBIDDEN = {'.uv-cache', '.venv', 'captures', 'recordings', '__pycache__'}


def _check_names(names, *, wheel: bool) -> None:
    clean = [name.replace('\\', '/') for name in names]
    for name in clean:
        parts = set(name.split('/'))
        if parts & FORBIDDEN or any(part.startswith('.venv-') or part == '.env' or part.startswith('.env.') for part in parts):
            raise ValueError('Contenuto locale non ammesso nel pacchetto')
    for file in REQUIRED:
        suffix = ('ramtaskman/' if wheel else '/src/ramtaskman/') + file
        if not any(name.endswith(suffix) for name in clean):
            raise ValueError(f'File richiesto mancante: {file}')
    if not any(name.endswith('/LICENSE') or name.endswith('/licenses/LICENSE') for name in clean):
        raise ValueError('Licenza mancante nel pacchetto')


def _run(command, *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180)
    if result.returncode:
        # The monitor may have printed real process names: do not echo output.
        raise RuntimeError(f'Comando di verifica terminato con codice {result.returncode}: {Path(command[0]).name}')
    return result


def verify() -> None:
    wheels = list((ROOT / 'dist').glob('ramtaskman-*.whl'))
    sdists = list((ROOT / 'dist').glob('ramtaskman-*.tar.gz'))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError('Serve esattamente un wheel e un sdist in dist/: scegliere la versione da verificare')
    with zipfile.ZipFile(wheels[0]) as archive:
        _check_names(archive.namelist(), wheel=True)
    with tarfile.open(sdists[0], 'r:gz') as archive:
        _check_names(archive.getnames(), wheel=False)
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['UV_CACHE_DIR'] = str(ROOT / '.uv-cache')
    env['UV_PYTHON_DOWNLOADS'] = 'never'
    env['PYTHONUTF8'] = '1'
    with tempfile.TemporaryDirectory(prefix='.venv-dist-check-', dir=ROOT) as folder:
        base = Path(folder)
        venv = base / 'ambiente con spazi'
        _run(['uv', 'venv', '--python', sys.executable, str(venv)], cwd=base, env=env)
        python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        executable = venv / ('Scripts/ramtaskman.exe' if os.name == 'nt' else 'bin/ramtaskman')
        _run(['uv', 'pip', 'install', '--offline', '--python', str(python), str(wheels[0])], cwd=base, env=env)
        output = _run([str(executable), '--json', '--max-measurements', '2'], cwd=base, env=env)
        document = json.loads(output.stdout)
        if document.get('measurement_attempted', 0) > 2:
            raise RuntimeError('Budget ignorato nella distribuzione installata')
        _run([str(executable), '--once'], cwd=base, env=env)
        _run([str(executable), '--version'], cwd=base, env=env)
        # Use only synthetic in-memory regions, assert replay never creates a live provider.
        code = '''
import asyncio, time
from unittest.mock import patch
from ramtaskman.regions import MemoryRegion, RegionSnapshot
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.capture_io import save_capture, load_capture
from ramtaskman.replay import ReplayApp
from ramtaskman import cli
r = MemoryRegion(0x1000, 0x2000, rss=0, pss=None)
s = RegionSnapshot(42, 1.0, 'demo', time.time(), [r], executable_identity='/demo/app')
c = freeze_snapshot(s, collection_session_id='test', sequence=1, executable_identity='/demo/app')
save_capture('test.rtm.json', c)
c = load_capture('test.rtm.json').current
with patch('ramtaskman.cli.Collector', side_effect=AssertionError('live')), \\
     patch('ramtaskman.replay.ReplayApp.run') as run, \\
     patch('sys.argv', ['ramtaskman', '--open', 'test.rtm.json']):
    assert cli.main() == 0
    run.assert_called_once()
async def check():
    with patch('ramtaskman.region_screen.make_region_provider', side_effect=AssertionError('live')):
        app = ReplayApp(c)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.screen.offline and app.screen.current_capture.regions[0].rss == 0
            await pilot.press('r', 'q')
            await pilot.pause()
asyncio.run(check())
'''
        _run([str(python), '-c', code], cwd=base, env=env)
    print('Distribuzione verificata: archivi, installazione isolata, CLI e replay sintetico offline.')


if __name__ == '__main__':
    try:
        verify()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f'Verifica distribuzione fallita: {error}', file=sys.stderr)
        raise SystemExit(1) from error
