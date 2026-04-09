# Visual TOM JobAsCode
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE.md)&nbsp;
[![fr](https://img.shields.io/badge/lang-en-red.svg)](README.md)  

Ce dépôt fournit un ensemble d'outils permettant la mise en place de "JobAsCode" avec Visual TOM.
Pour rappel, la réflexion "JobAsCode" considère les Traitements et objets liés comme du code et suivant donc un workflow avec un gestionnaire de versions.

Les outils proposés permettent :
  * De créer le paramétrage d'interaction avec VTOM et Git
  * La génération du code à partir d'un référentiel Visual TOM existant (extraction au format JSON de l'ensemble des objets)
  * La mise à jour du référentiel Visual TOM

# Disclaimer
Aucun support ni garanties ne seront fournis par Absyss SAS pour ce projet et fichiers associés. L'utilisation est à vos propres risques.

Absyss SAS ne peut être tenu responsable des dommages causés par l'utilisation d'un des fichiers mis à disposition dans ce dépôt Github.

Il est possible de faire appel à des jours de consulting pour l'implémentation.

# Prérequis

  * Visual TOM 7.1 ou supérieur
  * Un serveur VTOM (source ou/et cible)
  * Un dépôt git local (source ou/et cible)
  * (Recommandé) Un dépôt git central (`origin`). Ex: Github, Gitlab, Gitea...

Pour l'extraction du référentiel au format JSON dans un répertoire versionné (Git) :
  * Python 3
  * Git

Pour la mise à jour du référentiel après un commit avec Github :
  * Github Actions
  * Flux ouvert entre Github et le serveur d'API Visual TOM

# Consignes
Les 2 parties sont liées au JobAsCode mais peuvent être utilisées/mises en place indépendamment.

## Validation préparatoire des prérequis
Le script `prepareJobAsCode.py` prépare un seul côté (`source` ou `target`) à la fois:
  * validation du serveur VTOM choisi (API + Swagger/OpenAPI)
  * détection de la version Domain disponible (`/domain/x.y`)
  * préparation du dépôt local (création par clone si absent, initialisation si nécessaire)
  * configuration/alignement du remote central `origin`
  * mise à jour du fichier `config.py` (créé depuis `config.py.template` si absent)
  * fallback sur `config.py` pour `FQDN_HOSTNAME`, `API_KEY`, `GIT_ORIGIN`, `GIT_LOCAL`, `VERIFY_SSL`

Exemple (le script pose les questions en interactif) :
```bash
python3 prepareJobAsCode.py
```

Le rôle (`source`/`target`) et les autres paramètres sont demandés au lancement.
Les valeurs par défaut viennent de `config.py` quand elles sont renseignées.

Mode simulation (aucune écriture locale) :
```bash
python3 prepareJobAsCode.py ... --dry-run
```

Sortie JSON (pour CI) :
```bash
python3 prepareJobAsCode.py ... --output-json
```

Sortie JSON seule (sans logs texte) :
```bash
python3 prepareJobAsCode.py ... --json-only
```

## Extraction du référentiel au format JSON
Lorsque le référentiel est déjà existant dans Visual TOM, il est possible de l'extraire au format JSON afin de le stocker dans un gestionnaire de version.
  * Créer un jeton d'API à partir de l'interface Visual TOM avec une stratégie ayant les droits "Get"
  * Le fichier de configuration config.py est renseigné à l'étape précédente, notamment :
    * `FQDN_HOSTNAME` : nom du serveur avec le port du serveur d'API
    * `API_KEY` : clé d'API créée précédemment
    * `VERIFY_SSL` : Active ou non la vérification du certificat HTTPS (par défaut, le certificat est auto-signé donc non valide)
    * `GIT_LOCAL` : chemin local utilisé pour les fichiers extraits et le dépôt local
  * Lancer le script
  ```python3 exportAsCode.py```
  Par défaut, l'extraction est orientée import et n'exporte pas les fichiers snapshot
  agrégés du graphe (`graph.json`, `nodes.json`), non nécessaires pour `importAsCode.py`.
  Pour les inclure (export graphe complet/historique), utiliser :
  ```bash
  python3 exportAsCode.py --full-graph-snapshots
  ```
A la fin de l'exécution, une synthèse affiche les potentielles erreurs rencontrées.
Le répertoire de sortie (`GIT_LOCAL`) est vidé avant l'extraction (le dossier `.git` est conservé).
L'architecture du répertoire reprend celle des URL des API : typeObjet/nomObjet/typeSousObjet/nomSousObjet

### Limites
* En cas de mise à jour manuelle dans le référentiel et de modifications dans l'outil de versionning, des conflits peuvent apparaitre entre les dépôts locaux.

## Mise à jour du référentiel après un commit
Lorsque le référentiel est intégré à un outil de gestion de versions, la mise à jour du référentiel peut être automatisée en fonction des mises à jour de code.
Les étapes ci-après fonctionnent pour Github, mais le raisonnement reste le même avec d'autres outils de versionning dès qu'ils supportent des "actions sur événement".
* Créer un jeton d'API à partir de l'interface Visual TOM avec une stratégie ayant les droits "Post", "Put" et "Delete" sur les objets versionnés
* Déposer le fichier YAML `vtom-jobascode-github.yml` dans un répertoire `.github/workflows`
* Le workflow appelle `importAsCode.py` pour traiter les fichiers JSON ajoutés/modifiés/supprimés entre 2 commits et exécuter les appels API POST/PUT/DELETE

A partir de ce moment, toute action effectuée sur le dépôt entraîne l'exécution d'une action pour mettre à jour le référentiel (sauf les changements effectués dans le répertoire `.github/workflows`).

### Exécution de l'action de mise à jour du référentiel
Une fois que vous avez configuré les étapes précédentes, vous pouvez exécuter l'action de mise à jour du référentiel en effectuant les actions suivantes :

1. Effectuez un commit sur le dépôt contenant les modifications de code.
2. L'action de mise à jour du référentiel sera automatiquement déclenchée (création, modification et/ou suppression).
3. L'action récupérera les fichiers modifiés depuis le référentiel et les enverra au serveur Visual TOM en utilisant l'API.
4. Le référentiel Visual TOM sera mis à jour avec les modifications de code.

Assurez-vous de vérifier les résultats de l'action pour vous assurer que la mise à jour du référentiel s'est déroulée correctement.

### Exécution manuelle du script d'import
Le script peut aussi être lancé hors Github Actions, par exemple pour tester en local (simulation par défaut):

```bash
python3 importAsCode.py --from <sha-from> --to <sha-to>
```

Exécution réelle (appels API):

```bash
python3 importAsCode.py --from <sha-from> --to <sha-to> --run
```

### Limites
* Les fichiers JSON doivent respecter la structure attendue par le serveur d'API
* Les objets Domain, Graph et Security sont pris en compte selon le type de ressource
* L'ordre des objets est défini dans `config.py` (`IMPORT_ORDER_PREFIXES`)

# Licence
Ce projet est sous licence Apache 2.0. Voir le fichier [LICENCE](license) pour plus de détails.


# Code de conduite
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.1%20adopted-ff69b4.svg)](code-of-conduct.md)  
Absyss SAS a adopté le [Contributor Covenant](CODE_OF_CONDUCT.md) en tant que Code de Conduite et s'attend à ce que les participants au projet y adhère également. Merci de lire [document complet](CODE_OF_CONDUCT.md) pour comprendre les actions qui seront ou ne seront pas tolérées.
