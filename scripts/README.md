# Scripts

Scripts d'automatisation pour le projet.

Les scripts Python sont utilises localement uniquement pour l'initialisation et l'upload dans MinIO.

## Scripts disponibles

### create-minio-secret.sh
Crée le secret Kubernetes pour MinIO depuis le fichier `.env`.

```bash
./scripts/create-minio-secret.sh
```

### init-minio.py
Initialise MinIO : crée le bucket `datasets` et upload les fichiers CSV du dossier `datasets/` dans `raw/`.

```bash
uv run scripts/init-minio.py
```

Prerequis : `uv sync`

### validate.sh
Valide l'installation complète du cluster et des services.

```bash
./scripts/validate.sh
```

Vérifie :
- Présence des dépendances (docker, kubectl, k3d)
- État du cluster
- Accessibilité de MinIO
- Présence des fichiers CSV dans `datasets/`

## Ajouter un nouveau script

1. Créer le fichier dans `scripts/`
2. Le rendre exécutable : `chmod +x scripts/mon-script.sh`
3. Documenter son usage ici
4. Ajouter une target dans le Makefile si nécessaire
