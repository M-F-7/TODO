import os

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard santé", layout="centered") 

st.title("Bilan santé prévention - Les Hauts de France")

col1, col2 = st.columns([1, 2])

# -----------------------
# TEXTE DEPENSES 2023 (gauche)
# -----------------------
with col1:
    st.metric(
        label="Dépenses 2023",
        value="1,741 Md",
        delta="-20.66%",
        delta_color="inverse"
    )

# -----------------------
# DATA DEPENSES 2023
# -----------------------
data = pd.DataFrame({
    "annee": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "depense": [1165317843, 1424014090, 1147577877, 1248775184, 4790885515, 5156946564, 2216712546, 2195202680, 1741667768]
})

# -----------------------
# GRAPH DEPENSES 2023 (droite)
# -----------------------
series = ["depense"]

fig = px.line(
    data,
    x=data["annee"],
    y=series
)

fig.update_xaxes(showgrid=False, visible=False)
fig.update_yaxes(showgrid=False, visible=False)

fig.update_layout(
    height=120,  # clé pour aligner avec le texte
    margin=dict(l=0, r=0, t=10, b=10),
    showlegend=False
)

# legende
fig.update_traces(
    hovertemplate="<b>Année %{x}</b><br>Dépense %{y:,.0f}€",
)

with col2:
    st.plotly_chart(
    fig,
    width="stretch",
    config={"displayModeBar": False}
)

col1, col2 = st.columns([1, 2])

# -----------------------
# BILAN (gauche)
# -----------------------
with col1:
    st.markdown("###### Top 5 des preventions a prevoir")
    st.info("Les personnes de X a X  pour la pathologie X")
    st.info("Les personnes de X a X  pour la pathologie X")
    st.info("Les personnes de X a X  pour la pathologie X")
    st.info("Les personnes de X a X  pour la pathologie X")
    st.info("Les personnes de X a X  pour la pathologie X")

# -----------------------
# CARTE
# -----------------------
import folium
from streamlit_folium import st_folium
import requests
import json
from shapely.geometry import shape, box
from shapely.ops import unary_union

with col2:
    st.markdown("###### Taux de mortalité prématurée")

departements_hdf = ["02", "59", "60", "62", "80"]

data = pd.DataFrame({
    "code": departements_hdf,
    "nom": ["Aisne", "Nord", "Oise", "Pas-de-Calais", "Somme"],
    "taux": [3.5, 4.2, 2.8, 3.9, 3.1]
})

# GeoJSON
url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
geojson_complet = requests.get(url).json()

geojson = {
    "type": "FeatureCollection",
    "features": [
        f for f in geojson_complet["features"]
        if f["properties"]["code"] in departements_hdf
    ]
}

# Masque
shapes = [shape(f["geometry"]) for f in geojson["features"]]
region = unary_union(shapes)
monde = box(-180, -90, 180, 90)
masque = monde.difference(region)

# Conversion correcte en GeoJSON
masque_geojson = {
    "type": "Feature",
    "geometry": masque.__geo_interface__,
    "properties": {}
}

m = folium.Map(
    location=[50.2, 2.5],
    zoom_start=7,
    tiles="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
    attr="CartoDB",
    zoom_control=False,        # cache les boutons +/-
    scrollWheelZoom=False,     # désactive le zoom à la molette
    dragging=False,            # désactive le déplacement
    doubleClickZoom=False,     # désactive le zoom au double-clic
    touchZoom=False,           # désactive le zoom tactile
)

# Masque blanc
folium.GeoJson(
    data=masque_geojson,
    style_function=lambda x: {
        "fillColor": "white",
        "fillOpacity": 0.85,
        "color": "white",
        "weight": 0
    }
).add_to(m)

# Choropleth
folium.Choropleth(
    geo_data=geojson,
    data=data,
    columns=["code", "taux"],
    key_on="feature.properties.code",
    fill_color="Greens",
    fill_opacity=0.8,
    line_opacity=0.5,
    legend_name=None,
).add_to(m)

with col2:
    st_folium(
    m,
    use_container_width=True,
    height=500,
    returned_objects=[],       # désactive les callbacks inutiles
    zoom=7,
    center=[50.2, 2.5],
)

