#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filet de tests GARDE-FOU (smoke) — à lancer avant tout push :

    .venv/bin/python tests/smoke_test.py      (ou : python tests/smoke_test.py)

Couvre les régressions réellement rencontrées sur ce dépôt : figure/page construite
mais VIDE (grain TOTAL manquant), contrat de donnees.csv cassé, entité régionale
absente. Rapide (~15 s) et hermétique : génère les données fictives dans un dossier
TEMPORAIRE (ne touche ni data/ ni output/), construit un petit sous-ensemble de pages
clés et vérifie que chaque figure Plotly embarquée porte des données.

Sort avec un code ≠ 0 au premier échec (utilisable en CI avant le build complet).
"""
import base64
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generateur_fictif import generer_donnees_long, HOPITAL2GHU          # noqa: E402
from report_builder import (                                             # noqa: E402
    load_aphp, load_regional, load_survival, load_delais_hopitaux,
    build_rapport_global, build_rapport_appareil,
    build_rapport_comparaison_hopitaux, build_rapport_comparaison_hopitaux_delais,
)
from chart_utils import (                                                # noqa: E402
    regional_comparison, donut_market_share, delay_hospital_comparison,
    survival_hospital_comparison, line_evolution, REGIONAL_COLORS, GHU_LIST,
)

ECHOUES = []


def verifier(nom, ok, detail=""):
    tag = "✓" if ok else "✗"
    print(f"  {tag} {nom}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        ECHOUES.append(nom)


# ── Helpers « figure non vide » ────────────────────────────────────────────────
def _arrlen(v):
    """Longueur d'un tableau plotly : list, ndarray, ou bdata (encodage binaire v6)."""
    if isinstance(v, (list, tuple, np.ndarray)):
        return len(v)
    if isinstance(v, dict) and "bdata" in v:
        raw = base64.b64decode(v["bdata"])
        return len(raw) // np.dtype(v.get("dtype", "f8")).itemsize
    return 0


def points_fig(fig):
    """Nombre max de points portés par une figure plotly (objet graph_objects)."""
    n = 0
    for tr in fig.data:
        for k in ("x", "y", "values", "z", "labels", "parents"):
            v = getattr(tr, k, None)
            if v is not None:
                n = max(n, _arrlen(v))
    return n


