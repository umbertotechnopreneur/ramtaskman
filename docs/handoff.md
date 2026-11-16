# Passaggio al prossimo agente

## Piano di prosecuzione

Il riferimento per il lavoro successivo è il [piano di sviluppo dettagliato](piano-sviluppo.md),
preparato su richiesta dell'utente per continuare nella stessa chat. Copre F1 confronto,
F2 acquisizioni/replay, F3 piattaforme, F4 prestazioni e F5 consolidamento/distribuzione,
preceduti da F0 per i contratti comuni. La sequenza iniziale prevista è F0 → F1 → F2.
Il documento contiene criteri di accettazione, verifiche e registro. L'utente ha poi
autorizzato l'esecuzione del piano: controllare il registro e i test prima di ripartire.
Confronto e acquisizioni offline sono implementati; la validazione hardware Windows/macOS
e la mappa macOS rimangono aperte. Il budget generale è opzionale e la UI conserva il
risultato del confronto immutabile; la tabella è paginata, con verifiche prestazionali in corso.

## Obiettivo dell'utente

Un ramtaskman Python/Textual con la stessa UI terminale di gputaskman di Scott Hanselman,
ma dedicato a RAM per applicazione, PSS, USS e swap. L’utente ha poi richiesto
esplicitamente il supporto multipiattaforma: Linux, Windows e macOS. Preparare una base chiara sulla quale
possa proseguire un agente meno potente. Nessun cambio di framework; l'utente ha poi
richiesto esplicitamente la pubblicazione del repository GitHub.

## Stato Git alla consegna

La base RAM e i primi incrementi sono nei commit locali del branch
`codex/ramtaskman-foundation`. L'identità Git locale è configurata con i dati forniti
dall'utente; verificare lo stato corrente prima di modificare il repository. La rimozione
dei moduli GPU è intenzionale e la provenienza resta nella cronologia upstream.

## Come ripartire

1. Leggi [README](../README.md), [AGENTS](../AGENTS.md), [architettura](architecture.md)
   e [lessons](../lessons.md).
2. Controlla `git status`, branch corrente e ultimo commit. Il branch di lavoro è
   `codex/ramtaskman-foundation`; l'upstream GPU resta nella cronologia.
3. Avvia `./run.sh` (Linux/macOS) o `.\run.cmd` (Windows) dalla radice. Per una verifica rapida usa `./run.sh --once`.
4. Esegui i test indicati nel README prima e dopo una modifica funzionale.
5. Segui i blocchi del piano autorizzati dall'utente, in incrementi piccoli; non riscrivere tutto insieme.

## Già implementato

- Selettore backend: Linux con meminfo/smaps_rollup/PSI; Windows e macOS con psutil RSS/USS.
- PSS/swap per processo dichiarate non disponibili su Windows/macOS; nessuna stima sostitutiva.
- Modelli con None per dati sconosciuti, aggregati completi o null e copertura PSS.
- Raggruppamento Linux per istanza applicativa cgroup systemd esplicita con UID coerente,
  anche con helper diversi. Fallback utente/eseguibile o utente/nome, dichiarato;
  proprietario sconosciuto separato. Provenienza UI/JSON grouping/grouping_id.
- Ricerca nome/eseguibile/PID con `/`; filtri utente, con swap e dati parziali con `f`.
  Gli aggregati conservano tutti i membri; filtri prima del Top30 e durante drilldown.
- Dettaglio `d`: PSS anon/file/shmem, clean/dirty privata e condivisa, anonima, LazyFree, THP;
  campi Linux, letture parziali n/a, campione fissato all’apertura. Inspector con riepilogo.
- Barre separate PSS/RSS in `d`, a tutta larghezza; swap separata. Coerenza per PID;
  residuo PSS di troncamento ai kB esplicito, non usato per nascondere incoerenze.
- Lettura Linux smaps su richiesta per il PID scelto, con identità prima/dopo, limiti,
  cancellazione, campioni parziali dichiarati e valori mancanti None.
