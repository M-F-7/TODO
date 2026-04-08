# Source

Ce dossier contient le code source applicatif du projet.

## Structure

```text
src/
├── backend/   # API FastAPI
└── ui/        # Interface Streamlit
```

## Lancement

```bash
make deploy
```

L'API lit les donnees directement depuis MinIO.
L'UI interroge l'API pour afficher les datasets, leurs metadonnees et un apercu.
Les deux tournent dans le cluster Kubernetes, pas dans l'environnement local.
