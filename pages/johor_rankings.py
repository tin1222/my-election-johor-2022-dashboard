"""
pages/johor_rankings.py — Johor 2022 Rankings & Leaderboards
"""

from dash import dcc, html, Input, Output, callback, dash_table, ctx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from collections import defaultdict

from utils.johor_data import load_johor_results, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT, map_bounds_zoom
from pages.johor_map import load_geo

def coal_color(name):
    return JOHOR_COALITION_COLORS.get(str(name).upper(), "#9E9E9E")

def card_style():
    return {"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"12px","padding":"4px"}

CHART_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
)

TOP_N = 15

CATEGORIES = [
    {"value":"closest",     "emoji":"🔥","label":"Closest Races",      "desc":"Seats decided by the thinnest margins."},
    {"value":"biggest_maj", "emoji":"💪","label":"Dominant Wins",       "desc":"Landslide victories."},
    {"value":"highest_to",  "emoji":"📈","label":"Highest Turnout",     "desc":"Where voters showed up in force."},
    {"value":"lowest_to",   "emoji":"📉","label":"Lowest Turnout",      "desc":"Most disengaged constituencies."},
    {"value":"bn_strong",   "emoji":"🔵","label":"Strongest BN Seats",  "desc":"BN's dominant fortresses."},
    {"value":"ph_strong",   "emoji":"🔴","label":"Strongest PH Seats",  "desc":"PH's safest seats."},
    {"value":"pn_strong",   "emoji":"🟢","label":"Strongest PN Seats",  "desc":"PN's strongholds."},
    {"value":"largest",     "emoji":"🏙️","label":"Largest Electorates", "desc":"Biggest seats by registered voters."},
    {"value":"smallest",    "emoji":"🌾","label":"Smallest Electorates","desc":"Smallest seats."},
]

METRIC_LABELS = {
    "closest":"Winning Majority","biggest_maj":"Winning Majority",
    "highest_to":"Turnout (%)","lowest_to":"Turnout (%)",
    "bn_strong":"Winning Majority","ph_strong":"Winning Majority","pn_strong":"Winning Majority",
    "largest":"Electorate Size","smallest":"Electorate Size",
}

def _pill_bar(active_val):
    pills = []
    for cat in CATEGORIES:
        is_active = cat["value"] == active_val
        pills.append(html.Button(
            f"{cat['emoji']} {cat['label']}",
            id={"type":"jhr-rank-pill","index":cat["value"]},
            n_clicks=0,
            style={
                "background": ACCENT if is_active else BG_CARD2,
                "color": "white" if is_active else TEXT_MUTED,
                "border": f"1px solid {ACCENT if is_active else BORDER}",
                "borderRadius":"20px","padding":"6px 14px","fontSize":"12px",
                "cursor":"pointer","fontFamily":"Inter, sans-serif",
                "fontWeight":"600" if is_active else "400","whiteSpace":"nowrap",
            }
        ))
    return pills

