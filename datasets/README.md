# Datasets

Ce dossier contient les fichiers de donnees source du projet.

## Fichiers attendus

- `Taux_de_mortalite.csv`
- `effectifs.csv`
- `annuaire-des-entreprises-etablissements-08_04_2026.csv`

## Role

- stockage local des CSV bruts
- upload vers MinIO via `scripts/init-minio.py`

MinIO est la source de verite des donnees cote application.

## Usage

```bash
make init
```

Les objets sont ensuite stockes dans MinIO dans le bucket `datasets`.
