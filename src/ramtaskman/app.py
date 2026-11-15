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
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Input, Markdown, Select, Static
from textual.worker import get_current_worker

from .collector import Collector
from .models import ApplicationMemory, ProcessMemory, Snapshot
from .filters import MEMORY_FILTERS, RowFilter, owner_options
from .detail import GROUPING_LABELS, breakdown_summary, detail_content
from .report import size
from .ram_bar import SystemRamBar
from .region_screen import RegionScreen
from .widgets import spark

HELP_MD = """\
# ramtaskman · come leggere i numeri

Stessa struttura visiva di gputaskman, dedicata alla memoria di Linux, Windows e macOS.

| Campo | Significato |
|---|---|
| PSS | RAM privata + quota proporzionale delle pagine condivise |
| USS | Private_Clean + Private_Dirty: pagine residenti private |
| RSS | Pagine residenti, comprese quelle condivise: sommare può duplicarle |
| Swap | Swap da smaps_rollup, esclusa la swap shmem; può duplicare pagine condivise |
| SwapPSS | Quota proporzionale della swap condivisa contabilizzata da smaps_rollup |
| RAM used | MemTotal − MemAvailable: non coincide con la somma dei processi |
| Cache | Cached + Buffers + SReclaimable − Shmem; si sovrappone alla memoria disponibile |
| PSI some | Percentuale di tempo con almeno un task in attesa di memoria, media su 10 s |

**Barra RAM:** occupa tutta la larghezza e ripartisce i contatori OS Linux:
anonima, file cache (Cached − Shmem), condivisa/tmpfs, buffer, slab recuperabile/non
recuperabile, altro (residuo calcolato) e libera. Sono categorie contabili: l'ordine non
rappresenta indirizzi fisici. Disponibile è un indicatore separato e include cache
recuperabile, quindi non è un ulteriore segmento. I dettagli clean/dirty e PSS del
processo restano nella vista **d**, perché si sovrappongono ai contatori globali.
Se mancano campi o il campione è incoerente, la barra mostra in uso/disponibile e il
motivo della ripartizione assente. La legenda riporta anche categorie inferiori a un carattere.

**Windows/macOS:** USS e RSS da psutil; PSS, Swap e SwapPSS per processo non sono
esposti e restano n/a. Su Windows il private commit/pagefile NON è swap su disco.
Su macOS RAM used è total − available da psutil, non la Memory Pressure di Activity Monitor.

**Applicazione:** su Linux un cgroup systemd esplicito identifica l'istanza dell'app,
anche con helper diversi. Utenti e istanze distinte restano separati. Senza questa
identità (anche su Windows/macOS) si usa utente + eseguibile, oppure utente + nome
come euristica se il percorso non è leggibile. L'inspector indica il metodo usato.

**Ricerca e filtri:** premi **/** per cercare nome, eseguibile o PID esatto; **f** per
scegliere utente e stato memoria (**con swap** o **dati parziali**). Si combinano fra loro.
Un'applicazione corrisponde se un suo processo soddisfa la ricerca o lo stato memoria,
ma il totale mantiene tutti i membri. Entrando nella vista processi rimangono i filtri.
I filtri agiscono prima del limite Top 30; grafici e dashboard descrivono il sistema intero.
**Invio** dalla ricerca torna alla tabella. **Esc** dai controlli o **Reset** cancella i
filtri; **Esc** nella tabella dei processi torna alle app conservandoli. Dati parziali
considera solo i contatori supportati dal sistema; swap sconosciuta non significa swap usata.

**d** apre il dettaglio RAM del gruppo o processo: PSS anonima/file/shmem, privata e
condivisa clean/dirty, pagine anonime, LazyFree e THP. Campi solo Linux: altrove n/a.
Le righe sono viste sovrapposte, non vanno sommate tutte. Il dettaglio fissa il campione
all'apertura: chiudi e riapri per aggiornarlo. **Esc** o **d** chiude il dettaglio.

**r** o **Invio** su un processo apre la mappa delle regioni Linux. Dentro un'app,
**r** mostra prima i PID: ogni processo ha un proprio spazio virtuale. Le barre di **d**
ripartiscono separatamente PSS e RSS; la swap resta fuori dalla RAM residente.
Nella mappa: **v** alterna RSS/indirizzi virtuali, **s** ordina, **/** cerca file o
indirizzo 0x…, **f** filtra tipo/stato, **z** o **Invio** ingrandisce il vicinato della
regione selezionata, **r** aggiorna, **Esc** azzera i filtri/esce dallo zoom/torna indietro.
La mappa segue gli indirizzi virtuali, non i frame fisici. I buchi sono esclusi dalla
scala virtuale e segnalati con │; le regioni inferiori a un carattere restano in tabella.
Tipo indica l'origine della mappatura, non il suo contenuto: file può avere pagine CoW
private; heap/stack sono solo quelli riconosciuti. I campioni sono su richiesta e
mostrano età, durata e limiti di lettura. Windows: solo intervalli virtuali sperimentali;
macOS: mappa per regioni non disponibile.

Nelle regioni **b** fissa A, **r** raccoglie B e **c** apre il confronto. In confronto,
**v** cambia metrica, **s** ordine, **f** filtra lo stato e **Ctrl+B** rimuove A.
**Ctrl+S** salva i campioni, **Ctrl+O** apre un file offline. I file contengono metadati
e possono includere percorsi personali. I dati mancanti e le regioni riorganizzate
restano n/a; stesso intervallo non dimostra la stessa allocazione né un memory leak.

**n/a non è zero.** Un totale di applicazione è n/a se manca anche un solo valore.
Letture indica la copertura PSS/USS. I totali visibili nel dashboard sono somme
parziali delle sole letture disponibili e non rappresentano tutta la RAM del sistema.
Le letture non sono atomiche: i processi possono cambiare durante il campionamento.
Altri utenti, sandbox e permessi procfs possono impedire le letture. Nessuna elevazione automatica.
HugeTLB non è incluso nei normali contatori RSS/PSS/USS qui mostrati.

Il programma legge metadati: non legge /proc/PID/mem, cmdline, environment o contenuti delle app.

**g** applicazioni/processi · **Invio** processi dell'app selezionata · **Esc** torna alle app
**s** ordinamento · **c** grafico · **a** tutti/primi 30 · **m** compatto/completo
**/** ricerca · **f** filtri · **d** dettagli · **r** regioni · **p** pausa · **?** aiuto · **q** esci

Grafici: ultimi 60 campioni, percentuali con scala 0–100. Lo spazio vuoto indica un dato assente.
L'intervallo è una pausa dopo la rilevazione: la durata effettiva include il tempo di scansione.
"""


