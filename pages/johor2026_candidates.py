"""
pages/johor2026_candidates.py — Johor 2026 Candidates Overview
Nomination-day candidate data: every individual party kept distinct (no OTHERS lumping
for MUDA/BERSAMA/etc). Map uses JOHOR_2022_DUN_BOUNDARIES.geojson (boundaries assumed
unchanged for the 2026 contest). Demographic charts compare electorate composition
(2022 DUN composition data) against the 2026 candidates' own sex/age makeup.
"""

from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from collections import defaultdict

from utils.johor2026_data import (
    load_2026_candidates, party_color, bloc_color, load_geo, seat_options, seat_code_label, coalition_label,
)
from utils.johor_data import load_johor_demographics
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT, map_bounds_zoom

JOHOR_CENTER = (1.8, 103.3, 8.2)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(color=TEXT_MUTED, size=11)),
)

AGE_BUCKETS = ["Under 30", "30–39", "40–49", "50–59", "60 and above"]
AGE_ELECTORATE_COLS = {
    "Under 30":     ["18-20 (%)", "21-29 (%)"],
    "30–39":        ["30-39 (%)"],
    "40–49":        ["40-49 (%)"],
    "50–59":        ["50-59 (%)"],
    "60 and above": ["60-69 (%)", "70-79 (%)", "80-89 (%)", "ABOVE 90 (%)"],
}


def age_bucket(age):
    if pd.isna(age):
        return None
    age = float(age)
    if age < 30: return "Under 30"
    if age < 40: return "30–39"
    if age < 50: return "40–49"
    if age < 60: return "50–59"
    return "60 and above"


def card_style():
    return {"background": BG_CARD, "border": f"1px solid {BORDER}", "borderRadius": "12px", "padding": "4px"}


def _kpi(label, value, sub=None, color=ACCENT):
    return html.Div([
        html.Div(label, style={"color": TEXT_MUTED, "fontSize": "10px", "textTransform": "uppercase",
                                "letterSpacing": "0.08em", "marginBottom": "5px"}),
        html.Div(value, style={"color": color, "fontSize": "24px", "fontWeight": "700",
                                "lineHeight": "1.1", "letterSpacing": "-0.02em"}),
        html.Div(sub or "", style={"color": TEXT_MUTED, "fontSize": "10px", "marginTop": "3px"}),
    ], style={"background": BG_CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px",
              "padding": "14px 16px", "flex": "1", "minWidth": "130px"})


def _label_style():
    return {"color": TEXT_MUTED, "fontSize": "11px", "textTransform": "uppercase",
            "letterSpacing": "0.07em", "marginBottom": "5px", "display": "block"}


def _filter(df, seats, parties):
    if seats:
        df = df[df["UNIQUE CODE"].isin(seats)]
    if parties:
        df = df[df["PARTY"].isin(parties)]
    return df


