"""
pages/johor2026_simulation.py — Johor 2026 Seat-by-Seat Swing Simulator

Two tools on one page:
  1. Seat Detail — pick one DUN seat, redistribute each 2022 contesting party's votes
     (with its own turnout change) across whichever parties actually filed nomination
     for 2026 in that same seat. Every source row is normalised to 100% on compute, so
     votes are always fully accounted for even when a 2022 party has no 2026 equivalent
     (e.g. 2022 PN/Pejuang/PBM/Independent in Puteri Wangsa, where 2026 only has
     BN/PH/Muda/Bersama/Independent).
  2. Statewide Rollup — a generalised bloc-level swing (BN/PH/PN/Muda/Bersama/...)
     applied uniformly across all 56 seats, restricted to whichever blocs actually field
     a 2026 candidate in each seat, to project a full assembly seat count.
"""

from dash import dcc, html, Input, Output, State, callback, ALL, MATCH, dash_table, ctx, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from collections import defaultdict

from utils.johor2026_data import (
    load_2022_candidates, load_2026_candidates, get_seat_2022, get_seat_2026,
    bloc_votes_for_seat_2022, blocs_contesting_2026, seat_options, party_color, bloc_color,
    load_geo, coalition_label,
)
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT, map_bounds_zoom

JOHOR_CENTER = (1.8, 103.3, 8.2)
MAJORITY_SEATS = 29

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(color=TEXT_MUTED, size=11)),
)


def card_style():
    return {"background": BG_CARD, "border": f"1px solid {BORDER}", "borderRadius": "12px", "padding": "4px"}


TAB_STYLE = {
    "backgroundColor": BG_CARD, "color": TEXT_MUTED, "border": "none",
    "borderBottom": f"1px solid {BORDER}", "padding": "12px 16px",
    "fontFamily": "Inter, sans-serif", "fontSize": "13px",
}
TAB_SELECTED_STYLE = {
    "backgroundColor": BG_CARD2, "color": TEXT_PRIMARY, "border": "none",
    "borderBottom": f"3px solid {ACCENT}", "padding": "12px 16px",
    "fontFamily": "Inter, sans-serif", "fontSize": "13px", "fontWeight": "700",
}


def _label_style():
    return {"color": TEXT_MUTED, "fontSize": "11px", "textTransform": "uppercase",
            "letterSpacing": "0.07em", "marginBottom": "5px", "display": "block"}


def _kpi(label, value, sub=None, color=ACCENT):
    return html.Div([
        html.Div(label, style={"color": TEXT_MUTED, "fontSize": "10px", "textTransform": "uppercase",
                                "letterSpacing": "0.08em", "marginBottom": "5px"}),
        html.Div(value, style={"color": color, "fontSize": "22px", "fontWeight": "700",
                                "lineHeight": "1.1", "letterSpacing": "-0.02em"}),
        html.Div(sub or "", style={"color": TEXT_MUTED, "fontSize": "10px", "marginTop": "3px"}),
    ], style={"background": BG_CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px",
              "padding": "12px 14px", "flex": "1", "minWidth": "130px"})


def display_party(party_key, bloc=None):
    if str(party_key).startswith("INDEPENDENT ("):
        return "INDEPENDENT (" + party_key.split("(", 1)[1].rstrip(")").title() + ")"
    if str(party_key) == "INDEPENDENT":
        return "INDEPENDENT"
    return coalition_label(party_key, bloc)


def color_for_key(party_key):
    base = "INDEPENDENT" if str(party_key).startswith("INDEPENDENT") else party_key
    return party_color(base)


def party_bloc_lookup(df22, df26):
    lookup = dict(zip(df22["PARTY_KEY"], df22["BLOC"]))
    lookup.update(dict(zip(df26["PARTY_KEY"], df26["BLOC"])))
    return lookup


# ── Seat Detail: data prep ───────────────────────────────────────────────────────

def default_matrix(df22, df26):
    dst_keys = df26["PARTY_KEY"].tolist()
    matrix = {}
    for _, row in df22.iterrows():
        src = row["PARTY_KEY"]
        if src in dst_keys:
            matrix[src] = {d: (100.0 if d == src else 0.0) for d in dst_keys}
        else:
            even = round(100.0 / len(dst_keys), 1) if dst_keys else 0.0
            matrix[src] = {d: even for d in dst_keys}
    return matrix