class HelpScreen(ModalScreen):
    BINDINGS = [Binding('escape,q,question_mark', 'app.pop_screen', 'Close')]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > VerticalScroll { width: 140; max-width: 95%; height: 85%; border: thick $accent; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(HELP_MD)


class MemoryDetailScreen(ModalScreen):
    BINDINGS = [Binding('escape,d,q', 'app.pop_screen', 'Close')]
    DEFAULT_CSS = """
    MemoryDetailScreen { align: center middle; }
    MemoryDetailScreen > VerticalScroll { width: 140; max-width: 95%; height: 85%; border: round $secondary; background: $surface; padding: 1 2; }
    """

    def __init__(self, row: ApplicationMemory | ProcessMemory, platform: str) -> None:
        super().__init__()
        self.content = detail_content(row, platform)

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(self.content)


class RamTaskManager(App):
    TITLE = 'ramtaskman'
    CSS_PATH = 'app.tcss'
    BINDINGS = [
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
                 processes: bool = False, live: bool = True, region_reader=None) -> None:
        super().__init__()
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
        self.monitoring = False
        self.selected_key: str | None = None
        self.rows: dict[str, ProcessMemory | ApplicationMemory] = {}
        self.histories = {name: deque(maxlen=60) for name in self.CHARTS}
        self.row_filter = RowFilter()
        self.filters_open = False
        self._owner_options: list[tuple[str, str]] = []
        self._updating_filters = False
        self._row_generation = 0

    def compose(self) -> ComposeResult:
        with VerticalScroll(id='dashboard'):
            yield Static('Sampling RAM counters...', id='device')
            yield Static('Sampling system memory...', id='system')
            with Vertical(id='history'):
                with Horizontal(id='chart-controls'):
                    yield Static('Charts', id='chart-label')
                    yield Select([('All charts', -1), *((n, i) for i, n in enumerate(self.CHARTS))],
                                 value=-1, allow_blank=False, compact=True, id='chart-mode')
                    yield Static('Click to choose · c cycles', id='chart-hint')
                yield Static(id='charts')
                yield Static(id='chart-note')
        with Vertical(id='filters'):
            yield Input(placeholder='Cerca nome, eseguibile o PID esatto · Invio: tabella · Esc: reset', id='search')
            with Horizontal(id='filter-controls'):
                yield Select([('Tutti gli utenti', 'all')], value='all', allow_blank=False,
                             compact=True, id='user-filter')
                yield Select(MEMORY_FILTERS, value='all', allow_blank=False,
                             compact=True, id='memory-filter')
                yield Button('Reset', id='reset-filters', compact=True)
            yield Static(id='filter-status')
        yield DataTable(id='procs', cursor_type='row', zebra_stripes=True)
        yield Static('', id='inspector')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#procs', DataTable)
        for col in ('PID / N', 'Application / Process', 'User / UID', 'PSS', 'USS', 'RSS', 'Swap', 'SwapPSS', 'PSS%', 'Letture', "What's inside"):
            table.add_column(col, key=col)
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
                    if not worker.is_cancelled:
                        self.call_from_thread(self.show_error, f'{type(error).__name__}: {error}')
                else:
                    if not worker.is_cancelled:
                        self.call_from_thread(self.apply, snap)
            worker.cancelled_event.wait(self.interval)

    def show_error(self, reason: str) -> None:
        self.snap = None
        self.rows.clear()
        self.selected_key = None
        self.query_one('#procs', DataTable).clear()
        for history in self.histories.values():
            history.append(None)
        for widget in ('device', 'system', 'charts', 'inspector'):
            self.query_one(f'#{widget}', Static).update(Text('Rilevazione non disponibile: ' + reason, style='yellow'))

    def apply(self, snap: Snapshot) -> None:
        if self.paused:
            return
        self.snap = snap
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

    def render_dashboard(self) -> None:
        if not self.snap:
            return
        s, m = self.snap, self.snap.system
        bar = SystemRamBar(m)
        top = [Text(f'RAM del sistema · {s.platform} · ' + ('Ripartizione OS' if bar.detailed else 'Disponibilità'), style='bold'), bar, bar.legend(),
               Text(f'Totale {size(m.total)} · Uso netto {size(m.used)} · Disponibile {size(m.available)}', style='bold')]
        if bar.detailed:
            top.append(Text('Uso netto = totale − disponibile · Altro = residuo contabile.', style='grey70'))
        else:
            top.append(Text('Ripartizione OS n/a: ' + (m.segments_reason or 'contatori non esposti da questo backend') +
                            '. Barra: in uso / disponibile.', style='yellow'))
        if not self.monitoring:
            top.append(Text(f'PSS visible {size(s.visible_sum("pss"))}  USS visible {size(s.visible_sum("uss"))}  '
                            f'Swap {size(m.swap_used)} / {size(m.swap_total)}'))
        panel = self.query_one('#device', Static)
        panel.border_title = ('Slim monitoring' if self.monitoring else 'Full diagnostics') + (' · PAUSED' if self.paused else '')
        panel.update(Group(*top))
        system = self.query_one('#system', Static)
        system.border_title = 'System (OS-reported)'
        cpu = 'n/a' if m.cpu_percent is None else f'{m.cpu_percent:.0f}%'
        psi = 'n/a' if m.pressure_percent is None else f'{m.pressure_percent:.2f}%'
        status = Text(f'CPU {cpu}   Memory pressure (PSI some, 10s) {psi}\n')
        status.append(f'Letture PSS {s.measured}/{len(s.processes)} · USS {s.coverage("uss")}/{len(s.processes)} · {len(s.applications)} gruppi · '
                      f'non raccolti/terminati {s.skipped} · scan {s.sample_ms:.0f} ms\n')
        status.append('Totali dei processi visibili parziali. n/a = dato non disponibile.', style='yellow')
        if s.measurement_attempted is not None:
            status.append(f'\nBudget: {s.measurement_attempted} misure tentate · {s.measurement_deferred} rinviate · '
                          f'identità {"complete" if s.enumeration_complete else "incomplete: totali app n/a"}', style='yellow')
        elif not s.enumeration_complete:
            status.append('\nIdentità incomplete: totali app n/a.', style='yellow')
        if s.unsupported:
            status.append('\nPSS / Swap / SwapPSS per processo: n/a su questo backend. RSS e USS ove leggibili.', style='yellow')
        for note in m.notes:
            status.append('\n' + note, style='grey62')
        system.update(status)
        self.render_charts()

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
            cell = Text(f'{name:<12} ', style=self.CHART_COLORS[name])
            cell.append(f'{label:>8} ', style='bold')
            cell.append(spark(values, max(1, cell_width - 22), 100))
            cells.append(cell)
        for start in range(0, len(cells), columns):
            grid.add_row(*cells[start:start + columns])
        self.query_one('#charts', Static).update(grid)
        self.query_one('#chart-note', Static).update(
            f'Last 60 samples · 0–100% · blank = no reading · pause between scans {self.interval:g}s')

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
            info = GROUPING_LABELS[row.grouping] if grouped else (row.reason or ('smaps_rollup' if self.snap.platform == 'linux' else 'psutil: RSS / USS'))
            if grouped and not row.membership_complete:
                info += ' · membri incompleti'
            table.add_row(str(count) + ' procs' if grouped else str(row.pid), Text(row.name),
                          Text(str(row.uid) if row.uid is not None else (row.user or 'n/a')),
                          *(size(self.metric(row, m)) for m in self.SORTS[:-1]),
                          f'{100 * pss / self.snap.system.total:.1f}' if pss is not None and self.snap.system.total else 'n/a',
                          f'P {measured}/{count} U {sum(p.uss is not None for p in row.processes) if grouped else int(row.uss is not None)}/{count}', Text(info), key=f'{generation}|{row.key}')
        keys = list(self.rows)
        index = keys.index(selected) if selected in self.rows else 0
        self.selected_key = keys[index] if keys else None
        if keys:
            table.move_cursor(row=index, animate=False)
        self.sub_title = f'{"Processes" if self.process_view else "Applications"} · {metric.upper()} · {"All" if self.show_all else "Top 30"}'
        self.sub_title += f' · {len(rows)}/{matching}/{total}'
        self.query_one('#inspector', Static).border_subtitle = self.sub_title
        status = f'{len(rows)} mostrate · {matching} corrispondenti / {total} righe · grafici: sistema intero'
        if self.row_filter.memory == 'swap' and 'swap' in self.snap.unsupported:
            status = 'Swap per processo non disponibile su questo sistema; filtro senza risultati.'
        self.query_one('#filter-status', Static).update(Text(status))
        self.render_inspector()

    def render_inspector(self) -> None:
        row = self.rows.get(self.selected_key)
        panel = self.query_one('#inspector', Static)
        if row is None:
            panel.border_title = 'Inspector'
            panel.update('Nessun risultato. /: cerca · f: filtri · Esc: reset o ritorno alle app.' if self.row_filter.active else 'Nessuna riga disponibile.')
            return
        grouped = isinstance(row, ApplicationMemory)
        panel.border_title = Text(row.name)
        counters = '  '.join(f'{m.upper()} {size(self.metric(row, m))}' for m in self.SORTS[:-1])
        processes = row.processes if grouped else [row]
        pids = ', '.join(str(p.pid) for p in processes[:20]) + (' …' if len(processes) > 20 else '')
        reasons = sorted({p.reason for p in processes if p.reason})
        panel.update(Group(Text(counters, style='bold'),
                           breakdown_summary(row),
                           Text(f'PID: {pids} · ' + ('Invio: esplora i processi del gruppo.' if grouped else 'Invio / r: regioni · Esc: applicazioni.')),
                           Text((GROUPING_LABELS[row.grouping] + ': ' + (row.grouping_id or 'n/a')) if grouped else ('Eseguibile: ' + (row.executable or 'n/a')), style='grey62'),
                           Text(' · '.join(reasons) if reasons else 'Fonte: metadati del kernel; nessuna lettura dei contenuti della memoria.',
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
            self.push_screen(MemoryDetailScreen(row, self.snap.platform))

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
