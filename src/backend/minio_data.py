import io
import os
import csv
from contextlib import closing

import pandas as pd
from dotenv import load_dotenv
from minio import Minio


load_dotenv()

RAW_PREFIX = "raw/"


def get_minio_client() -> Minio:
    return Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
        secure=False,
    )


def get_bucket_name() -> str:
    return os.getenv("MINIO_BUCKET", "datasets")


def list_datasets() -> list[dict]:
    client = get_minio_client()
    bucket = get_bucket_name()
    datasets = []

    for obj in client.list_objects(bucket, prefix=RAW_PREFIX, recursive=True):
        if not obj.object_name.endswith(".csv"):
            continue
        datasets.append(
            {
                "name": obj.object_name.removeprefix(RAW_PREFIX),
                "object_name": obj.object_name,
                "size_bytes": obj.size,
                "last_modified": obj.last_modified.isoformat()
                if obj.last_modified
                else None,
            }
        )

    return sorted(datasets, key=lambda item: item["name"])


def _dataset_object_name(name: str) -> str:
    return f"{RAW_PREFIX}{name}"


def _detect_separator(text_sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _read_csv(name: str, **kwargs) -> pd.DataFrame:
    client = get_minio_client()
    bucket = get_bucket_name()
    object_name = _dataset_object_name(name)

    with closing(client.get_object(bucket, object_name)) as response:
        sample = response.read(4096)

    separator = _detect_separator(sample.decode("utf-8", errors="ignore"))

    with closing(client.get_object(bucket, object_name)) as response:
        # Read bytes fully before parsing to avoid parser reads on a closed socket stream.
        payload = response.read()

    text_stream = io.StringIO(payload.decode("utf-8", errors="replace"))
    return pd.read_csv(text_stream, sep=separator, **kwargs)


def read_dataset(name: str, **kwargs):
    """Read a CSV dataset from MinIO with separator auto-detection."""
    return _read_csv(name, **kwargs)


def iter_dataset_chunks(name: str, chunksize: int = 100_000, **kwargs):
    """Iterate over a CSV dataset from MinIO without loading it all in memory."""
    client = get_minio_client()
    bucket = get_bucket_name()
    object_name = _dataset_object_name(name)

    with closing(client.get_object(bucket, object_name)) as response:
        sample = response.read(4096)

    separator = _detect_separator(sample.decode("utf-8", errors="ignore"))

    response = client.get_object(bucket, object_name)
    text_stream = io.TextIOWrapper(response, encoding="utf-8")
    try:
        reader = pd.read_csv(text_stream, sep=separator, chunksize=chunksize, **kwargs)
        for chunk in reader:
            yield chunk
    finally:
        try:
            text_stream.detach()
        except Exception:
            pass
        response.close()


def iter_dataset_rows(name: str):
    """Iterate over CSV rows from MinIO as dictionaries without loading the file in memory."""
    client = get_minio_client()
    bucket = get_bucket_name()
    object_name = _dataset_object_name(name)

    with closing(client.get_object(bucket, object_name)) as response:
        sample = response.read(4096)

    separator = _detect_separator(sample.decode("utf-8", errors="ignore"))

    response = client.get_object(bucket, object_name)
    try:
        header = None
        buffer = b""
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            buffer += chunk
            lines = buffer.split(b"\n")
            buffer = lines.pop()

            for raw_line in lines:
                line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
                if not line:
                    continue
                if header is None:
                    header = next(csv.reader([line], delimiter=separator), None)
                    continue
                values = next(csv.reader([line], delimiter=separator), None)
                if values is None:
                    continue
                yield dict(zip(header, values))

        if buffer:
            line = buffer.rstrip(b"\r").decode("utf-8", errors="replace")
            if line:
                if header is None:
                    header = next(csv.reader([line], delimiter=separator), None)
                else:
                    values = next(csv.reader([line], delimiter=separator), None)
                    if values is not None:
                        yield dict(zip(header, values))
    finally:
        response.close()


def get_dataset_metadata(name: str) -> dict:
    client = get_minio_client()
    bucket = get_bucket_name()
    object_name = _dataset_object_name(name)
    stat = client.stat_object(bucket, object_name)
    header = _read_csv(name, nrows=0)

    return {
        "name": name,
        "object_name": object_name,
        "size_bytes": stat.size,
        "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
        "etag": stat.etag,
        "columns": header.columns.tolist(),
        "column_count": len(header.columns),
    }


def get_dataset_preview(name: str, limit: int = 20, offset: int = 0) -> dict:
    dataframe = _read_csv(name, skiprows=range(1, offset + 1), nrows=limit)
    return {
        "name": name,
        "rows": dataframe.fillna("").to_dict(orient="records"),
        "columns": dataframe.columns.tolist(),
        "row_count": len(dataframe),
        "offset": offset,
    }
