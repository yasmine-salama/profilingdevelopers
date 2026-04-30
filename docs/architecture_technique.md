# Architecture technique detaillee

## 1. Vue d'ensemble
L'application suit une architecture modulaire organisee autour de trois blocs principaux :
- un module de collecte et de preparation des donnees,
- un backend Flask expose sous forme d'application web,
- une couche de stockage et de visualisation.

Le projet adopte une logique ETL afin de separer clairement les responsabilites entre acquisition, transformation, chargement et exploitation.

## 2. Architecture logique
### 2.1 Couche Extract
Cette couche recupere les donnees depuis des sources externes ou locales.

Composants prevus :
- connecteurs API,
- connecteurs de scraping,
- lecteur de fichiers locaux CSV ou JSON.

Dans la version initiale, un jeu de donnees local est utilise afin de permettre les tests et la demonstration de l'application. Un connecteur GitHub API permet egalement d'importer un profil reel a partir d'un nom d'utilisateur ainsi que de rechercher plusieurs profils a partir d'un mot-cle.

### 2.2 Couche Transform
Cette couche effectue :
- le nettoyage,
- la suppression des doublons,
- la normalisation des champs,
- l'extraction des technologies,
- le calcul des indicateurs d'activite.

Cette couche repose principalement sur `pandas`.

### 2.3 Couche Load
Cette couche enregistre les donnees transformees dans une base relationnelle.

Tables principales :
- `developers`
- `developer_skills`
- `etl_runs`

SQLite est retenu pour la version initiale pour sa simplicite. La structure restera compatible avec une migration future vers PostgreSQL ou MySQL.

### 2.4 Couche Application
Cette couche est geree par Flask et comprend :
- les routes web,
- l'acces aux services metier,
- la generation des vues HTML,
- l'exposition eventuelle d'une API JSON.

### 2.5 Couche Presentation
Cette couche affiche :
- des indicateurs globaux,
- des graphiques interactifs,
- des tableaux de synthese.

Les vues sont rendues cote serveur avec des templates HTML. Les graphiques interactifs sont produits avec `plotly`.

## 3. Architecture physique du projet
Structure recommandee :

```text
Projet/
|-- app/
|   |-- __init__.py
|   |-- config.py
|   |-- database.py
|   |-- routes.py
|   |-- services/
|   |   |-- etl.py
|   |   |-- analysis.py
|   |-- templates/
|   |   |-- base.html
|   |   |-- index.html
|   |   |-- dashboard.html
|   |-- static/
|       |-- style.css
|-- data/
|   |-- sample_developers.json
|   |-- app.db
|-- docs/
|   |-- cahier_des_charges.md
|   |-- architecture_technique.md
|-- app.py
|-- requirements.txt
|-- README.md
```

## 4. Flux de donnees
### 4.1 Sequence de traitement
1. Lecture des donnees brutes.
2. Nettoyage et normalisation.
3. Extraction des competences.
4. Calcul des indicateurs d'activite.
5. Chargement dans la base.
6. Lecture des donnees consolidees pour affichage.

### 4.2 Exemple de pipeline
- Source brute : CSV ou source web.
- Transformation : `pandas` et fonctions Python.
- Chargement : insertion SQL dans SQLite.
- Consommation : Flask lit les donnees agregees et les affiche.

### 4.3 Flux GitHub multi-profils
1. L'utilisateur saisit une requete et un nombre maximal de resultats dans le dashboard.
2. Flask appelle `search_github_users()` dans `app/services/github_api.py`.
3. Le service interroge `search/users`, puis enrichit chaque resultat avec `users/{username}`.
4. Les resultats sont rendus dans `dashboard.html` avec cases a cocher et metadonnees.
5. L'utilisateur soumet une selection de profils vers `import_github_developers()`.
6. Le service ETL normalise les enregistrements, supprime les doublons et charge la base SQLite.
7. Le dashboard recharge ensuite les indicateurs, tableaux et graphiques a partir des donnees consolidees.

## 5. Modele de donnees
### 5.1 Table developers
- `id`
- `username`
- `source`
- `profile_url`
- `bio`
- `location`
- `repositories`
- `commits`
- `activity_score`
- `created_at`

### 5.2 Table developer_skills
- `id`
- `developer_id`
- `skill_name`
- `skill_score`

### 5.3 Table etl_runs
- `id`
- `run_date`
- `source_name`
- `records_loaded`
- `status`

## 6. Modules applicatifs
### 6.1 Module de chargement des donnees
Responsabilites :
- lire le jeu de donnees brut,
- transformer les lignes en enregistrements propres,
- charger les donnees dans la base.

Implementation actuelle :
- `app/services/etl.py`
- `app/services/github_api.py`
- `app/routes.py`

### 6.2 Module d'analyse
Responsabilites :
- calculer les totaux globaux,
- extraire les top technologies,
- produire les donnees necessaires aux graphiques.

Implementation actuelle :
- `app/services/analysis.py`

### 6.3 Module de visualisation
Responsabilites :
- generer les graphiques Plotly,
- preparer le HTML integre aux pages.
- afficher les resultats de recherche GitHub et les actions d'import en lot.

Implementation actuelle :
- `app/templates/dashboard.html`
- `app/static/style.css`

## 7. Extensibilite
L'architecture est prevue pour accueillir :
- de nouvelles sources de donnees,
- une API REST plus complete,
- des modules de machine learning,
- un moteur d'authentification,
- une separation frontend/backend si necessaire.

## 8. Integration du machine learning
Des traitements complementaires pourront etre ajoutes :
- classification de profils,
- clustering de developpeurs similaires,
- prediction d'activite,
- detection automatique de profils fortement specialises.

Ces traitements s'appuieront sur les donnees consolidees produites par la chaine ETL.

## 9. Securite et bonnes pratiques
- Validation des entrees.
- Gestion des erreurs de collecte.
- Respect des conditions d'utilisation des sources.
- Journalisation des executions ETL.
- Isolation de la configuration dans un module dedie.

## 10. Strategie de deploiement
### 10.1 En environnement local
- Execution avec Flask.
- Base SQLite locale.

### 10.2 En production
- WSGI via Gunicorn ou equivalent.
- Reverse proxy Nginx.
- Base PostgreSQL.
- Variables d'environnement pour la configuration.
