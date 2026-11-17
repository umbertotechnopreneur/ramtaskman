# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Sehen, wohin der Arbeitsspeicher geht – direkt im Terminal.

ramtaskman ist ein experimenteller Speichermonitor, der unter Linux und Windows entwickelt und getestet wird. Aus Neugier und Forschung entstanden, hilft er beim Verständnis des Speichers auf verschiedenen Systemen, ohne komplizierte Werkzeuge zu benötigen. Ein [VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto)-Projekt.

Es gibt auch ein experimentelles macOS-Backend. Da wir keinen Mac haben, haben wir es weder getestet noch validiert. Unsere Tests und die CI laufen unter Linux und Windows.

[Dokumentation](../README.md) · [Mitwirken](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Echte Textual-Oberfläche unter Linux mit synthetischen Daten. Das Titelbild zeigt einen Ausschnitt von Übersicht und Tabelle; die gezeigte Oberfläche ist englisch.*

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

Tasten: m wechselt den Modus, g Anwendungen/Prozesse, / sucht, f filtert, d zeigt Details, r öffnet Bereiche, ? erklärt die Werte und q beendet. Die vollständige technische Anleitung ist derzeit auf Englisch.

Die Übersicht startet mit `./run.sh --language de` (Windows: `.\run.cmd --language de`). Die Anwendungstexte sind in zehn Sprachen verfügbar: `--language` wählt die Sprache für Oberfläche, Fußzeile, Hilfe, CLI und den Textbericht `--once`. Auch technische Meldungen der Anwendung werden übersetzt. Kennungen und JSON-Schema bleiben stabil; Betriebssystemdetails und Texte aus gespeicherten Aufnahmen behalten ihre ursprüngliche Sprache. Die lokale Überprüfung umfasst Linux mit Python 3.14.4: synthetische Oberfläche mit 160×48 und 80×24, CLI, Paketbau, isolierte Installation und Replay. Windows wird in der CI geprüft; macOS ist von den Projektprüfungen ausgenommen. Eine muttersprachliche Prüfung der Übersetzungen steht weiterhin aus.

## Funktionen

1. RAM, verfügbaren Speicher, Cache und Verlauf überblicken; zwischen Slim und vollständiger Diagnose wählen.
2. Anwendungen und Prozesse untersuchen, verfügbare Messwerte sortieren und die Abdeckung prüfen.
3. RSS und USS ansehen; unter Linux zusätzlich PSS, Swap und SwapPSS mit Details und fehlenden Werten.
4. Nach Name, ausführbarer Datei oder exakter PID suchen und nach Benutzer, Swap oder unvollständigen Daten filtern.
5. Speicherbereiche unter Linux erkunden; die Windows-Ansicht virtueller Adressen ist experimentell.
6. Zwei Aufnahmen vergleichen und lokal speichern oder auch offline öffnen.

## Einblicke

![Full diagnostics](../images/full-diagnostics.png)

[Galerie](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## RAM-Wert und monatliche Aufteilung

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

Gib den Preis des gesamten RAM selbst ein; es gibt keine Preisabfrage oder Netzwerkanfrage. Standardmäßig gilt die vom Betriebssystem sichtbare Kapazität; `--ram-capacity-gib 32` steht für ein Kit mit nominell 32 GiB. Wert = Preis × zuordenbare Bytes / Kapazität. `--ram-months` verteilt diesen Hardwarewert auf die gewählten Monate: keine Rechnung, kein Energieverbrauch, kein Monatsdurchschnitt und keine garantierte Ersparnis. Linux verwendet PSS, Windows USS, also nur privaten residenten Speicher. Kein Ersatz durch RSS. Unvollständige Gruppen bleiben n/a (`null` in JSON). Anwendungen nicht mit ihren Prozessen oder dem Systemspeicher addieren. Die Messungen erfolgen nacheinander, nicht atomar. JSON enthält `ram_valuation` nur auf Anforderung. F1 öffnet Informationen und Danksagungen; Esc kehrt zur Überwachung zurück.

## Experimentell: Messwerte sorgfältig interpretieren

Messungen erfolgen nacheinander, Berechtigungen können die Sichtbarkeit einschränken und die Anwendungsgruppierung ist heuristisch. Fehlende Daten sind n/a, nicht null. RSS kann gemeinsam genutzte Seiten mehrfach zählen; Prozess-PSS ist nicht der gesamte RAM. Cache überschneidet sich mit verfügbarem Speicher. Prozess-Swap wird nicht aus Commit abgeleitet.

Linux liefert PSS und Prozess-Swap, sofern lesbar. Unter Windows und im experimentellen macOS-Backend werden sie hier nicht bereitgestellt. Linux-Bereiche nutzen smaps; Windows zeigt experimentelle virtuelle Bereiche; macOS hat noch keine Bereichsansicht. Die Projektprüfungen umfassen lokale Linux-Prüfungen und native Windows-CI-Prüfungen; macOS bleibt außerhalb dieses Umfangs.

Die manuelle Prüfung auf einem persönlichen Windows-PC steht noch aus.

## Nutzen, ändern, weitergeben

Du darfst ramtaskman unter der [MIT-Lizenz](../../LICENSE) nutzen, kopieren, ändern und weitergeben, auch kommerziell. Bewahre Copyright- und Erlaubnishinweis in Kopien oder wesentlichen Teilen auf. Die Software wird ohne Gewährleistung bereitgestellt. Beiträge und Übersetzungskorrekturen sind willkommen; Abhängigkeiten behalten ihre eigenen Lizenzen.

[Mitwirken](../../CONTRIBUTING.md) · [Drittanbieterhinweise](../../THIRD_PARTY_NOTICES.md)

## Inspiration und Dank

Danke an Scott Hanselman und GPU Taskman für die Inspiration. ramtaskman verwendet Teile des Projekts und passt dessen Terminaloberfläche für RAM an; es ist unabhängig und keine offizielle Veröffentlichung. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Übersetzungen mit KI-Unterstützung erstellt. Korrekturen durch Übersetzer und Muttersprachler sind willkommen.

[Vollständige technische Anleitung (Englisch)](../guida.md) · [MIT-Lizenz; ursprüngliches Copyright bleibt erhalten.](../../LICENSE)