- Esploratore `r`/Invio sul processo: mappa RSS/virtuale, tabella, inspector scorrevole,
  ricerca/filtri, selezione sincronizzata, zoom e aggiornamento manuale con età/durata.
- Barra RAM a tutta larghezza, segmentata per categorie OS Linux. `memory_segments.py`
  produce i byte, `ram_bar.py` li rende senza doppie contabilizzazioni. Fallback esplicito
  con motivo, Altro residuo derivato. Non è una mappa degli indirizzi fisici.
- Vista applicazioni, processi, Invio per entrare in un gruppo, Esc per tornare.
- PSS, USS, RSS, Swap, SwapPSS, percentuale PSS e ragioni dei dati mancanti.
- UI derivata dall'originale: CSS e helper copiati; struttura dei pannelli e grafici adattata.
- Sort, tutti/top 30, slim/full, pausa, aiuto, ridimensionamento e recupero dopo errori.
- CLI, output JSON con backend/capacità/copertura, lockfile, launcher Unix e Windows,
  CI configurata Linux/Windows/macOS e suite di test locale.
- Catture SVG sintetiche riproducibili, escluse da Git.

## Verifica Windows reale da programmare con F3

La parte Windows/macOS è implementata e coperta da simulazioni; non è stata eseguita su
questi sistemi. Su un PC Windows con Python e uv:

```powershell
.\run.cmd --once
.\run.cmd --json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\run.cmd
```

Verifica RSS/working set e USS/private working set con contatori equivalenti, non con
commit. Documenta versione Windows, Python, numero di processi, copertura e sample_ms.
Controlla processi protetti, uscita e resize. Per macOS ripeti con `./run.sh`, annotando
i limiti di permesso e il significato di available. Non dichiarare completata la
validazione hardware finché non è stata eseguita. Nessun riavvio/logout necessario.

## Incrementi consigliati, indipendenti

### 1. Estendere il riconoscimento delle app su Windows/macOS

I due backend hanno ancora il fallback eseguibile/nome. Prima di modificarli, verifica
su hardware e scegli metadati espliciti equivalenti: non dedurre identità da nomi generici
né usare cmdline/environ. Mantieni utenti e istanze separati. Su Linux cgroup già presente.

### 2. Ricerca, filtri e dettaglio: già completati

Non reimplementare queste funzioni. File: `filters.py`, `detail.py`, `app.py`, `app.tcss`.
Test in `test_filters.py`, `test_detail.py`, `test_ui.py`. Mantieni aggregati interi,
contatori globali non filtrati e n/a per totali incompleti. Dettaglio e aiuto non devono
interrompere l'aggiornamento della tabella sottostante. Le chiavi DataTable includono
la generazione per ignorare eventi di highlight obsoleti.

### 3. Regioni Linux: completate; prossimi incrementi separati

Non reimplementare le prime tre fasi richieste: barre di dettaglio, lettura Linux delle
regioni e mappa navigabile sono presenti. File: `memory_bars.py`, `detail.py`, `regions.py`,
`region_map.py`, `region_screen.py`; integrazione in `app.py`. Test dedicati: `test_detail.py`,
`test_regions.py`, `test_region_ui.py`.

Percorso: app → Invio → PID → r/Invio. `v` cambia RSS/virtuale; `s` cambia ordine della
tabella; `/` ricerca path/tipo/permessi o indirizzo 0x; `f` filtra tipo/stato; z/Invio
ingrandisce la regione con fino a due vicini per lato; `r` rilegge; Esc resetta filtri,
esce dallo zoom e torna ai processi. Tab permette di raggiungere l'inspector scorrevole.
La mappa resta in ordine virtuale e indica i buchi compressi; nessuna lettura dei frame fisici.

Il reader limita 32 MiB, 32.768 regioni e 3 s in modo cooperativo fra letture. I limiti
producono campioni parziali espliciti; errori e cambio identità cancellano i dati. La UI
invalida i valori vecchi all'inizio di ogni richiesta e scarta risposte obsolete. L'età
si aggiorna, ma le misure si rileggono soltanto all'apertura o con `r`. Non spostare smaps
completo nel campionamento normale. Non leggere mem/cmdline/environ o file mappati.