def make_map(df_all, df_filtered):
    geo = load_geo()
    if geo is None:
        fig = go.Figure()
        fig.add_annotation(text="GeoJSON not found", x=0.5, y=0.5, xref="paper", yref="paper",
                            font=dict(size=13, color=TEXT_MUTED), showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color=TEXT_PRIMARY))
        return fig

    by_seat = defaultdict(list)
    for _, row in df_all.iterrows():
        by_seat[row["UNIQUE CODE"]].append(row)

    highlighted_codes = set(df_filtered["UNIQUE CODE"].unique())

    def hover_for(code):
        rows = by_seat.get(code, [])
        if not rows:
            return "No candidate data"
        seat_label = rows[0]["SEAT_LABEL"]
        par = rows[0]["PARLIAMENTARY NAME"]
        lines = [f"<b>{seat_label.title()}</b> ({str(par).title()})", f"{len(rows)} candidate(s):"]
        for r in sorted(rows, key=lambda r: r["PARTY"]):
            sex = (r["SEX"] or "?")[:1]
            age = "?" if pd.isna(r["AGE"]) else int(r["AGE"])
            label = coalition_label(r["PARTY"], r["BLOC"])
            lines.append(f"&nbsp;&nbsp;• {label} — {r['CANDIDATE']} ({sex}, {age})")
        return "<br>".join(lines)

    fig = go.Figure()

    loc_z, hover_map = {}, {}
    for feat in geo["features"]:
        code = feat["id"]
        n = len(by_seat.get(code, []))
        loc_z[code] = n
        hover_map[code] = hover_for(code)
    fig.add_trace(go.Choroplethmap(
        geojson=geo, locations=list(loc_z.keys()), z=list(loc_z.values()),
        colorscale="Blues", showscale=True,
        colorbar=dict(title=dict(text="Candidates", font=dict(color=TEXT_MUTED, size=11)),
                      tickfont=dict(color=TEXT_MUTED, size=10), thickness=12, len=0.6),
        hovertext=list(hover_map.values()), hoverinfo="text",
        marker=dict(opacity=0.85, line=dict(color="#1a1a2e", width=0.4)),
        name="Candidates per seat",
    ))

    if highlighted_codes and len(highlighted_codes) < 56:
        feats = [f for f in geo["features"] if f["id"] in highlighted_codes]
        lat_c, lon_c, zoom = map_bounds_zoom(feats) if feats else JOHOR_CENTER
    else:
        lat_c, lon_c, zoom = JOHOR_CENTER

    fig.update_layout(
        map=dict(style="dark", center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        legend=dict(bgcolor=BG_CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=TEXT_MUTED, size=11), x=0.01, y=0.99, xanchor="left", yanchor="top"),
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER,
                        font=dict(family="Inter", color=TEXT_PRIMARY, size=12)),
    )
    return fig


def make_gender_chart(df, demo, seats_in_scope):
    demo_sub = demo[demo["UNIQUE CODE"].isin(seats_in_scope)] if seats_in_scope else demo
    elec_male = demo_sub["MALE ELECTORS (%)"].mean() if len(demo_sub) else 50
    elec_female = demo_sub["WOMEN ELECTORS (%)"].mean() if len(demo_sub) else 50

    n = len(df)
    cand_male = (df["SEX"] == "MALE").sum() / n * 100 if n else 0
    cand_female = (df["SEX"] == "FEMALE").sum() / n * 100 if n else 0

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Electorate", x=["Male", "Female"], y=[elec_male, elec_female],
        marker_color=ACCENT, opacity=0.55,
        text=[f"{v:.1f}%" for v in [elec_male, elec_female]], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Electorate: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(name="2026 Candidates", x=["Male", "Female"], y=[cand_male, cand_female],
        marker_color="#E91E63",
        text=[f"{v:.1f}%" for v in [cand_male, cand_female]], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Candidates: %{y:.1f}%<extra></extra>"))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Electorate vs Candidate Gender Breakdown", font=dict(size=14, color=TEXT_PRIMARY), x=0.01),
        barmode="group", showlegend=True,
        xaxis=dict(showgrid=False, color=TEXT_MUTED),
        yaxis=dict(range=[0, 100], ticksuffix="%", showgrid=True, gridcolor=BORDER, color=TEXT_MUTED),
        bargap=0.3, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def make_age_chart(df, demo, seats_in_scope):
    demo_sub = demo[demo["UNIQUE CODE"].isin(seats_in_scope)] if seats_in_scope else demo
    elec_vals = []
    for bucket in AGE_BUCKETS:
        cols = [c for c in AGE_ELECTORATE_COLS[bucket] if c in demo_sub.columns]
        elec_vals.append(sum(demo_sub[c].fillna(0).mean() for c in cols) if len(demo_sub) else 0)

    cand_ages = df["AGE"].dropna().apply(age_bucket)
    n = len(cand_ages)
    cand_vals = [(cand_ages == b).sum() / n * 100 if n else 0 for b in AGE_BUCKETS]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Electorate", x=AGE_BUCKETS, y=elec_vals,
        marker_color=ACCENT, opacity=0.55,
        text=[f"{v:.1f}%" for v in elec_vals], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Electorate: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(name="2026 Candidates", x=AGE_BUCKETS, y=cand_vals,
        marker_color="#E91E63",
        text=[f"{v:.1f}%" for v in cand_vals], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Candidates: %{y:.1f}%<extra></extra>"))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Electorate vs Candidate Age Breakdown", font=dict(size=14, color=TEXT_PRIMARY), x=0.01),
        barmode="group", showlegend=True,
        xaxis=dict(showgrid=False, color=TEXT_MUTED),
        yaxis=dict(ticksuffix="%", showgrid=True, gridcolor=BORDER, color=TEXT_MUTED),
        bargap=0.2, margin=dict(l=10, r=10, t=45, b=10))
    return fig


