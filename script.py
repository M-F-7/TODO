# export_region.py

import io
import os
import json
import argparse
import pandas as pd
from minio import Minio

# ─── 1. Arguments ─────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Export JSON pour dashboard santé")
parser.add_argument("--region", type=int, required=True, help="Code région (ex: 32)")
parser.add_argument("--annee", type=int, default=2023, help="Année de référence (défaut: 2023)")
parser.add_argument("--output", type=str, default=None, help="Fichier de sortie (défaut: stdout)")
args = parser.parse_args()

region = args.region
annee = args.annee

# ─── 2. Connexion & chargement MinIO ──────────────────────────────────────────
client = Minio(
    "localhost:9000",
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    secure=False,
)

def load_csv(client, bucket, path):
    r = client.get_object(bucket, path)
    data = r.read()
    r.close()
    r.release_conn()
    return pd.read_csv(io.BytesIO(data), sep=';')

df_dep = load_csv(client, "datasets", "raw/effectifs.csv")
df_nat = load_csv(client, "datasets", "raw/depenses.csv")

# ─── 3. Transformations ───────────────────────────────────────────────────────
df_dep = df_dep.rename(columns={"Ntop": "Ntop_dep"})
df_nat = df_nat.rename(columns={"Ntop": "Ntop_national", "montant": "montant_national"})

for df in [df_dep, df_nat]:
    df["key"] = (
        df["annee"].astype(str) + "|" +
        df["patho_niv1"].astype(str) + "|" +
        df["patho_niv2"].astype(str) + "|" +
        df["patho_niv3"].astype(str) + "|" +
        df["top"].astype(str)
    )

df_dep["weight"] = df_dep["Ntop_dep"] / df_dep.groupby(
    ["annee", "patho_niv1", "patho_niv2", "patho_niv3", "top"]
)["Ntop_dep"].transform("sum")

df_dep["Ntop_national"] = df_dep["key"].map(df_nat.set_index("key")["Ntop_national"])
df_dep["montant_national"] = df_dep["key"].map(df_nat.set_index("key")["montant_national"])
df_dep["montant_dep"] = df_dep["weight"] * df_dep["montant_national"]
df_dep.loc[
    (df_dep["Ntop_national"].isna()) | (df_dep["Ntop_national"] == 0),
    "montant_dep"
] = 0

# ─── 4. Filtrage région ───────────────────────────────────────────────────────
df_region = df_dep[df_dep["region"] == region].copy()

if df_region.empty:
    print(json.dumps({"error": f"Aucune donnée pour la région {region}"}))
    exit(1)

df_annee = df_region[df_region["annee"] == annee].copy()

# ─── 5. Construction du JSON ──────────────────────────────────────────────────

# [1] MÉTRIQUE PRINCIPALE — dépense totale de l'année + variation YoY
#     → utilisé par st.metric() : value + delta
depenses_par_annee = (
    df_region.groupby("annee")["montant_dep"]
    .sum()
    .sort_index()
)
depense_annee = depenses_par_annee.get(annee, 0)
depense_precedente = depenses_par_annee.get(annee - 1, None)
yoy = (
    round((depense_annee - depense_precedente) / depense_precedente * 100, 2)
    if depense_precedente else None
)

metric = {
    "annee": annee,
    "depense_totale": round(depense_annee),
    "yoy_pct": yoy  # ex: -20.66 → affiché "-20.66%" dans le delta Streamlit
}

# [2] SÉRIE TEMPORELLE — dépense totale par année
#     → utilisé par le graphique px.line()
serie_temporelle = [
    {"annee": int(y), "depense": round(v)}
    for y, v in depenses_par_annee.items()
]

# [3] TOP 5 PATHOLOGIES les plus coûteuses
#     → utilisé par le graphique px.bar() horizontal
top_pathologies = (
    df_annee.groupby("patho_niv1")["montant_dep"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
    .reset_index()
    .rename(columns={"patho_niv1": "patho", "montant_dep": "depense"})
)
top_pathologies["depense"] = top_pathologies["depense"].round().astype(int)
top_pathologies_list = top_pathologies.to_dict(orient="records")

# [4] DÉPENSES PAR ÂGE × PATHOLOGIE
#     → utilisé par px.pie() avec segmented_control par pathologie
depenses_age = (
    df_annee.groupby(["cla_age_5", "patho_niv1"])["montant_dep"]
    .sum()
    .reset_index()
    .rename(columns={"cla_age_5": "age", "patho_niv1": "patho", "montant_dep": "depense"})
)
depenses_age["depense"] = depenses_age["depense"].round().astype(int)
depenses_age_list = depenses_age.to_dict(orient="records")

# [5] DÉPENSES PAR SEXE × PATHOLOGIE
#     → utilisé par px.bar() groupé homme/femme
#     Le code sexe est typiquement : 1=Homme, 2=Femme, 9=Tous sexes
sexe_labels = {1: "Homme", 2: "Femme", 9: "Tous"}
depenses_sexe = (
    df_annee[df_annee["sexe"].isin([1, 2])]  # on exclut "Tous sexes" pour le comparatif
    .groupby(["patho_niv1", "sexe"])["montant_dep"]
    .sum()
    .reset_index()
    .rename(columns={"patho_niv1": "patho", "montant_dep": "depense"})
)
depenses_sexe["sexe"] = depenses_sexe["sexe"].map(sexe_labels)
depenses_sexe["depense"] = depenses_sexe["depense"].round().astype(int)

# On garde uniquement les top 5 pathologies pour rester cohérent avec le bar chart
top5_pathos = top_pathologies["patho"].tolist()
depenses_sexe_list = (
    depenses_sexe[depenses_sexe["patho"].isin(top5_pathos)]
    .to_dict(orient="records")
)

# ─── 6. Assemblage final ──────────────────────────────────────────────────────
output = {
    "meta": {
        "region": region,
        "annee_reference": annee,
    },
    "metric": metric,                        # → st.metric()
    "serie_temporelle": serie_temporelle,    # → px.line()
    "top_pathologies": top_pathologies_list, # → px.bar() horizontal
    "depenses_par_age": depenses_age_list,   # → px.pie() + segmented_control
    "depenses_par_sexe": depenses_sexe_list, # → px.bar() groupé
}

# ─── 7. Sortie ────────────────────────────────────────────────────────────────
json_str = json.dumps(output, ensure_ascii=False, indent=2)

if args.output:
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"✓ Export JSON écrit dans {args.output}")
else:
    print(json_str)  # stdout → pipe vers un autre outil