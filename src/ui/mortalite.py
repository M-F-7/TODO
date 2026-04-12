import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


st.set_page_config(layout="wide", page_title="Pilotage des couts sante")
st.title("Carte France interactive pour prevision des couts")
st.caption("Cliquez une region, puis un departement pour afficher les details (ages, sexes, pathologies, couts).")

DATASETS_DIR = Path("datasets")

if "selected_region" not in st.session_state:
    st.session_state.selected_region = None
if "selected_dep" not in st.session_state:
    st.session_state.selected_dep = None


REGIONS = {
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Bretagne": ["22", "29", "35", "56"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Corse": ["2A", "2B"],
}
DEPARTMENT_TO_REGION = {dep: reg for reg, deps in REGIONS.items() for dep in deps}


def _clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False).str.replace("\u202f", "", regex=False),
        errors="coerce",
    )


def _extract_dep_code(value: object) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip().upper()
    if not raw:
        return None

    if raw.startswith("2A") or raw.startswith("2B"):
        return raw[:2]
    if raw.startswith("97"):
        return raw[:3]

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 2:
        return digits[:2].zfill(2)
    return None


def _find_col(columns: list[str], patterns: list[str]) -> str | None:
    lowered = {c.lower().strip(): c for c in columns}
    for pattern in patterns:
        regex = re.compile(pattern)
        for col_lower, original in lowered.items():
            if regex.search(col_lower):
                return original
    return None


@st.cache_data
def load_mortality_data() -> pd.DataFrame:
    path = DATASETS_DIR / "Taux_de_mortalite.csv"
    df = pd.read_csv(path, sep=",", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"Unnamed: 0": "code_dep", "Departement": "departement", "Département": "departement"})
    df["code_dep"] = df["code_dep"].astype(str).str.strip().str.upper()

    mappings = {
        "Taux de mortalité standard. des 0-64 ans en 2024 (prématuré) (en ‰)": "taux_premature",
        "Taux de mortalite standard. des 0-64 ans en 2024 (premature) (en ‰)": "taux_premature",
        "Taux brut de mortalité en 2024 (en ‰)": "taux_brut",
        "Taux brut de mortalité des femmes en 2024 (en ‰)": "taux_femmes",
        "Taux brut de mortalité des hommes en 2024 (en ‰)": "taux_hommes",
        "Nombre de décès domiciliés en 2024": "deces_2024",
    }
    df = df.rename(columns=mappings)

    for metric in ["taux_premature", "taux_brut", "taux_femmes", "taux_hommes", "deces_2024"]:
        if metric in df.columns:
            df[metric] = _clean_numeric(df[metric])

    df["region"] = df["code_dep"].map(DEPARTMENT_TO_REGION)
    return df


@st.cache_data
def load_annuaire_health_data() -> pd.DataFrame:
    path = DATASETS_DIR / "annuaire-des-entreprises-etablissements-08_04_2026.csv"
    usecols = [
        "codeCommuneEtablissement",
        "sexeUniteLegale",
        "trancheEffectifsEtablissement",
        "activitePrincipaleEtablissement",
        "activitePrincipaleNAF25Etablissement",
    ]
    df = pd.read_csv(path, usecols=usecols, dtype=str, low_memory=False)
    df.columns = df.columns.str.strip()
    df["code_dep"] = df["codeCommuneEtablissement"].map(_extract_dep_code)
    return df


