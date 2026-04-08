# Infrastructure de base

Ce dossier contient les ressources Kubernetes partagées et de base.

## Fichiers

- `namespace.yaml` : Définit le namespace `storage` pour MinIO

## Pourquoi les namespaces sont ici ?

Les namespaces sont des ressources globales qui structurent le cluster. Ils sont donc dans `infrastructure/base/` plutôt que dans les dossiers de services individuels.

```
infrastructure/base/    → Ressources globales (namespaces)
services/storage/       → Ressources spécifiques à MinIO
```

## Ajouter un namespace

Quand vous ajouterez d'autres services :

```yaml
# infrastructure/base/namespace.yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: api
  labels:
    name: api
---
apiVersion: v1
kind: Namespace
metadata:
  name: processing
  labels:
    name: processing
```

## Ordre de déploiement

1. **Infrastructure** (namespaces) → `kubectl apply -f infrastructure/base/`
2. **Services** (deployments, etc.) → `kubectl apply -f services/storage/`