def _mini_stat(label, value, color=ACCENT):
    return html.Div([
        html.Div(label, style={"color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
                               "letterSpacing":"0.08em","marginBottom":"4px"}),
        html.Div(str(value), style={"color":color,"fontSize":"20px","fontWeight":"700",
                                    "letterSpacing":"-0.02em","lineHeight":"1.1"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px","padding":"13px 15px"})

def _ranked(category):
    df = load_johor_results()
    n = TOP_N
    configs = {
        "closest":     (df,"WINNING MAJORITY","nsmallest","{:,} votes"),
        "biggest_maj": (df,"WINNING MAJORITY","nlargest", "{:,} votes"),
        "highest_to":  (df,"TURNOUT (%)","nlargest",      "{:.1f}%"),
        "lowest_to":   (df,"TURNOUT (%)","nsmallest",     "{:.1f}%"),
        "largest":     (df,"TOTAL ELECTORATE","nlargest", "{:,}"),
        "smallest":    (df,"TOTAL ELECTORATE","nsmallest","{:,}"),
    }
    coal_configs = {"bn_strong":"BN","ph_strong":"PH","pn_strong":"PN"}

    if category in configs:
        base_df, col, method, fmt = configs[category]
        sub = getattr(base_df, method)(n, col).copy()
        sub["_METRIC"] = sub[col]
        sub["_METRIC_LABEL"] = sub[col].apply(
            lambda x: fmt.format(x) if "%" in fmt else fmt.format(int(x))
        )
    elif category in coal_configs:
        coal = coal_configs[category]
        sub = df[df["COALITION"]==coal].nlargest(n,"WINNING MAJORITY").copy()
        sub["_METRIC"] = sub["WINNING MAJORITY"]
        sub["_METRIC_LABEL"] = sub["WINNING MAJORITY"].apply(lambda x: f"{int(x):,} votes")
    else:
        sub = df.nsmallest(n,"WINNING MAJORITY").copy()
        sub["_METRIC"] = sub["WINNING MAJORITY"]
        sub["_METRIC_LABEL"] = sub["WINNING MAJORITY"].apply(lambda x: f"{int(x):,} votes")

    sub = sub.reset_index(drop=True)
    sub["RANK"] = sub.index + 1
    cat_obj = next(c for c in CATEGORIES if c["value"]==category)
    return sub, f"{cat_obj['emoji']} {cat_obj['label']} — Top {len(sub)}"

def layout():
    return html.Div([
        html.Div([
            html.Div([
                html.Span("RANKINGS", style={"background":"#F9A825","color":"#0D0F14",
                          "borderRadius":"4px","padding":"2px 8px","fontSize":"10px",
                          "fontWeight":"800","letterSpacing":"0.07em","marginRight":"10px"}),
                html.Span("Johor 2022 Leaderboards", style={"color":TEXT_MUTED,"fontSize":"13px"}),
            ], style={"marginBottom":"6px"}),
            html.H2("Johor State Election Leaderboards", style={
                "color":TEXT_PRIMARY,"fontSize":"clamp(18px,3vw,26px)",
                "fontWeight":"700","margin":"0 0 5px 0","letterSpacing":"-0.02em"}),
            html.Div("From razor-thin margins to landslide victories — every extreme, ranked.",
                     style={"color":TEXT_MUTED,"fontSize":"13px"}),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        html.Div([
            html.Div("Choose a leaderboard:", style={"color":TEXT_MUTED,"fontSize":"11px",
                "textTransform":"uppercase","letterSpacing":"0.07em","marginBottom":"10px"}),
            html.Div(id="jhr-rank-pill-bar", children=_pill_bar("closest"),
                     style={"display":"flex","gap":"8px","flexWrap":"wrap"}),
        ], style={"padding":"18px 28px 0"}),

        html.Div(id="jhr-rank-desc",
                 style={"padding":"8px 28px 0","color":TEXT_MUTED,"fontSize":"13px","fontStyle":"italic"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-rank-chart",config={"displayModeBar":False},
                                style={"height":"480px"})],
                     style={"flex":"3","minWidth":"340px",**card_style()}),
            html.Div(id="jhr-rank-side-stats",
                     style={"flex":"1","minWidth":"200px","display":"flex",
                            "flexDirection":"column","gap":"10px"}),
        ], style={"display":"flex","gap":"16px","padding":"14px 28px","flexWrap":"wrap"}),

        html.Div([
            html.Div([
                html.Div(id="jhr-rank-tbl-title", style={"color":TEXT_MUTED,"fontSize":"11px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","padding":"14px 16px 8px"}),
                html.Div(id="jhr-rank-tbl"),
            ], style=card_style()),
        ], style={"padding":"0 28px 16px"}),

        # Map of ranked seats
        html.Div([
            html.Div([
                html.Div(id="jhr-rank-map-title", style={"color":TEXT_MUTED,"fontSize":"11px",
                    "textTransform":"uppercase","letterSpacing":"0.07em","padding":"14px 16px 8px"}),
                dcc.Graph(id="jhr-rank-map", config={"displayModeBar":True,
                                                      "modeBarButtonsToRemove":["lasso2d","select2d"],
                                                      "displaylogo":False},
                          style={"height":"520px"}),
            ], style=card_style()),
        ], style={"padding":"0 28px 28px"}),
    ])

def make_rank_map(display, title):
    geo = load_geo()
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

    code_to_row = {row["UNIQUE CODE"]: row for _, row in display.iterrows()}
    highlight_codes = set(code_to_row.keys())

    other_feats = [f for f in geo["features"]
                   if f["properties"]["UNIQUE_ID"] not in highlight_codes]
    hl_feats    = [f for f in geo["features"]
                   if f["properties"]["UNIQUE_ID"] in highlight_codes]

    fig = go.Figure()

    coal_groups = defaultdict(list)
    for feat in hl_feats:
        row = code_to_row[feat["properties"]["UNIQUE_ID"]]
        coal_groups[row["COALITION"]].append((feat, row))

    for coal, items in sorted(coal_groups.items(), key=lambda x: -len(x[1])):
        sub_feats = [item[0] for item in items]
        sub_geo   = {"type": "FeatureCollection", "features": sub_feats}
        hover_texts = [
            f"<b>#{int(row['RANK'])} — {row['STATE CONSTITUENCY NAME'].title()}</b><br>"
            f"({row['PARLIAMENTARY NAME'].title()})<br>"
            f"Coalition: <b style='color:{coal_color(coal)}'>{coal}</b><br>"
            f"Party: {row['WINNING PARTY']}<br>"
            f"{row['_METRIC_LABEL']}<br>"
            f"Turnout: {row['TURNOUT (%)']:.1f}%"
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
            marker=dict(opacity=0.95, line=dict(color="#FFFFFF", width=1.5)),
            showlegend=True,
        ))

    if other_feats:
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": other_feats},
            locations=[f["id"] for f in other_feats],
            z=[0] * len(other_feats),
            colorscale=[[0, BORDER], [1, BORDER]],
            showscale=False,
            name="Other seats",
            hoverinfo="skip",
            marker=dict(opacity=0.3, line=dict(color="#1a1a2e", width=0.3)),
            showlegend=True,
        ))

    lat_c, lon_c, zoom = map_bounds_zoom(hl_feats)
    fig.update_layout(
        map=dict(style="dark", center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXT_PRIMARY, size=11),
        title=dict(text=title, font=dict(size=13, color=TEXT_PRIMARY), x=0.01),
        legend=dict(bgcolor=BG_CARD, bordercolor=BORDER, borderwidth=1,
                    font=dict(color=TEXT_MUTED, size=11),
                    title=dict(text="Coalition", font=dict(color=TEXT_PRIMARY, size=12)),
                    x=0.01, y=0.99, xanchor="left", yanchor="top"),
        margin=dict(l=0, r=0, t=35, b=0),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER,
                        font=dict(family="Inter", color=TEXT_PRIMARY, size=12)),
    )
    return fig