@st.cache_data
def load_effectifs_data() -> pd.DataFrame:
    path = DATASETS_DIR / "effectifs.csv"
    if not path.exists():
        return pd.DataFrame()

    header = pd.read_csv(path, nrows=0, low_memory=False)
    cols = header.columns.tolist()

    dep_col = _find_col(cols, [r"code[_ ]?dep", r"depart", r"code[_ ]?commune", r"codgeo", r"dep"])
    age_col = _find_col(cols, [r"age", r"tranche", r"classe"])
    sex_col = _find_col(cols, [r"sexe", r"genre"])
    pathology_col = _find_col(cols, [r"patholog", r"affection", r"ald", r"malad", r"diagnos"])
    cost_col = _find_col(cols, [r"cout", r"co[uû]t", r"depense", r"montant", r"rembours", r"charge"])

    selected_cols = [c for c in [dep_col, age_col, sex_col, pathology_col, cost_col] if c]
    if not selected_cols:
        return pd.DataFrame()

    df = pd.read_csv(path, usecols=selected_cols, dtype=str, low_memory=False)

    renamed = {}
    if dep_col:
        renamed[dep_col] = "dep_source"
    if age_col:
        renamed[age_col] = "age"
    if sex_col:
        renamed[sex_col] = "sexe"
    if pathology_col:
        renamed[pathology_col] = "pathologie"
    if cost_col:
        renamed[cost_col] = "cout"
    df = df.rename(columns=renamed)

    if "dep_source" in df.columns:
        df["code_dep"] = df["dep_source"].map(_extract_dep_code)
    if "cout" in df.columns:
        df["cout"] = _clean_numeric(df["cout"])

    return df


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


def _cost_projection(dep_row: pd.Series, dep_effectifs: pd.DataFrame) -> dict[str, float]:
    deces = float(dep_row.get("deces_2024", 0) or 0)
    taux_premature = float(dep_row.get("taux_premature", 0) or 0)

    observed_cost = 0.0
    if not dep_effectifs.empty and "cout" in dep_effectifs.columns:
        observed_cost = float(dep_effectifs["cout"].dropna().sum())

    # Proxy simple pour un ordre de grandeur local tant qu'on n'a pas un modele complet.
    socle = observed_cost if observed_cost > 0 else deces * 12000
    pressure_factor = 1 + (taux_premature / 10)
    expected = socle * pressure_factor

    return {
        "socle": socle,
        "expected": expected,
        "low": expected * 0.9,
        "high": expected * 1.15,
    }


