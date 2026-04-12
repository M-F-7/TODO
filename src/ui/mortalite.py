import os
from urllib.parse import quote

import plotly.express as px
import requests
import streamlit as st


st.set_page_config(layout="wide", page_title="Pilotage des couts sante")
st.title("Carte France interactive pour prevision des couts")
st.caption("Cliquez une region, puis un departement pour afficher les details (ages, sexes, pathologies, couts).")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

if "selected_region" not in st.session_state:
    st.session_state.selected_region = None
if "selected_dep" not in st.session_state:
    st.session_state.selected_dep = None


DROM_REGION_NAMES = {"Guadeloupe", "Martinique", "Guyane", "La Reunion", "La Réunion", "Mayotte"}
DROM_DEP_PREFIXES = ("97", "98")



def api_get(path: str, **kwargs) -> dict:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=120, **kwargs)
    if response.status_code == 404 and path.startswith("/analytics/"):
        raise RuntimeError(
            "API sans endpoints analytics. Redeploie l'API avec 'make deploy-api' "
            "(ou 'make deploy-prod')."
        )
    response.raise_for_status()
    return response.json()


@st.cache_data
def load_geojson_dep() -> dict:
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


@st.cache_data
def load_geojson_regions() -> dict:
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _filter_metropole_regions_geojson(geojson: dict) -> dict:
    features = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        name = str(props.get("nom", "")).strip()
        code = str(props.get("code", "")).strip()
        if name in DROM_REGION_NAMES:
            continue
        if code in {"01", "02", "03", "04", "06"}:
            continue
        features.append(feature)
    return {"type": geojson.get("type", "FeatureCollection"), "features": features}


def _filter_metropole_departments_geojson(geojson: dict, allowed_codes: set[str] | None = None) -> dict:
    features = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        dep_code = str(props.get("code", "")).strip().upper()
        if dep_code.startswith(DROM_DEP_PREFIXES):
            continue
        if allowed_codes is not None and dep_code not in allowed_codes:
            continue
        features.append(feature)
    return {"type": geojson.get("type", "FeatureCollection"), "features": features}


def _selected_location(selection: object) -> str | None:
    if not isinstance(selection, dict):
        return None
    sel = selection.get("selection") or {}
    points = sel.get("points") or []
    if not points:
        return None
    point = points[0]
    value = point.get("location")
    if value:
        return str(value)
    return None


def _series_to_rows(values: dict) -> list[dict]:
    return [{"label": key, "count": val} for key, val in values.items()]


@st.cache_data(ttl=120)
def load_regions_analytics() -> list[dict]:
    return api_get("/analytics/health/regions").get("items", [])


@st.cache_data(ttl=120)
def load_region_departments(region: str) -> list[dict]:
    safe_region = quote(region, safe="")
    return api_get(f"/analytics/health/regions/{safe_region}/departments").get("items", [])


@st.cache_data(ttl=120)
def load_department_details(dep_code: str) -> dict:
    return api_get(f"/analytics/health/departments/{dep_code}")


