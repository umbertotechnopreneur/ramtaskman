# Architettura

## Flusso

```text
CLI ── Collector.sample() ── Snapshot ─┬─ report.to_dict() → JSON
                                     ├─ report.table() → testo
                                     └─ RamTaskManager.apply() → UI

Processo selezionato ── RegionScreen ── worker ── LinuxRegionReader.read()
                                                  └─ RegionSnapshot → mappa/tabella/inspector
```

Il collector è indipendente da Textual. `make_backend()` sceglie `LinuxBackend` su Linux
o `PsutilBackend` configurato per Windows/macOS. Ogni backend espone `read_system()`,
`read_process()`, `name`, `source` e `unsupported` (metrica → motivo). `models.py` non dipende né da Textual né da psutil.
La UI usa un worker thread cancellabile e passa il campione al thread principale.
`worker.cancelled_event.wait()` permette di uscire senza attendere tutto l'intervallo.

## Fonti Linux

| Dato | Fonte | Nota |
|---|---|---|
| Totale, disponibile, cache, slab, swap globale | /proc/meminfo | byte dopo conversione kB × 1024 |
| RSS, PSS, USS, Swap, SwapPSS | /proc/PID/smaps_rollup | USS = Private_Clean + Private_Dirty |
| RSS quando rollup è inaccessibile | psutil.memory_info | fallback; PSS e USS restano null |
| Nome, UID, eseguibile, creazione | psutil | nessuna lettura cmdline o environ |
| CPU globale | psutil.cpu_percent | prima lettura null |
| Pressione memoria | /proc/pressure/memory, some avg10 | opzionale |
| Identità app | /proc/PID/cgroup | metadati limitati a 16 KiB, app systemd dell’UID corrente |
| Breakdown | smaps_rollup della stessa lettura | Pss_Anon/File/Shmem, Private/Shared Clean/Dirty, Anonymous, LazyFree, AnonHugePages |
| Regioni del processo selezionato | /proc/PID/smaps | lettura su richiesta distinta dal campionamento generale |

## Fonti Windows/macOS

`psutil.virtual_memory()` per RAM globale, `swap_memory()` per swap/pagefile globale,
`Process.memory_info()` per RSS, `memory_full_info().uss` per USS. PSS, Swap e SwapPSS
per processo restano None, con ragione in `Snapshot.unsupported`. Niente conversione da
VMS/private/pagefile: questi non rappresentano la stessa quantità. Cache/slab/PSI restano None.
Un errore sulla swap globale conserva i dati RAM e produce una nota.

Su Windows l'identità utente è dominio/nome, su macOS UID. I percorsi Windows vengono
normalizzati per il confronto senza distinzione maiuscole/minuscole. Un proprietario
sconosciuto non è un'identità condivisa: il processo rimane separato.

`ProcessMemory.key = PID + started_at`; si verifica `is_running()` dopo la lettura.
PID terminati/riutilizzati vengono scartati. Gli errori sui metadati di identità contano
in `skipped`. Gli errori su smaps conservano il processo con `reason` e valori null.

## Aggregazione

`Snapshot.applications` usa prima l'identità cgroup esplicita su Linux con UID noto,
`app_source=systemd-cgroup`, `app_id` completo e `app_name`. `grouping.py` accetta gerarchia
unificata e legacy name=systemd, sotto il percorso utente app.slice. Le unità app seguono
la convenzione systemd; sessioni e servizi generici non sono prove di identità applicativa.
L'identità conserva l'istanza intera, mentre il nome è solo descrittivo. Non unire istanze
solo perché mostrano lo stesso nome. UID non corrispondente, ambiguità fra gerarchie o
letture mancanti producono il fallback.

Altrimenti si raggruppa per `(utente, executable)` o `(utente, name)` quando il percorso
manca. Il gruppo espone `grouping`, `grouping_id`; se i membri hanno eseguibili diversi,
`executable=None`. `ApplicationMemory.total()` restituisce None se anche un solo membro
non espone la metrica. `Snapshot.visible_sum()` somma solo letture disponibili e restituisce
None quando non ne esiste nessuna. La copertura va sempre mostrata accanto ai totali.

Per raggruppamenti futuri non sommare aggregati e figli contemporaneamente. Non unire utenti
diversi. Non sostituire lo stato PSS mancante con RSS, né dedurre i byte condivisi da somme
incompatibili. Le pagine possono cambiare tra due letture; non imporre identità contabili
fra campioni sequenziali e totale globale.

## Contratto UI

Mantieni gli ID `dashboard`, `device`, `system`, `history`, `chart-controls`, `chart-mode`,
`charts`, `chart-note`, `procs`, `inspector` e le classi/stili del sorgente originale.
Il titolo dell'app non occupa una riga extra; il pannello inspector mostra modalità e sort.
I grafici usano 60 campioni e scala percentuale fissa. PSS/USS visible sono percentuali
della RAM totale, swap della swap totale, cache della RAM totale. PSI è già percentuale.

