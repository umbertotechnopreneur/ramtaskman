"""Explicit local capture dialogs; no automatic disk writes or process access."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static
from textual.worker import get_current_worker

from .capture_io import CaptureFormatError, load_capture, save_capture
from .i18n import translate
from .localized_screen import LocalizedModalScreen
from .messages import error_text, localize


class _LocalizedCaptureScreen(LocalizedModalScreen):
    """Use the owning app's language without changing the process locale."""

    def tr(self, key: str, **values: object) -> str:
        language = getattr(self.app, 'language', 'it')
        return translate(language, key, **values)


class CaptureSaveScreen(_LocalizedCaptureScreen):
    """Save a snapshot to an explicitly chosen path, confirming replacement separately."""
    BINDINGS = [Binding('escape', 'cancel', 'Annulla')]
    DEFAULT_CSS = '''
    CaptureSaveScreen { align: center middle; }
    CaptureSaveScreen > Vertical { width: 90; max-width: 95%; height: auto; max-height: 90%; border: round $accent; background: $surface; padding: 1 2; }
    CaptureSaveScreen Input { width: 100%; }
    CaptureSaveScreen Horizontal { height: auto; }
    CaptureSaveScreen Button { margin-right: 1; }
    #capture-overwrite { display: none; }
    '''

    def __init__(self, current, baseline=None) -> None:
        super().__init__()
        self.current, self.baseline = current, baseline
        self.pending_path: str | None = None
        self.busy = False
        self.request_id = 0

    def compose(self) -> ComposeResult:
        status = self.tr('complete' if self.current.complete else 'partial_sample')
        when = datetime.fromtimestamp(self.current.taken).strftime('%Y-%m-%d %H:%M:%S')
        with Vertical():
            yield Static(Text(self.tr('capture_save_title', name=self.current.name, pid=self.current.pid,
                                      time=when, status=status), style='bold'))
            yield Static(self.tr('capture_count', count=1 + int(self.baseline is not None)))
            yield Input(placeholder=self.tr('capture_path'), id='capture-path')
            with Horizontal():
                yield Button(self.tr('save'), id='capture-save', compact=True)
                yield Button(self.tr('replace_file'), id='capture-overwrite', compact=True, variant='warning')
                yield Button(self.tr('cancel'), id='capture-cancel', compact=True)
            yield Static('', id='capture-error')

    def on_mount(self) -> None:
        self.query_one('#capture-path', Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if self.pending_path is not None and event.value != self.pending_path:
            self.pending_path = None
            self.query_one('#capture-overwrite', Button).display = False
            self.query_one('#capture-error', Static).update('')

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.start_save(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == 'capture-cancel':
            self.action_cancel()
        elif event.button.id == 'capture-save':
            self.start_save(False)
        elif event.button.id == 'capture-overwrite':
            self.start_save(True)

    def start_save(self, overwrite: bool) -> None:
        if self.busy:
            return
        path = self.query_one('#capture-path', Input).value.strip()
        if not path:
            self.query_one('#capture-error', Static).update(self.tr('enter_path'))
            return
        if overwrite and path != self.pending_path:
            self.query_one('#capture-error', Static).update(self.tr('path_changed'))
            return
        self.request_id += 1
        self.busy = True
        self.query_one('#capture-error', Static).update(self.tr('saving'))
        self.write_file(self.request_id, path, overwrite)

    @work(thread=True, exclusive=True, group='capture-save')
    def write_file(self, request_id: int, path: str, overwrite: bool) -> None:
        worker = get_current_worker()
        try:
            save_capture(path, self.current, self.baseline, overwrite=overwrite)
        except FileExistsError:
            result = 'exists'
        except (CaptureFormatError, OSError, ValueError) as error:
            result = error_text(error)
        else:
            result = None
        if not worker.is_cancelled:
            try:
                self.app.call_from_thread(self._complete, request_id, path, result)
            except RuntimeError:
                pass

    def _complete(self, request_id: int, path: str, result: str | None) -> None:
        if not self.is_mounted or request_id != self.request_id:
            return
        self.busy = False
        if result == 'exists':
            self.pending_path = path
            self.query_one('#capture-overwrite', Button).display = True
            self.query_one('#capture-error', Static).update(self.tr('file_exists'))
        elif result is not None:
            language = getattr(self.app, 'language', 'it')
            self.query_one('#capture-error', Static).update(Text(localize(result, language), style='yellow'))
        else:
            self.dismiss(True)

    def action_cancel(self) -> None:
        if self.busy:
            # Do not claim cancellation of an atomic write already underway.
            self.query_one('#capture-error', Static).update(self.tr('wait_write'))
            return
        self.dismiss(False)


class CaptureOpenScreen(_LocalizedCaptureScreen):
    """Select and validate a bounded capture in a worker; returns CaptureFile or None."""
    BINDINGS = [Binding('escape', 'cancel', 'Annulla')]
    DEFAULT_CSS = '''
    CaptureOpenScreen { align: center middle; }
    CaptureOpenScreen > Vertical { width: 90; max-width: 95%; height: auto; max-height: 90%; border: round $secondary; background: $surface; padding: 1 2; }
    CaptureOpenScreen Input { width: 100%; }
    CaptureOpenScreen Horizontal { height: auto; }
    CaptureOpenScreen Button { margin-right: 1; }
    '''

    def __init__(self) -> None:
        super().__init__()
        self.request_id = 0
        self.busy = False

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.tr('capture_open_title'), classes='bold')
            yield Input(placeholder=self.tr('capture_path'), id='capture-open-path')
            with Horizontal():
                yield Button(self.tr('open'), id='capture-open', compact=True)
                yield Button(self.tr('cancel'), id='capture-open-cancel', compact=True)
            yield Static('', id='capture-open-error')

    def on_mount(self) -> None:
        self.query_one('#capture-open-path', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.start_open()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == 'capture-open':
            self.start_open()
        elif event.button.id == 'capture-open-cancel':
            self.action_cancel()

    def start_open(self) -> None:
        if self.busy:
            return
        path = self.query_one('#capture-open-path', Input).value.strip()
        if not path:
            self.query_one('#capture-open-error', Static).update(self.tr('enter_path'))
            return
        self.request_id += 1
        self.busy = True
        self.query_one('#capture-open-error', Static).update(self.tr('loading_capture'))
        self.read_file(self.request_id, path)

    @work(thread=True, exclusive=True, group='capture-open')
    def read_file(self, request_id: int, path: str) -> None:
        worker = get_current_worker()
        try:
            result = load_capture(Path(path))
        except (CaptureFormatError, OSError, ValueError) as error:
            result = error
        if not worker.is_cancelled:
            try:
                self.app.call_from_thread(self._complete, request_id, result)
            except RuntimeError:
                pass

    def _complete(self, request_id: int, result) -> None:
        if not self.is_mounted or request_id != self.request_id:
            return
        self.busy = False
        if isinstance(result, Exception):
            language = getattr(self.app, 'language', 'it')
            self.query_one('#capture-open-error', Static).update(Text(localize(error_text(result), language), style='yellow'))
        else:
            self.dismiss(result)

    def action_cancel(self) -> None:
        self.request_id += 1
        self.workers.cancel_node(self)
        self.dismiss(None)
