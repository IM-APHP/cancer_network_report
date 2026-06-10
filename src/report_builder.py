"""
report_builder.py
Construit les rapports HTML à partir des données.
Chaque fonction retourne une chaîne HTML complète (page autonome).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Mode données ───────────────────────────────────────────────────────────────
FAKE_DATA: bool = True  # False = données réelles, supprime les avertissements


def set_fake_data(value: bool) -> None:
    global FAKE_DATA
    FAKE_DATA = value


from chart_utils import (
    line_evolution, bar_comparison, stacked_treatments,
    donut_market_share, heatmap_appareils, waterfall_trends,
    kpi_indicators, regional_comparison, fig_to_html,
    heatmap_organes, treemap_organes,
    survival_by_stage, survival_evolution, survival_hospital_comparison,
    delay_evolution, delay_comparison_bar,
    bar_appareils_years,
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
  {fake_badge}
</header>

<nav class="report-nav">
{nav_links}
</nav>

{fake_banner}

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


def _render_page(year_range: str, **kwargs) -> str:
    """Wrapper autour de HTML_TEMPLATE.format() qui injecte les variables fake_data."""
    if FAKE_DATA:
        badge = f'<div class="badge">Données fictives — {year_range}</div>'
        banner = (
            '<div class="fake-data-banner">'
            '⚠ <strong>DONNÉES FICTIVES</strong> — Ce rapport est généré à partir de données'
            ' entièrement simulées à titre illustratif.'
            ' Les chiffres présentés ne reflètent pas la réalité clinique et ne doivent pas'
            ' être utilisés à des fins médicales, administratives ou décisionnelles.'
            '</div>'
        )
    else:
        badge = ""
        banner = ""
    return HTML_TEMPLATE.format(year_range=year_range, fake_badge=badge, fake_banner=banner, **kwargs)


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


def section(title: str, content: str, anchor: str = "", action: str = "") -> str:
    anch = f' id="{anchor}"' if anchor else ""
    if action:
        title_block = (
            f'<div style="display:flex;align-items:center;justify-content:'
            f'space-between;margin-bottom:20px">'
            f'<h2 class="section-title" style="margin-bottom:0">{title}</h2>'
            f'{action}</div>'
        )
    else:
        title_block = f'<h2 class="section-title">{title}</h2>'
    return f"""
<div class="section"{anch}>
  {title_block}
  {content}