## Barra globale OS

`memory_segments.partition_meminfo()` costruisce una partizione contabile di `MemTotal`:
AnonPages, Cached−Shmem, Shmem, Buffers, SReclaimable, SUnreclaim, residuo Other, MemFree.
`SystemMemory.segments` contiene byte interi; `segments_reason` spiega l'assenza della
partizione. Sono nuovi campi opzionali compatibili con i vecchi costruttori e col JSON.
Mancanti, negativi, Cached<Shmem, totale nullo o somma superiore a MemTotal producono
segments vuoto con ragione; non si tronca o normalizza il campione. Other è calcolato,
non è una misura diretta del kernel né riserva hardware esterna a MemTotal.

`SystemRamBar` è un renderable Rich: riceve la larghezza effettiva dal pannello a ogni
render, senza limite fisso. Il metodo dei resti maggiori assegna tutti i caratteri della
riga ai segmenti, preservando la lunghezza totale; l'arrotondamento è solo visivo, i byte
restano invariati. Le categorie piccole rimangono in legenda anche senza una cella.
La barra non ordina per indirizzo fisico. Il fallback mostra used/available in due colori
con etichetta esplicita; non si possono derivare le categorie Linux da RSS/PSS.

## Filtri e dettaglio

`RowFilter` in filters.py seleziona righe senza modificare Snapshot né i membri di un
ApplicationMemory. Le app si costruiscono prima del filtraggio: una corrispondenza di
helper conserva l'aggregato completo. Una query numerica è PID esatto; altrimenti
sottostringa casefold su nomi ed eseguibili. Utente, testo e stato memoria sono AND.
Swap richiede una misura positiva; partial considera solo metriche supportate.
I filtri precedono ordinamento/Top30 e si conservano nel drilldown. Il selettore utente
mantiene un account selezionato anche se scompare dal campione successivo.

La barra è nascosta normalmente. `/` o `f` la apre. CSS riduce lo spazio del dashboard
quando la barra è aperta per mantenere tabella e inspector accessibili a 80x24.
Le chiavi DataTable includono una generazione del rendering: eventi accodati di una
vecchia tabella non devono cambiare la selezione dopo un aggiornamento.

`detail.py` aggrega breakdown solo se tutti i membri espongono il campo; mostra la
copertura per campo. `MemoryDetailScreen` congela un renderable del campione selezionato,
mentre il worker prosegue. `detail_bars()` costruisce due `MemoryBreakdownBar`:
PSS anon/file/shmem e RSS private/shared clean/dirty. Ogni barra dichiara il proprio
denominatore; swap e SwapPSS restano separate. `MemoryPart` conserva byte, etichette e
colori; `cell_widths()` assegna tutti i caratteri disponibili senza cambiare i valori.
La legenda conserva le componenti inferiori a una cella. Un totale zero è noto; campi
mancanti e incoerenti producono n/a con copertura o motivo.

