# ramtaskman

[Italiano](README.md) · [English](docs/i18n/README.en.md) · [中文（简体）](docs/i18n/README.zh.md) · [한국어](docs/i18n/README.ko.md) · [Français](docs/i18n/README.fr.md) · [Tiếng Việt](docs/i18n/README.vi.md) · [Español](docs/i18n/README.es.md) · [Português](docs/i18n/README.pt.md) · [Deutsch](docs/i18n/README.de.md) · [日本語](docs/i18n/README.ja.md)

### Capire dove va la RAM, direttamente dal terminale.

**ramtaskman** è un monitor sperimentale della memoria per Linux, Windows e macOS.
Nasce dalla voglia di capire meglio cosa succede alla RAM passando da un sistema
all’altro, senza dover aprire strumenti complicati. È un progetto **Vibeware**:
un’idea personale nata per curiosità e ricerca, diventata uno strumento utile
nel lavoro di tutti i giorni.

![Vista principale di ramtaskman con RAM, grafici e applicazioni](docs/images/overview.png)

*Schermata dell’interfaccia reale catturata su Linux con dati dimostrativi sintetici.*

## Cosa puoi fare

1. **Vedere la RAM a colpo d’occhio.** Barra del sistema, memoria disponibile,
   cache e grafici storici in una UI da terminale, con modalità Slim e Full diagnostics.
2. **Esplorare app e processi.** Passa dai gruppi ai singoli PID e ordina le righe
   per le metriche disponibili, con indicazione della copertura delle letture.
3. **Capire le metriche.** Consulta RSS e USS; su Linux anche PSS, swap e SwapPSS,
   con dettaglio delle componenti e spiegazione dei valori mancanti.
4. **Trovare ciò che cerchi.** Ricerca per nome, eseguibile o PID e filtra per
   utente, swap e dati parziali.
5. **Navigare le regioni di memoria.** Su Linux esplora le mappature di un processo,
   i loro indirizzi virtuali e la residenza; su Windows la vista virtuale è sperimentale.
6. **Confrontare e salvare acquisizioni.** Fissa un campione A, raccogli B e confronta
   le variazioni; salva e riapri acquisizioni locali anche offline.

## Una dashboard, più lingue

![Sei schermate della dashboard in italiano, inglese, cinese, coreano, francese e vietnamita](docs/images/multilingual.png)

*Schermate catturate su Linux con dati sintetici. La localizzazione dell’app è in corso:
la dashboard è parzialmente tradotta; dettagli, regioni, errori e alcuni controlli
restano in italiano o inglese.*

## Uno sguardo dentro

**Full diagnostics** aggiunge la ripartizione della RAM, la barra USS delle app con
letture complete e i contatori disponibili per il sistema operativo.

![Diagnostica completa con ripartizione della RAM e USS delle applicazioni](docs/images/full-diagnostics.png)

**Mappa delle regioni**: scegli un processo per esplorarne le mappature e i relativi
contatori, senza leggere il contenuto della sua memoria.

![Mappa delle regioni di un processo con dati dimostrativi](docs/images/regions-resident.png)

Le immagini sono catturate su Linux dall’applicazione Textual con processi, percorsi e
numeri sintetici: sono esempi illustrativi, non misure del computer di sviluppo.

## Provalo

Servono **Python 3.11 o superiore** e [uv](https://docs.astral.sh/uv/). Su Linux
servono `/proc` e `smaps_rollup`. I launcher creano ambiente e cache nella cartella
del progetto; al primo avvio l’installazione delle dipendenze richiede rete.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

Su Windows, dalla cartella del progetto, usa **Windows Terminal** e avvia:

```powershell
.\run.cmd
```

Per un singolo campione o per l’output JSON: `./run.sh --once` e `./run.sh --json`
su Linux/macOS, oppure `.\run.cmd --once` e `.\run.cmd --json` su Windows.
Il progetto non è pubblicato su PyPI. Non condividere la stessa `.venv` tra sistemi:
ricreala localmente dopo aver copiato il progetto.

La dashboard supporta una traduzione parziale selezionabile con `--language`, per
esempio `./run.sh --language zh`. Codici disponibili: `it`, `en`, `zh` (cinese
semplificato), `ko`, `fr`, `vi`, `es`, `pt`, `de`, `ja`. Su Windows usa ad esempio
`.\run.cmd --language ko`. Le viste di dettaglio e altri messaggi non sono ancora
interamente tradotti.

**Scorciatoie utili:** `m` cambia modalità, `g` alterna app e processi, `/` cerca,
`f` filtra, `d` mostra i dettagli, `r` apre le regioni, `?` spiega le metriche e
`q` chiude il programma. La [guida completa](docs/guida.md) descrive tutti i controlli.

## Sperimentale, con i numeri in chiaro

Questo progetto è nato per ricerca e curiosità: usalo con spirito critico. Le misure
sono raccolte in momenti diversi, i permessi possono limitare la visibilità e il
raggruppamento delle applicazioni non è infallibile. Un valore non disponibile è
mostrato come **n/a**, non come zero.

| | Linux | Windows | macOS |
|---|---|---|---|
| RAM globale, RSS e USS | Disponibili | Disponibili | Disponibili |
| PSS e swap per processo | Disponibili se leggibili | n/a | n/a |
| Mappa regioni | `smaps`, su richiesta | Intervalli virtuali, sperimentale | Non ancora disponibile |
| Verifica su hardware | Eseguita localmente | Da verificare | Da verificare |

PSS non equivale alla RAM totale usata; RSS può contare più volte pagine condivise.
Cache e memoria disponibile si sovrappongono. La swap per processo non viene dedotta
dal commit. Le barre descrivono quote di consumo, non indirizzi fisici. I dettagli e
le altre limitazioni sono nella [guida](docs/guida.md) e nell’[audit dei contatori](docs/audit-contatori-piattaforma.md).

## Ispirazione e ringraziamenti

**Grazie a [Scott Hanselman](https://github.com/shanselman) e a [GPU Taskman](https://github.com/shanselman/gputaskman)**:
la sua interfaccia terminale e il suo progetto sono stati un’ispirazione concreta.
ramtaskman ne riutilizza parti e ne adatta l’impostazione alla memoria RAM; è un
progetto indipendente, non una release ufficiale di GPU Taskman. Provenienza e dettagli
del riutilizzo sono documentati in [docs/upstream.md](docs/upstream.md).

Distribuito sotto [licenza MIT](LICENSE), con il copyright originale conservato.

Traduzioni preparate con assistenza AI: sono gradite correzioni da traduttori e madrelingua.
