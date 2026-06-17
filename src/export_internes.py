#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export des DataFrames internes (issus des loaders pivot) vers les 3 CSV
historiques consommés par ``report_builder`` (intermédiaire CSV conservé : faible
risque, préserve ``run_reports.py --no-data``).

    exporter_csv(dossier_data="data", fictif=True) -> None

écrit, en ÉCRASANT volontairement les fichiers de l'ancien pipeline :
    aphp_data.csv       (df_aphp        — pivot_loader)
    survival_data.csv   (df_survie      — pivot_loader, schéma long stade/population)
    regional_data.csv   (df_regional    — regional_loader)

NB survie : les fichiers OECI ne fournissent la survie qu'au grain ORGANE et au
GRAND TOTAL (AP-HP/GHU Total). Or les rapports APPAREIL interrogent la survie au
niveau appareil (organe="TOTAL"). On reconstruit donc ces lignes appareil par
agrégation pondérée des organes — comme l'ancien ``generate_survival_data`` les
produisait directement. L'agrégation se fait PAR (annee, entite, appareil, stade,
population) : la dimension ``population`` est conservée dans la clé, jamais
écrasée (sinon double comptage des effectifs tous/nouveaux).
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from pivot_loader import charger_oeci, charger_delais_hopitaux   # noqa: E402
from regional_loader import charger_regional   # noqa: E402
from referentiels import ANNEE_MIN, ANNEE_MAX  # noqa: E402

# Gabarits réels (format réel, vides pour l'instant) : versionnés dans templates/.
TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")


def _survie_niveau_appareil(df_survie):
    """Reconstruit les lignes de survie au niveau APPAREIL (organe='TOTAL') par
    agrégation pondérée des lignes organe. Clé incluant ``population`` (pas de
    mélange tous/nouveaux). Renvoie df_survie augmenté de ces lignes.

    Pondération NaN-safe : pour CHAQUE mesure (survie_1an, survie_5ans) séparément,
    le poids est la somme de ``nb_patients_stade`` sur les seules lignes où la mesure
    ET le poids sont numériques. Moyenne = NaN (vide) si aucun poids valide — on ne
    force PAS 0 et une survie masquée (NaN) ne biaise pas le dénominateur."""
    organe = df_survie[df_survie["organe"] != "TOTAL"].copy()
    if organe.empty:
        return df_survie
    cle = ["annee", "entite", "appareil", "stade", "population"]
    # Les mesures sont déjà numériques (coercées dans pivot_loader) : une valeur
    # masquée vaut NaN. Numérateur = mesure×nb : NaN sur les lignes masquées, IGNORÉ
    # par la somme groupby (skipna) → identique à l'ancien code quand rien n'est
    # masqué. Dénominateur NaN-safe : nb seulement là où la mesure est non-NaN (0
    # sinon) → une survie masquée ne biaise plus le poids.
    organe["_w1"] = organe["survie_1an"] * organe["nb_patients_stade"]
    organe["_w5"] = organe["survie_5ans"] * organe["nb_patients_stade"]
    organe["_n1"] = organe["nb_patients_stade"].where(organe["survie_1an"].notna(), 0)
    organe["_n5"] = organe["nb_patients_stade"].where(organe["survie_5ans"].notna(), 0)
    g = organe.groupby(cle, as_index=False).agg(
        nb_patients_stade=("nb_patients_stade", "sum"),
        _w1=("_w1", "sum"), _n1=("_n1", "sum"),
        _w5=("_w5", "sum"), _n5=("_n5", "sum"),
    )
    # Moyenne = Σ(mesure×nb)/Σnb_valide ; ``.where(>0)`` → NaN si aucun poids valide
    # (pas de 0 forcé, round-safe ; surtout PAS ``replace(0, pd.NA)`` qui ferait
    # planter ``.round`` sur un groupe entièrement masqué). Arrondi via le ``round``
    # de Python (et non numpy) pour rester bit-identique à l'ancien code sur les ties
    # d'arrondi exacts (ex. 34.15 → 34.1), tout en préservant les NaN.
    def _round1(serie):
        return serie.map(lambda x: round(float(x), 1) if pd.notna(x) else x)
    g["survie_1an"] = _round1(g["_w1"] / g["_n1"].where(g["_n1"] > 0))
    g["survie_5ans"] = _round1(g["_w5"] / g["_n5"].where(g["_n5"] > 0))
    g["organe"] = "TOTAL"
    g = g[df_survie.columns]
    return pd.concat([df_survie, g], ignore_index=True)


