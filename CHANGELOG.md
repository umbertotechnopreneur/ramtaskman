# Modifiche

## In sviluppo — 0.1.0

- Derivazione terminale RAM da gputaskman, con contatori di sistema e processi e
  raggruppamento applicativo; attribuzione e licenza upstream nel README.
- Linux: barra per categorie OS, dettaglio PSS/RSS e mappa delle regioni con filtri,
  ricerca, zoom e confronto A/B. Windows: intervalli virtuali sperimentali; macOS:
  contatori generali, senza provider delle regioni.
- Salvataggio e replay offline delle acquisizioni, con dati mancanti espliciti.
- Budget opzionale di campionamento, paginazione delle tabelle e benchmark locali.
- Procedure riproducibili di verifica Windows e macOS, ancora da eseguire sui sistemi nativi.
- Verifica locale della distribuzione isolata e configurazione CI multipiattaforma;
  nessun rilascio PyPI.
- Nomi ed eseguibili letti dai metadati nativi, evitando i fallback impliciti di
  psutil sulla riga di comando e sul percorso del file.
- README e testi applicativi in dieci lingue, selezionabili con `--language`:
  dashboard, dettagli, regioni, aiuto, footer, CLI e diagnostica dei backend e delle
  acquisizioni. Gli identificatori, i dettagli OS e i testi già salvati restano
  originali. Verifiche locali Linux su CLI, UI multilingua, serializzazione e
  distribuzione; le traduzioni richiedono ancora revisione di madrelingua.

Stato e limiti delle misure, della compatibilità e delle prove si trovano nel README
e nel piano di sviluppo. La versione 0.1.0 è sperimentale.
