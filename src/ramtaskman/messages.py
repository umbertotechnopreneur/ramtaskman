"""Translate application diagnostics at presentation boundaries.

The str-compatible value keeps canonical Italian text for the model, JSON and
existing capture files. Live values also carry their message key and parameters,
so a UI can translate them without guessing at arbitrary process or OS text.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .i18n import translate


class LocalizedMessage(str):
    """A diagnostic with a stable key, also usable wherever str is expected."""

    def __new__(cls, key: str, values: Mapping[str, Any] | None = None):
        parameters = dict(values or {})
        instance = super().__new__(cls, translate('it', key, **parameters))
        instance.key = key
        instance.values = MappingProxyType(parameters)
        return instance

    def __reduce__(self):
        # dataclasses.asdict deep-copies non-dataclass fields. Reconstruct from
        # the key rather than treating the rendered string as a catalog key.
        return type(self), (self.key, dict(self.values))


def message(key: str, /, **values: object) -> LocalizedMessage:
    return LocalizedMessage(key, values)


def localize(value: object, language: str) -> str:
    """Translate owned diagnostics; preserve captured text, paths and OS details."""
    if isinstance(value, LocalizedMessage):
        parameters = {
            name: localize(parameter, language) if isinstance(parameter, LocalizedMessage) else parameter
            for name, parameter in value.values.items()
        }
        return translate(language, value.key, **parameters)
    return str(value)


def error_text(error: BaseException) -> str:
    """Retain a structured single-argument error until the UI chooses a language."""
    if len(error.args) == 1 and isinstance(error.args[0], LocalizedMessage):
        return error.args[0]
    return str(error)
