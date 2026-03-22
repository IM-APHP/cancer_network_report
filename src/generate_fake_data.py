"""
generate_fake_data.py
Génère des données fictives réalistes pour le rapport d'activité cancérologie AP-HP.
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

# ── Configuration ─────────────────────────────────────────────────────────────

YEARS = [2019, 2020, 2021, 2022, 2023]

GHU_LIST = ["GHU Centre", "GHU Mondor", "GHU Nord", "GHU PSSD", "GHU PSL", "GHU SUN"]
ENTITIES = ["AP-HP"] + GHU_LIST

REGIONAL_TYPES = ["AP-HP", "Clinique", "CH", "CHU", "PSPH"]

# Multiplicateurs annuels (2020 = impact COVID)
YEAR_MULTIPLIERS = {
    2019: 1.000,
    2020: 0.918,
    2021: 1.032,
    2022: 1.044,
    2023: 1.035,
}

# Part de marché de chaque GHU dans l'AP-HP (peut dépasser 100% total car un patient
# peut être traité dans plusieurs GHU)
GHU_BASE_SHARE = {
    "GHU Centre": 0.155,
    "GHU Mondor": 0.185,
    "GHU Nord":   0.225,
    "GHU PSSD":   0.125,
    "GHU PSL":    0.255,
    "GHU SUN":    0.165,
}

# Poids relatif par appareil dans l'ensemble régional (AP-HP share ≈ 32%)
REGIONAL_BASE_SHARES = {
    "AP-HP":    0.32,
    "Clinique": 0.22,
    "CH":       0.28,
    "CHU":      0.12,
    "PSPH":     0.06,
}

# Patients AP-HP 2019 par appareil (base de référence)
APHP_BASE_2019 = {
    "APPAREIL DIGESTIF":                                           9_500,
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX":                      5_200,
    "GLANDES ENDOCRINES":                                          1_350,
    "HEMATOLOGIE":                                                 4_200,
    "ORGANES GENITAUX FEMININS":                                   2_350,
    "ORGANES GENITAUX MASCULINS":                                  5_800,
    "OS / TISSUS MOUS":                                              920,
    "PEAU":                                                        2_450,
    "SEIN":                                                        7_500,
    "SYSTÈME NERVEUX":                                             1_600,
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": 3_250,
    "VADS":                                                        3_050,
    "VOIES URINAIRES":                                             3_500,
    "ŒIL":                                                           360,
}

# Distribution des organes au sein de chaque appareil (poids normalisés)
ORGANE_WEIGHTS = {
    "APPAREIL DIGESTIF": {
        "Colon-Rectum-Anus":              0.40,
        "Foie et voies biliaires":         0.15,
        "Pancréas":                        0.12,
        "Estomac":                         0.12,
        "Oesophage":                       0.08,
        "Autre (appareil digestif)":       0.06,
        "Intestin grêle":                  0.04,
        "Péritoine-rétropéritoine":        0.03,
    },
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX": {
        "Trachée, bronches, poumon":       0.75,
        "Plèvre":                          0.10,
        "Médiastin":                       0.08,
        "Autre (appareil respiratoire)":   0.07,
    },
    "GLANDES ENDOCRINES": {
        "Thyroïde":                        0.75,
        "Surrénale":                       0.12,
        "Autre (glandes endocrines)":      0.13,
    },
    "HEMATOLOGIE": {
        "Lymphome non Hodgkinien":                         0.24,
        "Myélome multiple et tumeur maligne à plasmocytes": 0.14,
        "Maladie myéloproliférative et syndrome myélodysplasique": 0.12,
        "Leucémie lymphoïde aigue":                        0.10,
        "Leucémie myéloïde aigue":                         0.10,
        "Leucémie lymphoïde, chronique ou non précisé":    0.08,
        "Lymphome Hodgkinien":                             0.07,
        "Leucémie myéloïde, chronique ou non précisé":     0.05,
        "Maladie immunoproliférative maligne":             0.03,
        "Leucémie aigue, autre":                           0.02,
        "Leucémie monocytaire aigue":                      0.015,
        "Leucémie chronique ou non précisé, autre":        0.01,
        "Leucémie monocytaire, chronique ou non précisé":  0.01,
        "Autre (hématologie)":                             0.025,
    },
    "ORGANES GENITAUX FEMININS": {
        "Corps utérus":                            0.38,
        "Ovaire":                                  0.30,
        "Col utérus":                              0.18,
        "Vulve et vagin":                          0.08,
        "Autre (organes génitaux féminins)":       0.06,
    },
    "ORGANES GENITAUX MASCULINS": {
        "Prostate":                                0.80,
        "Testicule":                               0.10,
        "Verge":                                   0.05,
        "Autre (organes génitaux masculins)":      0.05,
    },
    "OS / TISSUS MOUS": {
        "Os, articulations, cartilage articulaire": 0.55,
        "Tissus mous, nca":                        0.45,
    },
    "PEAU": {
        "Mélanome":                                0.70,
        "Autre (peau)":                            0.30,
    },
    "SEIN": {
        "Sein":                                    1.00,
    },
    "SYSTÈME NERVEUX": {
        "Système nerveux central":                 0.80,
        "Nerfs périphériques":                     0.20,
    },
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": {
        "T.M. secondaires et sièges mal définis":  1.00,
    },
    "VADS": {
        "Pharynx":                                 0.28,
        "Larynx":                                  0.22,
        "Cavité orale":                            0.20,
        "Langue":                                  0.12,
        "Fosses nasales, sinus, oreille moy/int":  0.08,
        "Glandes salivaires":                      0.05,
        "Lèvre":                                   0.03,
        "Autre (VADS)":                            0.02,
    },
    "VOIES URINAIRES": {
        "Rein":                                    0.45,
        "Vessie":                                  0.38,
        "Voies urinaires hautes":                  0.10,
        "Autre (voies urinaires)":                 0.07,
    },
    "ŒIL": {
        "Œil":                                     1.00,
    },
}

# Taux de recours aux soins par appareil (séjours / patients)
# (chirurgie, chimiothérapie, radiothérapie, soins_palliatifs)
TREATMENT_RATES = {
    "APPAREIL DIGESTIF":           (0.80, 0.65, 0.35, 0.12),
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX": (0.35, 0.75, 0.55, 0.18),
    "GLANDES ENDOCRINES":          (0.85, 0.20, 0.45, 0.04),
    "HEMATOLOGIE":                 (0.05, 1.20, 0.15, 0.12),
    "ORGANES GENITAUX FEMININS":   (0.70, 0.65, 0.60, 0.10),
    "ORGANES GENITAUX MASCULINS":  (0.55, 0.50, 0.65, 0.08),
    "OS / TISSUS MOUS":            (0.75, 0.50, 0.40, 0.10),
    "PEAU":                        (0.90, 0.30, 0.25, 0.05),
    "SEIN":                        (0.75, 0.85, 0.70, 0.06),
    "SYSTÈME NERVEUX":             (0.60, 0.55, 0.45, 0.15),
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": (0.20, 0.65, 0.30, 0.25),
    "VADS":                        (0.70, 0.60, 0.75, 0.12),
    "VOIES URINAIRES":             (0.80, 0.55, 0.40, 0.08),
    "ŒIL":                         (0.70, 0.25, 0.30, 0.05),
}

# Spécialisation de chaque GHU par appareil (multiplicateur de la part de base)
GHU_SPECIALTY = {
    "GHU Centre": {
        "SEIN": 1.30, "ORGANES GENITAUX FEMININS": 1.35, "SYSTÈME NERVEUX": 1.40,
    },
    "GHU Mondor": {
        "APPAREIL DIGESTIF": 1.25, "VOIES URINAIRES": 1.30, "ORGANES GENITAUX MASCULINS": 1.20,
    },
    "GHU Nord": {
        "APPAREIL RESPIRATOIRE ET AUTRES THORAX": 1.45, "VADS": 1.35, "HEMATOLOGIE": 1.20,
    },
    "GHU PSSD": {
        "PEAU": 1.55, "ŒIL": 1.80, "OS / TISSUS MOUS": 1.35,
    },
    "GHU PSL": {
        "HEMATOLOGIE": 1.50, "SYSTÈME NERVEUX": 1.60,
        "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": 1.30,
    },
    "GHU SUN": {
        "GLANDES ENDOCRINES": 1.60, "ORGANES GENITAUX FEMININS": 1.20, "SEIN": 1.15,
    },
}

# Taux de nouveaux patients (proportion des patients vus pour la 1ère fois)
NEW_PATIENT_RATE_BASE = 0.48

# Délais médians de prise en charge par appareil (jours)
# (global, chirurgie, chimiothérapie, radiothérapie)
DELAY_BASE = {
    "APPAREIL DIGESTIF":     (38, 45, 22, 40),
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX": (30, 38, 18, 32),
    "GLANDES ENDOCRINES":    (42, 50, 25, 45),
    "HEMATOLOGIE":           (22, 15, 12, 28),
    "ORGANES GENITAUX FEMININS": (35, 42, 22, 38),
    "ORGANES GENITAUX MASCULINS": (45, 52, 28, 48),
    "OS / TISSUS MOUS":      (40, 48, 25, 42),
    "PEAU":                  (32, 38, 20, 35),
    "SEIN":                  (28, 35, 18, 30),
    "SYSTÈME NERVEUX":       (25, 30, 18, 28),
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": (28, 35, 18, 30),
    "VADS":                  (32, 40, 20, 35),
    "VOIES URINAIRES":       (42, 50, 25, 45),
    "ŒIL":                   (38, 45, 25, 40),
}

# Taux de survie par stade : [(survie_1an, survie_5ans), ...] pour stades I, II, III, IV
SURVIVAL_RATES = {
    "SEIN":                  [(99, 98), (97, 85), (90, 66), (72, 20)],
    "APPAREIL DIGESTIF":     [(93, 91), (87, 78), (72, 58), (35,  9)],
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX": [(65, 52), (45, 28), (30, 15), (18, 4)],
    "GLANDES ENDOCRINES":    [(100, 99), (99, 97), (95, 85), (75, 50)],
    "HEMATOLOGIE":           [(88, 80), (83, 70), (72, 60), (62, 45)],
    "ORGANES GENITAUX FEMININS": [(93, 85), (85, 72), (70, 55), (40, 18)],
    "ORGANES GENITAUX MASCULINS": [(99, 97), (98, 95), (92, 85), (55, 30)],
    "OS / TISSUS MOUS":      [(88, 75), (75, 60), (60, 45), (35, 20)],
    "PEAU":                  [(99, 98), (92, 87), (78, 65), (45, 20)],
    "SYSTÈME NERVEUX":       [(90, 70), (75, 50), (55, 30), (35, 10)],
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": [(75, 55), (60, 40), (45, 25), (25, 8)],
    "VADS":                  [(90, 85), (82, 70), (70, 55), (50, 30)],
    "VOIES URINAIRES":       [(96, 95), (82, 75), (68, 60), (25, 10)],
    "ŒIL":                   [(97, 90), (88, 78), (72, 58), (45, 25)],
}

# Distribution des patients par stade [I, II, III, IV, Non précisé]
STAGE_DIST = {
    "SEIN":                  [0.40, 0.35, 0.15, 0.08, 0.02],
    "APPAREIL DIGESTIF":     [0.20, 0.30, 0.30, 0.18, 0.02],
    "APPAREIL RESPIRATOIRE ET AUTRES THORAX": [0.15, 0.15, 0.25, 0.40, 0.05],
    "GLANDES ENDOCRINES":    [0.55, 0.25, 0.12, 0.05, 0.03],
    "HEMATOLOGIE":           [0.22, 0.25, 0.28, 0.20, 0.05],
    "ORGANES GENITAUX FEMININS": [0.30, 0.30, 0.25, 0.12, 0.03],
    "ORGANES GENITAUX MASCULINS": [0.35, 0.35, 0.20, 0.08, 0.02],
    "OS / TISSUS MOUS":      [0.25, 0.30, 0.28, 0.15, 0.02],
    "PEAU":                  [0.45, 0.30, 0.15, 0.08, 0.02],
    "SYSTÈME NERVEUX":       [0.20, 0.25, 0.30, 0.22, 0.03],
    "T.M. SECONDAIRES, SIEGES MAL DEFINIS ET AUTRES LOCALISATIONS": [0.10, 0.20, 0.30, 0.35, 0.05],
    "VADS":                  [0.20, 0.30, 0.30, 0.18, 0.02],
    "VOIES URINAIRES":       [0.35, 0.30, 0.22, 0.10, 0.03],
    "ŒIL":                   [0.40, 0.30, 0.18, 0.10, 0.02],
}
STAGES = ["I", "II", "III", "IV", "Non précisé"]

# Multiplicateurs de délai selon année (COVID allonge les délais en 2020-2021)
DELAY_YEAR_MULT = {2019: 1.00, 2020: 1.18, 2021: 1.08, 2022: 1.02, 2023: 1.00}


# ── Fonctions utilitaires ──────────────────────────────────────────────────────

def cum_multiplier(year: int) -> float:
    """Multiplicateur cumulatif depuis 2019."""
    m = 1.0
    for y in YEARS:
        if y > YEARS[0] and y <= year:
            m *= YEAR_MULTIPLIERS[y]
    return m


def jitter(scale: float = 0.03) -> float:
    return 1 + np.random.normal(0, scale)


def make_row(annee, entite_or_type, key, appareil, organe, nb_patients, rates, new_rate, is_regional, delays=None):
    """Construit un dict de ligne pour le DataFrame."""
    base = dict(
        annee=annee,
        appareil=appareil,
        organe=organe,
        nb_patients=max(0, nb_patients),
        nb_nouveaux_patients=max(0, int(nb_patients * new_rate * jitter(0.04))),
        nb_sejours_chirurgie=max(0, int(nb_patients * rates[0] * jitter(0.04))),
        nb_sejours_chimiotherapie=max(0, int(nb_patients * rates[1] * jitter(0.04))),
        nb_sejours_radiotherapie=max(0, int(nb_patients * rates[2] * jitter(0.04))),
        nb_sejours_palliatifs=max(0, int(nb_patients * rates[3] * jitter(0.04))),
    )
    if delays is not None:
        ym = DELAY_YEAR_MULT.get(annee, 1.0)
        base["delai_global_median"]    = max(5, int(delays[0] * ym * jitter(0.08)))
        base["delai_chirurgie_median"] = max(5, int(delays[1] * ym * jitter(0.08)))
        base["delai_chimio_median"]    = max(3, int(delays[2] * ym * jitter(0.08)))
        base["delai_radio_median"]     = max(5, int(delays[3] * ym * jitter(0.08)))
    else:
        base["delai_global_median"]    = None
        base["delai_chirurgie_median"] = None
        base["delai_chimio_median"]    = None
        base["delai_radio_median"]     = None
    if is_regional:
        base["type_etab"] = key
    else:
        base["entite"] = key
    return base


# ── Génération des données AP-HP ───────────────────────────────────────────────

def generate_aphp_data() -> pd.DataFrame:
    """Génère les données institutionnelles AP-HP (AP-HP + chaque GHU)."""
    rows = []

    for year in YEARS:
        mult = cum_multiplier(year)

        for appareil, base_pts in APHP_BASE_2019.items():
            rates = TREATMENT_RATES[appareil]
            delays = DELAY_BASE[appareil]

            # ── Niveau AP-HP ──
            aphp_pts = max(0, int(base_pts * mult * jitter(0.02)))
            rows.append(make_row(year, "AP-HP", "AP-HP", appareil, "TOTAL",
                                 aphp_pts, rates, NEW_PATIENT_RATE_BASE, False, delays=delays))

            for organe, w in ORGANE_WEIGHTS[appareil].items():
                org_pts = max(0, int(aphp_pts * w * jitter(0.04)))
                rows.append(make_row(year, "AP-HP", "AP-HP", appareil, organe,
                                     org_pts, rates, NEW_PATIENT_RATE_BASE, False, delays=delays))

            # ── Niveau GHU ──
            for ghu in GHU_LIST:
                spec = GHU_SPECIALTY.get(ghu, {}).get(appareil, 1.0)
                share = min(GHU_BASE_SHARE[ghu] * spec, 0.45)
                ghu_pts = max(0, int(aphp_pts * share * jitter(0.03)))
                rows.append(make_row(year, ghu, ghu, appareil, "TOTAL",
                                     ghu_pts, rates, NEW_PATIENT_RATE_BASE, False, delays=delays))

                for organe, w in ORGANE_WEIGHTS[appareil].items():
                    org_pts = max(0, int(ghu_pts * w * jitter(0.05)))
                    rows.append(make_row(year, ghu, ghu, appareil, organe,
                                         org_pts, rates, NEW_PATIENT_RATE_BASE, False, delays=delays))

    df = pd.DataFrame(rows)

    # Calcul des totaux toutes pathologies confondues
    total_rows = []
    for year in YEARS:
        for entite in ENTITIES:
            sub = df[(df.annee == year) & (df.entite == entite) & (df.organe == "TOTAL")]
            total_rows.append({
                "annee": year, "entite": entite,
                "appareil": "TOTAL", "organe": "TOTAL",
                "nb_patients": sub.nb_patients.sum(),
                "nb_nouveaux_patients": sub.nb_nouveaux_patients.sum(),
                "nb_sejours_chirurgie": sub.nb_sejours_chirurgie.sum(),
                "nb_sejours_chimiotherapie": sub.nb_sejours_chimiotherapie.sum(),
                "nb_sejours_radiotherapie": sub.nb_sejours_radiotherapie.sum(),
                "nb_sejours_palliatifs": sub.nb_sejours_palliatifs.sum(),
                "delai_global_median": None,
                "delai_chirurgie_median": None,
                "delai_chimio_median": None,
                "delai_radio_median": None,
            })

    df = pd.concat([pd.DataFrame(total_rows), df], ignore_index=True)
    return df.sort_values(["annee", "entite", "appareil", "organe"]).reset_index(drop=True)


# ── Génération des données régionales ─────────────────────────────────────────

def generate_regional_data() -> pd.DataFrame:
    """Génère les données de contexte régional (Clinique, CH, CHU, PSPH, AP-HP)."""
    rows = []

    # Profils de prise en charge selon type d'établissement
    ETAB_PROFILES = {
        "AP-HP":    (1.00, 1.00, 1.00, 1.00),
        "Clinique": (1.25, 0.70, 0.60, 0.40),
        "CH":       (0.90, 0.85, 0.70, 0.90),
        "CHU":      (1.05, 1.10, 1.00, 1.00),
        "PSPH":     (0.85, 1.00, 0.90, 0.80),
    }

    for year in YEARS:
        mult = cum_multiplier(year)

        for appareil, base_pts in APHP_BASE_2019.items():
            rates = TREATMENT_RATES[appareil]
            delays = DELAY_BASE[appareil]
            aphp_pts = base_pts * mult
            regional_total = aphp_pts / REGIONAL_BASE_SHARES["AP-HP"]

            for type_etab, share in REGIONAL_BASE_SHARES.items():
                profile = ETAB_PROFILES[type_etab]
                etab_pts = max(0, int(regional_total * share * jitter(0.04)))
                adj_rates = tuple(r * p for r, p in zip(rates, profile))

                rows.append(make_row(year, type_etab, type_etab, appareil, "TOTAL",
                                     etab_pts, adj_rates, NEW_PATIENT_RATE_BASE, True, delays=delays))

                for organe, w in ORGANE_WEIGHTS[appareil].items():
                    org_pts = max(0, int(etab_pts * w * jitter(0.05)))
                    rows.append(make_row(year, type_etab, type_etab, appareil, organe,
                                         org_pts, adj_rates, NEW_PATIENT_RATE_BASE, True, delays=delays))

    df = pd.DataFrame(rows)

    total_rows = []
    for year in YEARS:
        for type_etab in REGIONAL_TYPES:
            sub = df[(df.annee == year) & (df.type_etab == type_etab) & (df.organe == "TOTAL")]
            total_rows.append({
                "annee": year, "type_etab": type_etab,
                "appareil": "TOTAL", "organe": "TOTAL",
                "nb_patients": sub.nb_patients.sum(),
                "nb_nouveaux_patients": sub.nb_nouveaux_patients.sum(),
                "nb_sejours_chirurgie": sub.nb_sejours_chirurgie.sum(),
                "nb_sejours_chimiotherapie": sub.nb_sejours_chimiotherapie.sum(),
                "nb_sejours_radiotherapie": sub.nb_sejours_radiotherapie.sum(),
                "nb_sejours_palliatifs": sub.nb_sejours_palliatifs.sum(),
            })

    df = pd.concat([pd.DataFrame(total_rows), df], ignore_index=True)
    return df.sort_values(["annee", "type_etab", "appareil", "organe"]).reset_index(drop=True)


# ── Données de survie ─────────────────────────────────────────────────────────

def generate_survival_data() -> pd.DataFrame:
    """Génère les données de survie par stade pour AP-HP et chaque GHU."""
    rows = []

    for year in YEARS:
        mult = cum_multiplier(year)
        # Légère amélioration de la survie au fil des ans (+0.3% /an)
        survival_trend = 1 + (year - 2019) * 0.003

        for appareil, base_pts in APHP_BASE_2019.items():
            aphp_pts = int(base_pts * mult)
            stage_dist = STAGE_DIST[appareil]
            surv_rates = SURVIVAL_RATES[appareil]

            for entity in ["AP-HP"] + GHU_LIST:
                if entity == "AP-HP":
                    ent_pts = aphp_pts
                else:
                    spec = GHU_SPECIALTY.get(entity, {}).get(appareil, 1.0)
                    ent_pts = int(aphp_pts * min(GHU_BASE_SHARE[entity] * spec, 0.45))

                # Par appareil (organe = TOTAL)
                for i, stade in enumerate(STAGES):
                    if stade == "Non précisé":
                        s1an = int(np.mean([r[0] for r in surv_rates]) * survival_trend)
                        s5ans = int(np.mean([r[1] for r in surv_rates]) * survival_trend)
                        dist_w = stage_dist[4]
                    else:
                        s1an = min(100, int(surv_rates[i][0] * survival_trend * jitter(0.02)))
                        s5ans = min(100, int(surv_rates[i][1] * survival_trend * jitter(0.02)))
                        dist_w = stage_dist[i]

                    nb_stade = max(1, int(ent_pts * dist_w * jitter(0.05)))
                    rows.append({
                        "annee": year, "entite": entity,
                        "appareil": appareil, "organe": "TOTAL",
                        "stade": stade, "nb_patients_stade": nb_stade,
                        "survie_1an": s1an, "survie_5ans": s5ans,
                    })

                # Par organe
                for organe, w in ORGANE_WEIGHTS[appareil].items():
                    org_pts = int(ent_pts * w)
                    for i, stade in enumerate(STAGES):
                        if stade == "Non précisé":
                            s1an = int(np.mean([r[0] for r in surv_rates]) * survival_trend)
                            s5ans = int(np.mean([r[1] for r in surv_rates]) * survival_trend)
                            dist_w = stage_dist[4]
                        else:
                            s1an = min(100, int(surv_rates[i][0] * survival_trend * jitter(0.03)))
                            s5ans = min(100, int(surv_rates[i][1] * survival_trend * jitter(0.03)))
                            dist_w = stage_dist[i]

                        nb_stade = max(1, int(org_pts * dist_w * jitter(0.06)))
                        rows.append({
                            "annee": year, "entite": entity,
                            "appareil": appareil, "organe": organe,
                            "stade": stade, "nb_patients_stade": nb_stade,
                            "survie_1an": s1an, "survie_5ans": s5ans,
                        })

    df = pd.DataFrame(rows)
    return df.sort_values(["annee", "entite", "appareil", "organe", "stade"]).reset_index(drop=True)


# ── Point d'entrée ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    print("Génération des données AP-HP...")
    aphp_df = generate_aphp_data()
    aphp_df.to_csv(data_dir / "aphp_data.csv", index=False)
    print(f"  → {len(aphp_df):,} lignes  →  data/aphp_data.csv")

    print("Génération des données régionales...")
    regional_df = generate_regional_data()
    regional_df.to_csv(data_dir / "regional_data.csv", index=False)
    print(f"  → {len(regional_df):,} lignes  →  data/regional_data.csv")

    print("Génération des données de survie...")
    survival_df = generate_survival_data()
    survival_df.to_csv(data_dir / "survival_data.csv", index=False)
    print(f"  → {len(survival_df):,} lignes  →  data/survival_data.csv")

    print("\nAperçu AP-HP (total):")
    print(aphp_df[(aphp_df.entite == "AP-HP") & (aphp_df.appareil == "TOTAL")][
        ["annee", "nb_patients", "nb_nouveaux_patients",
         "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
         "nb_sejours_radiotherapie"]
    ].to_string(index=False))
