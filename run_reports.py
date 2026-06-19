"""
run_reports.py
Script maître — génère tous les rapports HTML en une commande.

Chaîne (fictif) : generateur_fictif → data/donnees.csv → report_builder →
output/*.html. Auto-suffisante sur clone neuf (génération 100 % par code, AUCUN
xlsx ni gabarit). En réel : chargeur YAML des vrais fichiers de data/ → donnees.csv.

Usage :
    python run_reports.py              # Tout : données fictives + build
    python run_reports.py --data-only  # Phase données uniquement (donnees.csv)
    python run_reports.py --no-data    # Build uniquement, depuis donnees.csv
    python run_reports.py --real-data  # Source = fichiers réels (pas de génération fictive)
    python run_reports.py --ghu "GHU Nord"
    python run_reports.py --appareil "SEIN"
    python run_reports.py --organe "Sein" --appareil "SEIN"
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from generateur_fictif import generer_donnees_long, HOPITAL2GHU
from export_internes import exporter_csv
from chargeur_long import mapping_hopital_ghu, mapping_hopital_ghu_delais
from report_builder import (
    build_rapport_global,
    build_rapport_ghu,
    build_rapport_appareil,
    build_rapport_organe,
    build_rapport_comparaison_hopitaux,
    build_rapport_comparaison_hopitaux_delais,
    load_aphp, load_regional, load_survival, load_delais_hopitaux,
    set_fake_data,
)
from chart_utils import slugify
from referentiels import GHU_LIST, entrees_exclusion_non_matchees   # source unique


def _verifier_exclusions(surv, mapping, delais_hop, mapping_delais):
    """Garde-fou : signale les entrées de HOPITAUX_EXCLUS_COMPARAISON ne matchant
    AUCUN hôpital sur AUCUNE des deux pages (survie ∪ délais) → coquille / variante
    d'orthographe non couverte. Une entrée matchant une seule page est NORMALE."""
    noms = (set(surv["entite"]) & set(mapping)) | (set(delais_hop["entite"]) & set(mapping_delais))
    orphelines = entrees_exclusion_non_matchees(noms)
    if orphelines:
        print(f"  ⚠ Exclusion : {len(orphelines)} entrée(s) ne matchant AUCUN hôpital "
              f"(coquille/variante ?) : {orphelines}")

DATA_DIR     = Path(__file__).parent / "data"
OUTPUT_DIR   = Path(__file__).parent / "output"


def generate_data(fictif: bool = True):
    """Phase données → ``data/donnees.csv`` (format pivot long). En FICTIF : générateur
    Option B (valeurs aléatoires depuis les référentiels, aucun xlsx). En RÉEL :
    ingestion des vrais fichiers de data/ via le chargeur YAML."""
    DATA_DIR.mkdir(exist_ok=True)
    if fictif:
        print("\n[Option B] Génération fictive directe → donnees.csv...")
        long = generer_donnees_long()
        long.to_csv(DATA_DIR / "donnees.csv", index=False, encoding="utf-8")
        print(f"  → donnees.csv  {len(long):>9,} lignes · sources {sorted(long['source'].unique())}")
    else:
        print("\n[Réel] Ingestion des fichiers RÉELS → donnees.csv...")
        exporter_csv(dossier_data=str(DATA_DIR), fictif=False,
                     dossier_source=str(DATA_DIR))


def _mappings(fictif: bool):
    """(mapping survie, mapping délais) hôpital→GHU. FICTIF : référentiel
    ``HOPITAL2GHU`` (aucun xlsx) ; RÉEL : dérivé des feuilles « Survie globale » /
    « Délais PEC » des vrais fichiers."""
    if fictif:
        return HOPITAL2GHU, HOPITAL2GHU
    return (mapping_hopital_ghu(str(DATA_DIR), fictif=False),
            mapping_hopital_ghu_delais(str(DATA_DIR), fictif=False))


