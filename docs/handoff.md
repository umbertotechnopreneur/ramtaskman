# Stato attuale e passaggio di consegne

Aggiornato il 17 novembre 2026. Sviluppo e verifiche: Linux e Windows.
macOS è sperimentale, non testato né validato dal progetto perché non abbiamo un Mac;
non avviare o pianificare prove native macOS e non aggiungerlo alla CI.

## Ripartire

1. Leggi [README](../README.md), [AGENTS](../AGENTS.md), [lessons](../lessons.md)
   e [CONTRIBUTING](../CONTRIBUTING.md).
2. Controlla `git status` e preserva le modifiche presenti. Il branch di lavoro
   attuale è `codex/ramtaskman-foundation`; non presumere una copia pulita.
3. Usa l'[indice dei documenti](README.md) e l'[architettura](architecture.md).
4. Esegui controlli pertinenti alla modifica e documenta gli esiti realmente osservati.

**Richiesta attuale:** sistemare testi, organizzazione, attribuzioni e immagini,
e tradurre README principale e documentazione pubblica in inglese, conservando
MIT e crediti originali. Il 17 novembre 2026 l’utente ha poi autorizzato commit e push
di tutto e la prima release portable: ZIP Linux/Windows x64 e pacchetto Debian amd64.
Questa autorizzazione sostituisce il precedente vincolo di lasciare tutto locale.

## Funzioni presenti

- Python/Textual; backend Linux e Windows, macOS solo sperimentale.
- RAM globale, RSS/USS, PSS e swap per processo dove disponibili; dati mancanti
  espliciti, copertura e verifica PID + create_time.
- Gruppi Linux per istanza systemd esplicita; fallback utente/eseguibile o nome.
- Filtri, ordinamento, dettaglio, modalità Slim/Full e dieci lingue per UI e CLI.
- Regioni Linux su richiesta, provider virtuale Windows sperimentale;
  confronto A/B, salvataggio e replay offline, tabella paginata.
- Budget opzionale e annullamento cooperativo; nessuna lettura del contenuto della memoria.
- Valore della RAM (`valuation.py`, opzioni CLI, colonna UI, cataloghi e test)
  e About con F1 sono inclusi nella prima release; conservati dal lavoro preesistente.

Non reimplementare queste funzioni. Consulta [guida](guida.md), [schema delle
acquisizioni](schema-capture.md) e [piano con registro](piano-sviluppo.md).
La sequenza iniziale del piano è storica: confronto e replay sono già realizzati.

## Documentazione e immagini

- README principale e guide pubbliche sono in inglese; `docs/i18n/README.it.md`
  conserva la versione italiana. `docs/i18n/README.en.md` rimanda alla versione canonica.
  I nomi dei file esistenti restano stabili; indice e selettori delle lingue sono aggiornati.
  AGENTS, handoff, piano di lavoro e archivio storico restano note interne in italiano.
- [CONTRIBUTING](../CONTRIBUTING.md): ingresso per contributori, traduzioni e verifiche.
- [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md): provenienza, dipendenze e licenze.
- [Upstream](upstream.md): parti riutilizzate di GPU Taskman; `LICENSE` conserva la MIT originale.
- [Galleria](images/README.md): immagini sintetiche e procedura riproducibile.
- `tools/capture_screenshots.py` esporta l'app reale in SVG e misura i ritagli;
  `tools/render_readme_images.py` compone le tavole con resvg-py, gruppo opzionale `images`.
  La galleria pubblica usa la UI inglese; il default italiano dell'app non cambia.
- Le lingue richiedono ancora revisione madrelingua.

## Verifiche e limiti

L'ultima suite completa registrata prima di questo riordino è di **226 test locali
Linux: 223 passati e 3 prove native Windows saltate**. La CI storica del commit
`22e45d5` ha completato i sei job Linux/Windows, Python 3.11, 3.13 e 3.14,
con le prove native Windows. Dettagli nella [cronologia](history/2026-11-16.md).
Questi risultati appartengono ai rispettivi checkpoint, non a ogni modifica successiva.

Restano da eseguire le prove manuali su un PC Windows personale descritte nella
[procedura Windows](verifica-windows.md). I contratti simulati non attestano
l'hardware. macOS e la sua eventuale mappa rimangono fuori dal perimetro interno.

Per questo riordino, su Linux con Python 3.14.4 sono passati **6 test mirati**:
tre di distribuzione e tre di cataloghi/UI multilingua, con `run_test` a 160×48
e 80×24. Sono riusciti cattura sintetica completa, rendering delle sei immagini,
build wheel/sdist e verifica degli archivi, installazione isolata, CLI e replay
offline. Controllati visivamente i sei PNG e verificati 352 riferimenti locali
nei 39 Markdown, senza destinazioni mancanti; `git diff --check` pulito.
La MIT originale è identica byte per byte. L'archivio sorgente include anche
documentazione, immagini, strumenti, test e lockfile; la wheel include gli avvisi.
Le dipendenze runtime non sono cambiate. Non è stata rieseguita la suite completa
né una nuova verifica Windows; macOS non è stato verificato. Nessuna pubblicazione.

