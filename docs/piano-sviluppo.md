# Piano di sviluppo di ramtaskman — confronto, acquisizioni, piattaforme, prestazioni e distribuzione

Preparato il 16 novembre 2026. **Stato: piano da eseguire, non funzionalità già implementate.**

Questo documento è il riferimento operativo per proseguire **nella stessa chat**, anche
con un agente diverso. È scritto per permettere incrementi piccoli, verificabili e
riprendibili senza ricostruire tutte le decisioni dalla conversazione.

La richiesta attuale autorizza la preparazione del piano. L'esecuzione dei blocchi
inizierà con la successiva istruzione dell'utente. Non creare altre chat, remote,
pubblicazioni o servizi per dare seguito al solo documento.

## 1. Risultato atteso

L'utente vuole capire come è suddivisa la RAM e come cambia la memoria delle applicazioni.
Il prodotto finale di questo piano deve permettere di:

1. Aprire un processo, fissare un campione A e confrontarlo con un campione B.
2. Individuare intervalli cresciuti, ridotti, presenti solo in A/B o riorganizzati.
3. Salvare i metadati delle rilevazioni e riaprirli senza accedere ai processi originali.
4. Usare la stessa navigazione terminale su Linux, Windows e macOS, con capacità dichiarate.
5. Mantenere reattiva la UI anche con molti processi e regioni.
6. Installare e verificare una versione riproducibile, con documentazione e stato Git chiari.

L'interfaccia resta Python + Textual, con pannelli, tabella, inspector, barre e scorciatoie
coerenti con gputaskman. Le estensioni riguardano il modello dei dati e le viste terminali;
non è prevista una riscrittura web o grafica.

### Confini

- Il confronto descrive osservazioni del kernel; una crescita non prova un memory leak.
- Le regioni descrivono indirizzi virtuali e consumi residenti; nessuna mappa dei frame fisici.
- Non identificare oggetti Python, schede del browser, conversazioni o immagini dai soli metadati.
- Nessuna lettura di memoria applicativa, cmdline, environ o contenuti dei file mappati.
- Nessuna terminazione dei processi, modifica della loro memoria o elevazione automatica.
- Nessuna chiusura della sessione, riavvio o modifica del gestore grafico.
- Dati e cache restano nelle destinazioni già autorizzate; non usare altri dischi del PC ospite.
- Nessuna pubblicazione GitHub/PyPI, upload di acquisizioni o telemetria implicita.

## 2. Base verificata e inventario

Leggere prima [AGENTS](../AGENTS.md), [README](../README.md), [lezioni](../lessons.md),
[architettura](architecture.md), [handoff](handoff.md) e [provenienza](upstream.md).

### Stato alla preparazione del piano

| Area | Stato verificato nel repository |
|---|---|
| Versione | 0.1.0, Python >=3.11, psutil e Textual bloccati da uv.lock |
| Linux generale | meminfo, smaps_rollup, PSS/USS/RSS/swap, raggruppamento cgroup e fallback |
| Windows/macOS generali | Backend psutil, RSS/USS, contatori non supportati a n/a; test simulati |
| Barra di sistema | Partizione contabile Linux; fallback in uso/disponibile sugli altri OS |
| Dettaglio `d` | Barre PSS/RSS separate, clean/dirty e altri contatori, swap separata |
| Regioni Linux | smaps su richiesta, identità PID/create_time, limiti cooperativi |
| Esploratore | RSS/virtuale, ricerca, filtri, ordinamento, zoom, selezione e aggiornamento manuale |
| Stato delle regioni | Un solo campione corrente; nessuna baseline, cronologia o esportazione |
| JSON corrente | schema_version=1, sistema/processi/applicazioni; non contiene le regioni |
| Test | Ultima esecuzione documentata: 93 test passati su Linux |
| Pacchetti | Wheel e sdist costruiti; nuovi moduli/CSS inclusi, cache e catture escluse |
| CI | Configurata per Linux/Windows/macOS × Python 3.11/3.13/3.14; non eseguita su GitHub |
| Git | Branch codex/ramtaskman-foundation; staged, unstaged e file nuovi da preservare |

HEAD è ancora il commit upstream `7486bfa`; il lavoro RAM non è rappresentato da una serie
di commit conclusa. Le cancellazioni GPU sono intenzionali. L'assenza precedente di
nome/email Git è documentata: verificarla di nuovo al momento opportuno, senza inventare identità.

### File di partenza

| File esistente | Responsabilità da conservare |
|---|---|
| `models.py` | Misure generali, identità processo, aggregati e dati mancanti |
| `collector.py` | Selezione backend e campionamento generale |
| `backends/linux.py` | meminfo, rollup e metadati Linux |
| `backends/psutil_backend.py` | Backend Windows/macOS corrente |
| `regions.py` | Modelli regioni, parser smaps, lettore Linux |
| `region_screen.py` | Worker su richiesta e navigazione delle regioni |
| `region_map.py` | Proporzioni delle mappe e selezione dei blocchi |
| `detail.py`, `memory_bars.py` | Barre e contabilità delle viste aggregate |
| `filters.py`, `grouping.py` | Ricerca e raggruppamento applicativo |
| `report.py`, `cli.py` | Contratto CLI e JSON esistente |
| `app.py`, `app.tcss` | UI principale e campionamento in background |
| `tools/capture_screenshots.py` | Catture esclusivamente sintetiche |

I nomi indicati nelle sezioni successive sono proposte di nuovi moduli. Non creare
scheletri vuoti in anticipo: introdurre un file quando il blocco che lo usa è implementato.

## 3. Ordine operativo e dipendenze

I cinque punti richiesti mantengono questa numerazione:

- **F1:** confronto tra campioni.
- **F2:** salvataggio, riapertura e confronto offline.
- **F3:** completamento multipiattaforma.
- **F4:** prestazioni e campionamento a budget.
- **F5:** consolidamento, Git, CI e distribuzione.

**F0** è una breve preparazione comune, non un sesto progetto. F5 ha un controllo Git
iniziale e una chiusura finale; la pubblicazione rimane fuori dall'autorizzazione corrente.

Ordine raccomandato:

```text
Prima consegna:   F0 → F1.1 → F1.2 → F1.3 → F1.4
Seconda consegna: F1.4 → F2.1 → F2.2 → F2.3 → F2.4
Terza consegna:   F2.4 → F3.1 → F3.2 → F3.3 → F3.4 → F3.5

F4.1: misurare presto, dopo F0; ripetere quando arrivano i provider nativi
F4.2/F4.3/F4.4: ottimizzare dopo avere misure, senza cambiare i contratti di F1/F2
F5: consolidare localmente a ogni milestone; chiudere la matrice finale alla fine
```

Un agente può portare avanti i test simulati di F3 senza hardware Windows/Mac, ma deve
lasciare esplicitamente aperte le relative verifiche reali. Non dichiarare completato
un blocco perché non è possibile eseguirne la prova finale sulla macchina disponibile.

## 4. Regole trasversali da mantenere

1. `None`/`null`/`n/a` è diverso da zero. Ogni nuova metrica mantiene questa distinzione.
2. I totali completi richiedono tutte le misure necessarie; le somme visibili sono etichettate come tali.
3. RSS, PSS, USS, swap e commit non sono componenti additive dello stesso totale.
4. La contabilità OS non deve essere forzata a coincidere con la somma dei processi.
5. Ogni campione mantiene origine, identità, intervallo temporale, copertura e motivi delle assenze.
6. Filtri e ordinamento sono viste: non modificano i dati originali né la baseline.
7. Una scansione interrotta non rende scomparsi gli elementi non letti.
8. I dati importati non possono attivare letture live, comandi o accessi ai percorsi contenuti nel file.
9. Il worker della schermata si annulla con `cancel_node(self)`; non interrompere il worker principale.
10. Le raccolte restano fuori dal thread UI; anche il costo di trasformazione/render va misurato.
11. Preservare le scorciatoie esistenti; i caratteri digitati negli Input non attivano comandi globali.
12. Prove sintetiche e misure reali restano distinguibili in documentazione e schermate.

