# Formato acquisizioni ramtaskman v1

Il formato `.rtm.json` salva **metadati** delle regioni di un processo per la
consultazione locale offline. È indipendente da `--json`, che mantiene il suo contratto
precedente. Il file non contiene i byte della memoria delle applicazioni, ma può
contenere nomi di processi, percorsi, indirizzi, PID e orari: trattarlo come dato
potenzialmente personale. Nessuna acquisizione viene inviata automaticamente.

## Contenitore

Il file è JSON UTF-8. La radice contiene esattamente questi campi obbligatori:

| Campo | Tipo | Significato |
|---|---|---|
| `format` | stringa | `ramtaskman.capture` |
| `schema_version` | intero | `1` |
| `producer_version` | stringa | Versione dell'app che ha scritto il file |
| `current_capture_id` | stringa | Identificativo del campione corrente B |
| `baseline_capture_id` | stringa o null | Identificativo del campione fissato A |
| `captures` | array | Uno o due record di acquisizione |

Con un solo record, `baseline_capture_id` è null e `current_capture_id` punta al
record. Con due, i due ID devono essere distinti e puntare ciascuno a un record.
L'ordine dei record e gli orari non determinano i ruoli. Versioni o campi sconosciuti
sono rifiutati dal lettore v1: non si ignorano estensioni che potrebbero cambiare
la semantica dei numeri.

## Record acquisizione

Tutti i campi seguenti sono obbligatori anche quando il valore è null:

| Campo | Tipo | Significato |
|---|---|---|
| `capture_id`, `collection_session_id` | stringhe non vuote | Identità acquisizione e sessione di raccolta |
| `sequence` | intero >= 0 | Ordine della richiesta nella sessione |
| `platform`, `backend_id`, `backend_version` | stringhe non vuote | Origine e contratto del provider |
| `pid` | intero positivo | PID al momento della raccolta |
| `started_at` | numero finito >= 0 | Tempo di creazione del processo, secondi Unix |
| `name` | stringa non vuota | Nome del processo rilevato |
| `executable_identity` | stringa o null | Identità eseguibile disponibile, non aperta al replay |
| `taken` | numero finito >= 0 | Tempo Unix del campione |
| `sample_ms` | numero finito >= 0 | Durata in millisecondi della raccolta |
| `complete` | booleano | Enumerazione regioni completa oppure parziale/fallita |
| `reason` | stringa o null | Motivo principale di incompletezza o errore |
| `metric_definitions` | oggetto stringa→stringa | Identificativi delle definizioni dei contatori |
| `capabilities` | oggetto stringa→booleano | Capacità dichiarate del provider |
| `metric_coverage` | oggetto stringa→coppia di interi | Numero misurato e numero delle regioni osservate |
| `issues` | array di stringhe | Motivi o note associati al campione |
| `regions` | array | Elenco ordinato delle regioni osservate |

La copertura usa come denominatore le regioni **osservate**, anche in un campione
parziale. `complete=false` non permette di dedurre che le regioni assenti siano
scomparse. `started_at` e `taken` sono secondi Unix; `sample_ms` è una durata,
non una garanzia che la lettura sia atomica.

Due acquisizioni sono confrontabili temporalmente soltanto quando sessione,
identità del processo, piattaforma e semantiche richieste sono compatibili. Il fatto
che due file contengano lo stesso PID non prova che provengano dallo stesso processo.

## Regione

Tutti i campi sono obbligatori:

| Campo | Tipo | Significato |
|---|---|---|
| `start`, `end`, `offset` | stringhe | Esadecimale canonico minuscolo con prefisso `0x`, senza zeri iniziali superflui |
| `permissions`, `device`, `path`, `category` | stringhe | Metadati dell'intervallo e categoria descrittiva |
| `inode` | intero >= 0 | Identificativo file riportato dal provider quando applicabile |
| `rss`, `pss`, `uss`, `swap`, `swap_pss` | intero >= 0 o null | Contatori in byte; null significa non disponibile |
| `breakdown` | oggetto stringa→intero o null | Contatori aggiuntivi in byte |
| `vm_flags` | array di stringhe | Attributi di regione riportati dal provider |

Gli intervalli `[start, end)` sono crescenti, non vuoti e non sovrapposti. `end` e
`start` descrivono spazio virtuale; la dimensione virtuale è `end - start` e non
rappresenta necessariamente RAM residente. Il tipo di regione descrive l'origine
individuata dal provider e non dimostra il contenuto di ogni pagina.

`0` è una misura pari a zero; `null` è un valore sconosciuto o non supportato.
PSS, USS, RSS e swap sono viste differenti e non vanno sommate indiscriminatamente.

## Validazione e limiti

Il lettore limita il file a 64 MiB, le acquisizioni a due e le regioni a 32.768 per
acquisizione. La lettura applica il limite ai byte effettivamente letti. Sono rifiutati
JSON non valido, chiavi duplicate, NaN/Infinity, booleani nelle posizioni numeriche,
interi negativi o superiori a 64 bit senza segno, indirizzi non canonici o fuori
intervallo, stringhe superiori a 65.536 caratteri, caratteri di controllo C0/C1 e surrogate isolati,
array/oggetti oltre i limiti interni, regioni sovrapposte, ID incoerenti e coperture
incompatibili con le regioni osservate. La data del campione deve essere rappresentabile
sul sistema che visualizza il file. I testi sono dati e non vengono usati come comandi.

La scrittura usa un temporaneo nella stessa directory, flush e fsync; il percorso
esistente non viene sostituito senza una scelta esplicita. Se fallisce la scrittura,
il file precedente resta intatto e viene rimosso il temporaneo creato dalla richiesta.
Su filesystem che non supportano i collegamenti fisici, la creazione senza sostituzione
può fallire con il relativo errore: scegliere una destinazione supportata.

## Replay e confronto

```text
ramtaskman --open acquisizione.rtm.json
ramtaskman --compare prima.rtm.json dopo.rtm.json
```

`--open` apre uno o due campioni con i ruoli indicati nel file. `--compare` accetta
un solo campione per ciascun file: il primo è A e il secondo B. Un file con due
acquisizioni va invece aperto con `--open`. Il replay non costruisce un collector o
un provider e il tasto `r` non riattiva letture live sul PID salvato.

Per riprodurre un confronto: fissare A nella vista regioni, aggiornare il processo
per ottenere B, salvare il file esplicitamente, chiudere la vista e aprire il file.
I valori e la semantica A/B sono gli stessi; i risultati restano osservazioni
sequenziali e la crescita non dimostra da sola un memory leak. Se A e B sono lo
stesso campione, il codec rifiuta due record con lo stesso ID: aggiornare B o
salvare solo il campione corrente dopo aver rimosso la baseline.

Il file contiene l'intero campione disponibile e non solo le righe selezionate dai
filtri. La vista (ricerca, ordinamento e zoom) non viene salvata nella versione 1.
