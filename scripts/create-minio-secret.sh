#!/bin/bash
# Script pour créer le secret MinIO depuis .env

set -e

# Charger les variables depuis .env
if [ -f .env ]; then
    source .env
else
    echo "Erreur: fichier .env non trouvé"
    exit 1
fi

# Creer le secret Kubernetes dans les namespaces qui en ont besoin.
for namespace in storage api; do
    kubectl create secret generic minio-secret \
        --from-literal=root-user=$MINIO_ROOT_USER \
        --from-literal=root-password=$MINIO_ROOT_PASSWORD \
        --namespace=$namespace \
        --dry-run=client -o yaml | kubectl apply -f -
done

kubectl create secret generic jupyter-secret \
    --from-literal=token=${JUPYTER_TOKEN:-changeme-jupyter-token} \
    --namespace=jupyter \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✓ Secret MinIO créé/mis à jour"