## 5. F0 — preparazione comune

### F0.1 — rilevare la base senza modificarla

Eseguire `git status --short`, `git diff`, `git diff --cached` e
`git ls-files --others --exclude-standard`. Leggere anche i file nuovi: `git diff`
da solo non comprende tutta la consegna. Non usare reset, clean, checkout o stash
automatici per ottenere artificialmente un working tree pulito.

Eseguire la suite di partenza con il launcher/ambiente locale. Se fallisce, distinguere
regressione preesistente, ambiente e nuovo lavoro; registrare il comando e il risultato.
Non trattare 93 come numero da preservare: i test cresceranno e il risultato va riportato realmente.

Prima di cambiare storage o accelerazione rilevare macchina, RAM, GPU e dischi secondo
AGENTS. Per questo piano non sono necessari GPU, modelli locali o download di dataset.

**Uscita:** baseline nota, modifiche esistenti preservate e nessun refactoring funzionale.

### F0.2 — origine e capacità delle acquisizioni

Introdurre piccoli contratti indipendenti da Textual, in `capture_models.py` o modulo equivalente.
Riutilizzare `MemoryRegion`/`RegionSnapshot`; evitare una seconda rappresentazione quasi identica.
Preferire un involucro con metadati di acquisizione, senza rompere i costruttori attuali.

| Campo proposto | Significato |
|---|---|
| `capture_id` | UUID dell'acquisizione, non l'identità del processo |
| `collection_session_id` | UUID casuale generato una volta per avvio live del monitor |
| `sequence` | Numero crescente assegnato alle richieste nella sessione |
| `platform`, `backend_id`, `backend_version` | Origine e versione del contratto di raccolta |
| `pid`, `started_at` | Identità del processo, conservando la precisione realmente disponibile |
| `executable_identity` | Metadato opzionale per rilevare un cambio di immagine eseguibile |
| `started_wall`, `finished_wall`, `duration_ms` | Orari per visualizzazione e durata monotona |
| `enumeration_complete` | La lista degli intervalli è completa? |
| `metric_coverage` | Per metrica: letture valide/attese, unità, definizione e motivi |
| `capabilities` | Cosa può esporre il provider; distinto da ciò che una lettura ha ottenuto |
| `issues` | Codici stabili e descrizioni leggibili di errore/limite/assenza |

Decisione iniziale: confronto temporale verificato soltanto entro la stessa
`collection_session_id`, stesso processo e definizioni compatibili. Due file salvati
nella stessa sessione mantengono l'identità anche quando sono riaperti altrove.
Due avvii indipendenti del monitor non sono automaticamente riconosciuti come la stessa
origine. Questo limite è preferibile a usare hostname o PID come prova. Un identificatore
host/boot tra sessioni può essere aggiunto in futuro, con un contratto separato.

Non salvare un UUID persistente sul PC ospite per implementare questa prima versione.
Non trasformare un timestamp float in nanosecondi dichiarando una precisione inesistente.

Le capacità devono distinguere almeno: enumerazione regioni, RSS, USS, PSS, swap,
SwapPSS, clean/dirty, nomi file, attributi nativi, partizione globale. Una metrica non
supportata e una lettura negata hanno valori entrambi assenti, ma motivi differenti.

Il modello attuale ha `complete` unico. Conservare compatibilità, introducendo una
distinzione esplicita tra elenco completo e contatori completi prima che F3 inizi
enumerazioni complete con letture per pagina parziali. Non cambiare il significato
del vecchio flag senza aggiornare tutti i chiamanti e i test.

**Test:** uguaglianza di origine, sessioni diverse, PID riutilizzato, semantiche metriche
diverse, round-trip dei timestamp e separazione supporto/permesso/copertura.

**Uscita:** i nuovi metadati possono essere associati al lettore Linux esistente e la UI attuale funziona.

## 6. F1 — confronto tra campioni

### F1.1 — baseline e stato della sessione

Nuovo modulo proposto: `comparison.py`, con funzioni pure; stato UI separato in
`RegionScreen` o in un piccolo modello della vista.

Stato minimo:

```text
current_capture: campione corrente oppure assente
baseline_capture: copia immutabile del campione A oppure assente
comparison: risultato derivato, mai modificato dai filtri
comparison_mode: spento / acceso
loading_request_id: richiesta B attiva
```

Usare una copia profonda o dataclass immutabili con collezioni non mutabili per la
baseline. Congelare il solo dataclass esterno non congela liste e dizionari interni.
Il costo della copia va misurato; non copiare tutto a ogni evidenziazione di riga.

Transizioni richieste:

| Evento | Comportamento |
|---|---|
| Apertura processo | Raccolta corrente come oggi; nessuna baseline implicita |
| Fissa A | Copia il campione completo selezionato; mostra ora e identità |
| Nuova raccolta B | A resta fisso; i dati correnti obsoleti non sono mostrati come nuovi |
| Errore B | A resta esplicitamente storico; delta indisponibili, motivo visibile |
| B valido | Ricalcola confronto A→B; non sostituire A automaticamente |
| B parziale | Mostra copertura; delta ammessi solo dove entrambe le letture sono valide |
| Cambio processo | Non trasferire A silenziosamente al nuovo processo |
| Rimuovi A | Torna alla vista corrente, senza cancellare B |
| Chiudi vista | Annulla solo i suoi worker; rilascia baseline e risultati |

Per la prima versione il comando «Fissa A» richiede un elenco completo di regioni.
Un file storico parziale può essere aperto, ma non diventa automaticamente una baseline
per inferire presenze/assenze. Nessuna registrazione periodica implicita.

**Uscita:** aggiornamenti, errori, filtri e ordinamenti non alterano il campione fissato.

### F1.2 — algoritmo di confronto conservativo

Prima validare la comparabilità: sessione di raccolta, PID/create_time, piattaforma e
semantica di ogni metrica. Un eventuale cambio di eseguibile rende il confronto strutturale
non verificabile. Metadati uguali non dimostrano continuità dell'allocazione fra le due letture.

La chiave attuale `start-end` serve alla UI e non identifica un'allocazione nel tempo.
Mantenere due concetti distinti:

- `address_key`: intervallo `[start, end)`.
- `backing_signature`: metadati disponibili sull'origine, ad esempio device/inode/offset
  per un file Linux; tipo/stato e identificatori nativi per altri provider.

Permessi, nome e categoria possono cambiare senza che si possa dedurre un'allocazione
nuova. Registrare queste differenze; non usare soltanto il pathname, che può essere
rinominato o riportare `(deleted)`. Per regioni anonime, anche lo stesso intervallo con
gli stessi attributi potrebbe essere stato liberato e ricreato: etichettare il confronto
come confronto dello stesso intervallo osservato.

Ordine dell'algoritmo:

1. Validare che ciascuna lista sia ordinata, senza intervalli sovrapposti nello stesso campione.
2. Trovare corrispondenze esatte di intervallo e classificare la compatibilità dell'origine.
3. Per quelle compatibili, calcolare delta solo per contatori presenti in entrambi.
4. Evidenziare separatamente variazioni di permessi, nome, origine o attributi nativi.
5. Per confini cambiati, costruire gruppi di intervalli sovrapposti con una scansione ordinata.
6. Chiamarli «intervalli riorganizzati», non distribuire le vecchie misure sui nuovi pezzi.
7. Classificare gli intervalli non corrispondenti come «solo A»/«solo B» soltanto con
   enumerazioni complete; in caso contrario usare «non osservato nell'altro campione».

