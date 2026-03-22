"""
chart_utils.py
Fonctions de visualisation Plotly avec charte graphique AP-HP / style CovidTracker.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Palette de couleurs ────────────────────────────────────────────────────────

COLORS = {
    "AP-HP":       "#1A1A2E",
    "GHU Centre":  "#E63946",
    "GHU Mondor":  "#2A9D8F",
    "GHU Nord":    "#457B9D",
    "GHU PSSD":    "#F4A261",
    "GHU PSL":     "#264653",
    "GHU SUN":     "#A8DADC",
    # Types régionaux
    "Clinique":    "#FF6B6B",
    "CH":          "#4ECDC4",
    "CHU":         "#45B7D1",
    "PSPH":        "#96CEB4",
    # Modes de prise en charge
    "Chirurgie":         "#2196F3",
    "Chimiothérapie":    "#E63946",
    "Radiothérapie":     "#2A9D8F",
    "Soins palliatifs":  "#F4A261",
    # Misc
    "primary":   "#003189",
    "secondary": "#E63946",
}

TREATMENT_COLS = {
    "nb_sejours_chirurgie":       "Chirurgie",
    "nb_sejours_chimiotherapie":  "Chimiothérapie",
    "nb_sejours_radiotherapie":   "Radiothérapie",
    "nb_sejours_palliatifs":      "Soins palliatifs",
}

GHU_LIST = ["GHU Centre", "GHU Mondor", "GHU Nord", "GHU PSSD", "GHU PSL", "GHU SUN"]

# ── Style global ───────────────────────────────────────────────────────────────

BASE_LAYOUT = dict(
    font=dict(family="Inter, Arial, sans-serif", size=13, color="#1A1A2E"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=70, b=50, l=70, r=30),
    legend=dict(
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#DEE2E6",
        borderwidth=1,
        font_size=12,
    ),
    hovermode="x unified",
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False),
)


def _layout(**kwargs):
    d = BASE_LAYOUT.copy()
    d.update(kwargs)
    return d


def get_color(name: str) -> str:
    return COLORS.get(name, "#888888")


# ── Graphiques ─────────────────────────────────────────────────────────────────

def line_evolution(
    df: pd.DataFrame,
    x: str,
    y: str,
    group: str,
    title: str,
    y_label: str = "",
    entities: list = None,
    show_covid: bool = True,
) -> go.Figure:
    """Courbes d'évolution temporelle pour plusieurs entités."""
    fig = go.Figure()
    ents = entities or sorted(df[group].unique())

    for ent in ents:
        d = df[df[group] == ent].sort_values(x)
        vals = d[y].values
        pcts = [None] + [
            f"{(v - p) / p * 100:+.1f}%" if p else "N/A"
            for v, p in zip(vals[1:], vals[:-1])
        ]
        color = get_color(ent)
        width = 3 if ent == "AP-HP" else 2
        dash = "solid" if ent == "AP-HP" else "solid"

        fig.add_trace(go.Scatter(
            x=d[x], y=d[y],
            name=ent,
            mode="lines+markers",
            line=dict(color=color, width=width, dash=dash),
            marker=dict(size=8, color=color, line=dict(width=1.5, color="white")),
            customdata=pcts,
            hovertemplate=(
                f"<b>{ent}</b><br>"
                f"%{{y:,.0f}}<br>"
                f"Évol. N-1 : %{{customdata}}"
                "<extra></extra>"
            ),
        ))

    if show_covid:
        fig.add_vrect(
            x0=2019.5, x1=2020.5,
            fillcolor="#FFE8E8", opacity=0.5,
            line_width=0, layer="below",
            annotation_text="COVID-19",
            annotation_position="top left",
            annotation_font_size=11,
            annotation_font_color="#E63946",
        )

    fig.update_layout(
        title=dict(text=title, font_size=17),
        xaxis_title="Année",
        yaxis_title=y_label,
        **_layout(),
    )
    return fig


