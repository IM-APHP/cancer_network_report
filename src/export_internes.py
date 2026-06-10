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
from pivot_loader import charger_oeci          # noqa: E402
from regional_loader import charger_regional   # noqa: E402

# Gabarits réels (format réel, vides pour l'instant) : versionnés dans templates/.
TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")


def _survie_niveau_appareil(df_survie):
    """Reconstruit les lignes de survie au niveau APPAREIL (organe='TOTAL') par
    agrégation pondérée des lignes organe. Clé incluant ``population`` (pas de
    mélange tous/nouveaux). Renvoie df_survie augmenté de ces lignes."""
    organe = df_survie[df_survie["organe"] != "TOTAL"].copy()
    if organe.empty:
        return df_survie
    organe["_w1"] = organe["survie_1an"] * organe["nb_patients_stade"]
    organe["_w5"] = organe["survie_5ans"] * organe["nb_patients_stade"]
    cle = ["annee", "entite", "appareil", "stade", "population"]
    g = organe.groupby(cle, as_index=False).agg(
        nb_patients_stade=("nb_patients_stade", "sum"),
        _w1=("_w1", "sum"), _w5=("_w5", "sum"),
    )
    poids = g["nb_patients_stade"].replace(0, pd.NA)
    g["survie_1an"] = (g["_w1"] / poids).fillna(0).round(1)
    g["survie_5ans"] = (g["_w5"] / poids).fillna(0).round(1)
    g["organe"] = "TOTAL"
    g = g[df_survie.columns]
    return pd.concat([df_survie, g], ignore_index=True)


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

    df_survie = _survie_niveau_appareil(df_survie)

    chemins = {
        "aphp_data.csv": df_aphp,
        "survival_data.csv": df_survie,
        "regional_data.csv": df_regional,
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