Il confronto A/B e il salvataggio offline sono implementati: `b` fissa A, `r` raccoglie B,
`c` apre la comparazione, `v` cambia metrica, `s` ordinamento, Ctrl+S salva e Ctrl+O
apre un file. CLI `--open`/`--compare` non costruiscono il collector. La specifica del
formato è in [schema capture](schema-capture.md). Il provider Windows virtuale è
sperimentale e attende prove hardware, quello macOS resta da implementare.
La mappa fisica privilegiata è un progetto separato. Non presentare crescita come prova
automatica di leak né attribuire regioni a oggetti, immagini o schede del browser.

### 4. Prestazioni con molti processi

File: `collector.py`, `models.py`, `test_memory.py`, `report.py`.
Prima misura: mostra già sample_ms. Se serve un budget, progetta età dei valori e copertura
prima della cache. Accettazione: nessuna misura scaduta mostrata come attuale, nessuna
starvation dei processi piccoli, uscita rapida, motivi delle letture mancanti conservati.

### 5. Rifinitura visiva con confronto originale

File: `app.py`, `app.tcss`, `widgets.py`, `tools/capture_screenshots.py`.
Usa il sorgente originale al commit in [upstream](upstream.md) e lo screenshot fornito
dall'utente come riferimento. Conserva le metriche RAM e le avvertenze di copertura.
Accettazione: stessi pannelli, spaziature e interazioni comparabili; nessuna regressione
su terminale stretto; screenshot dichiarati sintetici. Il tema usa i token Textual
originali, perciò font, terminale e tema possono cambiare la resa.

## Cosa non promettere

- Non è un debugger del contenuto della RAM.
- Riconosce gli helper nella stessa istanza applicativa systemd esplicita; il fallback
  non identifica tutte le app desktop. Cgroup mancanti o non convenzionali restano fallback.
- I contatori generali Windows/macOS sono implementati ma non verificati su hardware;
  il provider Windows delle regioni virtuali è sperimentale, quello macOS non è ancora
  implementato. In WSL si misura solo la VM Linux, non l’host Windows.
- Non equiparare somme PSS/RSS alla RAM usata globale o somme swap alla swap globale.
- Le scansioni non sono atomiche; niente stime presentate come misure.
- Nessuna pubblicazione PyPI o automazione release richiesta; niente kill o elevazione automatica.

## Validazione iniziale

16 novembre 2026: Linux locale, Python 3.14.4, Textual 8.2.8, psutil 7.2.2.
Verifica della base prima dell'esploratore delle regioni: contabilità, dati mancanti, gruppi, PID riutilizzati/terminati,
CLI, UI 160x48 e 80x24, pausa, drilldown, aiuto, errore e recupero; selezione backend,
identità Windows, USS distinta dal commit, null per PSS/swap e resa UI Windows simulata;
cgroup/escaping/UID/istanze, breakdown, filtri combinati e totali integri, ricerca per helper/PID,
input senza attivare scorciatoie, dettaglio con refresh del campione principale;
partizione OS, campioni mancanti/incoerenti, larghezza barra 20/74/154/314 colonne e resize UI.
Una rilevazione reale ha visto 668 processi, 193 con PSS leggibile, circa 610 ms di scansione;
sono una misura puntuale, non una garanzia di prestazioni. RAM OS circa 30.26 GiB.
La GPU rilevata era RTX 4060 ma non viene utilizzata dal programma.

Build wheel/sdist completata; installazione del wheel in un ambiente separato e
avvio di `ramtaskman --once` verificati. Pacchetti controllati: CSS incluso, nessuna
cache o cattura locale inclusa. UI verificata visivamente con schermate sintetiche a colori.

Durante l’incremento, una verifica Linux ha raccolto circa 680 processi in 619 ms: 11
gruppi cgroup, di cui 2 con helper diversi, 192 processi con breakdown leggibile. È una
misura puntuale, non un benchmark garantito.

