"""
pages/johor_overview.py — Johor 2022 State Election Overview
"""

from dash import dcc, html, Input, Output, callback, ctx, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils.johor_data import load_johor_results, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT

def coal_color(name):
    return JOHOR_COALITION_COLORS.get(str(name).upper(), "#9E9E9E")

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
)

def card_style():
    return {"background": BG_CARD, "border": f"1px solid {BORDER}",
            "borderRadius": "12px", "padding": "4px"}

# ── Chart helpers ─────────────────────────────────────────────────────────────

def get_seats(df):     return df.groupby("COALITION").size().reset_index(name="SEATS")
def get_votes(df):
    vote_map = {"BN":"BN VOTE","PH":"PH VOTE","PN":"PN VOTE","PEJUANG":"PEJUANG VOTE"}
    rows = []; total = df["TOTAL VALID VOTES"].sum()
    for c, col in vote_map.items():
        if col in df.columns:
            v = df[col].sum()
            rows.append({"COALITION":c,"VOTES":v,"VOTE_SHARE":(v/total*100) if total>0 else 0})
    others = df["OTHERS VOTE"].sum() if "OTHERS VOTE" in df.columns else 0
    rows.append({"COALITION":"OTHERS","VOTES":others,"VOTE_SHARE":(others/total*100) if total>0 else 0})
    return pd.DataFrame(rows).sort_values("VOTES", ascending=False)

def make_seats_bar(df_seats):
    df = df_seats.sort_values("SEATS", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["SEATS"], y=df["COALITION"], orientation="h",
        marker_color=[coal_color(c) for c in df["COALITION"]],
        marker_line_color="rgba(0,0,0,0)",
        text=[str(int(v)) for v in df["SEATS"]],
        textposition="outside", textfont=dict(size=12, color=TEXT_PRIMARY),
        hovertemplate="<b>%{y}</b><br>Seats: %{x}<extra></extra>",
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Seats Won by Coalition", font=dict(size=14,color=TEXT_PRIMARY), x=0.01),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, color=TEXT_MUTED),
        yaxis=dict(showgrid=False, color=TEXT_MUTED, tickfont=dict(size=12)),
        bargap=0.3, margin=dict(l=10,r=50,t=45,b=10))
    return fig

def make_votes_donut(df_votes):
    df = df_votes[df_votes["VOTES"] > 0]
    total = int(df["VOTES"].sum())
    fig = go.Figure(go.Pie(
        labels=df["COALITION"].tolist(), values=df["VOTE_SHARE"].tolist(), hole=0.60,
        marker=dict(colors=[coal_color(c) for c in df["COALITION"]], line=dict(color=BG_DARK,width=2)),
        textinfo="label+percent", textfont=dict(size=11, color=TEXT_PRIMARY),
        hovertemplate="<b>%{label}</b><br>Vote Share: %{percent}<br>Votes: %{customdata:,}<extra></extra>",
        customdata=df["VOTES"].astype(int).tolist(),
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Popular Vote Share", font=dict(size=14,color=TEXT_PRIMARY), x=0.01),
        showlegend=True,
        annotations=[dict(text=f"<b>{total:,}</b><br><span style='font-size:10px'>total votes</span>",
                          x=0.5, y=0.5, font_size=15, showarrow=False, font_color=TEXT_PRIMARY)],
        margin=dict(l=10,r=10,t=45,b=10))
    return fig

def make_turnout_bar(df):
    df2 = df.groupby("STATE CONSTITUENCY NAME").agg(
        AVG_TURNOUT=("TURNOUT (%)","mean")
    ).reset_index().sort_values("AVG_TURNOUT", ascending=True)
    colors = ["#E53935" if v<55 else ("#F9A825" if v<63 else ACCENT) for v in df2["AVG_TURNOUT"]]

    # Full height for all bars — container handles scrolling
    full_h = max(400, len(df2) * 28)

    fig = go.Figure(go.Bar(
        x=df2["AVG_TURNOUT"],
        y=df2["STATE CONSTITUENCY NAME"].str.title(),
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)")),
        text=[f"{v:.1f}%" for v in df2["AVG_TURNOUT"]],
        textposition="outside", textfont=dict(size=9, color=TEXT_PRIMARY),
        hovertemplate="<b>%{y}</b><br>Turnout: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Voter Turnout by Constituency", font=dict(size=14,color=TEXT_PRIMARY), x=0.01),
        xaxis=dict(range=[35,75], showgrid=True, gridcolor=BORDER, zeroline=False,
                   color=TEXT_MUTED, ticksuffix="%"),
        yaxis=dict(showgrid=False, color=TEXT_MUTED, tickfont=dict(size=9)),
        bargap=0.15, margin=dict(l=10,r=70,t=45,b=10), height=full_h)
    fig.update_yaxes(type='category')
    return fig

