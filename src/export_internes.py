#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Écriture du fichier pivot LONG unique ``data/donnees.csv`` (cf.
contrat_donnees_pivot.md).

L'INGESTION (lecture des vrais fichiers / fictifs, mapping vers le format long,
reconstruction survie, filtre de période) est faite par ``chargeur_long`` — moteur
générique piloté par ``docs/descriptif_sources.yaml``. Ce module n'est plus qu'un
mince point d'entrée : ``charger_long`` → écriture de ``donnees.csv`` (+ une alerte
si l'extrait régional est encore vide).

    exporter_csv(dossier_data="data", fictif=True) -> None
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from chargeur_long import charger_long   # noqa: E402

# Mesures régionales : sert à détecter un extrait canceroBR encore VIDE.
_MESURES_REGIONAL = ["nb_patients", "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
                     "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]


def exporter_csv(dossier_data="data", fictif=True, dossier_source=None):
    """Ingère les sources (``fictif`` → ``*_fictif.xlsx`` ; réel → fichiers sans
    ``_fictif``, dans ``data/``) via ``chargeur_long`` et écrit ``donnees.csv`` dans
    ``dossier_data``. ``dossier_source`` force le répertoire des sources (défaut :
    ``dossier_data``)."""
    if dossier_source is None:
        dossier_source = dossier_data
    os.makedirs(dossier_data, exist_ok=True)
    print(f"Ingestion (fictif={fictif}) : {dossier_source}/ → {dossier_data}/donnees.csv")
    long = charger_long(dossier_source, fictif=fictif)

    # Alerte si l'extrait régional est encore un gabarit VIDE (dimensions présentes,
    # mesures toutes nulles) : report_builder masque alors les sections « Contexte
    # régional » (cf. regional_disponible) — on le trace pour ne pas amputer le
    # dashboard silencieusement.
    bn = long[(long["source"] == "BN") & (long["variable"].isin(_MESURES_REGIONAL))]
    if not bn.empty and float(pd.to_numeric(bn["valeur"], errors="coerce").fillna(0).sum()) == 0:
        print("  ⚠ Régional : mesures entièrement nulles (extrait canceroBR non rempli) "
              "→ sections « Contexte régional » MASQUÉES dans les rapports.")

    out = os.path.join(dossier_data, "donnees.csv")
    long.to_csv(out, index=False, encoding="utf-8")
    print(f"  → donnees.csv  {len(long):>9,} lignes · "
          f"{long['variable'].nunique()} variables · sources {sorted(long['source'].unique())}")
    return None


if __name__ == "__main__":
    exporter_csv("data", fictif=True)
