from fastapi import FastAPI, HTTPException, Query
from minio.error import S3Error
from pandas.errors import EmptyDataError

from src.backend.minio_data import (
    get_dataset_metadata,
    get_dataset_preview,
    list_datasets,
)


app = FastAPI(title="Datasets API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/datasets")
def datasets() -> dict:
    try:
        return {"items": list_datasets()}
    except S3Error as exc:
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc


@app.get("/datasets/{name}")
def dataset_metadata(name: str) -> dict:
    try:
        return get_dataset_metadata(name)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(status_code=404, detail="Dataset not found") from exc
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc
    except EmptyDataError as exc:
        raise HTTPException(status_code=400, detail="CSV vide ou invalide") from exc


@app.get("/datasets/{name}/preview")
def dataset_preview(
    name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return get_dataset_preview(name, limit=limit, offset=offset)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(status_code=404, detail="Dataset not found") from exc
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc
    except EmptyDataError as exc:
        raise HTTPException(status_code=400, detail="CSV vide ou invalide") from exc
