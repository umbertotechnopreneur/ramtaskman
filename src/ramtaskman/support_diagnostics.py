"""Local, bounded support diagnostics. No process names, paths or memory data."""

from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from urllib.parse import quote, urlencode

APP_ID = 'RamTaskMan'
SUPPORT = 'hello@umbertogiacobbi.biz'
DAILY_LIMIT = 2 * 1024 * 1024
HISTORY = timedelta(days=7)
LOG_NAME = re.compile(r'VibeWare-[0-9]{8}\.log')
LOCK = Lock()


def _app_directory() -> Path:
    return Path(os.environ['LOCALAPPDATA']) / 'VibeWare' / APP_ID


def _log_files(directory: Path):
    return (path for path in directory.glob('VibeWare-*.log')
            if LOG_NAME.fullmatch(path.name) and not path.is_symlink())


def record(event: str, error_type: str | None = None) -> None:
    """Record only caller-selected events and exception type names on Windows."""
    if os.name != 'nt' or 'LOCALAPPDATA' not in os.environ:
        return
    timestamp = datetime.now(UTC)
    directory = _app_directory() / 'logs'
    path = directory / f'VibeWare-{timestamp:%Y%m%d}.log'
    level = 'WRN' if error_type else 'INF'
    suffix = f' ({error_type})' if error_type else ''
    line = f'{timestamp.isoformat(timespec="milliseconds")[:-6]}Z [{level}] {event}{suffix}\n'
    try:
        with LOCK:
            directory.mkdir(parents=True, exist_ok=True)
            if not path.is_symlink() and (not path.exists() or path.stat().st_size < DAILY_LIMIT):
                with path.open('a', encoding='utf-8', newline='') as file:
                    file.write(line)
            cutoff = (timestamp - timedelta(days=6)).strftime('%Y%m%d')
            for file in _log_files(directory):
                if file.name[9:17] < cutoff:
                    file.unlink(missing_ok=True)
    except OSError:
        # Support logging must never interrupt the memory monitor.
        pass


def create_archive() -> Path:
    """Create a local ZIP containing timestamp-filtered diagnostics only."""
    now = datetime.now(UTC)
    since = now - HISTORY
    directory = _app_directory()
    cutoff = since.strftime('%Y%m%d')
    today = now.strftime('%Y%m%d')
    entries = {}
    with LOCK:
        for path in _log_files(directory / 'logs'):
            if not cutoff <= path.name[9:17] <= today or path.stat().st_size > DAILY_LIMIT + 4096:
                continue
            recent = []
            with path.open(encoding='utf-8', errors='replace') as file:
                for line in file:
                    try:
                        timestamp = datetime.fromisoformat(line[:24])
                    except ValueError:
                        continue
                    if timestamp.tzinfo is not None and since <= timestamp <= now:
                        recent.append(line)
            if recent:
                entries[f'logs/{path.name}'] = ''.join(recent)
    if not entries:
        raise FileNotFoundError('No diagnostics from the past seven days.')
    output = directory / 'diagnostics'
    output.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime('%Y%m%dT%H%M%S%f')[:-3] + 'Z'
    archive = output / f'VibeWare-{APP_ID}-diagnostics-{stamp}.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in entries.items():
            bundle.writestr(name, content)
        bundle.writestr('manifest.json', json.dumps({
            'format': 'vibeware-diagnostics-v1', 'app': APP_ID,
            'fromUtc': since.isoformat(), 'createdUtc': now.isoformat(),
        }))
    return archive


def _open_attached_draft(subject: str, body: str, archive: Path) -> bool:
    """Ask Simple MAPI for an interactive compose window with an attachment."""
    uint = ctypes.c_uint32
    ptr = ctypes.c_void_p
    text = ctypes.c_wchar_p

    class Recipient(ctypes.Structure):
        _fields_ = [('reserved', uint), ('mail_class', uint), ('name', text),
                    ('address', text), ('entry_id_size', uint), ('entry_id', ptr)]

    class Attachment(ctypes.Structure):
        _fields_ = [('reserved', uint), ('flags', uint), ('position', uint),
                    ('path', text), ('name', text), ('file_type', ptr)]

    class Message(ctypes.Structure):
        _fields_ = [('reserved', uint), ('subject', text), ('body', text), ('message_type', text),
                    ('date_received', text), ('conversation_id', text), ('flags', uint),
                    ('originator', ptr), ('recipient_count', uint), ('recipients', ctypes.POINTER(Recipient)),
                    ('file_count', uint), ('files', ctypes.POINTER(Attachment))]

    try:
        send = ctypes.WinDLL('mapi32.dll').MAPISendMailW
    except (OSError, AttributeError):
        return False
    send.argtypes = [ctypes.c_size_t, ctypes.c_size_t, ctypes.POINTER(Message), uint, uint]
    send.restype = uint
    recipient = Recipient(0, 1, SUPPORT, f'SMTP:{SUPPORT}', 0, None)
    attachment = Attachment(0, 0, 0xffffffff, str(archive), archive.name, None)
    message = Message(0, subject, body, None, None, None, 0, None, 1,
                      ctypes.pointer(recipient), 1, ctypes.pointer(attachment))
    # MAPI_DIALOG is mandatory. Success and user cancellation both end the operation.
    return send(0, 0, ctypes.byref(message), 0x8, 0) in (0, 1)


def open_email_draft(archive: Path) -> str:
    """Open a user-controlled compose window, with a mailto fallback."""
    subject = 'Ram Taskman diagnostics'
    body = 'Please describe the problem and how to reproduce it. Review the ZIP before sending.'
    if _open_attached_draft(subject, body, archive):
        return 'support_saved'
    query = urlencode(
        {'subject': subject, 'body': f'{body}\r\n\r\nAttach this file: {archive.name}'},
        quote_via=quote,
    )
    try:
        os.startfile(f'mailto:{SUPPORT}?{query}')
    except OSError:
        return 'support_no_mail'
    try:
        subprocess.Popen(['explorer.exe', f'/select,{archive}'])
    except OSError:
        pass
    return 'support_attach'
