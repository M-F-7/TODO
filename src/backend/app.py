import re
from time import time
from collections import Counter

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from minio.error import S3Error
from pandas.errors import EmptyDataError

from src.backend.minio_data import (
    get_dataset_metadata,
    get_dataset_preview,
    list_datasets,
    iter_dataset_rows,
    read_dataset,
)


app = FastAPI(title="Datasets API", version="0.1.0")


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
DROM_REGION_NAMES = {"Guadeloupe", "Martinique", "Guyane", "La Réunion", "La Reunion", "Mayotte"}
DROM_DEP_PREFIXES = ("97", "98")
CACHE_TTL_SECONDS = 300
_analytics_cache: dict[str, dict] = {}


def _cache_get(key: str):
    item = _analytics_cache.get(key)
    if not item:
        return None
    if (time() - item["at"]) > CACHE_TTL_SECONDS:
        _analytics_cache.pop(key, None)
        return None
    return item["value"]


def _cache_set(key: str, value):
    _analytics_cache[key] = {"at": time(), "value": value}


def _clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
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


def _load_mortality_df() -> pd.DataFrame:
    cached = _cache_get("mortality_df")
    if cached is not None:
        return cached

    df = read_dataset("Taux_de_mortalite.csv")
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"": "code_dep", "Unnamed: 0": "code_dep", "Departement": "departement", "Département": "departement"})
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
    for col in ["taux_premature", "taux_brut", "taux_femmes", "taux_hommes", "deces_2024"]:
        if col in df.columns:
            df[col] = _clean_numeric(df[col])

    df["region"] = df["code_dep"].map(DEPARTMENT_TO_REGION)
    df = df[df["code_dep"].notna()]
    df = df[~df["code_dep"].astype(str).str.startswith(DROM_DEP_PREFIXES)]
    df = df[df["region"].notna()]
    df = df[~df["region"].isin(DROM_REGION_NAMES)]

    _cache_set("mortality_df", df)
    return df


def _load_annuaire_all_aggregates() -> dict:
    cached = _cache_get("annuaire_all")
    if cached is not None:
        return cached

    usecols = [
        "codeCommuneEtablissement",
        "sexeUniteLegale",
        "trancheEffectifsEtablissement",
        "activitePrincipaleEtablissement",
    ]
    ann = read_dataset(
        "annuaire-des-entreprises-etablissements-08_04_2026.csv",
        usecols=usecols,
        dtype=str,
        low_memory=False,
    )
    ann["code_dep"] = ann["codeCommuneEtablissement"].map(_extract_dep_code)
    ann = ann.dropna(subset=["code_dep"])
    ann = ann[~ann["code_dep"].astype(str).str.startswith(DROM_DEP_PREFIXES)]

    out = {}
    for dep_code, dep_df in ann.groupby("code_dep"):
        out[dep_code] = {
            "etablissements": int(len(dep_df)),
            "sexes": dep_df["sexeUniteLegale"].replace({"": "ND", "[ND]": "ND"}).fillna("ND").value_counts().head(12).to_dict(),
            "tranches_effectifs": dep_df["trancheEffectifsEtablissement"].replace({"": "ND", "[ND]": "ND"}).fillna("ND").value_counts().head(12).to_dict(),
        }

    _cache_set("annuaire_all", out)
    return out


def _count_top_values(series: pd.Series, limit: int = 12) -> dict:
    return series.fillna("ND").value_counts().head(limit).to_dict()


def _load_annuaire_department_aggregate(dep: str) -> dict:
    cache_key = f"annuaire_{dep}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    usecols = [
        "codeCommuneEtablissement",
        "sexeUniteLegale",
        "trancheEffectifsEtablissement",
    ]
    ann = read_dataset(
        "annuaire-des-entreprises-etablissements-08_04_2026.csv",
        usecols=usecols,
        dtype=str,
        low_memory=False,
    )
    ann["code_dep"] = ann["codeCommuneEtablissement"].map(_extract_dep_code)
    ann = ann[ann["code_dep"] == dep]

    result = {
        "etablissements": int(len(ann)),
        "sexes": _count_top_values(ann["sexeUniteLegale"].replace({"": "ND", "[ND]": "ND"})) if not ann.empty else {},
        "tranches_effectifs": _count_top_values(ann["trancheEffectifsEtablissement"].replace({"": "ND", "[ND]": "ND"})) if not ann.empty else {},
    }
    _cache_set(cache_key, result)
    return result