def bar_comparison(
    df: pd.DataFrame,
    x: str,
    y: str,
    group: str,
    title: str,
    y_label: str = "",
    barmode: str = "group",
    entities: list = None,
) -> go.Figure:
    """Graphique en barres groupées ou empilées."""
    fig = go.Figure()
    ents = entities or sorted(df[group].unique())

    for ent in ents:
        d = df[df[group] == ent].sort_values(x)
        fig.add_trace(go.Bar(
            x=d[x], y=d[y],
            name=ent,
            marker_color=get_color(ent),
            hovertemplate=f"<b>{ent}</b><br>%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font_size=17),
        xaxis_title="Année",
        yaxis_title=y_label,
        barmode=barmode,
        **_layout(),
    )
    return fig


def stacked_treatments(
    df: pd.DataFrame,
    group_col: str,
    title: str,
    orientation: str = "v",
) -> go.Figure:
    """Barres empilées des 4 modes de prise en charge."""
    fig = go.Figure()
    groups = sorted(df[group_col].unique())

    for col, label in TREATMENT_COLS.items():
        if col not in df.columns:
            continue
        vals = [df[df[group_col] == g][col].sum() for g in groups]
        fig.add_trace(go.Bar(
            x=groups if orientation == "v" else vals,
            y=vals if orientation == "v" else groups,
            name=label,
            marker_color=get_color(label),
            orientation=orientation,
            hovertemplate=f"<b>{label}</b><br>%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font_size=17),
        barmode="stack",
        **_layout(),
    )
    return fig


def donut_market_share(
    df_year: pd.DataFrame,
    entity_col: str,
    value_col: str,
    title: str,
    entities: list = None,
) -> go.Figure:
    """Camembert/donut pour les parts de marché."""
    ents = entities or GHU_LIST
    d = df_year[df_year[entity_col].isin(ents)].copy()
    total = d[value_col].sum()

    fig = go.Figure(go.Pie(
        labels=d[entity_col],
        values=d[value_col],
        hole=0.55,
        marker_colors=[get_color(e) for e in d[entity_col]],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} patients<br>%{percent}<extra></extra>",
        sort=True,
    ))

    fig.add_annotation(
        text=f"<b>{total:,.0f}</b><br>patients",
        x=0.5, y=0.5,
        font_size=16, showarrow=False,
        xanchor="center",
    )

    fig.update_layout(
        title=dict(text=title, font_size=17),
        paper_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif"),
        margin=dict(t=70, b=30, l=30, r=30),
        legend=dict(font_size=12),
        showlegend=True,
    )
    return fig


def heatmap_appareils(
    df: pd.DataFrame,
    entity: str,
    value_col: str = "nb_patients",
    title: str = "",
) -> go.Figure:
    """Heatmap évolution par appareil au fil des années."""
    d = df[
        (df.get("entite", df.get("type_etab")) == entity)
        & (df.organe == "TOTAL")
        & (df.appareil != "TOTAL")
    ].copy()

    pivot = d.pivot_table(index="appareil", columns="annee", values=value_col, aggfunc="sum")
    # Normalisation par ligne (% par rapport à la moyenne)
    pivot_norm = pivot.div(pivot.mean(axis=1), axis=0).round(2)

    short_labels = [a[:35] + ("…" if len(a) > 35 else "") for a in pivot_norm.index]

    fig = go.Figure(go.Heatmap(
        z=pivot_norm.values,
        x=[str(c) for c in pivot_norm.columns],
        y=short_labels,
        customdata=pivot.values,
        colorscale="Blues",
        hovertemplate="<b>%{y}</b><br>Année %{x}<br>%{customdata:,.0f} patients<extra></extra>",
        showscale=True,
        colorbar=dict(title="Index<br>(moy.=1)", len=0.6),
    ))

    fig.update_layout(
        title=dict(text=title or f"Évolution par appareil — {entity}", font_size=17),
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed", tickfont_size=11),
        margin=dict(t=70, b=50, l=300, r=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif"),
        height=500,
    )
    return fig


def waterfall_trends(df_entity: pd.DataFrame, title: str = "") -> go.Figure:
    """Waterfall chart pour visualiser les variations annuelles."""
    d = df_entity.sort_values("annee")
    years = d["annee"].tolist()
    vals = d["nb_patients"].tolist()

    measures = ["absolute"] + ["relative"] * (len(vals) - 1)
    y_wf = [vals[0]] + [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    colors_wf = ["#003189"] + [
        "#2A9D8F" if v >= 0 else "#E63946" for v in y_wf[1:]
    ]

    fig = go.Figure(go.Waterfall(
        x=[str(y) for y in years],
        y=y_wf,
        measure=measures,
        connector=dict(line=dict(color="#CED4DA", width=1.5)),
        increasing=dict(marker_color="#2A9D8F"),
        decreasing=dict(marker_color="#E63946"),
        totals=dict(marker_color="#003189"),
        text=[f"{v:+,.0f}" if i > 0 else f"{v:,.0f}" for i, v in enumerate(y_wf)],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:+,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font_size=17),
        xaxis_title="Année",
        yaxis_title="Patients",
        **_layout(),
    )
    return fig


def kpi_indicators(values: dict, title: str = "") -> go.Figure:
    """Tableau de bord d'indicateurs KPI (Indicator tiles)."""
    n = len(values)
    cols = min(n, 4)
    rows = (n + cols - 1) // cols

    items = list(values.items())
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[v[0] for v in items],
        specs=[[{"type": "indicator"}] * cols for _ in range(rows)],
    )

    for i, (label, (value, delta, ref)) in enumerate(items):
        row = i // cols + 1
        col = i % cols + 1
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=value,
                delta=dict(
                    reference=ref,
                    valueformat=",.0f",
                    increasing_color="#2A9D8F",
                    decreasing_color="#E63946",
                ),
                number=dict(valueformat=",.0f", font_size=32),
            ),
            row=row, col=col,
        )

    fig.update_layout(
        title=dict(text=title, font_size=17),
        paper_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif"),
        height=140 * rows + 60,
        margin=dict(t=70, b=20, l=20, r=20),
    )
    return fig


