"""Textual layout adapted from Scott Hanselman's gputaskman (MIT)."""
from __future__ import annotations

from collections import deque

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Input, Markdown, Select, Static
from textual.worker import get_current_worker

from .collector import Collector
from .valuation import RamPrice, value_text
from .models import ApplicationMemory, ProcessMemory, Snapshot, SystemMemory
from .filters import RowFilter, owner_options
from .detail import breakdown_summary, detail_content
from .report import size
from .ram_bar import SystemRamBar
from .application_bar import application_uss_bar
from .region_screen import RegionScreen
from .widgets import spark
from .i18n import LANGUAGES, load_help, translate
from .localized_screen import LocalizedModalScreen, LocalizedScreen
from .messages import error_text, localize, message

class HelpScreen(LocalizedModalScreen):
    BINDINGS = [Binding('escape,q,question_mark', 'app.pop_screen', 'Close')]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > VerticalScroll { width: 140; max-width: 95%; height: 85%; border: thick $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(load_help(getattr(self.app, 'language', 'it')))


class AboutScreen(LocalizedModalScreen):
    BINDINGS = [Binding('escape,q,f1', 'app.pop_screen', 'Close')]
    DEFAULT_CSS = """
    AboutScreen { align: center middle; }
    AboutScreen > VerticalScroll { width: 86; max-width: 95%; height: 85%; border: round $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        from . import __version__
        with VerticalScroll():
            yield Static("┌─────────┐\n│ ▄▄▄▄▄▄▄ │\n│ V W   ▣ │\n│ ▄▄▄▄▄▄▄ │\n└─────────┘  VibeWare", markup=False)
            yield Markdown(f"# Ram Taskman {__version__}\n\n" + self.app.tr('about_body'))
            yield Button(self.app.tr('footer_close'), id='close-about')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'close-about':
            self.app.pop_screen()


class MemoryDetailScreen(LocalizedModalScreen):
    BINDINGS = [Binding('escape,d,q', 'app.pop_screen', 'Close')]
    DEFAULT_CSS = """
    MemoryDetailScreen { align: center middle; }
    MemoryDetailScreen > VerticalScroll { width: 140; max-width: 95%; height: 85%; border: round $secondary; background: $surface; padding: 1 2; }
    """

    def __init__(self, row: ApplicationMemory | ProcessMemory, platform: str, language: str = 'it') -> None:
        super().__init__()
        self.content = detail_content(row, platform, language)

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(self.content)


class RamTaskManager(App):
    TITLE = 'ramtaskman'
    CSS_PATH = 'app.tcss'
    BINDINGS = [
        Binding('f1', 'about', 'About'),
        Binding('q', 'quit', 'Quit'), Binding('s', 'cycle_sort', 'Sort'),
        Binding('c', 'cycle_chart', 'Chart'), Binding('a', 'toggle_all', 'All/Top'),
        Binding('g', 'toggle_group', 'Apps/PIDs'), Binding('m', 'toggle_monitoring', 'Slim/Full'),
        Binding('p', 'pause', 'Pause'), Binding('question_mark', 'help', 'Explain'),
        Binding('slash', 'search', 'Search'), Binding('f', 'filters', 'Filter'),
        Binding('d', 'detail', 'Detail'),
        Binding('r', 'regions', 'Regions'),
        Binding('escape', 'back', 'Apps / Clear', show=False),
    ]
    SORTS = ('pss', 'uss', 'rss', 'swap', 'swap_pss', 'name')
    CHART_COLORS = {
        'RAM': '#60a5fa', 'PSS visible': '#4ade80', 'USS visible': '#a78bfa',
        'Swap': '#fb923c', 'Cache': '#22d3ee', 'PSI some': '#ef4444',
    }
    CHARTS = tuple(CHART_COLORS)

    def __init__(self, collector: Collector | None = None, interval: float = 2.0,
                 processes: bool = False, live: bool = True, region_reader=None, *, slim: bool = True,
                 language: str = 'it', ram_price: RamPrice | None = None) -> None:
        super().__init__()
        self.ram_price = ram_price
        if language not in LANGUAGES:
            raise ValueError(translate('it', 'invalid_language', code=language))
        self.language = language
        self.collector = collector
        self.interval = interval
        self.live = live
        self.region_reader = region_reader
        self.process_view = processes
        self.app_filter: str | None = None
        self.snap: Snapshot | None = None
        self.sort_idx = 0
        self._default_sort_set = False
        self.chart_idx = -1
        self.paused = False
        self.show_all = False
        self.monitoring = slim
        self.selected_key: str | None = None
        self.rows: dict[str, ProcessMemory | ApplicationMemory] = {}
        self.histories = {name: deque(maxlen=60) for name in self.CHARTS}
        self.row_filter = RowFilter()
        self.filters_open = False
        self._owner_options: list[tuple[str, str]] = []
        self._updating_filters = False
        self._row_generation = 0

    def action_about(self) -> None:
        self.push_screen(AboutScreen())

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def get_default_screen(self) -> LocalizedScreen:
        return LocalizedScreen(id='_default')

    def compose(self) -> ComposeResult:
        with VerticalScroll(id='dashboard'):
            yield Static(self.tr('sampling_ram'), id='device')
            yield Static(self.tr('sampling_system'), id='system')
            with Vertical(id='history'):
                with Horizontal(id='chart-controls'):
                    yield Static(self.tr('charts'), id='chart-label')
                    yield Select([(self.tr('all_charts'), -1), *((self.chart_label(n), i) for i, n in enumerate(self.CHARTS))],
                                 value=-1, allow_blank=False, compact=True, id='chart-mode')
                    yield Static(self.tr('chart_hint'), id='chart-hint')
                yield Static(id='charts')
                yield Static(id='chart-note')
        with Vertical(id='filters'):
            yield Input(placeholder=self.tr('search'), id='search')
            with Horizontal(id='filter-controls'):
                yield Select([(self.tr('all_users'), 'all')], value='all', allow_blank=False,
                             compact=True, id='user-filter')
                yield Select([(self.tr('all_memory'), 'all'), (self.tr('with_swap'), 'swap'),
                              (self.tr('partial_data'), 'partial')], value='all', allow_blank=False,
                             compact=True, id='memory-filter')
                yield Button(self.tr('reset'), id='reset-filters', compact=True)
            yield Static(id='filter-status')
        yield DataTable(id='procs', cursor_type='row', zebra_stripes=True)
        yield Static('', id='inspector')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#procs', DataTable)
        for key, col in (('pid', 'PID / N'), ('app', self.tr('app_process')), ('user', self.tr('user')),
                         ('pss', 'PSS'), ('uss', 'USS'), ('rss', 'RSS'), ('swap', 'Swap'),
                         ('swap_pss', 'SwapPSS'), ('pss_pct', 'PSS%'), ('readings', self.tr('readings_col')),
                         ('inside', self.tr('inside'))):
            table.add_column(col, key=key)
            if key == 'app' and self.ram_price:
                table.add_column(self.tr('ram_monthly' if self.ram_price.months else 'ram_value'), key='ram_value')
        table.focus()
        if self.live:
            self.poll()

    @work(thread=True, exclusive=True)
    def poll(self) -> None:
        worker = get_current_worker()
        collector = self.collector or Collector()
        while not worker.is_cancelled:
            if not self.paused:
                try:
                    snap = (collector.sample(cancelled=lambda: worker.is_cancelled)
                            if isinstance(collector, Collector) else collector.sample())
                except Exception as error:
                    # A collector failure must clear stale values, not kill the
                    # worker: the next sampling cycle may recover on its own.
                    if not worker.is_cancelled:
                        reason = message('error_with_type', type=type(error).__name__, reason=error_text(error))
                        self.call_from_thread(self.show_error, reason)
                else:
                    if not worker.is_cancelled:
                        self.call_from_thread(self.apply, snap)
            worker.cancelled_event.wait(self.interval)

    def show_error(self, reason: str) -> None:
        self.snap = None
        self._refresh_region_memory_context()
        self.rows.clear()
        self.selected_key = None
        self.query_one('#procs', DataTable).clear()
        for history in self.histories.values():
            history.append(None)
        for widget in ('device', 'system', 'charts', 'inspector'):
            self.query_one(f'#{widget}', Static).update(Text(self.tr('sample_error', reason=localize(reason, self.language)), style='yellow'))

    def apply(self, snap: Snapshot) -> None:
        if self.paused:
            return
        self.snap = snap
        self._refresh_region_memory_context()
        self.update_owner_options()
        if not self._default_sort_set:
            self.sort_idx = 1 if 'pss' in snap.unsupported else 0
            self._default_sort_set = True
        m = snap.system
        def pct(value: int | None, total: int | None) -> float | None:
            return 100 * value / total if value is not None and total else None
        values = (pct(m.used, m.total), pct(snap.visible_sum('pss'), m.total),
                  pct(snap.visible_sum('uss'), m.total), pct(m.swap_used, m.swap_total),
                  pct(m.cache, m.total), m.pressure_percent)
        for name, value in zip(self.CHARTS, values):
            self.histories[name].append(value)
        self.render_dashboard()
        self.render_table()

    def _refresh_region_memory_context(self) -> None:
        """Update open region screens immediately when the system sample changes."""
        for screen in self.screen_stack:
            if isinstance(screen, RegionScreen) and screen.is_mounted:
                screen.render_memory_context()

    def _platform_details(self, memory: SystemMemory) -> list[Text]:
        """Render overlapping OS counters separately from the RAM partition."""
        lines: list[Text] = []
        linux = memory.linux_details
        if linux is not None:
            lines.append(Text(self.tr('linux_cache_slab', cache=size(memory.cache), slab=size(memory.slab)), style='cyan'))
            lines.append(Text(self.tr('linux_commit', total=size(linux.commit_total), limit=size(linux.commit_limit)), style='magenta'))
            lines.append(Text(self.tr('linux_commit_note'), style='grey70'))

            # Missing optional counters are explicit; they never become zero.
            counters = (('Committed_AS', linux.commit_total), ('CommitLimit', linux.commit_limit),
                        ('cache', memory.cache), ('Slab', memory.slab))
            missing = [name for name, value in counters if value is None]
            if missing:
                lines.append(Text(self.tr('meminfo_missing', fields=', '.join(missing)), style='yellow'))

        windows = memory.windows_details
        if windows is not None:
            lines.append(Text(self.tr('windows_cache_pool', cache=size(windows.system_cache),
                                      paged=size(windows.kernel_paged), nonpaged=size(windows.kernel_nonpaged)), style='cyan'))
            lines.append(Text(self.tr('windows_commit', total=size(windows.commit_total),
                                      limit=size(windows.commit_limit), peak=size(windows.commit_peak)), style='magenta'))
            lines.append(Text(self.tr('windows_memory_note'), style='grey70'))
            if windows.reason:
                lines.append(Text(localize(windows.reason, self.language), style='yellow'))
        return lines

    def render_dashboard(self) -> None:
        if self.snap is None:
            return
        snapshot = self.snap
        memory = snapshot.system
        bar = SystemRamBar(memory, self.language)
        partition_label = self.tr('os_breakdown' if bar.detailed else 'availability')
        heading = f'{self.tr("system_ram")} · {snapshot.platform} · {partition_label}'
        totals = (f'{self.tr("total")} {size(memory.total)} · {self.tr("net_used")} {size(memory.used)} · '
                  f'{self.tr("available")} {size(memory.available)}')
        content = [Text(heading, style='bold'), bar, bar.legend(), Text(totals, style='bold')]

        if bar.detailed:
            content.append(Text(self.tr('net_explanation'), style='grey70'))
        elif snapshot.platform == 'windows' and memory.windows_details is not None and not memory.windows_details.reason:
            content.append(Text(self.tr('ram_overlap_note'), style='grey70'))
        else:
            reason = localize(memory.segments_reason, self.language) if memory.segments_reason else self.tr('os_counters_missing')
            content.append(Text(self.tr('os_breakdown_missing', reason=reason), style='yellow'))

        if not self.monitoring:
            apps_bar = application_uss_bar(snapshot, self.language)
            content.extend((apps_bar.heading(), apps_bar, apps_bar.legend(),
                            Text(self.tr('uss_app_note'), style='grey70')))
            content.extend(self._platform_details(memory))
            content.append(Text(f'{self.tr("pss_visible")} {size(snapshot.visible_sum("pss"))}  '
                                f'{self.tr("uss_visible")} {size(snapshot.visible_sum("uss"))}  '
                                f'Swap {size(memory.swap_used)} / {size(memory.swap_total)}'))

        panel = self.query_one('#device', Static)
        panel_title = self.tr('slim' if self.monitoring else 'full')
        if self.paused:
            panel_title += ' · ' + self.tr('paused')
        panel.border_title = panel_title
        panel.update(Group(*content))

        system = self.query_one('#system', Static)
        system.border_title = self.tr('system')
        cpu = 'n/a' if memory.cpu_percent is None else f'{memory.cpu_percent:.0f}%'
        pressure = 'n/a' if memory.pressure_percent is None else f'{memory.pressure_percent:.2f}%'
        status = Text(f'CPU {cpu}   {self.tr("pressure")} {pressure}\n')
        status.append(f'{self.tr("readings")} PSS {snapshot.measured}/{len(snapshot.processes)} · '
                      f'USS {snapshot.coverage("uss")}/{len(snapshot.processes)} · '
                      f'{len(snapshot.applications)} {self.tr("groups")} · '
                      f'{self.tr("skipped")} {snapshot.skipped} · {self.tr("scan")} {snapshot.sample_ms:.0f} ms\n')
        status.append(self.tr('partial'), style='yellow')
        if snapshot.measurement_attempted is not None:
            identity = self.tr('identity_complete' if snapshot.enumeration_complete else 'identity_incomplete')
            status.append('\n' + self.tr('budget_status', attempted=snapshot.measurement_attempted,
                                        deferred=snapshot.measurement_deferred, identity=identity), style='yellow')
        elif not snapshot.enumeration_complete:
            status.append('\n' + self.tr('identity_incomplete_note'), style='yellow')
        if snapshot.unsupported:
            status.append('\n' + self.tr('unsupported_process_counters'), style='yellow')
        for note in memory.notes:
            status.append('\n' + localize(note, self.language), style='grey62')
        system.update(status)
        self.render_charts()

    def chart_label(self, name: str) -> str:
        """Translate display labels while history keys and colors stay stable."""
        keys = {'PSS visible': 'pss_visible', 'USS visible': 'uss_visible', 'Cache': 'chart_cache'}
        return self.tr(keys[name]) if name in keys else name

    def render_charts(self) -> None:
        width = max(1, self.size.width - 6)
        indices = list(range(len(self.CHARTS))) if self.chart_idx == -1 else [self.chart_idx]
        columns = min(len(indices), 3, max(1, (width + 2) // 46))
        cell_width = max(1, (width - 2 * (columns - 1)) // columns)
        grid = Table.grid(padding=(0, 2), pad_edge=False, expand=True)
        for _ in range(columns):
            grid.add_column(width=cell_width, no_wrap=True, overflow='crop')
        cells = []
        for index in indices:
            name = self.CHARTS[index]
            values = self.histories[name]
            current = values[-1] if values else None
            label = 'n/a' if current is None else f'{current:.1f}%'
            cell = Text(self.chart_label(name), style=self.CHART_COLORS[name])
            cell.truncate(13, overflow='crop', pad=True)
            cell.append(f'{label:>8} ', style='bold')
            cell.append(spark(values, max(1, cell_width - 22), 100))
            cells.append(cell)
        for start in range(0, len(cells), columns):
            grid.add_row(*cells[start:start + columns])
        self.query_one('#charts', Static).update(grid)
        self.query_one('#chart-note', Static).update(
            self.tr('chart_note', interval=f'{self.interval:g}'))

    @staticmethod
    def metric(row: ProcessMemory | ApplicationMemory, metric: str) -> int | None:
        return row.total(metric) if isinstance(row, ApplicationMemory) else getattr(row, metric)

    def render_table(self) -> None:
        if not self.snap:
            return
        rows = self.snap.applications
        if self.process_view:
            rows = ([p for a in rows if a.key == self.app_filter for p in a.processes]
                    if self.app_filter else self.snap.processes)
        total = len(rows)
        rows = [row for row in rows if self.row_filter.matches(row, self.snap.unsupported)]
        matching = len(rows)
        metric = self.SORTS[self.sort_idx]
        rows = sorted(rows, key=lambda r: (r.name.lower(), r.key) if metric == 'name' else
                      (self.metric(r, metric) is None, -(self.metric(r, metric) or 0), r.key))
        if not self.show_all:
            rows = rows[:30]
        self.rows = {r.key: r for r in rows}
        selected = self.selected_key
        table = self.query_one('#procs', DataTable)
        table.clear()
        self._row_generation += 1
        generation = self._row_generation
        for row in rows:
            grouped = isinstance(row, ApplicationMemory)
            pss = self.metric(row, 'pss')
            count = len(row.processes) if grouped else 1
            measured = row.measured if grouped else int(row.pss is not None)
            uss_measured = sum(p.uss is not None for p in row.processes) if grouped else int(row.uss is not None)
            if grouped:
                info = self.tr('group_' + row.grouping)
            else:
                metric_source = 'smaps_rollup' if self.snap.platform == 'linux' else 'psutil: RSS / USS'
                info = localize(row.reason, self.language) if row.reason else metric_source
            if grouped and not row.membership_complete:
                info += ' · ' + self.tr('group_incomplete')

            # Keep values, coverage and row identity separate from display text.
            identity = f'{count} {self.tr("processes").lower()}' if grouped else str(row.pid)
            owner = str(row.uid) if row.uid is not None else (row.user or 'n/a')
            memory_values = [size(self.metric(row, name)) for name in self.SORTS[:-1]]
            system_total = self.snap.system.total
            pss_percent = f'{100 * pss / system_total:.1f}' if pss is not None and system_total else 'n/a'
            coverage = f'P {measured}/{count} U {uss_measured}/{count}'
            row_key = f'{generation}|{row.key}'
            table.add_row(identity, Text(row.name),
                          *([value_text(row, self.snap, self.ram_price)] if self.ram_price else []),
                          Text(owner), *memory_values, pss_percent, coverage, Text(info), key=row_key)
        keys = list(self.rows)
        index = keys.index(selected) if selected in self.rows else 0
        self.selected_key = keys[index] if keys else None
        if keys:
            table.move_cursor(row=index, animate=False)
        sort_label = self.tr('name_label') if metric == 'name' else metric.upper()
        limit_label = self.tr('all' if self.show_all else 'top_thirty')
        self.sub_title = f'{self.tr("processes" if self.process_view else "applications")} · {sort_label} · {limit_label}'
        self.sub_title += f' · {len(rows)}/{matching}/{total}'
        self.query_one('#inspector', Static).border_subtitle = self.sub_title
        status = self.tr('filter_status', shown=len(rows), matching=matching, total=total)
        if self.row_filter.memory == 'swap' and 'swap' in self.snap.unsupported:
            status = self.tr('swap_filter_unsupported')
        self.query_one('#filter-status', Static).update(Text(status))
        self.render_inspector()

    def render_inspector(self) -> None:
        row = self.rows.get(self.selected_key)
        if isinstance(self.collector, Collector) and self.collector.selected_priority:
            self.collector.set_priority((row.pid, row.started_at) if isinstance(row, ProcessMemory) else None)
        panel = self.query_one('#inspector', Static)
        if row is None:
            panel.border_title = self.tr('inspector')
            panel.update(self.tr('no_matches') if self.row_filter.active else self.tr('no_rows'))
            return
        grouped = isinstance(row, ApplicationMemory)
        panel.border_title = Text(row.name)
        counters = '  '.join(f'{m.upper()} {size(self.metric(row, m))}' for m in self.SORTS[:-1])
        if self.ram_price:
            basis = 'PSS' if self.snap.platform == 'linux' else 'USS'
            counters += '\n' + self.tr('ram_monthly' if self.ram_price.months else 'ram_value') + ': ' + value_text(row, self.snap, self.ram_price) + ' · ' + basis
            counters += '\n' + self.tr('ram_value_note')
        processes = row.processes if grouped else [row]
        pids = ', '.join(str(p.pid) for p in processes[:20]) + (' …' if len(processes) > 20 else '')
        reasons = sorted({localize(p.reason, self.language) for p in processes if p.reason})
        panel.update(Group(Text(counters, style='bold'),
                           breakdown_summary(row, self.language),
                           Text(f'PID: {pids} · ' + self.tr('enter_group' if grouped else 'enter_regions')),
                           Text((self.tr('group_' + row.grouping) + ': ' + (row.grouping_id or 'n/a')) if grouped else (self.tr('executable') + ': ' + (row.executable or 'n/a')), style='grey62'),
                           Text(' · '.join(reasons) if reasons else self.tr('source'),
                                style='yellow' if reasons else 'grey62')))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        generation, _, key = str(event.row_key.value).partition('|')
        if generation != str(self._row_generation):
            return
        if key in self.rows:
            self.selected_key = key
            self.render_inspector()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        generation, _, key = str(event.row_key.value).partition('|')
        if generation != str(self._row_generation):
            return
        row = self.rows.get(key)
        if isinstance(row, ApplicationMemory):
            self.app_filter = row.key
            self.process_view = True
            self.selected_key = None
            self.render_table()
        elif isinstance(row, ProcessMemory):
            self.open_regions(row)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ('user-filter', 'memory-filter'):
            self.update_filters_from_controls()
        elif event.select.id == 'chart-mode' and isinstance(event.value, int):
            self.chart_idx = event.value
            self.render_charts()

    def on_resize(self) -> None:
        if self.is_mounted and self.snap:
            self.call_after_refresh(self.render_dashboard)

    def action_cycle_sort(self) -> None:
        self.sort_idx = (self.sort_idx + 1) % len(self.SORTS)
        self.render_table()

    def action_cycle_chart(self) -> None:
        self.query_one('#chart-mode', Select).value = (self.chart_idx + 2) % (len(self.CHARTS) + 1) - 1

    def action_toggle_all(self) -> None:
        self.show_all = not self.show_all
        self.render_table()

    def action_toggle_group(self) -> None:
        self.process_view = not self.process_view
        self.app_filter = None
        self.selected_key = None
        self.render_table()

    def action_back(self) -> None:
        if self.focused is not None and self.query_one('#filters') in self.focused.ancestors:
            self.reset_filters()
            return
        if not self.process_view and self.filters_open:
            self.reset_filters()
            return
        self.process_view = False
        self.selected_key = self.app_filter
        self.app_filter = None
        self.render_table()

    def action_pause(self) -> None:
        self.paused = not self.paused
        self.render_dashboard()

    def action_toggle_monitoring(self) -> None:
        self.monitoring = not self.monitoring
        self.render_dashboard()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_detail(self) -> None:
        row = self.rows.get(self.selected_key)
        if self.snap is not None and row is not None:
            self.push_screen(MemoryDetailScreen(row, self.snap.platform, self.language))

    def open_regions(self, row: ProcessMemory) -> None:
        if self.snap is not None:
            self.push_screen(RegionScreen(row, self.snap.platform, self.region_reader))

    def action_regions(self) -> None:
        row = self.rows.get(self.selected_key)
        if isinstance(row, ApplicationMemory):
            self.app_filter = row.key
            self.process_view = True
            self.selected_key = None
            self.render_table()
        elif isinstance(row, ProcessMemory):
            self.open_regions(row)

    def show_filters(self) -> None:
        self.filters_open = True
        self.query_one('#filters').display = True
        self.screen.add_class('filtering')

    def action_search(self) -> None:
        self.show_filters()
        self.query_one('#search', Input).focus()

    def action_filters(self) -> None:
        self.show_filters()
        self.query_one('#user-filter', Select).focus()

    def update_owner_options(self) -> None:
        if self.snap is None:
            return
        options = owner_options(self.snap.processes)
        options[0] = (self.tr('all_users'), 'all')
        # Keep a selected user in the selector even if their processes have all exited.
        if self.row_filter.owner != 'all' and self.row_filter.owner not in dict((v, k) for k, v in options):
            old_label = next((label for label, value in self._owner_options if value == self.row_filter.owner),
                             self.row_filter.owner)
            options.append((old_label, self.row_filter.owner))
        if options == self._owner_options:
            return
        self._owner_options = options
        self._updating_filters = True
        try:
            selector = self.query_one('#user-filter', Select)
            with selector.prevent(Select.Changed):
                selector.set_options(options)
                selector.value = self.row_filter.owner
        finally:
            self._updating_filters = False

    def update_filters_from_controls(self) -> None:
        if self._updating_filters or not self.is_mounted:
            return
        owner = self.query_one('#user-filter', Select).value
        memory = self.query_one('#memory-filter', Select).value
        if not isinstance(owner, str) or not isinstance(memory, str):
            return
        filters = RowFilter(self.query_one('#search', Input).value, owner, memory)
        if filters == self.row_filter:
            return
        self.row_filter = filters
        self.render_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'search':
            self.update_filters_from_controls()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'search':
            self.query_one('#procs', DataTable).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'reset-filters':
            self.reset_filters()

    def reset_filters(self) -> None:
        self._updating_filters = True
        try:
            self.row_filter = RowFilter()
            self.query_one('#search', Input).value = ''
            self.query_one('#user-filter', Select).value = 'all'
            self.query_one('#memory-filter', Select).value = 'all'
        finally:
            self._updating_filters = False
        self.filters_open = False
        self.query_one('#filters').display = False
        self.screen.remove_class('filtering')
        self.query_one('#procs', DataTable).focus()
        self.render_table()
