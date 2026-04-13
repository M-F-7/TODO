import os
import importlib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REGIONS_GEOJSON_URL = os.getenv(
    "REGIONS_GEOJSON_URL",
    "https://france-geojson.gregoiredavid.fr/repo/regions.geojson",
)


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


@st.cache_data(show_spinner=False)
def load_regions_geojson() -> dict:
    response = requests.get(REGIONS_GEOJSON_URL, timeout=30)
    response.raise_for_status()
    return response.json()


DROM_NAMES_SET = {"Guadeloupe", "Martinique", "La Réunion", "Mayotte", "Guyane"}


def filter_metropole_only(geojson: dict) -> dict:
    """Filter out DROM, keep only metropolitan France."""
    return {
        "type": geojson.get("type", "FeatureCollection"),
        "features": [
            feature
            for feature in geojson.get("features", [])
            if feature.get("properties", {}).get("nom") not in DROM_NAMES_SET
        ],
    }


def get_bounds_from_geojson(geojson: dict) -> tuple:
    """Extract bounding box from GeoJSON features."""
    lats, lons = [], []
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "Polygon":
            for ring in geometry.get("coordinates", []):
                for lon, lat in ring:
                    lons.append(lon)
                    lats.append(lat)
        elif geometry.get("type") == "MultiPolygon":
            for poly in geometry.get("coordinates", []):
                for ring in poly:
                    for lon, lat in ring:
                        lons.append(lon)
                        lats.append(lat)
    if not lats or not lons:
        return None
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def build_regions_df(geojson: dict) -> pd.DataFrame:
    rows = []
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        rows.append(
            {
                "code": properties.get("code"),
                "nom": properties.get("nom"),
            }
        )
    return pd.DataFrame(rows).dropna(subset=["code", "nom"])


def render_home_tab() -> None:
    st.header("Carte interactive des regions")
    st.caption("France métropolitaine - 12 régions.")

    try:
        geojson = load_regions_geojson()
    except requests.RequestException as exc:
        st.error(f"Impossible de charger la carte des regions: {exc}")
        return

    regions_df = build_regions_df(geojson)
    if regions_df.empty:
        st.warning("Aucune region detectee dans la source GeoJSON.")
        return

    st.caption("Carte en ton neutre: seule la region survolee est mise en couleur.")

    try:
        folium = importlib.import_module("folium")
    except ModuleNotFoundError:
        st.error("Le package 'folium' manque. Lance 'uv sync' puis redemarre l'UI.")
        return

    geojson_metro = filter_metropole_only(geojson)
    regions_df_metro = build_regions_df(geojson_metro)
    
    bounds = get_bounds_from_geojson(geojson_metro)
    
    if bounds:
        min_lat, min_lon = bounds[0]
        max_lat, max_lon = bounds[1]
        padding_lat = (max_lat - min_lat) * 0.05
        padding_lon = (max_lon - min_lon) * 0.05
        padded_bounds = [
            [min_lat - padding_lat, min_lon - padding_lon],
            [max_lat + padding_lat, max_lon + padding_lon]
        ]
    else:
        padded_bounds = [[41.0, -6.0], [51.5, 8.5]]
    
    region_map = folium.Map(
        location=[46.2, 2.0],
        zoom_start=6,
        tiles="CartoDB positron",
        control_scale=False,
        min_zoom=5,
        max_zoom=10,
        max_bounds=True,
    )
    
    region_map.fit_bounds(padded_bounds)

    folium.GeoJson(
        geojson_metro,
        name="Regions",
        style_function=lambda _: {
            "color": "#6b7280",
            "weight": 1,
            "fillColor": "#d1d5db",
            "fillOpacity": 0.04,
        },
        highlight_function=lambda _: {
            "color": "#1d4ed8",
            "weight": 2,
            "fillColor": "#2563eb",
            "fillOpacity": 0.55,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nom", "code"],
            aliases=["Region", "Code"],
            localize=True,
            sticky=False,
        ),
    ).add_to(region_map)
    
    if bounds:
        region_map.fit_bounds(bounds, padding=(40, 40))

    map_html = region_map.get_root().render()
    components.html(map_html, height=760)

    st.markdown("### Regions disponibles")
    st.dataframe(
        regions_df_metro.sort_values("nom").rename(columns={"nom": "Region", "code": "Code"}),
        use_container_width=True,
        hide_index=True,
    )


def render_dataset_tab() -> None:
    st.header("Exploration des datasets")

    try:
        datasets_response = api_get("/datasets")
        datasets = datasets_response.get("items", [])
    except requests.RequestException as exc:
        st.error(f"Impossible de contacter l'API: {exc}")
        return

    if not datasets:
        st.warning("Aucun dataset trouve dans MinIO. Lance d'abord 'make init'.")
        return

    dataset_by_name = {item["name"]: item for item in datasets}
    dataset_names = list(dataset_by_name)

    selected_dataset = st.selectbox("Dataset", dataset_names)
    controls_col1, controls_col2 = st.columns(2)
    with controls_col1:
        start_row = st.number_input("Ligne de depart", min_value=0, value=0, step=100)
    with controls_col2:
        limit = st.slider("Nombre de lignes", min_value=10, max_value=100, value=20, step=10)

    try:
        metadata = api_get(f"/datasets/{selected_dataset}")
        preview = api_get(
            f"/datasets/{selected_dataset}/preview",
            params={"limit": limit, "offset": start_row},
        )
    except requests.RequestException as exc:
        st.error(f"Erreur de chargement du dataset: {exc}")
        return

    st.subheader(selected_dataset)

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


st.set_page_config(page_title="Datasets Explorer", layout="wide")
st.title("Datasets Explorer")
st.caption(
    "UI beginner-friendly pour visualiser les CSV stockes dans MinIO via FastAPI."
)

with st.sidebar:
    st.header("Configuration")
    st.code(API_BASE_URL)

home_tab, datasets_tab = st.tabs(["Accueil", "Datasets"])

with home_tab:
    render_home_tab()

with datasets_tab:
    render_dataset_tab()