def regional_comparison(
    df_reg: pd.DataFrame,
    y_col: str,
    title: str,
    highlight: str = "AP-HP",
) -> go.Figure:
    """Comparaison AP-HP vs autres types d'établissements régionaux."""
    fig = go.Figure()
    types = sorted(df_reg["type_etab"].unique())

    for t in types:
        d = df_reg[df_reg["type_etab"] == t].sort_values("annee")
        width = 3 if t == highlight else 1.8
        dash = "solid" if t == highlight else "dot"
        fig.add_trace(go.Scatter(
            x=d["annee"], y=d[y_col],
            name=t,
            mode="lines+markers",
            line=dict(color=get_color(t), width=width, dash=dash),
            marker=dict(size=7, color=get_color(t)),
            hovertemplate=f"<b>{t}</b><br>%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font_size=17),
        xaxis_title="Année",
        **_layout(),
    )
    return fig


# ── Export HTML ────────────────────────────────────────────────────────────────

def fig_to_html(fig: go.Figure, full: bool = False) -> str:
    """Convertit une figure Plotly en HTML (fragment ou complet)."""
    return fig.to_html(
        full_html=full,
        include_plotlyjs="cdn" if full else False,
        config={"displayModeBar": True, "displaylogo": False},
    )


# ── Slugification ──────────────────────────────────────────────────────────────

import unicodedata as _ud

def slugify(name: str, max_len: int = 50) -> str:
    """Transforme un nom en slug URL-safe."""
    s = _ud.normalize('NFD', str(name).lower())
    s = ''.join(c for c in s if _ud.category(c) != 'Mn')
    for c in ' /(),.-':
        s = s.replace(c, '_')
    return '_'.join(p for p in s.split('_') if p)[:max_len]


# ── Heatmap organes ────────────────────────────────────────────────────────────

def heatmap_organes(
    df: pd.DataFrame,
    entity: str,
    appareil: str,
    entity_col: str = "entite",
    value_col: str = "nb_patients",
    title: str = "",
) -> go.Figure:
    """Heatmap évolution par organe pour un appareil donné."""
    d = df[
        (df[entity_col] == entity)
        & (df["appareil"] == appareil)
        & (df["organe"] != "TOTAL")
    ].copy()

    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"Pas de sous-organe pour {appareil}",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False)
        fig.update_layout(**_layout())
        return fig

    pivot = d.pivot_table(index="organe", columns="annee", values=value_col, aggfunc="sum")
    pivot_norm = pivot.div(pivot.mean(axis=1), axis=0).round(2)
    short_labels = [o[:40] + ("…" if len(o) > 40 else "") for o in pivot_norm.index]

    fig = go.Figure(go.Heatmap(
        z=pivot_norm.values,
        x=[str(c) for c in pivot_norm.columns],
        y=short_labels,
        customdata=pivot.values,
        colorscale="Blues",
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata:,.0f} patients<extra></extra>",
        showscale=True,
        colorbar=dict(title="Index<br>(moy=1)", len=0.6),
    ))
    fig.update_layout(
        title=dict(text=title or f"Évolution par organe — {appareil} — {entity}", font_size=17),
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed", tickfont_size=11),
        margin=dict(t=70, b=50, l=280, r=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif"),
        height=max(300, 50 * len(pivot_norm) + 120),
    )
    return fig


def treemap_organes(
    df: pd.DataFrame,
    entity: str,
    appareil: str,
    year: int,
    entity_col: str = "entite",
    value_col: str = "nb_patients",
) -> go.Figure:
    """Treemap de la répartition des organes pour une année donnée."""
    d = df[
        (df[entity_col] == entity)
        & (df["appareil"] == appareil)
        & (df["organe"] != "TOTAL")
        & (df["annee"] == year)
    ].copy()

    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas de données", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    fig = go.Figure(go.Treemap(
        labels=d["organe"],
        values=d[value_col],
        parents=[""] * len(d),
        textinfo="label+value+percent root",
        marker=dict(colorscale="Blues", showscale=False),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} patients<br>%{percentRoot:.1%}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Répartition par organe — {appareil} — {year}", font_size=17),
        paper_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif"),
        margin=dict(t=60, b=20, l=20, r=20),
        height=420,
    )
    return fig


