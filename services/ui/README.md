# Service UI

Ce dossier contient le deploiement Kubernetes de l'interface Streamlit.

## Role

- appeler l'API FastAPI
- afficher les metadonnees des datasets
- afficher un apercu des lignes

## Ressources

- `deployment.yaml`
- `service.yaml`

## Acces

- service interne : `http://ui.ui.svc.cluster.local:8501`
- acces local : `http://localhost:8501`
