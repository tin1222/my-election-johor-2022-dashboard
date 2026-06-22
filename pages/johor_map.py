"""
pages/johor_map.py — Johor 2022 Map
GeoJSON: JOHOR_2022_DUN_BOUNDARIES.geojson — 56 DUN constituency boundaries.
Choropleth coloured by coalition / turnout / majority %, matched on UNIQUE_ID/UNIQUE CODE.
"""

from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json, os
from collections import defaultdict

from utils.johor_data import load_johor_results, load_johor_demographics, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT, map_bounds_zoom

GEOJSON_PATH = "data/JOHOR_2022_DUN_BOUNDARIES.geojson"

JOHOR_CENTER = (1.8, 103.3, 8.2)

_GEO_CACHE   = {}
_URBAN_CACHE = {}

URBAN_OPTIONS = ["URBAN", "SEMI URBAN", "RURAL"]

def coal_color(n): return JOHOR_COALITION_COLORS.get(str(n).upper(), "#9E9E9E")
def card_style():  return {"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"12px","padding":"4px"}

def _kpi(label, value, sub=None, color=ACCENT):
    return html.Div([
        html.Div(label, style={"color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
                               "letterSpacing":"0.08em","marginBottom":"4px"}),
        html.Div(value, style={"color":color,"fontSize":"22px","fontWeight":"700",
                               "lineHeight":"1.1","letterSpacing":"-0.02em"}),
        html.Div(sub or "", style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"2px"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px",
              "padding":"12px 16px","flex":"1","minWidth":"110px"})

def load_geo():
    if "geo" in _GEO_CACHE:
        return _GEO_CACHE["geo"]
    if not os.path.exists(GEOJSON_PATH):
        return None
    with open(GEOJSON_PATH) as f:
        geo = json.load(f)
    for feat in geo["features"]:
        feat["id"] = feat["properties"]["UNIQUE_ID"]
    _GEO_CACHE["geo"] = geo
    return geo


def load_with_urban():
    if "df" in _URBAN_CACHE:
        return _URBAN_CACHE["df"]
    df    = load_johor_results().copy()
    demo  = load_johor_demographics()
    urban = demo[["UNIQUE CODE", "URBAN-RURAL CLASSIFICATION (2022)"]].rename(
        columns={"URBAN-RURAL CLASSIFICATION (2022)": "URBAN_CLASS"})
    df = df.merge(urban, on="UNIQUE CODE", how="left")
    df["URBAN_CLASS"] = df["URBAN_CLASS"].fillna("UNKNOWN").str.strip().str.upper()
    _URBAN_CACHE["df"] = df
    return df


def get_results(par_filter=None, coalition_filter=None, urban_filter=None):
    df = load_with_urban()
    if par_filter:
        df = df[df["PARLIAMENTARY NAME"].isin(par_filter)]
    if coalition_filter:
        df = df[df["COALITION"].isin(coalition_filter)]
    if urban_filter:
        df = df[df["URBAN_CLASS"] == urban_filter]
    return df


def make_map(color_mode="coalition", urban_filter=None,
             par_filter=None, coalition_filter=None):
    geo = load_geo()
    df  = get_results(par_filter, coalition_filter, urban_filter)

    if geo is None:
        fig = go.Figure()
        fig.add_annotation(
            text="GeoJSON not found — add JOHOR_2022_DUN_BOUNDARIES.geojson to data/",
            x=0.5, y=0.5, xref="paper", yref="paper",
            font=dict(size=14, color=TEXT_MUTED), showarrow=False,
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Inter", color=TEXT_PRIMARY))
        return fig

    code_to_row   = {row["UNIQUE CODE"]: row for _, row in df.iterrows()}
    visible_codes = set(code_to_row.keys())

    fig = go.Figure()

    if color_mode == "coalition":
        coal_groups = defaultdict(list)
        for feat in geo["features"]:
            code = feat["properties"]["UNIQUE_ID"]
            if code not in visible_codes:
                continue
            coal_groups[code_to_row[code]["COALITION"]].append((feat, code_to_row[code]))

        for coal, items in sorted(coal_groups.items(), key=lambda x: -len(x[1])):
            sub_feats = [item[0] for item in items]
            sub_geo   = {"type": "FeatureCollection", "features": sub_feats}
            hover_texts = [
                f"<b>{row['STATE CONSTITUENCY NAME'].title()}</b><br>"
                f"({row['PARLIAMENTARY NAME'].title()})<br>"
                f"Coalition: <b style='color:{coal_color(coal)}'>{coal}</b><br>"
                f"Winner: {row['WINNING PARTY']}<br>"
                f"Majority: {int(row['WINNING MAJORITY']):,}<br>"
                f"Turnout: {row['TURNOUT (%)']:.1f}%<br>"
                f"Class: {row['URBAN_CLASS'].title()}"
                for feat, row in items
            ]

            fig.add_trace(go.Choroplethmap(
                geojson=sub_geo,
                locations=[f["id"] for f in sub_feats],
                z=[1] * len(sub_feats),
                colorscale=[[0, coal_color(coal)], [1, coal_color(coal)]],
                showscale=False,
                name=f"{coal} ({len(sub_feats)})",
                hovertext=hover_texts,
                hoverinfo="text",
                marker=dict(opacity=0.9, line=dict(color="#1a1a2e", width=0.6)),
                showlegend=True,
            ))

    else:
        is_turnout = (color_mode == "turnout")
        colorscale = "Blues" if is_turnout else "RdYlGn"
        col_label  = "Turnout (%)" if is_turnout else "Majority %"

        def _val(row):
            return float(row["TURNOUT (%)"]) if is_turnout else float(row["MAJORITY_PCT"])

        sub_feats = [f for f in geo["features"] if f["properties"]["UNIQUE_ID"] in visible_codes]
        sub_geo   = {"type": "FeatureCollection", "features": sub_feats}

        loc_z, hover_map = {}, {}
        for feat in sub_feats:
            row = code_to_row[feat["properties"]["UNIQUE_ID"]]
            val = _val(row)
            loc_z[feat["id"]]    = val
            hover_map[feat["id"]] = (
                f"<b>{row['STATE CONSTITUENCY NAME'].title()}</b><br>"
                f"({row['PARLIAMENTARY NAME'].title()})<br>"
                f"{col_label}: {val:.1f}%<br>"
                f"Coalition: {row['COALITION']}<br>"
                f"Majority: {int(row['WINNING MAJORITY']):,}<br>"
                f"Class: {row['URBAN_CLASS'].title()}"
            )

        fig.add_trace(go.Choroplethmap(
            geojson=sub_geo,
            locations=list(loc_z.keys()),
            z=list(loc_z.values()),
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(text=col_label, font=dict(color=TEXT_MUTED, size=11)),
                tickfont=dict(color=TEXT_MUTED, size=10),
                thickness=12, len=0.6,
            ),
            hovertext=list(hover_map.values()),
            hoverinfo="text",
            marker=dict(opacity=0.85, line=dict(color="#1a1a2e", width=0.4)),
            name=col_label,
        ))

    # Auto-zoom: frame the filtered selection, else all of Johor
    if par_filter or coalition_filter or urban_filter:
        shown_feats = [f for f in geo["features"] if f["properties"]["UNIQUE_ID"] in visible_codes]
        lat_c, lon_c, zoom = map_bounds_zoom(shown_feats) if shown_feats else JOHOR_CENTER
    else:
        lat_c, lon_c, zoom = JOHOR_CENTER

    fig.update_layout(
        map=dict(style="dark", center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        legend=dict(bgcolor=BG_CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=TEXT_MUTED,size=11),
                    title=dict(text="Coalition",font=dict(color=TEXT_PRIMARY,size=12)),
                    x=0.01, y=0.99, xanchor="left", yanchor="top"),
        margin=dict(l=0,r=0,t=0,b=0),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER,
                        font=dict(family="Inter",color=TEXT_PRIMARY,size=12)),
    )
    return fig

def layout():
    df    = load_with_urban()
    coals = sorted([c for c in df["COALITION"].unique() if c not in ("OTHERS","INDEPENDENT")])
    coals += ["OTHERS","INDEPENDENT"]
    par_opts = [{"label":p.title(),"value":p}
                for p in sorted(df["PARLIAMENTARY NAME"].unique())]

    # Summary KPIs
    avg_turnout = df["TURNOUT (%)"].mean()
    total_elec  = int(df["TOTAL ELECTORATE"].sum())
    top_coal    = df.groupby("COALITION").size().idxmax()
    top_n       = df.groupby("COALITION").size().max()
    closest     = df.nsmallest(1, "WINNING MAJORITY").iloc[0]

    return html.Div([
        html.Div([
            html.Div([
                html.Span("MAP", style={"background":"#4CAF50","color":"white","borderRadius":"4px",
                          "padding":"2px 8px","fontSize":"10px","fontWeight":"800",
                          "letterSpacing":"0.07em","marginRight":"10px"}),
                html.Span("Johor 2022 DUN constituencies", style={"color":TEXT_MUTED,"fontSize":"13px"}),
            ], style={"marginBottom":"6px"}),
            html.H2("Johor State Election Map", style={"color":TEXT_PRIMARY,
                "fontSize":"clamp(18px,3vw,26px)","fontWeight":"700",
                "margin":"0 0 8px 0","letterSpacing":"-0.02em"}),
            html.Div([
                html.Span("56 DUN seats · GeoJSON: ", style={"color":TEXT_MUTED,"fontSize":"12px"}),
                html.Span("JOHOR_2022_DUN_BOUNDARIES",
                          style={"color":ACCENT,"fontSize":"12px"}),
            ]),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        # Controls bar
        html.Div([
            html.Div([
                html.Div("Colour by", style={"color":TEXT_MUTED,"fontSize":"10px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","marginBottom":"5px"}),
                dcc.RadioItems(
                    id="jhr-map-color-mode",
                    options=[
                        {"label":"Coalition",  "value":"coalition"},
                        {"label":"Turnout",     "value":"turnout"},
                        {"label":"Majority %",  "value":"majority_pct"},
                    ],
                    value="coalition", inline=True,
                    inputStyle={"marginRight":"4px","cursor":"pointer"},
                    labelStyle={"marginRight":"18px","fontSize":"13px",
                                "color":TEXT_PRIMARY,"cursor":"pointer"},
                ),
            ]),
            html.Div([
                html.Div("Filter Parliament Area", style={"color":TEXT_MUTED,"fontSize":"10px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","marginBottom":"5px"}),
                dcc.Dropdown(id="jhr-map-par-filter", options=par_opts, multi=True,
                             placeholder="All parliament areas", className="dash-dropdown-dark",
                             style={"minWidth":"220px"}),
            ]),
            html.Div([
                html.Div("Filter Coalition", style={"color":TEXT_MUTED,"fontSize":"10px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","marginBottom":"5px"}),
                dcc.Dropdown(id="jhr-map-coal",
                    options=[{"label":c,"value":c} for c in coals],
                    multi=True, placeholder="All coalitions", className="dash-dropdown-dark",
                    style={"minWidth":"200px"}),
            ]),
            html.Div([
                html.Div("Urban / Semi Urban / Rural", style={"color":TEXT_MUTED,"fontSize":"10px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","marginBottom":"5px"}),
                dcc.Dropdown(id="jhr-map-urban-filter",
                    options=[{"label":u.title(),"value":u} for u in URBAN_OPTIONS],
                    value="", clearable=True, placeholder="None",
                    className="dash-dropdown-dark", style={"minWidth":"200px"}),
            ]),
        ], style={
            "background":BG_CARD,"borderBottom":f"1px solid {BORDER}",
            "padding":"12px 28px","display":"flex","gap":"24px",
            "alignItems":"flex-start","flexWrap":"wrap",
            "position":"sticky","top":"52px","zIndex":"100",
        }),

        # KPI strip
        html.Div(id="jhr-map-kpi-strip", children=[
            _kpi("Seats Shown", "56", "in selection"),
            _kpi("Leading Coalition", top_coal, f"{top_n} seats", color=coal_color(top_coal)),
            _kpi("Avg Turnout", f"{avg_turnout:.1f}%", "in selection", color="#4CAF50"),
            _kpi("Total Electorate", f"{total_elec:,}", "registered voters"),
            _kpi("Closest Seat", closest["STATE CONSTITUENCY NAME"].title(),
                 f"Majority: {int(closest['WINNING MAJORITY']):,}",
                 color=coal_color(closest["COALITION"])),
        ], style={"display":"flex","gap":"10px","flexWrap":"wrap","padding":"16px 28px 0"}),

        # Map
        html.Div([
            html.Div([
                dcc.Graph(id="jhr-map-fig",
                          config={"displayModeBar":True,
                                  "modeBarButtonsToRemove":["lasso2d","select2d"],
                                  "displaylogo":False},
                          style={"height":"560px"}),
            ], style=card_style()),
        ], style={"padding":"16px 28px 28px"}),
    ], style={"background":BG_DARK,"minHeight":"100vh",
              "color":TEXT_PRIMARY,"fontFamily":"Inter, sans-serif"})

@callback(
    Output("jhr-map-fig","figure"),
    Output("jhr-map-kpi-strip","children"),
    Input("jhr-map-color-mode","value"),
    Input("jhr-map-par-filter","value"),
    Input("jhr-map-coal","value"),
    Input("jhr-map-urban-filter","value"),
)
def update_map(color_mode, par_filter, coal_filter, urban_filter):
    par    = par_filter if par_filter else None
    coal   = coal_filter if coal_filter else None
    urban  = urban_filter if urban_filter else None

    df = get_results(par, coal, urban)

    n          = len(df)
    avg_to     = df["TURNOUT (%)"].mean()
    total_elec = int(df["TOTAL ELECTORATE"].sum())
    seats_by_c = df.groupby("COALITION").size()
    top_coal   = seats_by_c.idxmax() if len(seats_by_c) else "—"
    top_n      = seats_by_c.max()    if len(seats_by_c) else 0
    closest    = df.nsmallest(1, "WINNING MAJORITY").iloc[0] if len(df) else None

    kpis = [
        _kpi("Seats Shown", str(n), "in selection"),
        _kpi("Leading Coalition", top_coal, f"{top_n} seats", color=coal_color(top_coal)),
        _kpi("Avg Turnout", f"{avg_to:.1f}%", "in selection", color="#4CAF50"),
        _kpi("Total Electorate", f"{total_elec:,}", "registered voters"),
    ]
    if closest is not None:
        kpis.append(_kpi(
            "Closest Seat",
            closest["STATE CONSTITUENCY NAME"].title(),
            f"Majority: {int(closest['WINNING MAJORITY']):,}",
            color=coal_color(closest["COALITION"]),
        ))

    fig_map = make_map(
        color_mode=color_mode or "coalition",
        urban_filter=urban,
        par_filter=par,
        coalition_filter=coal,
    )

    return fig_map, kpis
