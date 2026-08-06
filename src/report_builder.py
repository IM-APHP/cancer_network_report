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
    delay_evolution, delay_comparison_bar, delay_hospital_comparison,
    bar_appareils_years,
    slugify,
    GHU_LIST, TREATMENT_COLS, REGIONAL_COLORS,
)
from referentiels import (APPAREIL_RESIDUEL, HOPITAUX_EXCLUS_COMPARAISON, _est_exclu,
                          organe_publiable)
from format_long import pivoter_simple, pivoter_survie

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
  {footer_note}
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
        footer_note = "Indicateurs OECI — Données simulées à titre illustratif"
    else:
        badge = ""
        banner = ""
        footer_note = "Indicateurs OECI"
    return HTML_TEMPLATE.format(year_range=year_range, fake_badge=badge, fake_banner=banner,
                               footer_note=footer_note, **kwargs)


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


def ghu_switch_banner(current: str, href_fn, label: str = "Naviguer") -> str:
    """Bandeau de pastilles de navigation : AP-HP + chaque GHU, la courante mise en
    évidence. ``href_fn(entite)`` renvoie l'URL de la version correspondante."""
    pills = ""
    for ent in ["AP-HP"] + GHU_LIST:
        actif = ent == current
        style = ("background:#003189;color:#fff" if actif
                 else "background:#fff;color:#003189;border:1px solid #C5D0E6")
        pills += (
            f'<a href="{href_fn(ent)}" style="display:inline-block;margin:3px 4px;'
            f'padding:5px 13px;border-radius:14px;text-decoration:none;font-size:.82rem;'
            f'font-weight:600;{style}">{ent}</a>'
        )
    return (
        '<div style="margin-bottom:22px;padding:10px 14px;background:#F8F9FA;'
        'border:1px solid #E9ECEF;border-radius:10px">'
        f'<span style="font-size:.78rem;color:#6C757D;margin-right:6px">{label} :</span>'
        f'{pills}</div>'
    )


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


def _appareils_affichables(df: pd.DataFrame) -> list:
    """Appareils à AFFICHER : hors sentinelle 'TOTAL' et hors appareil résiduel
    (« Non décidable »). Centralise l'exclusion pour tous les listings/agrégations."""
    return [a for a in sorted(df[df.appareil != "TOTAL"].appareil.unique())
            if a != APPAREIL_RESIDUEL]


def organe_nav_links_html(aphp: pd.DataFrame, anchor_prefix: str = "rapport_organe_",
                          ghu: str = None) -> str:
    """Liens vers rapports organe, regroupés par appareil. L'appareil résiduel est
    exclu de la liste générale et ajouté séparément en fin de section (son rapport
    reste accessible). Si ``ghu`` est fourni, pointe vers les versions GHU
    (rapport_*_<ghu>.html) ; sinon vers les versions AP-HP."""
    suffixe = f"_{slugify(ghu)}" if ghu else ""

    def _bloc(app: str, force: bool = False) -> str:
        app_slug = slugify(app)
        # Pages organe PUBLIABLES uniquement (« Non décidable », « Autre (…) », NaN
        # exclus — pas de page dédiée, cf. referentiels.organe_publiable).
        orgs = sorted(
            o for o in aphp[(aphp.entite == "AP-HP") & (aphp.appareil == app)
                            & (aphp.organe != "TOTAL")].organe.unique()
            if organe_publiable(o)
        )
        if not orgs and not force:
            return ""
        out = (
            f'<div style="margin-bottom:14px">'
            f'<a href="rapport_appareil_{app_slug}{suffixe}.html" style="font-weight:700;'
            f'color:#003189;font-size:.9rem;text-decoration:none">{app} →</a><br>'
        )
        for org in orgs:
            org_slug = slugify(org)
            out += (
                f'<a href="{anchor_prefix}{org_slug}{suffixe}.html" style="display:inline-block;'
                f'margin:2px 6px;color:#457B9D;font-size:.82rem">{org} →</a>'
            )
        return out + "</div>"

    html = "".join(_bloc(app) for app in _appareils_affichables(aphp))
    # Appareil résiduel : lien dédié en fin de section, séparé.
    if APPAREIL_RESIDUEL in set(aphp["appareil"]):
        html += (
            '<div style="margin-top:12px;padding-top:12px;border-top:1px dashed #DEE2E6">'
            '<span style="font-size:.78rem;color:#6C757D">Catégorie résiduelle :</span><br>'
            + _bloc(APPAREIL_RESIDUEL, force=True) + '</div>'
        )
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

    # En-tête sur 3 niveaux : la survie est désormais déclinée par stade (I-III | IV)
    # → 2 colonnes par année ; le délai reste une colonne par année (non lié au stade).
    head = (
        "<tr>"
        '<th rowspan="3" style="text-align:left;min-width:190px;padding:8px">Appareil</th>'
        f'<th colspan="{2 * n}" style="background:#E8F4F8;padding:6px">Survie à 5 ans (%)</th>'
        f'<th colspan="{n}" style="background:#FFF3E0;padding:6px">Délai médian (j)</th>'
        "</tr><tr>"
        + "".join(f'<th colspan="2" style="background:#E8F4F8;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "".join(f'<th rowspan="2" style="background:#FFF3E0;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "</tr><tr>"
        + "".join('<th style="background:#E8F4F8;padding:3px 6px;font-weight:500;font-size:.78rem">I-III</th>'
                  '<th style="background:#E8F4F8;padding:3px 6px;font-weight:500;font-size:.78rem">IV</th>'
                  for _ in years)
        + "</tr>"
    )

    # Pré-index des valeurs (un filtre GLOBAL par table au lieu de ~180 filtres
    # booléens par page). Sémantique inchangée : drop_duplicates(keep="first")
    # reproduit exactement l'ancien « premier match » (s.iloc[0]).
    _s = surv_df[(surv_df.entite == entity) & (surv_df.organe == "TOTAL")
                 & (surv_df.population == "tous")]
    _s = _s.drop_duplicates(subset=["annee", "appareil", "stade"], keep="first")
    _survies = {(int(a), ap, st): v for a, ap, st, v in
                zip(_s["annee"], _s["appareil"], _s["stade"], _s["survie_5ans"])}
    _d = aphp_df[(aphp_df.entite == entity) & (aphp_df.organe == "TOTAL")]
    _d = _d.drop_duplicates(subset=["annee", "appareil"], keep="first")
    _delais = {(int(a), ap): v for a, ap, v in
               zip(_d["annee"], _d["appareil"],
                   _d.get("delai_global_median", pd.Series(index=_d.index, dtype=float)))}

    def _survie_cell(yr, app, stade):
        """Cellule survie 5 ans pour un stade donné (population « tous »). NaN/absent → « — »."""
        v = _survies.get((int(yr), app, stade))
        if v is None or pd.isna(v):
            return '<td style="text-align:center">—</td>'
        v = float(v)
        bg = "#d4edda" if v >= 80 else ("#fff3cd" if v >= 50 else "#f8d7da")
        return f'<td style="text-align:center;background:{bg};padding:5px 6px">{v:.0f}%</td>'

    body = ""
    for app in appareils:
        surv_cells = ""
        delay_cells = ""
        for yr in years:
            surv_cells += _survie_cell(yr, app, "I-III") + _survie_cell(yr, app, "IV")

            # Délai (inchangé : non décliné par stade)
            dv = _delais.get((int(yr), app))
            if dv is not None and pd.notna(dv):
                delay_cells += f'<td style="text-align:center;padding:5px 6px">{int(dv)}j</td>'
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
        'Survie à 5 ans par stade (I-III / IV). '
        '<span style="background:#d4edda;padding:2px 5px;border-radius:3px">≥ 80 %</span> '
        '<span style="background:#fff3cd;padding:2px 5px;border-radius:3px">50–79 %</span> '
        '<span style="background:#f8d7da;padding:2px 5px;border-radius:3px">< 50 %</span>'
        "</p>"
    )