COALITION_BLOCS = ("BN", "PH", "PN")


def make_party_bar(df):
    counts = df.groupby(["PARTY", "BLOC"]).size().reset_index(name="N").sort_values("N", ascending=True)
    counts["LABEL"] = [coalition_label(p, b) for p, b in zip(counts["PARTY"], counts["BLOC"])]

    def bar_color(party, bloc):
        return bloc_color(bloc) if bloc in COALITION_BLOCS else party_color(party)

    fig = go.Figure(go.Bar(
        x=counts["N"], y=counts["LABEL"], orientation="h",
        marker_color=[bar_color(p, b) for p, b in zip(counts["PARTY"], counts["BLOC"])],
        text=[str(v) for v in counts["N"]], textposition="outside",
        textfont=dict(size=11, color=TEXT_PRIMARY), showlegend=False,
        hovertemplate="<b>%{y}</b><br>Candidates: %{x}<extra></extra>",
    ))
    for bloc in COALITION_BLOCS:
        if bloc in counts["BLOC"].values:
            fig.add_trace(go.Bar(x=[None], y=[None], marker_color=bloc_color(bloc), name=bloc, showlegend=True))
    base_layout = {k: v for k, v in CHART_LAYOUT.items() if k != "legend"}
    fig.update_layout(**base_layout,
        title=dict(text="Candidates Fielded per Party", font=dict(size=14, color=TEXT_PRIMARY), x=0.01),
        xaxis=dict(showgrid=True, gridcolor=BORDER, color=TEXT_MUTED),
        yaxis=dict(showgrid=False, color=TEXT_MUTED, tickfont=dict(size=11)),
        legend=dict(x=0.99, y=0.02, xanchor="right", yanchor="bottom", bgcolor=BG_CARD,
                    bordercolor=BORDER, borderwidth=1, font=dict(color=TEXT_MUTED, size=11),
                    title=dict(text="Coalition", font=dict(color=TEXT_PRIMARY, size=11))),
        bargap=0.25, margin=dict(l=10, r=30, t=45, b=10),
        height=max(320, len(counts) * 26))
    return fig


