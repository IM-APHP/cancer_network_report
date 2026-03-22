"""
report_builder.py
Construit les rapports HTML à partir des données.
Chaque fonction retourne une chaîne HTML complète (page autonome).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

from chart_utils import (
    line_evolution, bar_comparison, stacked_treatments,
    donut_market_share, heatmap_appareils, waterfall_trends,
    kpi_indicators, regional_comparison, fig_to_html,
    heatmap_organes, treemap_organes,
    survival_by_stage, survival_evolution,
    delay_evolution, delay_comparison_bar,
    slugify,
    GHU_LIST, TREATMENT_COLS,
)

# ── Template HTML ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --primary:   #003189;
    --secondary: #E63946;
    --bg:        #F8F9FA;
    --card:      #FFFFFF;
    --text:      #1A1A2E;
    --muted:     #6C757D;
    --border:    #DEE2E6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Inter, Arial, sans-serif; background: var(--bg); color: var(--text); }}

  /* Header */
  .report-header {{
    background: linear-gradient(135deg, var(--primary) 0%, #1a4080 100%);
    color: white; padding: 28px 40px; display: flex;
    justify-content: space-between; align-items: center;
  }}
  .report-header h1 {{ font-size: 1.7rem; font-weight: 700; letter-spacing: -0.5px; }}
  .report-header .subtitle {{ font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }}
  .report-header .badge {{
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3);
    padding: 6px 16px; border-radius: 20px; font-size: 0.85rem;
  }}

  /* Nav */
  .report-nav {{
    background: white; border-bottom: 2px solid var(--primary);
    padding: 0 40px; display: flex; gap: 0; overflow-x: auto;
    position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,.08);
  }}
  .report-nav a {{
    display: block; padding: 14px 20px; color: var(--muted);
    text-decoration: none; font-size: 0.88rem; font-weight: 500;
    white-space: nowrap; border-bottom: 2px solid transparent; margin-bottom: -2px;
    transition: color 0.2s, border-color 0.2s;
  }}
  .report-nav a:hover {{ color: var(--primary); border-color: var(--primary); }}

  /* Content */
  .report-content {{ padding: 32px 40px; max-width: 1400px; margin: 0 auto; }}

  /* Section */
  .section {{ margin-bottom: 48px; }}
  .section-title {{
    font-size: 1.25rem; font-weight: 700; color: var(--primary);
    border-left: 4px solid var(--primary); padding-left: 12px;
    margin-bottom: 20px;
  }}

  /* KPI Cards */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{
    background: var(--card); border-radius: 10px; padding: 20px 24px;
    border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }}
  .kpi-card .label {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }}
  .kpi-card .value {{ font-size: 2rem; font-weight: 700; color: var(--text); line-height: 1; }}
  .kpi-card .delta {{ font-size: 0.82rem; margin-top: 6px; }}
  .kpi-card .delta.up   {{ color: #2A9D8F; }}
  .kpi-card .delta.down {{ color: var(--secondary); }}
  .kpi-card .delta.covid{{ color: #F4A261; }}

  /* Chart grid */
  .chart-grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .chart-grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
  .chart-card {{
    background: var(--card); border-radius: 10px; padding: 16px;
    border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }}
  .chart-card.full {{ grid-column: 1 / -1; }}

  /* Bandeau données fictives */
  .fake-data-banner {{
    background: #FFF3CD; border-bottom: 3px solid #F4A261;
    padding: 10px 40px; font-size: 0.88rem; color: #856404;
    display: flex; align-items: center; gap: 10px;
    font-weight: 500;
  }}
  .fake-data-banner strong {{ color: #6c4a00; }}

  /* COVID badge */
  .covid-note {{
    background: #FFF3CD; border: 1px solid #FFECB5; border-radius: 6px;
    padding: 8px 14px; font-size: 0.82rem; color: #856404;
    display: inline-flex; align-items: center; gap: 6px; margin-bottom: 16px;
  }}

  /* Footer */
  .report-footer {{
    background: var(--text); color: rgba(255,255,255,0.6);
    text-align: center; padding: 20px; font-size: 0.78rem; margin-top: 48px;
  }}

  @media (max-width: 900px) {{
    .chart-grid-2, .chart-grid-3 {{ grid-template-columns: 1fr; }}
    .report-content {{ padding: 20px; }}
    .report-header {{ padding: 20px; flex-direction: column; gap: 12px; }}
  }}
</style>
</head>
<body>

<header class="report-header">
  <div>
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
  </div>
  <div class="badge">Données fictives — 2019–2023</div>
</header>

<nav class="report-nav">
{nav_links}
</nav>

<div class="fake-data-banner">
  ⚠ <strong>DONNÉES FICTIVES</strong> — Ce rapport est généré à partir de données entièrement simulées à titre illustratif.
  Les chiffres présentés ne reflètent pas la réalité clinique et ne doivent pas être utilisés à des fins médicales, administratives ou décisionnelles.
</div>

<main class="report-content">
{content}
</main>

<footer class="report-footer">
  AP-HP — Rapport d'activité cancérologie &nbsp;|&nbsp;
  Généré le {date} &nbsp;|&nbsp;
  Indicateurs OECI — Données simulées à titre illustratif
</footer>
</body>
</html>
"""


