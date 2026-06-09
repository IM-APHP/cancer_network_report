#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remplit les gabarits de format Excel (OECI + régional) avec des données
fictives réalistes, au format STRICTEMENT identique.

Principe : les gabarits fournis dans ``data/`` contiennent déjà le squelette de
dimensions (colonnes Niveau, GHU, Hôpital, Appareil, Organe, Année, Classe age…).
Ce script NE TOUCHE PAS aux colonnes de dimension ni aux en-têtes (y compris les
en-têtes multi-lignes et cellules fusionnées de « Survie globale » et « Délais
PEC ») : il ne remplit que les colonnes de mesures, par-dessus le squelette
existant, puis écrit des copies suffixées ``_fictif`` (les gabarits restent
intacts).

Deux exceptions documentées :
  * « Origine géo » est livré DÉJÀ rempli dans le gabarit : ses 3 colonnes de
    valeurs sont régénérées en fictif (uniquement dans la copie).
  * « Survie globale » est livré ENTIÈREMENT vide (pas même le squelette de
    dimensions) : son squelette est reconstruit à partir des tuples de
    dimensions de « Délais PEC » (mêmes 5 dimensions), puis rempli.

Reproductibilité : seed fixe (np.random.seed(42)).

Cohérence garantie :
  * OECI : somme Hôpital → GHU → AP-HP, et Organe → Appareil (les lignes
    agrégées sont calculées par sommation des feuilles `Hopital Organe`).
  * Régional : agrégation interne Organe→Appareil→Total par établissement, et
    onglet Total = « Age < 18 ans » + « Age >= 18 ans » cellule à cellule
    (jointure sur (Niveau, Finess, Appareil, Organe, Année)).
  * Sous-effectifs ≤ effectif total ; pourcentages ∈ [0, 100] ; survie I-III >
    IV et 1 an > 5 ans ; délais : médiane > 0 et moyenne ≳ médiane ; origine géo
    IDF/hors-IDF/International ≈ 100 % par groupe ; creux COVID 2020 (~ -8 %).
