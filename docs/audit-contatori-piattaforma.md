# Audit dei contatori e del raggruppamento

Stato al 16 novembre 2026: analisi del sorgente psutil 7.2.2 bloccato in `uv.lock`,
eseguita su Linux; **non è una prova di funzionamento su Windows o macOS**.

| Voce | Windows, backend psutil corrente | macOS, backend psutil corrente |
|---|---|---|
| Totale/disponibile | `virtual_memory()` usa memoria fisica totale/disponibile; free coincide con available. | `virtual_memory()` usa available = inactive + free, secondo il sorgente psutil. |
| RSS | Working set esposto da `memory_info()`. | RSS esposto da `memory_info()`. |
| USS | `memory_full_info()` interroga il contatore nativo psutil della memoria privata residente. | `memory_full_info()` usa il contatore nativo psutil della memoria privata. |
| PSS | Non esposta da questo backend. | Non esposta da questo backend. |
| Swap per processo | Non esposta; pagefile/private commit non viene usato come swap su disco. | Non esposta da questo backend. |
| Swap globale | psutil combina commit limit, RAM fisica e performance counter pagefile; è un indicatore psutil, non il commit di un processo né un conteggio diretto di ogni pagina su disco. | psutil usa `swap_mem()`; la semantica effettiva va confrontata su Mac reale. |
| Partizione globale | Fallback in uso/disponibile. | Fallback in uso/disponibile. |
| App | Fallback account + eseguibile/nome. | Fallback UID + eseguibile/nome. |

Riferimenti primari: [sorgente psutil Windows](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/_pswindows.py),
[sorgente psutil macOS](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/_psosx.py),
[documentazione PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex).
Il sorgente installato e il lockfile sono il riferimento per la versione effettiva in uso;
controllare i risultati sui sistemi nativi con le procedure di verifica collegate dal README.

L'identità per nome o eseguibile è un'euristica: un interprete o launcher condiviso può
raggruppare programmi distinti. Un bundle ID o package ID può descrivere il prodotto,
ma non dimostra da solo l'identità di un'istanza e dei suoi helper. Finché non sono
stati verificati metadati affidabili e i casi a più utenti/istanze su hardware reale,
manteniamo il fallback dichiarato e non aggiungiamo aggregazioni speculative.

Non usare i campi di queste colonne come partizioni disgiunte senza dimostrare che
abbiano lo stesso dominio e non si sovrappongano. Le prove native e un confronto con
contatori equivalenti restano necessarie prima di rivendicare la parità tra piattaforme.
