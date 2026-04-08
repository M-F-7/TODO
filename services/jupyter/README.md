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

## Variables d'environnement

Le conteneur Jupyter charge maintenant les variables de `.env` via un `Secret` Kubernetes `app-env`.

Variables disponibles dans le pod :

- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `MINIO_BUCKET`
- `JUPYTER_TOKEN`

`MINIO_ENDPOINT` est ensuite surcharge a `minio.storage.svc.cluster.local:9000` pour fonctionner dans le cluster.