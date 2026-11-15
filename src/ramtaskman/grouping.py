"""Bounded recognition of systemd user application cgroups, not app-name guessing.

Naming convention: https://systemd.io/DESKTOP_ENVIRONMENTS/
Escaping: https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
"""
from __future__ import annotations

import re
import unicodedata

# /proc/PID/cgroup is small normally. Never parse a truncated prefix as evidence.
CGROUP_LIMIT = 16 * 1024
_UNIT = re.compile(r"app-(?:[A-Za-z0-9:_.@-]|\\x[0-9A-Fa-f]{2})+\.(?:scope|service)\Z")
_LAUNCHERS = ('gnome-', 'KDE-', 'flatpak-')


def unit_label(unit: str) -> str | None:
    """Display only: identity always keeps the full escaped instance path."""
    if len(unit) > 255 or not _UNIT.fullmatch(unit):
        return None
    body, suffix = unit[4:].rsplit('.', 1)
    if suffix == 'scope':
        # A scope requires a final instance discriminator in the naming convention.
        body, sep, instance = body.rpartition('-')
        if not sep or not body or not instance or '@' in body:
            return None
    else:
        if body.count('@') > 1:
            return None
        if '@' in body:
            body, instance = body.split('@')
            if not body or not instance:
                return None
    for launcher in _LAUNCHERS:
        if body.startswith(launcher):
            body = body[len(launcher):]
            break
    if not body:
        return None
    raw = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), body)
    label = raw.encode('latin1').decode('utf-8', errors='replace')
    # Unit names are untrusted metadata; render control characters as replacement glyphs.
    return ''.join('�' if unicodedata.category(c).startswith('C') else c for c in label)


def application_cgroup(text: str, uid: int | None) -> tuple[str, str] | None:
    """Return (instance path, label) only for an explicit app unit of this UID.

    Unified hierarchy and legacy name=systemd are supported. Root/session slices,
    arbitrary services and ambiguous multi-hierarchy identities are not evidence.
    The accepted app path is under the user's app.slice, never the whole session.
    Children delegated below an app unit share that same app instance.
    """
    if uid is None or len(text) > CGROUP_LIMIT:
        return None
    identities: set[tuple[str, str]] = set()
    for line in text.splitlines():
        fields = line.split(':', 2)
        if len(fields) != 3:
            continue
        hierarchy, controllers, path = fields
        if not (hierarchy == '0' and controllers == '') and 'name=systemd' not in controllers.split(','):
            continue
        prefix = f'/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/'
        if not path.startswith(prefix):
            continue
        tail = path[len(prefix):].split('/')
        # Optional nested application slices still must lead to a single app unit.
        cursor = 0
        while cursor < len(tail) and tail[cursor].startswith('app-') and tail[cursor].endswith('.slice'):
            cursor += 1
        if cursor >= len(tail):
            continue
        unit = tail[cursor]
        label = unit_label(unit)
        if label is None:
            continue
        # A nested unit is a different independently managed workload; do not inherit.
        if any(part.endswith(('.service', '.scope')) or part in ('.', '..', '') for part in tail[cursor + 1:]):
            continue
        instance_path = prefix + '/'.join(tail[:cursor + 1])
        identities.add((instance_path, label))
    return next(iter(identities)) if len(identities) == 1 else None
