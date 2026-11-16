"""Read native process metadata without psutil's command-line fallbacks.

The public Process.name() may expand a truncated name from cmdline(), while
Process.exe() may inspect cmdline() and probe the resulting file path. Neither
is permitted by this application's metadata-only contract.

psutil 7 (the supported major version) exposes its OS implementation as _proc.
Its native name/exe methods use procfs or OS metadata APIs without those public
fallbacks. Keep that private dependency here: if its shape changes, report an
unknown executable and an explicit PID label rather than broaden data access.
"""
from __future__ import annotations

import psutil


def _native_text(process: psutil.Process, field: str) -> str | None:
    """Read fresh native metadata; never populate or reuse public name/exe caches."""
    try:
        native = getattr(process, '_proc', None)
        read = getattr(native, field, None)
        value = read() if callable(read) else None
    except (AttributeError, NotImplementedError, PermissionError, psutil.AccessDenied):
        return None
    # A disappearing process must still propagate to the caller's PID/time
    # checks. Empty or unexpected return values provide no identity evidence.
    return value if isinstance(value, str) and value else None


def process_name(process: psutil.Process) -> str:
    """Return the native name, or a PID label when it cannot be read safely."""
    return _native_text(process, 'name') or f'PID {process.pid}'


def process_executable(process: psutil.Process) -> str | None:
    """Return native executable metadata without path probes or guessed values."""
    return _native_text(process, 'exe')