def make_coalition_heatmap(df):
    pivot = df.groupby(["PARLIAMENTARY NAME","COALITION"]).size().reset_index(name="SEATS")
    pivot = pivot.pivot_table(index="PARLIAMENTARY NAME", columns="COALITION", values="SEATS", fill_value=0)
    pivot.index = pivot.index.str.title()
    z = pivot.values.astype(int)
    text = [[str(int(v)) if v>0 else "" for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        text=text, texttemplate="%{text}", textfont=dict(size=11, color="white"),
        colorscale=[[0,BG_CARD2],[0.01,"#A8D4FF"],[0.3,"#4F8EF7"],[0.6,"#1565C0"],[1.0,"#1a3a5c"]],
        showscale=False,
        hovertemplate="<b>%{y}</b> — <b>%{x}</b><br>Seats: %{z}<extra></extra>",
    ))
    fig.update_layout(**CHART_LAYOUT,
        title=dict(text="Seats per Coalition × Parliament Area", font=dict(size=14,color=TEXT_PRIMARY), x=0.01),
        xaxis=dict(showgrid=False, color=TEXT_MUTED, tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, color=TEXT_MUTED, tickfont=dict(size=9), autorange="reversed"),
        showlegend=False, margin=dict(l=10,r=10,t=45,b=10))
    return fig