"""
import os
import numpy as np
import openpyxl

np.random.seed(42)

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
OECI_IN = os.path.join(DATA, "indicateurs_oeci_2025_M12.xlsx")
OECI_OUT = os.path.join(DATA, "indicateurs_oeci_2025_M12_fictif.xlsx")
PAT_IN = os.path.join(DATA, "canceroBR_16-25_Pat_13032026.xlsx")
PAT_OUT = os.path.join(DATA, "canceroBR_16-25_Pat_13032026_fictif.xlsx")
SEJ_IN = os.path.join(DATA, "canceroBR_16-25_Sej_13032026.xlsx")
SEJ_OUT = os.path.join(DATA, "canceroBR_16-25_Sej_13032026_fictif.xlsx")

# Mapping Hôpital -> GHU (nom complet OECI), relevé dans l'onglet « Effectifs recherche ».
HOSP2GHU = {
    # GHU Nord
    "Beaujon": "APHP.Nord-Université de Paris", "Bichat": "APHP.Nord-Université de Paris",
    "Bretonneau": "APHP.Nord-Université de Paris", "Lariboisière": "APHP.Nord-Université de Paris",
    "Louis Mourier": "APHP.Nord-Université de Paris", "Robert Debré": "APHP.Nord-Université de Paris",
    "Saint-Louis": "APHP.Nord-Université de Paris", "Villemin-Paul Doumer": "APHP.Nord-Université de Paris",
    # GHU PSL (Université Paris Saclay)
    "Ambroise Paré": "APHP.Université Paris Saclay", "Antoine Beclère": "APHP.Université Paris Saclay",
    "Bicêtre": "APHP.Université Paris Saclay", "Paul Brousse": "APHP.Université Paris Saclay",
    "Raymond Poincaré": "APHP.Université Paris Saclay", "Sainte-Perine": "APHP.Université Paris Saclay",
    # GHU Centre
    "Broca": "APHP.Centre-Université de Paris", "Cochin": "APHP.Centre-Université de Paris",
    "Corentin Celton": "APHP.Centre-Université de Paris", "Hegp": "APHP.Centre-Université de Paris",
    "Hôtel-Dieu": "APHP.Centre-Université de Paris", "Necker": "APHP.Centre-Université de Paris",
    # GHU Mondor
    "Emile Roux": "APHP.Hôpitaux Universitaires Henri-Mondor", "Georges Clémenceau": "APHP.Hôpitaux Universitaires Henri-Mondor",
    "Henri Mondor": "APHP.Hôpitaux Universitaires Henri-Mondor", "Joffre": "APHP.Hôpitaux Universitaires Henri-Mondor",
    # GHU PSSD
    "Avicenne": "APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis",
    "Jean Verdier": "APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis",
    "René Muret": "APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis",
    # GHU SUN
    "Armand Trousseau": "APHP.Sorbonne Université", "Charles Foix": "APHP.Sorbonne Université",
    "Pitie-Salpêtrière": "APHP.Sorbonne Université", "Rothschild": "APHP.Sorbonne Université",
    "Saint-Antoine": "APHP.Sorbonne Université", "Tenon": "APHP.Sorbonne Université",
}

# Facteurs de taille déterministes (gros sites pluridisciplinaires vs petits).
_HOSP_FACTOR = {h: round(float(f), 3) for h, f in
                zip(sorted(HOSP2GHU), 0.4 + 1.4 * np.random.rand(len(HOSP2GHU)))}


def hosp_factor(hop):
    return _HOSP_FACTOR.get(hop, 1.0)


_ORG_FACTOR = {}


def org_factor(app, org):
    """Facteur de fréquence par (appareil, organe), tiré une fois, stable."""
    key = (app, org)
    if key not in _ORG_FACTOR:
        _ORG_FACTOR[key] = float(np.random.uniform(0.3, 1.7))
    return _ORG_FACTOR[key]


def rint(x):
    return int(max(0, round(x)))


# ───────────────────────── sélection des feuilles pour agrégation OECI ──────
def select_leaves(niv, ghu_col, hop, app, org, leaves):
    """leaves : liste de (ghu_full, hop, app, org, vals).
    Renvoie le sous-ensemble de feuilles agrégées par la ligne (niv, …)."""
    if niv == "GH Organe":
        return [v for (g, h, a, o, v) in leaves if g == ghu_col and a == app and o == org]
    if niv == "APHP Organe":
        return [v for (g, h, a, o, v) in leaves if a == app and o == org]
    if niv == "Hop Total":
        return [v for (g, h, a, o, v) in leaves if h == hop]
    if niv == "GH Total":
        return [v for (g, h, a, o, v) in leaves if g == ghu_col]
    if niv == "APHP Total":
        return [v for (g, h, a, o, v) in leaves]
    return []


def collect_rows(ws, hdr):
    """Retourne [(rowidx, niveau, ghu, hopital, appareil, organe), …] sur les
    lignes de données non vides (colonnes 1..5)."""
    out = []
    for r in range(hdr + 1, ws.max_row + 1):
        niv = ws.cell(r, 1).value
        if niv in (None, ""):
            continue
        out.append((r, niv, ws.cell(r, 2).value, ws.cell(r, 3).value,
                    ws.cell(r, 4).value, ws.cell(r, 5).value))
    return out


# ════════════════════════════ OECI ═════════════════════════════════════════
def fill_origine_geo(ws):
    """3 colonnes : Nb patients (5), Nb patients tot (6), % patients (7).
    Regroupe les lignes consécutives partageant (Niveau, GHU, Hôpital) ; répartit
    un total entre les origines présentes (IDF dominant) ; % = part/tot*100."""
    groups = []  # [(key, [rowidx…], [origine…])]
    for r in range(2, ws.max_row + 1):
        niv = ws.cell(r, 1).value
        if niv in (None, ""):
            continue
        key = (niv, ws.cell(r, 2).value, ws.cell(r, 3).value)
        orig = ws.cell(r, 4).value
        if groups and groups[-1][0] == key:
            groups[-1][1].append(r); groups[-1][2].append(orig)
        else:
            groups.append((key, [r], [orig]))
    for (niv, ghu, hop), rows, origs in groups:
        scale = hosp_factor(hop) if hop else (6.0 if "GH" in (niv or "") else 33.0)
        total = rint(np.random.uniform(800, 3500) * max(scale, 0.5))
        # proportions de référence par origine
        ref = {"IDF": np.random.uniform(0.70, 0.82),
               "Fr_notIDF": np.random.uniform(0.12, 0.25),
               "International": np.random.uniform(0.003, 0.03)}
        present = [o for o in origs]
        w = np.array([ref.get(o, 0.1) for o in present], float)
        w = w / w.sum()
        parts = [rint(total * x) for x in w]
        diff = total - sum(parts)
        parts[int(np.argmax(parts))] += diff  # ajuste l'arrondi sur la plus grande part
        for r, part in zip(rows, parts):
            ws.cell(r, 5).value = part
            ws.cell(r, 6).value = total
            ws.cell(r, 7).value = round(part / total * 100, 1) if total else 0.0


def gen_patient_leaf(app, org, hop):
    base = rint(np.random.gamma(2.2, 18) * org_factor(app, org) * hosp_factor(hop) + 3)
    nvx = rint(base * np.random.uniform(0.40, 0.60))
    chir = rint(base * np.random.uniform(0.25, 0.55))
    nvx_chir = rint(min(chir, nvx) * np.random.uniform(0.5, 0.95))
    chimio = rint(base * np.random.uniform(0.20, 0.55))
    radio = rint(base * np.random.uniform(0.10, 0.40))
    sp = rint(base * np.random.uniform(0.05, 0.20))
    morts = rint(base * np.random.uniform(0.01, 0.07))
    morts_sp = rint(min(morts, sp) * np.random.uniform(0.3, 0.9))
    cart = rint(base * np.random.uniform(0, 0.03))
    greffe = rint(base * np.random.uniform(0, 0.04))
    return {6: base, 7: nvx, 8: chir, 9: nvx_chir, 10: chimio, 11: radio, 12: sp,
            13: morts, 14: morts_sp, 15: cart, 16: greffe}


def gen_sejour_leaf(app, org, hop):
    total = rint(np.random.gamma(2.4, 26) * org_factor(app, org) * hosp_factor(hop) + 4)
    chimio = rint(total * np.random.uniform(0.10, 0.45))
    chimio0 = rint(chimio * np.random.uniform(0.4, 0.9))
    chimio0_ped = rint(chimio0 * np.random.uniform(0, 0.15))
    radio = rint(total * np.random.uniform(0.05, 0.30))
    autres = rint(total * np.random.uniform(0.05, 0.25))
    chir = rint(total * np.random.uniform(0.10, 0.40))
    ped = rint(total * np.random.uniform(0, 0.12))
    sp = rint(total * np.random.uniform(0.02, 0.12))
    greffe = rint(total * np.random.uniform(0, 0.05))
    hemato = rint(total * np.random.uniform(0, 0.20))
    return {6: total, 7: chimio, 8: chimio0, 9: chimio0_ped, 10: radio, 11: autres,
            12: chir, 13: ped, 14: sp, 15: greffe, 16: hemato}


def gen_chirurgie_leaf(app, org, hop):
    nb = rint(np.random.gamma(2.0, 12) * org_factor(app, org) * hosp_factor(hop) + 2)
    rehosp30 = np.random.uniform(3, 12)
    rehosp90 = rehosp30 + np.random.uniform(1, 8)
    rechir30 = np.random.uniform(1, 6)
    rechir90 = rechir30 + np.random.uniform(0.5, 4)
    deces30 = np.random.uniform(0.3, 3.5)
    deces90 = deces30 + np.random.uniform(0.3, 3)
    return {6: nb,
            7: round(min(rehosp30, 100), 1), 8: round(min(rehosp90, 100), 1),
            9: round(min(rechir30, 100), 1), 10: round(min(rechir90, 100), 1),
            11: round(min(deces30, 100), 1), 12: round(min(deces90, 100), 1)}


def gen_delais_leaf(app, org, hop):
    """4 blocs de 5 colonnes : TOTAL(6-10), CHIRURGIE(11-15), MEDECINE(16-20),
    RADIOTHERAPIE(21-25) ; chaque bloc = Nb, Nb urg, %urg, Moyenne, Médiane."""
    base = rint(np.random.gamma(2.0, 14) * org_factor(app, org) * hosp_factor(hop) + 3)
    out = {}
    cols = {"TOTAL": 6, "CHIR": 11, "MED": 16, "RADIO": 21}
    frac = {"TOTAL": 1.0, "CHIR": np.random.uniform(0.3, 0.7),
            "MED": np.random.uniform(0.3, 0.7), "RADIO": np.random.uniform(0.2, 0.5)}
    med_ref = {"TOTAL": np.random.uniform(18, 35), "CHIR": np.random.uniform(20, 45),
               "MED": np.random.uniform(15, 30), "RADIO": np.random.uniform(25, 55)}
    for blk, c0 in cols.items():
        nb = rint(base * frac[blk])
        urg = rint(nb * np.random.uniform(0.05, 0.25))
        pct = round(urg / nb * 100, 1) if nb else 0.0
        med = max(1.0, med_ref[blk])
        moy = round(med * np.random.uniform(1.02, 1.20), 1)  # moyenne légèrement > médiane
        out[c0] = nb; out[c0 + 1] = urg; out[c0 + 2] = pct
        out[c0 + 3] = moy; out[c0 + 4] = round(med, 1)
    return out


def gen_survie_leaf(app, org, hop):
    """16 colonnes (6..21). Schéma : {Tous|Nvx} × {5ans|1an} × {I-III|IV}
    × {Nb, %}. I-III > IV ; 1 an > 5 ans ; Nvx ≤ Tous."""
    f = org_factor(app, org) * hosp_factor(hop)
    nb13_tous = rint(np.random.gamma(2.0, 14) * f + 3)
    nb4_tous = rint(nb13_tous * np.random.uniform(0.10, 0.35))
    nb13_nvx = rint(nb13_tous * np.random.uniform(0.40, 0.60))
    nb4_nvx = rint(nb4_tous * np.random.uniform(0.40, 0.60))
    s5_13 = np.random.uniform(55, 88)          # survie 5 ans, stade I-III
    s5_4 = np.random.uniform(8, min(40, s5_13 - 5))   # stade IV < I-III
    s1_13 = min(99.0, s5_13 + np.random.uniform(6, 14))   # 1 an > 5 ans
    s1_4 = min(99.0, s5_4 + np.random.uniform(8, 20))
    s1_4 = min(s1_4, s1_13 - 3)                # I-III > IV à 1 an aussi
    # colonnes : 6=Tous5a I-III nb,7=%, 8=IV nb,9=%, 10=Tous1a I-III nb,11=%,12=IV nb,13=%
    #            14..21 = idem « Nouveaux »
    def blk(nb13, nb4):
        return [nb13, round(s5_13, 1), nb4, round(s5_4, 1),
                nb13, round(s1_13, 1), nb4, round(s1_4, 1)]
    vals = blk(nb13_tous, nb4_tous) + blk(nb13_nvx, nb4_nvx)
    return {6 + i: v for i, v in enumerate(vals)}


def fill_count_sheet(ws, hdr, gen_leaf, measure_cols):
    """Onglets de comptages purs (patient, séjour) : agrégats = sommes."""
    rows = collect_rows(ws, hdr)
    vals = {}
    leaves = []
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            v = gen_leaf(app, org, hop)
            vals[r] = v
            leaves.append((HOSP2GHU.get(hop), hop, app, org, v))
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            continue
        sel = select_leaves(niv, ghu, hop, app, org, leaves)
        vals[r] = {c: sum(v[c] for v in sel) for c in measure_cols}
    for r, v in vals.items():
        for c, x in v.items():
            ws.cell(r, c).value = x


def fill_rate_sheet(ws, hdr, gen_leaf, count_col, rate_cols):
    """Onglet chirurgie : count_col sommé, rate_cols en moyenne pondérée par count_col."""
    rows = collect_rows(ws, hdr)
    vals = {}
    leaves = []
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            v = gen_leaf(app, org, hop)
            vals[r] = v
            leaves.append((HOSP2GHU.get(hop), hop, app, org, v))
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            continue
        sel = select_leaves(niv, ghu, hop, app, org, leaves)
        W = sum(v[count_col] for v in sel)
        agg = {count_col: W}
        for c in rate_cols:
            agg[c] = round(sum(v[c] * v[count_col] for v in sel) / W, 1) if W else 0.0
        vals[r] = agg
    for r, v in vals.items():
        for c, x in v.items():
            ws.cell(r, c).value = x


def fill_delais_sheet(ws, hdr=2):
    """4 blocs (TOTAL/CHIR/MED/RADIO). Nb & urg sommés ; %urg dérivé ;
    moyenne/médiane en moyenne pondérée par Nb."""
    rows = collect_rows(ws, hdr)
    vals = {}
    leaves = []
    blocks = [6, 11, 16, 21]
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            v = gen_delais_leaf(app, org, hop)
            vals[r] = v
            leaves.append((HOSP2GHU.get(hop), hop, app, org, v))
    for (r, niv, ghu, hop, app, org) in rows:
        if niv == "Hopital Organe":
            continue
        sel = select_leaves(niv, ghu, hop, app, org, leaves)
        agg = {}
        for c0 in blocks:
            nb = sum(v[c0] for v in sel)
            urg = sum(v[c0 + 1] for v in sel)
            agg[c0] = nb
            agg[c0 + 1] = urg
            agg[c0 + 2] = round(urg / nb * 100, 1) if nb else 0.0
            if nb:
                agg[c0 + 3] = round(sum(v[c0 + 3] * v[c0] for v in sel) / nb, 1)
                agg[c0 + 4] = round(sum(v[c0 + 4] * v[c0] for v in sel) / nb, 1)
            else:
                agg[c0 + 3] = 0.0
                agg[c0 + 4] = 0.0
        vals[r] = agg
    for r, v in vals.items():
        for c, x in v.items():
            ws.cell(r, c).value = x


def fill_survie_sheet(ws_sur, ws_del):
    """« Survie globale » est vide : on reconstruit son squelette à partir des
    tuples de dimensions de « Délais PEC », puis on remplit. Colonnes survie :
    Niveau(1), Appareil patient(2), Organe patient(3), GHU(4), Hôpital(5)."""
    del_rows = collect_rows(ws_del, 2)  # (r, niv, ghu, hop, app, org)
    nb_cols = [6, 8, 10, 12, 14, 16, 18, 20]   # colonnes « Nb patients »
    pct_cols = [7, 9, 11, 13, 15, 17, 19, 21]  # colonnes « % survie »
    out = []   # (niv, ghu, hop, app, org)
    for (r, niv, ghu, hop, app, org) in del_rows:
        out.append((niv, ghu, hop, app, org))
    # écriture du squelette (lignes 5..) + génération/agrégation
    leaves = []
    rowvals = {}
    base_r = 5
    for i, (niv, ghu, hop, app, org) in enumerate(out):
        r = base_r + i
        ws_sur.cell(r, 1).value = niv
        ws_sur.cell(r, 2).value = app
        ws_sur.cell(r, 3).value = org
        ws_sur.cell(r, 4).value = ghu
        ws_sur.cell(r, 5).value = hop
        if niv == "Hopital Organe":
            v = gen_survie_leaf(app, org, hop)
            rowvals[r] = v
            leaves.append((HOSP2GHU.get(hop), hop, app, org, v))
    for i, (niv, ghu, hop, app, org) in enumerate(out):
        r = base_r + i
        if niv == "Hopital Organe":
            continue
        sel = select_leaves(niv, ghu, hop, app, org, leaves)
        agg = {}
        for c in nb_cols:
            agg[c] = sum(v[c] for v in sel)
        for c in pct_cols:
            W = sum(v[c - 1] for v in sel)  # pondération par le Nb du même bloc
            agg[c] = round(sum(v[c] * v[c - 1] for v in sel) / W, 1) if W else 0.0
        rowvals[r] = agg
    for r, v in rowvals.items():
        for c, x in v.items():
            ws_sur.cell(r, c).value = x


def fill_effectifs(ws, hdr=1):
    """Niveau hiérarchique avec dimension Classe age (col 6). Mesures : Nb
    patients (7), Nb séjours (8) ≥ patients. Leaf = 'Hôpital - Organe - Appareil'."""
    rows = []
    for r in range(hdr + 1, ws.max_row + 1):
        niv = ws.cell(r, 1).value
        if niv in (None, ""):
            continue
        rows.append((r, niv, ws.cell(r, 2).value, ws.cell(r, 3).value,
                     ws.cell(r, 4).value, ws.cell(r, 5).value, ws.cell(r, 6).value))
    vals = {}
    leaves = []  # (ghu, hop, app, org, age, pat, sej)
    for (r, niv, ghu, hop, app, org, age) in rows:
        if niv == "Hôpital - Organe - Appareil":
            pat = rint(np.random.gamma(1.6, 6) * org_factor(app, org) * hosp_factor(hop)
                       * (1.0 if age == "Adultes" else 0.5 if age == "Gériatrie" else 0.2) + 1)
            sej = rint(pat * np.random.uniform(1.2, 3.5))
            vals[r] = {7: pat, 8: sej}
            leaves.append((ghu, hop, app, org, age, pat, sej))

    def agg(pred):
        sub = [(p, s) for (g, h, a, o, ag, p, s) in leaves if pred(g, h, a, o, ag)]
        return {7: sum(p for p, s in sub), 8: sum(s for p, s in sub)}

    for (r, niv, ghu, hop, app, org, age) in rows:
        if niv == "Hôpital - Organe - Appareil":
            continue
        if niv == "GHU - Organe - Appareil":
            vals[r] = agg(lambda g, h, a, o, ag: g == ghu and a == app and o == org and ag == age)
        elif niv == "AP-HP - Organe - Appareil":
            vals[r] = agg(lambda g, h, a, o, ag: a == app and o == org and ag == age)
        elif niv == "Hopital":
            vals[r] = agg(lambda g, h, a, o, ag: h == hop and ag == age)
        elif niv == "GHU":
            vals[r] = agg(lambda g, h, a, o, ag: g == ghu and ag == age)
        elif niv == "AP-HP":
            vals[r] = agg(lambda g, h, a, o, ag: ag == age)
        else:
            vals[r] = {7: 0, 8: 0}
    for r, v in vals.items():
        for c, x in v.items():
            ws.cell(r, c).value = x


def fill_oeci():
    print("OECI : lecture du gabarit…")
    wb = openpyxl.load_workbook(OECI_IN)
    fill_origine_geo(wb["Origine géo"])
    fill_count_sheet(wb["Indicateurs patient"], 1, gen_patient_leaf, list(range(6, 17)))
    fill_count_sheet(wb["Indicateurs séjour"], 1, gen_sejour_leaf, list(range(6, 17)))
    fill_rate_sheet(wb["Indicateurs chirurgie"], 1, gen_chirurgie_leaf, 6, list(range(7, 13)))
    fill_delais_sheet(wb["Délais PEC"], 2)
    fill_survie_sheet(wb["Survie globale"], wb["Délais PEC"])
    fill_effectifs(wb["Effectifs recherche"], 1)
    wb.save(OECI_OUT)
    print(f"  → écrit : {OECI_OUT}")


# ════════════════════════════ Régional ═════════════════════════════════════
# colonnes (1-based) : Pat -> dims 1..8, mesures 9..14 ; Sej -> dims 1..8, mesures 9..20
PAT_MEAS = list(range(9, 15))
SEJ_MEAS = list(range(9, 21))
# offset d'en-tête : Pat = 1 ligne, Sej = 2 lignes
# Conjoncture par année : base 2019 = 1,0, creux COVID 2020 (~ -8 %) puis légère reprise.
COVID = {2016: 0.95, 2017: 0.96, 2018: 0.98, 2019: 1.0, 2020: 0.92, 2021: 0.96,
         2022: 0.98, 2023: 1.0, 2024: 1.01, 2025: 1.02}


def _finess_factor(cache, finess, statut):
    if finess not in cache:
        base = {"CLCC": 2.2, "CHR/U": 1.6, "CH": 0.9, "PSPH/EBNL": 0.8, "Privé": 0.7}.get(statut, 1.0)
        cache[finess] = base * float(np.random.uniform(0.5, 1.5))
    return cache[finess]


def gen_pat_leaf(scale, age_sheet):
    """age_sheet ∈ {'<18','>=18'}. Renvoie dict mesure->val pour une ligne feuille."""
    if age_sheet == "<18":
        base = rint(np.random.gamma(1.4, 3) * scale + 0)
    else:
        base = rint(np.random.gamma(1.8, 9) * scale + 0)
    if base == 0:
        return {c: 0 for c in PAT_MEAS}
    nvx = rint(base * np.random.uniform(0.4, 0.65))
    sup75 = 0 if age_sheet == "<18" else rint(base * np.random.uniform(0.1, 0.4))
    chir = rint(base * np.random.uniform(0.2, 0.55))
    chimio = rint(base * np.random.uniform(0.15, 0.5))
    radio = rint(base * np.random.uniform(0.05, 0.35))
    return {9: base, 10: nvx, 11: sup75, 12: chir, 13: chimio, 14: radio}


def gen_sej_leaf(scale, age_sheet):
    if age_sheet == "<18":
        total = rint(np.random.gamma(1.5, 4) * scale)
    else:
        total = rint(np.random.gamma(2.0, 12) * scale)
    if total == 0:
        return {c: 0 for c in SEJ_MEAS}
    # composantes ≤ total
    chimio0 = rint(total * np.random.uniform(0.05, 0.3))
    radio0 = rint(total * np.random.uniform(0.02, 0.2))
    chir0 = rint(total * np.random.uniform(0.05, 0.25))
    autres0 = rint(total * np.random.uniform(0.05, 0.25))
    chir_p = rint(total * np.random.uniform(0.05, 0.3))
    j_chir = rint(chir_p * np.random.uniform(2, 8))       # journées ≥ séjours
    autres_p = rint(total * np.random.uniform(0.05, 0.25))
    j_autres = rint(autres_p * np.random.uniform(2, 8))
    pallia = rint(total * np.random.uniform(0.01, 0.1))
    journees = rint(total * np.random.uniform(2.5, 7))    # journées totales ≥ séjours
    non_chain = rint(total * np.random.uniform(0, 0.1))
    return {9: chimio0, 10: radio0, 11: chir0, 12: autres0,
            13: chir_p, 14: j_chir, 15: autres_p, 16: j_autres,
            17: pallia, 18: total, 19: journees, 20: non_chain}


def _row_key(ws, r):
    """Clé d'agrégation âge : (Niveau, Finess, Appareil, Organe, Année)."""
    return (ws.cell(r, 1).value, ws.cell(r, 3).value, ws.cell(r, 6).value,
            ws.cell(r, 7).value, ws.cell(r, 8).value)


