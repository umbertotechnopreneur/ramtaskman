# Verifica nativa Windows delle regioni

Questa procedura è **preparata ma non ancora eseguita su Windows reale**. Il provider
`VirtualQueryEx` è sperimentale: visualizza intervalli virtuali, non RSS per regione.
La prova usa soltanto un'allocazione controllata creata dal proprio processo Python.
Non richiede privilegi elevati, non legge i byte di altri processi e non cambia le
impostazioni o la sessione desktop.

## Prerequisiti

- Windows 10 o successivo, Python 64 bit >=3.11, `uv` e una copia del progetto.
- Terminale PowerShell o Windows Terminal. Le prove di UI richiedono un terminale
  che supporti colori e ridimensionamento.
- Non condividere `.venv` tra Linux e Windows: ricreare l'ambiente nel progetto come
  spiegato nel [README](../README.md). I launcher mantengono la cache nel progetto.
- Nessun riavvio, disabilitazione di protezioni, installazione di driver o permesso
  amministratore è necessario per eseguire il processo di prova.

Controllare che Python, uv e la directory del progetto siano disponibili. Dalla radice:

```powershell
.\run.cmd --version
.\run.cmd --once
.\run.cmd --json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Annotare versione/build di Windows, architettura del sistema e dell'interprete,
Python, psutil e Textual, senza copiare in report pubblici nomi o percorsi privati.
L'esito dei test simulati non sostituisce le letture native del passaggio seguente.

## Prova di allocazione controllata

Avviare dalla radice in PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv run --locked python tools\verify_windows_regions.py
```

Il comando stampa **solo a video** un JSON con versione del sistema, architettura,
dimensione della pagina, quattro fasi e risultato del provider. Per osservare la
stessa allocazione nella UI durante il test:

```powershell
uv run --locked python tools\verify_windows_regions.py --hold-seconds 60
```

Il PID temporaneo viene stampato sul terminale prima dell'attesa. In un secondo
terminale avviare `.\run.cmd --processes`, cercare quel PID con `/`, selezionarlo e
aprire la mappa con Invio. Tornare all'output del primo terminale al termine. La
durata massima selezionabile è 300 secondi; la verifica libera l'allocazione prima
di uscire. L'indirizzo virtuale mostrato nel JSON serve solo a confrontare la riga
del processo di prova e può cambiare tra esecuzioni.

Le fasi previste sono:

| Fase | Operazione | Cosa controllare |
|---|---|---|
| `reserved` | Riserva 8 MiB nel proprio processo | `VirtualQueryEx` mostra `MEM_RESERVE`; la riserva non è RAM residente. |
| `committed` | Effettua commit dell'intervallo | La regione risulta `MEM_COMMIT`; il commit non prova che le pagine siano residenti. |
| `touched` | Scrive un byte in ogni pagina dell'allocazione propria | Confrontare i bit osservati con la fase precedente; il provider dovrebbe trovare una regione che contiene l'indirizzo. |
| `released` | Libera l'intervallo | Osservare il nuovo stato; la mappa può essere cambiata nel frattempo. |

Il JSON riporta per `QueryWorkingSetEx` **pagine richieste**, pagine effettivamente
interrogate e conteggio dei bit `Valid` 1/0 soltanto se tutti i batch sono riusciti.
Se un batch fallisce, i contatori complessivi diventano `null` con motivo: `null` non
è zero. Un controllo fallito non sostituisce la diagnosi del codice di errore.

Il bit `Valid` non è etichettato come RSS né USS. `QueryWorkingSetEx` può interrogare
anche indirizzi fuori dal working set ordinario, incluse pagine AWE e pagine grandi;
le osservazioni della prova con pagine ordinarie non dimostrano automaticamente la
semantica di tutti i processi o tipi di pagina. Il provider riporta ancora RSS
`null` per regione. Fonti: [VirtualAlloc](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc),
[VirtualQueryEx](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex),
[QueryWorkingSetEx](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-queryworkingsetex),
[PSAPI_WORKING_SET_EX_BLOCK](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-psapi_working_set_ex_block).

Il risultato `provider.region_found = false` può dipendere da scansione parziale o
errore e va letto insieme a `provider.complete` e `provider.reason`; non equivale a
un'allocazione di dimensione zero. Il processo di prova raccoglie solo i propri dati.

## Casi aggiuntivi nella UI

1. **Processo accessibile:** aprire la mappa del PID di prova. Controllare che gli
   intervalli siano ordinati, con stato e protezione leggibili, e che i campi RSS,
   PSS, USS e swap per regione rimangano `n/a`.
2. **Processo terminato:** avviare un nuovo processo di prova, selezionarlo, lasciarlo
   terminare e premere `r`. Deve comparire il motivo, senza conservare la vecchia
   rilevazione come se fosse attuale. Non terminare processi estranei.
3. **Accesso negato:** se esiste un processo non accessibile all'utente corrente,
   verificare soltanto l'apertura della mappa e il messaggio di accesso negato.
   Non elevare privilegi per trasformare il caso in successo e non salvare dati privati.
4. **Terminale e ritorno:** provare 160×48 e 80×24, ricerca, pagine, ingrandimento,
   chiusura della vista e aggiornamento successivo del monitor principale.
5. **Acquisizione offline:** aprire un file sintetico `.rtm.json` proveniente da Linux
   con `--open`, quindi premere `r`: il file deve restare offline, senza interrogare
   il PID che conteneva. Il formato è descritto in [schema capture](schema-capture.md).

Per confrontare i contatori generali con uno strumento Windows, confrontare working
set con working set e memoria privata residente con una misura equivalente. Il
private commit/PagefileUsage non è swap su disco né USS. Annotare differenze di orario:
le letture dei due programmi non sono atomiche.

## Esito da registrare

Usare **passato / fallito / non eseguito**, separando ciascuna voce. Non pubblicare
l'output raw, che contiene indirizzi virtuali e potrebbe contenere altre informazioni
locali; condividere solo un riepilogo controllato.

| Voce | Esito | Dettaglio |
|---|---|---|
| Windows/build, architettura, versione Python | non eseguito | |
| Suite test e comandi generali | non eseguito | |
| Stati reserve/commit/touch/release | non eseguito | |
| `Valid`/copertura e casi di errore | non eseguito | |
| Provider trova intervallo controllato | non eseguito | |
| Processo terminato / accesso negato | non eseguito | |
| UI, resize e monitor dopo chiusura | non eseguito | |
| Replay offline | non eseguito | |
| Pagine grandi/AWE e 32/64 bit | non eseguito | Non coperti automaticamente dalla prova ordinaria. |

Se il test rivela un errore, riportare fase, eccezione e versione; non dichiarare
equivalenze RSS/working set o supporto cross-bitness finché non sono dimostrati.
