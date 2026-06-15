#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Référentiels partagés — SOURCE UNIQUE des correspondances figées (cf. CLAUDE.md).

Module feuille : n'importe rien du projet (évite tout cycle). Regroupe ce qui était
dupliqué (``GHU_LIST`` dans chart_utils et run_reports) et les tables de
correspondance des loaders (nom GHU → code ; Statut établissement → type)."""

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
GHU_NOM2CODE = {
    "APHP.Centre-Université de Paris": "GHU Centre",
    "APHP.Nord-Université de Paris": "GHU Nord",
    "APHP.Hôpitaux Universitaires Henri-Mondor": "GHU Mondor",
    "APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis": "GHU PSSD",
    "APHP.Sorbonne Université": "GHU SUN",        # SUN = Sorbonne
    "APHP.Université Paris Saclay": "GHU PSL",     # PSL = Paris Saclay
}

# Statut d'établissement régional → type interne (appliqué si Hôpital AP-HP ≠ Oui).
STATUT2TYPE = {
    "Privé": "Clinique",
    "CH": "CH",
    "CHR/U": "CHU",
    "PSPH/EBNL": "PSPH",
    "CLCC": "CLCC",
}
