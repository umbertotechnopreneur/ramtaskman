# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Comprendre où va la RAM, directement dans le terminal.

ramtaskman est un moniteur de mémoire expérimental développé et testé sous Linux et Windows. Né de la curiosité et de la recherche, il aide à comprendre la mémoire sur plusieurs systèmes sans recourir à des outils compliqués. C’est un projet Vibeware.

Le backend macOS est présent à titre expérimental. Nous ne disposons d’aucun Mac : macOS est donc hors du périmètre de vérification du projet et n’est ni testé ni validé par celui-ci. Des essais externes ne constituent pas une validation officielle ; aucune parité de fonctionnalités avec Linux et Windows n’est promise.

![ramtaskman](../images/overview.png)

*Interface Textual réelle capturée sous Linux avec des données fictives. Les captures montrent actuellement l’interface italienne.*


![Multilingual dashboard](../images/multilingual.png)

*Captures d’un précédent checkpoint de traduction, réalisées sous Linux avec des données fictives. Les textes de l’application, y compris le pied de page, la CLI et les messages techniques propres à l’application, sont désormais disponibles en dix langues.*

## Fonctions principales

1. Visualiser la RAM, la mémoire disponible, le cache et les graphiques ; choisir le mode Slim ou complet.
2. Explorer applications et processus, trier les métriques disponibles et vérifier la couverture des mesures.
3. Consulter RSS et USS ; sous Linux, aussi PSS, swap et SwapPSS, avec les valeurs absentes clairement signalées.
4. Rechercher par nom, exécutable ou PID exact et filtrer par utilisateur, swap ou données partielles.
5. Explorer les régions mémoire sous Linux ; la vue des adresses virtuelles Windows est expérimentale.
6. Comparer deux captures, les enregistrer et les rouvrir localement, même hors ligne.

## En images

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

## Démarrage

Python 3.11+ et uv sont nécessaires. Linux exige /proc et smaps_rollup. Le premier lancement télécharge les dépendances verrouillées. L’environnement et le cache restent dans le projet.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

Sous Windows, dans Windows Terminal et depuis le dossier du projet :

```powershell
.\run.cmd
```

Utilisez --once ou --json pour une mesure unique ou une sortie JSON. Ne partagez pas .venv entre systèmes : recréez-le localement. Le projet n’est pas publié sur PyPI.

Touches utiles : m change de mode, g alterne applications/processus, / recherche, f filtre, d affiche les détails, r ouvre les régions, ? explique les métriques et q quitte. Le guide technique complet est actuellement en italien.

Lancez le tableau de bord avec `./run.sh --language fr` (Windows : `.\run.cmd --language fr`). Les textes de l’application sont disponibles en dix langues : `--language` choisit la langue de l’interface, du pied de page, de l’aide, de la CLI et du rapport textuel `--once`. Les messages techniques produits par l’application sont également traduits. Les identifiants et le schéma JSON restent stables ; les détails du système d’exploitation et les textes des captures enregistrées conservent leur langue d’origine. La vérification locale porte sur Linux avec Python 3.14.4 : interface synthétique en 160×48 et 80×24, CLI, construction des paquets, installation isolée et replay. Les vérifications Windows sont effectuées en CI ; macOS est exclu des vérifications du projet. Les traductions attendent encore une relecture par des locuteurs natifs.

## Expérimental : interpréter les chiffres avec prudence

Les lectures sont séquentielles, les permissions peuvent limiter la visibilité et le regroupement des applications est heuristique. Une donnée absente vaut n/a, pas zéro. RSS peut compter deux fois les pages partagées ; la PSS des processus n’est pas la RAM totale. Le cache chevauche la mémoire disponible. Le swap par processus n’est pas déduit du commit.

Linux fournit PSS et swap par processus lorsque les données sont lisibles. Ils ne sont pas exposés ici sous Windows ni dans le backend macOS expérimental. Les régions Linux utilisent smaps ; celles de Windows sont des plages virtuelles expérimentales ; la carte macOS n’est pas encore disponible. Les vérifications du projet couvrent Linux en local et Windows en CI native ; macOS reste hors de ce périmètre.

## Inspiration et remerciements

Merci à Scott Hanselman et à GPU Taskman pour leur inspiration. ramtaskman réutilise des parties du projet et adapte son interface terminal à la RAM ; il est indépendant et n’est pas une version officielle. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Traductions réalisées avec l’aide de l’IA. Les corrections des traducteurs et locuteurs natifs sont les bienvenues.

[Guide technique complet (italien)](../guida.md) · [Licence MIT ; copyright original conservé.](../../LICENSE)
