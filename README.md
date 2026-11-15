# ramtaskman

Task manager **multipiattaforma per la RAM: Linux, Windows e macOS**, scritto in Python e Textual. Riprende layout,
widget, colori e scorciatoie di [gputaskman di Scott Hanselman](https://github.com/shanselman/gputaskman),
con un collector dedicato a memoria per applicazione, **PSS, USS, RSS, swap e SwapPSS**.

Prima versione funzionante, ancora sperimentale. Interfaccia terminale con pannelli
Full diagnostics → System → Charts → tabella → inspector → footer, come gputaskman.
Le metriche e le etichette sono adattate alla RAM; non è una copia pixel per pixel di ogni stato GPU.

## Avvio

Servono Python >=3.11 e `uv`. Linux richiede `/proc` e `smaps_rollup`.
Su Windows usa Windows Terminal. Su macOS usa Terminal o un terminale compatibile.
La versione minima è dichiarata in pyproject.toml; non viene imposto Python 3.14
su Windows o macOS. La macchina di sviluppo usa Python 3.14.4.

Linux/macOS:

```bash
./run.sh
./run.sh --once
./run.sh --json
./run.sh --processes --interval 2
```

Windows, da PowerShell o Prompt dei comandi:

```powershell
.\run.cmd
.\run.cmd --once
.\run.cmd --json
```

`run.sh` e `run.cmd` possono essere eseguiti da qualsiasi directory. Ambiente e cache delle dipendenze
restano nella cartella del progetto (`.venv`, `.uv-cache`, esclusi da Git).
Il primo avvio installa le dipendenze bloccate in `uv.lock` e richiede rete.
I launcher non scaricano Python automaticamente. Per selezionare esplicitamente un interprete già
installato: `UV_PYTHON=python3.13 ./run.sh`; in PowerShell imposta
`$env:UV_PYTHON = "3.13"` prima di `.\run.cmd`. Non condividere la stessa `.venv` tra
sistemi operativi: ricreala localmente dopo aver copiato il progetto.
La UI non usa GPU, API cloud, servizi esterni o telemetria.

In alternativa, dalla radice del progetto:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv sync --locked
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked ramtaskman
```

Non pubblicato su PyPI: non usare `pip install ramtaskman` per ottenere questa copia.
Non è necessaria l'elevazione dei privilegi; i processi protetti restano parzialmente visibili.

## Supporto per piattaforma

| Funzione | Linux | Windows | macOS |
|---|---|---|---|
| UI Textual, app/processi, grafici, JSON | Implementata | Implementata | Implementata |
| RAM globale e RSS | procfs / psutil | psutil / working set | psutil |
| USS | Private_Clean + Private_Dirty | psutil, memoria residente privata | psutil, memoria privata |
| PSS | smaps_rollup | n/a | n/a |
| Swap e SwapPSS per processo | smaps_rollup | n/a | n/a |
| Swap globale | meminfo | pagefile tramite psutil | psutil |
| Cache, slab, PSI Linux | Disponibili | n/a | n/a |
| Regioni del processo e mappa navigabile | smaps su richiesta | Solo intervalli virtuali, sperimentale | Non implementate |
| Validazione effettuata | Test e prova locale | Test simulati, da provare su PC Windows | Test simulati, da provare su Mac |

Su Windows/macOS l'ordinamento iniziale è USS, su Linux PSS. La stessa UI mantiene
le colonne non disponibili a n/a e spiega il limite. La CI è configurata per tutti e
tre i sistemi con Python 3.11, 3.13 e 3.14, ma non è stata eseguita su GitHub.

Le API native sono gestite da `psutil`: per questa base non occorrono pywin32 o WMI.
PSS non è esposta da psutil su Windows/macOS; il private commit/PagefileUsage Windows
non rappresenta la RAM privata residente né la swap effettiva di un processo.
Fonti: [psutil 7.2](https://psutil.io/7.2/#psutil.Process.memory_full_info),
[Microsoft PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex).

## Controlli

| Tasto | Azione |
|---|---|
| ↑ / ↓ | Seleziona una riga |
| Invio su un'applicazione | Mostra solo i processi del gruppo |
| Invio su un processo / r | Apre la mappa delle regioni; su un'app r mostra prima i suoi processi |
| Esc | Dalla tabella processi torna alle app; nei controlli ricerca cancella i filtri |
| g | Alterna applicazioni e tutti i processi |
| s | Ordina per PSS, USS, RSS, Swap, SwapPSS, nome |
| c / selettore Charts | Alterna grafici |
| a | Tutti / primi 30 secondo l'ordinamento |
| m | Slim / Full diagnostics |
| / | Cerca nome, percorso eseguibile o PID esatto |
| f | Apri i filtri per utente e stato memoria |
| d | Dettaglio della memoria del gruppo o processo selezionato |
| p | Pausa / riprendi |
| ? | Spiegazione delle metriche |
| q | Esci dal programma |

La chiusura del programma non chiude la sessione desktop.
Il dashboard e l'inspector scorrono nei terminali piccoli; la tabella scorre orizzontalmente.

## Barra RAM del sistema

La riga RAM si estende fino al bordo destro del pannello e mostra segmenti proporzionali
colorati. Le etichette compaiono dentro i segmenti quando lo spazio basta; la legenda
riporta tutte le categorie e i valori, comprese quelle inferiori a un carattere.

Su Linux la barra descrive la RAM utilizzabile riportata in `MemTotal`:

| Segmento | Contatore |
|---|---|
| Anonima | AnonPages |
| File cache | Cached − Shmem |
| Condivisa/tmpfs | Shmem |
| Buffer | Buffers |
| Slab ric. | SReclaimable |
| Slab non ric. | SUnreclaim |
| Altro | residuo calcolato: MemTotal meno gli altri segmenti |
| Libera | MemFree |

La somma dei segmenti è `MemTotal`. Altro è memoria non classificata dai contatori scelti,
non una misura esclusiva del kernel. `MemTotal` non è necessariamente tutta la RAM fisica
installata: alcune riserve hardware/kernel sono escluse dal totale utilizzabile.
Non si aggiungono di nuovo `Slab`, `Mapped`, PSS/RSS o i contatori clean/dirty dei processi:
si sovrappongono alle categorie già rappresentate.

**Disponibile** resta un indicatore separato: comprende memoria recuperabile, inclusa
parte della cache. **Uso netto** è `totale − disponibile`, lo stesso indicatore del grafico
RAM; non è la somma di tutte le categorie non libere. Le misure sono sequenziali.
Se mancano campi o il campione è incoerente, il motivo è mostrato e si usa la barra più
semplice in uso/disponibile. Questo è anche il fallback Windows/macOS attuale; non vengono
inventate categorie. Non si normalizzano valori incoerenti per farli rientrare nel totale.

È una **mappa dei consumi per categoria OS**, non una disposizione per indirizzo fisico.
Per un processo, `d` mostra la ripartizione aggregata e `r` apre la mappa delle regioni
Linux da `smaps`: indirizzi virtuali, file, permessi e residenza. Gli indirizzi virtuali
non sono posizioni fisiche contigue nella RAM.
Fonti: [procfs Linux](https://docs.kernel.org/filesystems/proc.html#meminfo),
[sorgente meminfo](https://github.com/torvalds/linux/blob/master/fs/proc/meminfo.c).

## Significato e limiti dei numeri

- **PSS**: memoria privata più quota proporzionale della memoria condivisa.
- **USS**: `Private_Clean + Private_Dirty` da `smaps_rollup`.
- **RSS**: memoria residente, comprese pagine condivise. Una somma può duplicarle.
- **Swap**: campo `Swap` di `smaps_rollup`; non include la swap shmem e può duplicare
  pagine condivise. **SwapPSS** ripartisce proporzionalmente la swap condivisa contabilizzata.
- **RAM used**: `total - available`; su Linux `MemTotal - MemAvailable`. Non è la somma
  di PSS/RSS. Su macOS available segue psutil (free + inactive), non la Memory Pressure
  di Activity Monitor. Su Windows free e available da psutil coincidono.
- **Cache**: `Cached + Buffers + SReclaimable - Shmem`, minimo zero, nel grafico storico.
  Si sovrappone alla memoria disponibile. Nella barra RAM file cache, buffer e slab
  recuperabile sono rappresentati separatamente, senza aggiungere questo totale una seconda volta.
- **Slab**: memoria del kernel da `meminfo`, non tutto il consumo del kernel.
- **PSI some**: percentuale di tempo con almeno un task in attesa di memoria,
  media su 10 secondi. Non è percentuale di RAM occupata.
- **n/a / null**: lettura non disponibile; zero è riservato a uno zero misurato.
  Il totale di un gruppo è sconosciuto se manca un solo valore della metrica.
  `Letture` indica le coperture PSS e USS del gruppo. Il dashboard mostra somme **visibili parziali**.
- Le pagine HugeTLB non sono incluse nei normali contatori qui mostrati.

**Applicazione:** su Linux viene usata l'istanza applicativa systemd quando il cgroup
utente la identifica esplicitamente (`app-*.scope` o `app-*.service` sotto `app.slice`).
Gli helper con eseguibili differenti della stessa istanza si uniscono; istanze e utenti
diversi restano separati. Non vengono aggregati intere sessioni o servizi generici.
Il nome visualizzato deriva dall'identità systemd, con eventuale escaping decodificato.
Il percorso completo dell'istanza resta consultabile nell'inspector e nel JSON.

Senza identità esplicita, anche su Windows/macOS, si usa `(utente, eseguibile)` o
`(utente, nome)` se il percorso manca: è un fallback dichiarato. Utente = UID su Unix,
dominio/nome su Windows. Con proprietario sconosciuto il processo resta separato.
Nel fallback, più programmi Python con lo stesso eseguibile possono ancora essere uniti.
L'inspector e il campo JSON `grouping` indicano il criterio (`cgroup`, `executable`, `name`).
Fonte per la convenzione: [systemd Desktop Integration](https://systemd.io/DESKTOP_ENVIRONMENTS/).

## Ricerca e filtri

Premi `/` per aprire la barra. La ricerca è una sottostringa letterale senza distinzione
maiuscole/minuscole su nome app, nome dei processi ed eseguibili. Una stringa di sole cifre
cerca invece un **PID esatto**. Non usa espressioni regolari. `Invio` riporta il focus alla
tabella, mantenendo la ricerca. Le lettere scritte nel campo non attivano le scorciatoie.

Con `f` apri i selettori:

- **Utente:** tutti oppure un UID/account tra quelli raccolti.
- **Con swap:** almeno un processo con swap misurata maggiore di zero; n/a non corrisponde.
- **Dati parziali:** manca una lettura fra le metriche supportate dal sistema. PSS e swap
  non supportate da Windows/macOS non rendono da sole tutte le righe parziali.

Ricerca, utente e stato memoria si combinano. Il filtro agisce **prima** del limite Top 30.
In vista app seleziona gruppi interi: tutti i processi rimangono nei totali, anche se solo
un helper corrisponde. In vista processi seleziona i singoli processi del contesto corrente.
Entrando in un'app con Invio e tornando con Esc i filtri vengono conservati. `Reset` o
`Esc` con focus nei controlli cancella tutti i filtri; Esc dalla tabella app li cancella
quando la barra è aperta. Grafici e dashboard continuano a descrivere l'intero sistema.
La barra indica righe mostrate, corrispondenti e totali; nessun risultato è segnalato.

## Memoria più granulare

Seleziona un'app o un processo e premi **d**. La finestra scorrevole mostra:

- **Barra PSS:** anonima, file e shmem, proporzionali alla PSS totale.
- **Barra RSS:** privata clean/dirty e condivisa clean/dirty, proporzionali alla RSS totale.
- **Swap e SwapPSS separate:** non entrano nelle barre della RAM residente.
- **PSS anonima, file e shmem:** ripartizione proporzionale per tipo di pagina.
- **Privata clean/dirty:** le due componenti di USS.
- **Condivisa clean/dirty:** pagine residenti condivise; nei gruppi possono essere contate più volte.
- **Anonymous, LazyFree e AnonHugePages:** altre viste sulle pagine anonime, recuperabili e THP.

Questi dettagli provengono dalla stessa lettura Linux `smaps_rollup`; non aggiungono una
scansione delle singole mappature. Sono **viste sovrapposte**, non componenti da sommare tutte.
Un campo mancante resta n/a con la copertura delle letture: un totale parziale non viene
mostrato come completo. Su Windows/macOS il dettaglio riporta i contatori generali disponibili
e indica n/a per la ripartizione Linux. La finestra fissa il campione all'apertura; chiudila
e riaprila per aggiornarla. `Esc` o `d` chiude. Il campionamento principale continua.
Fonte: [documentazione procfs del kernel Linux](https://docs.kernel.org/filesystems/proc.html).

Le barre usano tutta la larghezza disponibile e mantengono in legenda anche componenti
inferiori a un carattere. La coerenza viene verificata per ogni processo prima di sommare
un'applicazione; errori opposti non si compensano. RSS richiede la somma esatta. I tre
contatori PSS sono troncati separatamente ai kB da procfs: un residuo di 0, 1 o 2 KiB per
processo è rappresentato esplicitamente come **Arrotondamento procfs**, senza riscalare
le componenti. Altre incoerenze producono `n/a` con motivo.
Fonte: [kernel Linux, __show_smap](https://github.com/torvalds/linux/blob/v6.17/fs/proc/task_mmu.c).

## Mappa delle regioni Linux

Seleziona un'app, premi `Invio` per scegliere uno dei suoi processi, poi premi **r** o
**Invio** sul processo. Ogni PID ha uno spazio virtuale distinto: non vengono unite le
mappe dei processi di un gruppo. La vista conserva pannelli, bordi, colori e tabella
dell'interfaccia terminale. Su Windows il provider sperimentale mostra intervalli virtuali,
senza contatori residenti per regione; su macOS la funzione non è ancora disponibile.
Il provider Windows è coperto da simulazioni ma non è stato verificato su Windows reale.

La mappa ha due modalità, selezionabili con **v**:

- **RAM residente RSS:** la larghezza dei blocchi è proporzionale alla memoria residente
  delle regioni mostrate. Le pagine condivise possono ricorrere in più mappature.
- **Spazio virtuale:** la larghezza segue la dimensione virtuale delle regioni. L'ordine
  è quello degli indirizzi crescenti; i buchi sono esclusi dalla scala e le transizioni
  visibili sono segnate con `│`. Non è una rappresentazione dei frame fisici.

I colori distinguono eseguibile, librerie, file, heap/stack riconosciuti, anonima, shmem
e regioni speciali. Il tipo descrive l'origine della mappatura, con euristiche dichiarate:
un file può contenere anche pagine private modificate tramite copy-on-write. La memoria
anonima non viene chiamata automaticamente heap, né identificata come oggetti dell'app.

La tabella mostra indirizzi, tipo, dimensione virtuale, RSS, PSS, USS, swap, permessi e nome.
Il pannello inferiore aggiunge offset, inode, clean/dirty, SwapPSS, pagine anonime, THP,
HugeTLB e VmFlags. THP è già incluso nei contatori ordinari; HugeTLB rimane separato.
La selezione sulla barra e sulla tabella è sincronizzata. Le regioni troppo piccole per
una cella restano sempre selezionabili dalla tabella.

| Tasto nella mappa | Azione |
|---|---|
| ↑ / ↓, oppure clic sulla barra | Seleziona una regione |
| v | Alterna RSS e spazio virtuale |
| s | Ordina la tabella per RSS, PSS, dimensione virtuale, indirizzo; la mappa resta in ordine virtuale |
| / | Cerca nome/percorso, tipo, permessi o indirizzo esadecimale `0x…` contenuto nella regione |
| f | Filtra tipo e stato: residente, con swap, con pagine RSS condivise |
| Invio dalla ricerca | Riporta il focus alla tabella |
| z / Invio sulla tabella | Zoom sulla regione con fino a due regioni vicine per lato; ripeti per uscire |
| Tab, poi ↑ / ↓ / PgDn | Porta il focus al pannello dettagli e scorri il contenuto |
| r | Legge un nuovo campione del processo |
| b / Ctrl+B | Fissa il campione A / rimuove A |
| c | Alterna vista corrente e confronto A→B |
| Ctrl+S / Ctrl+O | Salva / apre un'acquisizione locale |
| Esc | Prima cancella i filtri aperti, poi esce dallo zoom, poi torna ai processi |
| q | Chiude la mappa e torna ai processi |

Ricerca e filtri si combinano; la mappa e il suo totale descrivono le regioni mostrate,
anche durante lo zoom. L'aggiornamento è **su richiesta**, all'apertura o con `r`: il
campionamento generale continua a usare `smaps_rollup`. Il pannello indica orario, età,
durata e completezza della lettura. Durante un nuovo caricamento o dopo un errore non
restano visualizzati vecchi valori come se fossero attuali.

La scansione ha limiti di 32 MiB di metadati, 32.768 regioni e 3 secondi, controllati
fra le letture. Cancellazione e tempo sono cooperativi: non interrompono una chiamata
procfs già in corso. Raggiungere un limite conserva soltanto le regioni già completate
e segnala il campione parziale. Permessi negati, processo terminato, PID riutilizzato o
dati malformati producono un motivo esplicito. Nessuna elevazione automatica.

Ogni processo è identificato da PID e data di creazione per evitare di riutilizzare
una selezione su un nuovo processo con lo stesso PID. Le letture sono sequenziali,
non atomiche; i totali globali e quelli per processo non sono tenuti artificialmente uguali.
I dati possono essere limitati da UID, namespace e permessi procfs. La UI espone le
letture mancanti senza elevazione automatica. Nessuna lettura di `/proc/PID/mem`,
cmdline, environment o contenuti delle applicazioni.

Il worker rileva in background e aspetta `--interval` secondi **dopo** ogni scansione;
il periodo effettivo include `sample_ms`. Default 2 s. I grafici conservano 60 campioni,
non necessariamente 60 secondi. Alla prima lettura la CPU è n/a.

## Confronto A/B e acquisizioni

Nella mappa, premi **b** per fissare A, esegui l'azione da osservare e premi **r** per
raccogliere B. Con **c** apri il confronto; `v` cambia la metrica e `s` cambia
l'ordinamento delle variazioni. Gli intervalli riorganizzati o i campioni incompleti
non producono delta inventati. A rimane fissato anche se B non è disponibile. Le letture
sono sequenziali: la crescita osservata non dimostra da sola una perdita di memoria.

Con **Ctrl+S** salva su un percorso scelto esplicitamente; **Ctrl+O** apre una lettura
salvata. Il file può contenere percorsi e nomi dei processi: controllalo prima di
condividerlo. Per aprire da terminale senza avviare rilevazioni live:

```bash
./run.sh --open acquisizione.rtm.json
./run.sh --compare prima.rtm.json dopo.rtm.json
```

`--compare` richiede un campione per file; `--open` apre anche un file con A e B.
Un confronto richiede sessione di raccolta, identità del processo e definizioni
compatibili. Un intervallo uguale non dimostra che sia rimasta la stessa allocazione.
Il formato è descritto in [schema capture](docs/schema-capture.md).

Il budget facoltativo `--max-measurements N` limita il numero di letture costose dei
processi per ciclo e le ruota tra i processi. Le letture rinviate restano n/a; il numero
di tentativi e rinvii è visibile. Il budget non è un limite di tempo sulle chiamate OS.
Il default continua a raccogliere tutti i processi.

## Struttura

```text
src/ramtaskman/
  cli.py        → Collector.sample()
  collector.py  → selezione backend, campionamento e copertura
  backends/     → Linux procfs; Windows/macOS psutil
  models.py     → ProcessMemory, ApplicationMemory, SystemMemory, Snapshot
  grouping.py   → identità applicative systemd da cgroup
  filters.py    → ricerca e filtri senza modificare gli aggregati
  detail.py     → ripartizione granulare con copertura e spiegazioni
  memory_bars.py → barre PSS/RSS con denominatori e ragioni esplicite
  memory_segments.py → contabilità globale Linux senza sovrapposizioni
  ram_bar.py    → barra RAM proporzionale a tutta larghezza e legenda
  regions.py    → parser smaps e lettura limitata del processo selezionato
  region_map.py → mappa RSS/virtuale con selezione delle regioni
  region_screen.py → esploratore con ricerca, filtri, zoom e aggiornamento su richiesta
  report.py     → tabella una tantum e JSON schema_version=1
  app.py        → Textual, worker, tabelle, navigazione e grafici
  app.tcss      → CSS copiato dalla UI originale
  widgets.py    → spark e stacked_bar originali
 tests/         → contabilità, CLI e UI con fixture indipendenti dall'hardware
 tools/         → cattura di schermate sintetiche
 docs/          → architettura, provenienza e passaggio al prossimo agente
```

## Verifica

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once
./run.sh --json
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/capture_screenshots.py
UV_CACHE_DIR="$PWD/.uv-cache" uv build
```

Le schermate SVG in `captures/` usano dati **sintetici**, non misure del PC. Sono escluse
da Git. Il JSON live contiene nomi, UID e percorsi degli eseguibili: controllarlo prima
di condividerlo. Non vengono salvate rilevazioni automaticamente.

Verificati localmente **140 test** con Python 3.14.4, build wheel/sdist e rilevazione Linux.
Su Windows/macOS sono stati verificati contratti con API simulate, non misure hardware.
La UI è stata catturata e controllata con fixture sintetiche, inclusi filtri, dettaglio RAM e regioni.
La suite include contabilità delle barre, parser e limiti smaps, identità PID, filtri,
selezione/zoom, aggiornamento ed errori della mappa, con UI 160×48 e 80×24 e campionamento
principale attivo mentre la mappa è aperta. I pacchetti includono i nuovi moduli e il CSS,
escludendo cache e catture locali.

## Provenienza e prosecuzione

- [Piano dettagliato: confronto, acquisizioni, piattaforme, prestazioni e distribuzione](docs/piano-sviluppo.md)
- [Provenienza, licenza e cosa è stato copiato](docs/upstream.md)
- [Architettura e invarianti](docs/architecture.md)
- [Passaggio al prossimo agente](docs/handoff.md)
- [Istruzioni per gli agenti](AGENTS.md)
- [Lezioni verificate](lessons.md)

Licenza MIT; copyright originale di Scott Hanselman conservato in [LICENSE](LICENSE).
La cronologia originale è conservata in Git. Questo progetto è una derivazione indipendente,
non una release ufficiale di Scott Hanselman. Nessuna pubblicazione è stata effettuata.
