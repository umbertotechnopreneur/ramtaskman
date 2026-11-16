"""Application messages, stored as readable UTF-8 catalogs for translators.

Catalog keys and replacement fields are the same in every language. Internal
identifiers, process names and paths are never translated. A caller chooses the
language once when constructing the app; no global locale is changed.
"""
from __future__ import annotations

import json
from importlib.resources import files

LANGUAGES = ('it', 'en', 'zh', 'ko', 'fr', 'vi', 'es', 'pt', 'de', 'ja')


def _load_catalog(language: str) -> dict[str, str]:
    """Load a bundled catalog, including when installed from a wheel."""
    resource = files('ramtaskman').joinpath('locales', f'{language}.json')
    return json.loads(resource.read_text(encoding='utf-8'))


CATALOG = {language: _load_catalog(language) for language in LANGUAGES}


def load_help(language: str) -> str:
    """Read the bundled guide for the language chosen by the owning app."""
    if language not in LANGUAGES:
        raise ValueError(translate('it', 'invalid_language', code=language))
    resource = files('ramtaskman').joinpath('locales', f'help.{language}.md')
    return resource.read_text(encoding='utf-8')


def translate(language: str, key: str, /, **values: object) -> str:
    """Format a translated message without interpreting interpolated data as markup."""
    return CATALOG[language][key].format(**values)
