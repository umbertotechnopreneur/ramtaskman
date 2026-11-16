# Revisione del codice — 16 novembre 2026

Revisione locale dei collector, modelli, aggregazione, contatori di piattaforma,
lettore regioni, confronto, acquisizioni e replay, interfaccia Textual, launcher,
verifiche di distribuzione e CI. Le prove native eseguite sono Linux; la lettura del
codice e i mock non sostituiscono prove hardware Windows/macOS.

## Correzioni apportate

- La verifica di distribuzione ora riusa la cache indicata dal chiamante e prepara
  le dipendenze dal lockfile con `uv sync --offline --no-install-project`, prima
  di installare e verificare il wheel. Il precedente `uv pip install --offline`
  falliva su una cache appena popolata perché mancavano metadati dell'indice.
  Il caso è stato riprodotto e verificato con cache e ambiente isolati nel progetto.
- La CI non annulla più gli altri sistemi al primo errore della matrice.
- Il salvataggio delle acquisizioni applica il limite durante la codifica JSON,
  prima di creare o sostituire file, evitando un'allocazione proporzionale a un
  documento molto oltre il limite consentito.
- Su Windows/macOS una lettura `memory_full_info` riuscita elimina un precedente
  errore RSS non più attuale; se entrambe le letture falliscono conserva entrambe
  le ragioni. Gli equivalenti su hardware restano da verificare.
- I nomi di eseguibili Unix conservano i backslash validi nel nome del file;
  quelli Windows continuano a usare le regole Windows, anche nei test simulati.
- Le barre e la mappa calcolano i margini usando le celle terminale, così caratteri
  a larghezza doppia non allargano il disegno oltre la dimensione disponibile.
- La mappa delle regioni elimina subito il contesto RAM vecchio dopo un errore
  del campionamento principale e lo aggiorna quando arriva un nuovo campione.
- Ricerca e legenda delle categorie usano le etichette della lingua scelta. I nomi
  di categoria sconosciuti provenienti da acquisizioni restano letterali.
- Cataloghi UTF-8 separati per lingua sostituiscono righe posizionali molto lunghe;
  i test verificano chiavi e segnaposto, e la verifica del wheel controlla che i
  cataloghi siano inclusi. Ripuliti import inutilizzati e chiariti alcuni contratti
  e passaggi delle funzioni di campionamento e salvataggio.

## Da completare

1. **Verifica della localizzazione.** I checkpoint successivi estendono i cataloghi
   alle schermate e ai messaggi applicativi, inclusi footer, CLI e diagnostica.
   Il contratto separa chiavi e parametri dalla presentazione, conservando i dati
   arbitrari e i dettagli del sistema operativo. L'incremento recente non è stato
   eseguito: restano da verificare layout, binding, errori CLI, serializzazione e
   inclusione delle risorse. Le lingue devono essere riviste da madrelingua.
2. **Prestazioni con carichi molto grandi.** Il confronto viene calcolato in worker,
   ma filtro, ordinamento e parte del rendering della tabella regioni sono ancora
   sincroni. Le misure e i limiti sono in [benchmark.md](benchmark.md); un eventuale
   spostamento in worker richiede gestione di annullamento e risultati obsoleti.
3. **Responsabilità delle schermate.** `RegionScreen` riunisce lettura asincrona,
   filtri, paginazione, confronto, rendering e salvataggio. Conviene separare in
   incrementi piccoli le funzioni pure di presentazione e le operazioni asincrone,
   preservando i test su selezione, generazioni e chiusura dei worker.
4. **Validazione multipiattaforma.** La prima esecuzione GitHub Actions è fallita
   nella verifica della distribuzione Linux e aveva annullato gli altri job. La
   correzione è stata riprodotta localmente; serviranno risultati CI nuovi. I mock
   non dimostrano la correttezza delle API native su un PC Windows o un Mac.

La verifica Ruff isolata per errori di sintassi e nomi/import (`F,E9`) è passata.
Una scansione con la configurazione Ruff dell'host segnala anche numerose regole
stilistiche e permessi eseguibili del filesystem portatile: non sono state applicate
correzioni automatiche indiscriminate o trattate quelle segnalazioni come bug.

La suite Linux ha eseguito 193 test con tre test nativi Windows saltati; i controlli
aggiuntivi su dettaglio localizzato e larghezza delle barre sono poi passati
separatamente. Sono state rigenerate catture sintetiche e verificati `--once`,
`--json`, build, installazione del wheel e replay in un ambiente isolato alimentato
da una cache nuova. Nessun nuovo risultato GitHub Actions è stato ottenuto per queste
modifiche locali.

## Checkpoint successivo senza test

Su richiesta dell'utente, l'incremento successivo è stato preparato e pubblicato
come checkpoint senza eseguire nuovi test, lint, build, catture o avvii dell'app.
I risultati sopra riguardano il lavoro precedente. I file di aiuto sono ora risorse
Markdown per le dieci lingue; la diagnostica OS e ulteriori testi del dettaglio e
del confronto usano i cataloghi. L'helper dei contatori di piattaforma riduce il
metodo principale del dashboard; le righe della tabella usano variabili esplicite
per valori, copertura e identità. La correttezza di queste ultime modifiche dovrà
essere verificata successivamente. I commit contengono `[skip ci]`.

L'ultimo incremento completa le descrizioni del footer e i testi applicativi di
CLI, rapporto `--once`, inspector, collector, provider, confronto e acquisizioni
nelle dieci lingue. I messaggi strutturati mantengono un testo italiano compatibile
con modello e JSON e vengono tradotti al confine della UI; i dettagli OS e i motivi
già registrati nei file rimangono originali. Non sono stati eseguiti nuovi test,
lint, build, catture o avvii dell'app neppure per questo incremento.
