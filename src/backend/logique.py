# logique.py
# Contient toute la logique métier : chargement MinIO, transformations pandas,
# calcul des poids et ventilation des dépenses nationales au niveau départemental.
# Ce module est appelé par api.py — il ne sait rien de FastAPI ni de Streamlit.

import io
import os
import pandas as pd
from minio import Minio
from functools import lru_cache


# ─── Client MinIO (singleton) ─────────────────────────────────────────────────
# On instancie le client une seule fois au démarrage du module.
# Les credentials sont lus depuis les variables d'environnement.
def _get_minio_client() -> Minio:
    return Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ROOT_USER"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


def _load_csv(client: Minio, bucket: str, path: str) -> pd.DataFrame:
    """Charge un CSV depuis MinIO et retourne un DataFrame pandas."""
    response = client.get_object(bucket, path)
    data = response.read()
    response.close()
    response.release_conn()
    return pd.read_csv(io.BytesIO(data), sep=";")


# ─── Chargement et préparation des données (mis en cache) ────────────────────
# @lru_cache évite de recharger et recalculer les données depuis MinIO
# à chaque requête. Le cache est invalidé au redémarrage du serveur.
@lru_cache(maxsize=1)
def _charger_donnees() -> pd.DataFrame:
    """
    Charge effectifs.csv et depenses.csv depuis MinIO,
    effectue toutes les transformations et retourne le DataFrame enrichi.
    Ce calcul est coûteux — il est exécuté une seule fois grâce au cache.
    """
    client = _get_minio_client()

    df_dep = _load_csv(client, "datasets", "raw/effectifs.csv")
    df_nat = _load_csv(client, "datasets", "raw/depenses.csv")

    # Renommage pour lever l'ambiguïté lors de la jointure
    df_dep = df_dep.rename(columns={"Ntop": "Ntop_dep"})
    df_nat = df_nat.rename(columns={
        "Ntop": "Ntop_national",
        "montant": "montant_national"
    })

    # Clé métier composite pour la jointure départements × national
    for df in [df_dep, df_nat]:
        df["key"] = (
            df["annee"].astype(str) + "|" +
            df["patho_niv1"].astype(str) + "|" +
            df["patho_niv2"].astype(str) + "|" +
            df["patho_niv3"].astype(str) + "|" +
            df["top"].astype(str)
        )

    # Poids du département : part des effectifs départementaux dans le total national
    # Formule : Ntop_dep / Σ(Ntop_dep) par groupe (annee × pathologie × top)
    df_dep["weight"] = df_dep["Ntop_dep"] / df_dep.groupby(
        ["annee", "patho_niv1", "patho_niv2", "patho_niv3", "top"]
    )["Ntop_dep"].transform("sum")

    # Jointure via dictionnaires (lookup O(1)) plutôt que pd.merge
    ntop_map = df_nat.set_index("key")["Ntop_national"].to_dict()
    montant_map = df_nat.set_index("key")["montant_national"].to_dict()

    df_dep["Ntop_national"] = df_dep["key"].map(ntop_map)
    df_dep["montant_national"] = df_dep["key"].map(montant_map)

    # Ventilation : montant_dep = poids × montant_national
    df_dep["montant_dep"] = df_dep["weight"] * df_dep["montant_national"]

    # Cas limites : clé absente ou Ntop_national nul → dépense forcée à 0
    df_dep.loc[
        (df_dep["Ntop_national"].isna()) | (df_dep["Ntop_national"] == 0),
        "montant_dep"
    ] = 0

    return df_dep


# ─── Fonction principale exposée à l'API ─────────────────────────────────────
def calculer_depenses(region: int, annee: int) -> dict:
    """
    Calcule et retourne toutes les données nécessaires au dashboard
    pour une région et une année données.

    Retourne un dict directement sérialisable en JSON par FastAPI.
    """
    df = _charger_donnees()

    # Filtrage sur la région
    df_region = df[df["region"] == region].copy()
    if df_region.empty:
        return {"error": f"Aucune donnée pour la région {region}"}

    # Filtrage sur l'année de référence
    df_annee = df_region[df_region["annee"] == annee].copy()
    if df_annee.empty:
        return {"error": f"Aucune donnée pour la région {region} en {annee}"}

    # ── 1. Métrique principale ────────────────────────────────────────────────
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
        "yoy_pct": yoy,
    }

    # ── 2. Série temporelle ───────────────────────────────────────────────────
    serie_temporelle = [
        {"annee": int(y), "depense": round(v)}
        for y, v in depenses_par_annee.items()
    ]

    # ── 3. Top 5 pathologies ──────────────────────────────────────────────────
    top_pathologies = (
        df_annee.groupby("patho_niv1")["montant_dep"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
        .rename(columns={"patho_niv1": "patho", "montant_dep": "depense"})
    )
    top_pathologies["depense"] = top_pathologies["depense"].round().astype(int)
    top5_list = top_pathologies["patho"].tolist()

    # ── 4. Dépenses par âge × pathologie ─────────────────────────────────────
    depenses_age = (
        df_annee.groupby(["cla_age_5", "patho_niv1"])["montant_dep"]
        .sum()
        .reset_index()
        .rename(columns={"cla_age_5": "age", "patho_niv1": "patho", "montant_dep": "depense"})
    )
    depenses_age["depense"] = depenses_age["depense"].round().astype(int)

    # ── 5. Dépenses par sexe × pathologie (top 5 seulement) ──────────────────
    # Codes sexe : 1 = Homme, 2 = Femme, 9 = Tous sexes (exclu du comparatif)
    sexe_labels = {1: "Homme", 2: "Femme"}
    depenses_sexe = (
        df_annee[df_annee["sexe"].isin([1, 2])]
        .groupby(["patho_niv1", "sexe"])["montant_dep"]
        .sum()
        .reset_index()
        .rename(columns={"patho_niv1": "patho", "montant_dep": "depense"})
    )
    depenses_sexe["sexe"] = depenses_sexe["sexe"].map(sexe_labels)
    depenses_sexe["depense"] = depenses_sexe["depense"].round().astype(int)
    depenses_sexe = depenses_sexe[depenses_sexe["patho"].isin(top5_list)]

    # ── Assemblage final ──────────────────────────────────────────────────────
    return {
        "meta": {"region": region, "annee_reference": annee},
        "metric": metric,
        "serie_temporelle": serie_temporelle,
        "top_pathologies": top_pathologies.to_dict(orient="records"),
        "depenses_par_age": depenses_age.to_dict(orient="records"),
        "depenses_par_sexe": depenses_sexe.to_dict(orient="records"),
    }
