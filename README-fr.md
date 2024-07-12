# Visual TOM JobAsCode
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE.md)&nbsp;
[![fr](https://img.shields.io/badge/lang-en-red.svg)](README.md)  

Ce dépôt fournit un ensemble d'outils permettant la mise en place de "JobAsCode" avec Visual TOM.
Pour rappel, la réflexion "JobAsCode" considère les Traitements et objets liés comme du code et suivant donc un workflow avec un gestionnaire de versions.

Les outils proposés couvrent 2 notions:
  * La génération du code à partir d'un référentiel Visual TOM existant (extraction au format JSON de l'ensemble des objets)
  * La mise à jour du référentiel Visual TOM lors d'un commit

# Disclaimer
Aucun support ni garanties ne seront fournis par Absyss SAS pour ce projet et fichiers associés. L'utilisation est à vos propres risques.

Absyss SAS ne peut être tenu responsable des dommages causés par l'utilisation d'un des fichiers mis à disposition dans ce dépôt Github.

Il est possible de faire appel à des jours de consulting pour l'implémentation.

# Prérequis

  * Visual TOM 7.1 or supérieur

Pour l'extraction du référentiel au format JSON :
  * Python 3

Pour la mise à jour du référentiel après un commit :
  * Github Actions
  * Flux ouvert entre Github et le serveur d'API Visual TOM

# Consignes
Les 2 parties sont liées au JobAsCode mais peuvent être utilisées/mises en place indépendamment.

## Extraction du référentiel au format JSON
Lorsque le référentiel est déjà existant dans Visual TOM, il est possible de l'extraire au format JSON afin de le stocker dans un gestionnaire de version.
  * Créer un jeton d'API à partir de l'interface Visual TOM avec une stratégie ayant les droits "Get"
  * Renseigner le fichier config.py :
    * `FQDN_HOSTNAME` : nom du serveur avec le port du serveur d'API
    * `API_KEY` : clé d'API créée précédemment
    * `VERIFY_SSL` : Active ou non la vérification du certificat HTTPS (par défaut, le certificat est auto-signé donc non valide)
    * `ROOT_PATH` : chemin où seront stockés les fichiers extraits
  * Lancer le script
  ```python3 exportAsCode.py```
A la fin de l'exécution, une synthèse affiche les potentielles erreurs rencontrées.
L'architecture du répertoire reprend celle des URL des API : typeObjet/nomObjet/typeSousObjet/nomSousObjet

Le script ne supprime pas les fichiers présents dans le répertoire de sortie avant de générer les nouveaux fichiers. Cela signifie que si des objets ont été supprimés du référentiel Visual TOM, alors les fichiers seront toujours présents. En fonction des besoins, il pourra être nécessaire d'ajouter une étape préliminaire pour vider le répertoire.

### Limites
* En cas de mise à jour manuelle dans le référentiel et de modifications dans l'outil de versionning, des conflits peuvent apparaitre entre les dépôts locaux.

## Mise à jour du référentiel après un commit
Lorsque le référentiel est intégré à un outil de gestion de versions, la mise à jour du référentiel peut être automatisée en fonction des mises à jour de code.
Les étapes ci-après fonctionnent pour Github mais le raisonnement restera le même avec d'autres outils de versionning dès qu'ils supportent des "actions sur événement".
* Créer un jeton d'API à partir de l'interface Visual TOM avec une stratégie ayant les droits "Post", "Put" et "Delete" sur les objets versionnés
* Créer une variable `VTOM_SERVER_NAME` dans le dépôt Github (Settings / Secrets and variables / Actions / Variables / New repository variable) dont la valeur est le nom du serveur Visual TOM avec le port
* Créer un secret `VTOM_TOKEN` dans le dépôt Github (Settings / Secrets and variables / Actions / Secrets / New repository secret) dont la valeur est le jeton d'API
* Déposer le fichier YAML `vtom-jobascode.yml` dans un répertoire `.github/workflows`

A partir de ce moment, toute action effectuée sur le dépôt entrainera l'exécution d'une action pour mettre à jour le référentiel (à part les changements effectués dans le répertoire .github/workflows).

### Exécution de l'action de mise à jour du référentiel
Une fois que vous avez configuré les étapes précédentes, vous pouvez exécuter l'action de mise à jour du référentiel en effectuant les actions suivantes :

1. Effectuez un commit sur le dépôt contenant les modifications de code.
2. L'action de mise à jour du référentiel sera automatiquement déclenchée (création, modification et/ou suppression).
3. L'action récupérera les fichiers modifiés depuis le référentiel et les enverra au serveur Visual TOM en utilisant l'API.
4. Le référentiel Visual TOM sera mis à jour avec les modifications de code.

Assurez-vous de vérifier les résultats de l'action pour vous assurer que la mise à jour du référentiel s'est déroulée correctement.

### Limites
* Les fichiers JSON doivent respecter la structure attendue par le serveur d'API
* Seuls les objets "Domain" sont pris en compte
* Les contraintes d'ordre entre les objets ne sont pas prises en compte (exemple: Agents avant Unités de soumission)

# Licence
Ce projet est sous licence Apache 2.0. Voir le fichier [LICENCE](license) pour plus de détails.


# Code de conduite
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.1%20adopted-ff69b4.svg)](code-of-conduct.md)  
Absyss SAS a adopté le [Contributor Covenant](CODE_OF_CONDUCT.md) en tant que Code de Conduite et s'attend à ce que les participants au projet y adhère également. Merci de lire [document complet](CODE_OF_CONDUCT.md) pour comprendre les actions qui seront ou ne seront pas tolérées.