Mai ripartire RSS/PSS/USS in proporzione alla dimensione virtuale per ricostruire uno
split: le pagine residenti non sono distribuite uniformemente. Se un gruppo di split/merge
copre esattamente la stessa unione di indirizzi, con origine compatibile e tutti i
contatori disponibili, si può mostrare il delta aggregato del gruppo, dichiarandone il
livello. Altrimenti lasciare il delta del gruppo a n/a.

Stati suggeriti, separati dal segno della variazione:

| Stato | Cosa significa |
|---|---|
| `same_interval` | Intervallo confrontabile; non prova di stessa allocazione |
| `metadata_changed` | Stesso intervallo, attributi cambiati |
| `backing_changed` | Origine incompatibile; evitare continuità implicita |
| `restructured` | Split/merge o confini cambiati |
| `only_a` / `only_b` | Presenza esclusiva osservata con copertura completa |
| `unobserved` | Copertura insufficiente per concludere un'assenza |
| `incompatible` | Origini/processi/definizioni non confrontabili |

Delta per una metrica nota in entrambi: `B − A`, in byte interi con segno. Non usare
`value or 0`. L'assenza provata di una regione in un campione completo può valere zero
nel contributo al delta, ma va distinta da una misura mancante e visualizzata come
assenza, non come uno zero misurato.

La direzione A→B è quella scelta dall'utente: non scambiare automaticamente i file.
Se le sequenze indicano B precedente ad A, segnalare «ordine temporale inverso» e
mantenere il segno B−A. Usare la sequenza della stessa sessione per l'ordine; un cambio
dell'orologio civile non deve invertire silenziosamente la cronologia. Finché non si
conosce un intervallo temporale affidabile, non derivare tassi in byte/secondo.

Il delta dell'intero processo si calcola dai totali completi A/B, non dalla somma delle
sole righe filtrate o delle corrispondenze fortunate. Delta totale e delta delle righe
visibili hanno etichette distinte. Le variazioni PSS possono dipendere dalla condivisione,
non soltanto da nuove allocazioni del processo.

**Esempi di accettazione:**

- RSS 100→130 MiB nello stesso intervallo: +30 MiB.
- USS 0→0: 0 B noto; USS null→10 MiB: delta n/a.
- Regione assente in B parziale: non dichiararla scomparsa.
- Una VMA da 16 MiB diventa due da 8 MiB: struttura cambiata, nessuna divisione artificiale della vecchia RSS.
- Stesso indirizzo con nuovo inode/offset: origine cambiata.
- Stesso PID su un'altra sessione di raccolta: confronto temporale non verificato.

**Test:** aggiungere `tests/test_comparison.py` con questi casi, file cancellati/nomi con
spazi, permessi mutati, contatori null, confronto identico, ordine A/B invertito,
processo terminato, snapshot vuoto completo, snapshot vuoto fallito e limiti di scansione.
Verificare che il motore non dipenda da Textual né da letture OS.

### F1.3 — vista di confronto nella stessa UI

Comandi proposti, da implementare senza sottrarre i tasti attuali:

| Contesto regioni | Nuovo comando |
|---|---|
| `b` | Fissa il campione corrente come baseline A |
| `c` | Alterna vista corrente e confronto A→B |
| `ctrl+b` | Rimuove la baseline |
| `r` | Raccoglie B, conservando A |

`c` resta il comando dei grafici nella schermata principale; nella schermata regioni
assume il significato locale. Documentare il contesto nel footer e nell'aiuto. Digitare
questi caratteri nella ricerca non deve attivare le azioni.

Pannelli della vista confronto:

1. In alto: processo, A/B con orari, durata, origine e copertura.
2. Tabella: intervallo/tipo, stato, valore A, valore B e delta della metrica scelta.
3. Selettore metrica: RSS, PSS, USS e swap quando disponibili; virtuale esplicitamente separato.
4. Inspector: tutti i contatori, motivi del mancato confronto e attributi modificati.
5. Filtri: stato del confronto e ricerca; ordinamento per crescita, riduzione, valore assoluto o indirizzo.

Le barre positive/negative di variazione devono avere zero identificabile e segno
testuale. Non inserire delta negativi nella barra proporzionale della RAM. Conservare
i colori delle categorie nella mappa corrente; non reinterpretarli come crescita senza legenda.
Una vista A/B può avere barre affiancate o righe sovrapposte chiaramente etichettate,
con scala comune; non usare due scale diverse facendo sembrare uguali consumi diversi.

A 80×24 dare priorità a stato, A/B/delta e selezione. Dettagli aggiuntivi nell'inspector
raggiungibile con Tab e scroll. Non rendere obbligatorio il mouse.

**Test UI:** pin, refresh, errore, recupero, filtri, resize, baseline immutabile,
processo diverso, ritorno alla vista corrente, tasti negli input e worker principale vivo.

### F1.4 — prima consegna e confini della cronologia

Consegnare inizialmente **due campioni**, non un registratore illimitato. A/B bastano
per l'obiettivo «prima e dopo questa operazione» e limitano il costo di memoria.

Un aggiornamento automatico opzionale è un incremento successivo della stessa fase:
default spento, nessuna sovrapposizione di richieste, pausa durante chiusura/cambio processo,
intervallo effettivo e campioni mancati visibili. Non accumulare automaticamente snapshot
completi in una lista. Se si aggiunge uno storico, usare un limite documentato sia in
campioni sia in memoria, indipendente dai 60 campioni aggregati già presenti.

**Milestone F1:** l'utente fissa A, esegue un'azione, raccoglie B e trova le variazioni
senza false sparizioni, falsi zeri o perdita della baseline. Documentazione e test aggiornati.

## 7. F2 — salvataggio, riapertura e confronto offline

### F2.1 — formato versionato e ambito

Nuovi moduli proposti: `capture_io.py` per codec/validazione e `capture_models.py` per
i contratti. Tenere il file JSON corrente di `report.to_dict()` compatibile: non usare
lo stesso nome/versione per un formato che assume significati diversi.

Formato proposto: JSON UTF-8 con suffisso `.rtm.json` e discriminante
`format = "ramtaskman.capture"`, `schema_version = 1` indipendente dal JSON generale.
Prima implementazione: una o due acquisizioni di regioni dello stesso processo, con
eventuale baseline; conservare il campione intero, non soltanto la tabella filtrata.

L'involucro deve contenere:

- versione del programma che ha scritto il file e versione dello schema;
- identificatori dell'acquisizione/sessione, sequenza e metadati del provider;
- identità del processo e timestamp/durate;
- capacità, definizioni delle metriche, unità e dimensione pagina quando rilevante;
- completezza dell'enumerazione, coperture e motivi;
- intervalli, attributi nativi, contatori e valori null;
- eventuale vista iniziale separata: filtro, modalità, ordinamento, selezione;
- modalità di esposizione dei percorsi, se in futuro viene aggiunta una redazione.

I ruoli sono espliciti: `current_capture_id` identifica il campione corrente e
`baseline_capture_id` è null oppure identifica A. Gli ID devono riferirsi a record
presenti e univoci; con due campioni devono essere distinti. Non ricavare i ruoli
dall'ordine dell'array o dai timestamp, perché il confronto può essere temporalmente
inverso. Con un solo record, corrente obbligatorio e baseline null.

Indirizzi e offset: stringhe esadecimali canoniche per evitare perdita di precisione
nei consumatori JSON che usano numeri a 53 bit. Contatori: interi in byte, senza stringhe
GiB/MiB. Timestamp: formato dichiarato, senza troncare l'identità del processo. Tutti
i campi di origine devono sopravvivere alla riapertura su un OS diverso.

