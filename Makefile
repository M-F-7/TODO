.PHONY: help install cluster build-images build-images-prod deploy deploy-prod deploy-storage deploy-api deploy-api-prod deploy-ui deploy-ui-prod deploy-jupyter run-ui init clean status logs logs-api logs-ui logs-jupyter stop start all

# Variables
CLUSTER_NAME=data-cluster
REGISTRY?=docker.io/library
IMAGE_TAG?=local
API_IMAGE=$(REGISTRY)/datasets-api:$(IMAGE_TAG)
UI_IMAGE=$(REGISTRY)/datasets-ui:$(IMAGE_TAG)
PROD_IMAGE_TAG?=prod
API_IMAGE_PROD=$(REGISTRY)/datasets-api:$(PROD_IMAGE_TAG)
UI_IMAGE_PROD=$(REGISTRY)/datasets-ui:$(PROD_IMAGE_TAG)
export KUBECONFIG=$HOME/.config/k3d/kubeconfig-data-cluster.yaml
BLUE=\033[1;34m
GREEN=\033[1;32m
YELLOW=\033[1;33m
NC=\033[0m

help: ## Affiche l'aide
	@echo "╔════════════════════════════════════════════╗"
	@echo "║       Cluster k3d + MinIO                  ║"
	@echo "╚════════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances (k3d, kubectl, uv)
	@echo "Installation des dépendances..."
	@command -v k3d >/dev/null 2>&1 || curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
	@command -v kubectl >/dev/null 2>&1 || { echo "Installez kubectl manuellement"; exit 1; }
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@uv sync
	@echo "✓ Dépendances installées"

cluster: ## Crée le cluster k3d
	@echo "Création du cluster..."
	@if k3d cluster list | grep -q "^$(CLUSTER_NAME)[[:space:]]"; then \
		echo "✓ Cluster deja present"; \
	else \
		k3d cluster create $(CLUSTER_NAME) \
			--servers 1 \
			--agents 2 \
			--port 9000:9000@loadbalancer \
			--port 9001:9001@loadbalancer \
			--port 8000:8000@loadbalancer \
			--port 8501:8501@loadbalancer \
			--port 8888:8888@loadbalancer; \
		echo "✓ Cluster créé"; \
	fi

deploy: ## Déploie MinIO
	@$(MAKE) deploy-storage
	@$(MAKE) build-images
	@$(MAKE) deploy-api
	@$(MAKE) deploy-ui
	@$(MAKE) deploy-jupyter

deploy-storage: ## Déploie MinIO
	@echo "Déploiement de MinIO..."
	@echo "1. Création du namespace..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@echo "2. Création du secret..."
	@./scripts/create-minio-secret.sh
	@echo "3. Déploiement des ressources MinIO..."
	@kubectl apply -f services/storage/minio-pvc.yaml
	@kubectl apply -f services/storage/minio-deployment.yaml
	@kubectl apply -f services/storage/minio-service.yaml
	@echo "✓ MinIO soumis au cluster"
	@echo ""
	@echo "MinIO Console: http://localhost:9001"
	@echo "MinIO API: http://localhost:9000"
	@echo "Credentials: voir .env"
	@echo "Verification: kubectl get pods -n storage"

build-images: ## Build les images Docker de l'API et de l'UI
	@echo "Build des images applicatives..."
	@docker build -f src/backend/Dockerfile -t $(API_IMAGE) .
	@docker build -f src/ui/Dockerfile -t $(UI_IMAGE) .
	@k3d image import -c $(CLUSTER_NAME) $(API_IMAGE) $(UI_IMAGE)
	@echo "✓ Images buildées et importées dans k3d"

build-images-prod: ## Build les images prod (sans import k3d)
	@echo "Build des images prod..."
	@docker build -f src/backend/Dockerfile -t $(API_IMAGE_PROD) .
	@docker build -f src/ui/Dockerfile -t $(UI_IMAGE_PROD) .
	@echo "✓ Images prod buildées: $(API_IMAGE_PROD) et $(UI_IMAGE_PROD)"

deploy-api: build-images ## Déploie l API FastAPI dans le cluster
	@echo "Déploiement de l'API..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@./scripts/create-minio-secret.sh
	@kubectl apply -f services/api/deployment.yaml
	@kubectl apply -f services/api/service.yaml
	@kubectl -n api rollout restart deployment/api
	@kubectl -n api rollout status deployment/api --timeout=180s
	@echo "✓ API soumise au cluster sur http://localhost:8000"
	@echo "Verification: kubectl get pods -n api"

deploy-api-prod: ## Déploie l API avec image prod
	@echo "Déploiement API prod..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@./scripts/create-minio-secret.sh
	@kubectl apply -f services/api/deployment.yaml
	@kubectl apply -f services/api/service.yaml
	@kubectl -n api set image deployment/api api=$(API_IMAGE_PROD)
	@kubectl -n api patch deployment api --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]'
	@echo "✓ API prod soumise au cluster avec image $(API_IMAGE_PROD)"

deploy-ui: build-images ## Déploie l UI Streamlit dans le cluster
	@echo "Déploiement de l'UI..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@kubectl apply -f services/ui/deployment.yaml
	@kubectl apply -f services/ui/service.yaml
	@kubectl -n ui rollout restart deployment/ui
	@kubectl -n ui rollout status deployment/ui --timeout=180s
	@echo "✓ UI soumise au cluster sur http://localhost:8501"
	@echo "Verification: kubectl get pods -n ui"

deploy-ui-prod: ## Déploie l UI avec image prod
	@echo "Déploiement UI prod..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@kubectl apply -f services/ui/deployment.yaml
	@kubectl apply -f services/ui/service.yaml
	@kubectl -n ui set image deployment/ui ui=$(UI_IMAGE_PROD)
	@kubectl -n ui patch deployment ui --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]'
	@echo "✓ UI prod soumise au cluster avec image $(UI_IMAGE_PROD)"

run-ui: ## Lance l UI Streamlit en local (hors Kubernetes)
	@API_BASE_URL=http://localhost:8000 uv run streamlit run src/ui/mortalite.py --server.port 8502 --server.address 0.0.0.0

deploy-prod: ## Déploie MinIO + API/UI en mode prod
	@$(MAKE) deploy-storage
	@$(MAKE) build-images-prod
	@$(MAKE) deploy-api-prod
	@$(MAKE) deploy-ui-prod
	@$(MAKE) deploy-jupyter

deploy-jupyter: ## Déploie JupyterLab dans le cluster
	@echo "Déploiement de JupyterLab..."
	@kubectl apply -f infrastructure/base/namespace.yaml
	@./scripts/create-minio-secret.sh
	@kubectl apply -f services/jupyter/jupyter-pvc.yaml
	@kubectl apply -f services/jupyter/deployment.yaml
	@kubectl apply -f services/jupyter/service.yaml
	@echo "✓ JupyterLab soumis au cluster sur http://localhost:8888"
	@echo "Verification: kubectl get pods -n jupyter"

init: ## Initialise MinIO et upload les CSV
	@echo "Initialisation de MinIO..."
	@KUBECONFIG=$(KUBECONFIG) kubectl port-forward -n storage svc/minio 19000:9000 >/tmp/minio-port-forward.log 2>&1 & \
	PORT_FORWARD_PID=$$!; \
	sleep 3; \
	MINIO_ENDPOINT=localhost:19000 uv run scripts/init-minio.py; \
	kill $$PORT_FORWARD_PID >/dev/null 2>&1 || true
	@echo "✓ MinIO initialisé"

status: ## Affiche le statut
	@printf "$(BLUE)╔════════════════════════════════════════════╗$(NC)\n"
	@printf "$(BLUE)║              Etat du Projet               ║$(NC)\n"
	@printf "$(BLUE)╚════════════════════════════════════════════╝$(NC)\n\n"
	@printf "$(YELLOW)Cluster:$(NC) %s\n" "$(CLUSTER_NAME)"
	@printf "$(YELLOW)Kubeconfig:$(NC) %s\n\n" "$(KUBECONFIG)"
	@printf "$(BLUE)Services$(NC)\n"
	@printf "  MinIO Console : $(GREEN)%s$(NC)\n" "http://localhost:9001"
	@printf "  MinIO API     : $(GREEN)%s$(NC)\n" "http://localhost:9000"
	@printf "  FastAPI       : $(GREEN)%s$(NC)\n" "http://localhost:8000"
	@printf "  Streamlit     : $(GREEN)%s$(NC)\n" "http://localhost:8501"
	@printf "  JupyterLab    : $(GREEN)%s$(NC)\n\n" "http://localhost:8888"
	@printf "$(BLUE)Nodes$(NC)\n"
	@kubectl get nodes -o wide
	@printf "\n$(BLUE)Pods$(NC)\n"
	@kubectl get pods -A
	@printf "\n$(BLUE)Services Kubernetes$(NC)\n"
	@kubectl get svc -A
	@printf "\n$(BLUE)Resume$(NC)\n"
	@printf "  storage/minio : " && kubectl get pods -n storage -l app=minio --no-headers 2>/dev/null | awk 'BEGIN{ok=0} /Running/ {ok=1} END{if(ok) print "$(GREEN)RUNNING$(NC)"; else print "$(YELLOW)NOT READY$(NC)"}'
	@printf "  api/api       : " && kubectl get pods -n api -l app=api --no-headers 2>/dev/null | awk 'BEGIN{ok=0} /Running/ {ok=1} END{if(ok) print "$(GREEN)RUNNING$(NC)"; else print "$(YELLOW)NOT READY$(NC)"}'
	@printf "  ui/ui         : " && kubectl get pods -n ui -l app=ui --no-headers 2>/dev/null | awk 'BEGIN{ok=0} /Running/ {ok=1} END{if(ok) print "$(GREEN)RUNNING$(NC)"; else print "$(YELLOW)NOT READY$(NC)"}'
	@printf "  jupyter/lab   : " && kubectl get pods -n jupyter -l app=jupyter --no-headers 2>/dev/null | awk 'BEGIN{ok=0} /Running/ {ok=1} END{if(ok) print "$(GREEN)RUNNING$(NC)"; else print "$(YELLOW)NOT READY$(NC)"}'

logs: ## Affiche les logs MinIO
	@kubectl logs -n storage -l app=minio --tail=100 -f

logs-api: ## Affiche les logs de l API
	@kubectl logs -n api -l app=api --tail=100 -f

logs-ui: ## Affiche les logs de l UI
	@kubectl logs -n ui -l app=ui --tail=100 -f

logs-jupyter: ## Affiche les logs de JupyterLab
	@kubectl logs -n jupyter -l app=jupyter --tail=100 -f

stop: ## Arrête le cluster
	@k3d cluster stop $(CLUSTER_NAME)

start: ## Démarre le cluster
	@k3d cluster start $(CLUSTER_NAME)

clean: ## Supprime tout
	@k3d cluster delete $(CLUSTER_NAME)

all: install cluster deploy init ## Installation complete du projet
	@echo ""
	@echo "✓ Installation terminée!"
	@echo ""
	@echo "Accès MinIO Console: http://localhost:9001"
	@echo "API FastAPI: http://localhost:8000"
	@echo "UI Streamlit: http://localhost:8501"
	@echo "JupyterLab: http://localhost:8888"