# -----------------------
# DATA DEPENSES PATHOLOGIES
# -----------------------
data = pd.DataFrame({
    "patho": ["Hospitalisations hors pathologies repérées", "Cancers", "Maladies inflammatoires ou rares ou infection VIH", "Traitements du risque vasculaire (hors patholo)", "Maladies cardioneurovasculaires"],
    "depense": [428194838, 247756431, 185392052, 100615114, 92894924]
})

# -----------------------
# GRAPH DEPENSES PATHOLOGIES (droite)
# -----------------------
st.markdown("###### Top 5 des pathologies les plus couteuses")

data_sorted = data.sort_values("depense", ascending=True)  # ascending=True car l'axe y est inversé dans plotly

fig = px.bar(
    data_sorted,
    x="depense",
    y="patho",
    orientation="h",
    text="patho",
    color="depense",
    color_continuous_scale="teal"
)

fig.update_layout(
    coloraxis_showscale=False,
    showlegend=False,
    height=300,
    margin=dict(l=0, r=0, t=10, b=10),
)

fig.update_traces(
    hovertemplate="<b>%{y}</b><br>Dépense : %{x}€",
    textposition="inside",
    insidetextanchor="start",
    marker=dict(cornerradius=10)
)

fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)

st.plotly_chart(
    fig,
    width="stretch",
    config={"displayModeBar": False}
)

# -----------------------
# DATA DEPENSES AGE
# -----------------------
data = pd.DataFrame([
    # ---------------- ALD ----------------
    ("00-04","ALD autres causes",224997),
    ("05-09","ALD autres causes",272595),
    ("10-14","ALD autres causes",325634),
    ("15-19","ALD autres causes",352531),
    ("20-24","ALD autres causes",278942),
    ("25-29","ALD autres causes",227868),
    ("30-34","ALD autres causes",253405),
    ("35-39","ALD autres causes",317625),
    ("40-44","ALD autres causes",347091),
    ("45-49","ALD autres causes",371721),
    ("50-54","ALD autres causes",474775),
    ("55-59","ALD autres causes",548213),
    ("60-64","ALD autres causes",682244),
    ("65-69","ALD autres causes",796934),
    ("70-74","ALD autres causes",893944),
    ("75-79","ALD autres causes",942902),
    ("80-84","ALD autres causes",739060),
    ("85-89","ALD autres causes",734829),
    ("90-94","ALD autres causes",502730),
    ("95+","ALD autres causes",194020),

    # ---------------- CANCERS ----------------
    ("00-04","Cancers",210404),
    ("05-09","Cancers",355514),
    ("10-14","Cancers",344093),
    ("15-19","Cancers",385784),
    ("20-24","Cancers",639656),
    ("25-29","Cancers",1048911),
    ("30-34","Cancers",1489810),
    ("35-39","Cancers",2350119),
    ("40-44","Cancers",3128778),
    ("45-49","Cancers",4092997),
    ("50-54","Cancers",6659492),
    ("55-59","Cancers",9249238),
    ("60-64","Cancers",13090797),
    ("65-69","Cancers",16624473),
    ("70-74","Cancers",19611588),
    ("75-79","Cancers",18376644),
    ("80-84","Cancers",11241056),
    ("85-89","Cancers",9258221),
    ("90-94","Cancers",4489550),
    ("95+","Cancers",1205712),

    # ---------------- DIABETE ----------------
    ("00-04","Diabète",1762),
    ("05-09","Diabète",9711),
    ("10-14","Diabète",18234),
    ("15-19","Diabète",26716),
    ("20-24","Diabète",34543),
    ("25-29","Diabète",46016),
    ("30-34","Diabète",67733),
    ("35-39","Diabète",104939),
    ("40-44","Diabète",165666),
    ("45-49","Diabète",263229),
    ("50-54","Diabète",449014),
    ("55-59","Diabète",678684),
    ("60-64","Diabète",936545),
    ("65-69","Diabète",1125280),
    ("70-74","Diabète",1198094),
    ("75-79","Diabète",970309),
    ("80-84","Diabète",541251),
    ("85-89","Diabète",382469),
    ("90-94","Diabète",179679),
    ("95+","Diabète",40771),

    # ---------------- COVID ----------------
    ("00-04","Covid-19",12567),
    ("05-09","Covid-19",443),
    ("10-14","Covid-19",282),
    ("15-19","Covid-19",362),
    ("20-24","Covid-19",644),
    ("25-29","Covid-19",846),
    ("30-34","Covid-19",886),
    ("35-39","Covid-19",1168),
    ("40-44","Covid-19",1531),
    ("45-49","Covid-19",2094),
    ("50-54","Covid-19",3424),
    ("55-59","Covid-19",5236),
    ("60-64","Covid-19",8015),
    ("65-69","Covid-19",11560),
    ("70-74","Covid-19",18407),
    ("75-79","Covid-19",21629),
    ("80-84","Covid-19",22918),
    ("85-89","Covid-19",29765),
    ("90-94","Covid-19",23925),
    ("95+","Covid-19",8861),

    # ---------------- CARDIO ----------------
    ("00-04","Cardio-neurovasculaire",14105),
    ("05-09","Cardio-neurovasculaire",15610),
    ("10-14","Cardio-neurovasculaire",11588),
    ("15-19","Cardio-neurovasculaire",24044),
    ("20-24","Cardio-neurovasculaire",41414),
    ("25-29","Cardio-neurovasculaire",66116),
    ("30-34","Cardio-neurovasculaire",103454),
    ("35-39","Cardio-neurovasculaire",225054),
    ("40-44","Cardio-neurovasculaire",427810),
    ("45-49","Cardio-neurovasculaire",891246),
    ("50-54","Cardio-neurovasculaire",1887761),
    ("55-59","Cardio-neurovasculaire",3469430),
    ("60-64","Cardio-neurovasculaire",5314517),
    ("65-69","Cardio-neurovasculaire",7032276),
    ("70-74","Cardio-neurovasculaire",7785158),
    ("75-79","Cardio-neurovasculaire",6713165),
    ("80-84","Cardio-neurovasculaire",4487804),
    ("85-89","Cardio-neurovasculaire",4280274),
    ("90-94","Cardio-neurovasculaire",2678536),
    ("95+","Cardio-neurovasculaire",953893),

], columns=["age", "patho", "depense"])


