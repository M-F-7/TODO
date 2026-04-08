import os

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_get(path: str, **kwargs) -> dict:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def format_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    if unit == "B":
        return f"{int(size)} {unit}"
    return f"{size:.2f} {unit}"


st.set_page_config(page_title="Datasets Explorer", layout="wide")
st.title("Datasets Explorer")
st.caption(
    "UI beginner-friendly pour visualiser les CSV stockes dans MinIO via FastAPI."
)

with st.sidebar:
    st.header("Configuration")
    st.code(API_BASE_URL)

try:
    datasets_response = api_get("/datasets")
    datasets = datasets_response.get("items", [])
except requests.RequestException as exc:
    st.error(f"Impossible de contacter l'API: {exc}")
    st.stop()

if not datasets:
    st.warning("Aucun dataset trouve dans MinIO. Lancez d'abord 'make init'.")
    st.stop()

dataset_by_name = {item["name"]: item for item in datasets}
dataset_names = list(dataset_by_name)

with st.sidebar:
    st.header("Pages")
    selected_dataset = st.radio("Dataset", dataset_names)
    st.caption("Chaque dataset agit comme une page dediee.")
    start_row = st.number_input("Ligne de depart", min_value=0, value=0, step=100)
    limit = st.slider(
        "Nombre de lignes", min_value=10, max_value=100, value=20, step=10
    )

try:
    metadata = api_get(f"/datasets/{selected_dataset}")
    preview = api_get(
        f"/datasets/{selected_dataset}/preview",
        params={"limit": limit, "offset": start_row},
    )
except requests.RequestException as exc:
    st.error(f"Erreur de chargement du dataset: {exc}")
    st.stop()

st.header(selected_dataset)

col1, col2, col3 = st.columns(3)
col1.metric("Colonnes", metadata["column_count"])
col2.metric("Taille", format_size(metadata["size_bytes"]))
col3.metric(
    "Lignes affichees",
    f"{preview['offset']} - {preview['offset'] + preview['row_count']}",
)

st.subheader("Metadonnees")
st.json(metadata)

st.subheader("Colonnes")
st.write(metadata["columns"])

st.subheader("Apercu")
st.caption(
    f"Affichage a partir de la ligne {preview['offset']} sur {preview['row_count']} lignes."
)
st.dataframe(pd.DataFrame(preview["rows"]), use_container_width=True)