def fmt_nb(n: int) -> str:
    """Formate un nombre avec espace comme séparateur de milliers."""
    return f"{int(n):,}".replace(",", "\u202f")


def delta_html(val: float, ref: float, invert: bool = False) -> str:
    """Renvoie un badge HTML pour la variation vs N-1."""
    if ref == 0:
        return ""
    pct = (val - ref) / ref * 100
    up = pct >= 0
    if invert:
        up = not up
    cls = "up" if up else "down"
    arrow = "▲" if pct >= 0 else "▼"
    # Flag COVID year
    return f'<span class="delta {cls}">{arrow} {abs(pct):.1f}% vs N-1</span>'


def kpi_card(label: str, value: int, ref: int = None, invert: bool = False, covid_year: bool = False) -> str:
    delta = ""
    if ref is not None:
        if covid_year:
            delta = f'<span class="delta covid">⚠ Année COVID-19</span>'
        else:
            delta = delta_html(value, ref, invert)
    return f"""
    <div class="kpi-card">
      <div class="label">{label}</div>
      <div class="value">{fmt_nb(value)}</div>
      {delta}
    </div>"""


def section(title: str, content: str, anchor: str = "") -> str:
    anch = f' id="{anchor}"' if anchor else ""
    return f"""
<div class="section"{anch}>
  <h2 class="section-title">{title}</h2>
  {content}
</div>"""


def chart_card(html: str, cls: str = "") -> str:
    return f'<div class="chart-card {cls}">{html}</div>'


def chart_grid(charts: list, cols: int = 2) -> str:
    inner = "\n".join(chart_card(c) for c in charts)
    return f'<div class="chart-grid-{cols}">{inner}</div>'


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_aphp(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "aphp_data.csv")


def load_regional(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "regional_data.csv")


def load_survival(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "survival_data.csv")


# ── Rapport global AP-HP ───────────────────────────────────────────────────────

