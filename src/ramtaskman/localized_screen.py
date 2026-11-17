"""Localize displayed bindings without mutating Textual's shared key maps."""
from __future__ import annotations

from dataclasses import replace

from textual.binding import ActiveBinding
from textual.screen import ModalScreen, Screen

from .i18n import translate

_BINDING_MESSAGES = {
    'about': 'about_title', 'quit': 'footer_quit', 'cycle_sort': 'footer_sort', 'sort': 'footer_sort',
    'cycle_chart': 'footer_chart', 'toggle_all': 'footer_all_top',
    'toggle_group': 'footer_apps_pids', 'toggle_monitoring': 'footer_slim_full',
    'pause': 'footer_pause', 'help': 'footer_help', 'search': 'footer_search',
    'filters': 'footer_filter', 'detail': 'footer_detail', 'regions': 'footer_regions',
    'back': 'footer_back', 'close': 'footer_close', 'pop_screen': 'footer_close',
    'refresh_regions': 'footer_refresh', 'mode': 'footer_mode', 'zoom': 'footer_zoom',
    'baseline': 'footer_baseline', 'clear_baseline': 'footer_clear_baseline',
    'compare': 'footer_compare', 'save_capture': 'save', 'open_capture': 'open',
    'previous_page': 'footer_previous_page', 'next_page': 'footer_next_page',
    'cancel': 'cancel', 'command_palette': 'footer_palette',
}


class _LocalizedBindings:
    @property
    def active_bindings(self) -> dict[str, ActiveBinding]:
        """Translate copies of display metadata, preserving actions and priorities."""
        language = getattr(self.app, 'language', 'it')
        bindings = super().active_bindings
        localized = {}
        for key, active in bindings.items():
            action = active.binding.action.rsplit('.', 1)[-1]
            message_key = _BINDING_MESSAGES.get(action)
            if message_key is None:
                localized[key] = active
                continue
            description = translate(language, message_key)
            binding = replace(active.binding, description=description,
                              tooltip=description if active.binding.tooltip else '')
            localized[key] = active._replace(binding=binding,
                                             tooltip=description if active.tooltip else '')
        return localized


class LocalizedScreen(_LocalizedBindings, Screen):
    """Default application screen with translated footer descriptions."""


class LocalizedModalScreen(_LocalizedBindings, ModalScreen):
    """Modal screen sharing its owning application's selected language."""
