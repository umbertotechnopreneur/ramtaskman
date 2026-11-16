# Provenienza

- Repository: <https://github.com/shanselman/gputaskman>
- Commit sorgente: `7486bfa0a35e032298534d9c408ff8ad96d9768a`
- Versione dichiarata nel sorgente: 0.4.1
- Acquisizione: 16 novembre 2026
- Autore originale: Scott Hanselman
- Licenza: MIT, conservata integralmente in [LICENSE](../LICENSE).

Il repository è stato clonato con la cronologia completa. Il lavoro RAM si trova sul
branch `codex/ramtaskman-foundation`. Il remote `upstream` identifica soltanto l'origine
pubblica; il push è disabilitato.

## Riutilizzo concreto

- `src/ramtaskman/app.tcss`: blocco CSS di `GpuTaskManager` copiato dal sorgente.
- `src/ramtaskman/widgets.py`: funzioni `spark` e `stacked_bar` copiate dal sorgente.
- `src/ramtaskman/app.py`: composizione degli stessi pannelli Textual, tabella a righe
  alternate, inspector, footer e schermata di aiuto; grafici adattati dalla griglia originale.
- Struttura `src/`, `tests/`, `tools/`, `docs/`, `pyproject.toml`, `uv.lock`, CI conservata
  come organizzazione, con backend RAM Linux/Windows/macOS e CI multipiattaforma.

I collector GPU, scanner di runtime/modelli, release automatiche e packaging GPU/Nix
sono stati rimossi dalla versione RAM. Non restano dipendenze NVIDIA. Il collector RAM,
i modelli, i report e i test sono dedicati al nuovo progetto.

Il sorgente originale resta consultabile senza mantenere una seconda copia attiva:

```bash
git show 7486bfa0a35e032298534d9c408ff8ad96d9768a:src/gputaskman/app.py
```

La UI conserva lo scheletro e lo stile, con contenuti adattati: una replica pixel per
pixel di tutte le viste GPU non è ancora verificata né prevista per le metriche differenti.