def compute_seat_simulation(code, pct_matrix, turnout_map):
    df22 = get_seat_2022(code)
    df26 = get_seat_2026(code)
    dst_keys = df26["PARTY_KEY"].tolist()

    row_info = {}
    projected = {d: 0.0 for d in dst_keys}
    flow = {}
    for _, row in df22.iterrows():
        src = row["PARTY_KEY"]
        base_votes = float(row["VOTES"])
        t_delta = float(turnout_map.get(src, 0) or 0)
        adj_votes = max(0.0, base_votes * (1 + t_delta / 100))

        raw_pcts = pct_matrix.get(src, {})
        row_total = sum(v for v in raw_pcts.values() if v is not None)
        flow[src] = {}
        if row_total > 0:
            for d in dst_keys:
                v = raw_pcts.get(d) or 0
                norm_pct = v / row_total * 100
                moved = adj_votes * norm_pct / 100
                flow[src][d] = moved
                projected[d] += moved
        else:
            for d in dst_keys:
                flow[src][d] = 0.0

        row_info[src] = dict(base_votes=base_votes, adj_votes=adj_votes,
                              t_delta=t_delta, row_total=row_total)

    projected_total = sum(projected.values())
    base_total = df22["VOTES"].sum()

    base_winner = df22.loc[df22["VOTES"].idxmax(), "PARTY_KEY"] if len(df22) else None
    base_sorted = sorted(df22["VOTES"].tolist(), reverse=True)
    base_margin = (base_sorted[0] - base_sorted[1]) if len(base_sorted) > 1 else (base_sorted[0] if base_sorted else 0)

    proj_winner = max(projected, key=projected.get) if projected else None
    proj_sorted = sorted(projected.values(), reverse=True)
    proj_margin = (proj_sorted[0] - proj_sorted[1]) if len(proj_sorted) > 1 else (proj_sorted[0] if proj_sorted else 0)

    seat_row26 = df26.iloc[0] if len(df26) else None
    electorate_2026 = float(seat_row26["TOTAL ELECTORATE"]) if seat_row26 is not None and pd.notna(seat_row26.get("TOTAL ELECTORATE")) else None
    turnout_2022 = float(df22.iloc[0]["TURNOUT (%)"]) if len(df22) and pd.notna(df22.iloc[0].get("TURNOUT (%)")) else None
    proj_turnout = (projected_total / electorate_2026 * 100) if electorate_2026 else None

    return dict(
        row_info=row_info, flow=flow, projected=projected, projected_total=projected_total,
        base_total=base_total, base_winner=base_winner, base_margin=base_margin,
        proj_winner=proj_winner, proj_margin=proj_margin,
        turnout_2022=turnout_2022, proj_turnout=proj_turnout, dst_keys=dst_keys,
    )


def make_seat_votechart(df22, df26, result):
    keys_22 = df22["PARTY_KEY"].tolist()
    keys_26 = result["dst_keys"]
    all_keys = list(dict.fromkeys(keys_22 + keys_26))
    bloc_lookup = party_bloc_lookup(df22, df26)

    base_total = result["base_total"] or 1
    proj_total = result["projected_total"] or 1
    base_share = {k: (df22.loc[df22["PARTY_KEY"] == k, "VOTES"].sum() / base_total * 100) if k in keys_22 else 0
                  for k in all_keys}
    proj_share = {k: (result["projected"].get(k, 0) / proj_total * 100) if k in keys_26 else 0
                  for k in all_keys}

    labels = [display_party(k, bloc_lookup.get(k)) for k in all_keys]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="2022 Actual", x=labels, y=[base_share[k] for k in all_keys],
        marker_color=[color_for_key(k) for k in all_keys], opacity=0.4,
        text=[f"{base_share[k]:.1f}%" for k in all_keys], textposition="outside",
        textfont=dict(size=10, color=TEXT_MUTED),
        hovertemplate="<b>%{x}</b><br>2022: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(name="2026 Projected", x=labels, y=[proj_share[k] for k in all_keys],
        marker_color=[color_for_key(k) for k in all_keys], opacity=1.0,
        text=[f"{proj_share[k]:.1f}%" for k in all_keys], textposition="outside",
        textfont=dict(size=11, color=TEXT_PRIMARY),
        hovertemplate="<b>%{x}</b><br>2026 Projected: %{y:.1f}%<extra></extra>"))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Vote Share — 2022 Actual vs 2026 Projected", font=dict(size=14, color=TEXT_PRIMARY), x=0.01),
        barmode="group", showlegend=True,
        xaxis=dict(showgrid=False, color=TEXT_MUTED),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=TEXT_MUTED, ticksuffix="%"),
        bargap=0.25, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def make_seat_minimap(code):
    geo = load_geo()
    fig = go.Figure()
    if geo is None:
        return fig
    other = [f for f in geo["features"] if f["id"] != code]
    sel = [f for f in geo["features"] if f["id"] == code]
    if other:
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": other},
            locations=[f["id"] for f in other], z=[0] * len(other),
            colorscale=[[0, BG_CARD2], [1, BG_CARD2]], showscale=False, showlegend=False,
            marker=dict(opacity=0.5, line=dict(color="#1a1a2e", width=0.4)), hoverinfo="skip",
        ))
    if sel:
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": sel},
            locations=[f["id"] for f in sel], z=[1], colorscale=[[0, ACCENT], [1, ACCENT]],
            showscale=False, showlegend=False,
            marker=dict(opacity=0.95, line=dict(color="#1a1a2e", width=1)),
            hovertext=[sel[0]["properties"]["NAMADUN"].title()], hoverinfo="text",
        ))
        lat_c, lon_c, zoom = map_bounds_zoom(sel)
    else:
        lat_c, lon_c, zoom = JOHOR_CENTER
    fig.update_layout(
        map=dict(style="dark", center=dict(lat=lat_c, lon=lon_c), zoom=max(zoom - 1.2, 4)),
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
    )
    return fig


