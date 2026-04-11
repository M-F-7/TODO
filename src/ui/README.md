# UI

Interface simple en Streamlit.

## Role

- afficher les datasets exposes par l'API
- voir les metadonnees d'un CSV
- afficher un apercu de lignes
- afficher une carte interactive des regions de France (metropole uniquement)
- surbrillance au survol d'une region (carte neutre hors hover)

## Lancement

```bash
make run-ui
```

L'UI locale demarre sur `http://localhost:8502`.
L'UI appelle l'API FastAPI sur `http://localhost:8000` par defaut.
