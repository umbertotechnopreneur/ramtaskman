# Benchmark locale della memoria

Questo documento descrive misure riproducibili, non requisiti di prestazione garantiti.
Lo strumento usa solo la libreria standard e dipendenze già installate nel progetto.

## Esecuzione

Dalla root, per le trasformazioni sintetiche:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000 32768 --repeat 5
```

Per includere la UI Textual 160×48 e le letture Linux **solo del processo del benchmark**:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python tools/benchmark_memory.py --sizes 100 1000 10000 32768 --repeat 5 --self-linux --ui
```

`--self-linux` non enumera gli altri processi e non stampa PID, nome, percorsi o dati
del computer: misura sul processo del benchmark i metadati di identità, `smaps_rollup`
e `smaps`, senza leggere memoria o i file mappati. Su altri sistemi la sezione è
dichiarata non disponibile. `--ui` usa esclusivamente processi, percorsi e regioni
sintetici e l'harness Textual; non scrive acquisizioni o screenshot. Le dipendenze
e la cache restano nel progetto secondo i launcher.

Ogni operazione viene eseguita una volta per riscaldamento e poi `--repeat` volte.
Le tabelle mostrano mediana, percentile alto e numero di misure quando disponibili.
Il calcolo del percentile con pochi campioni è molto sensibile a un singolo valore:
cinque osservazioni non sono sufficienti per stimare una coda statisticamente robusta.
Rilevare separatamente CPU, sistema, Python e versioni dell'app prima dei confronti;
non aggiungere percorsi o nomi dei processi privati a un rapporto condiviso.

Le misure dei singoli metodi della UI includono l'elaborazione Python e la creazione
delle righe; **escludono il paint effettivo del terminale**. Le misure con `pilot`
includono pause e attese dell'harness, quindi non equivalgono alla latenza di tastiera
reale. Per conoscere la latenza percepita servono anche prove manuali sul terminale reale.

## Risultati del 16 novembre 2026

Linux x86_64, Python 3.14.4, psutil 7.2.2, Textual 8.2.8; cinque ripetizioni dopo il
riscaldamento, terminale simulato 160×48. Sono osservazioni puntuali sulla macchina
usata in quel momento, non una previsione per altri sistemi.

### Letture reali del solo processo di prova

Il processo aveva 138 regioni al primo campione. I tempi sono mediana / percentile alto:

| Fase | Tempo |
|---|---:|
| Identità e metadati cgroup | 0,25 / 0,26 ms |
| Contatori `smaps_rollup` | 0,71 / 0,72 ms |
| Lettura delle regioni `smaps` | 7,81 / 7,93 ms |

RSS del benchmark prima/dopo la sequenza: 39,11 / 39,32 MiB; CPU consumata
complessivamente 50 ms con risoluzione del sistema; file descriptor prima/dopo: 4/4.
Le operazioni includono controlli d'identità propri dei metodi misurati: non sono
contatori kernel indipendenti. La scansione `smaps` è sequenziale e può mutare durante
la lettura. Non moltiplicare questi tempi per il numero di processi del PC per stimare
la scansione generale: permessi, numero di pagine e dimensione dei processi variano.

### Modello e UI con dati sintetici

| Processi / regioni | RAM Python fixture | Gruppi mediana | Filtro mediana | Diff A/B mediana / p95 | `render_regions` mediana / massimo |
|---:|---:|---:|---:|---:|---:|
| 100 | 0,09 MiB | 0,27 ms | 0,05 ms | 0,34 / 0,36 ms | 4,92 / 5,75 ms |
| 1.000 | 1,10 MiB | 1,56 ms | 0,56 ms | 3,26 / 3,26 ms | 11,93 / 15,03 ms |
| 10.000 | 11,29 MiB | 15,71 ms | 5,98 ms | 43,36 / 89,11 ms | 29,35 / 34,68 ms |
| 32.768 | 37,15 MiB | 51,76 ms | 19,46 ms | 171,47 / 242,03 ms | 70,88 / 73,82 ms |

L'ultima colonna misura `render_regions` sincrono dopo una ricerca, con tabella a
pagine di 250 righe; non include il paint. Con 32.768 regioni supera l'obiettivo
iniziale indicativo di 50 ms. Il diff viene mantenuto in cache per A/B immutati;
la prima elaborazione è stata successivamente spostata su un worker cancellabile.
I tempi di apertura UI completi di `pilot` erano 488 / 528 / 570 / 868 ms nelle
quattro dimensioni. Tre variazioni rapide del testo hanno prodotto un solo ridisegno
per ripetizione; l'attesa totale comprende debounce e pause imposte dal test.

### Avvio del confronto in background

Una seconda prova sintetica, tre ripetizioni con 32.768 regioni, ha confrontato due
varianti **entrambe con il calcolo nel worker**. Prima di specificare una descrizione
fissa a Textual, l'avvio dell'azione aveva mediana 153,17 ms: il decorator costruiva
nel thread UI una rappresentazione testuale delle due acquisizioni complete. Con la
descrizione fissa, la mediana è stata 1,61 ms, massimo 1,80 ms. Il tempo fino al
risultato visibile con harness e pause è stato rispettivamente 563,48 e 359,60 ms.
Sono poche ripetizioni; non dimostrano la latenza di un terminale reale né garantiscono
che la UI sia sempre reattiva durante codice Python nel worker. La GIL è condivisa.

Il motore di confronto controlla l'annullamento durante la validazione, l'elaborazione
delle regioni e i totali; la costruzione/ordinamento in memoria non è interrompibile
nel mezzo dell'operazione. Se l'utente chiude la vista o cambia campione, il worker
può finire un'operazione in corso ma il risultato vecchio viene scartato tramite
generazione e identità degli snapshot. Un risultato parziale non viene mostrato.

## Limiti e lavoro ancora aperto

- Non è stata eseguita una misura realistica su tutti i processi del PC: la prova
  reale riguarda esclusivamente il processo di benchmark.
- RSS prima/dopo e numero di fd indicano solo due punti; non dimostrano l'assenza di
  crescita in una lunga sessione. Servono molti cicli controllati, con serie temporali.
- I carichi sintetici non ricostruiscono la distribuzione, permessi, pagine grandi o
  tempi di un browser reale. Non sono state verificate latenze su terminali Windows/macOS.
- Oltre al diff, filtro, ordinamento e `render_regions` a 32.768 regioni possono ancora
  occupare il thread UI; spostarli in elaborazioni cancellabili richiede test di
  generazione e selezione, e ulteriori misure. La paginazione da sola non garantisce
  il completamento entro 50 ms.
- Cancellazione cooperativa non interrompe una syscall o un ordinamento già in corso.
- Il progetto non ha ancora misure di paint, latenza percepita, resize e chiusura su
  sistemi nativi e sotto carico variabile; F4 rimane aperta.