def make_flow_table(df22, df26, result):
    dst_keys = result["dst_keys"]
    bloc_lookup = party_bloc_lookup(df22, df26)
    dst_labels = {d: display_party(d, bloc_lookup.get(d)) for d in dst_keys}
    rows = []
    for src, info in result["row_info"].items():
        row = {"From (2022)": display_party(src, bloc_lookup.get(src)), "Adj. Votes": f"{info['adj_votes']:,.0f}"}
        for d in dst_keys:
            row[dst_labels[d]] = f"{result['flow'][src][d]:,.0f}"
        rows.append(row)
    total_row = {"From (2022)": "2026 Projected Total", "Adj. Votes": f"{result['projected_total']:,.0f}"}
    for d in dst_keys:
        total_row[dst_labels[d]] = f"{result['projected'][d]:,.0f}"
    rows.append(total_row)

    cols = ["From (2022)", "Adj. Votes"] + [dst_labels[d] for d in dst_keys]
    return dash_table.DataTable(
        data=rows, columns=[{"name": c, "id": c} for c in cols],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG_CARD2, "color": TEXT_MUTED, "fontWeight": "600",
                      "fontSize": "10px", "textTransform": "uppercase", "letterSpacing": "0.05em",
                      "border": f"1px solid {BORDER}", "padding": "8px 10px"},
        style_cell={"backgroundColor": BG_CARD, "color": TEXT_PRIMARY, "border": f"1px solid {BORDER}",
                    "padding": "7px 10px", "fontSize": "12px", "fontFamily": "Inter, sans-serif",
                    "textAlign": "right", "minWidth": "80px"},
        style_cell_conditional=[{"if": {"column_id": "From (2022)"}, "textAlign": "left", "fontWeight": "600"}],
        style_data_conditional=[{"if": {"filter_query": '{From (2022)} = "2026 Projected Total"'},
                                  "borderTop": f"2px solid {ACCENT}", "fontWeight": "700"}],
    )


def _num_input(id_, value, width="64px"):
    return dcc.Input(id=id_, type="number", value=value, min=-100, max=200, step=0.5, debounce=True,
                      style={"background": BG_CARD2, "border": f"1px solid {BORDER}", "color": TEXT_PRIMARY,
                             "borderRadius": "5px", "padding": "5px 6px", "width": width,
                             "fontFamily": "Inter", "fontSize": "12px", "textAlign": "center"})


