# Infrastructure

Ce dossier contient les configurations d'infrastructure partagées.

## Structure actuelle

```
infrastructure/
└── base/
    ├── namespace.yaml    # Namespaces K8s (storage, etc.)
    └── README.md
```

## Organisation

### Pourquoi les namespaces sont ici ?

Les **namespaces** sont des ressources globales qui structurent le cluster. Ils sont donc dans `infrastructure/` car :
- Ils sont partagés par potentiellement plusieurs services
- Ils doivent être créés avant les services
- Ils définissent la structure globale du cluster

### Règle d'organisation

```
infrastructure/    → Ressources GLOBALES (namespaces, RBAC global, etc.)
services/         → Ressources SPÉCIFIQUES à chaque service
```

Exemple :
```
infrastructure/base/namespace.yaml    → Définit "namespace: storage"
services/storage/minio-deployment.yaml → Utilise "namespace: storage"
```

## Extensions futures

Quand vous ajouterez plus de services, vous pourrez ajouter ici :

### Ingress
```
infrastructure/ingress/
├── README.md
├── nginx-ingress.yaml
└── ingress-rules.yaml
```

### Monitoring
```
infrastructure/monitoring/
├── README.md
├── prometheus/
└── grafana/
```

### Security
```
infrastructure/security/
├── README.md
├── network-policies.yaml
└── pod-security-policies.yaml
```

### Service Mesh (Istio, Linkerd)
```
infrastructure/service-mesh/
├── README.md
└── istio-config.yaml
```

## Pour l'instant

Le projet est volontairement simple. Ajoutez ces composants au fur et à mesure de vos besoins.