Le prove asincrone e la cattura sono state eseguite fuori dalla sandbox locale:
qui la chiusura dell'executor di Python restava in attesa anche con una prova
minima indipendente da ramtaskman, mentre fuori sandbox terminava regolarmente.
Non è stato introdotto un workaround nel codice applicativo.

### Traduzione pubblica in inglese — 17 novembre 2026

Tradotti README principale, guida, architettura, schema, audit, benchmark,
procedure Windows/macOS, revisione storica, lessons, changelog, provenienza,
CONTRIBUTING, attribuzioni e galleria. Conservati risultati storici, contratti,
limiti e crediti. Corretto il paragrafo dell'architettura che presentava il budget
già implementato come sviluppo futuro e un'ancora della revisione verso il vecchio handoff.

Rigenerate le catture sintetiche con galleria inglese e i sei PNG, controllati
visivamente. Verificati 365 riferimenti locali e 5 ancore in 40 file Markdown,
senza destinazioni mancanti. Build wheel/sdist, verifica degli archivi,
installazione isolata, CLI e replay sintetico offline riusciti; `git diff --check`
pulito e MIT identica a HEAD. La cattura usa `run_test`, include 160×48 e 80×24
e tutte le dieci lingue. Nessuna nuova suite applicativa completa, prova nativa
Windows o prova macOS: questo incremento riguarda documenti e lingua della galleria.
Le modifiche applicative preesistenti sono conservate. Nessuna pubblicazione.

### Presentazione, branding e disponibilità dei download

Su richiesta dell'utente: README inglese e italiano con stima del costo RAM
per app in evidenza, prezzo corrente inserito dall'utente, badge CI/Windows-Linux/MIT,
primo riferimento VibeWare collegato al manifesto sul sito e footer sul modello
VoiceDucker. Logo originale e sua MIT copiati senza modifiche da AgentInbox;
attribuzioni e archivio sorgente includono l'avviso del logo. Semplificati i passaggi
più burocratici nelle introduzioni pubbliche, mantenendo la politica macOS.

Il 17 novembre 2026 sono state lette release, esecuzioni e artifact GitHub sia
di `ramtaskman` sia di `VibeKit`: nessuna release e nessun pacchetto portable
Ram Taskman disponibile. La CI specifica esegue `uv build` e verifiche, senza
upload degli archivi. I pacchetti Windows/Linux di VibeKit appartengono ad altre app.
Il README collega quindi sorgente ZIP e pagina CI; non contiene finti download portable.
Ultima CI del repo autonomo riuscita: run `43895631787`, commit `22e45d5`;
il precedente riferimento a `6b757d4` era errato (run cancellata) ed è corretto sopra.
Non sono stati avviati workflow, caricati artifact o pubblicati contenuti.

Per prestazioni future misura prima di introdurre cache o controlli aggiuntivi;
conserva età, copertura e motivi delle letture mancanti. Non presentare una
crescita A/B come prova automatica di leak. Nessuna elevazione, kill o riavvio automatico.

## Cronologia

Il vecchio handoff completo è nell'[archivio del 16–17 novembre](history/2026-11-16.md).
Lezioni durature in [lessons](../lessons.md), cambiamenti per gli utenti in
[CHANGELOG](../CHANGELOG.md), stato operativo in questa pagina.

## Prima release portable — autorizzata il 17 novembre 2026

L'utente ha chiesto commit/push di tutte le modifiche e la prima release.
Workflow `release.yml` su tag `v0.1.0`: suite Linux/Windows su Python 3.11/3.13/3.14,
build nativi x64 PyInstaller con Python 3.13, ZIP Linux e Windows e `.deb` amd64.
Pubblicazione automatica soltanto dopo test e pacchetti riusciti. Nessun job macOS.
Ogni ZIP include Python, dipendenze e avvisi; controlli CLI e UI sintetica
(10 lingue, help, About, 160×48/80×24, replay offline) sullo ZIP estratto.
Il job Linux installa, verifica e rimuove anche il Debian su Ubuntu 22.04.
Checksum SHA-256, wheel e sdist allegati; nessuna pubblicazione PyPI.

Verifica pre-release locale Linux Python 3.14.4: **233 test, 230 passati e 3
nativi Windows saltati**, inclusi valore RAM e About. ZIP Linux estratto verificato.
Il filesystem portatile espone permessi 777: lo staging Debian usa una directory
temporanea con permessi normalizzati; i file ZIP ricevono permessi espliciti.
I pacchetti pubblicati sono costruiti dalla CI, non dal PC di sviluppo.
I link README puntano agli asset v0.1.0 e alla pagina dell'ultima release.
