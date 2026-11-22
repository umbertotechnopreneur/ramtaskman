> **Nome file** `handoff.md`<br>
> **Percorso completo** `E:\ramtaskman\docs\handoff.md`<br>
> **Percorso relativo** alla radice del repository `docs/handoff.md`

# Passaggio da Linux a Windows

Aggiornato per il candidato 0.1.1. Il progetto sviluppa e verifica su Linux e
Windows. macOS è sperimentale, senza test o validazione del progetto e fuori
dalla CI.

## Stato del checkout

- Il checkout usa `main` come base del candidato `0.1.1`. La localizzazione
  dell’aiuto e degli errori della valutazione RAM è nel commit `306ea56`.
  La correzione del test di chiusura del confronto A/B è nel commit `515f531`.
- Sono già disponibili le metriche RAM, la UI Textual con dieci lingue, le
  regioni virtuali sperimentali su Windows, il confronto A/B, il salvataggio
  e il replay offline, la valutazione della RAM e le diagnostiche di supporto
  in About. La [guida](guida.md) e l’[architettura](architecture.md) ne descrivono
  uso e limiti.
- I target sono ZIP portatili Windows e Linux x64, Debian amd64 e MSI Windows
  x64 per utente. L’MSI aggiunge il collegamento nel menu Start e il comando nel
  `PATH` utente. Il [controllo MSI](verifica-windows.md#verify-the-per-user-msi)
  è riutilizzabile dalla CI e da un account di prova Windows.

## Verifiche locali su Windows

Eseguite da sorgente il 19 novembre 2026 su Windows 11 x64, build 26300,
con Python 3.14.7, psutil 7.2.2 e Textual 8.2.8.

- **CLI e contatori RAM.** Passati i controlli della CLI localizzata, di
  `--once` e di `--json`. Nel campione reale RSS e USS del processo di
  prova erano coerenti con le letture psutil. PSS, Swap e SwapPSS per
  processo erano `null` nel JSON e le metriche indisponibili mostrate
  nella CLI erano `n/a`. La valutazione della RAM usava USS. Verificata
  anche la lettura dei contatori di commit di sistema.
- **Sonda delle regioni.** L’[allocazione controllata](verifica-windows.md#controlled-allocation-test)
  da 8 MiB ha attraversato `MEM_RESERVE`, `MEM_COMMIT` e `MEM_FREE`.
  Dopo la scrittura, `QueryWorkingSetEx` ha restituito `Valid=1` per tutte
  le 2.048 pagine. Il provider ha trovato l’intervallo e l’RSS per regione
  è rimasto indisponibile.
- **UI e replay.** Textual `run_test` a 160×48 e 80×24 ha usato il backend
  Windows per aprire la regione di prova e verificare ricerca, paginazione,
  zoom, ridimensionamento, accesso negato, aggiornamento dopo l’uscita del
  processo e ripresa del monitor. Il replay della cattura sintetica Linux
  è rimasto offline anche premendo `r`.
- **Suite completa dopo la correzione A/B.** 234 test, 232 passati,
  2 saltati per requisiti Linux, 0 fallimenti.

Le prove UI del 19 novembre sono state automatizzate con Textual sul PC Windows.

### Correzione del test di chiusura A/B

La prima suite completa aveva segnalato un fallimento intermittente. Nel
[test di chiusura](../tests/test_comparison_worker.py), il worker fittizio
poteva terminare allo scadere dei due secondi mentre la vista era ancora
aperta. Un ritardo di 2,5 secondi prima di Esc ha riprodotto il fallimento.
Il test ora conferma la chiusura prima di rilasciare il worker, attende che
il calcolo termini e controlla che la vista resti chiusa, il risultato
venga scartato e l’app continui a funzionare. La correzione riguarda solo
il test. Con lo stesso ritardo, il test corretto è passato.

Usare un ambiente Python Windows separato, ad esempio `.venv-windows`. La
[procedura Windows](verifica-windows.md#prerequisites) imposta ambiente e cache
nella cartella di progetto. Conservare le acquisizioni locali e usare dati
sintetici per materiali destinati alla condivisione.

## Evidenze e riferimenti

- **Linux** — il passaggio del 17 novembre riporta 233 test pre-release
  (230 passati, tre nativi Windows saltati) su Python 3.14.4. Riporta anche
  la verifica dello ZIP Linux estratto. Il precedente checkpoint di 226 test,
  i risultati dei runner e la migrazione dei documenti sono storici.
- **CI Windows** — i risultati sul precedente `main` riguardano il pacchetto
  per macchina. Il workflow del candidato controlla installazione silenziosa,
  avvio e rimozione del nuovo MSI, includendo il `PATH` utente.
- L’[indice](README.md) raccoglie i documenti correnti. Le
  [lezioni](../lessons.md) conservano i contratti tecnici e l’[archivio
  iniziale](history/2026-11-16.md) conserva i checkpoint storici. Il verbale
  Linux precedente è consultabile anche nella cronologia Git di questo file.

> **Nome file** `handoff.md`<br>
> **Percorso completo** `E:\ramtaskman\docs\handoff.md`<br>
> **Percorso relativo** alla radice del repository `docs/handoff.md`