def build_seat_panel(code):
    df22 = get_seat_2022(code)
    df26 = get_seat_2026(code)
    if not len(df22) or not len(df26):
        return html.Div("No data for this seat.", style={"color": TEXT_MUTED, "padding": "20px"})

    dst_keys = df26["PARTY_KEY"].tolist()
    matrix = default_matrix(df22, df26)
    base_total = df22["VOTES"].sum()
    dst_bloc = dict(zip(df26["PARTY_KEY"], df26["BLOC"]))

    header_cells = [html.Th("2022 Party (turnout Δ%)", style={"textAlign": "left", "padding": "8px 10px",
                     "color": TEXT_MUTED, "fontSize": "11px"})]
    for d in dst_keys:
        header_cells.append(html.Th([
            html.Span(display_party(d, dst_bloc.get(d)), style={"color": color_for_key(d), "fontWeight": "700"}),
        ], style={"textAlign": "center", "padding": "8px 6px", "fontSize": "11px", "minWidth": "84px"}))
    header_cells.append(html.Th("Row Total", style={"textAlign": "center", "padding": "8px 10px",
                        "color": TEXT_MUTED, "fontSize": "11px"}))

    body_rows = []
    for _, row in df22.iterrows():
        src = row["PARTY_KEY"]
        share = (row["VOTES"] / base_total * 100) if base_total else 0
        row_vals = [matrix[src][d] for d in dst_keys]
        cells = [html.Td([
            html.Div([
                html.Span("● ", style={"color": color_for_key(src)}),
                html.Span(display_party(src, row["BLOC"]), style={"fontWeight": "600", "fontSize": "12px"}),
            ]),
            html.Div(f"{int(row['VOTES']):,} votes ({share:.1f}%)",
                     style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "6px"}),
            html.Div("Turnout Difference", style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "2px"}),
            html.Div(
                dcc.Slider(id={"type": "j26-sim-to-slider", "src": src}, min=-100, max=100, step=0.5, value=0,
                           marks=None, included=False, tooltip={"placement": "bottom", "always_visible": False}),
                style={"width": "150px", "marginBottom": "2px"}),
            html.Div([
                _num_input({"type": "j26-sim-to", "src": src}, 0, width="56px"),
                html.Span("%", style={"color": TEXT_MUTED, "fontSize": "10px"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "4px"}),
        ], style={"padding": "8px 10px", "borderTop": f"1px solid {BORDER}"})]
        for d in dst_keys:
            cells.append(html.Td(
                _num_input({"type": "j26-sim-pct", "src": src, "dst": d}, matrix[src][d]),
                style={"padding": "8px 6px", "textAlign": "center", "borderTop": f"1px solid {BORDER}"}))
        cells.append(html.Td(
            html.Div(id={"type": "j26-sim-rowtotal", "src": src}, children=f"{sum(row_vals):.1f}%",
                     style={"fontWeight": "700", "fontSize": "12px", "color": "#4CAF50"}),
            style={"padding": "8px 10px", "textAlign": "center", "borderTop": f"1px solid {BORDER}"}))
        body_rows.append(html.Tr(cells))

    matrix_table = html.Table([
        html.Thead(html.Tr(header_cells)),
        html.Tbody(body_rows),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    lineup_2026 = html.Div([
        html.Div("2026 Lineup", style={"color": TEXT_MUTED, "fontSize": "11px", "textTransform": "uppercase",
                  "letterSpacing": "0.07em", "marginBottom": "8px"}),
        html.Div([
            html.Div([
                html.Span("● ", style={"color": color_for_key(r["PARTY_KEY"])}),
                html.Span(f"{display_party(r['PARTY_KEY'], r['BLOC'])} — {r['CANDIDATE']}", style={"fontSize": "12px"}),
                html.Span(f" ({(r['SEX'] or '?')[:1]}, {'?' if pd.isna(r['AGE']) else int(r['AGE'])})",
                          style={"color": TEXT_MUTED, "fontSize": "11px"}),
            ], style={"marginBottom": "4px"})
            for _, r in df26.iterrows()
        ]),
    ], style={**card_style(), "padding": "14px 16px", "flex": "1", "minWidth": "240px"})

    return html.Div([
        html.Div([
            lineup_2026,
            html.Div([dcc.Graph(id="j26-sim-minimap", figure=make_seat_minimap(code),
                                 config={"displayModeBar": False}, style={"height": "180px"})],
                     style={**card_style(), "flex": "1", "minWidth": "220px"}),
        ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"}),

        html.Div([
            html.Div("Swing & Turnout Matrix — % of each 2022 party's (turnout-adjusted) votes flowing to each 2026 party",
                      style={"color": TEXT_MUTED, "fontSize": "11px", "marginBottom": "8px"}),
            html.Div(matrix_table, style={"overflowX": "auto"}),
            html.Div("Each cell is independent — nothing is changed automatically. Enter the % of that "
                     "2022 party's (turnout-adjusted) votes going to each 2026 party yourself; the Row Total "
                     "turns red whenever it isn't exactly 100% (whether over or under), green when it is.",
                     style={"color": TEXT_MUTED, "fontSize": "10px", "marginTop": "8px", "fontStyle": "italic"}),
        ], style={**card_style(), "padding": "14px 16px", "marginBottom": "16px"}),

        html.Div(id="j26-sim-seat-kpis", style={"display": "flex", "gap": "12px", "flexWrap": "wrap",
                                                  "marginBottom": "16px"}),

        html.Div([
            html.Div([dcc.Graph(id="j26-sim-seat-chart", config={"displayModeBar": False}, style={"height": "360px"})],
                     style={**card_style(), "flex": "1", "minWidth": "320px"}),
        ], style={"marginBottom": "16px"}),

        html.Div([
            html.Div("Vote Flow Detail", style={"color": TEXT_MUTED, "fontSize": "11px", "textTransform": "uppercase",
                      "letterSpacing": "0.07em", "marginBottom": "8px"}),
            html.Div(id="j26-sim-flowtable"),
        ], style=card_style()),
    ])


@callback(
    Output("j26-sim-seat-panel", "children"),
    Input("j26-sim-seat", "value"),
    Input("j26-sim-seat-reset", "n_clicks"),
)
def render_seat_panel(code, _):
    if not code:
        return html.Div("Select a seat above to start simulating.",
                         style={"color": TEXT_MUTED, "padding": "30px", "textAlign": "center"})
    return build_seat_panel(code)


@callback(
    Output({"type": "j26-sim-to", "src": MATCH}, "value"),
    Output({"type": "j26-sim-to-slider", "src": MATCH}, "value"),
    Input({"type": "j26-sim-to", "src": MATCH}, "value"),
    Input({"type": "j26-sim-to-slider", "src": MATCH}, "value"),
    prevent_initial_call=True,
)
def sync_turnout(input_val, slider_val):
    trig = ctx.triggered_id
    if trig and trig.get("type") == "j26-sim-to-slider":
        return slider_val, no_update
    return no_update, input_val


@callback(
    Output({"type": "j26-sim-rowtotal", "src": MATCH}, "children"),
    Output({"type": "j26-sim-rowtotal", "src": MATCH}, "style"),
    Input({"type": "j26-sim-pct", "src": MATCH, "dst": ALL}, "value"),
)
def validate_row(values):
    total = sum((v or 0) for v in values)
    color = "#4CAF50" if abs(total - 100) < 0.05 else "#E53935"
    return f"{total:.1f}%", {"fontWeight": "700", "fontSize": "12px", "color": color}


@callback(
    Output("j26-sim-seat-kpis", "children"),
    Output("j26-sim-seat-chart", "figure"),
    Output("j26-sim-flowtable", "children"),
    Input({"type": "j26-sim-pct", "src": ALL, "dst": ALL}, "value"),
    Input({"type": "j26-sim-to", "src": ALL}, "value"),
    State({"type": "j26-sim-pct", "src": ALL, "dst": ALL}, "id"),
    State({"type": "j26-sim-to", "src": ALL}, "id"),
    State("j26-sim-seat", "value"),
)
def recompute_seat(pct_values, to_values, pct_ids, to_ids, code):
    if not code or not pct_ids:
        return no_update, no_update, no_update

    pct_matrix = defaultdict(dict)
    for id_, val in zip(pct_ids, pct_values):
        pct_matrix[id_["src"]][id_["dst"]] = val if val is not None else 0
    turnout_map = {id_["src"]: (val or 0) for id_, val in zip(to_ids, to_values)}

    result = compute_seat_simulation(code, pct_matrix, turnout_map)

    df22 = get_seat_2022(code)
    df26 = get_seat_2026(code)

    bloc_lookup = party_bloc_lookup(df22, df26)
    proj_w = result["proj_winner"]
    base_w = result["base_winner"]
    flipped = proj_w != base_w
    proj_share = (result["projected"].get(proj_w, 0) / result["projected_total"] * 100) if result["projected_total"] else 0
    base_share = (df22.loc[df22["PARTY_KEY"] == base_w, "VOTES"].sum() / result["base_total"] * 100) if result["base_total"] else 0

    kpis = [
        _kpi("2022 Actual Winner", display_party(base_w, bloc_lookup.get(base_w)) if base_w else "—",
             f"{base_share:.1f}% · majority {int(result['base_margin']):,}", color=color_for_key(base_w)),
        _kpi("2026 Projected Winner", display_party(proj_w, bloc_lookup.get(proj_w)) if proj_w else "—",
             f"{proj_share:.1f}% · majority {int(result['proj_margin']):,}"
             + (" ⚡ FLIPPED" if flipped else ""),
             color="#FF7043" if flipped else color_for_key(proj_w)),
        _kpi("Projected Turnout", f"{result['proj_turnout']:.1f}%" if result["proj_turnout"] is not None else "—",
             f"vs {result['turnout_2022']:.1f}% in 2022" if result["turnout_2022"] is not None else "",
             color=ACCENT),
        _kpi("Projected Total Votes", f"{int(result['projected_total']):,}",
             f"vs {int(result['base_total']):,} in 2022"),
    ]

    fig_chart = make_seat_votechart(df22, df26, result)
    flow_table = make_flow_table(df22, df26, result)

    return kpis, fig_chart, flow_table


# ── Statewide Rollup ──────────────────────────────────────────────────────────────
# Matrix rows = 2022 source groups; columns = 2026 destination groups.

SRC_GROUPS = ["BN", "PH", "PN", "MUDA", "OTHERS & INDEPENDENTS"]
SRC_BLOCS = {
    "BN":                    ["BN"],
    "PH":                    ["PH"],
    "PN":                    ["PN"],
    "MUDA":                  ["MUDA"],
    "OTHERS & INDEPENDENTS": ["PEJUANG", "PBM", "INDEPENDENT", "OTHERS"],
}

DST_COLS = ["BN", "PH", "PN", "MUDA + PSM", "BERSAMA", "OTHERS & INDEPENDENTS"]
DST_PARTIES = {
    "BN":                    frozenset(["UMNO", "MCA", "MIC", "GERAKAN"]),
    "PH":                    frozenset(["PKR", "DAP", "AMANAH"]),
    "PN":                    frozenset(["PAS", "PPBM", "BERSATU", "MIPP", "PEJUANG"]),
    "MUDA + PSM":            frozenset(["MUDA", "PSM"]),
    "BERSAMA":               frozenset(["BERSAMA"]),
    "OTHERS & INDEPENDENTS": frozenset(["POAM", "PUTRA", "WARISAN", "INDEPENDENT"]),
}
DST_TO_BLOC = {
    "BN": "BN", "PH": "PH", "PN": "PN",
    "MUDA + PSM": "MUDA", "BERSAMA": "BERSAMA",
    "OTHERS & INDEPENDENTS": "INDEPENDENT",
}


def default_rollup_matrix():
    m = {src: {dst: 0.0 for dst in DST_COLS} for src in SRC_GROUPS}
    m["BN"]["BN"] = 100.0
    m["PH"]["PH"] = 100.0
    m["PN"]["PN"] = 100.0
    m["MUDA"]["MUDA + PSM"] = 100.0
    m["OTHERS & INDEPENDENTS"]["OTHERS & INDEPENDENTS"] = 100.0
    return m


def get_statewide_src_totals():
    """Total 2022 votes per source group, cached."""
    c22 = load_2022_candidates()
    tot = sum(c22["VOTES"])
    out = {}
    for grp, blocs in SRC_BLOCS.items():
        v = int(c22[c22["BLOC"].isin(blocs)]["VOTES"].sum())
        out[grp] = (v, f"{v / tot * 100:.1f}%" if tot else "0%")
    return out


def simulate_statewide_matrix(pct_matrix, turnout_map):
    """Full swing matrix: each (src_group, dst_col) cell is a % of src votes going to dst."""
    c22 = load_2022_candidates()
    c26 = load_2026_candidates()
    seats = c22[["UNIQUE CODE", "SEAT_LABEL", "PARLIAMENTARY NAME"]].drop_duplicates()

    rows = []
    for _, seat in seats.iterrows():
        code = seat["UNIQUE CODE"]
        bloc_v = bloc_votes_for_seat_2022(code)
        seat_parties_26 = set(c26[c26["UNIQUE CODE"] == code]["PARTY"].unique())

        # Eligible dst columns for this seat (has at least one matching 2026 party)
        eligible_dst = {dst: DST_PARTIES[dst] & seat_parties_26
                        for dst in DST_COLS if DST_PARTIES[dst] & seat_parties_26}

        # Turnout-adjusted source votes per src group
        src_adj = {}
        for grp, blocs in SRC_BLOCS.items():
            base = sum(bloc_v.get(b, 0) for b in blocs)
            delta = float(turnout_map.get(grp, 0) or 0)
            src_adj[grp] = max(0.0, base * (1 + delta / 100))

        # Redistribute via matrix (rows normalised to 100% on compute)
        proj_by_dst = {dst: 0.0 for dst in DST_COLS}
        wasted = 0.0
        for grp, adj in src_adj.items():
            row = pct_matrix.get(grp, {})
            row_total = sum((v or 0) for v in row.values())
            if row_total <= 0:
                continue
            for dst in DST_COLS:
                pct = (row.get(dst) or 0) / row_total * 100
                moved = adj * pct / 100
                if dst in eligible_dst:
                    proj_by_dst[dst] += moved
                else:
                    wasted += moved

        # Project to bloc-level winner
        proj_by_bloc = {}
        for dst, v in proj_by_dst.items():
            if v > 0:
                b = DST_TO_BLOC.get(dst, dst)
                proj_by_bloc[b] = proj_by_bloc.get(b, 0) + v

        base_winner = max(bloc_v, key=bloc_v.get) if bloc_v else None
        proj_winner = max(proj_by_bloc, key=proj_by_bloc.get) if proj_by_bloc else base_winner

        rows.append(dict(
            code=code, seat=seat["SEAT_LABEL"], parliament=seat["PARLIAMENTARY NAME"],
            base_winner=base_winner, proj_winner=proj_winner,
            flipped=proj_winner != base_winner,
            proj_total=sum(proj_by_dst.values()), wasted=wasted,
        ))
    return rows


def make_rollup_map(rows):
    geo = load_geo()
    fig = go.Figure()
    if geo is None:
        return fig
    by_code = {r["code"]: r for r in rows}
    groups = defaultdict(list)
    for feat in geo["features"]:
        r = by_code.get(feat["id"])
        winner = r["proj_winner"] if r else "OTHERS"
        groups[winner].append((feat, r))
    for bloc, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        feats = [it[0] for it in items]
        hover = []
        for feat, r in items:
            if r:
                hover.append(f"<b>{r['seat'].title()}</b><br>2022: {r['base_winner']}<br>"
                              f"2026 Projected: <b>{r['proj_winner']}</b>" + (" ⚡" if r["flipped"] else ""))
            else:
                hover.append(feat["properties"]["NAMADUN"].title())
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": feats},
            locations=[f["id"] for f in feats], z=[1] * len(feats),
            colorscale=[[0, bloc_color(bloc)], [1, bloc_color(bloc)]], showscale=False,
            name=f"{bloc} ({len(feats)})", hovertext=hover, hoverinfo="text",
            marker=dict(opacity=0.9, line=dict(color="#1a1a2e", width=0.6)), showlegend=True,
        ))
    fig.update_layout(
        map=dict(style="dark", center=dict(lat=JOHOR_CENTER[0], lon=JOHOR_CENTER[1]), zoom=JOHOR_CENTER[2]),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        legend=dict(bgcolor=BG_CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=TEXT_MUTED, size=11), x=0.01, y=0.99, xanchor="left", yanchor="top"),
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER, font=dict(family="Inter", color=TEXT_PRIMARY, size=12)),
    )
    return fig


