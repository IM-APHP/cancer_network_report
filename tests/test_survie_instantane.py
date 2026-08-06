#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-régression : ``survival_by_stage`` doit retomber sur la dernière année AVEC
survie quand l'année demandée n'en a pas.

    .venv/bin/python tests/test_survie_instantane.py     (exit ≠ 0 si échec)

BUG couvert (réel uniquement, invisible en fictif) : les rapports appellent
``survival_by_stage(..., year=last_year)`` où last_year = dernière année du DATASET
(comptes patients, ex. 2025). La survie à 5 ans des années récentes n'existe pas
encore (recul nécessaire) → filtre vide → « Pas de données de survie » alors que des
années antérieures en ont. Le fictif générant de la survie pour TOUTES les années,
ce chemin n'y est jamais exercé.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from chart_utils import survival_by_stage                              # noqa: E402

# Frame façon load_survival : survie disponible jusqu'en 2023 SEULEMENT,
# alors que le dataset (comptes) court jusqu'en 2025.
surv = pd.DataFrame([
    dict(annee=an, entite="AP-HP", appareil="SEIN", organe="TOTAL", stade=st,
         population="tous", nb_patients_stade=100, survie_1an=90 - 10 * (st == "IV"),
         survie_5ans=75 - 20 * (st == "IV"))
    for an in (2022, 2023) for st in ("I-III", "IV")
])

echecs = []

def verifier(nom, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {nom}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        echecs.append(nom)

def _points(fig):
    return sum(len(tr.y) if tr.y is not None else 0 for tr in fig.data)

def _sans_donnees(fig):
    return any("Pas de données" in (a.text or "") for a in fig.layout.annotations or [])

# 1) Année demandée SANS survie (2025) → repli sur la dernière année disponible (2023).
fig = survival_by_stage(surv, "AP-HP", "SEIN", year=2025)
verifier("year=2025 sans survie → barres présentes (repli)", _points(fig) > 0,
         "figure vide « Pas de données »" if _sans_donnees(fig) else f"{_points(fig)} points")
verifier("titre affiche l'année de survie réelle (2023)",
         "(2023)" in (fig.layout.title.text or ""),
         f"titre = {fig.layout.title.text!r}")

# 2) Année demandée AVEC survie (2022) → comportement inchangé (pas de repli).
fig2 = survival_by_stage(surv, "AP-HP", "SEIN", year=2022)
verifier("year=2022 avec survie → 2022 conservée",
         _points(fig2) > 0 and "(2022)" in (fig2.layout.title.text or ""))

# 3) year=None → dernière année disponible (inchangé).
fig3 = survival_by_stage(surv, "AP-HP", "SEIN")
verifier("year=None → dernière année disponible (2023)",
         _points(fig3) > 0 and "(2023)" in (fig3.layout.title.text or ""))

# 4) AUCUNE survie pour l'entité/appareil → message « Pas de données » conservé.
fig4 = survival_by_stage(surv, "AP-HP", "VADS", year=2025)
verifier("aucune survie du tout → « Pas de données » conservé", _sans_donnees(fig4))

if echecs:
    print(f"\n✗ SURVIE INSTANTANÉ : {len(echecs)} échec(s)")
    sys.exit(1)
print("\n✓ SURVIE INSTANTANÉ : repli sur la dernière année avec survie OK")
