#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-régression : alignement d'index dans ``_lire_feuille_aphp`` (canceroAPHP).

    .venv/bin/python tests/test_alignement_aphp.py     (exit ≠ 0 si échec)

BUG couvert (mode réel uniquement, invisible en fictif) : quand les lignes AP-HP
retenues portent un index NON contigu (elles ne sont pas en tête du fichier réel —
les blocs Hop/GHU les précèdent), construire ``cadre`` avec ``annee.values`` (numpy)
lui donnait un RangeIndex, alors que les mesures assignées ensuite portent l'index
FILTRÉ de ``df`` → alignement pandas sur l'index → mesures quasi toutes NaN → grains
TOTAL AP-HP à 0. Ce test construit une fixture où les lignes AP-HP sont ENTRELACÉES
avec des lignes Hop/GHU (index retenus 1 et 3) et vérifie que les valeurs survivent.
Il ÉCHOUE sur la version ``annee.values`` et PASSE avec ``annee`` (Series indexée).
"""
import os
import sys
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import chargeur_long as CL                                            # noqa: E402

# ── Fixture : lignes AP-HP NON contiguës (précédées/entrelacées de GHU/Hop) ──────
tmp = tempfile.mkdtemp(prefix="alignement_aphp_")
path = os.path.join(tmp, "canceroAPHP_test_Pat.xlsx")
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Total"
ws.append(["Niveau", "Hopital - GH", "Appareil patient", "Organe patient", "Année",
           "Nb de patients", "Nouveaux patients"])
ws.append(["GHU - Organe",  "APHP_Centre", "SEIN", "Sein", 2024, 999, 999])  # idx 0 → filtrée
ws.append(["AP-HP - Total", "AP-HP", "TOTAL", "TOTAL", 2024, 80, 45])        # idx 1 → GARDÉE
ws.append(["Hop - Organe",  "Beaujon", "SEIN", "Sein", 2024, 999, 999])      # idx 2 → filtrée
ws.append(["AP-HP - Organe", "AP-HP", "SEIN", "Sein", 2024, 78, 44])         # idx 3 → GARDÉE
wb.save(path)

conf = CL._charger_descriptif()["sources"]["regional_aphp"]
conf_feuille = dict(conf["feuilles"]["total_patients"])
masque = set(conf["coercition"]["masque"])

lignes = CL._lire_feuille_aphp(path, conf_feuille, "BN", masque, conf["portee_retenue"])
d = pd.DataFrame(lignes)

echecs = []

def verifier(nom, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {nom}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        echecs.append(nom)

# 1) Aucune mesure NaN parasite : toutes les valeurs émises sont non nulles.
vals = pd.to_numeric(d["valeur"], errors="coerce")
verifier("aucune valeur NaN parasite", bool(vals.notna().all()),
         f"{int(vals.isna().sum())} NaN sur {len(vals)}")

# 2) Le grain TOTAL/TOTAL porte la valeur source (80), pas 0 (somme de NaN).
tot = d[(d.appareil == "TOTAL") & (d.organe == "TOTAL")
        & (d.variable == "nb_patients") & (d.population == "tous")]
verifier("grain TOTAL/TOTAL nb_patients = 80",
         len(tot) == 1 and float(tot["valeur"].iloc[0]) == 80.0,
         f"obtenu {tot['valeur'].tolist()}")

# 3) Le grain organe aussi (78) — et les nouveaux patients (45/44).
org = d[(d.organe == "Sein") & (d.variable == "nb_patients") & (d.population == "tous")]
verifier("grain organe nb_patients = 78",
         len(org) == 1 and float(org["valeur"].iloc[0]) == 78.0,
         f"obtenu {org['valeur'].tolist()}")
nvx = d[(d.appareil == "TOTAL") & (d.variable == "nb_patients") & (d.population == "nouveaux")]
verifier("TOTAL/TOTAL nouveaux patients = 45",
         len(nvx) == 1 and float(nvx["valeur"].iloc[0]) == 45.0,
         f"obtenu {nvx['valeur'].tolist()}")

if echecs:
    print(f"\n✗ ALIGNEMENT canceroAPHP : {len(echecs)} échec(s) — mesures perdues par "
          "désalignement d'index (cf. docstring).")
    sys.exit(1)
print("\n✓ ALIGNEMENT canceroAPHP : mesures préservées sur index non contigu")