La coerenza si verifica per processo prima dell'aggregazione. RSS deve coincidere con
la somma delle quattro componenti. Per PSS, procfs tronca separatamente a kB totale e
tre componenti: viene ammesso soltanto un residuo non negativo di 0/1/2 KiB per processo,
con valori allineati ai KiB. Il residuo è un segmento esplicito, mai una normalizzazione.
Fonte: [Linux __show_smap](https://github.com/torvalds/linux/blob/v6.17/fs/proc/task_mmu.c).
Gli altri contatori restano viste sovrapposte; non si sommano alle barre. Nessuna lettura
di smaps completo è necessaria per questa finestra.

## Regioni e mappa del processo

`regions.py` è indipendente da Textual. `MemoryRegion` contiene intervallo virtuale,
permessi, offset, device/inode, pathname, categoria euristica, RSS/PSS/USS/swap/SwapPSS,
breakdown e VmFlags. `size` deriva da end−start; `key` dall'intervallo. Il parser verifica
ordine/intersezioni, contatori duplicati o negativi, unità kB e coerenza di Size se presente.
Campi assenti restano None. USS deriva solo da Private_Clean+Private_Dirty; HugeTLB è
conservato separatamente. I path con spazi e file cancellati restano metadati: non si aprono.

`LinuxRegionReader.read(process, cancelled=...)` legge soltanto smaps del PID scelto.
Controlla PID+create_time prima e dopo tramite nuove istanze psutil, evitando create_time
in cache. `RegionSnapshot` conserva identità, orario, durata monotona, regioni, completezza
e motivo. Il metodo `total()` restituisce None per scansioni incomplete o metriche mancanti.
Permessi, fine processo, identità cambiata ed errori di parsing cancellano i dati raccolti.

Limiti predefiniti: 32 MiB, 32.768 regioni, 3 secondi; una singola riga è limitata a 64 KiB.
Al raggiungimento di un limite rimangono solo le regioni completate, con `complete=False`.
Tempo e cancellazione si controllano fra le letture: non sono timeout rigidi delle syscall.
Nessun uso di pagemap/PFN, mem, cmdline, environ o contenuti dei file mappati.

`RegionScreen` apre un worker cancellabile all'ingresso e con `r`, senza cambiare il
normale Collector. A ogni richiesta svuota i dati precedenti; `request_id` scarta risposte
superate e l'identità del risultato è verificata anche in UI. Chiudere la vista annulla
il worker e invalida le risposte. Windows/macOS mostrano un motivo senza avviare letture Linux.
Timestamp, età, durata e stato completo/parziale restano visibili; non c'è refresh periodico
dei dati delle regioni. L'età mostrata si aggiorna ogni secondo.

`RegionMap` ordina sempre per indirizzo, con area proporzionale a RSS oppure dimensione
virtuale. Nel secondo caso i buchi non hanno area: `│` segnala una transizione visibile
attraverso un buco o una regione filtrata. È una mappa virtuale, non una disposizione
fisica. RSS mancante impedisce di disegnare una barra completa fittizia. Le regioni sotto
una cella restano nella tabella. Il tipo descrive l'origine della mappatura: file-backed
non esclude pagine private anonime CoW, e anonima non implica heap o stack.

Ricerca e selettori filtrano nome, tipo, permessi o indirizzo 0x contenuto nell'intervallo;
stati residente/swap richiedono un valore positivo misurato, condivisa richiede entrambi
i contatori shared clean/dirty e somma positiva. La tabella può ordinare RSS/PSS/size/start;
selezione e clic sulla barra sono sincronizzati. `z` o Invio limita la mappa a fino a due
vicini per lato nell'insieme filtrato. Totali e titoli dichiarano sempre le regioni mostrate.
Esc azzera prima i filtri aperti, poi lo zoom, poi chiude. Le chiavi tabella includono una
generazione contro gli eventi obsoleti. Dashboard e inspector scorrono nel terminale stretto.

## Contratto CLI

Il confronto A/B usa `capture_models.py` per copie immutabili e `comparison.py` per
intervalli, identità, cambiamenti di origine e delta; una lettura parziale non prova
una sparizione. `capture_io.py` e `capture_dialog.py` salvano e aprono acquisizioni
versionate, distinte dal JSON generale, con limiti e validazione descritti in
[schema capture](schema-capture.md). `replay.py` apre la stessa vista senza creare un
collector o un provider; refresh live disabilitato. La sessione di acquisizione è
condivisa tra viste dello stesso avvio, non tra avvii distinti.

`region_provider.py` sceglie il provider: Linux smaps, Windows VirtualQueryEx
sperimentale (solo virtuale, test simulati), oppure un motivo esplicito su macOS.
L'immagine dell'eseguibile viene verificata prima e dopo la raccolta; se non è
disponibile il confronto dell'identità non è verificabile.

Il budget opzionale `Collector(max_measurements=N)` ruota le letture costose fra PID,
senza riutilizzare valori vecchi. Enumerazione incompleta rende i totali di gruppo n/a;
il JSON espone tentate/rinviate, `enumeration_complete` e `membership_complete`.
Il budget limita il numero di letture e non impone un timeout di sistema. Il collector
accetta cancellazione cooperativa. `tools/benchmark_memory.py` produce misure sintetiche.

`--once`, `--json`, `--processes`, `--interval`, `--version`; alias `rtm`.
JSON `schema_version=1`, `platform`, `source`, `unsupported`, copertura per metrica; tutte le quantità di memoria in byte, `taken` Unix time in secondi,
`processes[].breakdown` contiene byte/null per contatore; `applications[].grouping` e
`grouping_id` espongono la provenienza; le aggiunte sono compatibili con schema_version=1.
`sample_ms` durata monotona della scansione. Gli eseguibili possono avere percorsi personali:
nessuna esportazione automatica, fixture sintetiche per screenshot e test.
Le regioni sono una vista interattiva separata: non sono aggiunte al JSON o al percorso `--once`.

## Prestazioni e limiti

La v0.1 legge tutti gli smaps_rollup visibili (Linux) o memory_full_info (Windows/macOS)
in modo sequenziale a ogni campione.
Nel campionamento generale non ci sono cache di misure, budget o stime dei contatori. Questo rende la
semantica semplice ma richiede attenzione con migliaia di processi o tabelle delle pagine
molto grandi. Una futura scansione a budget dovrà aggiungere età e copertura dei dati:
non riutilizzare silenziosamente valori vecchi. La scansione delle regioni ha già limiti
e stato di completezza propri; non legge lo smaps completo di tutti i processi.