# ── Survie par stade ───────────────────────────────────────────────────────────

def survival_by_stage(
    df_surv: pd.DataFrame,
    entity: str,
    appareil: str,
    organe: str = "TOTAL",
    year: int = None,
) -> go.Figure:
    """Graphique en barres groupées : survie à 1 an et 5 ans par stade."""
    d = df_surv[
        (df_surv["entite"] == entity)
        & (df_surv["appareil"] == appareil)
        & (df_surv["organe"] == organe)
    ].copy()

    if year is None:
        year = int(d["annee"].max())
    d = d[d["annee"] == year]

    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas de données de survie", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    # Exclure "Non précisé" pour la lisibilité principale
    d = d[d["stade"] != "Non précisé"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d["stade"], y=d["survie_1an"],
        name="Survie à 1 an",
        marker_color="#2A9D8F",
        hovertemplate="Stade %{x}<br>Survie 1 an : <b>%{y}%</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=d["stade"], y=d["survie_5ans"],
        name="Survie à 5 ans",
        marker_color="#E63946",
        hovertemplate="Stade %{x}<br>Survie 5 ans : <b>%{y}%</b><extra></extra>",
    ))

    lo = _layout()
    lo["yaxis"] = dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False,
                       title="Taux de survie (%)", range=[0, 105])
    fig.update_layout(
        title=dict(text=f"Survie par stade — {appareil} — {entity} ({year})", font_size=17),
        xaxis_title="Stade",
        barmode="group",
        **lo,
    )
    return fig


