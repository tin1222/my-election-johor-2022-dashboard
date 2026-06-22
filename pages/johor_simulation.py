"""
pages/johor_simulation.py — Johor 2022 State Election Scenario Simulator
Same arithmetic swing model as Malaysia simulation, adapted for 56 DUN seats.
GeoJSON: JOHOR_2022_DUN_BOUNDARIES.geojson, matched on UNIQUE_ID/UNIQUE CODE.
"""

from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json, os
from collections import defaultdict

from utils.johor_data import load_johor_results, load_johor_demographics, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT, map_bounds_zoom

JOHOR_CENTER = (1.8, 103.3, 8.2)

def coal_color(n): return JOHOR_COALITION_COLORS.get(str(n).upper(), "#9E9E9E")
def card_style():  return {"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"12px","padding":"4px"}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(color=TEXT_MUTED,size=11)),
)

MAIN_COALITIONS  = ["BN", "PH", "PN", "PEJUANG"]
SWING_COALITIONS = ["BN", "PH", "PN"]
MAJORITY_SEATS   = 29   # simple majority in 56-seat assembly

GEOJSON_PATH = "data/JOHOR_2022_DUN_BOUNDARIES.geojson"
_GEO_CACHE = {}

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


def make_simulation_map(sim_df, seats=None):
    geo = load_geo()
    if geo is None:
        fig = go.Figure()
        fig.add_annotation(
            text="GeoJSON not found — add JOHOR_2022_DUN_BOUNDARIES.geojson to data/",
            x=0.5, y=0.5, xref="paper", yref="paper",
            font=dict(size=13, color=TEXT_MUTED), showarrow=False,
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Inter", color=TEXT_PRIMARY))
        return fig

    code_to_row = {row["UNIQUE CODE"]: row for _, row in sim_df.iterrows()}

    coal_groups = defaultdict(list)
    for feat in geo["features"]:
        code   = feat["properties"]["UNIQUE_ID"]
        row    = code_to_row.get(code)
        winner = row["SIM_WINNER"] if row is not None else "OTHERS"
        coal_groups[winner].append((feat, row))

    fig = go.Figure()
    for coal, items in sorted(coal_groups.items(), key=lambda x: -len(x[1])):
        sub_feats = [item[0] for item in items]
        sub_geo   = {"type": "FeatureCollection", "features": sub_feats}

        hover_texts = []
        for feat, row in items:
            if row is not None:
                flipped = row["SEAT_FLIPPED"]
                hover_texts.append(
                    f"<b>{row['STATE CONSTITUENCY NAME'].title()}</b><br>"
                    f"Johor 2022: {row['COALITION']}<br>"
                    f"Simulated: <b>{row['SIM_WINNER']}</b>"
                    + (" ⚡ FLIPPED" if flipped else "")
                )
            else:
                hover_texts.append(f"<b>{feat['properties']['NAMADUN'].title()}</b>")

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

    # Auto-zoom: frame the selected DUN seats, else all of Johor
    if seats:
        seat_set   = {s.upper() for s in seats}
        zoom_feats = [f for f in geo["features"] if f["properties"]["NAMADUN"].upper() in seat_set]
        lat_c, lon_c, zoom = map_bounds_zoom(zoom_feats) if zoom_feats else JOHOR_CENTER
    else:
        lat_c, lon_c, zoom = JOHOR_CENTER

    fig.update_layout(
        map=dict(style="dark", center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        legend=dict(
            bgcolor=BG_CARD, bordercolor=BORDER, borderwidth=1,
            font=dict(color=TEXT_MUTED, size=11),
            title=dict(text="Simulated Winner", font=dict(color=TEXT_PRIMARY, size=12)),
            x=0.01, y=0.99, xanchor="left", yanchor="top",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER,
                        font=dict(family="Inter", color=TEXT_PRIMARY, size=12)),
    )
    return fig

# ── Simulation engine ─────────────────────────────────────────────────────────

def simulate_johor(turnout_delta=0.0, swing_to="PH", swing_pct=0.0,
                   swing_from="BN", youth_boost=0.0,
                   eth_col=None, eth_boost=0.0,
                   constituencies=None,
                   swing2_from="PH", swing2_to="PN", swing2_pct=0.0):
    df = load_johor_results().copy()
    vote_col = {c: f"{c} VOTE" for c in MAIN_COALITIONS}
    aux_vote_col = {}
    for aux in ["OTHERS"]:
        col = f"{aux} VOTE"
        if col in df.columns:
            aux_vote_col[aux] = col

    # Step 1: Turnout scale
    df["SIM_TURNOUT"] = (df["TURNOUT (%)"] + turnout_delta).clip(30, 95)
    t_scale = (df["SIM_TURNOUT"] / df["TURNOUT (%)"].replace(0, np.nan)).fillna(1.0)
    for col in vote_col.values():
        if col in df.columns:
            df[col] = (df[col] * t_scale).round(0)

    # Step 2: Demographics
    try:
        demo = load_johor_demographics()
        merge_cols = ["UNIQUE CODE", "YOUTH_PCT"] + ([eth_col] if eth_col else [])
        df = df.merge(demo[merge_cols], on="UNIQUE CODE", how="left")
    except Exception:
        df["YOUTH_PCT"] = 0
    df["YOUTH_PCT"] = df.get("YOUTH_PCT", pd.Series(0, index=df.index)).fillna(0)

    # Step 3: Youth boost
    if youth_boost != 0:
        y_scale = 1 + (df["YOUTH_PCT"] / 100) * (youth_boost / 100)
        for col in [vote_col.get("PH",""), vote_col.get("BN",""), vote_col.get("PN","")]:
            if col and col in df.columns:
                df[col] = (df[col] * y_scale).round(0)

    # Step 4: Ethnicity boost
    if eth_boost != 0 and eth_col and eth_col in df.columns:
        e_scale = 1 + (df[eth_col].fillna(0) / 100) * (eth_boost / 100)
        for col in vote_col.values():
            if col in df.columns:
                df[col] = (df[col] * e_scale).round(0)

    # Step 5: Swing 1
    if swing_pct != 0 and swing_to != swing_from:
        to_col   = vote_col.get(swing_to)
        from_col = vote_col.get(swing_from)
        if to_col and from_col and to_col in df.columns and from_col in df.columns:
            shift = (df["TOTAL VALID VOTES"] * (swing_pct / 100)).round(0)
            shift = shift.clip(upper=df[from_col])
            df[from_col] = (df[from_col] - shift).clip(lower=0)
            df[to_col]   = df[to_col] + shift

    # Step 5b: Swing 2
    if swing2_pct != 0 and swing2_to != swing2_from:
        to_col2   = vote_col.get(swing2_to)
        from_col2 = vote_col.get(swing2_from)
        if to_col2 and from_col2 and to_col2 in df.columns and from_col2 in df.columns:
            shift2 = (df["TOTAL VALID VOTES"] * (swing2_pct / 100)).round(0)
            shift2 = shift2.clip(upper=df[from_col2])
            df[from_col2] = (df[from_col2] - shift2).clip(lower=0)
            df[to_col2]   = df[to_col2] + shift2

    # Step 6: Determine winner
    def _winner(row):
        votes = {c: row[col] for c, col in vote_col.items()
                 if col in row.index and pd.notna(row[col]) and row[col] > 0}
        for aux, col in aux_vote_col.items():
            if col in row.index and pd.notna(row[col]) and row[col] > 0:
                votes[aux] = row[col]
        if not votes:
            return row["COALITION"], 0, 0.0
        winner    = max(votes, key=votes.get)
        orig_coal = row["COALITION"]
        # OTHERS vote aggregates minor parties (MUDA, PBM etc.) —
        # preserve the actual coalition winner at baseline
        if winner in ("OTHERS",):
            if orig_coal not in ("OTHERS", "INDEPENDENT"):
                if votes.get(orig_coal, 0) > 0:
                    winner = orig_coal
                else:
                    winner = orig_coal  # trust the original result
        w_votes  = votes.get(winner, votes[max(votes, key=votes.get)])
        sorted_v = sorted(votes.values(), reverse=True)
        margin   = int(w_votes - sorted_v[1]) if len(sorted_v) > 1 else int(w_votes)
        total    = sum(votes.values())
        return winner, margin, round(margin/total*100, 2) if total > 0 else 0.0

    # Step 7: Apply constituency filter
    if constituencies:
        mask    = df["STATE CONSTITUENCY NAME"].isin(constituencies)
        df_sim  = df[mask].copy()
        df_rest = df[~mask].copy()
        res = df_sim.apply(_winner, axis=1, result_type="expand")
        df_sim["SIM_WINNER"]       = res[0]
        df_sim["SIM_MAJORITY"]     = res[1]
        df_sim["SIM_MAJORITY_PCT"] = res[2]
        df_sim["SEAT_FLIPPED"]     = df_sim["SIM_WINNER"] != df_sim["COALITION"]
        df_rest["SIM_WINNER"]       = df_rest["COALITION"]
        df_rest["SIM_MAJORITY"]     = df_rest["WINNING MAJORITY"]
        df_rest["SIM_MAJORITY_PCT"] = df_rest["MAJORITY_PCT"]
        df_rest["SEAT_FLIPPED"]     = False
        df = pd.concat([df_sim, df_rest], ignore_index=True)
    else:
        res = df.apply(_winner, axis=1, result_type="expand")
        df["SIM_WINNER"]       = res[0]
        df["SIM_MAJORITY"]     = res[1]
        df["SIM_MAJORITY_PCT"] = res[2]
        df["SEAT_FLIPPED"]     = df["SIM_WINNER"] != df["COALITION"]

    return df


# ── Helpers ───────────────────────────────────────────────────────────────────

def _majority_label(sim_seats):
    for coal, count in sorted(sim_seats.items(), key=lambda x: -x[1]):
        if count >= MAJORITY_SEATS:
            return f"✓ {coal} majority"
    return "✗ Hung assembly"

def _majority_color(sim_seats):
    for coal, count in sorted(sim_seats.items(), key=lambda x: -x[1]):
        if count >= MAJORITY_SEATS:
            return coal_color(coal)
    return "#E53935"

def _label_style():
    return {"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
            "letterSpacing":"0.07em","marginBottom":"8px","display":"block"}

def _kpi(label, value, sub=None, color=ACCENT):
    return html.Div([
        html.Div(label, style={"color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
                               "letterSpacing":"0.08em","marginBottom":"5px"}),
        html.Div(value, style={"color":color,"fontSize":"24px","fontWeight":"700",
                               "lineHeight":"1.1","letterSpacing":"-0.02em"}),
        html.Div(sub or "", style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"3px"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px",
              "padding":"14px 16px","flex":"1","minWidth":"120px"})


# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    df        = load_johor_results()
    coal_opts = [{"label":c,"value":c} for c in SWING_COALITIONS]
    seat_opts = [{"label":s.title(),"value":s}
                 for s in sorted(df["STATE CONSTITUENCY NAME"].unique())]
    par_opts  = [{"label":p.title(),"value":p}
                 for p in sorted(df["PARLIAMENTARY NAME"].unique())]

    ROW_STYLE   = {"display":"flex","gap":"20px","flexWrap":"wrap","alignItems":"flex-start"}
    PANEL_STYLE = {"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"16px 28px"}

    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("SIMULATION", style={"background":"#FF7043","color":"white","borderRadius":"4px",
                          "padding":"2px 8px","fontSize":"10px","fontWeight":"800",
                          "letterSpacing":"0.07em","marginRight":"10px"}),
                html.Span("What-if scenario builder",
                          style={"color":TEXT_MUTED,"fontSize":"13px"}),
            ], style={"marginBottom":"6px"}),
            html.H2("Johor State Election Scenario Simulator", style={"color":TEXT_PRIMARY,
                "fontSize":"clamp(18px,3vw,26px)","fontWeight":"700",
                "margin":"0 0 10px 0","letterSpacing":"-0.02em"}),
            html.Div([
                html.Span("Methodology: ", style={"color":TEXT_PRIMARY,"fontWeight":"600","fontSize":"12px"}),
                html.Span(
                    "Deterministic swing model on Johor 2022 DUN vote counts. "
                    "Turnout scales all votes proportionally; swing transfers a fixed % of valid votes "
                    "between coalitions; demographic boosts scale votes in seats where the selected group "
                    "is largest. Winners recalculated by simple plurality per seat. "
                    "No ML or probabilistic modelling.",
                    style={"color":TEXT_MUTED,"fontSize":"12px"},
                ),
            ], style={"background":BG_CARD2,"border":f"1px solid {BORDER}","borderRadius":"8px",
                      "padding":"10px 14px","borderLeft":"3px solid #FF7043","marginBottom":"8px"}),
            html.Div([
                html.Span("⚠ Disclaimer: ", style={"color":"#F9A825","fontWeight":"700","fontSize":"12px"}),
                html.Span(
                    "This simulator applies hypothetical swings to the Johor 2022 state election results "
                    "to explore what a future contest might look like "
                    "under the same coalitions. It does not account for new parties, splits, mergers, or "
                    "coalition realignments formed after the 2022 Johor election, and is not a forecast.",
                    style={"color":TEXT_MUTED,"fontSize":"12px"},
                ),
            ], style={"background":BG_CARD2,"border":"1px solid #F9A825","borderRadius":"8px",
                      "padding":"10px 14px","borderLeft":"3px solid #F9A825"}),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        # Row 1: Dropdowns (sticky)
        html.Div([
            # Vote swings
            html.Div([
                html.Label("Vote Swing", style=_label_style()),
                html.Div([
                    html.Div([
                        html.Div("FROM",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Dropdown(id="jhr-sim-swing-from",options=coal_opts,value="BN",
                                     clearable=False,className="dash-dropdown-dark",style={"minWidth":"80px"}),
                    ]),
                    html.Div("→",style={"color":TEXT_MUTED,"fontSize":"16px","alignSelf":"flex-end","paddingBottom":"6px"}),
                    html.Div([
                        html.Div("TO",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Dropdown(id="jhr-sim-swing-to",options=coal_opts,value="PH",
                                     clearable=False,className="dash-dropdown-dark",style={"minWidth":"80px"}),
                    ]),
                    html.Div([
                        html.Div("% of votes",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Input(id="jhr-sim-swing-pct",type="number",value=0,min=0,max=50,step=0.5,
                                  style={"background":BG_CARD2,"border":f"1px solid {BORDER}",
                                         "color":TEXT_PRIMARY,"borderRadius":"6px","padding":"6px 8px",
                                         "width":"72px","fontFamily":"Inter","fontSize":"13px"}),
                    ]),
                ], style={"display":"flex","gap":"8px","alignItems":"flex-end","marginBottom":"8px"}),
                html.Div([
                    html.Div([
                        html.Div("FROM",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Dropdown(id="jhr-sim-swing2-from",options=coal_opts,value="PN",
                                     clearable=False,className="dash-dropdown-dark",style={"minWidth":"80px"}),
                    ]),
                    html.Div("→",style={"color":TEXT_MUTED,"fontSize":"16px","alignSelf":"flex-end","paddingBottom":"6px"}),
                    html.Div([
                        html.Div("TO",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Dropdown(id="jhr-sim-swing2-to",options=coal_opts,value="BN",
                                     clearable=False,className="dash-dropdown-dark",style={"minWidth":"80px"}),
                    ]),
                    html.Div([
                        html.Div("% of votes",style={"color":TEXT_MUTED,"fontSize":"10px","marginBottom":"4px"}),
                        dcc.Input(id="jhr-sim-swing2-pct",type="number",value=0,min=0,max=50,step=0.5,
                                  style={"background":BG_CARD2,"border":f"1px solid {BORDER}",
                                         "color":TEXT_PRIMARY,"borderRadius":"6px","padding":"6px 8px",
                                         "width":"72px","fontFamily":"Inter","fontSize":"13px"}),
                    ]),
                ], style={"display":"flex","gap":"8px","alignItems":"flex-end"}),
            ], style={"flex":"2","minWidth":"260px"}),

            # Filters
            html.Div([
                html.Label("Limit to Constituencies", style=_label_style()),
                dcc.Dropdown(id="jhr-sim-seat-filter",options=seat_opts,multi=True,
                             placeholder="All 56 DUN seats",className="dash-dropdown-dark"),
                html.Div("Unselected seats keep actual result",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px","marginBottom":"10px"}),
                html.Label("Limit to Parliament Area", style=_label_style()),
                dcc.Dropdown(id="jhr-sim-par-filter",options=par_opts,multi=True,
                             placeholder="All parliament areas",className="dash-dropdown-dark"),
                html.Div("Narrows simulation to DUN seats within selected parliament areas",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px"}),
            ], style={"flex":"3","minWidth":"260px"}),

            # Ethnicity group
            html.Div([
                html.Label("Ethnicity Group", style=_label_style()),
                dcc.Dropdown(id="jhr-sim-eth-group",
                    options=[
                        {"label":"Malay",        "value":"MALAY (%)"},
                        {"label":"Chinese",       "value":"CHINESE (%)"},
                        {"label":"Indian",        "value":"INDIANS (%)"},
                        {"label":"Orang Asli",    "value":"ORANG ASLI (%)"},
                    ],
                    value="MALAY (%)", clearable=False, className="dash-dropdown-dark",
                ),
                html.Div("For ethnicity turnout boost below",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px"}),
            ], style={"flex":"1","minWidth":"160px"}),

            # Reset
            html.Div([
                html.Button("↺ Reset", id="jhr-sim-reset", n_clicks=0, style={
                    "background":"transparent","color":TEXT_MUTED,
                    "border":f"1px solid {BORDER}","borderRadius":"8px",
                    "padding":"8px 14px","cursor":"pointer","fontSize":"12px",
                    "fontFamily":"Inter","whiteSpace":"nowrap"}),
            ], style={"alignSelf":"flex-end"}),
        ], style={**PANEL_STYLE, **ROW_STYLE,
                  "position":"sticky","top":"52px","zIndex":"101"}),

        # Row 2: Sliders
        html.Div([
            html.Div([
                html.Label("Overall Turnout Change", style=_label_style()),
                dcc.Slider(id="jhr-sim-turnout",min=-50,max=50,step=0.5,value=0,
                           marks={-50:"-50pp",-25:"-25pp",0:"0",25:"+25pp",50:"+50pp"},
                           tooltip={"placement":"bottom","always_visible":True}),
                html.Div("Scales all votes proportionally (pp vs Johor 2022)",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px"}),
            ], style={"flex":"1","minWidth":"200px"}),
            html.Div([
                html.Label("Youth Turnout Boost (18–29)", style=_label_style()),
                dcc.Slider(id="jhr-sim-youth",min=-50,max=50,step=1,value=0,
                           marks={-50:"-50%",-25:"-25%",0:"0",25:"+25%",50:"+50%"},
                           tooltip={"placement":"bottom","always_visible":True}),
                html.Div("Extra scale for seats with high Under-30 voter share",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px"}),
            ], style={"flex":"1","minWidth":"200px"}),
            html.Div([
                html.Label("Ethnicity Turnout Boost", style=_label_style()),
                dcc.Slider(id="jhr-sim-eth-boost",min=-50,max=50,step=1,value=0,
                           marks={-50:"-50%",-25:"-25%",0:"0",25:"+25%",50:"+50%"},
                           tooltip={"placement":"bottom","always_visible":True}),
                html.Div("Boosts votes in seats where selected ethnicity is largest",
                         style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"4px"}),
            ], style={"flex":"1","minWidth":"200px"}),
        ], style={"display":"flex","gap":"20px","flexWrap":"wrap","alignItems":"flex-start",
                  "background":BG_CARD,"borderBottom":f"1px solid {BORDER}",
                  "padding":"14px 28px 18px"}),

        # Scenario label
        html.Div(id="jhr-sim-scenario",
                 style={"padding":"10px 28px 0","color":TEXT_MUTED,"fontSize":"12px","fontStyle":"italic"}),

        # KPIs
        html.Div(id="jhr-sim-kpis",
                 style={"display":"flex","gap":"12px","flexWrap":"wrap","padding":"12px 28px 0"}),

        # Map
        html.Div([
            html.Div([
                html.Div("Simulated Seat Winners — Johor", style={"color":TEXT_MUTED,"fontSize":"11px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","padding":"14px 16px 8px"}),
                dcc.Graph(id="jhr-sim-map", config={"displayModeBar":True,
                                                     "modeBarButtonsToRemove":["lasso2d","select2d"],
                                                     "displaylogo":False},
                          style={"height":"480px"}),
            ], style=card_style()),
        ], style={"padding":"16px 28px 0"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-sim-seat-chart",config={"displayModeBar":False},
                                style={"height":"340px"})],
                     style={"flex":"2","minWidth":"320px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-sim-flip-donut",config={"displayModeBar":False},
                                style={"height":"340px"})],
                     style={"flex":"1","minWidth":"260px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"16px 28px","flexWrap":"wrap"}),

        # Flipped table
        html.Div([
            html.Div([
                html.Div("Seats That Would Flip", style={"color":TEXT_MUTED,"fontSize":"11px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","padding":"14px 16px 8px"}),
                html.Div(id="jhr-sim-flipped-table"),
            ], style=card_style()),
        ], style={"padding":"0 28px 28px"}),

    ], style={"background":BG_DARK,"minHeight":"100vh",
              "color":TEXT_PRIMARY,"fontFamily":"Inter, sans-serif"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("jhr-sim-turnout","value"),
    Output("jhr-sim-swing-from","value"),
    Output("jhr-sim-swing-to","value"),
    Output("jhr-sim-swing-pct","value"),
    Output("jhr-sim-swing2-from","value"),
    Output("jhr-sim-swing2-to","value"),
    Output("jhr-sim-swing2-pct","value"),
    Output("jhr-sim-youth","value"),
    Output("jhr-sim-eth-group","value"),
    Output("jhr-sim-eth-boost","value"),
    Output("jhr-sim-seat-filter","value"),
    Output("jhr-sim-par-filter","value"),
    Input("jhr-sim-reset","n_clicks"),
    prevent_initial_call=True,
)
def reset_sim(_):
    return 0,"BN","PH",0,"PN","BN",0,0,"MALAY (%)",0,None,None


@callback(
    Output("jhr-sim-scenario","children"),
    Output("jhr-sim-kpis","children"),
    Output("jhr-sim-seat-chart","figure"),
    Output("jhr-sim-flip-donut","figure"),
    Output("jhr-sim-map","figure"),
    Output("jhr-sim-flipped-table","children"),
    Input("jhr-sim-turnout","value"),
    Input("jhr-sim-swing-from","value"),
    Input("jhr-sim-swing-to","value"),
    Input("jhr-sim-swing-pct","value"),
    Input("jhr-sim-swing2-from","value"),
    Input("jhr-sim-swing2-to","value"),
    Input("jhr-sim-swing2-pct","value"),
    Input("jhr-sim-youth","value"),
    Input("jhr-sim-eth-group","value"),
    Input("jhr-sim-eth-boost","value"),
    Input("jhr-sim-seat-filter","value"),
    Input("jhr-sim-par-filter","value"),
)
def run_simulation(turnout_delta, swing_from, swing_to, swing_pct,
                   swing2_from, swing2_to, swing2_pct,
                   youth_boost, eth_col, eth_boost,
                   seat_filter, par_filter):
    turnout_delta = float(turnout_delta or 0)
    swing_pct     = float(swing_pct or 0)
    swing2_pct    = float(swing2_pct or 0)
    youth_boost   = float(youth_boost or 0)
    eth_boost     = float(eth_boost or 0)
    seats         = seat_filter if seat_filter else None

    # Parliament area filter → expand to DUN seats within those areas
    if par_filter:
        df_all = load_johor_results()
        par_seats = df_all[df_all["PARLIAMENTARY NAME"].isin(par_filter)][
            "STATE CONSTITUENCY NAME"].tolist()
        seats = list(set(seats or par_seats) & set(par_seats)) if seats else par_seats

    df = simulate_johor(
        turnout_delta=turnout_delta,
        swing_to=swing_to or "PH", swing_pct=swing_pct,
        swing_from=swing_from or "BN",
        youth_boost=youth_boost, eth_col=eth_col, eth_boost=eth_boost,
        constituencies=seats,
        swing2_from=swing2_from or "PN", swing2_to=swing2_to or "BN",
        swing2_pct=swing2_pct,
    )

    # Scenario label
    parts = []
    if turnout_delta != 0:
        parts.append(f"Turnout {'↑' if turnout_delta>0 else '↓'}{abs(turnout_delta):.1f}pp")
    if swing_pct != 0:
        parts.append(f"{swing_pct:.1f}% swing {swing_from}→{swing_to}")
    if swing2_pct != 0:
        parts.append(f"{swing2_pct:.1f}% swing {swing2_from}→{swing2_to}")
    if youth_boost != 0:
        parts.append(f"Youth {'↑' if youth_boost>0 else '↓'}{abs(youth_boost):.0f}%")
    if eth_boost != 0 and eth_col:
        parts.append(f"{eth_col.replace(' (%)','').title()} {'↑' if eth_boost>0 else '↓'}{abs(eth_boost):.0f}%")
    if seats:
        parts.append(f"{len(seats)} seat(s) only")
    scenario_text = ("Scenario: " + " · ".join(parts)) if parts else \
        "Baseline Johor 2022 — adjust parameters above"

    # KPIs
    base_df_full = load_johor_results()
    flipped      = df[df["SEAT_FLIPPED"]]
    n_flipped    = len(flipped)
    base_seats   = base_df_full.groupby("COALITION").size().to_dict()
    sim_seats    = df.groupby("SIM_WINNER").size().to_dict()

    if seats:
        base_chart = base_df_full[base_df_full["STATE CONSTITUENCY NAME"].isin(seats)].groupby("COALITION").size().to_dict()
        sim_chart  = df[df["STATE CONSTITUENCY NAME"].isin(seats)].groupby("SIM_WINNER").size().to_dict()
        kpi_base   = base_chart; kpi_sim = sim_chart
        chart_title = f"Projected Seat Count — {len(seats)} Selected Seat(s)"
        show_maj    = False; kpi_scope = f"of {len(seats)} seats"
    else:
        base_chart = base_seats; sim_chart = sim_seats
        kpi_base   = base_seats; kpi_sim   = sim_seats
        chart_title = "Projected Seat Count vs Johor 2022 Baseline"
        show_maj    = True; kpi_scope = "of 56 seats"

    bn_sim = kpi_sim.get("BN",0); bn_base = kpi_base.get("BN",0)
    ph_sim = kpi_sim.get("PH",0); ph_base = kpi_base.get("PH",0)
    pn_sim = kpi_sim.get("PN",0); pn_base = kpi_base.get("PN",0)

    kpis = [
        _kpi("Seats Flipped", str(n_flipped), "vs Johor 2022",
             color="#FF7043" if n_flipped > 0 else TEXT_MUTED),
        _kpi("BN Projected", str(bn_sim),
             f"{'↑' if bn_sim>bn_base else '↓'}{abs(bn_sim-bn_base)} vs actual · {kpi_scope}",
             color=coal_color("BN")),
        _kpi("PH Projected", str(ph_sim),
             f"{'↑' if ph_sim>ph_base else '↓'}{abs(ph_sim-ph_base)} vs actual · {kpi_scope}",
             color=coal_color("PH")),
        _kpi("PN Projected", str(pn_sim),
             f"{'↑' if pn_sim>pn_base else '↓'}{abs(pn_sim-pn_base)} vs actual · {kpi_scope}",
             color=coal_color("PN")),
        _kpi("Simple Majority", "29 seats",
             _majority_label(sim_seats), color=_majority_color(sim_seats)),
    ]

    # Seat bar
    all_coal = [c for c in sorted(set(list(base_chart)+list(sim_chart)),
                                   key=lambda c: -base_chart.get(c,0))
                if base_chart.get(c,0)+sim_chart.get(c,0)>0]
    fig_seats = go.Figure()
    fig_seats.add_trace(go.Bar(name="Actual",x=all_coal,
        y=[base_chart.get(c,0) for c in all_coal],
        marker_color=[coal_color(c) for c in all_coal],opacity=0.35,
        text=[str(base_chart.get(c,0)) for c in all_coal],
        textposition="outside",textfont=dict(size=11,color=TEXT_MUTED),
        hovertemplate="<b>%{x}</b><br>Actual: %{y}<extra></extra>"))
    fig_seats.add_trace(go.Bar(name="Simulated",x=all_coal,
        y=[sim_chart.get(c,0) for c in all_coal],
        marker_color=[coal_color(c) for c in all_coal],opacity=1.0,
        text=[str(sim_chart.get(c,0)) for c in all_coal],
        textposition="outside",textfont=dict(size=12,color=TEXT_PRIMARY),
        hovertemplate="<b>%{x}</b><br>Simulated: %{y}<extra></extra>"))
    if show_maj:
        fig_seats.add_hline(y=MAJORITY_SEATS,line_dash="dash",line_color="#F9A825",line_width=1.5,
            annotation=dict(text=f"Majority ({MAJORITY_SEATS})",font=dict(size=10,color="#F9A825"),xanchor="right"))
    y_max = max(list(base_chart.values())+list(sim_chart.values())+[5])+2
    fig_seats.update_layout(**CHART_LAYOUT,
        title=dict(text=chart_title,font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        barmode="group",showlegend=True,
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,range=[0,max(y_max,10)]),
        bargap=0.2,bargroupgap=0.05,margin=dict(l=10,r=10,t=45,b=10))

    # Flip donut
    if n_flipped > 0:
        flip_summary = flipped.groupby(["COALITION","SIM_WINNER"]).size().reset_index(name="N")
        fig_flip = go.Figure(go.Pie(
            labels=[f"{r['COALITION']}→{r['SIM_WINNER']}" for _,r in flip_summary.iterrows()],
            values=flip_summary["N"].tolist(),hole=0.58,
            marker=dict(colors=[coal_color(r["SIM_WINNER"]) for _,r in flip_summary.iterrows()],
                        line=dict(color=BG_DARK,width=2)),
            textinfo="label+value",textfont=dict(size=11,color=TEXT_PRIMARY),
            hovertemplate="<b>%{label}</b><br>%{value} seats<extra></extra>"))
        fig_flip.update_layout(**CHART_LAYOUT,
            title=dict(text=f"{n_flipped} Seats Flipped",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
            annotations=[dict(text=f"<b>{n_flipped}</b><br><span style='font-size:11px'>flipped</span>",
                              x=0.5,y=0.5,font_size=20,showarrow=False,font_color="#FF7043")],
            showlegend=True,margin=dict(l=10,r=10,t=45,b=10))
    else:
        fig_flip = go.Figure()
        fig_flip.add_annotation(text="No seats flipped<br>under this scenario",
            x=0.5,y=0.5,xref="paper",yref="paper",
            font=dict(size=14,color=TEXT_MUTED),showarrow=False)
        fig_flip.update_layout(**CHART_LAYOUT,
            title=dict(text="Seats Flipped",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
            margin=dict(l=10,r=10,t=45,b=10))

    # Map
    fig_map = make_simulation_map(df, seats=seats)

    # Flipped table
    if n_flipped > 0:
        tbl = flipped[["STATE CONSTITUENCY NAME","PARLIAMENTARY NAME",
                        "COALITION","SIM_WINNER","WINNING MAJORITY",
                        "SIM_MAJORITY","SIM_MAJORITY_PCT"]].copy()
        tbl.columns = ["Constituency","Parliament Area","Actual Winner",
                       "Projected Winner","Actual Majority","Sim Majority","Sim Majority %"]
        tbl["Constituency"]   = tbl["Constituency"].str.title()
        tbl["Parliament Area"]= tbl["Parliament Area"].str.title()
        tbl["Actual Majority"]= tbl["Actual Majority"].apply(lambda x: f"{int(x):,}")
        tbl["Sim Majority"]   = tbl["Sim Majority"].apply(lambda x: f"{int(x):,}")
        tbl["Sim Majority %"] = tbl["Sim Majority %"].apply(lambda x: f"{x:.1f}%")
        tbl = tbl.sort_values("Sim Majority %")
        table = dash_table.DataTable(
            data=tbl.to_dict("records"),
            columns=[{"name":c,"id":c} for c in tbl.columns],
            style_table={"overflowX":"auto"},
            style_header={"backgroundColor":BG_CARD2,"color":TEXT_MUTED,"fontWeight":"600",
                          "fontSize":"11px","textTransform":"uppercase","letterSpacing":"0.06em",
                          "border":f"1px solid {BORDER}","padding":"10px 12px"},
            style_cell={"backgroundColor":BG_CARD,"color":TEXT_PRIMARY,"border":f"1px solid {BORDER}",
                        "padding":"9px 12px","fontSize":"13px","fontFamily":"Inter, sans-serif",
                        "textAlign":"left","minWidth":"90px"},
            style_data_conditional=[
                {"if":{"filter_query":'{Projected Winner} = "' + c + '"'},
                 "borderLeft":"3px solid " + col}
                for c, col in JOHOR_COALITION_COLORS.items()
            ],
            sort_action="native", page_size=20,
        )
    else:
        table = html.Div(
            "No seats flip under current parameters. Try increasing swing % or turnout change.",
            style={"color":TEXT_MUTED,"fontSize":"13px","padding":"16px"},
        )

    return scenario_text, kpis, fig_seats, fig_flip, fig_map, table
