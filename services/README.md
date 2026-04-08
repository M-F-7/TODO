# Services

Ce dossier contient tous les microservices de l'application.

## Structure

```
services/
├── api/              # Service FastAPI
│   ├── README.md
│   ├── deployment.yaml
│   └── service.yaml
├── jupyter/          # Service JupyterLab
│   ├── README.md
│   ├── deployment.yaml
│   ├── jupyter-pvc.yaml
│   └── service.yaml
├── storage/          # Service de stockage (MinIO)
│   ├── README.md
│   ├── minio-pvc.yaml
│   ├── minio-deployment.yaml
│   └── minio-service.yaml
└── ui/               # Service Streamlit
    ├── README.md
    ├── deployment.yaml
    └── service.yaml
```

## Services actuels

### Storage (MinIO)
Service de stockage objet S3-compatible pour stocker les fichiers CSV du projet.

### API (FastAPI)
Service backend qui lit les datasets dans MinIO et expose metadonnees et apercu.

### UI (Streamlit)
Service frontend qui appelle l'API et affiche les datasets dans une interface simple.

### JupyterLab
Service notebook interactif pour explorer les donnees directement dans le cluster.

## Ajouter un nouveau service

Pour ajouter un service (API, traitement, etc.) :

1. **Créer le dossier**
   ```bash
   mkdir -p services/mon-service
   ```

2. **Créer les manifests Kubernetes**
   ```bash
   # services/mon-service/namespace.yaml
   # services/mon-service/deployment.yaml
   # services/mon-service/service.yaml
   ```

3. **Ajouter un README**
   ```bash
   # services/mon-service/README.md
   ```

4. **Mettre à jour le Makefile**
   Ajouter une target pour déployer le nouveau service

## Bonnes pratiques

- Un namespace par service
- Un README par service
- Labels clairs : `app`, `component`, `version`
- Secrets via `.env` et scripts
- Configuration via ConfigMaps
