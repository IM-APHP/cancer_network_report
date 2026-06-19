#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Générateur fictif — Option B : produit ``data/donnees.csv`` (format pivot LONG du
contrat) DIRECTEMENT depuis des référentiels de dimensions, SANS aucun xlsx ni loader.

Producteur fictif autonome : aucune dépendance à un gabarit ni à un xlsx
(plus de fichiers `templates/` ni `*_fictif.xlsx`). Valeurs aléatoires plausibles, seed fixe,
respectant le contrat (survie ∈ [0,100], délais ≥ 0, comptes ≥ 0 ; stade/population
uniquement où applicable ; age=tous). Une MINORITÉ de valeurs de survie est masquée
(non émise → « — » dans la démo).

Cohérence : les comptes OECI sont générés par HÔPITAL puis agrégés hôpital→GHU→AP-HP
(les parts de marché GHU restent crédibles) ; les délais agrègent en moyenne pondérée.
La survie est générée par niveau (organe / appareil / total) avec des effectifs
décroissants, ordres I-III > IV et 1 an > 5 ans garantis. Le régional est généré par
TYPE d'établissement, indépendamment de l'AP-HP OECI (sources/périmètres distincts).

API :
    generer_donnees_long(seed=42) -> pd.DataFrame   (schéma format_long.LONG_COLS)
    HOPITAL2GHU                                       (hôpital → code GHU, pages inter-hôpitaux)
