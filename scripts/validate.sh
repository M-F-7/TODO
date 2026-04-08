#!/bin/bash
# Script de validation de l'installation

set -e

echo "==================================="
echo "  Validation de l'installation"
echo "==================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 est installé"
        return 0
    else
        echo -e "${RED}✗${NC} $1 n'est pas installé"
        return 1
    fi
}

check_cluster() {
    if k3d cluster list | grep -q "data-cluster"; then
        echo -e "${GREEN}✓${NC} Cluster k3d 'data-cluster' existe"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Cluster k3d 'data-cluster' n'existe pas"
        return 1
    fi
}

check_pods() {
    if kubectl get pods -n storage 2>/dev/null | grep -q "Running"; then
        echo -e "${GREEN}✓${NC} Pod MinIO est en cours d'exécution"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Pod MinIO n'est pas en cours d'exécution"
        return 1
    fi
}

check_minio_health() {
    if curl -s -f http://localhost:9000/minio/health/live > /dev/null; then
        echo -e "${GREEN}✓${NC} MinIO API est accessible (port 9000)"
        return 0
    else
        echo -e "${RED}✗${NC} MinIO API n'est pas accessible (port 9000)"
        return 1
    fi
}

check_minio_console() {
    if curl -s -f http://localhost:9001 > /dev/null; then
        echo -e "${GREEN}✓${NC} MinIO Console est accessible (port 9001)"
        return 0
    else
        echo -e "${RED}✗${NC} MinIO Console n'est pas accessible (port 9001)"
        return 1
    fi
}

check_csv_files() {
    local count=0
    if [ -f "datasets/effectifs.csv" ]; then
        echo -e "${GREEN}✓${NC} datasets/effectifs.csv existe ($(du -h datasets/effectifs.csv | cut -f1))"
        ((count++))
    else
        echo -e "${RED}✗${NC} datasets/effectifs.csv n'existe pas"
    fi

    if [ -f "datasets/annuaire-des-entreprises-etablissements-08_04_2026.csv" ]; then
        echo -e "${GREEN}✓${NC} datasets/annuaire-des-entreprises-etablissements-08_04_2026.csv existe ($(du -h datasets/annuaire-des-entreprises-etablissements-08_04_2026.csv | cut -f1))"
        ((count++))
    else
        echo -e "${RED}✗${NC} datasets/annuaire-des-entreprises-etablissements-08_04_2026.csv n'existe pas"
    fi
    
    return $((2 - count))
}

echo "1. Vérification des dépendances"
echo "--------------------------------"
DEPS_OK=true
check_command docker || DEPS_OK=false
check_command kubectl || DEPS_OK=false
check_command k3d || DEPS_OK=false
check_command uv || DEPS_OK=false
check_command make || DEPS_OK=false
echo ""

echo "2. Vérification du cluster"
echo "---------------------------"
CLUSTER_OK=true
check_cluster || CLUSTER_OK=false
if [ "$CLUSTER_OK" = true ]; then
    check_pods || CLUSTER_OK=false
fi
echo ""

echo "3. Vérification de MinIO"
echo "-------------------------"
MINIO_OK=true
if [ "$CLUSTER_OK" = true ]; then
    check_minio_health || MINIO_OK=false
    check_minio_console || MINIO_OK=false
else
    echo -e "${YELLOW}⚠${NC} Cluster non démarré, impossible de vérifier MinIO"
    MINIO_OK=false
fi
echo ""

echo "4. Vérification des fichiers CSV"
echo "---------------------------------"
CSV_OK=true
check_csv_files || CSV_OK=false
echo ""

echo "==================================="
echo "  Résumé"
echo "==================================="
echo ""

if [ "$DEPS_OK" = true ] && [ "$CLUSTER_OK" = true ] && [ "$MINIO_OK" = true ] && [ "$CSV_OK" = true ]; then
    echo -e "${GREEN}✓ Tout est prêt !${NC}"
    echo ""
    echo "Vous pouvez :"
    echo "  - Accéder à MinIO Console : http://localhost:9001"
    echo "  - Charger vos donnees depuis MinIO"
    echo "  - Voir le statut : make status"
    echo ""
    exit 0
elif [ "$DEPS_OK" = false ]; then
    echo -e "${RED}✗ Dépendances manquantes${NC}"
    echo ""
    echo "Exécutez : make install"
    echo ""
    exit 1
elif [ "$CLUSTER_OK" = false ]; then
    echo -e "${YELLOW}⚠ Cluster non démarré${NC}"
    echo ""
    echo "Exécutez : make cluster puis make deploy"
    echo ""
    exit 1
elif [ "$MINIO_OK" = false ]; then
    echo -e "${YELLOW}⚠ MinIO non accessible${NC}"
    echo ""
    echo "Vérifiez les logs : make logs"
    echo "Ou redémarrez : make stop puis make start"
    echo ""
    exit 1
else
    echo -e "${YELLOW}⚠ Configuration incomplète${NC}"
    echo ""
    echo "Pour une installation complète : make all"
    echo ""
    exit 1
fi
