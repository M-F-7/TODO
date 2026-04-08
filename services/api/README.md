# Service API

Ce dossier contient le deploiement Kubernetes de l'API FastAPI.

## Role

- lire les datasets directement depuis MinIO
- exposer les metadonnees et un apercu des CSV

## Ressources

- `deployment.yaml`
- `service.yaml`

## Acces

- service interne : `http://api.api.svc.cluster.local:8000`
- acces local : `http://localhost:8000`