@callback(
    Output("jhr-rank-pill-bar","children"),
    Output("jhr-rank-desc","children"),
    Output("jhr-rank-chart","figure"),
    Output("jhr-rank-side-stats","children"),
    Output("jhr-rank-tbl-title","children"),
    Output("jhr-rank-tbl","children"),
    Output("jhr-rank-map-title","children"),
    Output("jhr-rank-map","figure"),
    [Input({"type":"jhr-rank-pill","index":cat["value"]},"n_clicks") for cat in CATEGORIES],
)
def update_rankings(*_):
    triggered = ctx.triggered_id
    category = triggered["index"] if triggered and isinstance(triggered, dict) else "closest"
    sub, title = _ranked(category)
    cat_obj = next(c for c in CATEGORIES if c["value"]==category)

    asc = category in ("lowest_to","smallest","closest")
    display = sub.sort_values("_METRIC", ascending=not asc).tail(15)

    def _trunc(name, n=26): return name if len(name)<=n else name[:n-1]+"…"
    labels = display["STATE CONSTITUENCY NAME"].str.title().apply(_trunc) + \
             " (P." + display["PARLIAMENTARY CODE"].str.replace("P. ","") + ")"
    colors = [coal_color(c) for c in display["COALITION"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=display["_METRIC"], y=labels, orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)")),
        text=display["_METRIC_LABEL"], textposition="outside",
        textfont=dict(size=10, color=TEXT_PRIMARY),
        customdata=np.stack([display["WINNING PARTY"].fillna("—"),
                             display["TURNOUT (%)"].fillna(0),
                             display["WINNING MAJORITY"].fillna(0)], axis=-1),
        hovertemplate="<b>%{y}</b><br>Party: %{customdata[0]}<br>Value: %{x:,.0f}<br>"
                      "Turnout: %{customdata[1]:.1f}%<br>Majority: %{customdata[2]:,.0f}<extra></extra>",
        showlegend=False,
    ))
    seen = set()
    for _, row in display.iterrows():
        c = row["COALITION"]
        if c not in seen:
            seen.add(c)
            fig.add_trace(go.Bar(x=[None],y=[None],name=c,marker_color=coal_color(c),showlegend=True))

    fig.update_layout(**CHART_LAYOUT_BASE,
        title=dict(text=title, font=dict(size=14,color=TEXT_PRIMARY), x=0.01),
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color=TEXT_MUTED,size=11),
                    orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        xaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,tickformat=","),
        yaxis=dict(showgrid=False,color=TEXT_MUTED,tickfont=dict(size=10)),
        bargap=0.18, margin=dict(l=10,r=90,t=55,b=10))

    top1 = sub.iloc[0]
    coal_counts = sub["COALITION"].value_counts()
    dom_coal = coal_counts.index[0] if len(coal_counts) else "—"
    side = [
        _mini_stat("#1 Seat", top1["STATE CONSTITUENCY NAME"].title(), color=coal_color(top1["COALITION"])),
        _mini_stat("Seats shown", str(len(sub))),
        _mini_stat("Top Coalition", dom_coal, color=coal_color(dom_coal)),
        _mini_stat("Avg Turnout", f"{sub['TURNOUT (%)'].mean():.1f}%", color="#4CAF50"),
        _mini_stat("Avg Majority", f"{int(sub['WINNING MAJORITY'].mean()):,}", color="#F9A825"),
    ]

    metric_label = METRIC_LABELS.get(category, "Value")
    tbl = sub[["RANK","STATE CONSTITUENCY NAME","PARLIAMENTARY NAME",
               "WINNING PARTY","_METRIC_LABEL","TURNOUT (%)"]].copy()
    tbl["TURNOUT (%)"] = pd.to_numeric(tbl["TURNOUT (%)"], errors="coerce").apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    tbl.columns = ["#","Constituency","Parliament Area","Winning Party", metric_label,"Turnout (%)"]
    tbl["Constituency"]    = tbl["Constituency"].str.title()
    tbl["Parliament Area"] = tbl["Parliament Area"].str.title()

    style_cond = [
        {"if":{"filter_query":f'{{Winning Party}} contains "{c}"'},
         "borderLeft":f"3px solid {col}"}
        for c, col in JOHOR_COALITION_COLORS.items()
    ]

    table = dash_table.DataTable(
        data=tbl.to_dict("records"),
        columns=[{"name":c,"id":c} for c in tbl.columns],
        style_table={"overflowX":"auto"},
        style_header={"backgroundColor":BG_CARD2,"color":TEXT_MUTED,"fontWeight":"600",
                      "fontSize":"11px","textTransform":"uppercase","letterSpacing":"0.06em",
                      "border":f"1px solid {BORDER}","padding":"10px 12px"},
        style_cell={"backgroundColor":BG_CARD,"color":TEXT_PRIMARY,"border":f"1px solid {BORDER}",
                    "padding":"9px 12px","fontSize":"13px","fontFamily":"Inter, sans-serif",
                    "textAlign":"left","minWidth":"80px","whiteSpace":"normal"},
        style_cell_conditional=[{"if":{"column_id":"#"},"width":"40px","textAlign":"center",
                                  "color":TEXT_MUTED,"fontSize":"11px"}],
        style_data_conditional=style_cond,
        page_size=20, sort_action="native",
    )

    map_title = f"Map — {title} (Top {len(display)})"
    fig_map = make_rank_map(display, map_title)

    return (_pill_bar(category), cat_obj["desc"], fig, side,
            f"Full list — {title}", table, map_title, fig_map)
