#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Référentiels partagés — SOURCE UNIQUE des correspondances figées (cf. CLAUDE.md).

Module feuille : n'importe rien du projet (évite tout cycle). Regroupe ce qui était
dupliqué (``GHU_LIST`` dans chart_utils et run_reports) et les tables de
correspondance des loaders (nom GHU → code ; Statut établissement → type)."""

import unicodedata

# Période affichée (prod) : on ne conserve que ces années dans les CSV internes,
# bornes incluses. Le régional source couvre 2016-2025 ; on restreint à cette plage.
ANNEE_MIN = 2022
ANNEE_MAX = 2025

# Codes GHU internes — ordre d'affichage des rapports.
GHU_LIST = ["GHU Centre", "GHU Mondor", "GHU Nord", "GHU PSSD", "GHU PSL", "GHU SUN"]

# Appareil résiduel (catégorie « fourre-tout » PMSI) : exclu des affichages/agrégations
# par appareil, mais son rapport reste généré et accessible via un lien dédié.
APPAREIL_RESIDUEL = "Non décidable"

# Nom complet GHU (tel qu'écrit dans la colonne GHU des fichiers OECI) → code interne.
# La feuille « Survie globale » utilise une variante COURTE des libellés (différente des
# autres onglets) : on l'ajoute ici pour que _resoudre_entite couvre les deux conventions.
GHU_NOM2CODE = {
    # Forme longue (Indicateurs patient/séjour/chirurgie, Effectifs recherche, Délais PEC).
    "APHP.Centre-Université de Paris": "GHU Centre",
    "APHP.Nord-Université de Paris": "GHU Nord",
    "APHP.Hôpitaux Universitaires Henri-Mondor": "GHU Mondor",
    "APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis": "GHU PSSD",
    "APHP.Sorbonne Université": "GHU SUN",        # SUN = Sorbonne
    "APHP.Université Paris Saclay": "GHU PSL",     # PSL = Paris Saclay
    # Forme courte (feuille « Survie globale »).
    "AP-HP.Centre": "GHU Centre",
    "AP-HP.Nord": "GHU Nord",
    "AP-HP.Henri Mondor": "GHU Mondor",
    "AP-HP.Seine-Saint-Denis": "GHU PSSD",
    "AP-HP.Sorbonne Université": "GHU SUN",
    "AP-HP.Saclay": "GHU PSL",
}

# Hôpitaux EXCLUS des comparaisons inter-hôpitaux (survie ET délais) : sites SSR /
# gériatrie qui n'ont pas vocation à y figurer. « Survie globale » et « Délais PEC »
# orthographient les hôpitaux différemment → l'exclusion matche de façon NORMALISÉE
# (casse/accents/traits d'union) et couvre les variantes connues d'une feuille à l'autre.
HOPITAUX_EXCLUS_COMPARAISON = [
    "Joffre", "Hôtel-Dieu", "René Muret", "Charles Foix", "Bretonneau", "Sainte-Périne",
    "Rothschild", "Broca", "Corentin Celton", "Georges Clémenceau", "Emile Roux",
    # variantes d'orthographe selon la feuille :
    "Broca-La Collegiale",   # forme « Survie globale » de Broca
    "Saint Périne",          # forme « Survie globale » de Sainte-Périne (« Saint » sans e)
]


def _normaliser_hopital(nom):
    """Normalise un nom d'hôpital pour comparaison robuste : minuscules, suppression
    des accents, traits d'union → espaces, espaces compactés."""
    s = unicodedata.normalize("NFKD", str(nom or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))   # ôte les accents
    s = s.lower().replace("-", " ")
    return " ".join(s.split())


_HOPITAUX_EXCLUS_NORM = [_normaliser_hopital(h) for h in HOPITAUX_EXCLUS_COMPARAISON]


def _est_exclu(nom):
    """Vrai si ``nom`` correspond (forme normalisée) à une entrée de
    HOPITAUX_EXCLUS_COMPARAISON, soit à l'identique, soit comme forme ÉTENDUE
    (« entrée + espace + … », ex. « Broca-La Collegiale » exclu par « Broca »)."""
    n = _normaliser_hopital(nom)
    if not n:
        return False
    return any(n == e or n.startswith(e + " ") for e in _HOPITAUX_EXCLUS_NORM)


def entrees_exclusion_non_matchees(noms):
    """Garde-fou : entrées de HOPITAUX_EXCLUS_COMPARAISON ne matchant AUCUN des
    ``noms`` fournis (formes normalisées). Une entrée non matchée signale une coquille
    ou une variante d'orthographe non couverte. NB : il est normal qu'une entrée ne
    matche qu'UNE des deux pages (ex. « Joffre » = délais seul ; les variantes
    « Survie globale » = survie seule) → passer l'UNION des deux pages pour ne
    signaler que les entrées orphelines des DEUX côtés."""
    norms = [_normaliser_hopital(n) for n in noms]
    return [e for e, en in zip(HOPITAUX_EXCLUS_COMPARAISON, _HOPITAUX_EXCLUS_NORM)
            if not any(n == en or n.startswith(en + " ") for n in norms)]


# Statut d'établissement régional → type interne (appliqué si Hôpital AP-HP ≠ Oui).
STATUT2TYPE = {
    "Privé": "Clinique",
    "CH": "CH",
    "CHR/U": "CHU",
    "PSPH/EBNL": "PSPH",
    "CLCC": "CLCC",
}