# -----------------------
# GRAPH DEPENSES AGE (gauche)
# -----------------------
st.markdown("###### Depense par âge")

pathos = data["patho"].unique().tolist()
options = ["Total"] + pathos

selected_patho = st.segmented_control(
    "Pathologie",
    options=options,
    default="Total"
)

if selected_patho == "Total":
    df_work = data
else:
    df_work = data[data["patho"] == selected_patho]

df_pie = df_work.groupby("age", as_index=False)["depense"].sum()

fig = px.pie(
    df_pie,
    names="age",
    values="depense",
    hole=0.4,
    color_discrete_sequence=px.colors.sequential.Teal
)

fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5
    ),
    margin=dict(l=10, r=10, t=40, b=40)
)

st.plotly_chart(
    fig,
    width="stretch",
    config={"displayModeBar": False}
)

# -----------------------
# DATA DEPENSES SEXE
# -----------------------
df = pd.DataFrame([
    ("Cancers", "Homme", 1200000),
    ("Cancers", "Femme", 1350000),
    ("Diabète", "Homme", 450000),
    ("Diabète", "Femme", 520000),
    ("Cardio", "Homme", 980000),
    ("Cardio", "Femme", 870000),
], columns=["patho", "sexe", "depense"])

# -----------------------
# GRAPH DEPENSES SEXE
# -----------------------
st.markdown("###### Depense par sexe")

fig = px.bar(
    df,
    x="patho",
    y="depense",
    color="sexe",
    barmode="group",   # 👈 côte à côte
    text_auto=".2s",   # labels sur les barres
    color_discrete_sequence=px.colors.sequential.Teal
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
    hovertemplate=
         "%{fullData.name}<br>" +
        "Dépense : %{y:,.0f} €" +
        "<extra></extra>"
)

st.plotly_chart(
    fig,
    width="stretch",
    config={"displayModeBar": False}
)