"""
import numpy as np
import pandas as pd

from referentiels import GHU_LIST, STATUT2TYPE, ANNEE_MIN, ANNEE_MAX
from format_long import LONG_COLS

SENTINELLE = "TOTAL"

# ── Référentiels de dimensions (relevés sur la structure réelle) ────────────────
APPAREIL_ORGANES = {
    'APPAREIL DIGESTIF': ['Autre (appareil digestif)', 'Colon-Rectum-Anus', 'Estomac', 'Foie et voies biliaires', 'Intestin grêle', 'Non décidable', 'Oesophage', 'Pancréas', 'Péritoine-rétropéritoine'],
    'APPAREIL RESPIRATOIRE ET AUTRES THORAX': ['Autre (appareil respiratoire)', 'Médiastin', 'Non décidable', 'Plèvre', 'Trachée, bronches, poumon'],
    'GLANDES ENDOCRINES': ['Autre (glandes endocrines)', 'Non décidable', 'Surrénale', 'Thyroïde'],
    'HEMATOLOGIE': ['Autre (hématologie)', 'Leucémie aigue, autre', 'Leucémie chronique ou non précisé, autre', 'Leucémie lymphoïde aigue', 'Leucémie lymphoïde, chronique ou non précisé', 'Leucémie monocytaire aigue', 'Leucémie monocytaire, chronique ou non précisé', 'Leucémie myéloïde aigue', 'Leucémie myéloïde, chronique ou non précisé', 'Lymphome Hodgkinien', 'Lymphome non Hodgkinien', 'Maladie immunoproliférative maligne', 'Maladie myéloproliférative et syndrome myélodysplasique', 'Myélome multiple et tumeur maligne à plasmocytes', 'Non décidable'],
    'Non décidable': ['Non décidable'],
    'ORGANES GENITAUX FEMININS': ['Autre (organes génitaux féminins)', 'Col utérus', 'Corps utérus', 'Non décidable', 'Ovaire', 'Vulve et vagin'],
    'ORGANES GENITAUX MASCULINS': ['Autre (organes génitaux masculins)', 'Non décidable', 'Prostate', 'Testicule', 'Verge'],
    'OS / TISSUS MOUS': ['Non décidable', 'Os, articulations, cartilage articulaire', 'Tissus mous, nca'],
    'PEAU': ['Autre (peau)', 'Mélanome', 'Non décidable'],
    'SEIN': None,
    'SYSTÈME NERVEUX': ['Autre (SNC)', 'Nerfs périphériques', 'Non décidable', 'Système nerveux central'],
    'T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS': None,
    'VADS': ['Autre (VADS)', 'Cavité orale', 'Fosses nasales, sinus, oreille moy/int', 'Glandes salivaires', 'Langue', 'Larynx', 'Lèvre', 'Non décidable', 'Pharynx'],
    'VOIES URINAIRES': ['Autre (voies urinaires)', 'Non décidable', 'Rein', 'Vessie', 'Voies urinaires hautes'],
    'ŒIL': None,
}

# Hôpital → code GHU (relevé sur « Délais PEC » réel). Sert AUSSI de mapping pour les
# pages de comparaison inter-hôpitaux en mode fictif (aucun xlsx à lire).
HOPITAL2GHU = {
    'Broca': 'GHU Centre', 'Cochin': 'GHU Centre', 'Corentin Celton': 'GHU Centre',
    'Hegp': 'GHU Centre', 'Hôtel-Dieu': 'GHU Centre', 'Necker': 'GHU Centre',
    'Emile Roux': 'GHU Mondor', 'Georges Clémenceau': 'GHU Mondor',
    'Henri Mondor': 'GHU Mondor', 'Joffre': 'GHU Mondor',
    'Avicenne': 'GHU PSSD', 'Jean Verdier': 'GHU PSSD', 'René Muret': 'GHU PSSD',
    'Beaujon': 'GHU Nord', 'Bichat': 'GHU Nord', 'Bretonneau': 'GHU Nord',
    'Lariboisière': 'GHU Nord', 'Louis Mourier': 'GHU Nord', 'Robert Debré': 'GHU Nord',
    'Saint-Louis': 'GHU Nord',
    'Armand Trousseau': 'GHU SUN', 'Charles Foix': 'GHU SUN', 'Pitie-Salpêtrière': 'GHU SUN',
    'Rothschild': 'GHU SUN', 'Saint-Antoine': 'GHU SUN', 'Tenon': 'GHU SUN',
    'Ambroise Paré': 'GHU PSL', 'Antoine Beclère': 'GHU PSL', 'Bicêtre': 'GHU PSL',
    'Paul Brousse': 'GHU PSL', 'Raymond Poincaré': 'GHU PSL', 'Sainte-Perine': 'GHU PSL',
}
HOPITAUX = list(HOPITAL2GHU)
TYPE_ETAB = sorted(set(STATUT2TYPE.values()))            # Clinique, CH, CHU, PSPH, CLCC
ANNEES = tuple(range(ANNEE_MIN, ANNEE_MAX + 1))          # 2022..2025

_SEJOURS = ["nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
            "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]
_SEJOUR_RATIO = {"nb_sejours_chirurgie": (0.25, 0.55), "nb_sejours_chimiotherapie": (0.20, 0.55),
                 "nb_sejours_radiotherapie": (0.10, 0.40), "nb_sejours_palliatifs": (0.05, 0.20)}
_DELAIS = ["delai_global_median", "delai_chirurgie_median",
           "delai_traitement_medical_median", "delai_radio_median"]
_SEUIL_MASQUAGE = 5                                      # survie masquée si nb_stade < 5


def _organes(ap):
    o = APPAREIL_ORGANES[ap]
    return o if o else [None]                            # mono-organe → organe vide (NaN)


def _ligne(rows, an, source, niveau, entite, app, org, variable, population, valeur,
           stade=None):
    rows.append({"annee": an, "source": source, "niveau": niveau, "entite": entite,
                 "appareil": app, "organe": org, "age": "tous", "stade": stade,
                 "population": population, "variable": variable, "valeur": valeur})


def _emettre_comptes(rows, an, source, niveau, entite, app, org, c, delais=None):
    """Émet les comptes (et délais) d'une cellule. ``c`` = dict de mesures."""
    _ligne(rows, an, source, niveau, entite, app, org, "nb_patients", "tous", c["nb_patients"])
    _ligne(rows, an, source, niveau, entite, app, org, "nb_patients", "nouveaux", c["nb_nouveaux"])
    for s in _SEJOURS:
        _ligne(rows, an, source, niveau, entite, app, org, s, "tous", c[s])
    if delais:
        for d in _DELAIS:
            _ligne(rows, an, source, niveau, entite, app, org, d, "tous", delais[d])