Esempio strutturale, non fixture completa e non codice già disponibile:

```json
{
  "format": "ramtaskman.capture",
  "schema_version": 1,
  "producer_version": "versione-effettiva",
  "current_capture_id": "uuid",
  "baseline_capture_id": null,
  "captures": [
    {
      "capture_id": "uuid",
      "collection_session_id": "uuid-sessione",
      "sequence": 4,
      "platform": "linux",
      "backend_id": "linux-smaps",
      "process": {"pid": 100, "started_at": 1700000000.25},
      "enumeration_complete": true,
      "regions": [
        {"start": "0x400000", "end": "0x404000", "rss": 8192, "pss": null}
      ]
    }
  ],
  "view": {"mode": "resident"}
}
```

Definire quali campi sono obbligatori nel codec reale; non importare automaticamente
questo esempio incompleto come una rilevazione valida. Versioni maggiori sconosciute
devono produrre un errore comprensibile. Eventuali estensioni facoltative sconosciute
possono essere conservate/ignorate soltanto senza cambiare la contabilità.

Un futuro salvataggio del sistema generale avrà un tipo di record distinto. Non fingere
che il campione generale e quello delle regioni, raccolti in momenti diversi, siano atomici.

### F2.2 — scrittura locale affidabile

Comando UI proposto: `ctrl+s`, con dialogo Textual per il percorso di destinazione.
L'utente deve vedere cosa salva: processo, orario, completezza, uno/due campioni e
presenza di percorsi. Nessun salvataggio automatico all'apertura della mappa.

Comportamento:

1. Validare il modello prima della serializzazione.
2. Scegliere una destinazione esplicita; non cambiare dischi o usare directory interne non autorizzate.
3. Scrivere un temporaneo nella stessa directory del file finale.
4. Chiudere correttamente il file, completare la scrittura e rinominare atomicamente quando supportato.
5. Se la destinazione esiste, richiedere nella UI la scelta di sostituire o cambiare nome.
6. Su errore/disco pieno lasciare il file precedente intatto e mostrare un messaggio utile.
7. Eliminare soltanto il temporaneo creato da questa operazione, mai file estranei.

Non introdurre pickle, oggetti Python serializzati o esecuzione di classi indicate nel file.
I percorsi sono dati potenzialmente personali: conservarli nel salvataggio esplicito,
non inviarli a servizi. La prima versione non promette anonimizzazione automatica.
Se si aggiunge una redazione, deve essere dichiarata e preservare la comparabilità con
token coerenti nello stesso insieme A/B; non usare hash globali dei pathname come anonimato garantito.

Aggiungere a `.gitignore` una destinazione convenzionale di acquisizioni locali, per
esempio `recordings/`, senza impedire fixture sintetiche controllate sotto `tests/fixtures/`.
Il solo gitignore non sostituisce il controllo del contenuto prima di un commit.

**Test:** round-trip completo/parziale/null/zero, due campioni, Unicode/spazi, errore di
scrittura, file esistente, temporaneo rimosso e file originale integro. Niente nuovi test
generici del filesystem: testare il contratto concreto del codec/salvataggio.

### F2.3 — importazione limitata e replay senza raccolta

Limiti iniziali proposti, da dichiarare come decisioni di progetto: 64 MiB per file,
massimo due acquisizioni di regioni nel contenitore v1 e 32.768 regioni per acquisizione.
Verificare la dimensione durante la lettura, non soltanto con uno stat iniziale.
Per file oltre limite proporre un messaggio, non aumentare silenziosamente la memoria allocata.

Validazione prima della UI:

- JSON ben formato, niente chiavi duplicate ambigue, niente NaN/Infinity;
- discriminante/versione e campi obbligatori;
- interi veri per byte/PID: rifiutare booleani usati come numeri;
- quantità non negative, intervalli validi, indirizzi entro il dominio dichiarato;
- limiti su stringhe/attributi e assenza di duplicati delle regioni;
- coerenza tra identità dei record, baseline e capacità dichiarate;
- nessuna esecuzione o apertura automatica dei pathname contenuti;
- testo mostrato come testo, senza interpretare markup Rich o sequenze di controllo importate.

Separare errori di formato da contatori non disponibili: un file corrotto non è un
campione con tutti zeri. I controlli strutturali non devono imporre uguaglianze tra
metriche che il provider non garantisce.

Comando UI proposto: `ctrl+o`; CLI proposta:

```text
ramtaskman --open acquisizione.rtm.json
ramtaskman --compare prima.rtm.json dopo.rtm.json
```

Sono comandi futuri. Implementare la mutua esclusione con le modalità live esistenti;
messaggi CLI e codici di uscita devono essere definiti nei test. `--compare` apre
inizialmente la TUI di confronto; un formato batch del diff può essere aggiunto dopo,
senza confonderlo con l'attuale `--json`.

Per eliminare ambiguità nella prima versione, `--compare A B` richiede **esattamente
una acquisizione per file**: il primo argomento è A, il secondo B. Se un file ne contiene
due, rifiutare il comando con un messaggio che indica di usare `--open` per il confronto
già contenuto; non scegliere automaticamente il primo o l'ultimo record. `--open` su
un file con due campioni usa i ruoli espliciti e può aprire direttamente la vista A/B.
Se in futuro si aggiungono selettori per capture_id, documentarli e testarli separatamente.

Modifica decisiva: `cli.main()` oggi costruisce `Collector()` prima di scegliere la
modalità. Spostare quella costruzione nel ramo live. Nel replay non costruire collector,
provider nativi o worker di campionamento. La vista deve usare i dati importati con
un'indicazione permanente «Acquisizione salvata — nessun aggiornamento live».

`r` nel replay non deve rileggere il PID del file; disabilitarlo o spiegare che il
campione è fisso. Un file Linux deve aprirsi anche su Windows/Mac senza tentare `/proc`.
I filtri, la mappa e il confronto devono riutilizzare le funzioni pure della UI corrente.

**Test:** sostituire Collector/reader con stub che falliscono se chiamati; aprire e
navigare il replay deve riuscire senza una sola chiamata. Provare caricamento fallito
senza perdere la vista precedente, file troppo grande, versione futura, dati malformati,
piattaforma diversa e origine incompatibile nel confronto.

### F2.4 — consegna offline

Aggiornare README, help, schema documentato e fixture sintetiche complete.
L'utente deve poter salvare A e B, chiudere il programma, riaprirli e ottenere gli
stessi valori e stati del confronto. Stato della ricerca e zoom sono accessori;
nessuna loro informazione può sostituire i dati originali.

**Milestone F2:** replay portabile, senza letture live e senza perdita di null,
copertura, identità o semantica. Export del campione completo indipendente dai filtri.

## 8. F3 — completamento multipiattaforma

### F3.1 — separare provider, dati e UI

`RegionScreen` oggi controlla `platform == 'linux'` e istanzia `LinuxRegionReader`.
Introdurre `make_region_provider()` e un protocollo unico; iniettare il provider come
già si fa nei test con `region_reader`. La UI deve interrogare capacità, non moltiplicare
rami Windows/Linux/macOS dentro i widget.

Contratto proposto:

```text
RegionProvider
  capabilities
  read(process_identity, limits, cancellation) -> acquisizione regioni

make_region_provider(platform) -> Linux / Windows / Mac / Unsupported
```

Possibile organizzazione: mantenere modelli comuni in `regions.py`, estrarre il reader
Linux in `backends/linux_regions.py`, aggiungere `windows_regions.py`, `macos_regions.py`
e una factory. Conservare inizialmente un re-export compatibile per i test/chiamanti.
Non rinominare contemporaneamente tutti i moduli senza necessità.

Adattamenti al modello:

- metadati nativi in una struttura limitata e serializzabile;
- `permissions` leggibili, senza presentare una stringa Linux come equivalente perfetto su altri OS;
- metriche native con nome distinto, unità, fonte e definizione;
- dimensione pagina rilevata, non fissata a 4096;
- origine/categoria e attendibilità della classificazione;
- separazione enumerazione completa / letture delle pagine complete;
- default/fallback di ordinamento coerente con le metriche disponibili.

Un provider può avere la mappa virtuale disponibile e la mappa residente indisponibile.
La UI deve comunque mostrare le regioni, senza convertirne la dimensione virtuale in RSS.

**Uscita:** Linux invariato nelle funzioni e nel costo; provider simulati con capacità
diverse aprono la stessa schermata senza dipendenze native importate sul sistema sbagliato.

### F3.2 — Windows: intervalli prima, residenza dopo

Fatto verificato: `VirtualQueryEx` descrive intervalli dello spazio virtuale del processo;
`QueryWorkingSetEx` interroga informazioni sulle pagine agli indirizzi richiesti.
Queste API sono la base proposta per la nuova raccolta, non una funzione già presente.
Fonti: [VirtualQueryEx](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex),
[QueryWorkingSetEx](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-queryworkingsetex).

**W1 — prova tecnica su Windows reale.**

- Rilevare OS, architettura del sistema/interprete, dimensione pagina e versione Python.
- Usare un piccolo processo di prova con allocazioni controllate, non un processo privato dell'utente.
- Confermare ABI, dimensioni strutture, larghezza puntatori e codici di errore.
- Provare almeno processo accessibile, terminato e non accessibile.
- Documentare il comportamento delle architetture diverse; non dichiarare copertura cross-bitness senza prova.

**W2 — enumerazione virtuale.**

- Aprire handle con i diritti necessari; chiuderlo in ogni uscita, compresi errori e cancellazione.
- Avanzare con controlli su dimensione nulla, overflow, progresso e limite degli indirizzi.
- Distinguere libero, riservato e committed; tipo private/mapped/image e protezioni native.
- Non trasformare spazio riservato o committed in RAM residente.
- Rappresentare i vuoti come struttura della mappa, non come consumo del processo.
- Raccogliere eventuali nomi file con API di metadati documentate e permessi disponibili.
- Limiti di regioni, chiamate, byte di risultato e tempo; risultato parziale con motivo.

**W3 — contatori residenti per regione.**

- Interrogare pagine in batch limitati, senza creare un array grande quanto tutto lo spazio virtuale.
- Evitare accessi ai contenuti e operazioni che forzano la residenza delle pagine per misurarle.
- Aggregare soltanto osservazioni valide, indicando la copertura della regione.
- Distinguere successo della chiamata API, pagine effettivamente interrogate e bit
  `PSAPI_WORKING_SET_EX_BLOCK.Valid`. Quest'ultimo non è l'esito della chiamata:
  interpretare il ramo `Invalid` quando previsto dal contratto e non leggere campi
  riservati al ramo valido. Una pagina interrogata con stato non residente documentato
  non equivale a una lettura fallita. Provare esplicitamente residenti, non residenti,
  batch falliti e batch parziali, mantenendo separate copertura e residenza.
- Se una regione non è interamente valutata, conservarne i metadati e lasciare il totale
  residente sconosciuto; eventuale somma osservata deve avere un nome distinto.
- Verificare il caso di pagine grandi e la semantica della granularità restituita.
- Attribuire USS solo quando la definizione di residenza privata è verificata, senza
  sostituirla con MEM_PRIVATE, commit o un semplice flag «può essere condivisa».

Il campo ShareCount dell'informazione working-set è limitato; non usarlo per inventare
una PSS equivalente a Linux. Anche Shared va interpretato secondo la documentazione.
Fonte: [PSAPI_WORKING_SET_EX_BLOCK](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-psapi_working_set_ex_block).

PSS, swap effettiva e SwapPSS per regione restano n/a finché non esiste una fonte con
semantica dimostrata. Commit e riserva possono essere mostrati come contatori Windows,
con barre/denominatori propri. Il percorso file identifica l'origine della mappatura,
non esclude pagine private prodotte da copy-on-write.

**W4 — verifica end-to-end.**

Confrontare contatori equivalenti con strumenti OS, annotando le differenze temporali.
Usare allocazioni di prova: riserva senza touch, commit, touch, file mappato e rilascio.
Non aspettarsi uguaglianza perfetta tra letture sequenziali. Ripetere apertura/chiusura
per individuare handle persi; verificare keyboard/resize e replay Linux su Windows.

**Uscita Windows:** mappa virtuale reale, residenza quando misurabile, errori chiari,
limiti rispettati, CI nativa e rapporto hardware. Nessun requisito di amministratore
per il normale avvio; i processi non accessibili rimangono parziali.

### F3.3 — macOS: prova delle API e limiti di accesso

Fatto verificato: XNU espone interrogazioni di regioni Mach e strutture con informazioni
sulle regioni/submap. La traduzione dei campi in contatori ramtaskman deve essere verificata
sull'SDK e sul sistema realmente usati, non dedotta dal nome del campo.
Fonti: [mach_vm.defs](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/mach_vm.defs),
[vm_region.h](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/vm_region.h).

**M1 — prova tecnica obbligatoria.**

- Verificare SDK, ABI, tipi, conteggi delle strutture e page size sul Mac disponibile.
- Provare prima il proprio processo e un processo di test figlio.
- Verificare quale accesso al task è consentito senza modifiche alle protezioni del sistema.
- Distinguere una capacità non disponibile da un errore di autorizzazione.
- Registrare architettura reale: un test ARM64 non valida automaticamente x86_64 e viceversa.

**M2 — regioni e submap.**

- Valutare `mach_vm_region_recurse` e i flavor/contatori documentati nell'SDK usato.
- Percorrere correttamente le submap, con limiti di profondità, progresso e numero di intervalli.
- Non sommare un contenitore e i suoi figli: produrre una lista finale senza duplicazioni.
- Gestire indirizzi, offset, protezioni e riferimenti/porte con durata esplicita.
- Rilasciare tutte le risorse native anche quando il task termina o la lettura è annullata.

**M3 — semantica delle misure.**

- Collegare soltanto contatori verificati alle colonne comuni.
- Mantenere distinti resident, private resident, compressed, reusable, footprint e virtuale.
- Non trasformare ref_count in divisore PSS; non convertire automaticamente un campo
  riferito a pagine non residenti in swap su disco.
- Preservare i contatori nativi interessanti con nomi e unità propri, anche quando non
  entrano nelle barre comuni.
- Se un metadato file non è disponibile, mostrare n/a, senza aprire il file o ricostruire
  il nome leggendo memoria, cmdline o environment.

Non disabilitare SIP, non modificare entitlements o configurazioni di sicurezza per
ottenere artificialmente una dimostrazione. Se l'accesso ai processi esterni è limitato,
la consegna deve descrivere precisamente quel limite e cosa rimane utilizzabile.

**M4 — validazione:** processo di prova con regioni riconoscibili, processo terminato,
lettura negata, snapshot parziale, conteggi pagina e submap; confronto con fonti OS
equivalenti e prove UI/replay. Test simulati separati dalle prove hardware.

### F3.4 — sistema globale e raggruppamento applicativo

La parità multipiattaforma riguarda anche le etichette e il riconoscimento delle app,
non soltanto l'apertura della mappa.

**Contatori generali:** fare un audit del backend psutil corrente sulla versione bloccata.
Verificare soprattutto il significato delle quantità chiamate swap/pagefile/commit,
free/available e cache su ciascun OS. Correggere eventualmente etichette e note prima
di aggiungere categorie nuove.

