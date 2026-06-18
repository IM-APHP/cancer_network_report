#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration ponctuelle : 4 CSV larges historiques → ``data/donnees.csv`` (long).

Lit les anciens ``data/aphp_data.csv`` · ``survival_data.csv`` · ``regional_data.csv``
· ``delais_hopitaux_data.csv`` et produit le fichier pivot long unique, via le même
convertisseur que le pipeline (``format_long.tables_vers_long``).

Usage :
    python scripts/migrer_donnees_long.py            # data/ par défaut
    python scripts/migrer_donnees_long.py <dossier>  # autre dossier

Vérifie un round-trip (re-pivot → tables d'origine) et journalise les comptes.
Idempotent : ré-exécutable sans effet de bord (réécrit donnees.csv).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from format_long import (                       # noqa: E402
    tables_vers_long, pivoter_simple, pivoter_survie,
)

ANCIENS = {
    "aphp": "aphp_data.csv",
    "survie": "survival_data.csv",
    "regional": "regional_data.csv",
    "delais_hop": "delais_hopitaux_data.csv",
}


def _lire(dossier: Path, nom: str):
    chemin = dossier / nom
    if not chemin.exists():
        return None
    df = pd.read_csv(chemin)
    return df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")],
                   errors="ignore")


def _comparer(nom, rec, orig, cle):
    """Round-trip : compare la table re-pivotée à l'originale (clé triée)."""
    if orig is None:
        print(f"  {nom:<11} : source absente, ignoré")
        return
    cols = list(orig.columns)
    rec = rec[cols].sort_values(cle, na_position="last").reset_index(drop=True)
    orig = orig.sort_values(cle, na_position="last").reset_index(drop=True)
    exact = rec.equals(orig)
    note = "EXACT" if exact else f"rec {len(rec)} vs orig {len(orig)}"
    print(f"  {nom:<11} : {'✓' if exact else '≈'} {note}")


def main(dossier="data"):
    dossier = Path(dossier)
    df_aphp = _lire(dossier, ANCIENS["aphp"])
    df_survie = _lire(dossier, ANCIENS["survie"])
    df_regional = _lire(dossier, ANCIENS["regional"])
    df_delais_hop = _lire(dossier, ANCIENS["delais_hop"])

    long = tables_vers_long(df_aphp, df_survie, df_regional, df_delais_hop)
    out = dossier / "donnees.csv"
    long.to_csv(out, index=False, encoding="utf-8")
    print(f"→ {out}  ({len(long):,} lignes, {long['variable'].nunique()} variables, "
          f"sources {sorted(long['source'].unique())})")

    # Round-trip (sanity) : re-pivot → tables d'origine.
    print("Round-trip :")
    cle4 = ["annee", "entite", "appareil", "organe"]
    _comparer("aphp", pivoter_simple(long, "DIM APHP", ["aphp", "ghu"]), df_aphp, cle4)
    _comparer("regional", pivoter_simple(long, "BN", ["aphp", "type_etab"]),
              df_regional, cle4)
    _comparer("survie", pivoter_survie(long),
              df_survie, ["annee", "entite", "appareil", "organe", "stade", "population"])
    # délais-hôpitaux : les lignes niveau HÔPITAL sont exactes ; les lignes AP-HP/GHU
    # sont le sur-ensemble (identique en valeur) fourni par la table OECI.
    if df_delais_hop is not None:
        rec_dh = pivoter_simple(long, "DIM APHP", ["aphp", "ghu", "hopital"],
                                variables=[c for c in df_delais_hop.columns
                                           if c.startswith("delai_")],
                                reconstruire_nouveaux=False)
        from referentiels import GHU_LIST
        hop = set(df_delais_hop["entite"]) - {"AP-HP"} - set(GHU_LIST)
        rec_h = rec_dh[rec_dh["entite"].isin(hop)]
        orig_h = df_delais_hop[df_delais_hop["entite"].isin(hop)]
        _comparer("delais_hop", rec_h, orig_h, cle4)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
