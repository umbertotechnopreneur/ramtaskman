> **Nome file** `README.it.md`<br>
> **Percorso completo** `E:\ramtaskman\docs\i18n\README.it.md`<br>
> **Percorso relativo** alla radice del repository `docs/i18n/README.it.md`

# ramtaskman

[![CI](https://github.com/umbertotechnopreneur/ramtaskman/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/umbertotechnopreneur/ramtaskman/actions/workflows/ci.yml)
![Piattaforme: Windows e Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-0078D4)
[![Licenza: MIT](https://img.shields.io/badge/license-MIT-2EA44F)](../../LICENSE)

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Capire dove va la RAM, direttamente dal terminale.

**ramtaskman** è un monitor sperimentale della memoria sviluppato e testato su Linux e Windows.
Nasce dalla voglia di capire meglio cosa succede alla RAM passando da un sistema
all’altro, senza dover aprire strumenti complicati. È un progetto **[VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto)**:
un’idea personale nata per curiosità e ricerca, diventata uno strumento utile
nel lavoro di tutti i giorni.

**Dai un prezzo alla RAM usata da ogni app.** Inserisci il prezzo attuale della
tua RAM e visualizza una stima semplice della quota di costo hardware attribuibile
a ciascuna app.

C'è anche un backend macOS sperimentale. Non abbiamo un Mac, quindi non lo abbiamo
testato né validato. Le nostre prove e la CI riguardano Linux e Windows.

[Avvio](#provalo) · [Guida (inglese)](../guida.md) · [Documentazione](../README.md) · [Contribuire](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman: dashboard e applicazioni con dati dimostrativi sintetici](../images/cover.png)

*Cattura Textual su Linux: ritaglio di dashboard e tabella in inglese con dati sintetici.
La cornice è una composizione grafica; macOS resta sperimentale e non validato.*

## Provalo

[Ultima release e download](https://github.com/umbertotechnopreneur/ramtaskman/releases/latest)

**I pacchetti x64 includono Python e dipendenze.** Non richiedono .NET.
Estrai tutto lo ZIP portabile e
avvia `ramtaskman.exe` su Windows o `./ramtaskman` su Linux. I pacchetti Linux x64
richiedono glibc 2.35+ (Debian 12+ / Ubuntu 22.04+). Per Debian usa
`sudo apt install ./ramtaskman_<versione>_amd64.deb` con il nome del file scaricato.
Dalla versione 0.1.1, l’MSI per Windows x64 installa per l’utente corrente e rende
`ramtaskman` disponibile nei terminali aperti dopo l’installazione. L’MSI e
l’eseguibile Windows sono privi di firma. I pacchetti ARM64 non sono disponibili.
Le [istruzioni dei pacchetti](../../packaging/PORTABLE.md) spiegano i dettagli;
i checksum sono disponibili nella release.

Per partire dal sorgente, segui invece i passaggi qui sotto.

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
su Linux, oppure `.\run.cmd --once` e `.\run.cmd --json` su Windows. Gli stessi
comandi Unix restano disponibili per il backend macOS sperimentale e non testato.
Il progetto non è pubblicato su PyPI. Non condividere la stessa `.venv` tra sistemi:
ricreala localmente dopo aver copiato il progetto.

I testi dell’app sono disponibili in dieci lingue: `--language` seleziona la lingua
dell’interfaccia, del footer, dell’aiuto, della CLI e del report testuale `--once`,
per esempio `./run.sh --language zh --once`. Codici disponibili: `it`, `en`, `zh`
(cinese semplificato), `ko`, `fr`, `vi`, `es`, `pt`, `de`, `ja`. Su Windows usa ad
esempio `.\run.cmd --language ko`. Anche i messaggi tecnici prodotti dall’app sono
tradotti; identificatori e schema JSON restano stabili, mentre dettagli del sistema
operativo e testi delle acquisizioni conservano la lingua originale. La verifica
locale riguarda Linux con Python 3.14.4: UI sintetica a 160×48 e 80×24, CLI, build,
installazione isolata e replay. Le verifiche native Windows sono eseguite in CI;
la prova manuale su un PC personale resta da completare. macOS è escluso dalle
verifiche del progetto. Le traduzioni attendono ancora una revisione madrelingua.

**Scorciatoie utili:** `m` cambia modalità, `g` alterna app e processi, `/` cerca,
`f` filtra, `d` mostra i dettagli, `r` apre le regioni, `?` spiega le metriche e
`q` chiude il programma. La [guida completa in inglese](../guida.md) descrive tutti i controlli.

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
7. **Stimare il costo RAM di ogni app.** Inserisci un prezzo attuale della RAM per
   tradurre l'uso di memoria in una quota del costo hardware, anche ripartita su più mesi.

## Esplora la memoria

La diagnostica completa distingue RAM del sistema e USS delle app con letture
complete. La mappa delle regioni mostra contatori e indirizzi virtuali; il confronto
A/B aiuta a individuare le variazioni fra due acquisizioni.

![Pannello Full diagnostics: RAM e USS delle applicazioni complete](../images/full-diagnostics.png)

*Ritaglio del pannello diagnostico reale, con dati sintetici. Le quote rappresentano
consumi, non indirizzi fisici; le letture dei processi possono essere incomplete.*

[Vista completa](../images/overview.png) · [Regioni](../images/regions-resident.png) · [Confronto A/B](../images/regions-comparison.png) · [Dieci lingue](../images/multilingual.png)

La [galleria](../images/README.md) contiene tutte le immagini, provenienza e
comandi per rigenerarle. Processi, percorsi e numeri sono sintetici: non sono
misurazioni del computer di sviluppo.

## Valore della RAM e quota mensile

```bash
./run.sh --ram-price 320 --ram-currency EUR
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
./run.sh --json --ram-price 320 --ram-months 36
```

Il prezzo è quello dell’intera RAM della macchina, inserito da te: nessun listino
automatico né richiesta di rete. La capacità predefinita è quella visibile al sistema
operativo, che può essere inferiore alla capacità fisica nominale. Se il prezzo riguarda
un kit da 32 GiB, puoi specificare `--ram-capacity-gib 32`.

Valore = prezzo × byte attribuibili / capacità. `--ram-months` divide questo valore
per il numero di mesi scelto: è una quota del costo hardware, non una bolletta, un
consumo energetico o un risparmio garantito. La quota corrente non è una media mensile.

Linux usa PSS, che ripartisce le pagine condivise; Windows usa USS, quindi valuta
solo la memoria privata residente ed esclude quella condivisa. Nessun fallback a RSS.
I gruppi incompleti o non misurabili rimangono n/a (null nel JSON). Non sommare i
valori delle app con quelli dei processi che le compongono, né con la memoria del
sistema. Cache, kernel e processi inaccessibili non vengono attribuiti arbitrariamente
a Windows o ad altre app. I campioni sono sequenziali, non atomici.

La colonna del valore segue le misure reali durante il monitoraggio; l’inspector
indica la metrica usata. JSON aggiunge `ram_valuation` solo quando richiesto.

Premi **F1** per l’About: VibeWare, Umberto Giacobbi, sito, ringraziamenti a Scott
Hanselman e riferimenti alla provenienza MIT. Esc chiude senza fermare il monitor.

## Come leggere le misure

Il progetto è ancora sperimentale. Le misure vengono raccolte una dopo l'altra,
quindi non descrivono tutte lo stesso istante. I permessi possono limitare ciò
che vediamo e il raggruppamento delle app è un'approssimazione. Le letture mancanti
sono indicate con **n/a**.

| | Linux | Windows | macOS (sperimentale, non testato) |
|---|---|---|---|
| RAM globale, RSS e USS | Disponibili | Disponibili | Backend presente, non validato |
| PSS e swap per processo | Disponibili se leggibili | n/a | n/a |
| Mappa regioni | `smaps`, su richiesta | Intervalli virtuali, sperimentale | Non ancora disponibile |
| Verifiche del progetto | Suite e prove locali | Suite e prove native in CI | Fuori ambito: nessun Mac disponibile |

PSS non equivale alla RAM totale usata; RSS può contare più volte pagine condivise.
Cache e memoria disponibile si sovrappongono. La swap per processo non viene dedotta
dal commit. Le barre descrivono quote di consumo, non indirizzi fisici. I dettagli e
le altre limitazioni sono nella [guida](../guida.md) e nell’[audit dei contatori](../audit-contatori-piattaforma.md).

## Usa, modifica, condividi

Puoi usare, copiare, modificare e redistribuire ramtaskman, anche per uso commerciale,
secondo la [licenza MIT](../../LICENSE). Conserva gli avvisi di copyright e il testo della
licenza nelle copie o nelle parti sostanziali distribuite. Il software è fornito
senza garanzie, come indicato nella licenza.

Sono benvenuti correzioni, traduzioni, segnalazioni e miglioramenti:
[come contribuire](../../CONTRIBUTING.md). Per le dipendenze e il codice riutilizzato,
consulta le [attribuzioni di terze parti](../../THIRD_PARTY_NOTICES.md).

## Ispirazione e ringraziamenti

**Grazie a [Scott Hanselman](https://github.com/shanselman) e a [GPU Taskman](https://github.com/shanselman/gputaskman)**:
la sua interfaccia terminale e il suo progetto sono stati un’ispirazione concreta.
ramtaskman è un adattamento indipendente dedicato alla RAM e riutilizza parti
dell'interfaccia originale. Le [note sulla provenienza](../upstream.md) spiegano
da dove vengono e come sono state adattate.

Distribuito sotto [licenza MIT](../../LICENSE), con il copyright originale conservato.

Traduzioni preparate con assistenza AI: sono gradite correzioni da traduttori e madrelingua.

---

### Questo è VibeWare · [Manifesto](https://umbertogiacobbi.biz/vibeware/manifesto)

Ho creato ramtaskman con l'aiuto dell'AI, partendo da GPU Taskman di Scott Hanselman.
Ne definisco lo scopo, guido lo sviluppo e mi assumo la responsabilità di verificarne
funzionamento, prestazioni e sicurezza. VibeWare è la mia iniziativa per costruire
software utile e aperto con l'AI: ti invito a giudicare il risultato e le prove che lo accompagnano.

Per scoprire cosa significa VibeWare e perché l'ho creato, leggi il
[manifesto VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto).

[ramtaskman su GitHub](https://github.com/umbertotechnopreneur/ramtaskman) · [VibeWare su GitHub](https://github.com/umbertotechnopreneur/VibeWare) · [umbertogiacobbi.biz](https://umbertogiacobbi.biz)

*Puoi esplorare, adattare e condividere ramtaskman sotto licenza MIT, conservando
i crediti originali: il mio contributo alla comunità degli sviluppatori.*

[Termini](https://umbertogiacobbi.biz/terms/) · [Privacy](https://umbertogiacobbi.biz/privacy/)

<p align="right">
  <a href="https://umbertogiacobbi.biz/vibeware/manifesto">
    <img src="../images/vibeware-logo.png" alt="VibeWare — leggi il manifesto" width="160">
  </a><br>
  <strong>VibeWare</strong><br>
  <em>Human intent, AI execution, and plenty of tokens</em>
</p>

> **Nome file** `README.it.md`<br>
> **Percorso completo** `E:\ramtaskman\docs\i18n\README.it.md`<br>
> **Percorso relativo** alla radice del repository `docs/i18n/README.it.md`