def layout():
    df = load_2026_candidates()
    seat_opts = seat_options()
    party_bloc = df.groupby("PARTY")["BLOC"].first()
    party_opts = [{"label": coalition_label(p, party_bloc[p]), "value": p} for p in sorted(party_bloc.index)]

    return html.Div([
        html.Div([
            html.Div([
                html.Span("CANDIDATES", style={"background": "#26C6DA", "color": "#06262b", "borderRadius": "4px",
                          "padding": "2px 8px", "fontSize": "10px", "fontWeight": "800",
                          "letterSpacing": "0.07em", "marginRight": "10px"}),
                html.Span("Johor 2026 Nomination", style={"color": TEXT_MUTED, "fontSize": "13px"}),
            ], style={"marginBottom": "6px"}),
            html.H2("Johor 2026 — Candidates Overview", style={"color": TEXT_PRIMARY,
                "fontSize": "clamp(18px,3vw,26px)", "fontWeight": "700", "margin": "0 0 8px 0",
                "letterSpacing": "-0.02em"}),
        ], style={"background": BG_CARD, "borderBottom": f"1px solid {BORDER}", "padding": "20px 28px"}),

        # Filters
        html.Div([
            html.Div([
                html.Label("Constituency", style=_label_style()),
                dcc.Dropdown(id="j26-cand-seat", options=seat_opts, multi=True,
                             placeholder="All 56 DUN seats", className="dash-dropdown-dark"),
            ], style={"flex": "2", "minWidth": "220px"}),
            html.Div([
                html.Label("Party", style=_label_style()),
                dcc.Dropdown(id="j26-cand-party", options=party_opts, multi=True,
                             placeholder="All parties", className="dash-dropdown-dark"),
            ], style={"flex": "2", "minWidth": "220px"}),
            html.Button("↺ Reset", id="j26-cand-reset", n_clicks=0, style={
                "background": "transparent", "color": TEXT_MUTED, "border": f"1px solid {BORDER}",
                "borderRadius": "8px", "padding": "8px 14px", "cursor": "pointer", "fontSize": "12px",
                "fontFamily": "Inter", "alignSelf": "flex-end", "whiteSpace": "nowrap"}),
        ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "alignItems": "flex-start",
                  "background": BG_CARD, "borderBottom": f"1px solid {BORDER}", "padding": "14px 28px",
                  "position": "sticky", "top": "52px", "zIndex": "100"}),

        html.Div(id="j26-cand-kpis", style={"display": "flex", "gap": "12px", "flexWrap": "wrap",
                                             "padding": "20px 28px 0"}),

        html.Div([
            html.Div([
                html.Div("Where Candidates Are Contesting", style={"color": TEXT_MUTED, "fontSize": "11px",
                    "textTransform": "uppercase", "letterSpacing": "0.07em", "padding": "14px 16px 8px"}),
                dcc.Graph(id="j26-cand-map", config={"displayModeBar": True,
                          "modeBarButtonsToRemove": ["lasso2d", "select2d"], "displaylogo": False},
                          style={"height": "480px"}),
            ], style=card_style()),
        ], style={"padding": "16px 28px 0"}),

        html.Div([
            html.Div([dcc.Graph(id="j26-cand-gender", config={"displayModeBar": False}, style={"height": "340px"})],
                     style={"flex": "1", "minWidth": "300px", **card_style()}),
            html.Div([dcc.Graph(id="j26-cand-age", config={"displayModeBar": False}, style={"height": "340px"})],
                     style={"flex": "1", "minWidth": "300px", **card_style()}),
        ], style={"display": "flex", "gap": "16px", "padding": "16px 28px", "flexWrap": "wrap"}),

        html.Div([
            html.Div([dcc.Graph(id="j26-cand-party-bar", config={"displayModeBar": False})],
                     style=card_style()),
        ], style={"padding": "0 28px 16px"}),

        html.Div([
            html.Div([
                html.Div("Candidate List", style={"color": TEXT_MUTED, "fontSize": "11px",
                    "textTransform": "uppercase", "letterSpacing": "0.07em", "padding": "14px 16px 8px"}),
                html.Div(id="j26-cand-table"),
            ], style=card_style()),
        ], style={"padding": "0 28px 28px"}),

    ], style={"background": BG_DARK, "minHeight": "100vh", "color": TEXT_PRIMARY, "fontFamily": "Inter, sans-serif"})


@callback(
    Output("j26-cand-seat", "value"), Output("j26-cand-party", "value"),
    Input("j26-cand-reset", "n_clicks"), prevent_initial_call=True,
)
def reset_filters(_):
    return None, None


