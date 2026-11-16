"""On-demand process-region explorer using the existing Textual terminal style."""
from __future__ import annotations

from datetime import datetime
from time import time
from uuid import uuid4

from rich.console import Group
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import DataTable, Footer, Input, Select, Static
from textual.worker import get_current_worker

from .models import ProcessMemory
from .application_bar import process_uss_bar
from .ram_bar import SystemRamBar
from .i18n import translate
from .region_map import CATEGORIES, RegionMap
from .delta_bar import DeltaBar
from .regions import MemoryRegion, RegionSnapshot
from .report import size
from .capture_models import CaptureSnapshot, freeze_snapshot
from .comparison import ComparisonCancelled, compare_captures
from .region_provider import make_region_provider
from .localized_screen import LocalizedModalScreen
from .messages import error_text, localize, message

COMPARISON_STATES = (
    'same_interval', 'metadata_changed', 'backing_changed', 'backing_unverified',
    'restructured', 'only_a', 'only_b', 'unobserved',
)


def filter_regions(regions: list[MemoryRegion], query: str, category: str, state: str,
                   language: str = 'it') -> list[MemoryRegion]:
    query = query.strip().casefold()
    address = None
    if query.startswith('0x'):
        try:
            address = int(query, 16)
        except ValueError:
            pass
    labels = ({key: translate(language, 'category_' + key) for key in CATEGORIES}
              if query else {})
    result = []
    for region in regions:
        if category != 'all' and region.category != category:
            continue
        if state == 'resident' and not (region.rss is not None and region.rss > 0):
            continue
        if state == 'swap' and not (region.swap is not None and region.swap > 0):
            continue
        if state == 'shared':
            shared = [region.breakdown.get(k) for k in ('shared_clean', 'shared_dirty')]
            if not all(v is not None for v in shared) or sum(shared) <= 0:
                continue
        if query:
            label = labels.get(region.category, region.category)
            haystack = f'{region.path} {region.permissions} {region.start:x}-{region.end:x} {label}'.casefold()
            address_matches = address is not None and region.start <= address < region.end
            if not address_matches and query not in haystack:
                continue
        result.append(region)
    return result


