# ramtaskman · comprendre les chiffres

La structure visuelle de gputaskman, adaptée à la mémoire de Linux, Windows et macOS.

| Champ | Signification |
|---|---|
| PSS | RAM privée plus une part proportionnelle des pages partagées |
| USS | Private_Clean + Private_Dirty : pages résidentes privées |
| RSS | Pages résidentes, y compris partagées ; les additionner peut les compter plusieurs fois |
| Swap | Swap de smaps_rollup, hors swap shmem ; des pages partagées peuvent être comptées plusieurs fois |
| SwapPSS | Part proportionnelle du swap partagé comptabilisé par smaps_rollup |
| RAM used | MemTotal − MemAvailable ; ce n'est pas la somme des processus |
| Cache | Cached + Buffers + SReclaimable − Shmem ; recouvre en partie la mémoire disponible |
| PSI some | Pourcentage de temps avec au moins une tâche en attente de mémoire, moyenne sur 10 s |

**Barre RAM :** occupe toute la largeur et répartit les compteurs Linux en mémoire anonyme, cache de fichiers (Cached − Shmem), mémoire partagée/tmpfs, tampons, slab récupérable/non récupérable, autre (résidu calculé) et mémoire libre. Ce sont des catégories comptables ; leur ordre ne représente pas des adresses physiques. La mémoire disponible est un indicateur distinct comprenant du cache récupérable : elle n'est donc pas un segment supplémentaire. Les détails clean/dirty et PSS des processus restent dans **d**, car ils recouvrent les compteurs globaux. S'il manque des champs ou si l'échantillon est incohérent, la barre affiche utilisée/disponible et explique l'absence de répartition. La légende inclut les catégories plus petites qu'un caractère.

**Barre USS des applis :** les 10 premières applis avec USS complète et les autres applis complètes. L'échelle est la somme USS des seules applis complètes de l'échantillon, pas la RAM totale. Numéros et couleurs renvoient à la légende. Les groupes partiels sont exclus et la couverture est indiquée. Le regroupement suit le tableau ; les segments ne sont pas des adresses physiques.

**Windows/macOS :** USS et RSS proviennent de psutil ; PSS, Swap et SwapPSS par processus ne sont pas exposés et restent n/a. Le commit privé/pagefile Windows n'est PAS du swap sur disque. Sous macOS, RAM used est total − available de psutil, pas la pression mémoire d'Activity Monitor.

**Application :** sous Linux, un cgroup systemd explicite identifie l'instance d'une appli, même avec des assistants aux exécutables différents. Utilisateurs et instances distincts restent séparés. Sans cette identité, y compris sous Windows/macOS, le regroupement utilise utilisateur + exécutable, ou utilisateur + nom comme heuristique si le chemin est illisible. L'inspecteur indique la méthode.

**Recherche et filtres :** **/** recherche un nom, un exécutable ou un PID exact ; **f** choisit utilisateur et état mémoire (**avec swap** ou **données partielles**). Les filtres se combinent. Une appli correspond si l'un de ses processus satisfait la recherche ou l'état mémoire, mais le total conserve tous ses membres. Les filtres restent en vue processus. Ils s'appliquent avant Top 30 ; graphiques et tableau de bord décrivent tout le système. **Entrée** depuis la recherche revient au tableau. **Échap** dans les contrôles ou **Reset** efface les filtres ; **Échap** dans le tableau des processus revient aux applis en les conservant. Données partielles ne considère que les compteurs pris en charge ; un swap inconnu ne signifie pas un swap utilisé.

**d** ouvre le détail RAM du groupe ou du processus : PSS anonyme/fichier/shmem, privée et partagée clean/dirty, pages anonymes, LazyFree et THP. Champs Linux uniquement : ailleurs n/a. Ces lignes sont des vues qui se recouvrent ; ne pas toutes les additionner. Le détail fixe l'échantillon à l'ouverture : fermer puis rouvrir pour actualiser. **Échap** ou **d** ferme le détail.

**r** ou **Entrée** sur un processus ouvre la carte des régions Linux. Sur une appli, **r** montre d'abord les PID : chaque processus possède son propre espace virtuel. Les barres de **d** répartissent PSS et RSS séparément ; le swap reste hors de la RAM résidente.

Dans la carte : **v** alterne RSS/adresses virtuelles, **s** trie, **/** recherche un fichier ou une adresse 0x…, **f** filtre type/état, **z** ou **Entrée** zoome sur le voisinage de la région sélectionnée, **r** actualise, **Échap** efface les filtres/quitte le zoom/revient en arrière. La carte suit les adresses virtuelles, pas les cadres physiques. Les lacunes sont exclues de l'échelle virtuelle et marquées par │ ; les régions de moins d'un caractère restent dans le tableau. Le type indique l'origine, pas le contenu : un fichier peut contenir des pages CoW privées ; seuls les tas/piles reconnus sont étiquetés ainsi. Les échantillons sont à la demande, avec âge, durée et limites de lecture. Windows : plages virtuelles expérimentales seulement ; macOS : pas de carte des régions.

Dans les régions, **b** fixe A, **r** collecte B et **c** ouvre la comparaison. En comparaison, **v** change de métrique, **s** d'ordre, **f** filtre l'état et **Ctrl+B** supprime A. **Ctrl+S** enregistre les échantillons, **Ctrl+O** ouvre un fichier hors ligne. Les fichiers contiennent des métadonnées et peuvent inclure des chemins personnels. Données manquantes et régions réorganisées restent n/a ; un même intervalle ne prouve ni la même allocation ni une fuite mémoire.

**n/a n'est pas zéro.** Le total d'une appli est n/a dès qu'une valeur manque. Lectures indique la couverture PSS/USS. Les totaux visibles du tableau de bord sont des sommes partielles des lectures disponibles et ne représentent pas toute la RAM du système. Les lectures ne sont pas atomiques : les processus peuvent changer pendant l'échantillonnage. Autres utilisateurs, bacs à sable et permissions procfs peuvent bloquer les lectures. Aucune élévation automatique. HugeTLB est exclu des compteurs RSS/PSS/USS ordinaires affichés ici.

Le programme lit des métadonnées, pas /proc/PID/mem, cmdline, environment ou le contenu des applis.

**g** applis/processus · **Entrée** processus de l'appli choisie · **Échap** retour aux applis

**s** tri · **c** graphique · **a** tous/30 premiers · **m** compact/complet

**/** recherche · **f** filtres · **d** détails · **r** régions · **p** pause · **?** aide · **q** quitter

Graphiques : 60 derniers échantillons, pourcentages sur une échelle 0–100. Le vide indique une donnée absente. L'intervalle est une pause après la mesure ; la durée réelle inclut aussi l'analyse.
