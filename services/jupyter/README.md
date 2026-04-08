# Service JupyterLab

Ce dossier contient le deploiement Kubernetes de JupyterLab.

## Role

- fournir un notebook interactif dans le cluster
- permettre l'exploration des datasets et du code depuis le navigateur

## Ressources

- `jupyter-pvc.yaml`
- `deployment.yaml`
- `service.yaml`

## Acces

- URL : `http://localhost:8888`
- token : valeur `JUPYTER_TOKEN` dans `.env`