# Mesures de séjours du format interne (pas de « séjours totaux » → on les somme).
_SEJOUR_COLS = ["nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
                "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]


def _ligne_pat_sej(row):
    """(nb_patients, nb_séjours) d'une ligne interne. nb_séjours = somme des 4
    mesures de séjours (pas de « séjours totaux » dans la source)."""
    r = row.iloc[0]
    return (int(r["nb_patients"]),
            int(sum(int(r[c]) for c in _SEJOUR_COLS if c in row.columns)))


def _counts_table_html(first_col: str, items: list, value_fn, years: list) -> str:
    """Rendu commun du tableau chiffré (blocs « Nb patients » / « Nb séjours » par
    année). ``value_fn(item, annee)`` renvoie ``(pat, sej)`` ou ``None`` si absent.
    Style aligné sur le tableau « Survie et délais »."""
    n = len(years)
    head = (
        "<tr>"
        f'<th rowspan="2" style="text-align:left;min-width:190px;padding:8px">{first_col}</th>'
        f'<th colspan="{n}" style="background:#E8F4F8;padding:6px">Nb patients</th>'
        f'<th colspan="{n}" style="background:#FFF3E0;padding:6px">Nb séjours</th>'
        "</tr><tr>"
        + "".join(f'<th style="background:#E8F4F8;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "".join(f'<th style="background:#FFF3E0;padding:4px 6px;font-weight:500">{y}</th>' for y in years)
        + "</tr>"
    )
    body = ""
    for it in items:
        pat_cells = ""
        sej_cells = ""
        for yr in years:
            v = value_fn(it, yr)
            if v is not None:
                pat, sej = v
                pat_cells += f'<td style="text-align:center;padding:5px 6px">{fmt_nb(pat)}</td>'
                sej_cells += f'<td style="text-align:center;padding:5px 6px">{fmt_nb(sej)}</td>'
            else:
                pat_cells += '<td style="text-align:center">—</td>'
                sej_cells += '<td style="text-align:center">—</td>'
        body += f'<tr><td style="font-size:.82rem;padding:6px 8px">{str(it)[:40]}</td>{pat_cells}{sej_cells}</tr>'
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


def appareil_counts_table(aphp_df: pd.DataFrame, entity: str, years: list = None) -> str:
    """Tableau chiffré par appareil (remplace la heatmap d'évolution) : lignes =
    appareils (hors résiduel/TOTAL), colonnes = années, blocs Nb patients / séjours."""
    if years is None:
        years = sorted(aphp_df["annee"].unique())

    def vf(app, yr):
        row = aphp_df[(aphp_df.entite == entity) & (aphp_df.appareil == app)
                      & (aphp_df.organe == "TOTAL") & (aphp_df.annee == yr)]
        return None if row.empty else _ligne_pat_sej(row)

    return _counts_table_html("Appareil", _appareils_affichables(aphp_df), vf, years)


def organe_counts_table(aphp_df: pd.DataFrame, entity: str, appareil: str,
                        years: list = None) -> str:
    """Tableau chiffré par organe (remplace heatmap_organes) pour un appareil :
    lignes = organes (sentinelle « TOTAL » filtrée), colonnes = années, blocs
    Nb patients / Nb séjours."""
    if years is None:
        years = sorted(aphp_df["annee"].unique())
    organes = sorted(
        aphp_df[(aphp_df.entite == entity) & (aphp_df.appareil == appareil)
                & (aphp_df.organe != "TOTAL")].organe.unique()
    )

    def vf(org, yr):
        row = aphp_df[(aphp_df.entite == entity) & (aphp_df.appareil == appareil)
                      & (aphp_df.organe == org) & (aphp_df.annee == yr)]
        return None if row.empty else _ligne_pat_sej(row)

    return _counts_table_html("Organe", organes, vf, years)


# ── Loaders ────────────────────────────────────────────────────────────────────

def reconstruire_grains(df: pd.DataFrame) -> pd.DataFrame:
    """Point d'entrée UNIQUE de reconstruction des grains TOTAL d'une vue large :
    organe=TOTAL par (entite, annee, appareil) PUIS appareil=TOTAL par (entite, annee).
    Comptes → somme, délais → moyenne NaN-safe. Garde « reconstruire seulement si
    absent » PAR GROUPE : les grains fournis par la source (dont l'AP-HP régional
    dédupliqué canceroAPHP, OECI « Hop Total »…) ne sont JAMAIS recalculés.
    Consommé par load_aphp / load_regional / load_delais_hopitaux — un load_* ne peut
    plus « oublier » un grain en n'appelant qu'un helper sur deux."""
    return _add_appareil_total(_add_organe_total(df))


def _add_organe_total(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les lignes organe=TOTAL manquantes par (entite, annee, appareil) —
    vectorisé (anti-jointure sur les groupes déjà pourvus + groupby agrégé, comptes →
    somme, délais → moyenne NaN-safe). Ordre des lignes ajoutées = tri groupby,
    identique à l'ancienne boucle par groupe."""
    num_cols = [c for c in ["nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
                            "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie",
                            "nb_sejours_palliatifs"] if c in df.columns]
    delay_cols = [c for c in ["delai_global_median", "delai_chirurgie_median",
                               "delai_traitement_medical_median", "delai_radio_median"] if c in df.columns]
    cles = ["entite", "annee", "appareil"]
    src = df[df["appareil"] != "TOTAL"]
    if src.empty or (not num_cols and not delay_cols):
        return df
    # Anti-jointure : groupes ayant DÉJÀ leur organe=TOTAL (fourni par la source).
    deja = src.loc[src["organe"] == "TOTAL", cles].drop_duplicates()
    if not deja.empty:
        src = src.merge(deja.assign(_deja=1), on=cles, how="left")
        src = src[src["_deja"].isna()].drop(columns="_deja")
        if src.empty:
            return df
    # Agrégation par groupe (ordre trié du groupby, comme l'ancienne boucle).
    if num_cols:
        agg = src.groupby(cles)[num_cols].sum().reset_index()
        if delay_cols:
            agg = agg.merge(src.groupby(cles)[delay_cols].mean().reset_index(), on=cles)
    else:
        agg = src.groupby(cles)[delay_cols].mean().reset_index()
    agg["organe"] = "TOTAL"
    return pd.concat([df, agg], ignore_index=True)


def _add_appareil_total(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les lignes appareil=TOTAL manquantes en agrégeant organe=TOTAL. Tolérant
    aux tableaux SANS colonnes de comptes (délais seuls, cf. load_delais_hopitaux) : on
    ne somme/moyenne que les colonnes présentes (comptes → somme, délais → moyenne).
    Garde par (entite, annee) — même sémantique que _add_organe_total : on ne reconstruit
    QUE les couples n'ayant pas déjà leur appareil=TOTAL (cas mixte : une entité fournie
    par la source, une autre à reconstruire)."""
    num_cols = [c for c in ["nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
                            "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie",
                            "nb_sejours_palliatifs"] if c in df.columns]
    delay_cols = [c for c in ["delai_global_median", "delai_chirurgie_median",
                               "delai_traitement_medical_median", "delai_radio_median"] if c in df.columns]
    # Source d'agrégation : lignes organe=TOTAL hors grand total déjà présent.
    org_total = df[(df["organe"] == "TOTAL") & (df["appareil"] != "TOTAL")]
    if org_total.empty or (not num_cols and not delay_cols):
        return df                                # rien à agréger → df inchangé
    # Garde : couples (entite, annee) ayant DÉJÀ leur appareil=TOTAL (fourni par la source).
    deja = df.loc[df["appareil"] == "TOTAL", ["entite", "annee"]].drop_duplicates()
    if not deja.empty:
        org_total = org_total.merge(deja.assign(_deja=1), on=["entite", "annee"], how="left")
        org_total = org_total[org_total["_deja"].isna()].drop(columns="_deja")
        if org_total.empty:
            return df                            # tout est déjà fourni → df inchangé
    agg = org_total[["entite", "annee"]].drop_duplicates()
    if num_cols:                                 # comptes → somme
        agg = agg.merge(org_total.groupby(["entite", "annee"])[num_cols].sum().reset_index(),
                        on=["entite", "annee"])
    if delay_cols:                               # délais → moyenne (NaN-safe)
        agg = agg.merge(org_total.groupby(["entite", "annee"])[delay_cols].mean().reset_index(),
                        on=["entite", "annee"])
    agg = agg.copy()
    agg["appareil"] = "TOTAL"
    agg["organe"] = "TOTAL"
    return pd.concat([df, agg], ignore_index=True)


# Mapping des noms d'appareils régionaux → noms AP-HP
_APPAREIL_MAP = {
    "OS-TISSUS MOUS":  "OS / TISSUS MOUS",
    "OEIL":            "ŒIL",
    "?IL":             "ŒIL",   # mojibake RÉEL : « Œ » exporté en « ? » (0x3F) dans les xlsx canceroBR/canceroAPHP
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


# ── Chargement depuis le format pivot LONG (donnees.csv) ───────────────────────
# Le stockage est long ; les consommateurs reçoivent des vues LARGES via les load_*,
# qui filtrent une tranche (source/niveau/variable) puis pivotent variable→colonnes
# (cf. contrat_donnees_pivot.md §7). Colonnes larges figées (ordre/présence garantis).

_COLS_APHP = ["annee", "entite", "appareil", "organe",
              "nb_patients", "nb_nouveaux_patients",
              "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
              "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
              "delai_global_median", "delai_chirurgie_median",
              "delai_traitement_medical_median", "delai_radio_median"]
_COLS_REGIONAL = ["annee", "entite", "appareil", "organe",
                  "nb_patients", "nb_nouveaux_patients",
                  "nb_sejours_chirurgie", "nb_sejours_chimiotherapie",
                  "nb_sejours_radiotherapie", "nb_sejours_palliatifs"]
_COLS_SURVIE = ["annee", "entite", "appareil", "organe", "stade", "population",
                "nb_patients_stade", "survie_1an", "survie_5ans"]
_COLS_DELAIS_HOP = ["annee", "entite", "appareil", "organe",
                    "delai_global_median", "delai_chirurgie_median",
                    "delai_traitement_medical_median", "delai_radio_median"]


# ── Mémoïsation des chargements ────────────────────────────────────────────────
# Un build complet relisait donnees.csv (~18 Mo) ~25 fois : build_rapport_ghu /
# build_rapport_global rechargent leurs vues à chaque appel. Le fichier ne changeant
# pas pendant un build, on mémoïse par (chemin résolu, mtime_ns, taille) — toute
# régénération de donnees.csv (notebooks 05/06, --data-only) change la clé et purge.
_CACHE_LONG: dict = {}     # {(chemin, mtime_ns, taille): DataFrame long partagé}
_CACHE_VUES: dict = {}     # {(nom_vue, chemin, mtime_ns, taille): DataFrame large}


def _cle_fichier(data_dir: Path) -> tuple:
    p = (Path(data_dir) / "donnees.csv").resolve()
    st = p.stat()
    return (str(p), st.st_mtime_ns, st.st_size)


def _charger_long(data_dir: Path) -> pd.DataFrame:
    """Lit le fichier pivot long unique ``donnees.csv``. ``dtype`` forcé sur ``stade``
    (majoritairement vide hors survie) pour éviter le DtypeWarning de pandas.
    MÉMOÏSÉ : le DataFrame retourné est PARTAGÉ, en lecture seule par convention —
    les pivots (``pivoter_simple``/``pivoter_survie``) copient avant modification."""
    cle = _cle_fichier(data_dir)
    df = _CACHE_LONG.get(cle)
    if df is None:
        _CACHE_LONG.clear()
        _CACHE_VUES.clear()          # nouveau fichier → purge des vues dérivées
        df = pd.read_csv(data_dir / "donnees.csv", dtype={"stade": "string"})
        df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")],
                     errors="ignore")
        _CACHE_LONG[cle] = df
    return df


def _vue_memoisee(nom: str, data_dir: Path, construire) -> pd.DataFrame:
    """Mémoïse une vue large ``load_*`` par état du fichier. Retourne une COPIE
    défensive : les consommateurs peuvent modifier leur exemplaire sans corrompre
    le cache (ils partagent déjà les frames préchargées dans run_reports)."""
    cle = (nom, *_cle_fichier(data_dir))
    df = _CACHE_VUES.get(cle)
    if df is None:
        df = construire()
        _CACHE_VUES[cle] = df
    return df.copy()


def _reindex_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Garantit la présence et l'ordre des colonnes larges attendues (une variable
    absente de l'extrait → colonne vide, jamais de KeyError côté consommateurs)."""
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols]


def load_aphp(data_dir: Path) -> pd.DataFrame:
    return _vue_memoisee("aphp", data_dir, lambda: _construire_aphp(data_dir))


def _construire_aphp(data_dir: Path) -> pd.DataFrame:
    long = _charger_long(data_dir)
    df = pivoter_simple(long, "DIM APHP", ["aphp", "ghu"])
    df = _reindex_cols(df, _COLS_APHP)
    df = reconstruire_grains(df)
    return df


def load_regional(data_dir: Path) -> pd.DataFrame:
    return _vue_memoisee("regional", data_dir, lambda: _construire_regional(data_dir))


def _construire_regional(data_dir: Path) -> pd.DataFrame:
    long = _charger_long(data_dir)
    df = pivoter_simple(long, "BN", ["aphp", "type_etab"])
    df = _reindex_cols(df, _COLS_REGIONAL)
    # Normalisation des valeurs (idem ancienne lecture CSV) : libellés établissement
    # et noms d'appareils/organes régionaux → conventions AP-HP.
    df["entite"]   = df["entite"].replace(_ETAB_MAP)
    df["appareil"] = df["appareil"].replace(_APPAREIL_MAP)
    df["organe"]   = df["organe"].replace({"Total Organe": "TOTAL"})
    # Reconstruction des grains organe=TOTAL / appareil=TOTAL manquants (idem load_aphp) :
    # le régional est stocké au grain ORGANE, or l'accueil filtre appareil=="TOTAL" et les
    # rapports par appareil filtrent organe=="TOTAL". Gardes NaN-safe : les helpers sautent
    # tout (entite, annee, appareil) ayant déjà un organe=TOTAL, et n'ajoutent pas de
    # appareil=TOTAL s'il existe déjà → en RÉEL (canceroBR/canceroAPHP fournissent ces grains)
    # rien n'est recalculé (valeurs source et dédup AP-HP de canceroAPHP préservées) ; en
    # FICTIF (grain organe seul) ils sont reconstruits par somme des comptes.
    df = reconstruire_grains(df)
    return df


# Mesures régionales affichées : sert à détecter un extrait canceroBR encore VIDE
# (gabarit non rempli → toutes mesures nulles). Cf. regional_disponible().
_MESURES_REGIONAL = [
    "nb_patients", "nb_nouveaux_patients", "nb_sejours_chirurgie",
    "nb_sejours_chimiotherapie", "nb_sejours_radiotherapie", "nb_sejours_palliatifs",
]


def regional_disponible(reg: pd.DataFrame) -> bool:
    """Vrai si l'extrait régional porte des MESURES (≠ gabarit vide). Tant que les
    vrais fichiers canceroBR ne sont pas livrés, ``data/`` contient les gabarits
    (dimensions remplies, mesures vides → toutes nulles) : on masque alors les
    sections « Contexte régional » plutôt que d'afficher des graphiques/tableaux
    vides. Critère : au moins une mesure régionale strictement positive."""
    if reg is None or reg.empty:
        return False
    cols = [c for c in _MESURES_REGIONAL if c in reg.columns]
    if not cols:
        return False
    total = pd.to_numeric(
        reg[cols].stack(), errors="coerce").fillna(0).sum()
    return float(total) > 0


def load_survival(data_dir: Path) -> pd.DataFrame:
    return _vue_memoisee("survie", data_dir, lambda: _construire_survival(data_dir))


def _construire_survival(data_dir: Path) -> pd.DataFrame:
    long = _charger_long(data_dir)
    df = pivoter_survie(long, source="EDS APHP")
    return _reindex_cols(df, _COLS_SURVIE)


def load_delais_hopitaux(data_dir: Path) -> pd.DataFrame:
    return _vue_memoisee("delais_hop", data_dir,
                         lambda: _construire_delais_hopitaux(data_dir))


def _construire_delais_hopitaux(data_dir: Path) -> pd.DataFrame:
    """Délais médians niveau hôpital (+ AP-HP/GHU) pour la comparaison inter-hôpitaux.
    Le grain APPAREIL (organe=TOTAL) est ABSENT de la source (Total + Organe seulement)
    → reconstruit ici par ``_add_organe_total`` (moyenne des médianes par organe), comme
    pour ``load_aphp``. Le grain global appareil=TOTAL vient de la source « Hop Total » en
    RÉEL (garde active → non recalculé) ; en FICTIF il est reconstruit par
    ``_add_appareil_total`` (moyenne des délais par appareil) — sinon la comparaison
    inter-hôpitaux au grain global serait vide."""
    long = _charger_long(data_dir)
    # Niveaux aphp/ghu (repères AP-HP/GHU des graphiques) + hopital (les barres). Les
    # délais aphp/ghu viennent de la tranche DIM APHP commune (identiques à load_aphp).
    df = pivoter_simple(long, "DIM APHP", ["aphp", "ghu", "hopital"],
                        variables=_COLS_DELAIS_HOP[4:], reconstruire_nouveaux=False)
    df = _reindex_cols(df, _COLS_DELAIS_HOP)
    if df.empty:
        return df
    # Un délai 0 = ABSENT (case OECI non renseignée, 0-fill du merge patients/séjours
    # côté DIM APHP), pas une vraie médiane de 0 jour : on le neutralise (→ NaN) pour
    # qu'il ne pollue PAS la moyenne reconstruite par appareil. Les vraies lignes de
    # délais (source « Délais PEC ») ne contiennent jamais de 0.
    delais = _COLS_DELAIS_HOP[4:]
    df[delais] = df[delais].replace(0, float("nan"))
    df = reconstruire_grains(df)   # grains appareil + global (reconstruits en fictif, gardés en réel)
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

    # ── Contexte régional (seulement si l'extrait régional est rempli) ──
    reg_dispo = regional_disponible(reg)
    if reg_dispo:
        reg_total = reg[(reg.appareil == "TOTAL")]
        fig_reg_pts = regional_comparison(reg_total, "nb_patients",
                                          "Patients — AP-HP vs contexte régional",
                                          color_map=REGIONAL_COLORS)
        reg_total_last = reg[(reg.appareil == "TOTAL") & (reg.organe == "TOTAL")
                             & (reg.annee == last_year)]
        # entities = types d'établissement (sinon donut_market_share filtre sur GHU_LIST par défaut)
        types_etab = sorted(reg_total_last["entite"].unique())
        fig_reg_donut = donut_market_share(
            reg_total_last, "entite", "nb_patients",
            f"Répartition de l'activité par type d'établissement — {last_year}",
            entities=types_etab, color_map=REGIONAL_COLORS)

    # ── Graphique patients par appareil ──
    fig_bar_app = bar_appareils_years(aphp)

    # ── Assembly HTML ──
    # Bandeau inter-GHU uniforme (AP-HP courant mis en évidence)
    content = ghu_switch_banner(
        "AP-HP",
        lambda e: "index.html" if e == "AP-HP" else f"rapport_{slugify(e)}.html",
    )

    content += section("Indicateurs clés — " + str(last_year), kpis_html + covid_note, "kpis")

    # Contexte régional — juste sous les indicateurs clés (masqué si extrait vide)
    if reg_dispo:
        content += section("Contexte régional", f"""
            <p style="margin-bottom:16px;font-size:.9rem;color:var(--muted)">
              Comparaison avec les autres types d'établissements de la région Île-de-France
              (Cliniques, Centres Hospitaliers, CHU, PSPH).
            </p>
            <div class="chart-grid-2">
              {chart_card(fig_to_html(fig_reg_pts))}
              {chart_card(fig_to_html(fig_reg_donut))}
            </div>
        """, "regional")

    content += section("Évolution globale du nombre de patients", f"""
        {covid_note}
        <div class="chart-grid-2">
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

    # Liens vers pages appareils (hors appareil résiduel)
    app_links_global = ""
    for app in _appareils_affichables(aphp):
        app_s = slugify(app)
        app_links_global += (
            f'<a href="rapport_appareil_{app_s}.html" style="display:inline-block;'
            f'margin:3px 8px;color:#457B9D;font-size:.85rem">{app} →</a>'
        )
    content += section("Analyse par appareil", f"""
        {chart_card(fig_to_html(fig_bar_app), "full")}
        {chart_card(tbl_appareils, "full")}
    """, "appareils")

    # Survie et délais — tableau par appareil
    surv_table = survival_delay_table(surv, aphp, "AP-HP")
    _btn = ('background:#003189;color:white;padding:8px 18px;border-radius:7px;'
            'text-decoration:none;font-weight:600;font-size:.85rem;white-space:nowrap;'
            'display:inline-block;margin-left:8px')
    lien_cmp = (
        f'<a href="rapport_comparaison_hopitaux.html" style="{_btn}">'
        'Inter-hôpitaux — Survie →</a>'
        f'<a href="comparaison_hopitaux_delais.html" style="{_btn}">'
        'Inter-hôpitaux — Délais →</a>'
    )
    content += section("Survie et délais de prise en charge — par appareil",
                       surv_table, "survie", action=lien_cmp)

    # Navigation bas de page : rapports par appareil + par organe
    content += section("Rapports par appareil",
                       f'<div style="line-height:2.2">{app_links_global}</div>', "nav-appareils")
    content += section("Rapports par organe", organe_nav_links_html(aphp), "nav-organes")

    nav = "\n".join([l for l in [
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#regional">Contexte régional</a>' if reg_dispo else None,
        '<a href="#evolution">Évolution globale</a>',
        '<a href="#ghu">Groupes hospitaliers</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#survie">Survie & Délais</a>',
        '<a href="#nav-organes">Par organe</a>',
        '<a href="rapport_comparaison_hopitaux.html">Inter-hôpitaux survie</a>',
        '<a href="comparaison_hopitaux_delais.html">Inter-hôpitaux délais</a>',
    ] if l])

    html = _render_page(year_range,
        title="Cancérologie AP-HP — Tableau de bord",
        subtitle=f"Vue d'ensemble · {year_range} · Indicateurs OECI",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )

    out = output_dir / "index.html"   # page d'accueil (fusion de l'ancien index)
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

    # Graphiques — Part de marché de ce GHU (alignement sur les années communes)
    aphp_pts = aphp_total.set_index("annee")["nb_patients"]
    share_data = ghu_total.copy()
    share_data["part_marche"] = share_data.apply(
        lambda r: r["nb_patients"] / aphp_pts[r["annee"]] * 100
        if r["annee"] in aphp_pts.index else None, axis=1
    )
    fig_share = line_evolution(share_data, "annee", "part_marche", "entite",
                               f"Part de marché dans l'AP-HP — {ghu_name} (%)",
                               entities=[ghu_name], y_zero=True)

    # Séjours
    melted = ghu_total.melt(
        id_vars=["annee"], value_vars=list(TREATMENT_COLS.keys()),
        var_name="type_sejour", value_name="nb_sejours",
    )
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 f"Séjours par mode de prise en charge — {ghu_name}",
                                 entities=list(TREATMENT_COLS.values()))

    # Répartition entre tous les GHU de l'AP-HP (identique au rapport AP-HP)
    ghu_total_all = aphp[(aphp.entite.isin(GHU_LIST)) & (aphp.appareil == "TOTAL")]
    fig_repart_donut = donut_market_share(
        ghu_total_all[ghu_total_all.annee == last_year], "entite", "nb_patients",
        f"Répartition par GHU — {last_year}")
    fig_repart_lines = line_evolution(ghu_total_all, "annee", "nb_patients", "entite",
                                      "Patients par GHU — évolution", entities=GHU_LIST)

    # Tableau chiffré par appareil (remplace la heatmap)
    tbl_appareils = appareil_counts_table(aphp, ghu_name)

    # Survie (stade II comme représentatif)
    fig_surv = survival_by_stage(surv, ghu_name, "SEIN", year=last_year)
    fig_delay = delay_evolution(aphp, ghu_name, "SEIN")

    nav = "\n".join([
        '<a href="index.html">← Accueil AP-HP</a>',
        '<a href="#kpis">Indicateurs clés</a>',
        '<a href="#repartition">Répartition GHU</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#appareils">Par appareil</a>',
        '<a href="#survie">Survie & Délais</a>',
        '<a href="#nav-organes">Par organe</a>',
    ])

    # Bandeau inter-GHU (AP-HP + chaque GHU, GHU courant mis en évidence)
    content = ghu_switch_banner(
        ghu_name,
        lambda e: "index.html" if e == "AP-HP" else f"rapport_{slugify(e)}.html",
        label="Naviguer",
    )
    content += section(f"Indicateurs clés — {last_year}", kpis_html, "kpis")
    content += section("Répartition entre les groupes hospitaliers (GHU)", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_repart_donut))}
          {chart_card(fig_to_html(fig_repart_lines))}
        </div>
    """, "repartition")
    content += section("Évolution — Patients", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_share))}
          {chart_card(fig_to_html(fig_sejours))}
        </div>
    """, "evolution")
    app_links_ghu = ""
    for app in _appareils_affichables(aphp):
        app_s = slugify(app)
        ghu_s = slugify(ghu_name)
        app_links_ghu += (
            f'<a href="rapport_appareil_{app_s}_{ghu_s}.html" style="display:inline-block;'
            f'margin:3px 8px;color:#457B9D;font-size:.85rem">{app} →</a>'
        )
    organe_links_ghu = organe_nav_links_html(aphp, ghu=ghu_name)
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
    # Navigation par organe (GHU) — déplacée en bas de page
    content += section(f"Rapports par organe ({ghu_name})", organe_links_ghu, "nav-organes")

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


def _market_share_evolution(ent_df: pd.DataFrame, aphp_df: pd.DataFrame,
                            entity: str, libelle: str):
    """Courbe d'évolution de la part de marché d'un GHU dans l'AP-HP :
    nb_patients(GHU) / nb_patients(AP-HP) × 100, par année, sur le périmètre donné."""
    aphp_pts = aphp_df.set_index("annee")["nb_patients"]
    d = ent_df[["annee", "nb_patients"]].copy()
    d["part_marche"] = [
        (nb / aphp_pts[an] * 100) if (an in aphp_pts.index and aphp_pts[an]) else None
        for an, nb in zip(d["annee"], d["nb_patients"])
    ]
    d["entite"] = entity
    return line_evolution(d, "annee", "part_marche", "entite",
                          f"Part de marché de {entity} dans l'AP-HP — {libelle} (%)",
                          entities=[entity], y_zero=True)


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

    # Organes — tableau chiffré (remplace heatmap_organes) + treemap
    tbl_organes = organe_counts_table(aphp, entity, appareil)
    fig_tree = treemap_organes(aphp, entity, appareil, last_year)

    # Survie : répartition par stade + évolution POUR LES DEUX stades (I-III et IV)
    fig_surv = survival_by_stage(surv, entity, appareil, year=last_year)
    fig_surv_evo_i3 = survival_evolution(surv, entity, appareil, stade="I-III")
    fig_surv_evo_iv = survival_evolution(surv, entity, appareil, stade="IV")

    # Délais
    fig_delay = delay_evolution(aphp, entity, appareil)
    all_delay_ents = pd.concat([aphp_app, ghu_app])
    fig_delay_cmp = delay_comparison_bar(all_delay_ents, appareil, last_year)

    # Contexte régional (seulement si l'extrait régional est rempli)
    reg_dispo = regional_disponible(reg)
    if reg_dispo:
        reg_app = reg[(reg.appareil == appareil) & (reg.organe == "TOTAL")]
        fig_reg = regional_comparison(reg_app, "nb_patients",
                                      f"Contexte régional — {appareil}",
                                      color_map=REGIONAL_COLORS)
        reg_app_last = reg_app[reg_app.annee == last_year]
        fig_reg_donut = donut_market_share(
            reg_app_last, "entite", "nb_patients",
            f"Parts de marché régional — {appareil} ({last_year})",
            entities=sorted(reg_app_last["entite"].unique()), color_map=REGIONAL_COLORS)

    # Bandeau d'accès aux versions GHU (promu en HAUT de page)
    _app_slug = slugify(appareil)
    ghu_banner = ghu_switch_banner(
        entity,
        lambda e: (f"rapport_appareil_{_app_slug}.html" if e == "AP-HP"
                   else f"rapport_appareil_{_app_slug}_{slugify(e)}.html"),
    )

    nav = "\n".join([
        '<a href="index.html">← AP-HP Global</a>',
        f'<a href="#kpis">Indicateurs {last_year}</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#organes">Par organe</a>',
        '<a href="#survie">Survie</a>',
        '<a href="#delais">Délais</a>',
    ])

    content = ghu_banner
    content += section(f"Indicateurs clés — {appareil} — {last_year}", kpis_html, "kpis")
    if entity == "AP-HP":
        # AP-HP : Évolution = contexte RÉGIONAL (si dispo) + séjours par mode.
        # Extrait régional vide → on n'affiche que les séjours (pas de cartes vides).
        if reg_dispo:
            evo_html = f"""
            <div class="chart-grid-2">
              {chart_card(fig_to_html(fig_reg))}
              {chart_card(fig_to_html(fig_reg_donut))}
            </div>
            <div style="margin-top:20px">{chart_card(fig_to_html(fig_sejours), "full")}</div>
            """
        else:
            evo_html = f'{chart_card(fig_to_html(fig_sejours), "full")}'
    else:
        # GHU : patients = TOUS les GHU ; part de marché du GHU dans l'AP-HP ; pas de régional
        fig_pts_ghu = line_evolution(ghu_app, "annee", "nb_patients", "entite",
                                     f"Patients par GHU — {appareil}", entities=GHU_LIST)
        fig_market = _market_share_evolution(ent_app, aphp_app, entity, appareil)
        evo_html = f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts_ghu))}
          {chart_card(fig_to_html(fig_donut))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_sejours))}
          {chart_card(fig_to_html(fig_market))}
        </div>
        """
    content += section("Évolution du nombre de patients", evo_html, "evolution")
    # Liens organes pour cet appareil (pages publiables uniquement, cf. referentiels).
    app_slug_local = slugify(appareil)
    orgs_of_app = sorted(
        o for o in aphp[(aphp.entite == "AP-HP") & (aphp.appareil == appareil)
                        & (aphp.organe != "TOTAL")].organe.unique()
        if organe_publiable(o)
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
        {chart_card(tbl_organes, "full")}
        <div style="margin-top:20px">{chart_card(fig_to_html(fig_tree), "full")}</div>
        {f'<div style="margin-top:16px;padding:14px;background:#F8F9FA;border-radius:8px"><strong style="color:#003189">Organes — {appareil} :</strong><br>{org_links_html}</div>' if org_links_html else ''}
    """, "organes", action=organes_action)
    content += section("Survie par stade", f"""
        {chart_card(fig_to_html(fig_surv), "full")}
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_surv_evo_i3))}
          {chart_card(fig_to_html(fig_surv_evo_iv))}
        </div>
    """, "survie")
    content += section("Délais de prise en charge", f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_delay))}
          {chart_card(fig_to_html(fig_delay_cmp))}
        </div>
    """, "delais")

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

    # Patients GHU
    ghu_org = org_data[org_data.entite.isin(GHU_LIST)]
    ghu_last = ghu_org[ghu_org.annee == last_year]
    fig_donut = donut_market_share(ghu_last, "entite", "nb_patients",
                                   f"Répartition GHU — {organe} ({last_year})")

    melted = ent_org.melt(id_vars=["annee"], value_vars=list(TREATMENT_COLS.keys()),
                           var_name="type_sejour", value_name="nb_sejours")
    melted["label"] = melted["type_sejour"].map(TREATMENT_COLS)
    fig_sejours = line_evolution(melted, "annee", "nb_sejours", "label",
                                 f"Séjours par mode de PEC — {organe}",
                                 entities=list(TREATMENT_COLS.values()))

    # Survie : répartition par stade + évolution POUR LES DEUX stades (I-III et IV)
    surv_org = surv[(surv.organe == organe) & (surv.appareil == appareil)] if surv is not None else pd.DataFrame()
    org_surv = organe if not surv_org.empty else "TOTAL"
    fig_surv = survival_by_stage(surv, entity, appareil,
                                 **({"organe": organe} if not surv_org.empty else {}), year=last_year)
    fig_surv_evo_i3 = survival_evolution(surv, entity, appareil, organe=org_surv, stade="I-III")
    fig_surv_evo_iv = survival_evolution(surv, entity, appareil, organe=org_surv, stade="IV")

    # Délais
    fig_delay = delay_evolution(aphp, entity, appareil, organe=organe)

    # Contexte régional (seulement si l'extrait régional est rempli)
    reg_dispo = regional_disponible(reg)
    if reg_dispo:
        reg_org = reg[(reg.appareil == appareil) & (reg.organe == organe)]
        if reg_org.empty:
            reg_org = reg[(reg.appareil == appareil) & (reg.organe == "TOTAL")]
        fig_reg = regional_comparison(reg_org, "nb_patients",
                                      f"Contexte régional — {organe}",
                                      color_map=REGIONAL_COLORS)
        reg_org_last = reg_org[reg_org.annee == last_year]
        fig_reg_donut = donut_market_share(
            reg_org_last, "entite", "nb_patients",
            f"Parts de marché régional — {organe} ({last_year})",
            entities=sorted(reg_org_last["entite"].unique()), color_map=REGIONAL_COLORS)

    app_slug = slugify(appareil)
    org_slug = slugify(organe)

    # Bandeau d'accès aux versions GHU (promu en HAUT de page)
    ghu_banner = ghu_switch_banner(
        entity,
        lambda e: (f"rapport_organe_{org_slug}.html" if e == "AP-HP"
                   else f"rapport_organe_{org_slug}_{slugify(e)}.html"),
    )

    nav = "\n".join([
        f'<a href="rapport_appareil_{app_slug}.html">← {appareil}</a>',
        f'<a href="#kpis">Indicateurs {last_year}</a>',
        '<a href="#evolution">Évolution</a>',
        '<a href="#survie">Survie</a>',
        '<a href="#delais">Délais</a>',
    ])

    content = ghu_banner
    content += section(f"Indicateurs clés — {organe} — {last_year}", kpis_html, "kpis")
    if entity == "AP-HP":
        # AP-HP : Évolution = contexte RÉGIONAL (si dispo) + séjours par mode.
        # Extrait régional vide → on n'affiche que les séjours (pas de cartes vides).
        if reg_dispo:
            evo_html = f"""
            <div class="chart-grid-2">
              {chart_card(fig_to_html(fig_reg))}
              {chart_card(fig_to_html(fig_reg_donut))}
            </div>
            <div style="margin-top:20px">{chart_card(fig_to_html(fig_sejours), "full")}</div>
            """
        else:
            evo_html = f'{chart_card(fig_to_html(fig_sejours), "full")}'
    else:
        # GHU : patients = TOUS les GHU ; part de marché du GHU dans l'AP-HP ; pas de régional
        fig_pts_ghu = line_evolution(ghu_org, "annee", "nb_patients", "entite",
                                     f"Patients par GHU — {organe}", entities=GHU_LIST)
        fig_market = _market_share_evolution(ent_org, aphp_org, entity, organe)
        evo_html = f"""
        <div class="chart-grid-2">
          {chart_card(fig_to_html(fig_pts_ghu))}
          {chart_card(fig_to_html(fig_donut))}
        </div>
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_sejours))}
          {chart_card(fig_to_html(fig_market))}
        </div>
        """
    content += section("Évolution", evo_html, "evolution")
    content += section("Survie par stade", f"""
        {chart_card(fig_to_html(fig_surv), "full")}
        <div class="chart-grid-2" style="margin-top:20px">
          {chart_card(fig_to_html(fig_surv_evo_i3))}
          {chart_card(fig_to_html(fig_surv_evo_iv))}
        </div>
    """, "survie")
    content += section("Délais de prise en charge",
                       chart_card(fig_to_html(fig_delay)), "delais")

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

    # Exclusion des sites SSR/gériatrie : journalisée une fois par page.
    exclus = sorted({e for e in surv_df["entite"].unique()
                     if e in mapping and _est_exclu(e)})
    print(f"  Survie inter-hôpitaux : {len(exclus)} hôpital(aux) exclu(s) : {exclus}")

    def _a_des_donnees(appareil):
        h = surv_df[(surv_df.appareil == appareil) & (surv_df.organe == "TOTAL")
                    & (surv_df.stade == "I-III") & (surv_df.population == "tous")
                    & (surv_df.annee == last_year) & (surv_df.entite.isin(mapping))
                    & (~surv_df.entite.map(_est_exclu))]
        return not h.empty

    intro = (
        '<p style="color:#6C757D;font-size:.9rem;margin-bottom:18px">'
        'Survie à 5 ans (barres) et à 1 an (losanges) par hôpital, déclinée par '
        '<b>stade (I-III puis IV)</b>. Les hôpitaux sont <b>colorés par GHU</b> et triés par '
        'survie décroissante. Le trait plein noir marque la référence <b>AP-HP</b> ; les '
        'pointillés colorés, la référence de chaque <b>GHU</b>.</p>'
    )

    def _paire_stades(appareil):
        """Deux graphiques empilés (stade I-III puis IV) pour un appareil donné."""
        html = ""
        for stade in ("I-III", "IV"):
            fig = survival_hospital_comparison(surv_df, mapping, appareil=appareil,
                                               organe="TOTAL", stade=stade,
                                               population="tous", annee=last_year)
            html += chart_card(fig_to_html(fig), "full")
        return html

    content = ""
    # 1. Comparaison globale (toutes localisations) — I-III + IV
    content += section("Comparaison globale — toutes localisations",
                       intro + _paire_stades("TOTAL"),
                       "global")

    # 2. Déclinaison par grand appareil (sections non vides) — I-III + IV
    nav_app = []
    for app in _APPAREILS_COMPARAISON:
        if not _a_des_donnees(app):
            continue
        anchor = "cmp-" + slugify(app)
        content += section(app.capitalize(), _paire_stades(app), anchor)
        nav_app.append(f'<a href="#{anchor}">{app.capitalize()}</a>')

    nav = "\n".join([
        '<a href="index.html">← Accueil AP-HP</a>',
        '<a href="#global">Comparaison globale</a>',
    ] + nav_app + [
        '<a href="comparaison_hopitaux_delais.html">Délais →</a>',   # cross-link réciproque
    ])

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


