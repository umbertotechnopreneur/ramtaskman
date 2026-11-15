# Lezioni verificate

## Memoria non leggibile non significa zero

La scansione locale senza elevazione ha rilevato molti processi senza accesso a smaps_rollup.
La UI deve mantenere n/a e mostrare la copertura. Un totale di gruppo con un membro mancante
non è un totale completo: il test `test_incomplete_group_does_not_claim_complete_total` lo verifica.

## Cache e disponibile si sovrappongono

MemAvailable include memoria recuperabile. Nella barra per categorie OS non è un segmento:
si usa MemFree per la RAM libera e Cached − Shmem per separare cache dei file e shmem.
Slab non va sommato ai suoi figli SReclaimable/SUnreclaim. La somma delle categorie più il
residuo deve coincidere con MemTotal; campioni incoerenti hanno un motivo esplicito e
fallback in uso/disponibile. Verifiche in test_system_segments.py e test_memory.py.

## Windows: commit non significa swap né RAM privata residente

Il sorgente psutil 7.2.2 distingue RSS/working set e USS da private/pagefile/commit.
Il backend Windows usa memory_full_info().uss e lascia PSS/swap per processo a None;
il test test_windows_uss_is_not_commit_and_swap_is_not_pagefile protegge questa distinzione.
Riferimento: documentazione Microsoft PROCESS_MEMORY_COUNTERS_EX, collegata dal README.

## Una ricerca su un helper deve conservare il totale dell’app

Costruire gli aggregati prima di filtrare evita che cercare un PID o un helper trasformi
il suo consumo nel totale apparente dell’applicazione. I filtri selezionano gruppi interi;
nel drilldown selezionano i processi. I test di filters e UI verificano questa distinzione.

## L’identità dell’istanza è più precisa del nome del programma

Un cgroup applicativo systemd esplicito può contenere helper con eseguibili diversi.
Il percorso completo identifica l’istanza; il nome visualizzato può essere uguale a quello
di altre istanze. Non aggregare per la sola etichetta, per l’intera sessione o per UID diverso.
Parser e test in grouping.py/test_grouping.py verificano questi limiti.

## I worker Textual appartengono al manager dell'app

`screen.workers` è il manager globale, non un manager isolato della schermata.
Per chiudere una lettura su richiesta usare `cancel_node(screen)`: `cancel_all()`
interromperebbe anche il monitoraggio principale. Il test di chiusura in
test_region_ui.py verifica che il worker dell'app resti attivo mentre quello delle
regioni riceve l'annullamento. Per dettagli scorrevoli da tastiera usare un
VerticalScroll: rendere focusabile un semplice Static non lo rende scorrevole.