def build_rollup_matrix_row(src, totals_row):
    """Build one HTML table row for a 2022 source group."""
    total_v, total_pct = totals_row
    defaults = default_rollup_matrix()[src]
    row_val_sum = sum(defaults.values())

    cells = [html.Td([
        html.Div([
            html.Span("● ", style={"color": bloc_color(SRC_BLOCS[src][0])}),
            html.Span(src, style={"fontWeight": "700", "fontSize": "12px"}),
        ]),
        html.Div(f"{total_v:,} votes ({total_pct} statewide)",
                 style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "6px"}),
        html.Div("Turnout Difference", style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "2px"}),
        html.Div(
            dcc.Slider(id={"type": "j26-roll-to-slider", "src": src}, min=-100, max=100, step=0.5, value=0,
                       marks=None, included=False, tooltip={"placement": "bottom", "always_visible": False}),
            style={"width": "140px", "marginBottom": "2px"}),
        html.Div([
            _num_input({"type": "j26-roll-to", "src": src}, 0, width="56px"),
            html.Span("%", style={"color": TEXT_MUTED, "fontSize": "10px"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "4px"}),
    ], style={"padding": "8px 10px", "borderTop": f"1px solid {BORDER}"})]

    for dst in DST_COLS:
        cells.append(html.Td(
            _num_input({"type": "j26-roll-pct", "src": src, "dst": dst}, defaults[dst]),
            style={"padding": "8px 6px", "textAlign": "center", "borderTop": f"1px solid {BORDER}"}))

    cells.append(html.Td(
        html.Div(id={"type": "j26-roll-rowtotal", "src": src}, children=f"{row_val_sum:.1f}%",
                 style={"fontWeight": "700", "fontSize": "12px", "color": "#4CAF50"}),
        style={"padding": "8px 10px", "textAlign": "center", "borderTop": f"1px solid {BORDER}"}))
    return html.Tr(cells)