def build_rapport_global(data_dir: Path, output_dir: Path) -> Path:
    aphp = load_aphp(data_dir)
    reg  = load_regional(data_dir)
    surv = load_survival(data_dir)

    # Sous-ensembles utiles
    aphp_total = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL")]
    ghu_total  = aphp[(aphp.entite.isin(GHU_LIST)) & (aphp.appareil == "TOTAL")]

    years = sorted(aphp_total.annee.unique())
    last_year = years[-1]
    prev_year = years[-2]

    lv = aphp_total[aphp_total.annee == last_year].iloc[0]
    pv = aphp_total[aphp_total.annee == prev_year].iloc[0]

    # ── KPI ──
    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card("Patients (total)", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += kpi_card("Séjours radiothérapie", lv.nb_sejours_radiotherapie, pv.nb_sejours_radiotherapie)
    kpis_html += kpi_card("Soins palliatifs", lv.nb_sejours_palliatifs, pv.nb_sejours_palliatifs)
    kpis_html += "</div>"

    covid_note = '<div class="covid-note">⚠ L\'année 2020 est marquée par l\'impact de la pandémie COVID-19 sur l\'activité hospitalière.</div>'

    # ── Graphiques évolution globale ──
    fig_pts = line_evolution(aphp_total, "annee", "nb_patients", "entite",
                             "Évolution du nombre de patients — AP-HP")
    fig_new = line_evolution(aphp_total, "annee", "nb_nouveaux_patients", "entite",
                             "Évolution des nouveaux patients — AP-HP")

    # Séjours par type (AP-HP)
    melted = aphp_total.melt(
        id_vars=["annee"],
        value_vars=list(TREATMENT_COLS.keys()),
        var_name="type_sejour", value_name="nb_sejours",
    )
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 "Évolution des séjours par mode de prise en charge",
                                 entities=list(TREATMENT_COLS.values()))

    # Waterfall
    fig_wf = waterfall_trends(aphp_total, "Variation annuelle du nombre de patients — AP-HP")

    # ── Parts de marché GHU ──
    ghu_last = ghu_total[ghu_total.annee == last_year]
    fig_donut = donut_market_share(ghu_last, "entite", "nb_patients",
                                   f"Répartition par GHU — {last_year}")
    fig_ghu_bar = bar_comparison(ghu_total, "annee", "nb_patients", "entite",
                                 "Patients par GHU — évolution", barmode="group",
                                 entities=GHU_LIST)

    # ── Heatmap appareils ──
    fig_heat = heatmap_appareils(aphp, "AP-HP", title="Évolution par appareil (index, moy=1) — AP-HP")

    # ── Contexte régional ──
    reg_total = reg[(reg.appareil == "TOTAL")]
    fig_reg_pts = regional_comparison(reg_total, "nb_patients",
                                      "Patients — AP-HP vs contexte régional")
    fig_reg_chir = regional_comparison(reg_total, "nb_sejours_chirurgie",
                                       "Séjours chirurgie — AP-HP vs contexte régional")

    # ── Assembly HTML ──
    content = ""

    content += section("Indicateurs clés — " + str(last_year), kpis_html + covid_note, "kpis")

    content += section("Évolution globale du nombre de patients", f"""
        {covid_note}
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts))}
          {chart_card(fig_to_html(fig_new))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_wf))}
          {chart_card(fig_to_html(fig_sejours))}
        </div>
    """, "evolution")

    content += section("Répartition entre les groupes hospitaliers (GHU)", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_donut))}
          {chart_card(fig_to_html(fig_ghu_bar))}
        </div>
    """, "ghu")

    content += section("Analyse par appareil pathologique", f"""
        {chart_card(fig_to_html(fig_heat), "full")}
    """, "appareils")

    content += section("Contexte régional", f"""
        <p style="margin-bottom:16px;font-size:.9rem;color:var(--muted)">
          Comparaison avec les autres types d'établissements de la région Île-de-France
          (Cliniques, Centres Hospitaliers, CHU, PSPH).
        </p>
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_reg_pts))}
          {chart_card(fig_to_html(fig_reg_chir))}
        </div>
    """, "regional")

    # Survie SEIN (référence)
    fig_surv_sein = survival_by_stage(surv, "AP-HP", "SEIN", year=last_year)
    content += section("Survie — SEIN (référence AP-HP)", f"""
        {chart_card(fig_to_html(fig_surv_sein))}
    """, "survie")

    nav = "\n".join([
        '<a href="index.html">Accueil</a>',
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#evolution">Évolution globale</a>',
        '<a href="#ghu">Groupes hospitaliers</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#regional">Contexte régional</a>',
        '<a href="#survie">Survie</a>',
    ])

    html = HTML_TEMPLATE.format(
        title="Rapport d'activité cancérologie — AP-HP",
        subtitle="Vue d'ensemble · 2019–2023 · Indicateurs OECI",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    out = output_dir / "rapport_global_aphp.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out


# ── Rapport individuel GHU ─────────────────────────────────────────────────────

def build_rapport_ghu(ghu_name: str, data_dir: Path, output_dir: Path) -> Path:
    aphp = load_aphp(data_dir)
    surv = load_survival(data_dir)

    ghu_total = aphp[(aphp.entite == ghu_name) & (aphp.appareil == "TOTAL")]
    aphp_total = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL")]

    years = sorted(ghu_total.annee.unique())
    last_year = years[-1]
    prev_year = years[-2]

    lv = ghu_total[ghu_total.annee == last_year].iloc[0]
    pv = ghu_total[ghu_total.annee == prev_year].iloc[0]

    # KPI
    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card("Patients (total)", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += kpi_card("Séjours radiothérapie", lv.nb_sejours_radiotherapie, pv.nb_sejours_radiotherapie)
    kpis_html += "</div>"

    # Graphiques
    compare = pd.concat([ghu_total, aphp_total])
    fig_pts = line_evolution(compare, "annee", "nb_patients", "entite",
                             f"Patients — {ghu_name} vs AP-HP",
                             entities=[ghu_name, "AP-HP"])
    fig_new = line_evolution(compare, "annee", "nb_nouveaux_patients", "entite",
                             f"Nouveaux patients — {ghu_name} vs AP-HP",
                             entities=[ghu_name, "AP-HP"])

    # Part de marché de ce GHU
    share_data = ghu_total.copy()
    aphp_ref = aphp_total.copy()
    share_data["part_marche"] = share_data["nb_patients"].values / aphp_ref["nb_patients"].values * 100
    fig_share = line_evolution(share_data, "annee", "part_marche", "entite",
                               f"Part de marché dans l'AP-HP — {ghu_name} (%)",
                               entities=[ghu_name])

    # Séjours
    melted = ghu_total.melt(
        id_vars=["annee"], value_vars=list(TREATMENT_COLS.keys()),
        var_name="type_sejour", value_name="nb_sejours",
    )
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 f"Séjours par mode de prise en charge — {ghu_name}",
                                 entities=list(TREATMENT_COLS.values()))

    # Heatmap appareils
    fig_heat = heatmap_appareils(aphp, ghu_name, title=f"Évolution par appareil — {ghu_name}")

    # Survie (stade II comme représentatif)
    fig_surv = survival_by_stage(surv, ghu_name, "SEIN", year=last_year)
    fig_delay = delay_evolution(aphp, ghu_name, "SEIN")

    nav = "\n".join([
        '<a href="rapport_global_aphp.html">← AP-HP Global</a>',
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#sejours">Séjours</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#survie">Survie</a>',
    ])

    content = ""
    content += section(f"Indicateurs clés — {last_year}", kpis_html, "kpis")
    content += section("Évolution — Patients", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts))}
          {chart_card(fig_to_html(fig_new))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_share))}
          {chart_card(fig_to_html(fig_sejours))}
        </div>
    """, "evolution")
    content += section("Analyse par appareil pathologique",
                       chart_card(fig_to_html(fig_heat), "full"), "appareils")
    content += section("Survie et délais — SEIN (exemple)", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_surv))}
          {chart_card(fig_to_html(fig_delay))}
        </div>
    """, "survie")

    html = HTML_TEMPLATE.format(
        title=f"Rapport d'activité — {ghu_name}",
        subtitle=f"Activité cancérologie · 2019–2023 · Indicateurs OECI",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    slug = ghu_name.lower().replace(" ", "_")
    out = output_dir / f"rapport_{slug}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out


# ── Rapport par appareil ───────────────────────────────────────────────────────

def build_rapport_appareil(appareil: str, data_dir: Path, output_dir: Path,
                            entity: str = "AP-HP",
                            aphp: pd.DataFrame = None,
                            reg: pd.DataFrame = None,
                            surv: pd.DataFrame = None) -> Path:
    if aphp is None: aphp = load_aphp(data_dir)
    if reg  is None: reg  = load_regional(data_dir)
    if surv is None: surv = load_survival(data_dir)

    app_data = aphp[(aphp.appareil == appareil) & (aphp.organe == "TOTAL")]
    ent_app  = app_data[app_data.entite == entity]
    aphp_app = app_data[app_data.entite == "AP-HP"]

    years = sorted(ent_app.annee.unique())
    last_year = years[-1]
    prev_year = years[-2]

    if ent_app.empty:
        return None

    lv = ent_app[ent_app.annee == last_year].iloc[0]
    pv = ent_app[ent_app.annee == prev_year].iloc[0]

    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card(f"Patients {entity}", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += kpi_card("Séjours radiothérapie", lv.nb_sejours_radiotherapie, pv.nb_sejours_radiotherapie)
    if hasattr(lv, 'delai_global_median') and pd.notna(lv.delai_global_median):
        kpis_html += kpi_card("Délai médian (j)", int(lv.delai_global_median), int(pv.delai_global_median), invert=True)
    kpis_html += "</div>"

    # Charts patients
    compare_ents = [entity] if entity != "AP-HP" else []
    compare_ents += ["AP-HP"] if entity != "AP-HP" else []
    all_ents = pd.concat([ent_app] + ([aphp_app] if entity != "AP-HP" else []))
    fig_pts = line_evolution(all_ents, "annee", "nb_patients", "entite",
                             f"Patients — {appareil}", entities=[entity] + (["AP-HP"] if entity != "AP-HP" else []))

    ghu_app = app_data[app_data.entite.isin(GHU_LIST)]
    ghu_last = ghu_app[ghu_app.annee == last_year]
    fig_donut = donut_market_share(ghu_last, "entite", "nb_patients",
                                   f"Répartition GHU — {appareil} ({last_year})")

    melted = ent_app.melt(id_vars=["annee"], value_vars=list(TREATMENT_COLS.keys()),
                           var_name="type_sejour", value_name="nb_sejours")
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 f"Séjours par mode de PEC — {appareil}",
                                 entities=list(TREATMENT_COLS.values()))

    # Organes
    fig_heat_org = heatmap_organes(aphp, entity, appareil,
                                    title=f"Évolution par organe — {appareil} — {entity}")
    fig_tree = treemap_organes(aphp, entity, appareil, last_year)

    # Survie
    fig_surv = survival_by_stage(surv, entity, appareil, year=last_year)
    fig_surv_evo = survival_evolution(surv, entity, appareil, stade="II")

    # Délais
    fig_delay = delay_evolution(aphp, entity, appareil)
    all_delay_ents = pd.concat([aphp_app, ghu_app])
    fig_delay_cmp = delay_comparison_bar(all_delay_ents, appareil, last_year)

    # Contexte régional
    reg_app = reg[(reg.appareil == appareil) & (reg.organe == "TOTAL")]
    fig_reg = regional_comparison(reg_app, "nb_patients",
                                  f"Contexte régional — {appareil}")

    # Navigation links — liens vers versions GHU
    ghu_links = ""
    for ghu in GHU_LIST:
        ghu_slug = slugify(ghu)
        app_slug = slugify(appareil)
        ghu_links += f'<a href="rapport_appareil_{app_slug}_{ghu_slug}.html" style="margin:0 6px;color:#003189;font-size:.85rem">{ghu}</a>'

    nav = "\n".join([
        '<a href="rapport_global_aphp.html">← AP-HP Global</a>',
        f'<a href="#kpis">Indicateurs {last_year}</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#organes">Par organe</a>',
        '<a href="#survie">Survie</a>',
        '<a href="#delais">Délais</a>',
        '<a href="#regional">Contexte régional</a>',
    ])

    content = ""
    content += section(f"Indicateurs clés — {appareil} — {last_year}", kpis_html, "kpis")
    content += section("Évolution du nombre de patients", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts))}
          {chart_card(fig_to_html(fig_donut))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_sejours))}
          {chart_card(fig_to_html(fig_reg))}
        </div>
    """, "evolution")
    content += section("Analyse par organe", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_heat_org))}
          {chart_card(fig_to_html(fig_tree))}
        </div>
    """, "organes")
    content += section("Survie par stade", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_surv))}
          {chart_card(fig_to_html(fig_surv_evo))}
        </div>
    """, "survie")
    content += section("Délais de prise en charge", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_delay))}
          {chart_card(fig_to_html(fig_delay_cmp))}
        </div>
    """, "delais")

    if entity == "AP-HP":
        content += f'<div style="margin-top:16px;padding:16px;background:#F8F9FA;border-radius:8px"><strong>Voir aussi par GHU :</strong> {ghu_links}</div>'

    html = HTML_TEMPLATE.format(
        title=f"Rapport — {appareil}" + (f" — {entity}" if entity != "AP-HP" else ""),
        subtitle=f"Activité cancérologie AP-HP · 2019–2023",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    app_slug = slugify(appareil)
    if entity == "AP-HP":
        out = output_dir / f"rapport_appareil_{app_slug}.html"
    else:
        ghu_slug = slugify(entity)
        out = output_dir / f"rapport_appareil_{app_slug}_{ghu_slug}.html"
    out.write_text(html, encoding="utf-8")
    return out


# ── Rapport par organe ────────────────────────────────────────────────────────

def build_rapport_organe(organe: str, appareil: str, data_dir: Path, output_dir: Path,
                          entity: str = "AP-HP",
                          aphp: pd.DataFrame = None,
                          reg: pd.DataFrame = None,
                          surv: pd.DataFrame = None) -> Path:
    if aphp is None: aphp = load_aphp(data_dir)
    if reg  is None: reg  = load_regional(data_dir)
    if surv is None: surv = load_survival(data_dir)

    org_data = aphp[(aphp.appareil == appareil) & (aphp.organe == organe)]
    ent_org  = org_data[org_data.entite == entity]
    aphp_org = org_data[org_data.entite == "AP-HP"]

    if ent_org.empty:
        return None

    years = sorted(ent_org.annee.unique())
    last_year = years[-1]
    prev_year = years[-2]
    lv = ent_org[ent_org.annee == last_year].iloc[0]
    pv = ent_org[ent_org.annee == prev_year].iloc[0]

    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card(f"Patients {entity}", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += kpi_card("Séjours radiothérapie", lv.nb_sejours_radiotherapie, pv.nb_sejours_radiotherapie)
    if hasattr(lv, 'delai_global_median') and pd.notna(lv.delai_global_median):
        kpis_html += kpi_card("Délai médian (j)", int(lv.delai_global_median), int(pv.delai_global_median), invert=True)
    kpis_html += "</div>"

    # Patients GHU comparison
    ghu_org = org_data[org_data.entite.isin(GHU_LIST)]
    all_ents = pd.concat([aphp_org, ghu_org])
    fig_pts = line_evolution(all_ents, "annee", "nb_patients", "entite",
                             f"Patients — {organe}", entities=[entity] + (GHU_LIST if entity == "AP-HP" else ["AP-HP"]))

    ghu_last = ghu_org[ghu_org.annee == last_year]
    fig_donut = donut_market_share(ghu_last, "entite", "nb_patients",
                                   f"Répartition GHU — {organe} ({last_year})")

    melted = ent_org.melt(id_vars=["annee"], value_vars=list(TREATMENT_COLS.keys()),
                           var_name="type_sejour", value_name="nb_sejours")
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 f"Séjours par mode de PEC — {organe}",
                                 entities=list(TREATMENT_COLS.values()))

    # Survie
    surv_org = surv[(surv.organe == organe) & (surv.appareil == appareil)] if surv is not None else pd.DataFrame()
    if not surv_org.empty:
        fig_surv = survival_by_stage(surv, entity, appareil, organe=organe, year=last_year)
        fig_surv_evo = survival_evolution(surv, entity, appareil, organe=organe, stade="II")
    else:
        fig_surv = survival_by_stage(surv, entity, appareil, year=last_year)
        fig_surv_evo = survival_evolution(surv, entity, appareil, stade="II")

    # Délais
    fig_delay = delay_evolution(aphp, entity, appareil, organe=organe)

    # Contexte régional
    reg_org = reg[(reg.appareil == appareil) & (reg.organe == organe)]
    if reg_org.empty:
        reg_org = reg[(reg.appareil == appareil) & (reg.organe == "TOTAL")]
    fig_reg = regional_comparison(reg_org, "nb_patients",
                                  f"Contexte régional — {organe}")

    app_slug = slugify(appareil)
    org_slug = slugify(organe)

    # GHU links
    ghu_links = ""
    for ghu in GHU_LIST:
        ghu_slug = slugify(ghu)
        ghu_links += f'<a href="rapport_organe_{org_slug}_{ghu_slug}.html" style="margin:0 6px;color:#003189;font-size:.85rem">{ghu}</a>'

    nav = "\n".join([
        f'<a href="rapport_appareil_{app_slug}.html">← {appareil}</a>',
        f'<a href="#kpis">Indicateurs {last_year}</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#survie">Survie</a>',
        '<a href="#delais">Délais</a>',
        '<a href="#regional">Contexte régional</a>',
    ])

    content = ""
    content += section(f"Indicateurs clés — {organe} — {last_year}", kpis_html, "kpis")
    content += section("Évolution", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts))}
          {chart_card(fig_to_html(fig_donut))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_sejours))}
          {chart_card(fig_to_html(fig_reg))}
        </div>
    """, "evolution")
    content += section("Survie par stade", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_surv))}
          {chart_card(fig_to_html(fig_surv_evo))}
        </div>
    """, "survie")
    content += section("Délais de prise en charge",
                       chart_card(fig_to_html(fig_delay)), "delais")

    if entity == "AP-HP":
        content += f'<div style="margin-top:16px;padding:16px;background:#F8F9FA;border-radius:8px"><strong>Voir aussi par GHU :</strong> {ghu_links}</div>'

    html = HTML_TEMPLATE.format(
        title=f"Rapport — {organe}" + (f" — {entity}" if entity != "AP-HP" else ""),
        subtitle=f"{appareil} · Activité cancérologie AP-HP · 2019–2023",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    if entity == "AP-HP":
        out = output_dir / f"rapport_organe_{org_slug}.html"
    else:
        ghu_slug = slugify(entity)
        out = output_dir / f"rapport_organe_{org_slug}_{ghu_slug}.html"
    out.write_text(html, encoding="utf-8")
    return out


# ── Page d'index ───────────────────────────────────────────────────────────────

def build_index(data_dir: Path, output_dir: Path) -> Path:
    aphp = load_aphp(data_dir)
    last_year = aphp.annee.max()
    lv = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL") & (aphp.annee == last_year)].iloc[0]
    pv = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL") & (aphp.annee == last_year - 1)].iloc[0]

    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card(f"Patients AP-HP {last_year}", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += "</div>"

    # Liens GHU
    ghu_cards = ""
    for ghu in GHU_LIST:
        slug = ghu.lower().replace(" ", "_")
        ghu_cards += f"""
        <a href="rapport_{slug}.html" style="
            display:block; background:white; border:1px solid #DEE2E6;
            border-radius:10px; padding:20px; text-decoration:none; color:#1A1A2E;
            box-shadow: 0 1px 3px rgba(0,0,0,.06);
            transition: box-shadow 0.2s, transform 0.2s;
        " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,.12)';this.style.transform='translateY(-2px)'"
           onmouseout="this.style.boxShadow='0 1px 3px rgba(0,0,0,.06)';this.style.transform='none'">
            <div style="font-weight:700;font-size:1rem;margin-bottom:4px">{ghu}</div>
            <div style="font-size:.8rem;color:#6C757D">Rapport individuel →</div>
        </a>"""

    appareils = sorted(aphp[(aphp.appareil != "TOTAL")].appareil.unique())
    app_links = ""
    for app in appareils:
        app_slug = slugify(app)
        app_links += f'<a href="rapport_appareil_{app_slug}.html" style="display:inline-block;margin:4px 8px;color:#003189;font-size:.9rem">{app} →</a><br>'

    # Organe links grouped by appareil
    organe_links = ""
    for app in appareils:
        app_slug = slugify(app)
        orgs = sorted(aphp[(aphp.entite == "AP-HP") & (aphp.appareil == app) & (aphp.organe != "TOTAL")].organe.unique())
        if orgs:
            organe_links += f'<div style="margin-bottom:12px"><strong style="color:#003189">{app}</strong><br>'
            for org in orgs:
                org_slug = slugify(org)
                organe_links += f'<a href="rapport_organe_{org_slug}.html" style="display:inline-block;margin:2px 6px;color:#457B9D;font-size:.85rem">{org} →</a>'
            organe_links += '</div>'

    content = section("Indicateurs AP-HP " + str(last_year), kpis_html, "kpis")
    content += section("Rapports par Groupe Hospitalier Universitaire", f"""
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px">
          {ghu_cards}
        </div>
    """, "ghu")
    content += section("Rapports par appareil pathologique", app_links, "appareils")
    content += section("Rapports par organe", organe_links, "organes")
    content += section("Rapport global AP-HP", f"""
        <a href="rapport_global_aphp.html" style="
            display:inline-block; background:#003189; color:white;
            padding:12px 28px; border-radius:8px; text-decoration:none;
            font-weight:600; font-size:1rem;
        ">Voir le rapport complet AP-HP →</a>
    """)

    html = HTML_TEMPLATE.format(
        title="Rapport d'activité cancérologie — AP-HP",
        subtitle="Tableau de bord · Indicateurs OECI · 2019–2023",
        nav_links='<a href="rapport_global_aphp.html">Rapport global AP-HP</a>',
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    out = output_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out