def build_rapport_comparaison_hopitaux_delais(delais_df: pd.DataFrame, mapping: dict,
                                              output_dir: Path) -> Path:
    """Page « Comparaison inter-hôpitaux — Délais » : délai global médian par hôpital,
    trié CROISSANT (plus court = mieux), coloré par GHU, marqueurs des modalités
    (chir/traitement médical/radio), repères AP-HP/GHU. Comparaison globale (TOTAL/TOTAL) puis
    déclinaison par grand appareil (sections non vides). Calque de la page survie."""
    annees = sorted(delais_df["annee"].unique()) if not delais_df.empty else []
    last_year = int(annees[-1]) if annees else None
    year_range = f"{annees[0]}–{annees[-1]}" if annees else ""

    # Exclusion des sites SSR/gériatrie : journalisée une fois par page.
    exclus = sorted({e for e in delais_df["entite"].unique()
                     if e in mapping and _est_exclu(e)})
    print(f"  Délais inter-hôpitaux : {len(exclus)} hôpital(aux) exclu(s) : {exclus}")

    def _a_des_donnees(appareil):
        h = delais_df[(delais_df.appareil == appareil) & (delais_df.organe == "TOTAL")
                      & (delais_df.annee == last_year) & (delais_df.entite.isin(mapping))
                      & (delais_df.delai_global_median.notna())
                      & (~delais_df.entite.map(_est_exclu))]
        return not h.empty

    intro = (
        '<p style="color:#6C757D;font-size:.9rem;margin-bottom:18px">'
        'Délai global médian de prise en charge (barres) par hôpital, avec les délais '
        'par modalité (<b>chirurgie, traitement médical, radiothérapie</b>) en marqueurs. '
        'Les hôpitaux sont <b>colorés par GHU</b> et triés par délai <b>croissant</b> '
        '(un délai plus court est meilleur). Le trait plein noir marque la référence '
        '<b>AP-HP</b> ; les pointillés colorés, la référence de chaque <b>GHU</b>.</p>'
    )

    content = ""
    # 1. Comparaison globale (toutes localisations)
    fig_glob = delay_hospital_comparison(delais_df, mapping, appareil="TOTAL",
                                         organe="TOTAL", annee=last_year)
    content += section("Comparaison globale — toutes localisations",
                       intro + chart_card(fig_to_html(fig_glob), "full"),
                       "global")

    # 2. Déclinaison par grand appareil (sections non vides)
    nav_app = []
    for app in _APPAREILS_COMPARAISON:
        if not _a_des_donnees(app):
            continue
        anchor = "cmp-" + slugify(app)
        fig = delay_hospital_comparison(delais_df, mapping, appareil=app,
                                        organe="TOTAL", annee=last_year)
        content += section(app.capitalize(), chart_card(fig_to_html(fig), "full"), anchor)
        nav_app.append(f'<a href="#{anchor}">{app.capitalize()}</a>')

    nav = "\n".join([
        '<a href="index.html">← Accueil AP-HP</a>',
        '<a href="#global">Comparaison globale</a>',
    ] + nav_app + [
        '<a href="rapport_comparaison_hopitaux.html">Survie →</a>',   # cross-link réciproque
    ])

    html = _render_page(year_range,
        title="Comparaison inter-hôpitaux — Délais",
        subtitle=f"Délais de PEC par hôpital, groupés par GHU · {year_range} · Indicateurs OECI",
        nav_links=nav,
        content=content,
        date=datetime.now().strftime("%d/%m/%Y"),
    )
    out = output_dir / "comparaison_hopitaux_delais.html"
    out.write_text(html, encoding="utf-8")
    print(f"  → {out}")
    return out