Windows: valutare i contatori pubblici disponibili, per esempio quelli restituiti da
[GetPerformanceInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getperformanceinfo),
come indicatori separati. macOS: documentare le categorie ottenibili dalle API host
supportate. Una partizione colorata globale è ammessa solo dopo aver dimostrato che
le componenti sono disgiunte, nello stesso dominio e con totale noto. Altrimenti
mantenere la barra in uso/disponibile e mostrare gli altri contatori separatamente.
Non chiamare «slab» una categoria nativa diversa per ottenere lo stesso colore.

**Raggruppamento:** separare identità dell'applicazione e identità della sua istanza.
Un package ID, bundle ID o pathname può essere utile come etichetta, ma non basta sempre
a riconoscere l'istanza e tutti i suoi helper. Studiare metadati espliciti per piattaforma;
non unire l'intero albero di un launcher, una sessione o tutti i processi dello stesso interprete.

Conservare sempre UID/account, provenienza del raggruppamento e fallback dichiarato.
Non mescolare utenti. Ogni processo appartiene a un solo gruppo nella stessa vista.
La ricerca di un helper continua a selezionare il gruppo intero senza alterarne i totali.
Se non esiste un criterio migliore verificato, il fallback corrente resta una scelta valida.

**Test:** due istanze con stesso nome, helper differenti, proprietario sconosciuto,
launcher condiviso, processi Python/Electron distinti, processi usciti e campi non leggibili.

### F3.5 — matrice di accettazione per piattaforma

Creare un rapporto breve per ogni ambiente realmente provato:

| Campo | Informazione richiesta |
|---|---|
| Ambiente | OS/build, architettura sistema e Python, versioni Python/psutil/Textual |
| Capacità | Regioni, nomi, resident, private, metriche native, limitazioni |
| Casi reali | Processo proprio, test figlio, protetto, terminato, memoria mappata |
| Risorse | Durata, conteggio regioni/pagine, handle/porte, memoria del monitor |
| UI | Tastiera, resize, 160×48 e 80×24, chiusura e ripristino monitoraggio |
| Offline | Apertura di acquisizioni provenienti da un altro OS, senza raccolta |
| Esito | Passato / fallito / non eseguito, con motivo |

**Milestone F3:** funzionalità disponibili dichiarate per piattaforma, prove native
effettive e fallback comprensibili. Non richiedere numeri identici tra OS; richiedere
definizioni corrette, navigazione coerente e nessuna metrica fabbricata.

## 9. F4 — prestazioni e campionamento a budget

### F4.1 — misurare prima di cambiare architettura

Introdurre uno strumento di benchmark locale con dati sintetici, per esempio
`tools/benchmark_memory.py`. Non usarlo come dipendenza runtime e non aggiungere pacchetti
se timer standard, tracemalloc e psutil già presenti sono sufficienti.

Separare almeno:

1. enumerazione processi e identità;
2. lettura contatori generali;
3. lettura regioni;
4. raggruppamento, filtro, ordinamento e diff;
5. popolamento DataTable e rendering;
6. latenza di risposta a ricerca, selezione, resize e chiusura;
7. RSS del monitor e risorse native dopo cicli ripetuti.

Carichi sintetici proposti: 100/1.000/10.000 processi e 100/1.000/10.000/32.768 regioni,
con distribuzioni variabili, contatori null e ritardi artificiali. Non generare file
enormi nel repository; costruire i dati in memoria o in output locali ignorati.

Misurare warm-up, mediana e percentile alto su ripetizioni definite. Registrare macchina,
dimensione terminale e versioni. Le misure reali precedenti (63 regioni in circa 7 ms,
784 processi in circa 869 ms) sono esempi puntuali, non soglie universali.

Obiettivi iniziali da verificare, non risultati già ottenuti:

- le azioni ordinarie di tastiera non attendono la conclusione di una raccolta;
- elaborazioni UI lunghe sono suddivise in tranche, mirando a <50 ms di occupazione continua;
- dopo debounce, una ricerca tipica risponde nell'ordine di 200 ms sulla macchina misurata;
- cancellazione recepita entro la successiva unità di lavoro, salvo syscall nativa già in corso;
- nessuna crescita monotona non spiegata di memoria/handle durante cicli ripetuti.

Non mettere soglie wall-clock rigide e fragili nella CI comune. I test verificano limiti,
fairness e cancellazione con clock/ritardi controllati; il benchmark misura i tempi reali.

### F4.2 — budget del campionamento generale

`Collector.sample()` oggi scansiona tutti i processi in sequenza. Aggiungere cancellazione,
limiti e telemetria mantenendo il contratto dei dati mancanti.

Modello di copertura da aggiungere prima del budget:

- enumerazione completata o parziale;
- processi enumerati, identità riuscite, misure tentate/valide, negati, usciti e rinviati;
- timestamp per osservazione o intervallo della lettura;
- motivo della scansione parziale;
- età e provenienza di eventuali misure conservate.

Prima implementazione raccomandata: **nessuna cache dei contatori di memoria**.
Un processo rinviato conserva l'identità enumerata, ma i contatori non letti sono null
con motivo «non campionato nel budget». Non riempire con il valore del giro precedente.
La cache di metadati economici, se necessaria, deve essere invalidata da PID/create_time.

L'enumerazione delle identità precede la scansione costosa, ma può a sua volta essere
limitata: rappresentare esplicitamente anche questo caso. Se non si conoscono tutti i
membri di un'applicazione, il suo totale non può diventare «completo» solo perché tutte
le righe presenti hanno una misura. Adeguare i modelli di gruppo/copertura prima di
applicare budget che possono troncare l'elenco.

Politica di scheduling:

1. Coda ruotante tra i processi per evitare che i primi PID consumino sempre il budget.
2. Preferenza limitata al processo/app selezionati, senza escludere indefinitamente gli altri.
3. Backoff per letture ripetutamente negate o lente, con nuovo tentativo e motivo visibili.
4. Nessuna sovrapposizione illimitata di giri; massimo uno per tipo di raccolta.
5. Uscita/pausa/cambio contesto controllati tra unità di lavoro.

Budget configurabili con valori finiti e limiti sensati. Conservare il comportamento
completo come default finché le misure non giustificano un nuovo default. Documentare
se l'intervallo resta pausa dopo la scansione o diventa una scadenza: non cambiare
silenziosamente il significato di `--interval`.

**Test:** processi lenti, primi PID costosi, arrivi/uscite continui, equità su più giri,
permessi, rinvii, campioni vuoti e aggregati incompleti. Nessun punto storico deve
sembrare aggiornato quando contiene soltanto valori precedenti.

### F4.3 — costo della UI, del confronto e delle importazioni

Oggi `render_regions()` ricrea la DataTable a ogni filtro/ordinamento. Il worker di
raccolta non protegge il thread UI da questo costo.

Procedere dalle misure, in questo ordine:

- evitare il ricalcolo del diff immutabile quando cambia solo la selezione;
- calcolare una volta gruppi e indici per ogni nuova snapshot;
- applicare un debounce breve alla ricerca, mantenendo Invio immediato;
- spostare trasformazioni costose su snapshot immutabili in worker cancellabili;
- scartare risultati di ricerca/ordinamento superati tramite generazioni;
- aggiornare in modo incrementale le righe, o inserirle in tranche limitate;
- usare le capacità di virtualizzazione della tabella prima di costruire widget propri;
- se serve paginazione, dichiarare righe totali/visibili e non cambiare i totali della mappa senza indicarlo.

La mappa ha tante celle quante sono le colonne del terminale; non deve allocare un
oggetto per ogni byte o pagina fisica. Il calcolo può usare liste ordinate e somme
cumulative. Per split/merge evitare confronti di ogni regione con ogni altra: preferire
una scansione ordinata con complessità legata al numero di intervalli.