# ── Génération ──────────────────────────────────────────────────────────────────
def _generer_oeci(rows, rng):
    """Comptes + délais DIM APHP : hôpital × appareil × organe, agrégés hôpital→GHU→
    AP-HP (comptes sommés, délais en moyenne pondérée par les patients)."""
    taille_hop = {h: rng.uniform(0.4, 1.8) for h in HOPITAUX}
    freq = {(ap, org): rng.uniform(0.3, 1.7)
            for ap in APPAREIL_ORGANES for org in _organes(ap)}
    fac_an = {a: 0.95 + 0.035 * (a - ANNEE_MIN) for a in ANNEES}   # légère croissance

    for ap in APPAREIL_ORGANES:
        for org in _organes(ap):
            f = freq[(ap, org)]
            for an in ANNEES:
                yf = fac_an[an]
                feuilles = {}                            # hop → (comptes, délais)
                for h in HOPITAUX:
                    base = int(max(2, round(rng.gamma(2.2, 13) * f * taille_hop[h] * yf)))
                    c = {"nb_patients": base,
                         "nb_nouveaux": int(round(base * rng.uniform(0.40, 0.60)))}
                    for s, (lo, hi) in _SEJOUR_RATIO.items():
                        c[s] = int(round(base * rng.uniform(lo, hi)))
                    dg = round(rng.uniform(18, 38), 1)
                    delais = {"delai_global_median": dg,
                              "delai_chirurgie_median": round(dg + rng.uniform(2, 10), 1),
                              "delai_traitement_medical_median": round(dg + rng.uniform(-3, 5), 1),
                              "delai_radio_median": round(dg + rng.uniform(5, 16), 1)}
                    feuilles[h] = (c, delais)
                    _emettre_comptes(rows, an, "DIM APHP", "hopital", h, ap, org, c, delais)

                def _agg(hops):
                    c = {k: sum(feuilles[h][0][k] for h in hops)
                         for k in ["nb_patients", "nb_nouveaux", *_SEJOURS]}
                    w = c["nb_patients"] or 1
                    delais = {d: round(sum(feuilles[h][1][d] * feuilles[h][0]["nb_patients"]
                                           for h in hops) / w, 1) for d in _DELAIS}
                    return c, delais

                for ghu in GHU_LIST:
                    hops = [h for h in HOPITAUX if HOPITAL2GHU[h] == ghu]
                    c, delais = _agg(hops)
                    _emettre_comptes(rows, an, "DIM APHP", "ghu", ghu, ap, org, c, delais)
                c, delais = _agg(HOPITAUX)
                _emettre_comptes(rows, an, "DIM APHP", "aphp", "AP-HP", ap, org, c, delais)


def _survie_bloc(rng, taille):
    """(nb_I-III, nb_IV, s1_I-III, s5_I-III, s1_IV, s5_IV) plausibles, ordres garantis."""
    nb13 = int(max(1, round(rng.gamma(3.0, taille))))
    nb4 = int(round(nb13 * rng.uniform(0.25, 0.52)))
    s5_13 = rng.uniform(55, 88)
    s5_4 = rng.uniform(8, max(10, s5_13 - 6))
    s1_13 = min(99.0, s5_13 + rng.uniform(6, 14))
    s1_4 = min(s1_13 - 3, s5_4 + rng.uniform(8, 20))
    return nb13, nb4, round(s1_13, 1), round(s5_13, 1), round(s1_4, 1), round(s5_4, 1)


