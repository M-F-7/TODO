# Service de Stockage (MinIO)

Ce dossier contient les manifests Kubernetes pour déployer MinIO.

## Fichiers

- `minio-pvc.yaml` : Volume persistant de 20Gi pour les données
- `minio-deployment.yaml` : Déploiement MinIO (1 replica)
- `minio-service.yaml` : Service LoadBalancer pour exposer MinIO

**Note** : Le namespace `storage` est défini dans `infrastructure/base/namespace.yaml`

## Déploiement

```bash
# Depuis la racine du projet
make deploy
```

Ou manuellement :

```bash
# 1. Créer le namespace (infrastructure)
kubectl apply -f infrastructure/base/namespace.yaml

# 2. Créer le secret
./scripts/create-minio-secret.sh

# 3. Déployer MinIO
kubectl apply -f services/storage/minio-pvc.yaml
kubectl apply -f services/storage/minio-deployment.yaml
kubectl apply -f services/storage/minio-service.yaml
```

## Accès

- **Console Web**: http://localhost:9001
- **API S3**: http://localhost:9000
- **Credentials**: Voir le fichier `.env` à la racine

## Ajout de nouveaux services

Pour ajouter d'autres services plus tard :

1. Créer un nouveau dossier : `services/mon-service/`
2. Ajouter les manifests Kubernetes
3. Ajouter un README.md expliquant le service
4. Mettre à jour le Makefile si nécessaire

## Structure du stockage

MinIO stocke les données dans le bucket `datasets` :

```
datasets/
├── raw/                    # Fichiers CSV bruts
│   ├── effectifs.csv
│   └── StockEtablissement_utf8.csv
```

Les fichiers sources locaux sont ranges dans `datasets/` a la racine du projet.
