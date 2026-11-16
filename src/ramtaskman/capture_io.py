"""Versioned bounded capture format; data only, never access recorded paths."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import __version__
from .capture_models import CaptureSnapshot, FrozenRegion, METRICS
from .messages import error_text, message

MAX_BYTES = 64 << 20
MAX_REGIONS = 32768
MAX_STRING = 65536
MAX_UINT = (1 << 64) - 1
_HEX = re.compile(r'0x(?:0|[1-9a-f][0-9a-f]*)\Z')


class CaptureFormatError(ValueError):
    """A capture is malformed, unsupported or exceeds declared limits."""


@dataclass(frozen=True)
class CaptureFile:
    current: CaptureSnapshot
    baseline: CaptureSnapshot | None = None


def _error(text: str):
    raise CaptureFormatError(text)


def _object(value: Any, name: str) -> dict:
    if not isinstance(value, dict) or len(value) > 256:
        _error(message('capture_invalid_object', name=name))
    return value


def _keys(obj: dict, required: set[str], name: str) -> None:
    if not required.issubset(obj):
        _error(message('capture_missing_fields', name=name, fields=', '.join(sorted(required - obj.keys()))))
    # Unknown fields cannot be silently dropped: they may change metric semantics.
    if obj.keys() - required:
        _error(message('capture_unknown_fields', name=name, fields=', '.join(sorted(obj.keys() - required))))


def _text(value: Any, name: str, *, nullable=False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) > MAX_STRING:
        _error(message('capture_invalid_text', name=name))
    if any(ord(ch) < 32 or 0x7f <= ord(ch) <= 0x9f or 0xd800 <= ord(ch) <= 0xdfff for ch in value):
        _error(message('capture_control_characters', name=name))
    return value


def _uint(value: Any, name: str, *, nullable=False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or not 0 <= value <= MAX_UINT:
        _error(message('capture_unsigned_limit', name=name))
    return value


def _number(value: Any, name: str) -> float:
    if type(value) not in (int, float) or value < 0 or value > 1e15 or not math.isfinite(value):
        _error(message('capture_finite_number', name=name))
    return float(value)


def _addr(value: Any, name: str) -> int:
    if not isinstance(value, str) or len(value) > 18 or not _HEX.fullmatch(value):
        _error(message('capture_canonical_address', name=name))
    return _uint(int(value, 16), name)


def _mapping(value: Any, name: str, parser) -> dict:
    obj = _object(value, name)
    return {_text(k, f'{name}.key'): parser(v, f'{name}.{k}') for k, v in obj.items()}


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        _error(message('capture_boolean', name=name))
    return value


def _coverage(value: Any, name: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        _error(message('capture_coverage_pair', name=name))
    actual, total = (_uint(v, name) for v in value)
    if actual > total:
        _error(message('capture_coverage_inconsistent', name=name))
    return actual, total


_REGION_KEYS = {'start', 'end', 'offset', 'permissions', 'device', 'inode', 'path', 'category',
                'rss', 'pss', 'uss', 'swap', 'swap_pss', 'breakdown', 'vm_flags'}
_CAPTURE_KEYS = {'pid', 'started_at', 'name', 'taken', 'regions', 'sample_ms', 'reason',
                 'complete', 'capture_id', 'collection_session_id', 'sequence', 'platform',
                 'backend_id', 'executable_identity', 'metric_definitions', 'backend_version',
                 'capabilities', 'metric_coverage', 'issues'}


def _decode_region(value: Any) -> FrozenRegion:
    region_label = message('capture_label_region')
    obj = _object(value, region_label)
    _keys(obj, _REGION_KEYS, region_label)
    start, end, offset = (_addr(obj[k], k) for k in ('start', 'end', 'offset'))
    if start >= end:
        _error(message('capture_invalid_region', name=region_label))
    flags = obj['vm_flags']
    if not isinstance(flags, list) or len(flags) > 256:
        _error(message('capture_invalid_flags'))
    return FrozenRegion(start=start, end=end, offset=offset,
        permissions=_text(obj['permissions'], 'permissions'), device=_text(obj['device'], 'device'),
        inode=_uint(obj['inode'], 'inode'), path=_text(obj['path'], 'path'),
        category=_text(obj['category'], 'category'),
        **{k: _uint(obj[k], k, nullable=True) for k in ('rss','pss','uss','swap','swap_pss')},
        breakdown=_mapping(obj['breakdown'], 'breakdown', lambda v, n: _uint(v, n, nullable=True)),
        vm_flags=tuple(_text(v, 'VmFlag') for v in flags))


def _decode_capture(value: Any) -> CaptureSnapshot:
    capture_label = message('capture_label_capture')
    obj = _object(value, capture_label)
    _keys(obj, _CAPTURE_KEYS, capture_label)
    rows = obj['regions']
    if not isinstance(rows, list) or len(rows) > MAX_REGIONS:
        _error(message('capture_region_count'))
    regions = tuple(_decode_region(row) for row in rows)
    previous = 0
    for region in regions:
        if region.start < previous:
            _error(message('capture_overlapping_regions'))
        previous = region.end
    issues = obj['issues']
    if not isinstance(issues, list) or len(issues) > 256:
        _error(message('capture_invalid_issues'))
    values = dict(pid=_uint(obj['pid'], 'pid'), started_at=_number(obj['started_at'], 'started_at'),
        taken=_number(obj['taken'], 'taken'), sample_ms=_number(obj['sample_ms'], 'sample_ms'),
        sequence=_uint(obj['sequence'], 'sequence'), complete=_boolean(obj['complete'], 'complete'),
        regions=regions, reason=_text(obj['reason'], 'reason', nullable=True),
        executable_identity=_text(obj['executable_identity'], 'executable_identity', nullable=True),
        metric_definitions=_mapping(obj['metric_definitions'], 'metric_definitions', _text),
        capabilities=_mapping(obj['capabilities'], 'capabilities', _boolean),
        metric_coverage=_mapping(obj['metric_coverage'], 'metric_coverage', _coverage),
        issues=tuple(_text(v, 'issue') for v in issues))
    try:
        datetime.fromtimestamp(values['taken'])
    except (ValueError, OverflowError, OSError) as error:
        raise CaptureFormatError(message('capture_unrepresentable_date')) from error
    for key in ('name','capture_id','collection_session_id','platform','backend_id','backend_version'):
        values[key] = _text(obj[key], key)
        if not values[key]:
            _error(message('capture_empty_value', name=key))
    if not values['pid']:
        _error(message('capture_positive_pid'))
    for metric, (observed, total) in values['metric_coverage'].items():
        if metric in METRICS:
            if total != len(regions) or observed != sum(getattr(r, metric) is not None for r in regions):
                _error(message('capture_coverage_regions', metric=metric))
    return CaptureSnapshot(**values)


def _region_data(row: FrozenRegion) -> dict:
    result = {k: getattr(row, k) for k in _REGION_KEYS if k not in ('start','end','offset','breakdown','vm_flags')}
    result.update(start=hex(row.start), end=hex(row.end), offset=hex(row.offset),
                  breakdown=dict(row.breakdown), vm_flags=list(row.vm_flags))
    return result


def _capture_data(capture: CaptureSnapshot) -> dict:
    result = {k: getattr(capture, k) for k in _CAPTURE_KEYS if k not in
              ('regions','metric_definitions','capabilities','metric_coverage','issues')}
    result.update(regions=[_region_data(r) for r in capture.regions],
                  metric_definitions=dict(capture.metric_definitions), capabilities=dict(capture.capabilities),
                  metric_coverage={k: list(v) for k, v in capture.metric_coverage.items()}, issues=list(capture.issues))
    return result


def _decode_document(obj: Any) -> CaptureFile:
    obj = _object(obj, 'file')
    _keys(obj, {'format','schema_version','producer_version','current_capture_id','baseline_capture_id','captures'}, 'file')
    if obj['format'] != 'ramtaskman.capture' or type(obj['schema_version']) is not int or obj['schema_version'] != 1:
        _error(message('capture_schema_unsupported'))
    _text(obj['producer_version'], 'producer_version')
    rows = obj['captures']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2:
        _error(message('capture_count_invalid'))
    captures = [_decode_capture(row) for row in rows]
    lookup = {c.capture_id: c for c in captures}
    if len(lookup) != len(captures):
        _error(message('capture_duplicate_id'))
    current_id = _text(obj['current_capture_id'], 'current_capture_id')
    baseline_id = _text(obj['baseline_capture_id'], 'baseline_capture_id', nullable=True)
    if current_id not in lookup or (baseline_id is not None and (baseline_id not in lookup or baseline_id == current_id)):
        _error(message('capture_invalid_roles'))
    if len(captures) != (2 if baseline_id is not None else 1):
        _error(message('capture_unassigned_capture'))
    return CaptureFile(lookup[current_id], lookup[baseline_id] if baseline_id is not None else None)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _text(key, message('capture_label_json_key'))
        if key in result:
            _error(message('capture_duplicate_json_key', key=key))
        result[key] = value
    return result


def load_capture(path: str | Path) -> CaptureFile:
    with open(path, 'rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        _error(message('capture_size_limit'))
    try:
        obj = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                         parse_constant=lambda value: _error(message('capture_non_finite', value=value)))
    except CaptureFormatError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise CaptureFormatError(message('capture_invalid_json', reason=error_text(error))) from error
    return _decode_document(obj)


def save_capture(path: str | Path, current: CaptureSnapshot, baseline: CaptureSnapshot | None = None,
                 *, overwrite: bool = False) -> None:
    """Validate, size-bound and atomically persist a local capture.

    When overwrite is false, a concurrent file creation wins and the existing
    file is never replaced. A temporary file is removed on every failure.
    """
    if baseline is not None and baseline.capture_id == current.capture_id:
        _error(message('capture_same_baseline'))
    captures = [current] if baseline is None else [baseline, current]
    doc = {'format':'ramtaskman.capture', 'schema_version':1, 'producer_version':__version__,
           'current_capture_id':current.capture_id, 'baseline_capture_id':baseline.capture_id if baseline else None,
           'captures':[_capture_data(c) for c in captures]}
    _decode_document(doc)  # Validate even programmatically generated data before writing.
    # Enforce the byte limit while encoding. Building a full JSON string first
    # could allocate gigabytes before discovering that the capture is too large.
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    data = bytearray()
    for chunk in encoder.iterencode(doc):
        encoded = chunk.encode('utf-8')
        if len(data) + len(encoded) > MAX_BYTES:
            _error(message('capture_size_limit'))
        data.extend(encoded)
    dest = Path(path)
    temp = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix='.ramtaskman-', suffix='.tmp', dir=dest.parent)
        temp = Path(temp_name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp, dest)
            temp = None
        else:
            # Hard-link atomically refuses to replace a concurrently created file.
            os.link(temp, dest)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