Per l'incremento delle regioni sono passati **93 test** complessivi. La suite comprende: barre PSS/RSS e troncamento ai KiB,
campioni incompleti, parser smaps/permessi/identità/limiti, ricerca e filtri delle regioni,
mappa RSS/virtuale, selezione/zoom/resize, aggiornamenti manuali e scarto delle risposte
obsolete, campionamento principale non interrotto dalla mappa. Le schermate Textual
sintetiche a 160×48 e 80×24 sono state controllate visivamente, incluso l'inspector
scorrevole. L'aggiornamento manuale conserva selezione e zoom quando ancora validi.
Build wheel/sdist riuscite; nuovi moduli e CSS inclusi, cache/catture escluse.

La prova Linux sul processo della verifica ha letto 63 regioni, campione completo in
6,65 ms. La CLI JSON ha raccolto 784 processi in circa 869 ms. Sono misure puntuali,
non garanzie di prestazioni. Le simulazioni non costituiscono verifica dei backend
nativi Windows/macOS.

Per l'incremento A/B, replay e prestazioni sono passati 149 test locali su Linux (Python 3.14.4).
Un processo di prova ha allocato e toccato 8 MiB: delta RSS complessivo osservato
+8.572.928 byte, con campioni completi. Wheel/sdist ricostruiti e installati in
ambiente isolato locale; verificate CLI e apertura offline di un file sintetico.
Confronto e salvataggio usano metadati, non contenuti della memoria. Windows resta
simulato, macOS per regione non implementato; CI remota non eseguita.
La tabella delle regioni è paginata a 250 righe con Ctrl+U/D o Ctrl+frecce, mantenendo
la mappa e i totali sulle regioni filtrate. Nel budget sono disponibili priorità e
backoff opzionali; il comportamento predefinito rimane senza budget.

Incremento successivo: 171 test eseguiti su Linux, 170 passati e uno Windows nativo
saltato; verifica distribuzione, screenshot sintetici e confronto del processo di prova
riusciti. Il confronto e la copia immutabile vengono preparati in worker cancellabili.
Prove native preparate in [verifica Windows](verifica-windows.md) e
[verifica macOS](verifica-macos.md), non eseguite sui sistemi rispettivi. Il
[rapporto benchmark](benchmark.md) riporta anche la parte di elaborazione ancora
sincrona e i limiti delle misure. Audit psutil in [audit contatori](audit-contatori-piattaforma.md).

Vedi README per i comandi di test, build e cattura e il piano per gli incrementi ancora aperti.

## Allineamento Linux alle modifiche Windows

16 novembre 2026: le modifiche presenti nella copia di lavoro condividono anche su Linux
la partenza Slim, la barra USS delle app complete e il contesto RAM/USS del PID nella
mappa live. Full diagnostics Linux espone inoltre `Committed_AS` e `CommitLimit` da
meminfo, cache e slab, distinguendoli dai contatori Windows. Campi opzionali assenti
restano n/a/null. Le schermate sono state generate con fixture sintetiche; i test UI
coprono anche Linux a 160×48 e 80×24. Su Linux sono stati eseguiti i launcher `--once`
e `--json`, la build e una lettura completa delle regioni del solo processo di prova
(64 regioni, circa 3,9 ms, misura puntuale). La suite locale ha eseguito 184 test,
con 3 test nativi Windows saltati. Nessuna nuova verifica hardware Windows o macOS è
stata eseguita in questa sessione.

## Pubblicazione e lingue

L'utente ha richiesto la pubblicazione GitHub e un README in dieci lingue, inclusi
cinese semplificato, coreano, francese, vietnamita e spagnolo. Le traduzioni sono
state preparate con assistenza AI e richiedono revisione di madrelingua. Le immagini
sono catture Textual su Linux con dati sintetici; il banner ritaglia sei dashboard.
La dashboard ha una prima localizzazione per dieci lingue tramite `--language`;
la UI non è ancora interamente tradotta: aiuto, dettagli, regioni, messaggi dei
backend e altre parti richiedono lavoro. Il README dichiara questo limite.
