# Verifica delle regioni su macOS

**Stato:** procedura e diagnostica preparate su Linux; non sono state compilate o
eseguite con un SDK macOS. La mappa delle regioni macOS di ramtaskman resta da
implementare e validare. I test simulati non dimostrano l'ABI del Mac.

## Preparazione

Usare un Mac sul quale è già presente un compilatore C con SDK macOS; non sono
richiesti privilegi amministrativi per la prova sul processo proprio. Servono anche
Python >=3.11 e `uv` per la suite dell'app. La diagnostica Mach può essere lanciata
con Python standard, senza installare altre librerie Python.

Dalla radice del progetto copiata su una destinazione autorizzata:

```bash
sw_vers
uname -m
python3 --version
cc --version
```

Annotare versione/build macOS, architettura, versione Python e versione/SDK del
compilatore. Un test ARM64 non verifica automaticamente x86_64, e viceversa. Se
compilatore o SDK non sono già disponibili, interrompere la prova e registrare il
motivo: non installarli automaticamente né modificare configurazioni di sistema.
Non usare `sudo`, disattivare SIP, cambiare entitlements o terminare sessioni.

## Probe Mach: solo il processo di prova

```bash
python3 tools/verify_macos_regions.py
```

Il wrapper compila `tools/macos_region_probe.c` usando gli **header dell'SDK locale**:
i tipi e il layout delle strutture vengono così determinati dal compilatore macOS,
senza duplicare l'ABI Mach in ctypes. Il compilatore e i suoi temporanei vengono
indirizzati in una directory temporanea sotto `captures/` del progetto, poi rimossa.
Se `captures/` punta fuori dal progetto, il wrapper si ferma. Non apre rete, file
mappati o contenuti dei processi: usa soltanto `mach_task_self()` dell'helper.

L'helper crea una mappatura anonima sintetica propria da 8 MiB, consulta la regione,
scrive un byte per pagina **nella propria mappatura di prova**, consulta di nuovo,
scorre le regioni proprie tre volte ed esegue `munmap`. Non usa `task_for_pid` e non
esamina altri processi. Non conserva automaticamente l'output. Il JSON non include
indirizzi, PID, nomi dei processi o percorsi mappati; include versione kernel,
architettura e versione Python. Controllare sempre l'output prima di condividerlo.

Il probe limita a 100.000 chiamate per enumerazione e 32 livelli di submap. Un timeout
di 30 secondi interrompe il processo di prova; la compilazione ha timeout di 60 secondi.
Un errore di compilazione, un valore inatteso o un limite raggiunto sono segnalati,
non presentati come una misurazione completa. Nessun timeout promette di interrompere
istantaneamente una singola chiamata kernel.

### Interpretazione del risultato

| Campo | Verifica |
|---|---|
| `probe_exit_code` | 0 indica che il probe ha completato i controlli indicati; 1 segnala errore del probe. Il wrapper può uscire con 2 se non eseguibile. |
| `page_bytes`, `allocation_bytes` | Dimensione pagina riportata dal sistema e 8 MiB richiesti. |
| `before_kr`, `after_kr` | 0 significa che l'interrogazione della regione di prova è riuscita; altrimenti il contatore associato è null. |
| `before_resident_pages`, `after_resident_pages` | Campo nativo Mach per la **regione rilevata**, prima/dopo aver toccato la mappatura. |
| `before_region_bytes`, `after_region_bytes` | Dimensione della regione restituita dal kernel, da valutare insieme ai contatori. |
| `enumerations` | Tre rilevazioni: foglie, submap, chiamate, profondità massima, totale virtuale, codice finale e `limited`. |
| `cpu_seconds` | Tempo CPU dell'helper per le tre scansioni, non latenza di parete e non benchmark dell'intera app. |
| `rss_before_native`, `rss_after_native` | `ru_maxrss` nativo dell'helper: massimo storico secondo il sistema, non delta RSS istantaneo. |
| `munmap_ok` | La mappatura di prova è stata rilasciata. |

Una mappatura può essere unita o divisa dal sistema: la regione restituita può
comprendere più memoria della singola allocazione. Perciò non è garantito che il
delta di `pages_resident` sia esattamente 8 MiB/page size, né che la differenza tra
due scansioni sia atomica. Le pagine possono cambiare tra le letture. Un aumento
coerente con il tocco è un'osservazione da registrare, non una prova che il campo sia
equivalente a PSS o USS Linux. In `enumerations`, un risultato completo atteso ha
`limited: false`, almeno una foglia e codice finale 1 o 3; altri codici sono errori
e il wrapper esce con codice non zero. Un confronto fra somme va fatto solo dopo aver
verificato semantica e assenza di sovrapposizioni.

Per controllare errori e ripetibilità, eseguire il comando più volte, annotando per
ogni esecuzione l'esito del programma, conteggi e codici Mach. Se emergono crescite
continuative sospette, investigare prima di concludere che vi siano perdite: l'helper
è riavviato a ogni esecuzione. Il probe non acquisisce ulteriori task port o diritti
Mach da rilasciare; la porta self è presa in prestito e ogni mmap creata è rilasciata.
Un controllo completo di perdite di porte/handle attraverso un futuro provider
richiederà inoltre prove ripetute **nello stesso processo** e strumenti nativi adatti.

## Applicazione e replay

Nel progetto su Mac, eseguire:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run --locked python -m unittest discover -s tests -v
./run.sh --once
./run.sh --json
./run.sh
```

Il primo uso di uv può richiedere la rete per le dipendenze dichiarate. Non copiare
la `.venv` Linux: creare l'ambiente sulla macchina di destinazione. La UI macOS
attuale mostra i contatori generali disponibili, ma la mappa delle regioni è ancora
segnalata come non implementata. Verificare avvio, uscita, 160×48 e 80×24, ricerca,
filtri e significato del fallback. Non condividere l'output live `--json` senza
controllare nomi, utenti e percorsi. Per il replay usare solo file sintetici o una
acquisizione esplicitamente scelta dall'utente; `--open file.rtm.json` deve restare
offline e `r` non deve avviare rilevazioni sul PID salvato.

## Limiti ancora da verificare su Mac

- Questo probe non verifica la lettura di un **processo figlio** né il diniego su un
  processo protetto: non ottiene task port esterne. Occorrerà una prova separata con
  un figlio di test avviato e controllato esplicitamente, e una prova di errore
  autorizzata, senza forzare privilegi. Se il sistema rifiuta l'accesso, registrare
  codice e contesto come limite, non tentare di aggirarlo.
- La corrispondenza di resident, private, compressed, reusable e footprint con le
  metriche di ramtaskman è da verificare con fonti Apple e strumenti equivalenti;
  PSS non deve essere stimata da ref_count.
- L'accesso ai task esterni, le differenze fra versioni e architetture, submap e
  stabilità sotto cancellazione richiedono test nativi prima del provider macOS.
- I test `test_verify_macos_probe.py` controllano wrapper e flusso C con header
  **simulati su Linux**. Non dimostrano compilazione SDK, ABI o misurazioni macOS.

Riferimenti: [strutture delle regioni Mach, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/vm_region.h),
[interfacce mach_vm, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/mach_vm.defs),
[codici kern_return, XNU](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/kern_return.h).