def build_rollup_panel():
    totals = get_statewide_src_totals()

    hdr_style = {"textAlign": "center", "padding": "8px 6px", "color": TEXT_MUTED, "fontSize": "11px",
                 "minWidth": "84px"}
    header_cells = [html.Th("2022 Source (turnout Δ%)", style={"textAlign": "left", "padding": "8px 10px",
                     "color": TEXT_MUTED, "fontSize": "11px"})]
    for dst in DST_COLS:
        header_cells.append(html.Th(html.Span(dst, style={"fontWeight": "700"}), style=hdr_style))
    header_cells.append(html.Th("Row Total", style={"textAlign": "center", "padding": "8px 10px",
                        "color": TEXT_MUTED, "fontSize": "11px"}))

    matrix_table = html.Table([
        html.Thead(html.Tr(header_cells)),
        html.Tbody([build_rollup_matrix_row(src, totals[src]) for src in SRC_GROUPS]),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    return html.Div([
        html.Div(id="j26-roll-kpis", style={"display": "flex", "gap": "12px", "flexWrap": "wrap",
                                              "marginBottom": "16px"}),

        html.Div([
            html.Div([
                html.Div("2022 → 2026 Swing & Turnout Matrix", style={"color": TEXT_PRIMARY, "fontSize": "14px",
                          "fontWeight": "700"}),
                html.Button("↺ Reset", id={"type": "j26-roll-reset", "panel": "rollup"}, n_clicks=0, style={
                    "background": "transparent", "color": TEXT_MUTED, "border": f"1px solid {BORDER}",
                    "borderRadius": "8px", "padding": "5px 12px", "cursor": "pointer", "fontSize": "11px",
                    "fontFamily": "Inter", "whiteSpace": "nowrap"}),
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                      "marginBottom": "8px"}),
            html.Div(matrix_table, style={"overflowX": "auto"}),
            html.Div("Each row should sum to 100%. The Row Total turns red if it doesn't. "
                     "If a 2026 party doesn't contest a given seat, votes to that column are excluded "
                     "from that seat's projection (counted as wasted votes in the KPIs above).",
                     style={"color": TEXT_MUTED, "fontSize": "10px", "marginTop": "8px", "fontStyle": "italic"}),
        ], style={**card_style(), "padding": "14px 16px", "marginBottom": "16px"}),

        html.Div([
            html.Div([
                html.Div("Projected 2026 Bloc Winner by Seat", style={"color": TEXT_MUTED, "fontSize": "11px",
                          "textTransform": "uppercase", "letterSpacing": "0.07em", "padding": "12px 14px 6px"}),
                dcc.Graph(id="j26-roll-map", config={"displayModeBar": True,
                          "modeBarButtonsToRemove": ["lasso2d", "select2d"], "displaylogo": False},
                          style={"height": "460px"}),
            ], style=card_style()),
        ], style={"marginBottom": "16px"}),

        html.Div([
            html.Div([dcc.Graph(id="j26-roll-seat-bar", config={"displayModeBar": False}, style={"height": "340px"})],
                     style={**card_style(), "flex": "1", "minWidth": "320px"}),
        ], style={"marginBottom": "16px"}),

        html.Div([
            html.Div("Seats That Would Flip", style={"color": TEXT_MUTED, "fontSize": "11px",
                      "textTransform": "uppercase", "letterSpacing": "0.07em", "padding": "12px 14px 6px"}),
            html.Div(id="j26-roll-flip-table"),
        ], style=card_style()),
    ])


@callback(
    Output({"type": "j26-roll-to", "src": MATCH}, "value"),
    Output({"type": "j26-roll-to-slider", "src": MATCH}, "value"),
    Input({"type": "j26-roll-to", "src": MATCH}, "value"),
    Input({"type": "j26-roll-to-slider", "src": MATCH}, "value"),
    prevent_initial_call=True,
)
def sync_rollup_turnout(input_val, slider_val):
    trig = ctx.triggered_id
    if trig and trig.get("type") == "j26-roll-to-slider":
        return slider_val, no_update
    return no_update, input_val


@callback(
    Output({"type": "j26-roll-rowtotal", "src": MATCH}, "children"),
    Output({"type": "j26-roll-rowtotal", "src": MATCH}, "style"),
    Input({"type": "j26-roll-pct", "src": MATCH, "dst": ALL}, "value"),
)
def validate_rollup_row(values):
    total = sum((v or 0) for v in values)
    color = "#4CAF50" if abs(total - 100) < 0.05 else "#E53935"
    return f"{total:.1f}%", {"fontWeight": "700", "fontSize": "12px", "color": color}


@callback(
    Output("j26-roll-kpis", "children"),
    Output("j26-roll-map", "figure"),
    Output("j26-roll-seat-bar", "figure"),
    Output("j26-roll-flip-table", "children"),
    Input({"type": "j26-roll-pct", "src": ALL, "dst": ALL}, "value"),
    Input({"type": "j26-roll-to", "src": ALL}, "value"),
    State({"type": "j26-roll-pct", "src": ALL, "dst": ALL}, "id"),
    State({"type": "j26-roll-to", "src": ALL}, "id"),
)
def recompute_rollup_matrix(pct_values, to_values, pct_ids, to_ids):
    if not pct_ids:
        return no_update, no_update, no_update, no_update

    pct_matrix = defaultdict(dict)
    for id_, val in zip(pct_ids, pct_values):
        pct_matrix[id_["src"]][id_["dst"]] = val if val is not None else 0
    turnout_map = {id_["src"]: (val or 0) for id_, val in zip(to_ids, to_values)}

    rows = simulate_statewide_matrix(pct_matrix, turnout_map)

    n_flipped = sum(1 for r in rows if r["flipped"])
    base_seats = pd.Series([r["base_winner"] for r in rows]).value_counts().to_dict()
    proj_seats = pd.Series([r["proj_winner"] for r in rows]).value_counts().to_dict()
    total_wasted = sum(r["wasted"] for r in rows)

    leading = max(proj_seats, key=proj_seats.get) if proj_seats else "—"
    leading_n = proj_seats.get(leading, 0)
    has_majority = leading_n >= MAJORITY_SEATS

    kpis = [
        _kpi("Seats Flipped", str(n_flipped), "vs Johor 2022", color="#FF7043" if n_flipped else TEXT_MUTED),
        _kpi("Leading Bloc (2026 Projected)", leading, f"{leading_n} of 56 seats", color=bloc_color(leading)),
        _kpi("Simple Majority", "✓ Reached" if has_majority else "✗ Hung", "29 seats needed",
             color="#4CAF50" if has_majority else "#E53935"),
        _kpi("Wasted Swing Votes", f"{int(total_wasted):,}",
             "swung to blocs not on the 2026 ballot in that seat"),
    ]

    all_blocs = sorted(set(list(base_seats) + list(proj_seats)), key=lambda b: -base_seats.get(b, 0))
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name="2022 Actual", x=all_blocs, y=[base_seats.get(b, 0) for b in all_blocs],
        marker_color=[bloc_color(b) for b in all_blocs], opacity=0.4,
        text=[str(base_seats.get(b, 0)) for b in all_blocs], textposition="outside",
        textfont=dict(size=11, color=TEXT_MUTED)))
    fig_bar.add_trace(go.Bar(name="2026 Projected", x=all_blocs, y=[proj_seats.get(b, 0) for b in all_blocs],
        marker_color=[bloc_color(b) for b in all_blocs], opacity=1.0,
        text=[str(proj_seats.get(b, 0)) for b in all_blocs], textposition="outside",
        textfont=dict(size=12, color=TEXT_PRIMARY)))
    fig_bar.add_hline(y=MAJORITY_SEATS, line_dash="dash", line_color="#F9A825", line_width=1.5,
        annotation=dict(text=f"Majority ({MAJORITY_SEATS})", font=dict(size=10, color="#F9A825"), xanchor="right"))
    fig_bar.update_layout(**CHART_LAYOUT,
        title=dict(text="Projected Seat Count by Bloc", font=dict(size=14, color=TEXT_PRIMARY), x=0.01),
        barmode="group", showlegend=True,
        xaxis=dict(showgrid=False, color=TEXT_MUTED),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=TEXT_MUTED), bargap=0.2,
        margin=dict(l=10, r=10, t=45, b=10))

    fig_map = make_rollup_map(rows)

    flipped_rows = [r for r in rows if r["flipped"]]
    if flipped_rows:
        tbl = pd.DataFrame([{
            "Constituency": r["seat"].upper(), "Parliament Area": str(r["parliament"]).upper(),
            "2022 Winner": r["base_winner"], "2026 Projected": r["proj_winner"],
        } for r in flipped_rows]).sort_values("Constituency")
        table = dash_table.DataTable(
            data=tbl.to_dict("records"), columns=[{"name": c, "id": c} for c in tbl.columns],
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": BG_CARD2, "color": TEXT_MUTED, "fontWeight": "600",
                          "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.06em",
                          "border": f"1px solid {BORDER}", "padding": "10px 12px"},
            style_cell={"backgroundColor": BG_CARD, "color": TEXT_PRIMARY, "border": f"1px solid {BORDER}",
                        "padding": "9px 12px", "fontSize": "13px", "fontFamily": "Inter, sans-serif", "textAlign": "left"},
            sort_action="native", page_size=20,
        )
    else:
        table = html.Div("No seats flip under current parameters.",
                          style={"color": TEXT_MUTED, "fontSize": "13px", "padding": "16px"})

    return kpis, fig_map, fig_bar, table