def fill_regional(path_in, path_out, gen_leaf, meas_cols, hdr):
    print(f"Régional : lecture de {os.path.basename(path_in)} (peut être long)…")
    wb = openpyxl.load_workbook(path_in)
    sheet_vals = {}   # sheetname -> {rowidx: {col: val}}
    age_dicts = {}    # sheetname -> {key: {col: val}}  (toutes lignes)
    fcache = {}
    # 1) feuilles d'âge : génère feuilles 'Organe' puis agrège Appareil/Total
    for sname, tag in [("Age < 18 ans", "<18"), ("Age >= 18 ans", ">=18")]:
        ws = wb[sname]
        vals = {}
        leaf_idx = {}  # (finess, appareil, organe, année) -> dict
        for r in range(hdr + 1, ws.max_row + 1):
            niv = ws.cell(r, 1).value
            if niv in (None, ""):
                continue
            if niv == "Organe":
                finess = ws.cell(r, 3).value
                statut = ws.cell(r, 5).value
                annee = ws.cell(r, 8).value
                scale = _finess_factor(fcache, finess, statut) * COVID.get(annee, 1.0)
                v = gen_leaf(scale, tag)
                vals[r] = v
                leaf_idx[(finess, ws.cell(r, 6).value, ws.cell(r, 7).value, annee)] = v
        # agrégats Appareil (Σ organes même finess/appareil/année) et Total (Σ même finess/année)
        from collections import defaultdict
        by_app = defaultdict(lambda: {c: 0 for c in meas_cols})
        by_tot = defaultdict(lambda: {c: 0 for c in meas_cols})
        for (finess, app, org, annee), v in leaf_idx.items():
            ka = (finess, app, annee)
            kt = (finess, annee)
            for c in meas_cols:
                by_app[ka][c] += v[c]
                by_tot[kt][c] += v[c]
        for r in range(hdr + 1, ws.max_row + 1):
            niv = ws.cell(r, 1).value
            if niv == "Appareil":
                vals[r] = dict(by_app[(ws.cell(r, 3).value, ws.cell(r, 6).value, ws.cell(r, 8).value)])
            elif niv == "Total":
                vals[r] = dict(by_tot[(ws.cell(r, 3).value, ws.cell(r, 8).value)])
        sheet_vals[sname] = vals
        # index par clé pour la somme d'âges
        ad = {}
        for r, v in vals.items():
            ad[_row_key(ws, r)] = v
        age_dicts[sname] = ad
        print(f"  {sname}: {len(vals)} lignes remplies")
    # 2) onglet Total = Σ des deux feuilles d'âge, cellule à cellule
    ws = wb["Total"]
    d1 = age_dicts["Age < 18 ans"]
    d2 = age_dicts["Age >= 18 ans"]
    vals = {}
    miss = 0
    for r in range(hdr + 1, ws.max_row + 1):
        niv = ws.cell(r, 1).value
        if niv in (None, ""):
            continue
        k = _row_key(ws, r)
        v1 = d1.get(k); v2 = d2.get(k)
        if v1 is None and v2 is None:
            miss += 1
            vals[r] = {c: 0 for c in meas_cols}
            continue
        vals[r] = {c: (v1[c] if v1 else 0) + (v2[c] if v2 else 0) for c in meas_cols}
    sheet_vals["Total"] = vals
    print(f"  Total: {len(vals)} lignes (clé absente des 2 âges : {miss})")
    # 3) écriture
    for sname, vals in sheet_vals.items():
        ws = wb[sname]
        for r, v in vals.items():
            for c, x in v.items():
                ws.cell(r, c).value = x
    wb.save(path_out)
    print(f"  → écrit : {path_out}")


def main():
    fill_oeci()
    fill_regional(PAT_IN, PAT_OUT, gen_pat_leaf, PAT_MEAS, hdr=1)
    fill_regional(SEJ_IN, SEJ_OUT, gen_sej_leaf, SEJ_MEAS, hdr=2)
    print("\nTerminé.")


if __name__ == "__main__":
    main()
