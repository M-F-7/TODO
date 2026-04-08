# Organisation du Projet

## 📁 Structure et logique

```
.
├── datasets/                 # Donnees source versionnees par DVC
├── infrastructure/           # 🏗️ Ressources GLOBALES du cluster
│   └── base/
│       └── namespace.yaml   # Définit les namespaces
│
└── services/                # 📦 Ressources SPÉCIFIQUES aux services
    └── storage/
        ├── minio-deployment.yaml
        ├── minio-pvc.yaml
        └── minio-service.yaml
```

## 🤔 Pourquoi cette organisation ?

### Infrastructure = Global
Les namespaces sont dans `infrastructure/` car ils sont **globaux** :
- Créés en premier (avant les services)
- Peuvent être utilisés par plusieurs services
- Définissent la structure du cluster

### Services = Spécifique
Chaque service a son dossier avec ses ressources propres :
- Deployments
- Services
- PVC
- ConfigMaps
- etc.

## 📝 Ordre de déploiement

```bash
1. infrastructure/base/namespace.yaml    # Crée les namespaces
   ↓
2. scripts/create-minio-secret.sh        # Crée les secrets
   ↓
3. services/storage/*.yaml               # Déploie MinIO
```

Le Makefile gère cet ordre automatiquement avec `make deploy`.

## 🔄 Ajouter un nouveau service

### Étape 1 : Ajouter le namespace (si nouveau)
```yaml
# infrastructure/base/namespace.yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: mon-service
```

### Étape 2 : Créer le dossier du service
```bash
mkdir -p services/mon-service
```

### Étape 3 : Ajouter les manifests
```bash
services/mon-service/
├── deployment.yaml       # Utilise "namespace: mon-service"
├── service.yaml
├── configmap.yaml
└── README.md
```

### Étape 4 : Mettre à jour le Makefile
```makefile
deploy-mon-service: ## Déploie mon-service
	kubectl apply -f services/mon-service/
```

## ✅ Bonnes pratiques

1. **Namespaces** : Toujours dans `infrastructure/base/`
2. **Ressources spécifiques** : Toujours dans `services/<nom>/`
3. **README** : Un par dossier pour expliquer
4. **Labels cohérents** : `app`, `component`, `version`

## 🎯 Résumé visuel

```
infrastructure/     services/storage/
    │                    │
    ├─ namespace.yaml    ├─ minio-deployment.yaml
    │                    │  (uses namespace: storage)
    │                    │
    │                    ├─ minio-service.yaml
    │                    └─ minio-pvc.yaml
    │
    └─ Définit "storage" ← Utilisé par MinIO
```