def render_department_details(dep_code: str, mortality_df: pd.DataFrame, annuaire_df: pd.DataFrame, effectifs_df: pd.DataFrame) -> None:
    dep_data = mortality_df[mortality_df["code_dep"] == dep_code]
    if dep_data.empty:
        st.warning("Aucune donnee trouvee pour ce departement.")
        return

    row = dep_data.iloc[0]
    st.subheader(f"Departement {dep_code} - {row.get('departement', 'N/A')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Taux premature (0-64)", f"{row.get('taux_premature', float('nan')):.2f} ‰")
    c2.metric("Taux brut", f"{row.get('taux_brut', float('nan')):.2f} ‰")
    c3.metric("Taux femmes", f"{row.get('taux_femmes', float('nan')):.2f} ‰")
    c4.metric("Taux hommes", f"{row.get('taux_hommes', float('nan')):.2f} ‰")

    deces = row.get("deces_2024")
    if pd.notna(deces):
        st.info(f"Deces domicilies 2024: {int(deces):,}".replace(",", " "))

    dep_annuaire = annuaire_df[annuaire_df["code_dep"] == dep_code]
    if not effectifs_df.empty and "code_dep" in effectifs_df.columns:
        dep_effectifs = effectifs_df[effectifs_df["code_dep"] == dep_code]
    else:
        dep_effectifs = pd.DataFrame()

    left, right = st.columns(2)

    with left:
        st.markdown("### Structures de sante (annuaire)")
        st.metric("Nb etablissements", f"{len(dep_annuaire):,}".replace(",", " "))

        if not dep_annuaire.empty:
            sexes = dep_annuaire["sexeUniteLegale"].replace({"": "ND", "[ND]": "ND"}).fillna("ND")
            sexe_dist = sexes.value_counts().rename_axis("sexe").reset_index(name="count")
            st.dataframe(sexe_dist, use_container_width=True, hide_index=True)

            effectif_dist = (
                dep_annuaire["trancheEffectifsEtablissement"]
                .replace({"": "ND", "[ND]": "ND"})
                .fillna("ND")
                .value_counts()
                .head(8)
                .rename_axis("tranche")
                .reset_index(name="count")
            )
            st.dataframe(effectif_dist, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Population / couts pathologies (effectifs.csv)")
        if dep_effectifs.empty:
            st.warning("Aucune ligne exploitable trouvee dans effectifs.csv pour ce departement.")
        else:
            if "age" in dep_effectifs.columns:
                age_dist = dep_effectifs["age"].fillna("ND").value_counts().head(12).rename_axis("age").reset_index(name="count")
                st.dataframe(age_dist, use_container_width=True, hide_index=True)

            if "sexe" in dep_effectifs.columns:
                sex_dist = dep_effectifs["sexe"].fillna("ND").value_counts().rename_axis("sexe").reset_index(name="count")
                st.dataframe(sex_dist, use_container_width=True, hide_index=True)

            if "pathologie" in dep_effectifs.columns:
                patho_dist = (
                    dep_effectifs["pathologie"]
                    .fillna("ND")
                    .value_counts()
                    .head(10)
                    .rename_axis("pathologie")
                    .reset_index(name="count")
                )
                st.dataframe(patho_dist, use_container_width=True, hide_index=True)

            if "cout" in dep_effectifs.columns:
                st.metric("Cout observe (somme)", f"{dep_effectifs['cout'].dropna().sum():,.0f} EUR".replace(",", " "))

    projection = _cost_projection(row, dep_effectifs)
    st.markdown("### Prevision de cout annuel")
    p1, p2, p3 = st.columns(3)
    p1.metric("Scenario bas", f"{projection['low']:,.0f} EUR".replace(",", " "))
    p2.metric("Scenario central", f"{projection['expected']:,.0f} EUR".replace(",", " "))
    p3.metric("Scenario haut", f"{projection['high']:,.0f} EUR".replace(",", " "))
    st.caption("Projection indicative basee sur mortalite + cout observe (si present). A raffiner avec un modele metier.")


mortality_df = load_mortality_data()
annuaire_df = load_annuaire_health_data()
effectifs_df = load_effectifs_data()
geojson_dep = load_geojson_dep()
geojson_reg = load_geojson_regions()

sidebar_choices = ["France entiere"] + sorted(mortality_df["region"].dropna().unique())
region_choice = st.sidebar.selectbox("Choisir une region", sidebar_choices)
if region_choice == "France entiere":
    st.session_state.selected_region = None
else:
    st.session_state.selected_region = region_choice
    st.session_state.selected_dep = None

if st.session_state.selected_region is None:
    region_df = mortality_df.groupby("region", as_index=False).agg(
        taux_premature=("taux_premature", "mean"),
        deces_2024=("deces_2024", "sum"),
    )

    fig_region = px.choropleth(
        region_df,
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
    if clicked_region:
        st.session_state.selected_region = clicked_region
        st.write(f"Region cliquee: {clicked_region}")
        st.rerun()

else:
    region = st.session_state.selected_region
    st.subheader(f"Region selectionnee: {region}")
    st.write(f"Region cliquee: {region}")

    region_deps = mortality_df[mortality_df["region"] == region].copy()
    fig_dep = px.choropleth(
        region_deps,
        geojson=geojson_dep,
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
    if clicked_dep:
        st.session_state.selected_dep = clicked_dep
        st.rerun()

    manual_dep = st.selectbox(
        "Ou selection manuelle du departement",
        options=[""] + sorted(region_deps["code_dep"].dropna().unique().tolist()),
        format_func=lambda x: "Choisir..." if x == "" else x,
    )
    if manual_dep:
        st.session_state.selected_dep = manual_dep

    if st.session_state.selected_dep:
        render_department_details(
            dep_code=st.session_state.selected_dep,
            mortality_df=mortality_df,
            annuaire_df=annuaire_df,
            effectifs_df=effectifs_df,
        )

    if st.button("Retour a la carte des regions"):
        st.session_state.selected_region = None
        st.session_state.selected_dep = None
        st.rerun()
