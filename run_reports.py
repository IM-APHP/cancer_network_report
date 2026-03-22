"""
run_reports.py
Script maître — génère tous les rapports HTML en une commande.

Usage :
    python run_reports.py              # Tout générer
    python run_reports.py --data-only  # Données uniquement
    python run_reports.py --no-data    # Ne pas régénérer les données
    python run_reports.py --ghu "GHU Nord"
    python run_reports.py --appareil "SEIN"
    python run_reports.py --organe "Sein" --appareil "SEIN"
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from generate_fake_data import generate_aphp_data, generate_regional_data, generate_survival_data
from report_builder import (
    build_index,
    build_rapport_global,
    build_rapport_ghu,
    build_rapport_appareil,
    build_rapport_organe,
    load_aphp, load_regional, load_survival,
)
from chart_utils import slugify

DATA_DIR   = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"

GHU_LIST = ["GHU Centre", "GHU Mondor", "GHU Nord", "GHU PSSD", "GHU PSL", "GHU SUN"]


def generate_data():
    DATA_DIR.mkdir(exist_ok=True)
    print("\n[1/3] Génération des données AP-HP...")
    df = generate_aphp_data()
    df.to_csv(DATA_DIR / "aphp_data.csv", index=False)
    print(f"  → {len(df):,} lignes")

    print("[2/3] Génération des données régionales...")
    df_reg = generate_regional_data()
    df_reg.to_csv(DATA_DIR / "regional_data.csv", index=False)
    print(f"  → {len(df_reg):,} lignes")

    print("[3/3] Génération des données de survie...")
    df_surv = generate_survival_data()
    df_surv.to_csv(DATA_DIR / "survival_data.csv", index=False)
    print(f"  → {len(df_surv):,} lignes")


def build_all_reports():
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
    parser.add_argument("--data-only", action="store_true")
    parser.add_argument("--no-data",   action="store_true")
    parser.add_argument("--ghu",       type=str)
    parser.add_argument("--appareil",  type=str)
    parser.add_argument("--organe",    type=str)
    args = parser.parse_args()

    if not args.no_data:
        generate_data()

    if args.data_only:
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

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

    build_all_reports()


if __name__ == "__main__":
    main()