_RE_NEWPLOT = re.compile(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\])\s*,\s*\{', re.S)


def figures_vides_html(path):
    """[(index, nb_traces)] des figures VIDES embarquées dans une page HTML."""
    html = Path(path).read_text(encoding="utf-8")
    vides = []
    figs = _RE_NEWPLOT.findall(html)
    for j, brut in enumerate(figs):
        traces = json.loads(brut)
        n = 0
        for tr in traces:
            for k in ("x", "y", "values", "z", "labels", "parents"):
                n = max(n, _arrlen(tr.get(k)))
        if n == 0:
            vides.append((j, len(traces)))
    return figs, vides


def grain(df):
    a = df["appareil"] == "TOTAL"
    o = df["organe"] == "TOTAL"
    return np.where(a & o, "TOTAL/TOTAL", np.where(~a & o, "appareil", "organe"))


# ════ 1. Génération fictive (hermétique, dossier temporaire) ════
tmp = Path(tempfile.mkdtemp(prefix="smoke_"))
data_dir, out_dir = tmp / "data", tmp / "output"
data_dir.mkdir(); out_dir.mkdir()

print("1) Génération fictive → donnees.csv (temporaire)")
long = generer_donnees_long()
long.to_csv(data_dir / "donnees.csv", index=False, encoding="utf-8")
verifier("donnees.csv généré (> 100k lignes)", len(long) > 100_000, f"{len(long)} lignes")

# ════ 2. Contrat de donnees.csv ════
print("2) Contrat de donnees.csv")
COLONNES = ["annee", "source", "niveau", "entite", "appareil", "organe",
            "age", "stade", "population", "variable", "valeur"]
VARIABLES = {"nb_patients", "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
             "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
             "delai_global_median", "delai_chirurgie_median",
             "delai_traitement_medical_median", "delai_radio_median",
             "nb_patients_stade", "survie_1an", "survie_5ans"}
verifier("colonnes exactes", list(long.columns) == COLONNES, str(list(long.columns)))
verifier("sources ⊆ {BN, DIM APHP, EDS APHP}",
         set(long["source"]) == {"BN", "DIM APHP", "EDS APHP"})
verifier("niveaux ⊆ {aphp, ghu, hopital, type_etab}",
         set(long["niveau"]) == {"aphp", "ghu", "hopital", "type_etab"})
verifier("variables = vocabulaire du contrat", set(long["variable"]) == VARIABLES)
cle = [c for c in COLONNES if c != "valeur"]
verifier("clé d'unicité (0 doublon)", not long.duplicated(subset=cle).any())
v = pd.to_numeric(long["valeur"], errors="coerce")
sv = v[long["variable"].isin(["survie_1an", "survie_5ans"])]
verifier("survie ∈ [0,100]", bool(len(sv)) and bool(sv.between(0, 100).all()))
dl = v[long["variable"].str.startswith("delai_")]
verifier("délais présents et ≥ 0", bool(len(dl)) and bool((dl >= 0).all()))

# ════ 3. Grains TOTAL après les load_* (le pattern de bug récurrent) ════
print("3) Grains TOTAL présents après les load_*")
aphp = load_aphp(data_dir)
reg = load_regional(data_dir)
surv = load_survival(data_dir)
dh = load_delais_hopitaux(data_dir)

ap_tot = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL") & (aphp.organe == "TOTAL")]
verifier("load_aphp : AP-HP au grain TOTAL/TOTAL, patients > 0",
         not ap_tot.empty and bool((ap_tot.nb_patients > 0).all()))
verifier("load_aphp : délais AP-HP TOTAL/TOTAL non nuls",
         not ap_tot.empty and bool(ap_tot.delai_global_median.notna().all()))

reg_tot = reg[(reg.appareil == "TOTAL") & (reg.organe == "TOTAL")]
TYPES = {"AP-HP", "Clinique", "CH", "CHU", "PSPH", "CLCC"}
verifier("load_regional : 6 entités (AP-HP + 5 types) au grain TOTAL/TOTAL",
         set(reg_tot.entite) == TYPES, f"observé {sorted(set(reg_tot.entite))}")
verifier("load_regional : valeurs régionales > 0 (extrait non vide)",
         bool((pd.to_numeric(reg_tot.nb_patients, errors="coerce") > 0).any()))

dh_tot = dh[(dh.appareil == "TOTAL") & (dh.organe == "TOTAL")]
nb_hop = dh_tot[~dh_tot.entite.isin(["AP-HP", *GHU_LIST])].entite.nunique()
verifier("load_delais_hopitaux : grain global présent, ≥ 30 hôpitaux",
         nb_hop >= 30, f"{nb_hop} hôpitaux")

sv_tot = surv[(surv.entite == "AP-HP") & (surv.appareil == "TOTAL") & (surv.organe == "TOTAL")]
verifier("load_survival : AP-HP au grain TOTAL/TOTAL", not sv_tot.empty)

# ════ 4. Figures clés NON VIDES (fonctions chart_utils) ════
print("4) Figures clés non vides")
annee = int(aphp.annee.max())
verifier("regional_comparison (contexte régional)",
         points_fig(regional_comparison(reg_tot, "nb_patients", "t",
                                        color_map=REGIONAL_COLORS)) > 0)
rl = reg_tot[reg_tot.annee == annee]
verifier("donut types d'établissement (avec entities)",
         points_fig(donut_market_share(rl, "entite", "nb_patients", "t",
                                       entities=sorted(rl.entite.unique()),
                                       color_map=REGIONAL_COLORS)) >= 6)
verifier("delay_hospital_comparison (global TOTAL/TOTAL)",
         points_fig(delay_hospital_comparison(dh, HOPITAL2GHU, appareil="TOTAL",
                                              organe="TOTAL", annee=annee)) > 0)
verifier("survival_hospital_comparison (global, stade I-III)",
         points_fig(survival_hospital_comparison(surv, HOPITAL2GHU, appareil="TOTAL",
                                                 stade="I-III")) > 0)
verifier("line_evolution patients AP-HP",
         points_fig(line_evolution(ap_tot.sort_values("annee"), "annee", "nb_patients",
                                   "entite", "t")) > 0)

# ════ 5. Pages clés : construites ET sans figure vide ════
print("5) Pages clés construites et sans figure vide")
pages = []
pages.append(build_rapport_global(data_dir, out_dir))                       # index.html
pages.append(build_rapport_comparaison_hopitaux(surv, HOPITAL2GHU, out_dir))
pages.append(build_rapport_comparaison_hopitaux_delais(dh, HOPITAL2GHU, out_dir))
pages.append(build_rapport_appareil("SEIN", data_dir, out_dir, entity="AP-HP",
                                    aphp=aphp, reg=reg, surv=surv))
for page in pages:
    ok_page = page is not None and Path(page).exists()
    verifier(f"page générée : {Path(page).name if page else '?'}", ok_page)
    if ok_page:
        figs, vides = figures_vides_html(page)
        verifier(f"  figures non vides ({len(figs)} embarquées) : {Path(page).name}",
                 len(figs) > 0 and not vides, f"vides={vides}")

# ════ Bilan ════
print(f"\n{'─'*60}")
if ECHOUES:
    print(f"✗ SMOKE TEST : {len(ECHOUES)} échec(s)")
    for nom in ECHOUES:
        print("   ✗", nom)
    sys.exit(1)
print("✓ SMOKE TEST : tous les garde-fous sont verts")
