# Démarrage Rapide

## Installation en 3 minutes

```bash
# 1. Tout installer et déployer
make all

# 2. Vérifier que ça fonctionne
make status

# 3. Accéder aux services
# MinIO Console: http://localhost:9001
# API: http://localhost:8000
# UI: http://localhost:8501
# JupyterLab: http://localhost:8888
```

## Credentials

Voir le fichier `.env` :

## Commandes utiles

```bash
make help       # Toutes les commandes
make status     # État du cluster
make deploy     # Déploie MinIO + API + UI + JupyterLab
make init       # Upload les CSV vers MinIO
make logs       # Logs de MinIO
make logs-api   # Logs de l API
make logs-ui    # Logs de l UI
make logs-jupyter # Logs de JupyterLab
make stop       # Arrêter le cluster
make start      # Démarrer le cluster
make clean      # Tout supprimer
```

## Structure des données

Les CSV sources sont dans `datasets/` localement, puis dans MinIO :

```text
datasets/
├── effectifs.csv
└── annuaire-des-entreprises-etablissements-08_04_2026.csv
```

Dans MinIO :

```
Bucket: datasets
└── raw/
    ├── effectifs.csv
    └── annuaire-des-entreprises-etablissements-08_04_2026.csv
```

## Ajouter des données

```bash
# 1. Ajouter un fichier dans datasets/
cp mon-fichier.csv datasets/

# 2. Uploader vers MinIO
make init
```

## Problème ?

```bash
./scripts/validate.sh  # Diagnostic complet
```
