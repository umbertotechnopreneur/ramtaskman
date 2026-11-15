# Istruzioni per ramtaskman

Scrivi in italiano. Leggi README.md, lessons.md e docs/handoff.md prima di modificare.
Controlla `git status` e preserva il lavoro esistente. Non pubblicare, creare remote di
pubblicazione o inviare contenuti senza richiesta dell'utente.

## Obiettivo e confini

UI terminale Python/Textual con la stessa struttura visiva di gputaskman di Scott Hanselman,
dedicata a RAM, PSS, USS e swap su Linux, Windows e macOS. Conserva LICENSE e docs/upstream.md. Non reintrodurre
backend GPU, dipendenze NVIDIA o pubblicazione PyPI ereditati. I backend RAM Windows/macOS
sono invece parte dell’obiettivo richiesto.
Non riscrivere la UI in un altro framework. Scomponi le estensioni in cambiamenti piccoli.

## Regole dei dati

1. Non disponibile = None nel modello, null nel JSON, n/a nella UI. Mai zero inventato.
2. Linux: PSS/USS da smaps_rollup. Windows/macOS: USS da psutil, PSS non disponibile.
   Non stimarle da RSS. Totali incompleti = None. Commit/pagefile non è USS né swap per processo.
3. RSS può duplicare pagine condivise. PSS dei processi non equivale a RAM totale usata.
4. SwapPSS e Swap sono metriche diverse. Non forzare uguaglianze con la swap globale.
5. Cache e memoria disponibile si sovrappongono: non sommarle come partizioni indipendenti.
6. Le identità dei processi includono PID e create_time. Verifica l'identità dopo la lettura.
7. L'aggregazione per eseguibile è un'euristica applicativa esplicitata. Non chiamarla
   riconoscimento certo di browser, Electron, container o programmi Python.
8. Nessuna lettura di memoria, cmdline, environ, file privati o rete. Non terminare processi.
9. Campionamento fuori dal thread UI; misura sample_ms. Non mostrare dati vecchi come attuali
   dopo un errore. Degrada con una ragione e recupera al campione successivo.

## Verifiche

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once
./run.sh --json
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/capture_screenshots.py
UV_CACHE_DIR="$PWD/.uv-cache" uv build
```

Per modifiche UI usa Textual run_test, `await pilot.pause()` prima delle asserzioni,
verifica 160x48 e 80x24. Esegui solo controlli pertinenti; non aggiungere test per semplici note.
Non salvare nomi e percorsi dei processi reali nelle fixture o nelle schermate pubblicate.
CI configurata su Linux/Windows/macOS; qui è stata eseguita solo la suite locale Linux.
I test mock non sostituiscono le verifiche hardware: documenta cosa è stato davvero eseguito.

## Ambiente portatile

Linux avviato da USB e usato su PC differenti. Prima di cambiare accelerazione o storage,
rileva RAM, GPU e dischi. La cartella del progetto è autorizzata; non spostare cache o dati
su altri dischi interni senza accordo. Non inserire percorsi assoluti del PC nei file del
progetto. Usa run.sh per tenere .venv e .uv-cache locali. Ricrea .venv se il percorso cambia.
L'utente privilegia agenti di coding e API cloud per sviluppo AI; questo monitor non ne richiede.

Non eseguire o programmare logout, reboot, spegnimento, riavvio desktop o arresto del gestore
grafico. Lascia sempre aperta la sessione dell'utente.