</div>"""


def chart_card(html: str, cls: str = "") -> str:
    return f'<div class="chart-card {cls}">{html}</div>'


def chart_grid(charts: list, cols: int = 2) -> str:
    inner = "\n".join(chart_card(c) for c in charts)
    return f'<div class="chart-grid-{cols}">{inner}</div>'


# ── Helpers réutilisables ──────────────────────────────────────────────────────

def ghu_nav_cards_html() -> str:
    """Grille de cartes de navigation vers les 6 GHU."""
    cards = ""
    for ghu in GHU_LIST:
        slug = ghu.lower().replace(" ", "_")
        cards += (
            f'<a href="rapport_{slug}.html" style="display:block;background:white;'
            f'border:1px solid #DEE2E6;border-radius:10px;padding:20px;'
            f'text-decoration:none;color:#1A1A2E;box-shadow:0 1px 3px rgba(0,0,0,.06);'
            f'transition:box-shadow .2s,transform .2s" '
            f'onmouseover="this.style.boxShadow=\'0 4px 12px rgba(0,0,0,.12)\';this.style.transform=\'translateY(-2px)\'" '
            f'onmouseout="this.style.boxShadow=\'0 1px 3px rgba(0,0,0,.06)\';this.style.transform=\'none\'">'
            f'<div style="font-weight:700;font-size:1rem;margin-bottom:4px">{ghu}</div>'
            f'<div style="font-size:.8rem;color:#6C757D">Rapport individuel →</div></a>'
        )
    return (
        '<div style="display:grid;grid-template-columns:'
        'repeat(auto-fit,minmax(180px,1fr));gap:16px">'
        + cards + "</div>"
    )


def organe_nav_links_html(aphp: pd.DataFrame, anchor_prefix: str = "rapport_organe_") -> str:
    """Liens vers rapports organe, regroupés par appareil."""
    appareils = sorted(aphp[aphp.appareil != "TOTAL"].appareil.unique())
    html = ""
    for app in appareils:
        app_slug = slugify(app)
        orgs = sorted(
            aphp[(aphp.entite == "AP-HP") & (aphp.appareil == app) & (aphp.organe != "TOTAL")]
            .organe.unique()
        )
        if not orgs:
            continue
        html += (
            f'<div style="margin-bottom:14px">'
            f'<a href="rapport_appareil_{app_slug}.html" style="font-weight:700;'
            f'color:#003189;font-size:.9rem;text-decoration:none">{app} →</a><br>'
        )
        for org in orgs:
            org_slug = slugify(org)
            html += (
                f'<a href="{anchor_prefix}{org_slug}.html" style="display:inline-block;'
                f'margin:2px 6px;color:#457B9D;font-size:.82rem">{org} →</a>'
            )
        html += "</div>"
    return html


def survival_delay_table(
    surv_df: pd.DataFrame,
    aphp_df: pd.DataFrame,
    entity: str,
    years: list = None,
) -> str:
    """Table HTML : lignes = appareils, colonnes = années, valeurs = survie5ans + délai."""
    if years is None:
        years = sorted(aphp_df["annee"].unique())

    appareils = sorted(aphp_df[aphp_df.appareil != "TOTAL"].appareil.unique())
    n = len(years)

    head = (
        "<tr>"
        f'<th rowspan="2" style="text-align:left;min-width:190px;padding:8px">Appareil</th>'
        f'<th colspan="{n}" style="background:#E8F4F8;padding:6px">Survie à 5 ans (%)</th>'
        f'<th colspan="{n}" style="background:#FFF3E0;padding:6px">Délai médian (j)</th>'
        "</tr><tr>"
        + "".join(f'<th style="background:#E8F4F8;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "".join(f'<th style="background:#FFF3E0;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "</tr>"
    )

    body = ""
    for app in appareils:
        surv_cells = ""
        delay_cells = ""
        for yr in years:
            # Survie à 5 ans pondérée par les stades — filtrer UNE population
            # (sinon le poids nb_patients_stade est compté deux fois : tous + nouveaux).
            s = surv_df[
                (surv_df.entite == entity) & (surv_df.appareil == app)
                & (surv_df.organe == "TOTAL") & (surv_df.annee == yr)
                & (surv_df.population == "tous")
            ]
            if not s.empty:
                w = (s.survie_5ans * s.nb_patients_stade).sum() / s.nb_patients_stade.sum()
                bg = "#d4edda" if w >= 80 else ("#fff3cd" if w >= 50 else "#f8d7da")
                surv_cells += f'<td style="text-align:center;background:{bg};padding:5px 6px">{w:.0f}%</td>'
            else:
                surv_cells += '<td style="text-align:center">—</td>'

            # Délai
            d = aphp_df[
                (aphp_df.entite == entity) & (aphp_df.appareil == app)
                & (aphp_df.organe == "TOTAL") & (aphp_df.annee == yr)
            ]
            if not d.empty and pd.notna(d.iloc[0].get("delai_global_median")):
                delay_cells += f'<td style="text-align:center;padding:5px 6px">{int(d.iloc[0]["delai_global_median"])}j</td>'
            else:
                delay_cells += '<td style="text-align:center">—</td>'

        short = app[:40]
        body += f'<tr><td style="font-size:.82rem;padding:6px 8px">{short}</td>{surv_cells}{delay_cells}</tr>'

    return (
        '<div style="overflow-x:auto">'
        '<table style="border-collapse:collapse;width:100%;font-size:.83rem;border:1px solid #DEE2E6">'
        f'<thead style="background:#F8F9FA">{head}</thead>'
        f'<tbody>{body}</tbody>'
        "</table></div>"
        '<p style="font-size:.78rem;color:#6C757D;margin-top:8px">'
        'Survie à 5 ans pondérée par la distribution des stades. '
        '<span style="background:#d4edda;padding:2px 5px;border-radius:3px">≥ 80 %</span> '
        '<span style="background:#fff3cd;padding:2px 5px;border-radius:3px">50–79 %</span> '
        '<span style="background:#f8d7da;padding:2px 5px;border-radius:3px">< 50 %</span>'
        "</p>"
    )


# Mesures de séjours du format interne (pas de « séjours totaux » → on les somme).
_SEJOUR_COLS = ["nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
                "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]


def appareil_counts_table(aphp_df: pd.DataFrame, entity: str, years: list = None) -> str:
    """Tableau chiffré par appareil (remplace la heatmap d'évolution) : lignes =
    appareils, colonnes = années, deux blocs « Nb patients » et « Nb séjours ».
    « Nb séjours » = somme chirurgie+chimio+radio+palliatifs (le format interne n'a
    pas de mesure « séjours totaux »). Style aligné sur « Survie et délais »."""
    if years is None:
        years = sorted(aphp_df["annee"].unique())
    appareils = sorted(aphp_df[aphp_df.appareil != "TOTAL"].appareil.unique())
    n = len(years)

    head = (
        "<tr>"
        f'<th rowspan="2" style="text-align:left;min-width:190px;padding:8px">Appareil</th>'
        f'<th colspan="{n}" style="background:#E8F4F8;padding:6px">Nb patients</th>'
        f'<th colspan="{n}" style="background:#FFF3E0;padding:6px">Nb séjours</th>'
        "</tr><tr>"
        + "".join(f'<th style="background:#E8F4F8;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "".join(f'<th style="background:#FFF3E0;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "</tr>"
    )

    body = ""
    for app in appareils:
        pat_cells = ""
        sej_cells = ""
        for yr in years:
            row = aphp_df[(aphp_df.entite == entity) & (aphp_df.appareil == app)
                          & (aphp_df.organe == "TOTAL") & (aphp_df.annee == yr)]
            if not row.empty:
                r = row.iloc[0]
                pat = int(r["nb_patients"])
                sej = int(sum(int(r[c]) for c in _SEJOUR_COLS if c in row.columns))
                pat_cells += f'<td style="text-align:center;padding:5px 6px">{fmt_nb(pat)}</td>'
                sej_cells += f'<td style="text-align:center;padding:5px 6px">{fmt_nb(sej)}</td>'
            else:
                pat_cells += '<td style="text-align:center">—</td>'
                sej_cells += '<td style="text-align:center">—</td>'
        short = app[:40]
        body += f'<tr><td style="font-size:.82rem;padding:6px 8px">{short}</td>{pat_cells}{sej_cells}</tr>'

    return (
        '<div style="overflow-x:auto">'
        '<table style="border-collapse:collapse;width:100%;font-size:.83rem;border:1px solid #DEE2E6">'
        f'<thead style="background:#F8F9FA">{head}</thead>'
        f'<tbody>{body}</tbody>'
        "</table></div>"
        '<p style="font-size:.78rem;color:#6C757D;margin-top:8px">'
        '« Nb séjours » = somme chirurgie + chimiothérapie + radiothérapie + soins palliatifs '
        '(pas de mesure « séjours totaux » dans la source).</p>'
    )


# ── Loaders ────────────────────────────────────────────────────────────────────

def _add_organe_total(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les lignes organe=TOTAL manquantes par (entite, annee, appareil)."""
    num_cols = [
        "nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
        "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
    ]
    delay_cols = [c for c in ["delai_global_median", "delai_chirurgie_median",
                               "delai_chimio_median", "delai_radio_median"] if c in df.columns]
    rows_to_add = []
    for (entite, annee, appareil), grp in df[df["appareil"] != "TOTAL"].groupby(
        ["entite", "annee", "appareil"]
    ):
        if "TOTAL" in grp["organe"].values:
            continue  # déjà présent
        row = {"entite": entite, "annee": annee, "appareil": appareil, "organe": "TOTAL"}
        for c in num_cols:
            if c in grp.columns:
                row[c] = grp[c].sum()
        for c in delay_cols:
            if c in grp.columns:
                row[c] = grp[c].mean()
        rows_to_add.append(row)
    if rows_to_add:
        df = pd.concat([df, pd.DataFrame(rows_to_add)], ignore_index=True)
    return df


def _add_appareil_total(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les lignes appareil=TOTAL manquantes en agrégeant organe=TOTAL."""
    if "TOTAL" in df["appareil"].values:
        return df
    num_cols = [
        "nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
        "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
    ]
    delay_cols = [c for c in ["delai_global_median", "delai_chirurgie_median",
                               "delai_chimio_median", "delai_radio_median"] if c in df.columns]
    org_total = df[df["organe"] == "TOTAL"]
    agg = org_total.groupby(["entite", "annee"])[num_cols].sum().reset_index()
    if delay_cols:
        agg_d = org_total.groupby(["entite", "annee"])[delay_cols].mean().reset_index()
        agg = agg.merge(agg_d, on=["entite", "annee"])
    agg["appareil"] = "TOTAL"
    agg["organe"] = "TOTAL"
    return pd.concat([df, agg], ignore_index=True)


# Mapping des noms d'appareils régionaux → noms AP-HP
_APPAREIL_MAP = {
    "OS-TISSUS MOUS":  "OS / TISSUS MOUS",
    "OEIL":            "ŒIL",
    "Total Appareil":  "TOTAL",
}

# Mapping des types d'établissements régionaux → libellés affichés
_ETAB_MAP = {
    "APHP":      "AP-HP",
    "Cliniques": "Clinique",
    "ESPIC":     "PSPH",
    "CLCC":      "CLCC",
    "CH":        "CH",
}


def load_aphp(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "aphp_data.csv")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")
    df = _add_organe_total(df)
    df = _add_appareil_total(df)
    return df


def load_regional(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "regional_data.csv")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")
    # Renommage colonne entite
    if "entite" not in df.columns and "type_etab" in df.columns:
        df = df.rename(columns={"type_etab": "entite"})
    # Normalisation des valeurs
    df["entite"]   = df["entite"].replace(_ETAB_MAP)
    df["appareil"] = df["appareil"].replace(_APPAREIL_MAP)
    if "organe" in df.columns:
        df["organe"] = df["organe"].replace({"Total Organe": "TOTAL"})
    return df


def load_survival(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "survival_data.csv")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")
    return df


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
    year_range = f"{years[0]}–{years[-1]}"

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

    covid_note = (
        '<div class="covid-note">⚠ L\'année 2020 est marquée par l\'impact de la pandémie COVID-19 sur l\'activité hospitalière.</div>'
        if 2020 in years else ""
    )

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
                                 entities=list(TREATMENT_COLS.values()), y_zero=True)

    # Waterfall
    fig_wf = waterfall_trends(aphp_total, "Variation annuelle du nombre de patients — AP-HP")

    # ── Parts de marché GHU ──
    ghu_last = ghu_total[ghu_total.annee == last_year]
    fig_donut = donut_market_share(ghu_last, "entite", "nb_patients",
                                   f"Répartition par GHU — {last_year}")
    fig_ghu_bar = bar_comparison(ghu_total, "annee", "nb_patients", "entite",
                                 "Patients par GHU — évolution", barmode="group",
                                 entities=GHU_LIST)

    # ── Tableau chiffré par appareil (remplace la heatmap) ──
    tbl_appareils = appareil_counts_table(aphp, "AP-HP")

    # ── Contexte régional ──
    reg_total = reg[(reg.appareil == "TOTAL")]
    fig_reg_pts = regional_comparison(reg_total, "nb_patients",
                                      "Patients — AP-HP vs contexte régional")
    fig_reg_chir = regional_comparison(reg_total, "nb_sejours_chirurgie",
                                       "Séjours chirurgie — AP-HP vs contexte régional")

    # ── Graphique patients par appareil ──
    fig_bar_app = bar_appareils_years(aphp)

    # ── Assembly HTML ──
    content = ""

    # GHU liens sobres
    ghu_links_global = " &nbsp;|&nbsp; ".join(
        f'<a href="rapport_{g.lower().replace(" ","_")}.html" style="color:#003189">{g}</a>'
        for g in GHU_LIST
    )
    content += section("Groupes Hospitaliers Universitaires",
                       f'<div style="line-height:2">{ghu_links_global}</div>', "ghu-nav")

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

    # Liens vers pages appareils
    app_links_global = ""
    for app in sorted(aphp[aphp.appareil != "TOTAL"].appareil.unique()):
        app_s = slugify(app)
        app_links_global += (
            f'<a href="rapport_appareil_{app_s}.html" style="display:inline-block;'
            f'margin:3px 8px;color:#457B9D;font-size:.85rem">{app} →</a>'
        )
    content += section("Analyse par appareil", f"""
        {chart_card(fig_to_html(fig_bar_app), "full")}
        {chart_card(tbl_appareils, "full")}
        <div style="margin-top:16px;padding:14px;background:#F8F9FA;border-radius:8px">
          <strong style="color:#003189">Rapports par appareil :</strong><br>
          {app_links_global}
        </div>
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

    # Survie et délais — tableau par appareil
    surv_table = survival_delay_table(surv, aphp, "AP-HP")
    lien_cmp = (
        '<a href="rapport_comparaison_hopitaux.html" style="display:inline-block;'
        'background:#003189;color:white;padding:8px 18px;border-radius:7px;'
        'text-decoration:none;font-weight:600;font-size:.85rem;white-space:nowrap">'
        'Comparaison inter-hôpitaux →</a>'
    )
    content += section("Survie et délais de prise en charge — par appareil",
                       surv_table, "survie", action=lien_cmp)

    nav = "\n".join([
        '<a href="index.html">← Dashboard</a>',
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#evolution">Évolution globale</a>',
        '<a href="#ghu">Groupes hospitaliers</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#regional">Contexte régional</a>',
        '<a href="#survie">Survie & Délais</a>',
        '<a href="rapport_comparaison_hopitaux.html">Inter-hôpitaux</a>',
    ])

    html = _render_page(year_range,
        title="Rapport d'activité cancérologie — AP-HP",
        subtitle=f"Vue d'ensemble · {year_range} · Indicateurs OECI",
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
    year_range = f"{years[0]}–{years[-1]}"

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

    # Part de marché de ce GHU (alignement sur les années communes)
    aphp_pts = aphp_total.set_index("annee")["nb_patients"]
    share_data = ghu_total.copy()
    share_data["part_marche"] = share_data.apply(
        lambda r: r["nb_patients"] / aphp_pts[r["annee"]] * 100
        if r["annee"] in aphp_pts.index else None, axis=1
    )
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

    # Tableau chiffré par appareil (remplace la heatmap)
    tbl_appareils = appareil_counts_table(aphp, ghu_name)

    # Survie (stade II comme représentatif)
    fig_surv = survival_by_stage(surv, ghu_name, "SEIN", year=last_year)
    fig_delay = delay_evolution(aphp, ghu_name, "SEIN")

    nav = "\n".join([
        '<a href="index.html">← Dashboard</a>',
        '<a href="rapport_global_aphp.html">AP-HP Global</a>',
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#survie">Survie & Délais</a>',
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
    app_links_ghu = ""
    for app in sorted(aphp[aphp.appareil != "TOTAL"].appareil.unique()):
        app_s = slugify(app)
        ghu_s = slugify(ghu_name)
        app_links_ghu += (
            f'<a href="rapport_appareil_{app_s}_{ghu_s}.html" style="display:inline-block;'
            f'margin:3px 8px;color:#457B9D;font-size:.85rem">{app} →</a>'
        )
    content += section("Analyse par appareil", f"""
        {chart_card(tbl_appareils, "full")}
        <div style="margin-top:16px;padding:14px;background:#F8F9FA;border-radius:8px">
          <strong style="color:#003189">Rapports par appareil :</strong><br>
          {app_links_ghu}
        </div>
    """, "appareils")
    surv_table = survival_delay_table(surv, aphp, ghu_name)
    content += section("Survie et délais de prise en charge — par appareil",
                       surv_table, "survie")

    html = _render_page(year_range,
        title=f"Rapport d'activité — {ghu_name}",
        subtitle=f"Activité cancérologie · {year_range} · Indicateurs OECI",
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

    if ent_app.empty:
        return None

    years = sorted(ent_app.annee.unique())
    if len(years) < 2:
        return None
    last_year = years[-1]
    prev_year = years[-2]
    year_range = f"{years[0]}–{years[-1]}"

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
    fig_surv_evo = survival_evolution(surv, entity, appareil, stade="I-III")

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
    # Liens organes pour cet appareil
    app_slug_local = slugify(appareil)
    orgs_of_app = sorted(
        aphp[(aphp.entite == "AP-HP") & (aphp.appareil == appareil) & (aphp.organe != "TOTAL")]
        .organe.unique()
    )
    org_links_html = ""
    for org in orgs_of_app:
        org_slug = slugify(org)
        suffix = f"_{slugify(entity)}" if entity != "AP-HP" else ""
        org_links_html += (
            f'<a href="rapport_organe_{org_slug}{suffix}.html" style="display:inline-block;'
            f'margin:3px 8px;color:#457B9D;font-size:.85rem">{org} →</a>'
        )
    organes_action = (
        '<a href="index.html#nav-organes" style="font-size:.82rem;color:#457B9D;'
        'text-decoration:none;white-space:nowrap">→ Tous les organes</a>'
    )
    content += section("Analyse par organe", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_heat_org))}
          {chart_card(fig_to_html(fig_tree))}
        </div>
        {f'<div style="margin-top:16px;padding:14px;background:#F8F9FA;border-radius:8px"><strong style="color:#003189">Organes — {appareil} :</strong><br>{org_links_html}</div>' if org_links_html else ''}
    """, "organes", action=organes_action)
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

    html = _render_page(year_range,
        title=f"Rapport — {appareil}" + (f" — {entity}" if entity != "AP-HP" else ""),
        subtitle=f"Activité cancérologie AP-HP · {year_range}",
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
    if len(years) < 2:
        return None
    last_year = years[-1]
    prev_year = years[-2]
    year_range = f"{years[0]}–{years[-1]}"
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
        fig_surv_evo = survival_evolution(surv, entity, appareil, organe=organe, stade="I-III")
    else:
        fig_surv = survival_by_stage(surv, entity, appareil, year=last_year)
        fig_surv_evo = survival_evolution(surv, entity, appareil, stade="I-III")

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

    html = _render_page(year_range,
        title=f"Rapport — {organe}" + (f" — {entity}" if entity != "AP-HP" else ""),
        subtitle=f"{appareil} · Activité cancérologie AP-HP · {year_range}",
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


# ── Comparaison inter-hôpitaux (survie) ────────────────────────────────────────

# Grands appareils déclinés en sections (rendus seulement si données présentes).
_APPAREILS_COMPARAISON = ["SEIN", "APPAREIL DIGESTIF", "APPAREIL RESPIRATOIRE ET AUTRES THORAX",
                          "VOIES URINAIRES", "ORGANES GENITAUX FEMININS"]


def build_rapport_comparaison_hopitaux(surv_df: pd.DataFrame, mapping: dict,
                                       output_dir: Path) -> Path:
    """Page unique « Comparaison inter-hôpitaux — Survie » : survie par hôpital,
    groupée/colorée par GHU, repères AP-HP/GHU. Comparaison globale (TOTAL/TOTAL)
    puis déclinaison par grand appareil (sections non vides uniquement)."""
    annees = sorted(surv_df["annee"].unique()) if not surv_df.empty else []
    last_year = int(annees[-1]) if annees else None
    year_range = f"{annees[0]}–{annees[-1]}" if annees else ""

    def _a_des_donnees(appareil):
        h = surv_df[(surv_df.appareil == appareil) & (surv_df.organe == "TOTAL")
                    & (surv_df.stade == "I-III") & (surv_df.population == "tous")
                    & (surv_df.annee == last_year) & (surv_df.entite.isin(mapping))]
        return not h.empty

    intro = (
        '<p style="color:#6C757D;font-size:.9rem;margin-bottom:18px">'
        'Survie à 5 ans (barres) et à 1 an (losanges) par hôpital, pour les patients de '
        'stade I-III. Les hôpitaux sont <b>colorés par GHU</b> et triés par survie décroissante. '
        'Le trait plein noir marque la référence <b>AP-HP</b> ; les pointillés colorés, la '
        'référence de chaque <b>GHU</b>.</p>'
    )

    content = ""
    # 1. Comparaison globale (toutes localisations)
    fig_glob = survival_hospital_comparison(surv_df, mapping, appareil="TOTAL",
                                            organe="TOTAL", stade="I-III",
                                            population="tous", annee=last_year)
    content += section("Comparaison globale — toutes localisations",
                       intro + chart_card(fig_to_html(fig_glob), "full"),
                       "global")

    # 2. Déclinaison par grand appareil (sections non vides)
    nav_app = []
    for app in _APPAREILS_COMPARAISON:
        if not _a_des_donnees(app):
            continue
        anchor = "cmp-" + slugify(app)
        fig = survival_hospital_comparison(surv_df, mapping, appareil=app,
                                           organe="TOTAL", stade="I-III",
                                           population="tous", annee=last_year)
        content += section(app.capitalize(), chart_card(fig_to_html(fig), "full"), anchor)
        nav_app.append(f'<a href="#{anchor}">{app.capitalize()}</a>')

    nav = "\n".join([
        '<a href="index.html">← Dashboard</a>',
        '<a href="rapport_global_aphp.html">Rapport global AP-HP</a>',
        '<a href="#global">Comparaison globale</a>',
    ] + nav_app)

    html = _render_page(year_range,
        title="Comparaison inter-hôpitaux — Survie",
        subtitle=f"Survie par hôpital, groupée par GHU · {year_range} · Indicateurs OECI",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )
    out = output_dir / "rapport_comparaison_hopitaux.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out


# ── Page d'index ───────────────────────────────────────────────────────────────

def build_index(data_dir: Path, output_dir: Path) -> Path:
    aphp = load_aphp(data_dir)
    reg  = load_regional(data_dir)
    years_all = sorted(aphp["annee"].unique())
    last_year = int(years_all[-1])
    prev_year = int(years_all[-2])
    year_range = f"{years_all[0]}–{years_all[-1]}"
    lv = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL") & (aphp.annee == last_year)].iloc[0]
    pv = aphp[(aphp.entite == "AP-HP") & (aphp.appareil == "TOTAL") & (aphp.annee == prev_year)].iloc[0]

    # ── KPI ──
    kpis_html = '<div class="kpi-grid">'
    kpis_html += kpi_card(f"Patients AP-HP {last_year}", lv.nb_patients, pv.nb_patients)
    kpis_html += kpi_card("Nouveaux patients", lv.nb_nouveaux_patients, pv.nb_nouveaux_patients)
    kpis_html += kpi_card("Séjours chirurgie", lv.nb_sejours_chirurgie, pv.nb_sejours_chirurgie)
    kpis_html += kpi_card("Séjours chimiothérapie", lv.nb_sejours_chimiotherapie, pv.nb_sejours_chimiotherapie)
    kpis_html += "</div>"

    btn_global = (
        '<a href="rapport_global_aphp.html" style="display:inline-block;background:#003189;'
        'color:white;padding:9px 22px;border-radius:7px;text-decoration:none;'
        'font-weight:600;font-size:.88rem;white-space:nowrap">Rapport complet AP-HP →</a>'
    )

    # ── Liens de navigation ──
    organe_links = organe_nav_links_html(aphp)

    # ── Assemblage ──
    content = ""

    # 1. KPI + bouton inline
    content += section(
        f"Indicateurs AP-HP {last_year}",
        kpis_html,
        "kpis",
        action=btn_global,
    )

    # 2. GHU cards
    content += section(
        "Groupes Hospitaliers Universitaires",
        ghu_nav_cards_html(),
        "ghu",
    )

    # 3. Comparaison inter-hôpitaux (survie)
    cmp_link = (
        '<a href="rapport_comparaison_hopitaux.html" style="display:inline-block;'
        'background:#003189;color:white;padding:10px 22px;border-radius:7px;'
        'text-decoration:none;font-weight:600;font-size:.88rem">'
        'Comparer les hôpitaux par survie →</a>'
        '<p style="color:#6C757D;font-size:.85rem;margin-top:10px">'
        'Survie à 5 ans par hôpital, groupée et colorée par GHU, avec repères AP-HP / GHU.</p>'
    )
    content += section("Comparaison inter-hôpitaux — Survie", cmp_link, "comparaison")

    # 4. Navigation liens simples
    content += section("Rapports par appareil / organe", organe_links, "nav-organes")

    nav = "\n".join([
        '<a href="#kpis">Indicateurs</a>',
        '<a href="#ghu">Par GHU</a>',
        '<a href="#comparaison">Inter-hôpitaux</a>',
        '<a href="#nav-organes">Appareils / Organes</a>',
    ])

    html = _render_page(year_range,
        title="Dashboard — Cancérologie AP-HP",
        subtitle=f"Tableau de bord · Indicateurs OECI · {year_range}",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    out = output_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out
