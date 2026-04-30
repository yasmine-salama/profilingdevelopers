# Cahier des charges

## 1. Contexte
Le projet a pour objectif de concevoir une application web permettant d'analyser des profils de developpeurs a partir de donnees disponibles en ligne. Le systeme doit collecter, nettoyer, structurer, analyser et visualiser ces informations afin de produire une lecture simple et exploitable des competences, des technologies maitrisees et du niveau d'activite.

## 2. Problematique
Les informations relatives aux profils techniques sont souvent dispersees sur plusieurs plateformes et presentees sous des formats heterogenes. Il est donc difficile d'obtenir une vue synthetique et comparable des competences et de l'activite d'un developpeur.

## 3. Objectifs
### 3.1 Objectif general
Mettre en place une application web capable d'extraire, transformer, stocker et visualiser des donnees de profils developpeurs.

### 3.2 Objectifs specifiques
- Collecter des donnees depuis des sources accessibles.
- Nettoyer et normaliser les donnees collectees.
- Stocker les donnees dans une base relationnelle.
- Produire des indicateurs sur les competences et l'activite.
- Afficher les resultats dans des dashboards clairs et interactifs.
- Prevoir une architecture extensible pour des traitements analytiques et du machine learning.

## 4. Perimetre fonctionnel
### 4.1 Fonctionnalites incluses
- Importer ou collecter des donnees de profils.
- Importer un profil GitHub a partir d'un nom d'utilisateur.
- Rechercher plusieurs profils GitHub via l'API GitHub.
- Selectionner plusieurs resultats puis les importer en lot.
- Executer une chaine ETL.
- Detecter les technologies mentionnees ou utilisees.
- Calculer des indicateurs d'activite.
- Consulter un tableau de bord global.
- Consulter une liste de profils structures.

### 4.2 Fonctionnalites evolutives
- Ajout de nouvelles sources de donnees.
- Mise en place d'une authentification.
- Filtres avances sur les dashboards.
- Classification automatique des profils.
- Recommandation ou scoring avance via machine learning.

## 5. Utilisateurs cibles
- Encadrants ou evaluateurs souhaitant analyser plusieurs profils.
- Recruteurs ou analystes voulant comparer des competences techniques.
- Etudiants ou chercheurs realisant une etude exploratoire sur des profils developpeurs.

## 6. Besoins fonctionnels
### 6.1 Collecte
- Le systeme doit pouvoir lire des donnees depuis une source locale ou distante.
- Le systeme doit pouvoir etre adapte a des API ou a du scraping.
- Le systeme doit permettre une recherche multi-profils sur GitHub par mot-cle.
- Le systeme doit permettre la selection de plusieurs profils GitHub avant import.

### 6.2 Transformation
- Le systeme doit supprimer les doublons.
- Le systeme doit gerer les valeurs manquantes.
- Le systeme doit normaliser les noms de technologies.
- Le systeme doit extraire les competences pertinentes.

### 6.3 Stockage
- Le systeme doit enregistrer les profils et les technologies dans une base SQL.
- Le systeme doit conserver une structure de donnees exploitable pour l'analyse.

### 6.4 Analyse
- Le systeme doit fournir un resume du nombre de profils, des technologies dominantes et des niveaux d'activite.
- Le systeme doit calculer des indicateurs simples exploitables dans les dashboards.

### 6.5 Visualisation
- Le systeme doit afficher des graphiques et tableaux de synthese.
- Le systeme doit presenter une interface claire, legere et simple a utiliser.
- Le systeme doit afficher dans le dashboard les resultats de recherche GitHub avant import.

## 7. Besoins non fonctionnels
- Simplicite d'utilisation.
- Architecture modulaire et maintenable.
- Performance suffisante pour un volume de donnees modere.
- Fiabilite du traitement ETL.
- Facilite d'evolution vers des traitements plus avances.

## 8. Contraintes techniques
- Langage principal : Python.
- Framework web : Flask.
- Base de donnees : SQL, avec SQLite pour la premiere version.
- Bibliotheques de traitement : Pandas, NumPy.
- Collecte : Requests, BeautifulSoup.
- Visualisation : Plotly, Matplotlib.
- Interface : HTML, CSS.

## 9. Livrables attendus
- Une application web fonctionnelle.
- Une base de donnees structuree.
- Une documentation technique.
- Un cahier des charges.
- Une architecture technique detaillee.

## 10. Risques et limites
- Variabilite des sources en ligne.
- Restrictions d'acces aux donnees ou aux API.
- Qualite heterogene des donnees collectees.
- Evolution possible des besoins pendant le projet.

## 11. Perspectives
- Ajout d'autres connecteurs de donnees.
- Enrichissement des tableaux de bord.
- Integration d'algorithmes de clustering, classification ou scoring.
- Deploiement sur une infrastructure cloud.
