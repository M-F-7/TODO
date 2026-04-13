# api.py
# Routeur FastAPI : définit les endpoints HTTP, valide les paramètres,
# appelle la logique métier et retourne le JSON.
# Ce fichier ne contient aucun calcul — il délègue tout à logique.py.

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from src.backend.logique import calculer_depenses

app = FastAPI(
    title="API Santé Régionale",
    description="Ventilation des dépenses de santé par région, pathologie, âge et sexe.",
    version="1.0.0",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Autorise Streamlit (localhost:8501) à appeler l'API depuis le navigateur.
# En production, remplace "*" par l'URL exacte de ton front.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─── Route principale ──────────────────────────────────────────────────────────
@app.get(
    "/region/{code_region}",
    summary="Données dashboard pour une région",
    response_description="JSON structuré pour alimenter tous les graphiques du dashboard",
)
def get_region(
    code_region: int,
    annee: int = Query(default=2023, ge=2015, le=2030, description="Année de référence"),
):
    """
    Retourne toutes les données nécessaires au dashboard Streamlit :
    - `metric` : dépense totale + variation YoY
    - `serie_temporelle` : évolution annuelle (graphique ligne)
    - `top_pathologies` : top 5 pathologies coûteuses (graphique barres horizontal)
    - `depenses_par_age` : répartition âge × pathologie (graphique camembert)
    - `depenses_par_sexe` : comparatif homme/femme sur le top 5 (graphique barres groupées)
    """
    result = calculer_depenses(region=code_region, annee=annee)

    # Si la logique retourne une erreur métier, on la traduit en HTTP 404
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ─── Route utilitaire : liste des années disponibles ──────────────────────────
@app.get("/region/{code_region}/annees", summary="Années disponibles pour une région")
def get_annees(code_region: int):
    """Retourne la liste des années disponibles pour une région donnée."""
    from src.backend.logique import _charger_donnees
    df = _charger_donnees()
    df_region = df[df["region"] == code_region]
    if df_region.empty:
        raise HTTPException(status_code=404, detail=f"Région {code_region} introuvable")
    annees = sorted(df_region["annee"].unique().tolist())
    return {"region": code_region, "annees": annees}


# ─── Healthcheck ───────────────────────────────────────────────────────────────
@app.get("/health", summary="Vérification que l'API est opérationnelle")
def health():
    return {"status": "ok"}