def kpi_card(title, value, subtitle=None, color=ACCENT):
    return html.Div([
        html.Div(title, style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                               "letterSpacing":"0.08em","marginBottom":"6px"}),
        html.Div(value, style={"color":color,"fontSize":"28px","fontWeight":"700",
                               "lineHeight":"1.1","letterSpacing":"-0.02em"}),
        html.Div(subtitle or "", style={"color":TEXT_MUTED,"fontSize":"11px","marginTop":"4px"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px",
              "padding":"18px 20px","flex":"1","minWidth":"130px"})

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    df = load_johor_results()
    coals = sorted([c for c in df["COALITION"].unique() if c not in ("OTHERS","INDEPENDENT")])
    coals += ["OTHERS","INDEPENDENT"]
    seat_opts = [{"label":s.title(),"value":s} for s in sorted(df["STATE CONSTITUENCY NAME"].unique())]
    coal_opts = [{"label":c,"value":c} for c in coals]

    return html.Div([
        html.Div([
            html.H1("Johor 2022 State Election Results", style={
                "color":TEXT_PRIMARY,"fontSize":"clamp(18px,3vw,28px)","fontWeight":"700",
                "margin":"0 0 4px 0","letterSpacing":"-0.02em"}),
            html.Div("56 State Seats (DUN) · 12 March 2022",
                     style={"color":TEXT_MUTED,"fontSize":"13px"}),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        # Filters
        html.Div([html.Div([
            html.Div([
                html.Label("Constituency", style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                                                   "letterSpacing":"0.07em","marginBottom":"4px","display":"block"}),
                dcc.Dropdown(id="jhr-filter-seat", options=seat_opts, multi=True,
                             placeholder="All Constituencies", className="dash-dropdown-dark"),
            ], style={"flex":"2","minWidth":"180px"}),
            html.Div([
                html.Label("Coalition", style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                                               "letterSpacing":"0.07em","marginBottom":"4px","display":"block"}),
                dcc.Dropdown(id="jhr-filter-coal", options=coal_opts, multi=True,
                             placeholder="All Coalitions", className="dash-dropdown-dark"),
            ], style={"flex":"2","minWidth":"140px"}),
            html.Div([
                html.Label("Turnout Range", style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                                                    "letterSpacing":"0.07em","marginBottom":"4px","display":"block"}),
                html.Div("Shows only DUN seats whose voter turnout falls within this range.",
                         style={"color":TEXT_MUTED,"fontSize":"11px","fontStyle":"italic","marginBottom":"6px"}),
                html.Div([
                    dcc.Input(id="jhr-filter-turnout-min", type="number", value=0, min=0, max=100, step=1,
                              style={"background":BG_CARD2,"border":f"1px solid {BORDER}",
                                     "color":TEXT_PRIMARY,"borderRadius":"6px","padding":"5px 6px",
                                     "width":"56px","fontFamily":"Inter","fontSize":"12px"}),
                    html.Span("–", style={"color":TEXT_MUTED}),
                    dcc.Input(id="jhr-filter-turnout-max", type="number", value=100, min=0, max=100, step=1,
                              style={"background":BG_CARD2,"border":f"1px solid {BORDER}",
                                     "color":TEXT_PRIMARY,"borderRadius":"6px","padding":"5px 6px",
                                     "width":"56px","fontFamily":"Inter","fontSize":"12px"}),
                    html.Span("%", style={"color":TEXT_MUTED,"fontSize":"12px"}),
                ], style={"display":"flex","gap":"6px","alignItems":"center","marginBottom":"8px"}),
                dcc.RangeSlider(id="jhr-filter-turnout", min=0, max=100, step=1, value=[0,100],
                    marks={0:{"label":"0%","style":{"color":TEXT_MUTED}},
                           50:{"label":"50%","style":{"color":TEXT_MUTED}},
                           100:{"label":"100%","style":{"color":TEXT_MUTED}}},
                    tooltip={"placement":"bottom","always_visible":False}),
            ], style={"flex":"3","minWidth":"220px","paddingTop":"4px"}),
            html.Button("↺ Reset", id="jhr-btn-reset", style={
                "background":"transparent","border":f"1px solid {BORDER}","color":TEXT_MUTED,
                "borderRadius":"6px","padding":"8px 16px","cursor":"pointer","fontSize":"12px",
                "fontFamily":"Inter","alignSelf":"flex-end","whiteSpace":"nowrap"}),
        ], style={"display":"flex","gap":"20px","alignItems":"flex-start","flexWrap":"wrap"})],
        style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"14px 28px",
               "position":"sticky","top":"52px","zIndex":"100"}),

        html.Div(id="jhr-kpi-strip",
                 style={"display":"flex","gap":"12px","flexWrap":"wrap","padding":"20px 28px 0"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-chart-seats",config={"displayModeBar":False},style={"height":"320px"})],
                     style={"flex":"1","minWidth":"280px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-chart-votes",config={"displayModeBar":False},style={"height":"320px"})],
                     style={"flex":"1","minWidth":"280px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"20px 28px","flexWrap":"wrap"}),

html.Div([
            html.Div([
                html.Div(
                    dcc.Graph(id="jhr-chart-turnout", config={"displayModeBar":False}),
                    style={
                        "height": "560px",
                        "overflowY": "auto",
                        "overflowX": "hidden",
                    }
                )
            ], style={"flex":"1","minWidth":"300px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-chart-heatmap",config={"displayModeBar":False},style={"height":"600px"})],
                     style={"flex":"2","minWidth":"360px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"0 28px 28px","flexWrap":"wrap"}),
    ])

# ── Callbacks ─────────────────────────────────────────────────────────────────

def _filter(seats, coals, turnout_range):
    df = load_johor_results()
    if seats:  df = df[df["STATE CONSTITUENCY NAME"].isin(seats)]
    if coals:  df = df[df["COALITION"].isin(coals)]
    if turnout_range:
        df = df[(df["TURNOUT (%)"]>=turnout_range[0]) & (df["TURNOUT (%)"]<=turnout_range[1])]
    return df

JHR_TURNOUT_MIN, JHR_TURNOUT_MAX = 0, 100

@callback(
    Output("jhr-filter-seat","value"), Output("jhr-filter-coal","value"),
    Output("jhr-filter-turnout","value"),
    Output("jhr-filter-turnout-min","value"),
    Output("jhr-filter-turnout-max","value"),
    Input("jhr-btn-reset","n_clicks"),
    Input("jhr-filter-turnout","value"),
    Input("jhr-filter-turnout-min","value"),
    Input("jhr-filter-turnout-max","value"),
    prevent_initial_call=True,
)
def sync_filters(_, slider_val, min_val, max_val):
    trig = ctx.triggered_id
    if trig == "jhr-btn-reset":
        return None, None, [JHR_TURNOUT_MIN, JHR_TURNOUT_MAX], JHR_TURNOUT_MIN, JHR_TURNOUT_MAX

    lo, hi = slider_val if slider_val else [JHR_TURNOUT_MIN, JHR_TURNOUT_MAX]
    if trig == "jhr-filter-turnout-min" and min_val is not None:
        lo = min_val
    elif trig == "jhr-filter-turnout-max" and max_val is not None:
        hi = max_val

    lo = max(JHR_TURNOUT_MIN, min(lo, JHR_TURNOUT_MAX))
    hi = max(JHR_TURNOUT_MIN, min(hi, JHR_TURNOUT_MAX))
    if lo > hi:
        lo, hi = hi, lo

    return no_update, no_update, [lo, hi], lo, hi

@callback(
    Output("jhr-kpi-strip","children"),
    Output("jhr-chart-seats","figure"), Output("jhr-chart-votes","figure"),
    Output("jhr-chart-turnout","figure"), Output("jhr-chart-heatmap","figure"),
    Input("jhr-filter-seat","value"), Input("jhr-filter-coal","value"),
    Input("jhr-filter-turnout","value"),
)
def update(seats, coals, turnout_range):
    df = _filter(seats, coals, turnout_range)
    total = len(df)
    avg_to = df["TURNOUT (%)"].mean()
    total_votes = df["TOTAL VALID VOTES"].sum()
    seats_by_c  = df.groupby("COALITION").size()
    top_coal    = seats_by_c.idxmax() if len(seats_by_c) else "—"
    top_n       = seats_by_c.max()   if len(seats_by_c) else 0
    med_maj     = df[df["WINNING MAJORITY"]>0]["WINNING MAJORITY"].median()

    kpis = [
        kpi_card("Constituencies", str(total), "shown"),
        kpi_card("Avg Turnout", f"{avg_to:.1f}%", "voter participation", color="#4CAF50"),
        kpi_card("Total Valid Votes", f"{int(total_votes):,}", "across selection"),
        kpi_card("Leading Coalition", top_coal, f"{top_n} seats", color=coal_color(top_coal)),
        kpi_card("Median Majority",
                 f"{int(med_maj):,}" if not np.isnan(med_maj) else "—", "winning margin"),
    ]

    df_votes_base = _filter(seats, None, turnout_range)
    return (kpis,
            make_seats_bar(get_seats(df)),
            make_votes_donut(get_votes(df_votes_base)),
            make_turnout_bar(df),
            make_coalition_heatmap(df))