def build_all_reports(fictif: bool = True):
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Pre-load dataframes once
    print("\n  Chargement des données...")
    aphp = load_aphp(DATA_DIR)
    reg  = load_regional(DATA_DIR)
    surv = load_survival(DATA_DIR)

    appareils = sorted(aphp[aphp.appareil != "TOTAL"].appareil.unique())

    # Organes par appareil
    organes_by_app = {}
    for app in appareils:
        orgs = sorted(aphp[(aphp.entite == "AP-HP") & (aphp.appareil == app) & (aphp.organe != "TOTAL")].organe.unique())
        organes_by_app[app] = orgs

    print("\n[Rapports HTML]")

    print("\n  Page d'accueil (global AP-HP → index.html)...")
    build_rapport_global(DATA_DIR, OUTPUT_DIR)

    mapping, mapping_delais = _mappings(fictif)

    print("\n  Comparaison inter-hôpitaux (survie)...")
    build_rapport_comparaison_hopitaux(surv, mapping, OUTPUT_DIR)

    print("\n  Comparaison inter-hôpitaux (délais)...")
    delais_hop = load_delais_hopitaux(DATA_DIR)
    build_rapport_comparaison_hopitaux_delais(delais_hop, mapping_delais, OUTPUT_DIR)

    _verifier_exclusions(surv, mapping, delais_hop, mapping_delais)

    print("\n  Rapports GHU individuels...")
    for ghu in GHU_LIST:
        out = build_rapport_ghu(ghu, DATA_DIR, OUTPUT_DIR)
        if out: print(f"    → {out.name}")

    print("\n  Rapports par appareil (AP-HP)...")
    for app in appareils:
        out = build_rapport_appareil(app, DATA_DIR, OUTPUT_DIR, entity="AP-HP",
                                     aphp=aphp, reg=reg, surv=surv)
        if out: print(f"    → {out.name}")

    print("\n  Rapports par appareil × GHU (84 fichiers)...")
    for app in appareils:
        for ghu in GHU_LIST:
            out = build_rapport_appareil(app, DATA_DIR, OUTPUT_DIR, entity=ghu,
                                         aphp=aphp, reg=reg, surv=surv)

    print("\n  Rapports par organe (AP-HP)...")
    for app, organes in organes_by_app.items():
        for org in organes:
            out = build_rapport_organe(org, app, DATA_DIR, OUTPUT_DIR, entity="AP-HP",
                                       aphp=aphp, reg=reg, surv=surv)

    print("\n  Rapports par organe × GHU...")
    for app, organes in organes_by_app.items():
        for org in organes:
            for ghu in GHU_LIST:
                out = build_rapport_organe(org, app, DATA_DIR, OUTPUT_DIR, entity=ghu,
                                           aphp=aphp, reg=reg, surv=surv)

    html_files = list(OUTPUT_DIR.glob("*.html"))
    print(f"\n✓ {len(html_files)} fichiers HTML générés dans output/")
    print(f"  Ouvrez output/index.html pour démarrer.\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only",  action="store_true")
    parser.add_argument("--no-data",    action="store_true")
    parser.add_argument("--real-data",  action="store_true",
                        help="Données réelles : supprime les avertissements 'données fictives'")
    parser.add_argument("--ghu",        type=str)
    parser.add_argument("--appareil",   type=str)
    parser.add_argument("--organe",     type=str)
    parser.add_argument("--comparaison-hopitaux", action="store_true",
                        help="Construit seulement la page de comparaison inter-hôpitaux")
    args = parser.parse_args()

    # --real-data est ORTHOGONAL à --no-data/--data-only : il change la SOURCE
    # (fichiers réels au lieu des fictifs) et masque les bandeaux « données fictives ».
    fictif = not args.real_data
    if args.real_data:
        set_fake_data(False)

    if not args.no_data:
        generate_data(fictif=fictif)

    if args.data_only:
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    if args.comparaison_hopitaux:
        surv = load_survival(DATA_DIR)
        mapping, mapping_delais = _mappings(fictif)
        build_rapport_comparaison_hopitaux(surv, mapping, OUTPUT_DIR)
        delais_hop = load_delais_hopitaux(DATA_DIR)
        build_rapport_comparaison_hopitaux_delais(delais_hop, mapping_delais, OUTPUT_DIR)
        _verifier_exclusions(surv, mapping, delais_hop, mapping_delais)
        return

    if args.ghu:
        build_rapport_ghu(args.ghu, DATA_DIR, OUTPUT_DIR)
        return

    if args.appareil and args.organe:
        aphp = load_aphp(DATA_DIR)
        reg  = load_regional(DATA_DIR)
        surv = load_survival(DATA_DIR)
        build_rapport_organe(args.organe, args.appareil, DATA_DIR, OUTPUT_DIR,
                             aphp=aphp, reg=reg, surv=surv)
        return

    if args.appareil:
        aphp = load_aphp(DATA_DIR)
        reg  = load_regional(DATA_DIR)
        surv = load_survival(DATA_DIR)
        build_rapport_appareil(args.appareil, DATA_DIR, OUTPUT_DIR,
                               aphp=aphp, reg=reg, surv=surv)
        return

    build_all_reports(fictif=fictif)


if __name__ == "__main__":
    main()