Importazione e confronto di file grandi devono avere gli stessi limiti/cancellazione
della raccolta. Nessun parser o worker abbandonato deve continuare ad accumulare risultati
dopo che l'utente ha chiuso la schermata.

**Test UI:** generazioni fuori ordine, digitazione veloce, resize durante caricamento,
chiusura prima del risultato, selezione stabile, baseline conservata e controllo dei
worker. Misurare separatamente tempo di trasformazione e tempo di mount/render.

### F4.4 — consegna prestazionale

Conservare un rapporto breve con dati prima/dopo, numero di ripetizioni e macchina.
Non dichiarare «più veloce» da una sola misura né nascondere il costo di memoria della cache.
Preferire una modifica con beneficio misurato a parallelismo generalizzato non necessario.

Se si valuta una raccolta parallela, limitarne esplicitamente la concorrenza e verificare
contenzione, pressione sul kernel, cancellazione e consistenza. I budget sono cooperativi;
un timeout duro delle syscall richiederebbe isolamento ulteriore e non va promesso da un thread.

**Milestone F4:** UI reattiva sul carico dichiarato, copertura onesta, nessuna starvation
nei test controllati e comportamento di memoria/risorse spiegato.

## 10. F5 — consolidamento, Git, CI e distribuzione

### F5.1 — preservare e registrare il lavoro locale

Separare il consolidamento della base esistente dai nuovi incrementi. Prima di creare
commit controllare index, working tree e file nuovi; le rimozioni dei moduli GPU fanno
parte della derivazione RAM e non vanno ripristinate automaticamente.

Verificare l'identità Git effettiva. Se manca, chiedere soltanto i dati necessari al
commit; non inventarli e non cambiare configurazioni globali. Questo blocca il commit,
non la possibilità di completare codice, documentazione e verifiche già autorizzati.

Sequenza suggerita dei commit, quando l'esecuzione del piano sarà autorizzata:

1. base ramtaskman già verificata e piano;
2. origine/capacità e confronto puro;
3. UI del confronto;
4. codec e replay;
5. provider comuni e backend per piattaforma, separati;
6. ottimizzazioni misurate;
7. pacchetti, documentazione e preparazione della versione.

Usare staging esplicito e controllare il diff staged prima di ciascun commit. Non
aggiungere indiscriminatamente acquisizioni, log o artefatti. Non riscrivere la cronologia
upstream. Mantenere il prefisso `codex/` per nuovi branch quando necessari.

### F5.2 — CI e test di integrazione

Conservare la matrice corrente come punto di partenza: Python 3.11/3.13/3.14 su Linux,
Windows e macOS. Verificare le versioni effettive disponibili al momento dell'esecuzione;
le etichette `*-latest` non garantiscono una specifica architettura o release del sistema.

Distinguere job:

- test puri dei modelli, diff, codec, filtri e mappe;
- test Textual headless con fixture sintetiche;
- smoke nativo del provider sul processo di test accessibile;
- build e verifica dei contenuti dei pacchetti;
- installazione pulita e avvio del comando installato;
- replay cross-platform senza accesso live.

I test OS-specific devono essere saltati con motivo sull'OS sbagliato; non devono
passare usando accidentalmente un mock nel job definito nativo. Un processo protetto
può rendere legittima una misura non disponibile: verificare il contratto, non richiedere
privilegi aggiuntivi al runner.

La CI si esegue solo quando il codice è in un ambiente remoto autorizzato o in un runner
locale predisposto. Preparare i file workflow non equivale a un risultato CI passato.
Non caricare log di processi reali, acquisizioni o pathname personali come artefatti.

### F5.3 — pacchetti e installazione

Wheel/sdist sono la prima distribuzione supportata; mantenere `run.sh`/`run.cmd` per
l'uso portatile della sorgente. Nessun obbligo iniziale di produrre eseguibili monolitici.

Per ogni release candidata:

1. Sincronizzare versione in `pyproject.toml` e `src/ramtaskman/__init__.py`.
2. Aggiornare lockfile solo se necessario e motivare eventuali nuove dipendenze.
3. Costruire wheel/sdist dalla versione candidata.
4. Ispezionare i contenuti: moduli, CSS e licenza presenti; cache, catture, acquisizioni,
   credenziali e ambienti virtuali assenti.
5. Installare il wheel in un ambiente isolato nella directory del progetto autorizzata.
6. Avviare `ramtaskman --version`, `--once`, `--json` e un replay sintetico dall'esterno
   della directory sorgente, per escludere import accidentali del checkout.
7. Verificare i launcher da una directory con spazi e da una posizione diversa dalla root.
8. Verificare messaggi per Python/uv mancanti, senza download automatici non previsti.

Un eventuale eseguibile autonomo è una sottofase esplicita: scegliere il packager dopo
aver verificato Textual, dipendenze native, firma, architetture, dimensione e avvio.
Non reintrodurre automaticamente gli script GPU rimossi dal progetto originario.

Mantenere il nome del pacchetto locale; prima di una futura pubblicazione verificare
disponibilità del nome, canale e proprietà. Il piano non autorizza a riservare nomi,
creare repository remoti o pubblicare pacchetti.

### F5.4 — documentazione e versione candidata

Aggiornare:

- README: avvio, comandi nuovi, casi d'uso A/B, replay e matrice delle capacità;
- help interno: scorciatoie contestuali, metriche e gestione delle assenze;
- architecture: contratti dei provider, identità, comparabilità e copertura;
- handoff: cosa è completato, prove svolte e prossimo blocco;
- lessons: soltanto lezioni verificate, senza convertirlo in diario;
- schema del formato salvato ed esempi sintetici validi;
- changelog: comportamento cambiato, compatibilità e limiti noti;
- note di validazione native: ambienti davvero provati e casi ancora non eseguiti.

Conservare LICENSE MIT e attribuzione upstream. Le schermate devono essere sintetiche,
coerenti con i contatori e riproducibili quanto necessario; nessun dato reale pubblico
senza richiesta dell'utente.

Preparare localmente una release candidata con elenco degli artefatti e risultati.
Un tag/commit locale può far parte del consolidamento autorizzato; push, pubblicazione
di release o upload richiedono una richiesta esplicita. Non aggiungere una seconda
approvazione se l'utente avrà già autorizzato chiaramente quell'azione.

**Milestone F5:** stato Git comprensibile, versione installabile, verifiche documentate
e limiti dichiarati. «Pronto localmente» e «pubblicato» sono stati distinti.

## 11. Matrice dei test e criteri di completamento

| Area | Test obbligatori | Verifica pratica |
|---|---|---|
| Origine | sessione/PID/start, timestamp, capacità e semantiche | nessun confronto tra processi diversi |
| Diff | null/zero, assenze, split/merge, backing cambiato | A→azione→B comprensibile |
| Baseline | immutabilità, errori, refresh, selezione | A non si sposta automaticamente |
| File | round-trip, versioni, limiti, salvataggio fallito | apri altrove senza letture live |
| Replay | Collector/reader vietati, controlli disattivati | r non interroga il PID salvato |
| Windows | ABI, handles, regioni, pagine, permessi, limiti | prova nativa su macchina documentata |
| macOS | ABI, task/submap, page size, risorse e accessi | prova nativa su macchina documentata |
| Gruppi | istanze/utenti/helper, provenienza, copertura | ricerca non altera il totale app |
| Budget | equità, limiti, cancellazione, contatori rinviati | nessuna misura vecchia spacciata per nuova |
| UI | 160×48, 80×24, resize, tastiera, scroll, worker | uso completo senza mouse |
| Pacchetto | contenuti/installazione/versione/CLI/replay | eseguito fuori dalla directory sorgente |

Regola di completamento di ogni blocco:

1. Comportamento implementato e osservabile.
2. Test pertinenti passati, senza sostituire hardware con mock nella descrizione.
3. Diff controllato, nessuna modifica estranea.
4. Documentazione dei cambiamenti e limiti aggiornata.
5. Stato dell'esecuzione annotato con comando, ambiente e risultato.

### Comandi di verifica da riutilizzare

Dalla radice del repository, su Linux/macOS:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once
./run.sh --json
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/capture_screenshots.py
UV_CACHE_DIR="$PWD/.uv-cache" uv build
git diff --check
```

Su Windows, in PowerShell, dalla radice del repository:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run --locked python -m unittest discover -s tests -v
.\run.cmd --once
.\run.cmd --json
uv run --locked python tools/capture_screenshots.py
uv build
git diff --check
```

Durante F1 eseguire prima i test del confronto, quando aggiunti:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -p 'test_comparison.py' -v
```

Usare lo stesso criterio per codec, provider e UI dei blocchi successivi. Dopo i test
mirati, una suite completa prima della consegna individua regressioni tra componenti.
Le catture devono continuare a usare fixture sintetiche; l'output `--once`/`--json`
live non va copiato automaticamente in documentazione, fixture o artefatti remoti.
I comandi futuri `--open`/`--compare` si verificano solo dopo la loro implementazione.

Per le prove manuali A/B usare un processo di test controllato: rilevare A, allocare
e toccare una regione, rilevare B, verificare l'aumento residente, poi rilasciare la
regione e raccogliere un altro campione. La mancata restituzione immediata di memoria
da parte di un allocatore non è automaticamente un errore del monitor. Registrare
la metrica verificata e il comportamento del processo di prova.

Non eseguire suite e benchmark ripetutamente senza un cambiamento o un dubbio concreto.
Per la sola modifica di questo piano bastano verifica dei collegamenti, coerenza e diff;
non servono nuovi test o dipendenze runtime.

## 12. Elenco operativo per il prossimo agente

Tutte le caselle seguenti sono inizialmente aperte. Le prime tre fasi precedenti
(barre/lettore Linux/mappa) non sono rappresentate qui perché già completate.

- [x] F0.1 — baseline Git e test iniziali.
- [x] F0.2 — origine, identità e capacità delle acquisizioni.
- [x] F1.1 — baseline immutabile e macchina a stati.
- [x] F1.2 — confronto puro e casi di topologia/assenza.
- [x] F1.3 — vista Textual del confronto, barra e scorciatoie.
- [x] F1.4 — confronto reale Linux, UI e documentazione.
- [x] F2.1 — contratto JSON capture e codec.
- [x] F2.2 — salvataggio locale affidabile.
- [x] F2.3 — importazione limitata, CLI e replay senza collector.
- [x] F2.4 — round-trip A/B, documentazione e fixture.
- [x] F3.1 — protocollo/factory provider e capacità native.
- [ ] F3.2-W1 — prova tecnica Windows reale; probe e procedura preparati.
- [ ] F3.2-W2 — enumerazione Windows.
- [ ] F3.2-W3 — residenza Windows e copertura per pagina.
- [ ] F3.2-W4 — integrazione e verifica Windows reale.
- [ ] F3.3-M1 — prova tecnica macOS reale; probe e procedura preparati.
- [ ] F3.3-M2 — enumerazione macOS/submap.
- [ ] F3.3-M3 — contatori macOS verificati.
- [ ] F3.3-M4 — integrazione e verifica macOS reale.
- [ ] F3.4 — audit globale e raggruppamento per piattaforma.
- [ ] F3.5 — matrice finale delle capacità e delle prove.
- [ ] F4.1 — benchmark sintetici e letture sul processo di prova; mancano misure su carichi reali estesi.
- [x] F4.2 — budget opzionale, copertura, rotazione, cancellazione, priorità e backoff limitati.
- [ ] F4.3 — cache diff, debounce e tabella paginata; restano misure sistematiche su carichi reali.
- [ ] F4.4 — rapporto prestazioni e controllo risorse.
- [x] F5.1 — identità locale configurata e base consolidata nel commit locale 3a4613f.
- [ ] F5.2 — CI e smoke nativi con esiti verificati.
- [ ] F5.3 — wheel/sdist e installazione Linux verificate; verifiche native e launcher restanti aperti.
- [ ] F5.4 — documentazione e versione candidata locale.

L'agente può spezzare un blocco in ulteriori passi, ma non marcarlo completato finché
il relativo criterio di uscita non è soddisfatto. Se hardware o identità Git mancano,
annotare il limite e proseguire il lavoro indipendente già autorizzato.

### Registro da usare durante l'esecuzione

Aggiornare questa tabella dopo risultati verificati, senza inventare esecuzioni:

| Blocco | Stato | File principali | Verifiche eseguite | Limite residuo / prossimo passo |
|---|---|---|---|---|
| Pianificazione | Completata | Questo documento | Collegamenti e coerenza documentale | Implementazione dei blocchi non iniziata |
| F0–F2 | Completati | capture_models.py, comparison.py, capture_io.py, capture_dialog.py, replay.py, region_screen.py | Test sintetici; confronto Linux con mmap di prova: RSS +8.572.928 byte | Letture sequenziali non provano continuità dell'allocazione |
| F3 | In corso | region_provider.py, backends/windows_regions.py, tools/verify_windows_regions.py, tools/verify_macos_regions.py | Enumerazione Windows e probe simulati; sorgente psutil esaminato | Eseguire [prove Windows](verifica-windows.md) e [macOS](verifica-macos.md); residenza Windows e provider macOS restano aperti |
| F4 | In corso | collector.py, models.py, tools/benchmark_memory.py, [rapporto benchmark](benchmark.md) | Budget e schedulazione; diff in worker, debounce, tabella paginata; misure sintetiche e sul processo di prova | Prove su carichi reali/UI e obiettivi prestazionali non ancora completi |
| F5 | In corso | README, schema-capture.md, workflow, Git | Build, audit e installazione Linux isolata; console script, CLI e replay sintetico verificati; workflow configurato | Matrice CI remota e installazioni native non ancora verificate |
| Verifiche preparate | Completate localmente | tools/verify_windows_regions.py, tools/verify_macos_regions.py, relative procedure | Test simulati, supporto non nativo esplicito e verifica distribuzione locale | Probe Windows/macOS da eseguire sui sistemi originali |

Stati ammessi: da iniziare, in corso, completato, in attesa di verifica esterna.
Distinguere sempre un impedimento esterno da un errore ancora da correggere nel codice.

## 13. Istruzione pronta per continuare nella stessa chat

Testo suggerito per avviare il primo incremento:

> Continua in questa chat sul repository ramtaskman. Leggi AGENTS.md, README.md,
> lessons.md, docs/handoff.md e docs/piano-sviluppo.md. Preserva staged, unstaged e file
> nuovi. Implementa F0 e F1 del piano: origine delle acquisizioni, baseline immutabile,
> confronto conservativo delle regioni e vista Textual A/B. Mantieni i contratti dei
> dati mancanti e la UI attuale. Esegui i test pertinenti, aggiorna documentazione e
> registro del piano, e riferisci cosa è stato realmente verificato. Non pubblicare,
> non creare altre chat e non estendere il lavoro ai provider nativi prima di questa
> consegna. Se un'operazione Git richiede identità non configurata, completa prima il
> lavoro indipendente e chiedi soltanto l'informazione mancante.

Per i successivi passaggi indicare i blocchi desiderati, per esempio F2 oppure F3.1 e
F3.2. Se l'utente autorizza l'intero piano, procedere nelle dipendenze definite senza
richiedere conferme per ogni modifica locale reversibile. La sola lettura di questo
documento non autorizza pubblicazioni o nuove attività fuori dal perimetro.