# ── Page layout ───────────────────────────────────────────────────────────────────

def layout():
    return html.Div([
        html.Div([
            html.Div([
                html.Span("SIMULATION", style={"background": "#FF7043", "color": "white", "borderRadius": "4px",
                          "padding": "2px 8px", "fontSize": "10px", "fontWeight": "800",
                          "letterSpacing": "0.07em", "marginRight": "10px"}),
                html.Span("Seat-by-seat swing builder, based on Johor 2022 results", style={"color": TEXT_MUTED, "fontSize": "13px"}),
            ], style={"marginBottom": "6px"}),
            html.H2("Johor 2026 Scenario Simulator", style={"color": TEXT_PRIMARY,
                "fontSize": "clamp(18px,3vw,26px)", "fontWeight": "700", "margin": "0 0 10px 0",
                "letterSpacing": "-0.02em"}),
            html.Div([
                html.Span("⚠ Disclaimer: ", style={"color": "#F9A825", "fontWeight": "700", "fontSize": "12px"}),
                html.Span(
                    "This tool redistributes Johor 2022 DUN vote counts onto the parties that actually filed "
                    "nomination for 2026 in each seat. It is a deterministic arithmetic model based on "
                    "user-defined swing assumptions, not a forecast or poll.",
                    style={"color": TEXT_MUTED, "fontSize": "12px"}),
            ], style={"background": BG_CARD2, "border": "1px solid #F9A825", "borderRadius": "8px",
                      "padding": "10px 14px", "borderLeft": "3px solid #F9A825"}),
        ], style={"background": BG_CARD, "borderBottom": f"1px solid {BORDER}", "padding": "20px 28px"}),

        dcc.Tabs(id="j26-sim-tabs", value="seat", children=[
            dcc.Tab(label="Seat Detail", value="seat", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            dcc.Tab(label="Statewide Rollup", value="state", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        ], style={"padding": "0 28px", "backgroundColor": BG_CARD, "borderBottom": f"1px solid {BORDER}"}),

        html.Div(id="j26-sim-tab-content", style={"padding": "20px 28px 28px"}),
    ], style={"background": BG_DARK, "minHeight": "100vh", "color": TEXT_PRIMARY, "fontFamily": "Inter, sans-serif"})


@callback(
    Output("j26-sim-tab-content", "children"),
    Input("j26-sim-tabs", "value"),
    Input({"type": "j26-roll-reset", "panel": ALL}, "n_clicks"),
)
def render_tab(tab, _reset_clicks):
    if tab == "state":
        return build_rollup_panel()
    opts = seat_options()
    return html.Div([
        html.Div([
            html.Div([
                html.Label("Select a DUN seat to simulate", style=_label_style()),
                dcc.Dropdown(id="j26-sim-seat", options=opts, value=opts[40]["value"] if len(opts) > 40 else None,
                             clearable=False, className="dash-dropdown-dark", style={"maxWidth": "360px"}),
            ], style={"flex": "1"}),
            html.Button("↺ Reset This Seat", id="j26-sim-seat-reset", n_clicks=0, style={
                "background": "transparent", "color": TEXT_MUTED, "border": f"1px solid {BORDER}",
                "borderRadius": "8px", "padding": "8px 14px", "cursor": "pointer", "fontSize": "12px",
                "fontFamily": "Inter", "alignSelf": "flex-end", "whiteSpace": "nowrap"}),
        ], style={"display": "flex", "gap": "16px", "alignItems": "flex-end", "marginBottom": "16px"}),
        html.Div(id="j26-sim-seat-panel"),
    ])