@callback(
    Output("j26-cand-kpis", "children"),
    Output("j26-cand-map", "figure"),
    Output("j26-cand-gender", "figure"),
    Output("j26-cand-age", "figure"),
    Output("j26-cand-party-bar", "figure"),
    Output("j26-cand-table", "children"),
    Input("j26-cand-seat", "value"),
    Input("j26-cand-party", "value"),
)
def update(seats, parties):
    df_all = load_2026_candidates()
    df = _filter(df_all, seats, parties)
    demo = load_johor_demographics()
    seats_in_scope = set(df["UNIQUE CODE"].unique())

    n = len(df)
    n_seats = df["UNIQUE CODE"].nunique()
    n_parties = df["PARTY"].nunique()
    female_pct = (df["SEX"] == "FEMALE").sum() / n * 100 if n else 0
    seat_counts = df_all[df_all["UNIQUE CODE"].isin(seats_in_scope)].groupby("UNIQUE CODE").size() \
                  if seats else df_all.groupby("UNIQUE CODE").size()
    crowded_code = seat_counts.idxmax() if len(seat_counts) else None
    crowded_label = df_all[df_all["UNIQUE CODE"] == crowded_code]["SEAT_LABEL"].iloc[0] if crowded_code else "—"
    crowded_n = int(seat_counts.max()) if len(seat_counts) else 0

    kpis = [
        _kpi("Candidates", str(n), f"across {n_seats} seat(s)"),
        _kpi("Parties Fielding Candidates", str(n_parties), "individually tracked", color="#26C6DA"),
        _kpi("Female Candidates", f"{female_pct:.1f}%", "of selection", color="#E91E63"),
        _kpi("Most Crowded Seat", crowded_label.title() if crowded_label else "—",
             f"{crowded_n} candidates", color="#FF7043"),
    ]

    fig_map = make_map(df_all, df)
    fig_gender = make_gender_chart(df, demo, seats_in_scope)
    fig_age = make_age_chart(df, demo, seats_in_scope)
    fig_party = make_party_bar(df)

    tbl_df = df[["SEAT_NUM", "SEAT_LABEL", "PARLIAMENTARY NAME", "PARTY", "BLOC", "CANDIDATE", "SEX", "AGE"]].copy()
    tbl_df["DUN Code"] = tbl_df["SEAT_NUM"].apply(seat_code_label)
    tbl_df["Party"] = [coalition_label(p, b) for p, b in zip(tbl_df["PARTY"], tbl_df["BLOC"])]
    tbl_df["SEAT_LABEL"] = tbl_df["SEAT_LABEL"].str.title()
    tbl_df["PARLIAMENTARY NAME"] = tbl_df["PARLIAMENTARY NAME"].astype(str).str.title()
    tbl_df["AGE"] = tbl_df["AGE"].apply(lambda x: "—" if pd.isna(x) else int(x))
    tbl_df = tbl_df.rename(columns={"SEAT_LABEL": "DUN Name", "PARLIAMENTARY NAME": "Parliament Area",
                                     "CANDIDATE": "Candidate Name", "SEX": "Sex", "AGE": "Age"})
    tbl_df = tbl_df[["DUN Code", "DUN Name", "Parliament Area", "Party", "Candidate Name", "Sex", "Age"]]
    tbl_df = tbl_df.sort_values(["DUN Code", "Party"])

    table = dash_table.DataTable(
        data=tbl_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in tbl_df.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG_CARD2, "color": TEXT_MUTED, "fontWeight": "600",
                      "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.06em",
                      "border": f"1px solid {BORDER}", "padding": "10px 12px"},
        style_cell={"backgroundColor": BG_CARD, "color": TEXT_PRIMARY, "border": f"1px solid {BORDER}",
                    "padding": "9px 12px", "fontSize": "13px", "fontFamily": "Inter, sans-serif",
                    "textAlign": "left", "minWidth": "90px"},
        sort_action="native", page_size=20,
    )

    return kpis, fig_map, fig_gender, fig_age, fig_party, table
