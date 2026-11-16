# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Sehen, wohin der Arbeitsspeicher geht – direkt im Terminal.

ramtaskman ist ein experimenteller Speichermonitor für Linux, Windows und macOS. Aus Neugier und Forschung entstanden, hilft er beim Verständnis des Speichers auf verschiedenen Systemen, ohne komplizierte Werkzeuge zu benötigen. Ein Vibeware-Projekt.

![ramtaskman](../images/overview.png)

*Echte Textual-Oberfläche unter Linux, aufgenommen mit synthetischen Beispieldaten. Die Bilder zeigen derzeit die italienische Oberfläche.*


![Multilingual dashboard](../images/multilingual.png)

*Teilweise übersetzte Übersicht in sechs Sprachen; unter Linux mit synthetischen Daten aufgenommen.*

## Funktionen

1. RAM, verfügbaren Speicher, Cache und Verlauf überblicken; zwischen Slim und vollständiger Diagnose wählen.
2. Anwendungen und Prozesse untersuchen, verfügbare Messwerte sortieren und die Abdeckung prüfen.
3. RSS und USS ansehen; unter Linux zusätzlich PSS, Swap und SwapPSS mit Details und fehlenden Werten.
4. Nach Name, ausführbarer Datei oder exakter PID suchen und nach Benutzer, Swap oder unvollständigen Daten filtern.
5. Speicherbereiche unter Linux erkunden; die Windows-Ansicht virtueller Adressen ist experimentell.
6. Zwei Aufnahmen vergleichen und lokal speichern oder auch offline öffnen.

## Einblicke

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

## Starten

Benötigt werden Python 3.11+ und uv. Linux benötigt /proc und smaps_rollup. Beim ersten Start werden die festgelegten Abhängigkeiten über das Netzwerk installiert. Umgebung und Cache bleiben im Projektordner.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

Unter Windows im Projektordner mit Windows Terminal:

```powershell
.\run.cmd
```

--once liefert eine einzelne Messung, --json eine JSON-Ausgabe. .venv nicht zwischen Betriebssystemen teilen, sondern lokal neu erstellen. Das Projekt ist nicht auf PyPI veröffentlicht.

Tasten: m wechselt den Modus, g Anwendungen/Prozesse, / sucht, f filtert, d zeigt Details, r öffnet Bereiche, ? erklärt die Werte und q beendet. Die vollständige technische Anleitung ist derzeit auf Italienisch.

Die Übersicht startet mit `./run.sh --language de` (Windows: `.\run.cmd --language de`). Die Übersetzung ist unvollständig: detaillierte Erklärungen, Bereiche, Fehler und einige Bedienelemente bleiben italienisch oder englisch.

## Experimentell: Messwerte sorgfältig interpretieren

Messungen erfolgen nacheinander, Berechtigungen können die Sichtbarkeit einschränken und die Anwendungsgruppierung ist heuristisch. Fehlende Daten sind n/a, nicht null. RSS kann gemeinsam genutzte Seiten mehrfach zählen; Prozess-PSS ist nicht der gesamte RAM. Cache überschneidet sich mit verfügbarem Speicher. Prozess-Swap wird nicht aus Commit abgeleitet.

Linux liefert PSS und Prozess-Swap, sofern lesbar. Unter Windows und macOS werden sie hier nicht bereitgestellt. Linux-Bereiche nutzen smaps; Windows zeigt experimentelle virtuelle Bereiche; macOS hat noch keine Bereichsansicht. Hardware wurde lokal unter Linux geprüft; Windows und macOS benötigen native Validierung.

## Inspiration und Dank

Danke an Scott Hanselman und GPU Taskman für die Inspiration. ramtaskman verwendet Teile des Projekts und passt dessen Terminaloberfläche für RAM an; es ist unabhängig und keine offizielle Veröffentlichung. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Übersetzungen mit KI-Unterstützung erstellt. Korrekturen durch Übersetzer und Muttersprachler sind willkommen.

[Vollständige technische Anleitung (Italienisch)](../guida.md) · [MIT-Lizenz; ursprüngliches Copyright bleibt erhalten.](../../LICENSE)