def render_department_details(dep_code: str) -> None:
    try:
        details = load_department_details(dep_code)
    except requests.RequestException as exc:
        st.error(f"Impossible de charger les details du departement {dep_code}: {exc}")
        return
    row = details.get("department", {})
    annuaire = details.get("annuaire", {})
    effectifs = details.get("effectifs", {})
    projection = details.get("projection", {})

    st.subheader(f"Departement {dep_code} - {row.get('departement', 'N/A')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Taux premature (0-64)", f"{float(row.get('taux_premature', 0) or 0):.2f} ‰")
    c2.metric("Taux brut", f"{float(row.get('taux_brut', 0) or 0):.2f} ‰")
    c3.metric("Taux femmes", f"{float(row.get('taux_femmes', 0) or 0):.2f} ‰")
    c4.metric("Taux hommes", f"{float(row.get('taux_hommes', 0) or 0):.2f} ‰")

    st.info(f"Deces domicilies 2024: {int(row.get('deces_2024', 0) or 0):,}".replace(",", " "))

    left, right = st.columns(2)

    with left:
        st.markdown("### Structures de sante (annuaire)")
        st.metric("Nb etablissements", f"{int(annuaire.get('etablissements', 0)):,}".replace(",", " "))
        st.dataframe(_series_to_rows(annuaire.get("sexes", {})), use_container_width=True, hide_index=True)
        st.dataframe(_series_to_rows(annuaire.get("tranches_effectifs", {})), use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Population / couts pathologies (effectifs.csv)")
        if int(effectifs.get("rows", 0)) == 0:
            st.warning("Aucune ligne exploitable trouvee dans effectifs.csv pour ce departement.")
        else:
            st.dataframe(_series_to_rows(effectifs.get("ages", {})), use_container_width=True, hide_index=True)
            st.dataframe(_series_to_rows(effectifs.get("sexes", {})), use_container_width=True, hide_index=True)
            st.dataframe(_series_to_rows(effectifs.get("pathologies", {})), use_container_width=True, hide_index=True)
            st.metric("Cout observe (somme)", f"{float(effectifs.get('cout_total', 0) or 0):,.0f} EUR".replace(",", " "))

    st.markdown("### Prevision de cout annuel")
    p1, p2, p3 = st.columns(3)
    p1.metric("Scenario bas", f"{float(projection.get('low', 0) or 0):,.0f} EUR".replace(",", " "))
    p2.metric("Scenario central", f"{float(projection.get('expected', 0) or 0):,.0f} EUR".replace(",", " "))
    p3.metric("Scenario haut", f"{float(projection.get('high', 0) or 0):,.0f} EUR".replace(",", " "))
    st.caption("Projection indicative basee sur mortalite + cout observe (si present). A raffiner avec un modele metier.")


try:
    api_get("/health")
    geojson_dep = load_geojson_dep()
    geojson_reg = _filter_metropole_regions_geojson(load_geojson_regions())
    regions_rows = [
        row for row in load_regions_analytics()
        if row.get("region") and row.get("region") not in DROM_REGION_NAMES
    ]
except RuntimeError as exc:
    st.error(str(exc))
    st.info("Commande de correction: make deploy-api")
    st.stop()
except requests.RequestException as exc:
    st.error(f"API inaccessible ({API_BASE_URL}): {exc}")
    st.stop()

with st.sidebar:
    st.subheader("Configuration")
    st.code(API_BASE_URL)

sidebar_choices = ["France entiere"] + sorted([row.get("region") for row in regions_rows if row.get("region")])
default_region = st.session_state.selected_region if st.session_state.selected_region in sidebar_choices else "France entiere"
region_choice = st.sidebar.selectbox(
    "Choisir une region",
    sidebar_choices,
    index=sidebar_choices.index(default_region),
)
if region_choice == "France entiere":
    if st.session_state.selected_region is not None:
        st.session_state.selected_region = None
        st.session_state.selected_dep = None
else:
    if st.session_state.selected_region != region_choice:
        st.session_state.selected_region = region_choice
        st.session_state.selected_dep = None

if st.session_state.selected_region is None:
    fig_region = px.choropleth(
        regions_rows,
        geojson=geojson_reg,
        locations="region",
        featureidkey="properties.nom",
        color="taux_premature",
        color_continuous_scale="YlOrRd",
        hover_name="region",
        hover_data={"deces_2024": ":,.0f", "taux_premature": ":.2f"},
        title="Cliquez une region",
    )
    fig_region.update_geos(fitbounds="locations", visible=False)

    event = st.plotly_chart(fig_region, key="map_regions", on_select="rerun", use_container_width=True)
    clicked_region = _selected_location(event)
    if clicked_region and clicked_region != st.session_state.selected_region:
        st.session_state.selected_region = clicked_region
        st.session_state.selected_dep = None
        st.write(f"Region cliquee: {clicked_region}")
        st.rerun()
else:
    region = st.session_state.selected_region
    st.subheader(f"Region selectionnee: {region}")
    st.write(f"Region cliquee: {region}")

    region_deps = load_region_departments(region)
    allowed_dep_codes = {
        str(row.get("code_dep", "")).strip().upper()
        for row in region_deps
        if row.get("code_dep")
    }
    geojson_dep_region = _filter_metropole_departments_geojson(
        geojson_dep,
        allowed_codes=allowed_dep_codes,
    )

    fig_dep = px.choropleth(
        region_deps,
        geojson=geojson_dep_region,
        locations="code_dep",
        featureidkey="properties.code",
        color="taux_premature",
        color_continuous_scale="YlOrRd",
        hover_name="departement",
        hover_data={"deces_2024": ":,.0f", "taux_premature": ":.2f"},
        title="Cliquez un departement",
    )
    fig_dep.update_geos(fitbounds="locations", visible=False)

    dep_event = st.plotly_chart(fig_dep, key="map_deps", on_select="rerun", use_container_width=True)
    clicked_dep = _selected_location(dep_event)
    if clicked_dep and clicked_dep != st.session_state.selected_dep:
        st.session_state.selected_dep = clicked_dep

    manual_dep = st.selectbox(
        "Ou selection manuelle du departement",
        options=[""] + sorted([row.get("code_dep") for row in region_deps if row.get("code_dep")]),
        format_func=lambda x: "Choisir..." if x == "" else x,
    )
    if manual_dep:
        st.session_state.selected_dep = manual_dep

    if st.session_state.selected_dep:
        render_department_details(dep_code=st.session_state.selected_dep)

    if st.button("Retour a la carte des regions"):
        st.session_state.selected_region = None
        st.session_state.selected_dep = None
        st.rerun()
