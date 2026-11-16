# ramtaskman · die Zahlen verstehen

Die visuelle Struktur von gputaskman, angepasst an den Speicher von Linux, Windows und macOS.

| Feld | Bedeutung |
|---|---|
| PSS | Privater RAM plus anteilige gemeinsam genutzte Seiten |
| USS | Private_Clean + Private_Dirty: private residente Seiten |
| RSS | Residente Seiten einschließlich gemeinsam genutzter Seiten; Summieren kann mehrfach zählen |
| Swap | Swap aus smaps_rollup ohne shmem-Swap; gemeinsam genutzte Seiten können mehrfach gezählt werden |
| SwapPSS | Anteiliger gemeinsam genutzter Swap, den smaps_rollup erfasst |
| RAM used | MemTotal − MemAvailable; entspricht nicht der Summe der Prozesse |
| Cache | Cached + Buffers + SReclaimable − Shmem; überschneidet sich mit verfügbarem Speicher |
| PSI some | Zeitanteil mit mindestens einer auf Speicher wartenden Aufgabe, über 10 s gemittelt |

**RAM-Balken:** nutzt die ganze Breite und teilt Linux-Zähler in anonymen Speicher, Dateicache (Cached − Shmem), geteilt/tmpfs, Puffer, rückgewinnbaren/nicht rückgewinnbaren Slab, Sonstiges (berechneter Rest) und freien Speicher. Dies sind Bilanzkategorien; ihre Reihenfolge stellt keine physischen Adressen dar. Verfügbarer Speicher ist ein eigener Indikator und enthält rückgewinnbaren Cache, also kein zusätzliches Segment. Prozessdetails zu clean/dirty und PSS stehen unter **d**, da sie globale Zähler überlappen. Fehlen Felder oder ist die Messung inkonsistent, zeigt der Balken belegt/verfügbar und erklärt die fehlende Aufteilung. Die Legende enthält auch Kategorien unter einer Zeichenbreite.

**App-USS-Balken:** die zehn größten Apps mit vollständigem USS und die übrigen vollständigen Apps. Die Skala ist die USS-Summe nur dieser vollständigen Apps, nicht der gesamte RAM. Zahlen und Farben verweisen auf die Legende. Unvollständige Gruppen werden ausgeschlossen; die Abdeckung wird angegeben. Gruppierung wie in der Tabelle; Segmente sind keine physischen Adressen.

**Windows/macOS:** USS und RSS stammen aus psutil; PSS, Swap und SwapPSS je Prozess werden nicht bereitgestellt und bleiben n/a. Privater Commit/Pagefile unter Windows ist KEIN Swap auf der Festplatte. Unter macOS ist RAM used psutils total − available, nicht der Speicherdruck der Aktivitätsanzeige.

**Anwendung:** unter Linux identifiziert eine explizite systemd-cgroup die App-Instanz, auch mit Hilfsprozessen unterschiedlicher Programme. Verschiedene Benutzer und Instanzen bleiben getrennt. Ohne diese Identität, auch unter Windows/macOS, wird Benutzer + Programm verwendet oder Benutzer + Name als Heuristik, wenn der Pfad nicht lesbar ist. Der Inspektor nennt das Verfahren.

**Suche und Filter:** **/** sucht nach Name, Programm oder exakter PID; **f** wählt Benutzer und Speicherzustand (**mit Swap** oder **unvollständige Daten**). Filter lassen sich kombinieren. Eine App passt, wenn ein Prozess Suchbegriff oder Speicherzustand erfüllt; ihre Summe behält alle Mitglieder. Filter bleiben beim Wechsel zur Prozessansicht erhalten. Sie wirken vor Top 30; Diagramme und Übersicht beschreiben das gesamte System. **Enter** aus der Suche kehrt zur Tabelle zurück. **Esc** in den Steuerelementen oder **Reset** löscht Filter; **Esc** in der Prozesstabelle kehrt mit erhaltenen Filtern zu Apps zurück. Unvollständige Daten berücksichtigt nur unterstützte Zähler; unbekannter Swap bedeutet nicht verwendeten Swap.

**d** öffnet RAM-Details der Gruppe oder des Prozesses: anonymer/Datei/shmem-PSS, privat und geteilt clean/dirty, anonyme Seiten, LazyFree und THP. Nur Linux-Felder, sonst n/a. Die Zeilen überlappen sich und dürfen nicht alle addiert werden. Die Messung wird beim Öffnen fixiert; zum Aktualisieren schließen und neu öffnen. **Esc** oder **d** schließt die Details.

**r** oder **Enter** auf einem Prozess öffnet die Linux-Bereichskarte. Bei einer App zeigt **r** zunächst die PIDs: jeder Prozess hat seinen eigenen virtuellen Raum. Die Balken unter **d** teilen PSS und RSS getrennt auf; Swap gehört nicht zum residenten RAM.

In der Karte: **v** wechselt RSS/virtuelle Adressen, **s** sortiert, **/** sucht Dateien oder Adresse 0x…, **f** filtert Typ/Zustand, **z** oder **Enter** vergrößert die Nachbarschaft der gewählten Region, **r** aktualisiert, **Esc** löscht Filter/verlässt Zoom/geht zurück. Die Karte folgt virtuellen Adressen, nicht physischen Frames. Lücken sind von der virtuellen Skala ausgeschlossen und mit │ markiert; Regionen unter einer Zeichenbreite bleiben in der Tabelle. Der Typ beschreibt die Herkunft, nicht den Inhalt: Dateibereiche können private CoW-Seiten enthalten; nur erkannte Heaps/Stacks werden so benannt. Messungen erfolgen auf Anfrage und zeigen Alter, Dauer und Lesegrenzen. Windows: nur experimentelle virtuelle Bereiche; macOS: keine Bereichskarte.

In Regionen fixiert **b** A, **r** erfasst B, **c** öffnet den Vergleich. Dort wechselt **v** die Metrik, **s** die Reihenfolge, **f** filtert den Zustand und **Ctrl+B** entfernt A. **Ctrl+S** speichert Messungen, **Ctrl+O** öffnet eine Datei offline. Dateien enthalten Metadaten und möglicherweise persönliche Pfade. Fehlende Daten und umstrukturierte Bereiche bleiben n/a; dasselbe Intervall beweist weder dieselbe Allokation noch ein Speicherleck.

**n/a ist nicht null.** Eine App-Summe ist n/a, sobald ein Wert fehlt. Messungen zeigt PSS/USS-Abdeckung. Sichtbare Summen sind Teilsummen verfügbarer Messwerte, nicht der gesamte System-RAM. Messungen sind nicht atomar: Prozesse können sich währenddessen ändern. Andere Benutzer, Sandboxes und procfs-Rechte können Zugriffe verhindern. Keine automatische Rechteerhöhung. HugeTLB ist in den hier gezeigten gewöhnlichen RSS/PSS/USS-Zählern nicht enthalten.

Das Programm liest Metadaten, nicht /proc/PID/mem, cmdline, environment oder App-Inhalte.

**g** Apps/Prozesse · **Enter** Prozesse der gewählten App · **Esc** zurück zu Apps

**s** Sortierung · **c** Diagramm · **a** alle/erste 30 · **m** kompakt/vollständig

**/** Suche · **f** Filter · **d** Details · **r** Bereiche · **p** Pause · **?** Hilfe · **q** beenden

Diagramme zeigen die letzten 60 Messungen als Prozentwerte von 0–100. Leere Stellen bedeuten fehlende Daten. Das Intervall ist die Pause nach der Messung; die tatsächliche Dauer enthält zusätzlich den Scan.
