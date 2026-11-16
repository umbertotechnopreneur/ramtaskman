# ramtaskman · come leggere i numeri

Sviluppiamo e testiamo su Linux e Windows. Il backend macOS è sperimentale e non è testato né validato dal progetto, perché non abbiamo un Mac disponibile. Eventuali verifiche macOS restano contributi esterni; la CI del progetto non include macOS.

Stessa struttura visiva di gputaskman, dedicata alla memoria di Linux, Windows e macOS.

| Campo | Significato |
|---|---|
| PSS | RAM privata + quota proporzionale delle pagine condivise |
| USS | Private_Clean + Private_Dirty: pagine residenti private |
| RSS | Pagine residenti, comprese quelle condivise: sommare può duplicarle |
| Swap | Swap da smaps_rollup, esclusa la swap shmem; può duplicare pagine condivise |
| SwapPSS | Quota proporzionale della swap condivisa contabilizzata da smaps_rollup |
| RAM used | MemTotal − MemAvailable: non coincide con la somma dei processi |
| Cache | Cached + Buffers + SReclaimable − Shmem; si sovrappone alla memoria disponibile |
| PSI some | Percentuale di tempo con almeno un task in attesa di memoria, media su 10 s |

**Barra RAM:** occupa tutta la larghezza e ripartisce i contatori OS Linux:
anonima, file cache (Cached − Shmem), condivisa/tmpfs, buffer, slab recuperabile/non
recuperabile, altro (residuo calcolato) e libera. Sono categorie contabili: l'ordine non
rappresenta indirizzi fisici. Disponibile è un indicatore separato e include cache
recuperabile, quindi non è un ulteriore segmento. I dettagli clean/dirty e PSS del
processo restano nella vista **d**, perché si sovrappongono ai contatori globali.
Se mancano campi o il campione è incoerente, la barra mostra in uso/disponibile e il
motivo della ripartizione assente. La legenda riporta anche categorie inferiori a un carattere.

**Barra USS app:** prime 10 app con USS completa e altre app complete. La scala è la
somma USS delle sole app complete del campione, non la RAM totale. Numeri e colori
rimandano alla legenda. I gruppi parziali sono esclusi e la copertura è dichiarata.
Il raggruppamento segue la tabella; i segmenti non indicano indirizzi fisici.

**Windows/macOS:** USS e RSS da psutil; PSS, Swap e SwapPSS per processo non sono
esposti e restano n/a. Su Windows il private commit/pagefile NON è swap su disco.
Su macOS RAM used è total − available da psutil, non la Memory Pressure di Activity Monitor.

**Applicazione:** su Linux un cgroup systemd esplicito identifica l'istanza dell'app,
anche con helper diversi. Utenti e istanze distinte restano separati. Senza questa
identità (anche su Windows/macOS) si usa utente + eseguibile, oppure utente + nome
come euristica se il percorso non è leggibile. L'inspector indica il metodo usato.

**Ricerca e filtri:** premi **/** per cercare nome, eseguibile o PID esatto; **f** per
scegliere utente e stato memoria (**con swap** o **dati parziali**). Si combinano fra loro.
Un'applicazione corrisponde se un suo processo soddisfa la ricerca o lo stato memoria,
ma il totale mantiene tutti i membri. Entrando nella vista processi rimangono i filtri.
I filtri agiscono prima del limite Top 30; grafici e dashboard descrivono il sistema intero.
**Invio** dalla ricerca torna alla tabella. **Esc** dai controlli o **Reset** cancella i
filtri; **Esc** nella tabella dei processi torna alle app conservandoli. Dati parziali
considera solo i contatori supportati dal sistema; swap sconosciuta non significa swap usata.

**d** apre il dettaglio RAM del gruppo o processo: PSS anonima/file/shmem, privata e
condivisa clean/dirty, pagine anonime, LazyFree e THP. Campi solo Linux: altrove n/a.
Le righe sono viste sovrapposte, non vanno sommate tutte. Il dettaglio fissa il campione
all'apertura: chiudi e riapri per aggiornarlo. **Esc** o **d** chiude il dettaglio.

**r** o **Invio** su un processo apre la mappa delle regioni Linux. Dentro un'app,
**r** mostra prima i PID: ogni processo ha un proprio spazio virtuale. Le barre di **d**
ripartiscono separatamente PSS e RSS; la swap resta fuori dalla RAM residente.
Nella mappa: **v** alterna RSS/indirizzi virtuali, **s** ordina, **/** cerca file o
indirizzo 0x…, **f** filtra tipo/stato, **z** o **Invio** ingrandisce il vicinato della
regione selezionata, **r** aggiorna, **Esc** azzera i filtri/esce dallo zoom/torna indietro.
La mappa segue gli indirizzi virtuali, non i frame fisici. I buchi sono esclusi dalla
scala virtuale e segnalati con │; le regioni inferiori a un carattere restano in tabella.
Tipo indica l'origine della mappatura, non il suo contenuto: file può avere pagine CoW
private; heap/stack sono solo quelli riconosciuti. I campioni sono su richiesta e
mostrano età, durata e limiti di lettura. Windows: solo intervalli virtuali sperimentali;
macOS: mappa per regioni non disponibile.

Nelle regioni **b** fissa A, **r** raccoglie B e **c** apre il confronto. In confronto,
**v** cambia metrica, **s** ordine, **f** filtra lo stato e **Ctrl+B** rimuove A.
**Ctrl+S** salva i campioni, **Ctrl+O** apre un file offline. I file contengono metadati
e possono includere percorsi personali. I dati mancanti e le regioni riorganizzate
restano n/a; stesso intervallo non dimostra la stessa allocazione né un memory leak.

**n/a non è zero.** Un totale di applicazione è n/a se manca anche un solo valore.
Letture indica la copertura PSS/USS. I totali visibili nel dashboard sono somme
parziali delle sole letture disponibili e non rappresentano tutta la RAM del sistema.
Le letture non sono atomiche: i processi possono cambiare durante il campionamento.
Altri utenti, sandbox e permessi procfs possono impedire le letture. Nessuna elevazione automatica.
HugeTLB non è incluso nei normali contatori RSS/PSS/USS qui mostrati.

Il programma legge metadati: non legge /proc/PID/mem, cmdline, environment o contenuti delle app.

**g** applicazioni/processi · **Invio** processi dell'app selezionata · **Esc** torna alle app
**s** ordinamento · **c** grafico · **a** tutti/primi 30 · **m** compatto/completo
**/** ricerca · **f** filtri · **d** dettagli · **r** regioni · **p** pausa · **?** aiuto · **q** esci

Grafici: ultimi 60 campioni, percentuali con scala 0–100. Lo spazio vuoto indica un dato assente.
L'intervallo è una pausa dopo la rilevazione: la durata effettiva include il tempo di scansione.
