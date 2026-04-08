# Cluster k3d + MinIO

Infrastructure de base pour gérer des données volumineuses avec versionnage.

## 🎯 Objectif

Déployer un cluster Kubernetes local (k3d) avec MinIO pour stocker des fichiers CSV volumineux et les servir directement aux futurs services.

## 📁 Structure du projet

```
.
├── src/                  # Code source backend et UI
├── services/              # Microservices
│   └── storage/          # Service MinIO
├── infrastructure/        # Infrastructure partagée (vide pour l'instant)
├── datasets/             # CSV bruts a uploader vers MinIO
├── scripts/              # Scripts d'automatisation
├── docs/                 # Documentation additionnelle
├── .env                  # Variables d'environnement (credentials)
├── k3d-config.yaml       # Configuration du cluster
├── Makefile              # Automatisation
└── README.md             # Ce fichier
```

**Chaque dossier contient un README expliquant son contenu.**

Voir aussi `ORGANIZATION.md` pour comprendre pourquoi les namespaces sont dans `infrastructure/` et non dans `services/`.

## 🚀 Démarrage rapide

```bash
# 1. Installation complète
make all

# 2. Accéder à MinIO
# Console: http://localhost:9001
# Credentials: voir .env
```

## 📋 Prérequis

- Docker
- kubectl (sera vérifié)
- k3d (sera installé)
- uv

## ⚙️ Prérequis d'exécution

Pour exécuter le projet, il faut :

- Docker en cours de fonctionnement
- `kubectl` disponible dans le `PATH`
- `curl` pour installer `k3d` et `uv`
- acces reseau pour telecharger les outils et images Docker

### Installation de uv

Le projet utilise `uv` du repo Astral : https://github.com/astral-sh/uv

Installation officielle :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Le `Makefile` utilise cette meme methode si `uv` n'est pas deja installe.

## 🔧 Commandes principales

```bash
make help       # Affiche l'aide
make install    # Installe les dépendances
make cluster    # Crée le cluster k3d
make deploy     # Déploie MinIO + API + UI + JupyterLab
make init       # Initialise MinIO et upload les CSV
make status     # Affiche le statut
make logs       # Affiche les logs MinIO
make clean      # Supprime tout
```

## 📊 Données

Le projet gère deux fichiers CSV dans `datasets/` :
- `datasets/effectifs.csv`
- `datasets/annuaire-des-entreprises-etablissements-08_04_2026.csv` (36 MB)

Ces fichiers sont :
1. conserves localement dans `datasets/`
2. uploades dans MinIO
3. disponibles ensuite directement via l'API S3 MinIO

## 🔗 MinIO

Le projet utilise uniquement `MinIO`.

- pas de DVC
- pas de DagsHub
- pas besoin d'exposer MinIO publiquement en local
- les futurs services liront directement dans MinIO

## 🔐 Configuration

Les credentials sont dans `.env` :


**Important** : Ne commitez jamais le `.env` dans Git (déjà dans `.gitignore`).

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│          Cluster k3d                    │
│  ┌───────────────────────────────────┐  │
│  │  Namespace: storage               │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Pod: MinIO                 │  │  │
│  │  │  - API: 9000                │  │  │
│  │  │  - Console: 9001            │  │  │
│  │  │  - Volume: 20Gi PVC         │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         ↕                    ↕
    ┌─────────┐         ┌─────────┐
    │Services │         │  Local  │
    │ futurs  │         │ Browser │
    └─────────┘         └─────────┘
```

## 📦 Ajouter des services

Cette architecture est extensible. Pour ajouter un service :

1. Créer un dossier `services/mon-service/`
2. Ajouter les manifests Kubernetes
3. Créer un README expliquant le service
4. Ajouter une commande dans le Makefile

Exemples de services futurs :
- `services/api/` : API REST pour accéder aux données
- `services/processing/` : Traitement de données
- `services/ml/` : Modèles ML

## 🔄 Workflow MinIO

```bash
# Ajouter ou remplacer un fichier dans datasets/
cp nouveau_fichier.csv datasets/

# Uploader vers MinIO
make init
```

## 🌐 API et UI

Le projet fournit maintenant :

- une API `FastAPI` pour exposer les datasets et leurs metadonnees
- une UI `Streamlit` pour parcourir ces donnees simplement
- un service `JupyterLab` pour explorer les datasets dans un notebook

### Deployer l'API et l'UI

```bash
make deploy
```

API disponible sur `http://localhost:8000`.

Routes principales :

- `GET /health`
- `GET /datasets`
- `GET /datasets/{name}`
- `GET /datasets/{name}/preview`

UI disponible sur `http://localhost:8501`.

JupyterLab disponible sur `http://localhost:8888`.
Le token de connexion est la valeur `JUPYTER_TOKEN` dans `.env`.

Ordre recommande :

1. `make deploy`
2. `make init`
3. ouvrir `http://localhost:8000` pour l'API
4. ouvrir `http://localhost:8501` pour l'UI
5. ouvrir `http://localhost:8888` pour JupyterLab

L'interface affiche :

- la liste des CSV presents dans MinIO
- les metadonnees d'un dataset
- un apercu des lignes du CSV selectionne
- un notebook JupyterLab disponible dans le cluster pour l'exploration libre

## 🐛 Dépannage

```bash
# Vérifier l'installation
./scripts/validate.sh

# Voir les logs
make logs

# Vérifier le statut
make status

# Redémarrer
make stop
make start
```

### Problèmes courants

**MinIO inaccessible** :
```bash
kubectl get pods -n storage
kubectl logs -n storage -l app=minio
```

**Upload vers MinIO echoue** :
```bash
# Vérifier MinIO
curl http://localhost:9000/minio/health/live
```

## 📚 Documentation

- README principal : Ce fichier
- Source : `src/README.md`
- Services : `services/README.md`
- Scripts : `scripts/README.md`
- Infrastructure : `infrastructure/README.md`

## 🛠️ Technologies

- **k3d** : Kubernetes léger dans Docker
- **MinIO** : Stockage objet S3-compatible
- **kubectl** : CLI Kubernetes
- **uv** : Environnement virtuel et execution Python
- **pyproject.toml** : Dependencies gerees par `uv add` et `uv remove`

## 📄 Licence

Projet éducatif et de développement.