def _emettre_survie(rows, rng, an, niveau, entite, app, org, taille):
    """Émet la survie d'une cellule (I-III & IV × tous & nouveaux). nb_patients_stade
    toujours émis ; survie MASQUÉE (non émise → « — ») pour les PETITS effectifs
    (< 5 patients), comme le secret statistique réel : ne touche jamais les grands
    totaux, frappe les stades IV de localisations rares et les petits hôpitaux."""
    for pop, ech in (("tous", 1.0), ("nouveaux", 0.6)):
        nb13, nb4, s1_13, s5_13, s1_4, s5_4 = _survie_bloc(rng, taille)
        nb13 = int(round(nb13 * ech)); nb4 = int(round(nb4 * ech))
        for stade, nb, s1, s5 in (("I-III", nb13, s1_13, s5_13), ("IV", nb4, s1_4, s5_4)):
            _ligne(rows, an, "EDS APHP", niveau, entite, app, org,
                   "nb_patients_stade", pop, nb, stade=stade)
            if nb >= _SEUIL_MASQUAGE:                     # < 5 patients → survie masquée
                _ligne(rows, an, "EDS APHP", niveau, entite, app, org,
                       "survie_1an", pop, s1, stade=stade)
                _ligne(rows, an, "EDS APHP", niveau, entite, app, org,
                       "survie_5ans", pop, s5, stade=stade)


def _generer_survie(rows, rng):
    """Survie EDS APHP. aphp/ghu : organe + appareil(TOTAL) + grand total. hopital :
    appareil(TOTAL) + grand total seulement (l'organe-niveau hôpital n'est pas affiché).
    Effectifs décroissants organe < appareil < total ; entités plus petites pour GHU/hôp."""
    niveaux = [("aphp", ["AP-HP"], 1.0), ("ghu", GHU_LIST, 0.6), ("hopital", HOPITAUX, 0.4)]
    for niveau, entites, ech in niveaux:
        for entite in entites:
            for an in ANNEES:
                for ap in APPAREIL_ORGANES:
                    if niveau != "hopital":
                        for org in _organes(ap):
                            _emettre_survie(rows, rng, an, niveau, entite, ap, org,
                                            taille=18 * ech)
                    # niveau appareil (organe=TOTAL)
                    _emettre_survie(rows, rng, an, niveau, entite, ap, SENTINELLE,
                                    taille=46 * ech)
                # grand total (appareil=TOTAL, organe=TOTAL)
                _emettre_survie(rows, rng, an, niveau, entite, SENTINELLE, SENTINELLE,
                                taille=170 * ech)


def _generer_regional(rows, rng):
    """Régional BN : AP-HP + types d'établissement, par appareil × organe. Périmètre
    indépendant de l'OECI (aucune égalité attendue). Pas de délais."""
    entites = [("aphp", "AP-HP", 1.0)] + [("type_etab", t, rng.uniform(0.3, 1.4)) for t in TYPE_ETAB]
    freq = {(ap, org): rng.uniform(0.3, 1.7)
            for ap in APPAREIL_ORGANES for org in _organes(ap)}
    fac_an = {a: 0.95 + 0.035 * (a - ANNEE_MIN) for a in ANNEES}
    for niveau, entite, taille in entites:
        for ap in APPAREIL_ORGANES:
            for org in _organes(ap):
                for an in ANNEES:
                    base = int(max(3, round(rng.gamma(2.2, 16) * freq[(ap, org)]
                                            * taille * fac_an[an])))
                    c = {"nb_patients": base,
                         "nb_nouveaux": int(round(base * rng.uniform(0.40, 0.60)))}
                    for s, (lo, hi) in _SEJOUR_RATIO.items():
                        c[s] = int(round(base * rng.uniform(lo, hi)))
                    _emettre_comptes(rows, an, "BN", niveau, entite, ap, org, c)


def generer_donnees_long(seed=42):
    """Produit le DataFrame long complet (DIM APHP + EDS APHP + BN)."""
    rng = np.random.default_rng(seed)
    rows = []
    _generer_oeci(rows, rng)
    _generer_survie(rows, rng)
    _generer_regional(rows, rng)
    df = pd.DataFrame(rows, columns=LONG_COLS)
    return df.reset_index(drop=True)


if __name__ == "__main__":
    d = generer_donnees_long()
    print(f"{len(d):,} lignes · sources {sorted(d['source'].unique())} · "
          f"variables {d['variable'].nunique()}")