def survival_evolution(
    df_surv: pd.DataFrame,
    entity: str,
    appareil: str,
    organe: str = "TOTAL",
    stade: str = "II",
) -> go.Figure:
    """Évolution de la survie au fil des années pour un stade donné."""
    d = df_surv[
        (df_surv["entite"] == entity)
        & (df_surv["appareil"] == appareil)
        & (df_surv["organe"] == organe)
        & (df_surv["stade"] == stade)
    ].sort_values("annee")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["annee"], y=d["survie_1an"],
        name="Survie à 1 an",
        mode="lines+markers",
        line=dict(color="#2A9D8F", width=2.5),
        marker=dict(size=8),
        hovertemplate="Survie 1 an : %{y}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=d["annee"], y=d["survie_5ans"],
        name="Survie à 5 ans",
        mode="lines+markers",
        line=dict(color="#E63946", width=2.5),
        marker=dict(size=8),
        hovertemplate="Survie 5 ans : %{y}%<extra></extra>",
    ))

    lo = _layout()
    lo["yaxis"] = dict(showgrid=True, gridcolor="#F0F0F0", zeroline=False,
                       title="Taux de survie (%)", range=[0, 105])
    fig.update_layout(
        title=dict(text=f"Évolution de la survie (stade {stade}) — {appareil} — {entity}", font_size=17),
        xaxis_title="Année",
        **lo,
    )
    return fig


# ── Délais de prise en charge ──────────────────────────────────────────────────

def delay_evolution(
    df: pd.DataFrame,
    entity: str,
    appareil: str,
    organe: str = "TOTAL",
    entity_col: str = "entite",
) -> go.Figure:
    """Évolution des délais médians de prise en charge."""
    d = df[
        (df[entity_col] == entity)
        & (df["appareil"] == appareil)
        & (df["organe"] == organe)
    ].sort_values("annee").copy()

    if d.empty or "delai_global_median" not in d.columns:
        fig = go.Figure()
        fig.add_annotation(text="Pas de données de délai", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    delay_cols = {
        "delai_global_median":    ("Délai global",        "#1A1A2E"),
        "delai_chirurgie_median": ("Chirurgie",           "#2196F3"),
        "delai_chimio_median":    ("Chimiothérapie",      "#E63946"),
        "delai_radio_median":     ("Radiothérapie",       "#2A9D8F"),
    }

    fig = go.Figure()
    for col, (label, color) in delay_cols.items():
        if col in d.columns and d[col].notna().any():
            fig.add_trace(go.Scatter(
                x=d["annee"], y=d[col],
                name=label,
                mode="lines+markers",
                line=dict(color=color, width=2.5 if "global" in col else 1.8),
                marker=dict(size=7),
                hovertemplate=f"<b>{label}</b><br>%{{y}} jours<extra></extra>",
            ))

    fig.add_vrect(
        x0=2019.5, x1=2020.5,
        fillcolor="#FFE8E8", opacity=0.5,
        line_width=0, layer="below",
        annotation_text="COVID-19",
        annotation_position="top left",
        annotation_font_size=11,
        annotation_font_color="#E63946",
    )

    fig.update_layout(
        title=dict(text=f"Délais médians de PEC — {appareil} — {entity}", font_size=17),
        xaxis_title="Année",
        yaxis_title="Délai (jours)",
        **_layout(),
    )
    return fig


def delay_comparison_bar(
    df: pd.DataFrame,
    appareil: str,
    year: int,
    entity_col: str = "entite",
    entities: list = None,
) -> go.Figure:
    """Barres comparant les délais globaux entre entités pour une année donnée."""
    d = df[
        (df["appareil"] == appareil)
        & (df["organe"] == "TOTAL")
        & (df["annee"] == year)
    ].copy()

    if entities:
        d = d[d[entity_col].isin(entities)]

    if d.empty or "delai_global_median" not in d.columns:
        return go.Figure()

    d = d.sort_values("delai_global_median")
    colors = [get_color(e) for e in d[entity_col]]

    fig = go.Figure(go.Bar(
        x=d[entity_col], y=d["delai_global_median"],
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>%{y} jours<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Délai global médian — {appareil} — {year}", font_size=17),
        xaxis_title="",
        yaxis_title="Délai (jours)",
        **_layout(),
    )
    return fig