class RegionScreen(LocalizedModalScreen):
    BINDINGS = [
        Binding('escape', 'back', 'Indietro'), Binding('q', 'close', 'Chiudi'),
        Binding('r', 'refresh_regions', 'Aggiorna'), Binding('v', 'mode', 'RSS/Virtuale'),
        Binding('s', 'sort', 'Ordina'), Binding('z', 'zoom', 'Zoom'),
        Binding('slash', 'search', 'Cerca'), Binding('f', 'filters', 'Filtri'),
        Binding('b', 'baseline', 'Fissa A'), Binding('ctrl+b', 'clear_baseline', 'Cancella A'),
        Binding('c', 'compare', 'Confronto'), Binding('ctrl+s', 'save_capture', 'Salva'),
        Binding('ctrl+o', 'open_capture', 'Apri'),
        Binding('ctrl+left,ctrl+u', 'previous_page', 'Pagina prec.'),
        Binding('ctrl+right,ctrl+d', 'next_page', 'Pagina succ.'),
    ]
    SORTS = ('rss', 'pss', 'size', 'start')
    PAGE_SIZE = 250
    DEFAULT_CSS = """
    RegionScreen { layout: vertical; background: $background; }
    #region-dashboard { height: auto; max-height: 50%; }
    #region-summary { height: auto; border: round $accent; padding: 0 1; }
    #region-memory { height: auto; border: round $success; padding: 0 1; }
    #region-map-panel { height: auto; border: round $secondary; padding: 0 1; }
    #region-map-title, #region-legend, #region-map-note { height: auto; }
    #region-map-note { color: $text-muted; }
    #region-filters { display: none; height: auto; }
    #region-search { height: 1; border: none; padding: 0 1; }
    #region-selectors { height: 1; }
    #region-kind, #region-state, #comparison-state { width: 1fr; }
    #region-count { height: 1; padding: 0 1; color: $text-muted; }
    #region-table { height: 1fr; min-height: 4; }
    #region-inspector { height: auto; max-height: 30%; overflow-y: auto; border: round $secondary; padding: 0 1; }
    """

    def __init__(self, process: ProcessMemory, platform: str, reader=None, *,
                 offline_capture: CaptureSnapshot | None = None, offline_baseline: CaptureSnapshot | None = None) -> None:
        super().__init__()
        self.process, self.platform = process, platform
        self.offline = offline_capture is not None
        self.reader = reader
        injected_platform = getattr(getattr(reader, 'capabilities', None), 'platform', None)
        use_reader = reader is not None and (platform == 'linux' or injected_platform == platform)
        self.provider = None if self.offline else (reader if use_reader else make_region_provider(platform))
        self.current_capture = offline_capture
        self.baseline = offline_baseline
        self.session_id = ''
        self.comparison_mode = False
        self.comparison_metric = 'rss'
        self.comparison_sort = 0
        self.comparison_rows = {}
        self.page = 0
        self.page_keys: list[str] = []
        self._comparison_inputs = None
        self._comparison_result = None
        self._comparison_pending = None
        self._comparison_request = 0
        self._comparison_error = None
        self._search_timer = None
        self.snapshot: RegionSnapshot | None = None
        self.rows: dict[str, MemoryRegion] = {}
        self.selected: str | None = None
        self.mode = 'virtual' if platform == 'windows' else 'resident'
        self.sort_index = 3 if platform == 'windows' else 0
        self.zoom_key: str | None = None
        self.generation = 0
        self.request_id = 0
        self.loading = False
        self._restore_selected: str | None = None
        self._restore_zoom: str | None = None
        self._restore_page = 0

    def tr(self, key: str, **values: object) -> str:
        return translate(getattr(self.app, 'language', 'it'), key, **values)

    def comparison_label(self, status: str) -> str:
        """Translate known states, keeping unknown captured identifiers literal."""
        return self.tr('comparison_' + status) if status in COMPARISON_STATES else status

    def metric_label(self, metric: str) -> str:
        """Keep counter symbols while translating virtual-size/address labels."""
        if metric == 'size':
            return self.tr('region_column_virtual')
        if metric == 'start':
            return self.tr('region_column_address')
        return metric.upper()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id='region-dashboard'):
            yield Static(id='region-summary')
            yield Static(id='region-memory')
            with Vertical(id='region-map-panel'):
                yield Static(id='region-map-title')
                yield RegionMap(language=getattr(self.app, 'language', 'it'), id='region-map')
                yield DeltaBar(id='delta-bar')
                yield Static(id='region-legend')
                yield Static(id='region-map-note')
        with Vertical(id='region-filters'):
            yield Input(placeholder=self.tr('region_search'), id='region-search')
            with Horizontal(id='region-selectors'):
                yield Select([(self.tr('region_all_types'), 'all'),
                              *((self.tr('category_' + k), k) for k in CATEGORIES)],
                             allow_blank=False, value='all', compact=True, id='region-kind')
                yield Select([(self.tr('region_all_states'), 'all'), (self.tr('region_resident'), 'resident'), (self.tr('region_with_swap'), 'swap'),
                              (self.tr('region_shared') + ' RSS > 0', 'shared')], allow_blank=False, value='all', compact=True, id='region-state')
                yield Select([(self.tr('comparison_all'), 'all'),
                              *((self.comparison_label(status), status) for status in COMPARISON_STATES)],
                             allow_blank=False, value='all', compact=True, id='comparison-state')
        yield Static(id='region-count')
        yield DataTable(id='region-table', cursor_type='row', zebra_stripes=True)
        with VerticalScroll(id='region-inspector'):
            yield Static(id='region-details')
        yield Footer()

    def on_mount(self) -> None:
        if not hasattr(self.app, '_region_collection_session'):
            self.app._region_collection_session = str(uuid4())
            self.app._region_capture_sequence = 0
        self.session_id = self.app._region_collection_session
        self.query_one('#comparison-state', Select).display = self.comparison_mode
        table = self.query_one('#region-table', DataTable)
        self.set_columns(False)
        table.focus()
        self.set_interval(1, self.render_summary)
        if self.offline:
            self.snapshot = self.current_capture
            self.comparison_mode = self.baseline is not None
            self.query_one('#comparison-state', Select).display = self.comparison_mode
            if self.comparison_mode:
                self.set_columns(True)
            self.render_regions()
        else:
            self.action_refresh_regions()

    def set_columns(self, comparison: bool) -> None:
        table = self.query_one('#region-table', DataTable)
        table.clear(columns=True)
        # Column identities remain stable when their displayed labels change.
        columns = (
            (('start', self.tr('region_column_address')), ('status', self.tr('region_column_state')),
             ('a', 'A'), ('b', 'B'), ('delta', 'Δ B−A'), ('region', self.tr('region_column_region')))
            if comparison else
            (('start', self.tr('region_column_address')), ('category', self.tr('region_column_type')),
             ('size', self.tr('region_column_virtual')), ('rss', 'RSS'), ('pss', 'PSS'), ('uss', 'USS'),
             ('swap', 'Swap'), ('permissions', self.tr('region_column_permissions')),
             ('path', self.tr('region_column_file')))
        )
        for key, label in columns:
            table.add_column(label, key=key)

    def on_unmount(self) -> None:
        self._cancel_search_timer()
        self.request_id += 1
        self._comparison_request += 1
        self.workers.cancel_node(self)

    def action_refresh_regions(self) -> None:
        if self.offline:
            self.notify(self.tr('region_notice_offline'), severity='warning')
            return
        self._invalidate_comparison()
        if not self.loading:
            self._restore_selected, self._restore_zoom = self.selected, self.zoom_key
            self._restore_page = self.page
        self.request_id += 1
        self.snapshot = None
        self.current_capture = None
        self.loading = True
        self.render_regions()
        # Assign the sequence on the UI thread before dispatch. Cancelled or
        # superseded reads may leave gaps, which do not alter ordering.
        self.app._region_capture_sequence += 1
        self.load_regions(self.request_id, self.app._region_capture_sequence)

    @work(thread=True, exclusive=True, group='region-read')
    def load_regions(self, request_id: int, sequence: int) -> None:
        worker = get_current_worker()
        try:
            result = self.provider.read(self.process, cancelled=lambda: worker.is_cancelled)
            if (result.pid, result.started_at) != (self.process.pid, self.process.started_at):
                result = RegionSnapshot(self.process.pid, self.process.started_at, self.process.name, time(),
                                        reason=message('region_identity_changed'), complete=False)
        except Exception as error:
            result = RegionSnapshot(self.process.pid, self.process.started_at, self.process.name, time(),
                                    reason=message('region_read_failed', type=type(error).__name__, reason=error_text(error)), complete=False)
        if not worker.is_cancelled:
            try:
                captured = self._freeze(result, sequence)
            except Exception as error:
                result = RegionSnapshot(self.process.pid, self.process.started_at, self.process.name, time(),
                                        reason=message('region_capture_failed', type=type(error).__name__), complete=False)
                captured = self._freeze(result, sequence)
            if worker.is_cancelled:
                return
            try:
                self.app.call_from_thread(self.accept_snapshot, request_id, result, captured)
            except RuntimeError:
                # The app may have closed while procfs was returning the last read.
                pass

    def _freeze(self, snapshot: RegionSnapshot, sequence: int) -> CaptureSnapshot:
        return freeze_snapshot(snapshot, collection_session_id=self.session_id,
                               sequence=sequence, platform=self.platform,
                               backend_id='linux-smaps' if self.platform == 'linux' else self.platform,
                               executable_identity=snapshot.executable_identity,
                               metric_definitions=None if self.platform == 'linux' else {'size': 'virtual.interval.bytes'})

    def accept_snapshot(self, request_id: int, snapshot: RegionSnapshot,
                        captured: CaptureSnapshot | None = None) -> None:
        if request_id != self.request_id or not self.is_mounted:
            return
        if (snapshot.pid, snapshot.started_at) != (self.process.pid, self.process.started_at):
            snapshot = RegionSnapshot(self.process.pid, self.process.started_at, self.process.name, time(),
                                      reason=message('region_identity_changed'), complete=False)
            captured = None
        self.loading = False
        if captured is None:
            # Compatibility for callers injecting a snapshot directly. Normal
            # live reads supply a worker-created immutable capture.
            self.app._region_capture_sequence += 1
            captured = self._freeze(snapshot, self.app._region_capture_sequence)
        self.snapshot = self.current_capture = captured
        self.selected, self.zoom_key = self._restore_selected, self._restore_zoom
        self.page = self._restore_page
        self.render_regions()

    def render_summary(self) -> None:
        if not self.is_mounted:
            return
        self.render_memory_context()
        panel = self.query_one('#region-summary', Static)
        panel.border_title = Text(self.tr('region_title', name=self.process.name, pid=self.process.pid))
        if self.loading:
            baseline_note = (' · ' + self.tr('region_baseline', time=datetime.fromtimestamp(self.baseline.taken).strftime('%H:%M:%S'))
                             if self.baseline else '')
            panel.update(self.tr('region_loading') + baseline_note + ' · Esc')
        elif self.snapshot:
            snap = self.snapshot
            date = datetime.fromtimestamp(snap.taken).strftime('%H:%M:%S')
            status = self.tr('region_complete' if snap.complete else 'region_partial')
            if self.offline:
                status += ' · ' + self.tr('region_offline')
            if self.baseline:
                status += ' · ' + self.tr('region_baseline', time=datetime.fromtimestamp(self.baseline.taken).strftime('%H:%M:%S'))
            age = self.tr('region_age', age=f'{max(0, time()-snap.taken):.0f}')
            source = self.tr('region_fixed') if self.offline else self.tr('region_live', platform=self.platform)
            panel.update(Group(Text(f'{status} · {date} · {age} · {snap.sample_ms:.0f} ms', style='bold'),
                               Text(localize(snap.reason, getattr(self.app, 'language', 'it')) if snap.reason else source,
                                    style='yellow' if snap.reason else 'grey70')))
        else:
            panel.update(self.tr('region_none'))

    def render_memory_context(self) -> None:
        panel = self.query_one('#region-memory', Static)
        panel.display = not self.offline
        if self.offline:
            return
        panel.border_title = Text(self.tr('region_ram_context', name=self.process.name, pid=self.process.pid))
        snap = getattr(self.app, 'snap', None)
        if snap is None:
            panel.update(Text(self.tr('region_ram_missing'), style='yellow'))
            return
        bar = SystemRamBar(snap.system, getattr(self.app, 'language', 'it'))
        process_bar = process_uss_bar(snap, self.process, getattr(self.app, 'language', 'it'))
        current = next((p for p in snap.processes if p.key == self.process.key), None)
        panel.update(Group(bar, bar.legend(), process_bar, process_bar.legend(),
                           Text(f'PID {self.process.pid} · USS {size(current.uss if current else None)} · '
                                f'RSS {size(current.rss if current else None)} · '
                                + self.tr('region_ram_age', age=f'{max(0, time() - snap.taken):.0f}'), style='bold'),
                           Text(process_bar.reason or process_bar.note, style='yellow' if process_bar.reason else 'grey70'),
                           Text(self.tr('region_scale_note'), style='grey70')))

    def render_regions(self) -> None:
        if not self.is_mounted:
            return
        self.render_summary()
        if self.comparison_mode:
            self.render_comparison()
            return
        regions = self.snapshot.regions if self.snapshot else []
        kind, state = self.query_one('#region-kind', Select).value, self.query_one('#region-state', Select).value
        filtered = filter_regions(regions, self.query_one('#region-search', Input).value, str(kind), str(state),
                                  getattr(self.app, 'language', 'it'))
        sort = self.SORTS[self.sort_index]
        ordered = sorted(filtered, key=lambda r: (r.start,) if sort == 'start' else
                         (getattr(r, sort) is None, -(getattr(r, sort) or 0), r.start))
        self.rows = {r.key: r for r in ordered}
        pages = max(1, (len(ordered) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        page_rows = ordered[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]
        self.page_keys = [row.key for row in page_rows]
        if self.selected not in self.page_keys:
            self.selected = self.page_keys[0] if self.page_keys else None
        table = self.query_one('#region-table', DataTable)
        table.clear()
        self.generation += 1
        for r in page_rows:
            category = (self.tr('category_' + r.category) if r.category in CATEGORIES else r.category)
            table.add_row(f'{r.start:x}–{r.end:x}', Text(category),
                          size(r.size), size(r.rss), size(r.pss), size(r.uss), size(r.swap), Text(r.permissions),
                          Text(r.path or '[' + self.tr('category_anonymous').lower() + ']'), key=f'{self.generation}|{r.key}')
        if self.selected:
            table.move_cursor(row=self.page_keys.index(self.selected), animate=False)
        partial = ' · ' + self.tr('partial_sample') if self.snapshot and not self.snapshot.complete else ''
        self.query_one('#region-count', Static).update(self.tr('region_count', shown=len(ordered),
            total=len(regions), sort=self.metric_label(sort), page=self.page + 1, pages=pages, partial=partial))
        self.render_map()
        self.render_inspector()

    def render_map(self) -> None:
        self.query_one('#region-map', RegionMap).display = True
        self.query_one('#delta-bar', DeltaBar).display = False
        regions = sorted(self.rows.values(), key=lambda r: r.start)
        if self.zoom_key not in self.rows:
            self.zoom_key = None
        if self.zoom_key:
            index = next(i for i, r in enumerate(regions) if r.key == self.zoom_key)
            regions = regions[max(0, index-2):index+3]
        self.query_one('#region-map', RegionMap).set_regions(regions, self.mode, self.selected)
        values = [r.size if self.mode == 'virtual' else r.rss for r in regions]
        total = sum(values) if values and all(v is not None for v in values) else None
        title = self.tr('region_virtual' if self.mode == 'virtual' else 'region_resident_title')
        title += ' · ' + self.tr('region_shown', size=size(total))
        if self.zoom_key:
            title += f' · {self.tr("footer_zoom")} {len(regions)}/{len(self.rows)}'
        if self.mode == 'virtual' and regions:
            title += f' · 0x{regions[0].start:x}–0x{regions[-1].end:x} ({self.tr("region_end_exclusive")})'
        self.query_one('#region-map-title', Static).update(Text(title, style='bold'))
        legend = Text()
        for category in dict.fromkeys(r.category for r in regions):
            label, color = CATEGORIES.get(category, (category, '#6b7280'))
            if category in CATEGORIES:
                label = self.tr('category_' + category)
            legend.append('■ ', style=color)
            legend.append(label + '  ')
        self.query_one('#region-legend', Static).update(legend)
        note = self.tr('region_virtual_note' if self.mode == 'virtual' else 'region_resident_note')
        selected = self.rows.get(self.selected)
        if selected is not None:
            note += f' ◆ PID {self.process.pid}: 0x{selected.start:x}–0x{selected.end:x} ({self.tr("region_end_exclusive")}).'
        self.query_one('#region-map-note', Static).update(note + ' ' + self.tr('region_selection_note'))

    def render_inspector(self) -> None:
        panel = self.query_one('#region-inspector', VerticalScroll)
        details = self.query_one('#region-details', Static)
        row = self.rows.get(self.selected)
        if row is None:
            panel.border_title = self.tr('region_detail')
            details.update(self.tr('region_no_match'))
            return
        panel.border_title = Text(row.path or '[' + self.tr('category_anonymous').lower() + ']')
        panel.border_subtitle = self.tr('region_scroll_hint')
        breakdown = ' · '.join(f'{self.tr(label)} {size(row.breakdown.get(key))}' for key, label in (
            ('private_clean', 'detail_private_clean'), ('private_dirty', 'detail_private_dirty'),
            ('shared_clean', 'detail_shared_clean'), ('shared_dirty', 'detail_shared_dirty')))
        origin = (f'offset 0x{row.offset:x} · inode {row.inode}' if self.platform == 'linux' else
                  self.tr('region_origin_missing'))
        huge_pages = self.tr('region_hugetlb', private=size(row.breakdown.get('private_hugetlb')),
                             shared=size(row.breakdown.get('shared_hugetlb')))
        details.update(Group(
            Text(f'0x{row.start:x}–0x{row.end:x} · {row.permissions} · {origin}', style='bold'),
            Text(f'{self.tr("region_column_virtual")} {size(row.size)} · RSS {size(row.rss)} · PSS {size(row.pss)} · USS {size(row.uss)}'),
            Text(f'Swap {size(row.swap)} · SwapPSS {size(row.swap_pss)} · {breakdown}'),
            Text(f'{self.tr("category_anonymous")} {size(row.breakdown.get("anonymous"))} · '
                 f'THP {size(row.breakdown.get("anon_huge_pages"))} · {huge_pages}'),
            Text('VmFlags: ' + (' '.join(row.vm_flags) or 'n/a'), style='grey70'),
            Text(self.tr('region_type_caution'), style='grey70')))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        event.stop()
        generation, _, key = str(event.row_key.value).partition('|')
        if self.comparison_mode:
            if generation == str(self.generation) and key in self.comparison_rows:
                self.selected = key
                self.render_comparison_inspector()
            return
        if generation == str(self.generation) and key in self.rows:
            self.selected = key
            self.render_map()
            self.render_inspector()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        if self._search_timer is not None:
            self._cancel_search_timer()
            self.render_regions()
            return  # The selected row was from the old filter generation.
        if self.comparison_mode:
            return
        generation, _, key = str(event.row_key.value).partition('|')
        if generation == str(self.generation) and key in self.rows:
            self.selected = key
            self.action_zoom()

    def on_region_map_chosen(self, event: RegionMap.Chosen) -> None:
        event.stop()
        if self._search_timer is not None:
            self._cancel_search_timer()
            self.render_regions()
            return
        if self.comparison_mode:
            return
        if event.key in self.rows:
            self.selected = event.key
            index = list(self.rows).index(event.key)
            if event.key not in self.page_keys:
                self.page = index // self.PAGE_SIZE
                self.render_regions()
            self.query_one('#region-table', DataTable).move_cursor(row=self.page_keys.index(event.key), animate=False)
            self.query_one('#region-table', DataTable).focus()
            self.render_map()
            self.render_inspector()

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        if self.is_mounted:
            self._cancel_search_timer()
            self.page = 0
            self.render_regions()

    def _cancel_search_timer(self) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
            self._search_timer = None

    def _apply_search(self) -> None:
        self._search_timer = None
        if self.is_mounted:
            self.page = 0
            self.render_regions()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if self.is_mounted:
            self._cancel_search_timer()
            if self.query_one('#region-filters').display:
                self._search_timer = self.set_timer(.15, self._apply_search)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._cancel_search_timer()
        self.page = 0
        self.render_regions()
        self.query_one('#region-table', DataTable).focus()

    def action_mode(self) -> None:
        if self.comparison_mode:
            metrics = ('rss', 'pss', 'uss', 'swap', 'size')
            self.comparison_metric = metrics[(metrics.index(self.comparison_metric) + 1) % len(metrics)]
            self.render_regions()
            return
        self.mode = 'virtual' if self.mode == 'resident' else 'resident'
        self.render_map()

    def action_sort(self) -> None:
        self.page = 0
        if self.comparison_mode:
            self.comparison_sort = (self.comparison_sort + 1) % 4
        else:
            self.sort_index = (self.sort_index + 1) % len(self.SORTS)
        self.render_regions()

    def _change_page(self, step: int) -> None:
        count = len(self.comparison_rows) if self.comparison_mode else len(self.rows)
        pages = max(1, (count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        new_page = max(0, min(pages - 1, self.page + step))
        if new_page != self.page:
            self.page = new_page
            self.selected = None
            self.render_regions()

    def action_previous_page(self) -> None:
        self._change_page(-1)

    def action_next_page(self) -> None:
        self._change_page(1)

    def action_zoom(self) -> None:
        if self.comparison_mode:
            return
        self.zoom_key = None if self.zoom_key else self.selected
        self.render_map()

    def action_search(self) -> None:
        self.query_one('#region-filters').display = True
        self.query_one('#region-search', Input).focus()

    def action_filters(self) -> None:
        self.query_one('#region-filters').display = True
        self.query_one('#region-kind', Select).focus()

    def action_baseline(self) -> None:
        if self.current_capture is None or not self.current_capture.complete:
            self.notify(self.tr('region_notice_baseline_complete'), severity='warning')
            return
        self._invalidate_comparison()
        self.baseline = self.current_capture
        self.render_regions()
        self.notify(self.tr('region_notice_baseline_set'))

    def action_clear_baseline(self) -> None:
        self.baseline = None
        self._invalidate_comparison()
        if self.comparison_mode:
            self.comparison_mode = False
            self.page = 0
            self.set_columns(False)
            self.query_one('#comparison-state', Select).display = False
        self.render_regions()

    def action_compare(self) -> None:
        if not self.baseline or not self.current_capture:
            self.notify(self.tr('region_notice_need_samples'), severity='warning')
            return
        if not self.comparison_mode and self._comparison_error:
            # Only an explicit re-entry retries an error. Ordinary repaints
            # must never create an uncontrolled retry loop.
            self._invalidate_comparison()
        self.comparison_mode = not self.comparison_mode
        if not self.comparison_mode and self._comparison_pending is not None:
            self._invalidate_comparison()
        self.page = 0
        self.query_one('#comparison-state', Select).display = self.comparison_mode
        self.selected = None
        self.set_columns(self.comparison_mode)
        self.render_regions()

    def action_save_capture(self) -> None:
        if not self.current_capture:
            self.notify(self.tr('region_none'), severity='warning')
            return
        from .capture_dialog import CaptureSaveScreen
        self.app.push_screen(CaptureSaveScreen(self.current_capture, self.baseline))

    def action_open_capture(self) -> None:
        from .capture_dialog import CaptureOpenScreen
        self.app.push_screen(CaptureOpenScreen(), self.open_loaded_capture)

    def open_loaded_capture(self, loaded) -> None:
        if loaded is None:
            return
        c = loaded.current
        process = ProcessMemory(c.pid, c.started_at, c.name, None, c.executable_identity)
        self.app.push_screen(RegionScreen(process, c.platform, offline_capture=c,
                                          offline_baseline=loaded.baseline))

    def comparison_for_current(self):
        """Return cached result or start a worker for the immutable A/B captures.

        All callbacks are guarded by a request generation *and* capture identity;
        cancelling a thread is cooperative and never publishes partial results.
        """
        if self.baseline is None or self.current_capture is None:
            return None
        current = (self.baseline, self.current_capture)
        if (self._comparison_inputs is not None and self._comparison_inputs[0] is current[0]
                and self._comparison_inputs[1] is current[1]):
            return self._comparison_result
        if (self._comparison_pending is None or self._comparison_pending[0] is not current[0]
                or self._comparison_pending[1] is not current[1]):
            self._invalidate_comparison()
            self._comparison_pending = current
            self.calculate_comparison(self._comparison_request, *current)
        return None

    def _invalidate_comparison(self) -> None:
        self._comparison_request += 1
        self._comparison_inputs = self._comparison_result = self._comparison_pending = None
        self._comparison_error = None
        if self.is_mounted:
            self.workers.cancel_group(self, 'region-comparison')

    @work(thread=True, exclusive=True, group='region-comparison', description='Confronto regioni A/B')
    def calculate_comparison(self, request: int, baseline: CaptureSnapshot, current: CaptureSnapshot) -> None:
        worker = get_current_worker()
        try:
            result = compare_captures(baseline, current, cancelled=lambda: worker.is_cancelled)
        except ComparisonCancelled:
            return
        except Exception as error:
            result = error
        if not worker.is_cancelled:
            try:
                self.app.call_from_thread(self.accept_comparison, request, baseline, current, result)
            except RuntimeError:
                pass

    def accept_comparison(self, request: int, baseline: CaptureSnapshot, current: CaptureSnapshot, result) -> None:
        if (not self.is_mounted or request != self._comparison_request or not self.comparison_mode
                or baseline is not self.baseline or current is not self.current_capture):
            return
        self._comparison_pending = None
        if isinstance(result, Exception):
            self._comparison_inputs = (baseline, current)
            self._comparison_result = None
            self._comparison_error = self.tr('comparison_unavailable', reason=type(result).__name__)
            self.render_comparison()
            return
        self._comparison_inputs = (baseline, current)
        self._comparison_result = result
        self.render_comparison()

    def render_comparison(self) -> None:
        self.query_one('#region-map', RegionMap).display = False
        bar = self.query_one('#delta-bar', DeltaBar)
        bar.display = True
        bar.set_values(None, None)
        table = self.query_one('#region-table', DataTable)
        table.clear()
        self.generation += 1
        self.comparison_rows = {}
        self.query_one('#region-map', RegionMap).set_regions([], 'resident', None)
        self.query_one('#region-legend', Static).update('')
        self.query_one('#region-map-note', Static).update(self.tr('comparison_hint'))
        if not self.baseline or not self.current_capture:
            self.query_one('#region-map-title', Static).update(self.tr('comparison_missing_current'))
            self.query_one('#region-count', Static).update('')
            self.render_comparison_inspector()
            return
        result = self.comparison_for_current()
        if result is None:
            self.query_one('#region-map-title', Static).update(self._comparison_error or self.tr('comparison_loading'))
            self.query_one('#region-count', Static).update('')
            self.render_comparison_inspector()
            return
        if not result.compatible:
            reason = localize(result.reason, getattr(self.app, 'language', 'it'))
            self.query_one('#region-map-title', Static).update(Text(self.tr('comparison_unavailable', reason=reason), style='yellow'))
            self.query_one('#region-count', Static).update('')
            self.render_comparison_inspector()
            return
        metric = self.comparison_metric
        def signed(value):
            return 'n/a' if value is None else ('+' if value > 0 else '−' if value < 0 else '') + size(abs(value))
        title = self.tr('comparison_total_delta', metric=self.metric_label(metric), delta=signed(result.totals[metric]))
        if result.reverse_order:
            title += ' · ' + self.tr('comparison_reverse')
        self.query_one('#region-map-title', Static).update(Text(title, style='bold'))
        a_total, b_total = self.baseline.total(metric), self.current_capture.total(metric)
        scale = max(a_total, b_total) if a_total is not None and b_total is not None else None
        bar.set_values(result.totals[metric], scale)
        self.query_one('#region-legend', Static).update(Text(self.tr('comparison_scale', size=size(scale))))
        query = self.query_one('#region-search', Input).value.strip().casefold()
        kind = self.query_one('#region-kind', Select).value
        state = self.query_one('#region-state', Select).value
        status = self.query_one('#comparison-state', Select).value
        visible = [row for row in result.rows
                   if (status == 'all' or row.status == status)
                   and filter_regions(list(row.after + row.before), query, str(kind), str(state),
                                      getattr(self.app, 'language', 'it'))]
        sort = self.tr(('comparison_sort_growth', 'comparison_sort_reduction',
                        'comparison_sort_absolute', 'comparison_sort_address')[self.comparison_sort])
        def sort_key(row):
            delta = row.delta(metric)
            if self.comparison_sort == 3:
                return (row.start,)
            if delta is None:
                return (True, 0, row.start)
            value = (-delta if self.comparison_sort == 0 else delta if self.comparison_sort == 1 else -abs(delta))
            return (False, value, row.start)
        visible.sort(key=sort_key)
        self.comparison_rows = {row.key: row for row in visible}
        pages = max(1, (len(visible) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        page_rows = visible[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]
        self.page_keys = [row.key for row in page_rows]
        for row in page_rows:
            region = (row.after or row.before)[0]
            table.add_row(f'{row.start:x}–{row.end:x}', Text(self.comparison_label(row.status)), size(row.value_a(metric)),
                          size(row.value_b(metric)), signed(row.delta(metric)),
                          Text(region.path or '[' + self.tr('category_anonymous').lower() + ']'),
                          key=f'{self.generation}|{row.key}')
        self.query_one('#region-count', Static).update(self.tr('comparison_count', shown=len(self.comparison_rows),
            total=len(result.rows), metric=self.metric_label(metric), sort=sort, page=self.page + 1, pages=pages))
        if self.selected not in self.page_keys:
            self.selected = self.page_keys[0] if self.page_keys else None
        if self.selected:
            table.move_cursor(row=self.page_keys.index(self.selected), animate=False)
        self.render_comparison_inspector()

    def render_comparison_inspector(self) -> None:
        panel = self.query_one('#region-inspector', VerticalScroll)
        details = self.query_one('#region-details', Static)
        row = self.comparison_rows.get(self.selected)
        panel.border_title = self.tr('comparison_inspector_title')
        if row is None:
            details.update(self.tr('comparison_no_intervals'))
            return
        lines = [Text(f'{self.comparison_label(row.status)} · 0x{row.start:x}–0x{row.end:x}', style='bold')]
        for metric in ('rss', 'pss', 'uss', 'swap', 'size'):
            delta = row.delta(metric)
            change = 'n/a' if delta is None else ('+' if delta > 0 else '−' if delta < 0 else '') + size(abs(delta))
            lines.append(Text(f'{self.metric_label(metric)} · A {size(row.value_a(metric))} · B {size(row.value_b(metric))} · Δ {change}'))
        change_labels = {'permissions': 'region_column_permissions', 'path': 'region_column_file',
                         'category': 'region_column_type'}
        changes = ', '.join(self.tr(change_labels[name]) if name in change_labels else name for name in row.changes)
        changes = changes or self.tr('comparison_no_changes')
        lines.append(Text(self.tr('comparison_attributes', changes=changes), style='grey70'))
        lines.append(Text(self.tr('comparison_caution'), style='yellow'))
        details.update(Group(*lines))

    def action_back(self) -> None:
        if self.query_one('#region-filters').display:
            self._cancel_search_timer()
            self.query_one('#region-search', Input).value = ''
            self.query_one('#region-kind', Select).value = 'all'
            self.query_one('#region-state', Select).value = 'all'
            self.query_one('#comparison-state', Select).value = 'all'
            self.query_one('#region-filters').display = False
            self.query_one('#region-table', DataTable).focus()
            self.render_regions()
        elif self.zoom_key:
            self.zoom_key = None
            if self.comparison_mode:
                self.render_comparison()
            else:
                self.render_map()
        else:
            self.action_close()

    def action_close(self) -> None:
        self._cancel_search_timer()
        self.request_id += 1
        self.workers.cancel_node(self)
        self.dismiss()
