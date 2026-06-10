"""
run_reports.py
Script maître — génère tous les rapports HTML en une commande.

Chaîne (fictif) : templates/ → fill_fake_data → data/*.xlsx → export_internes →
data/*.csv → report_builder → output/*.html. Auto-suffisante sur clone neuf
(templates/ versionné, data/ recréé).

Usage :
    python run_reports.py              # Tout : données fictives + build
    python run_reports.py --data-only  # Phase données uniquement (xlsx + CSV)
    python run_reports.py --no-data    # Build uniquement, depuis les CSV existants
    python run_reports.py --real-data  # Source = fichiers réels (pas de génération fictive)
    python run_reports.py --ghu "GHU Nord"
    python run_reports.py --appareil "SEIN"
    python run_reports.py --organe "Sein" --appareil "SEIN"
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import fill_fake_data
from export_internes import exporter_csv
from pivot_loader import mapping_hopital_ghu
from report_builder import (
    build_index,
    build_rapport_global,
    build_rapport_ghu,
    build_rapport_appareil,
    build_rapport_organe,
    build_rapport_comparaison_hopitaux,
    load_aphp, load_regional, load_survival,
    set_fake_data,
)
from chart_utils import slugify
from referentiels import GHU_LIST   # source unique

DATA_DIR     = Path(__file__).parent / "data"
OUTPUT_DIR   = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _source_oeci_dir(fictif: bool) -> str:
    """Répertoire des xlsx OECI selon le mode (fictif → data/, réel → templates/),
    pour les lectures qui nécessitent les xlsx (ex. mapping hôpital→GHU)."""
    return str(DATA_DIR if fictif else TEMPLATES_DIR)


def generate_data(fictif: bool = True):
    """Phase données = (fictif) génération des xlsx depuis templates/ puis export
    CSV ; (réel) export CSV directement depuis les fichiers réels. Dans les deux
    cas, écrit les 3 CSV internes (aphp/survival/regional) dans data/."""
    DATA_DIR.mkdir(exist_ok=True)
    if fictif:
        print("\n[1/2] Génération des fichiers fictifs (templates/ → data/*.xlsx)...")
        fill_fake_data.main()
        print("\n[2/2] Export interne (xlsx fictifs → 3 CSV)...")
        exporter_csv(dossier_data=str(DATA_DIR), fictif=True)
    else:
        print("\n[1/1] Export interne depuis les fichiers RÉELS (→ 3 CSV)...")
        exporter_csv(dossier_data=str(DATA_DIR), fictif=False)


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

    print("\n  Page d'index...")
    build_index(DATA_DIR, OUTPUT_DIR)

    print("\n  Rapport global AP-HP...")
    build_rapport_global(DATA_DIR, OUTPUT_DIR)

    print("\n  Comparaison inter-hôpitaux (survie)...")
    mapping = mapping_hopital_ghu(_source_oeci_dir(fictif), fictif=fictif)
    build_rapport_comparaison_hopitaux(surv, mapping, OUTPUT_DIR)

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
        mapping = mapping_hopital_ghu(_source_oeci_dir(fictif), fictif=fictif)
        build_rapport_comparaison_hopitaux(surv, mapping, OUTPUT_DIR)
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
