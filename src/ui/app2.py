# app.py
# Front Streamlit : consomme l'API FastAPI et affiche le dashboard.
# Aucune logique de calcul ici — tout vient du JSON retourné par l'API.

import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# ─── Configuration ─────────────────────────────────────────────────────────────
API_URL = "http://localhost:8001"  # URL de l'API FastAPI

st.set_page_config(page_title="Dashboard santé", layout="centered")


# ─── Fonctions d'appel API ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache 5 minutes — évite de rappeler l'API à chaque interaction
def fetch_data(region: int, annee: int) -> dict:
    """Appelle l'API et retourne le JSON. Lève une exception si l'API est indisponible."""
    try:
        response = requests.get(
            f"{API_URL}/region/{region}",
            params={"annee": annee},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except ValueError:
            detail = e.response.text or str(e)
        st.error(f"Erreur API : {detail}")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"Erreur API : {e.response.json().get('detail', str(e))}")
        st.stop()


@st.cache_data(ttl=300)
def fetch_annees(region: int) -> list:
    """Récupère les années disponibles pour une région."""
    try:
        r = requests.get(f"{API_URL}/region/{region}/annees", timeout=10)
        r.raise_for_status()
        return r.json()["annees"]
    except Exception:
        return list(range(2015, 2024))  # Fallback si la route est indisponible


# ─── Sidebar : sélection région / année ───────────────────────────────────────
with st.sidebar:
    st.markdown("### Paramètres")
    region = st.number_input("Code région", min_value=1, max_value=99, value=32, step=1)
    annees_dispo = fetch_annees(region)
    annee = st.selectbox("Année de référence", options=annees_dispo, index=len(annees_dispo) - 1)

# ─── Chargement des données ────────────────────────────────────────────────────
data = fetch_data(region=region, annee=annee)

df_serie  = pd.DataFrame(data["serie_temporelle"])
df_top    = pd.DataFrame(data["top_pathologies"])
df_age    = pd.DataFrame(data["depenses_par_age"])
df_sexe   = pd.DataFrame(data["depenses_par_sexe"])
metric    = data["metric"]

# ─── Titre ────────────────────────────────────────────────────────────────────
st.title(f"Bilan santé — Région {region}")

# ─── Bloc 1 : métrique + courbe temporelle ────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.metric(
        label=f"Dépenses {metric['annee']}",
        value=f"{metric['depense_totale'] / 1e9:.3f} Md",
        delta=f"{metric['yoy_pct']}%" if metric["yoy_pct"] is not None else "NA",
        delta_color="inverse",
    )

with col2:
    fig = px.line(df_serie, x="annee", y="depense")
    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False, visible=False)
    fig.update_layout(height=120, margin=dict(l=0, r=0, t=10, b=10), showlegend=False)
    fig.update_traces(hovertemplate="<b>Année %{x}</b><br>Dépense %{y:,.0f}€")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─── Bloc 2 : top 5 pathologies ───────────────────────────────────────────────
st.markdown("###### Top 5 des pathologies les plus coûteuses")

df_top_sorted = df_top.sort_values("depense", ascending=True)
fig = px.bar(
    df_top_sorted,
    x="depense", y="patho",
    orientation="h",
    text="patho",
    color="depense",
    color_continuous_scale="teal",
)
fig.update_layout(
    coloraxis_showscale=False,
    showlegend=False,
    height=300,
    margin=dict(l=0, r=0, t=10, b=10),
)
fig.update_traces(
    hovertemplate="<b>%{y}</b><br>Dépense : %{x:,.0f}€",
    textposition="inside",
    insidetextanchor="start",
    marker=dict(cornerradius=10),
)
fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─── Bloc 3 : dépenses par âge ────────────────────────────────────────────────
st.markdown("###### Dépenses par âge")

pathos = df_age["patho"].unique().tolist()
options = ["Total"] + pathos
selected_patho = st.segmented_control("Pathologie", options=options, default="Total")

df_pie = (
    df_age if selected_patho == "Total"
    else df_age[df_age["patho"] == selected_patho]
)
df_pie = df_pie.groupby("age", as_index=False)["depense"].sum()

fig = px.pie(
    df_pie,
    names="age", values="depense",
    hole=0.4,
    color_discrete_sequence=px.colors.sequential.Teal,
)
fig.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    margin=dict(l=10, r=10, t=40, b=40),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─── Bloc 4 : dépenses par sexe ───────────────────────────────────────────────
st.markdown("###### Dépenses par sexe")

fig = px.bar(
    df_sexe,
    x="patho", y="depense",
    color="sexe",
    barmode="group",
    text_auto=".2s",
    color_discrete_sequence=px.colors.sequential.Teal,
)
fig.update_layout(
    xaxis_title=None,
    yaxis_title=None,
    legend_title_text=None,
    yaxis_tickformat=",.0f",
    margin=dict(l=20, r=20, t=40, b=20),
)
fig.update_traces(
    marker=dict(cornerradius=10),
    hovertemplate="%{fullData.name}<br>Dépense : %{y:,.0f} €<extra></extra>",
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})