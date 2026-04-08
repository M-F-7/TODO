# Backend

Backend minimal en FastAPI.

## Routes

- `GET /health`
- `GET /datasets`
- `GET /datasets/{name}`
- `GET /datasets/{name}/preview?limit=20`

## Role

- se connecter a MinIO
- lister les CSV presents dans `raw/`
- retourner des metadonnees simples
- retourner un apercu tabulaire
