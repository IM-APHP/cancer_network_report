#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format pivot LONG/tidy — conversion entre les tables larges internes et le
fichier unique ``donnees.csv``.

Source de vérité : ``docs/contrat_donnees_pivot.md``. Une ligne = une observation :

    (annee, source, niveau, entite, appareil, organe, age, stade, population, variable) → valeur

Ce module fournit les DEUX sens :
  - ``tables_vers_long(...)``  : 4 DataFrames larges → 1 DataFrame long (stockage).
  - ``pivoter_simple / pivoter_survie`` : long → large (vues de chargement).

Décisions actées (cf. contrat) :
  - ``nb_nouveaux_patients`` n'est PLUS une variable : c'est ``nb_patients`` +
    ``population = nouveaux``. Les vues larges la RECONSTRUISENT.
  - ``age = tous`` partout (dimension réservée, chantier différé).
  - ``stade`` vide hors survie.
  - Pas de bourrage NaN : on n'émet pas de ligne pour une valeur absente/masquée.
  - Les délais AP-HP/GHU apparaissent à la fois dans la table OECI (df_aphp) et la
    table délais-hôpitaux (valeurs identiques) : DÉDUPLIQUÉS sur la clé.
"""
import numpy as np
import pandas as pd

from referentiels import GHU_LIST, STATUT2TYPE

# Colonnes du format long (ordre canonique).
LONG_COLS = ["annee", "source", "niveau", "entite", "appareil", "organe",
             "age", "stade", "population", "variable", "valeur"]

# Clé d'unicité = tout sauf la valeur.
CLE_LONG = [c for c in LONG_COLS if c != "valeur"]

_GHU_SET = set(GHU_LIST)
_TYPE_ETAB_SET = set(STATUT2TYPE.values())   # {Clinique, CH, CHU, PSPH, CLCC}

# Sentinelle interne pour traverser pivot/unstack sans perdre les organes vides
# (NaN dans une clé d'index est silencieusement supprimé par pandas). Chaîne neutre
# (pas d'octet nul, qui ferait échouer le remplacement inverse) qui n'apparaît jamais
# comme vrai libellé d'organe.
_NA = "__ORGANE_VIDE__"

# Colonnes larges entières (à recaster en int après pivot ; jamais NaN dans nos
# données). Inclut ``nb_nouveaux_patients`` (colonne RECONSTRUITE depuis
# nb_patients/population=nouveaux), absente du vocabulaire des variables long.
_VARS_ENTIERES = {
    "nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
    "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie",
    "nb_sejours_palliatifs", "nb_patients_stade",
}


def niveau_depuis_entite(entite) -> str:
    """Grain d'une entité : AP-HP→aphp ; code GHU→ghu ; type d'établissement
    (referentiels.STATUT2TYPE)→type_etab ; tout le reste→hopital."""
    if entite == "AP-HP":
        return "aphp"
    if entite in _GHU_SET:
        return "ghu"
    if entite in _TYPE_ETAB_SET:
        return "type_etab"
    return "hopital"


# ─────────────────────────── large → long ──────────────────────────────────
def _melt_simple(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Tables comptes/délais (aphp, regional, délais-hôpitaux) : pas de ``stade`` ;
    ``nb_nouveaux_patients`` → ``nb_patients`` + ``population = nouveaux`` ; le reste
    en ``population = tous``."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLS)
    idv = ["annee", "entite", "appareil", "organe"]
    mesures = [c for c in df.columns if c not in idv]
    m = df.melt(id_vars=idv, value_vars=mesures, var_name="_m", value_name="valeur")
    m = m[m["valeur"].notna()].copy()                      # pas de bourrage NaN
    nouveaux = m["_m"] == "nb_nouveaux_patients"
    m["variable"] = np.where(nouveaux, "nb_patients", m["_m"])
    m["population"] = np.where(nouveaux, "nouveaux", "tous")
    m["source"] = source
    m["niveau"] = m["entite"].map(niveau_depuis_entite)
    m["age"] = "tous"
    m["stade"] = pd.NA
    return m[LONG_COLS]


def _melt_survie(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Survie : ``stade`` et ``population`` portés par les colonnes ; variables
    conservées telles quelles."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLS)
    idv = ["annee", "entite", "appareil", "organe", "stade", "population"]
    mesures = [c for c in ["nb_patients_stade", "survie_1an", "survie_5ans"]
               if c in df.columns]
    m = df.melt(id_vars=idv, value_vars=mesures, var_name="variable", value_name="valeur")
    m = m[m["valeur"].notna()].copy()                      # survie masquée → non émise
    m["source"] = source
    m["niveau"] = m["entite"].map(niveau_depuis_entite)
    m["age"] = "tous"
    return m[LONG_COLS]


def tables_vers_long(df_aphp, df_survie, df_regional, df_delais_hop) -> pd.DataFrame:
    """4 tables larges → format long unique. Les délais AP-HP/GHU présents à la fois
    dans ``df_aphp`` (DIM APHP) et ``df_delais_hop`` (valeurs identiques) sont
    dédupliqués ; ``df_aphp`` fournit le jeu de référence, ``df_delais_hop`` apporte
    en propre les délais niveau hôpital."""
    parts = [
        _melt_simple(df_aphp, "DIM APHP"),
        _melt_survie(df_survie, "EDS APHP"),
        _melt_simple(df_regional, "BN"),
        _melt_simple(df_delais_hop, "DIM APHP"),
    ]
    long = pd.concat(parts, ignore_index=True)
    long = long.drop_duplicates(subset=CLE_LONG, keep="first").reset_index(drop=True)
    return long[LONG_COLS]


# ─────────────────────────── long → large ──────────────────────────────────
def _restaurer_organe(serie: pd.Series) -> pd.Series:
    return serie.replace(_NA, np.nan)


def _caster_entiers(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if c in _VARS_ENTIERES and df[c].notna().all():
            df[c] = df[c].astype("int64")
    return df


def _pivoter_ordonne(d: pd.DataFrame, idx: list, champ_col: str) -> pd.DataFrame:
    """Pivote ``champ_col → colonnes`` en PRÉSERVANT l'ordre de première apparition
    des lignes. ``unstack`` trierait l'index, ce qui modifierait les départages de
    tri à valeur égale dans les graphiques de comparaison inter-hôpitaux (bars triées
    par survie/délai) → sortie non identique. On réindexe donc sur l'ordre d'origine
    (= ordre de génération porté par donnees.csv)."""
    d = d.copy()
    d["organe"] = d["organe"].fillna(_NA)
    ordre = list(dict.fromkeys(d[idx].itertuples(index=False, name=None)))
    wide = d.set_index(idx + [champ_col])["valeur"].unstack(champ_col)
    wide = wide.reindex(pd.MultiIndex.from_tuples(ordre, names=idx)).reset_index()
    wide.columns.name = None
    wide["organe"] = _restaurer_organe(wide["organe"])
    return _caster_entiers(wide)


def pivoter_simple(long: pd.DataFrame, source: str, niveaux, variables=None,
                   reconstruire_nouveaux=True) -> pd.DataFrame:
    """Vue large comptes/délais : filtre (source, niveaux[, variables]) puis pivote
    ``variable → colonnes``. ``nb_patients``/``population=nouveaux`` est restitué dans
    la colonne ``nb_nouveaux_patients`` (si ``reconstruire_nouveaux``). Index large :
    (annee, entite, appareil, organe)."""
    d = long[(long["source"] == source) & (long["niveau"].isin(niveaux))].copy()
    if variables is not None:
        d = d[d["variable"].isin(variables)]
    if d.empty:
        return pd.DataFrame(columns=["annee", "entite", "appareil", "organe"])
    # nom de colonne cible : nouveaux patients → colonne dédiée
    if reconstruire_nouveaux:
        nouveaux = (d["variable"] == "nb_patients") & (d["population"] == "nouveaux")
        d["col"] = np.where(nouveaux, "nb_nouveaux_patients", d["variable"])
    else:
        d["col"] = d["variable"]
    return _pivoter_ordonne(d, ["annee", "entite", "appareil", "organe"], "col")


def pivoter_survie(long: pd.DataFrame, source="EDS APHP") -> pd.DataFrame:
    """Vue large survie : index (annee, entite, appareil, organe, stade, population),
    colonnes = nb_patients_stade, survie_1an, survie_5ans."""
    d = long[long["source"] == source].copy()
    if d.empty:
        return pd.DataFrame(columns=["annee", "entite", "appareil", "organe",
                                     "stade", "population", "nb_patients_stade",
                                     "survie_1an", "survie_5ans"])
    return _pivoter_ordonne(
        d, ["annee", "entite", "appareil", "organe", "stade", "population"], "variable")