def _filtrer_periode(df):
    """Restreint un DataFrame aux années ANNEE_MIN..ANNEE_MAX (bornes incluses).
    Sans effet si la colonne ``annee`` est absente."""
    if "annee" not in df.columns:
        return df
    annee = pd.to_numeric(df["annee"], errors="coerce")
    return df[(annee >= ANNEE_MIN) & (annee <= ANNEE_MAX)]


def exporter_csv(dossier_data="data", fictif=True, dossier_source=None):
    """Lit les xlsx (fictif → ``data/*_fictif.xlsx`` ; réel → gabarits ``templates/``)
    et écrit les 3 CSV internes dans ``dossier_data``. ``dossier_source`` force le
    répertoire des xlsx sources (défaut : data/ en fictif, templates/ en réel)."""
    if dossier_source is None:
        dossier_source = dossier_data if fictif else TEMPLATES
    os.makedirs(dossier_data, exist_ok=True)
    print(f"Export interne (fictif={fictif}) : source {dossier_source}/ → {dossier_data}/")
    df_aphp, df_survie = charger_oeci(dossier_source, fictif=fictif)
    df_regional = charger_regional(dossier_source, fictif=fictif)
    df_delais_hop = charger_delais_hopitaux(dossier_source, fictif=fictif)

    # Alerte si l'extrait régional est encore un gabarit VIDE (dimensions présentes,
    # mesures toutes nulles) : les sections « Contexte régional » seront masquées par
    # report_builder (cf. regional_disponible). Signalé ici pour ne pas produire un
    # dashboard silencieusement amputé sans trace dans les logs.
    mes_reg = ["nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
               "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie",
               "nb_sejours_palliatifs"]
    cols_reg = [c for c in mes_reg if c in df_regional.columns]
    if cols_reg and float(df_regional[cols_reg].to_numpy().sum()) == 0:
        print("  ⚠ Régional : mesures entièrement nulles (extrait canceroBR non rempli) "
              "→ sections « Contexte régional » MASQUÉES dans les rapports.")

    df_survie = _survie_niveau_appareil(df_survie)

    # Restriction de la période affichée (prod) : ANNEE_MIN..ANNEE_MAX inclus.
    # Le régional source couvre 2016-2025 ; on coupe avant d'écrire les CSV.
    df_aphp       = _filtrer_periode(df_aphp)
    df_survie     = _filtrer_periode(df_survie)
    df_regional   = _filtrer_periode(df_regional)
    df_delais_hop = _filtrer_periode(df_delais_hop)
    print(f"  Période restreinte à {ANNEE_MIN}-{ANNEE_MAX}")

    chemins = {
        "aphp_data.csv": df_aphp,
        "survival_data.csv": df_survie,
        "regional_data.csv": df_regional,
        "delais_hopitaux_data.csv": df_delais_hop,
    }
    for nom, df in chemins.items():
        out = os.path.join(dossier_data, nom)
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  → {nom:<20} {len(df):>7,} lignes, {len(df.columns)} colonnes")
    return None


if __name__ == "__main__":
    exporter_csv("data", fictif=True)

    # contrôle rapide du schéma de survie écrit
    surv = pd.read_csv(os.path.join("data", "survival_data.csv"))
    print("\nsurvival_data.csv :")
    print("  colonnes :", list(surv.columns))
    print("  stade :", sorted(surv["stade"].dropna().unique().tolist()))
    print("  population :", sorted(surv["population"].dropna().unique().tolist()))
    print("  lignes appareil (organe=TOTAL, appareil≠TOTAL) :",
          int(((surv["organe"] == "TOTAL") & (surv["appareil"] != "TOTAL")).sum()))