def _load_effectifs_department_aggregate(dep: str) -> dict:
    cache_key = f"effectifs_{dep}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    rows = 0
    age_counts: Counter[str] = Counter()
    sex_counts: Counter[str] = Counter()
    pathology_counts: Counter[str] = Counter()
    cost_total = 0.0
    for row in iter_dataset_rows("effectifs.csv"):
        dep_value = str(row.get("dept") or row.get("dep") or row.get("code_dep") or row.get("codgeo") or "").strip()
        if dep_value != dep:
            continue

        rows += 1
        age_value = str(row.get("libelle_classe_age") or row.get("cla_age_5") or row.get("age") or row.get("tranche") or "").strip()
        sex_value = str(row.get("libelle_sexe") or row.get("sexe") or row.get("genre") or "").strip()
        pathology_value = str(row.get("patho_niv3") or row.get("patho_niv2") or row.get("patho_niv1") or row.get("pathologie") or "").strip()
        if age_value:
            age_counts.update([age_value if age_value not in {"", "[ND]"} else "ND"])
        if sex_value:
            sex_counts.update([sex_value if sex_value not in {"", "[ND]"} else "ND"])
        if pathology_value:
            pathology_counts.update([pathology_value if pathology_value not in {"", "[ND]"} else "ND"])

    result = {
        "rows": rows,
        "ages": dict(age_counts.most_common(12)),
        "sexes": dict(sex_counts.most_common(12)),
        "pathologies": dict(pathology_counts.most_common(12)),
        "cout_total": float(cost_total),
    }

    _cache_set(cache_key, result)
    return result


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


@app.get("/analytics/health/regions")
def analytics_regions() -> dict:
    try:
        df = _load_mortality_df()
        grouped = (
            df.groupby("region", as_index=False)
            .agg(
                taux_premature=("taux_premature", "mean"),
                deces_2024=("deces_2024", "sum"),
            )
            .fillna(0)
        )
        return {"items": grouped.to_dict(orient="records")}
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(
                status_code=424,
                detail="Dataset 'Taux_de_mortalite.csv' absent dans MinIO. Lancez 'make init'.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc


@app.get("/analytics/health/regions/{region}/departments")
def analytics_region_departments(region: str) -> dict:
    try:
        df = _load_mortality_df()
        region_df = df[df["region"] == region].copy()
        if region_df.empty:
            raise HTTPException(status_code=404, detail="Region not found")
        return {"items": region_df.fillna(0).to_dict(orient="records")}
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(
                status_code=424,
                detail="Dataset 'Taux_de_mortalite.csv' absent dans MinIO. Lancez 'make init'.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc


@app.get("/analytics/health/departments/{dep_code}")
def analytics_department(dep_code: str) -> dict:
    try:
        dep = dep_code.upper().strip()
        if dep.startswith(DROM_DEP_PREFIXES):
            raise HTTPException(status_code=404, detail="Department not found")

        df = _load_mortality_df()
        dep_df = df[df["code_dep"] == dep]
        if dep_df.empty:
            raise HTTPException(status_code=404, detail="Department not found")

        row = dep_df.iloc[0]
        annuaire = _load_annuaire_department_aggregate(dep)
        effectifs = _load_effectifs_department_aggregate(dep)

        deces = float(row.get("deces_2024", 0) or 0)
        taux = float(row.get("taux_premature", 0) or 0)
        observed = float(effectifs.get("cout_total", 0) or 0)
        socle = observed if observed > 0 else deces * 12000
        expected = socle * (1 + (taux / 10))

        return {
            "department": {
                "code_dep": dep,
                "departement": row.get("departement"),
                "region": row.get("region"),
                "taux_premature": float(row.get("taux_premature", 0) or 0),
                "taux_brut": float(row.get("taux_brut", 0) or 0),
                "taux_femmes": float(row.get("taux_femmes", 0) or 0),
                "taux_hommes": float(row.get("taux_hommes", 0) or 0),
                "deces_2024": int(float(row.get("deces_2024", 0) or 0)),
            },
            "annuaire": annuaire,
            "effectifs": effectifs,
            "projection": {
                "low": expected * 0.9,
                "expected": expected,
                "high": expected * 1.15,
            },
        }
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(
                status_code=424,
                detail="Dataset 'Taux_de_mortalite.csv' absent dans MinIO. Lancez 'make init'.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"MinIO error: {exc.code}") from exc
