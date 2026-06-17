#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chargement des fichiers RÉGIONAUX (canceroBR Pat + Sej) vers le FORMAT INTERNE
consommé par ``report_builder`` (pandas).

Comparaison AP-HP vs établissements franciliens. Convention temporelle OPPOSÉE à
l'OECI : ici l'année vient de la COLONNE ``Année`` (multi-années 2017→2025 dans un
seul fichier), pas du nom de fichier. Granularité = établissement (``N° Finess``) ;
3 onglets par tranche d'âge (``Total`` = ``<18`` + ``≥18``). On ne lit QUE l'onglet
``Total``.

Contrairement à l'OECI, on AGRÈGE bien (somme) les mesures par type d'établissement :
le fichier est par Finess, le tableau de bord compare par TYPE. On sélectionne donc
les lignes par ``Niveau`` (pré-roulées par établissement), puis on somme par type.

API publique :
    charger_regional(dossier="data", fictif=True) -> df_regional
"""
import os
import glob

import pandas as pd

# ───────────────────────── correspondances à figer ─────────────────────────
from referentiels import STATUT2TYPE   # source unique

ENTITES_REGIONAL = {"AP-HP", *STATUT2TYPE.values()}

SENTINELLE = "TOTAL"

# Les 8 premières colonnes (dimensions) sont identiques entre Pat et Sej — on les
# renomme par position (les libellés diffèrent : « Appareil patient » vs « séjour »).
DIMS = ["niveau", "hopital_aphp", "finess", "raison", "statut", "appareil", "organe", "annee"]

# Schéma de sortie (ordre EXACT).
COLS_REGIONAL = [
    "annee", "entite", "appareil", "organe",
    "nb_patients", "nb_nouveaux_patients",
    "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
    "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
]
MESURES_PAT = ["nb_patients", "nb_nouveaux_patients"]
MESURES_SEJ = ["nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
               "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]


# ───────────────────────────── utilitaires ─────────────────────────────────
def _to_num(serie):
    """Coerce une série en numérique, robuste au format français des vraies données :
    espaces de milliers (normaux ET insécables \\xa0), « % », virgule décimale. Les
    valeurs non convertibles (masquées, libellés…) deviennent NaN. Même logique que la
    coercition de la survie (pivot_loader)."""
    nettoye = (serie.astype(str)
               .str.replace("\xa0", "", regex=False)
               .str.replace(" ", "", regex=False)
               .str.replace("%", "", regex=False)
               .str.replace(",", ".", regex=False))
    return pd.to_numeric(nettoye, errors="coerce")


def _coercer(df, cols, label):
    """Coerce en place les colonnes ``cols`` de ``df`` via ``_to_num`` AVANT toute
    somme (pandas 2.x refuse d'additionner int + str). Logue un diagnostic distinguant
    les NOMBRES FORMATÉS récupérés (« 1 234 », « 12,5 ») des VRAIES valeurs non
    numériques tombées à NaN (masquage / libellés parasites)."""
    recuperes, masques = set(), set()
    for c in cols:
        if c not in df.columns:
            continue
        orig = df[c]
        brut = orig.astype(str)
        num = _to_num(orig)
        strip = brut.str.strip()
        # Marqueurs de cellule VIDE des vraies données : chaîne vide, NaN, OU uniquement
        # des points (« . », « .. » : convention « ligne vide » du canceroBR réel). On les
        # exclut du diagnostic — ce ne sont pas de vraies valeurs non numériques.
        vide = ((strip == "") | strip.str.fullmatch(r"\.+").fillna(False)
                | strip.str.lower().isin(["nan", "none"]))
        non_vide = orig.notna() & ~vide
        formate = brut.str.contains(r"[ \xa0,]", regex=True, na=False)
        recuperes.update(brut[num.notna() & formate & non_vide].unique().tolist())
        masques.update(brut[num.isna() & non_vide].unique().tolist())
        df[c] = num
    if recuperes:
        print(f"  Régional {label} : {len(recuperes)} valeur(s) au format FR récupérée(s), "
              f"ex. {sorted(recuperes)[:5]}")
    if masques:
        print(f"  Régional {label} : valeur(s) non numérique(s) → NaN, ex. {sorted(masques)[:10]}")
    return df


def _trouver_fichier(dossier, fictif, tag):
    """Chemin unique du fichier canceroBR ``tag`` ∈ {Pat, Sej}. En mode fictif on
    ne lit QUE les ``*_fictif.xlsx`` ; en mode réel on exclut les ``_fictif``."""
    cands = glob.glob(os.path.join(dossier, f"canceroBR_*_{tag}_*.xlsx"))
    if fictif:
        cands = [p for p in cands if p.endswith("_fictif.xlsx")]
    else:
        cands = [p for p in cands if "_fictif" not in os.path.basename(p)]
    if not cands:
        mode = "fictif" if fictif else "réel"
        raise FileNotFoundError(
            f"Aucun fichier régional {tag} ({mode}) dans {dossier!r} "
            f"(motif canceroBR_*_{tag}_*{'_fictif' if fictif else ''}.xlsx).")
    return sorted(cands)[0]


def _entite_regional(hopital_aphp, statut):
    """Hôpital AP-HP == 'Oui' → 'AP-HP' (prioritaire) ; sinon Statut → type."""
    if str(hopital_aphp).strip() == "Oui":
        return "AP-HP"
    return STATUT2TYPE.get(str(statut).strip())


def _lire_total(path, header):
    """Lit l'onglet ``Total``, normalise les 8 colonnes de dimension par position,
    ajoute ``entite`` et applique la sentinelle TOTAL selon ``Niveau``
    (Total → app+org ; Appareil → org ; Organe → rien)."""
    df = pd.read_excel(path, sheet_name="Total", header=header)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={df.columns[i]: DIMS[i] for i in range(len(DIMS))})
    df = df[df["niveau"].isin(("Total", "Appareil", "Organe"))].copy()
    df["entite"] = [_entite_regional(h, s) for h, s in zip(df["hopital_aphp"], df["statut"])]
    df = df[df["entite"].notna()].copy()
    # sentinelle pilotée par le Niveau (pas par le contenu des cellules)
    df.loc[df["niveau"] == "Total", ["appareil", "organe"]] = SENTINELLE
    df.loc[df["niveau"] == "Appareil", "organe"] = SENTINELLE
    return df


def _frame_patients(path):
    df = _lire_total(path, header=0)   # en-tête sur 1 ligne
    df = df.rename(columns={"Nb de patients": "nb_patients",
                            "Nouveaux patients": "nb_nouveaux_patients"})
    # Coercition numérique AVANT la somme (format FR : « 1 234 » → 1234).
    df = _coercer(df, MESURES_PAT, "patients")
    cle = ["annee", "entite", "appareil", "organe"]
    return df.groupby(cle, as_index=False)[MESURES_PAT].sum()


def _frame_sejours(path):
    df = _lire_total(path, header=1)   # en-tête sur 2 lignes (blocs 0 jour / >0 jour / Total)
    # nb_sejours_chirurgie = chirurgie « 0 jour » + « > 0 jour » : les deux colonnes
    # « Séjours avec chirurgie » (dédupliquées « .1 » par pandas) sont sommées.
    chir_cols = [c for c in df.columns if str(c).startswith("Séjours avec chirurgie")]
    if len(chir_cols) != 2:
        raise ValueError(f"Attendu 2 colonnes « Séjours avec chirurgie », trouvé {chir_cols}")
    # Coercer les 2 colonnes chirurgie AVANT la somme par ligne, puis la calculer.
    df = _coercer(df, chir_cols, "séjours chirurgie")
    df["nb_sejours_chirurgie"] = df[chir_cols].sum(axis=1)
    df = df.rename(columns={
        "Séjours avec chimio": "nb_sejours_chimiotherapie",
        "Séjours avec radiothérapie": "nb_sejours_radiotherapie",
        "Nb de séjours palliatifs": "nb_sejours_palliatifs",
    })
    # Coercer les autres mesures de séjours AVANT le groupby().sum().
    df = _coercer(df, ["nb_sejours_chimiotherapie", "nb_sejours_radiotherapie",
                       "nb_sejours_palliatifs"], "séjours")
    cle = ["annee", "entite", "appareil", "organe"]
    return df.groupby(cle, as_index=False)[MESURES_SEJ].sum()


# ──────────────────────────── assemblage public ────────────────────────────
def charger_regional(dossier="data", fictif=True):
    """Charge le régional → df_regional au format interne (une ligne par
    (annee, entite, appareil, organe) ; entite = TYPE d'établissement)."""
    pat = _frame_patients(_trouver_fichier(dossier, fictif, "Pat"))
    sej = _frame_sejours(_trouver_fichier(dossier, fictif, "Sej"))
    cle = ["annee", "entite", "appareil", "organe"]
    df = pat.merge(sej, on=cle, how="outer")
    mesures = MESURES_PAT + MESURES_SEJ
    df[mesures] = df[mesures].fillna(0)
    df["annee"] = df["annee"].round().astype(int)
    for c in mesures:
        df[c] = df[c].round().astype(int)
    return df[COLS_REGIONAL].sort_values(cle).reset_index(drop=True)


# ─────────────────────────── validation standalone ─────────────────────────
def _valider(df):
    pb = []
    if list(df.columns) != COLS_REGIONAL:
        pb.append(f"colonnes ≠ schéma : {list(df.columns)}")
    ent_inc = set(df["entite"]) - ENTITES_REGIONAL
    if ent_inc:
        pb.append(f"entite inattendues : {ent_inc}")
    # 3 granularités présentes
    g_total = ((df.appareil == SENTINELLE) & (df.organe == SENTINELLE)).sum()
    g_app = ((df.appareil != SENTINELLE) & (df.organe == SENTINELLE)).sum()
    g_org = ((df.appareil != SENTINELLE) & (df.organe != SENTINELLE)).sum()
    if g_total == 0:
        pb.append("aucune ligne TOTAL/TOTAL (compat report_builder)")
    if g_app == 0:
        pb.append("aucune ligne Appareil/TOTAL")
    if g_org == 0:
        pb.append("aucune ligne Appareil/Organe")
    # pas de NaN sur les mesures réellement consommées
    if int(df[["nb_patients", "nb_sejours_chirurgie"]].isna().sum().sum()) != 0:
        pb.append("NaN sur nb_patients / nb_sejours_chirurgie")
    return pb, (g_total, g_app, g_org)


def _main():
    print("Chargement régional fictif (data/)…")
    df = charger_regional("data", fictif=True)
    pb, (g_total, g_app, g_org) = _valider(df)

    print("\n=== df_regional ===")
    print(f"  lignes : {len(df):,}")
    print(f"  années : {sorted(df['annee'].unique())}")
    print(f"  entites : {sorted(df['entite'].unique())}")
    print(f"  granularités : TOTAL/TOTAL={g_total:,} | Appareil/TOTAL={g_app:,} | Appareil/Organe={g_org:,}")

    annee_ref = int(df["annee"].max())
    print(f"\n  Somme patients par type — année {annee_ref} (toutes localisations, TOTAL/TOTAL) :")
    tot = df[(df.annee == annee_ref) & (df.appareil == SENTINELLE) & (df.organe == SENTINELLE)]
    for _, row in tot.sort_values("nb_patients", ascending=False).iterrows():
        print(f"    {row.entite:>9} : {row.nb_patients:>9,} patients | chir {row.nb_sejours_chirurgie:>8,}")

    print("\n=== Validation ===")
    if pb:
        print(f"  {len(pb)} ANOMALIE(S) :")
        for m in pb:
            print(f"    - {m}")
    else:
        print("  OK — schéma, entités, granularités et mesures conformes.")
    print("  (Rappel : aucune égalité attendue AP-HP régional vs AP-HP OECI — "
          "sources et périmètres différents.)")


if __name__ == "__main__":
    _main()
