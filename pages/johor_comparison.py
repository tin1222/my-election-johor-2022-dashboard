"""
pages/johor_comparison.py — Johor 2022 Constituency Comparison
"""

from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils.johor_data import load_johor_results, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT

def coal_color(n): return JOHOR_COALITION_COLORS.get(str(n).upper(), "#9E9E9E")
def card_style():   return {"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"12px","padding":"4px"}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
)

COLOR_A, COLOR_B = ACCENT, "#FF7043"

def layout():
    df = load_johor_results()
    seats = sorted(df["STATE CONSTITUENCY NAME"].dropna().unique())
    opts  = [{"label":s.title(),"value":s} for s in seats]
    defaults = [seats[0], seats[1]] if len(seats)>1 else [seats[0], seats[0]]

    return html.Div([
        html.Div([
            html.Div([
                html.Span("COMPARE", style={"background":COLOR_A,"color":"white","borderRadius":"4px",
                          "padding":"2px 8px","fontSize":"10px","fontWeight":"700",
                          "letterSpacing":"0.07em","marginRight":"10px"}),
                html.Span("Johor DUN side-by-side", style={"color":TEXT_MUTED,"fontSize":"13px"}),
            ], style={"marginBottom":"6px"}),
            html.H2("Constituency Comparison", style={"color":TEXT_PRIMARY,"fontSize":"clamp(18px,3vw,26px)",
                "fontWeight":"700","margin":"0 0 5px 0","letterSpacing":"-0.02em"}),
            html.Div("Compare vote breakdowns, turnout, majority and electorate size for any two DUN seats.",
                     style={"color":TEXT_MUTED,"fontSize":"13px"}),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        html.Div([
            html.Div([
                _picker("Constituency A","jhr-cmp-a",opts,defaults[0],COLOR_A),
                _picker("Constituency B","jhr-cmp-b",opts,defaults[1],COLOR_B),
            ], style={"display":"flex","gap":"16px","flexWrap":"wrap"}),
        ], style={"padding":"20px 28px 0"}),

        html.Div(id="jhr-cmp-cards",
                 style={"display":"flex","gap":"12px","flexWrap":"wrap","padding":"16px 28px 0"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-cmp-votes",config={"displayModeBar":False},style={"height":"320px"})],
                     style={"flex":"2","minWidth":"340px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-cmp-turnout",config={"displayModeBar":False},style={"height":"320px"})],
                     style={"flex":"1","minWidth":"260px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"16px 28px","flexWrap":"wrap"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-cmp-majority",config={"displayModeBar":False},style={"height":"260px"})],
                     style={"flex":"1","minWidth":"300px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-cmp-electorate",config={"displayModeBar":False},style={"height":"260px"})],
                     style={"flex":"1","minWidth":"300px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"0 28px 28px","flexWrap":"wrap"}),
    ])

def _picker(label, id_, opts, default, dot_color):
    return html.Div([
        html.Div([
            html.Span(style={"width":"9px","height":"9px","borderRadius":"50%",
                             "background":dot_color,"display":"inline-block","marginRight":"7px"}),
            html.Label(label, style={"color":TEXT_MUTED,"fontSize":"11px",
                                     "textTransform":"uppercase","letterSpacing":"0.07em","verticalAlign":"middle"}),
        ], style={"marginBottom":"6px"}),
        dcc.Dropdown(id=id_, options=opts, value=default, clearable=False,
                     className="dash-dropdown-dark", style={"minWidth":"250px"}),
    ], style={"flex":"1","minWidth":"240px"})

def _stat_card(label, va, vb):
    def fmt(v): return "—" if v is None or (isinstance(v,float) and pd.isna(v)) else str(v)
    return html.Div([
        html.Div(label, style={"color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
                               "letterSpacing":"0.08em","marginBottom":"8px"}),
        html.Div([
            html.Div([html.Div("A",style={"color":COLOR_A,"fontSize":"9px","fontWeight":"700","marginBottom":"2px"}),
                      html.Div(fmt(va),style={"color":TEXT_PRIMARY,"fontSize":"15px","fontWeight":"700"})]),
            html.Div(style={"width":"1px","background":BORDER,"margin":"0 10px","alignSelf":"stretch"}),
            html.Div([html.Div("B",style={"color":COLOR_B,"fontSize":"9px","fontWeight":"700","marginBottom":"2px"}),
                      html.Div(fmt(vb),style={"color":TEXT_PRIMARY,"fontSize":"15px","fontWeight":"700"})]),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px",
              "padding":"13px 16px","flex":"1","minWidth":"130px"})

def _get_votes(row):
    cols = {"BN":"BN VOTE","PH":"PH VOTE","PN":"PN VOTE","PEJUANG":"PEJUANG VOTE"}
    out = {}
    for c, col in cols.items():
        v = row.get(col,0)
        if pd.notna(v) and v>0: out[c] = int(v)
    others = row.get("OTHERS VOTE",0)
    if pd.notna(others) and others>0: out["OTHERS"] = int(others)
    return out

@callback(
    Output("jhr-cmp-cards","children"),
    Output("jhr-cmp-votes","figure"),
    Output("jhr-cmp-turnout","figure"),
    Output("jhr-cmp-majority","figure"),
    Output("jhr-cmp-electorate","figure"),
    Input("jhr-cmp-a","value"), Input("jhr-cmp-b","value"),
)
def update(sa, sb):
    df = load_johor_results()
    def get_row(name):
        r = df[df["STATE CONSTITUENCY NAME"]==name]
        return r.iloc[0] if len(r) else None
    ra, rb = get_row(sa), get_row(sb)
    empty = go.Figure()
    if ra is None or rb is None: return [], empty, empty, empty, empty

    na = ra["STATE CONSTITUENCY NAME"].title()
    nb = rb["STATE CONSTITUENCY NAME"].title()
    def pct(v): return f"{v:.1f}%" if pd.notna(v) else "—"
    def num(v): return f"{int(v):,}" if pd.notna(v) else "—"

    cards = [
        _stat_card("Parliament Area", ra["PARLIAMENTARY NAME"].title(), rb["PARLIAMENTARY NAME"].title()),
        _stat_card("Coalition",       ra["COALITION"],                  rb["COALITION"]),
        _stat_card("Winning Party",   ra["WINNING PARTY"],              rb["WINNING PARTY"]),
        _stat_card("Turnout",         pct(ra["TURNOUT (%)"]),           pct(rb["TURNOUT (%)"])),
        _stat_card("Winning Majority",num(ra["WINNING MAJORITY"]),      num(rb["WINNING MAJORITY"])),
        _stat_card("Majority %",      pct(ra["MAJORITY_PCT"]),          pct(rb["MAJORITY_PCT"])),
        _stat_card("Electorate",      num(ra["TOTAL ELECTORATE"]),      num(rb["TOTAL ELECTORATE"])),
    ]

    vda, vdb = _get_votes(ra), _get_votes(rb)
    coalitions = sorted(set(list(vda)+list(vdb)))
    fig_votes = go.Figure()
    for name_s, vd, color in [(na,vda,COLOR_A),(nb,vdb,COLOR_B)]:
        fig_votes.add_trace(go.Bar(
            name=name_s, x=coalitions, y=[vd.get(c,0) for c in coalitions],
            marker_color=color, opacity=0.9,
            text=[f"{vd.get(c,0):,}" if vd.get(c,0) else "" for c in coalitions],
            textposition="outside", textfont=dict(size=10,color=TEXT_PRIMARY),
            hovertemplate=f"<b>{name_s}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
        ))
    fig_votes.update_layout(**CHART_LAYOUT,
        title=dict(text="Vote Breakdown by Coalition",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        barmode="group",showlegend=True,
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,tickformat=","),
        bargap=0.15)

    to_a = float(ra["TURNOUT (%)"]) if pd.notna(ra["TURNOUT (%)"]) else 0
    to_b = float(rb["TURNOUT (%)"]) if pd.notna(rb["TURNOUT (%)"]) else 0
    nat_avg = load_johor_results()["TURNOUT (%)"].mean()
    fig_to = go.Figure()
    for name_s, val, color in [(na,to_a,COLOR_A),(nb,to_b,COLOR_B)]:
        fig_to.add_trace(go.Bar(x=[val],y=[name_s],orientation="h",marker_color=color,
            text=[f"  {val:.1f}%"],textposition="outside",textfont=dict(size=13,color=TEXT_PRIMARY),
            hovertemplate=f"<b>{name_s}</b><br>Turnout: {val:.1f}%<extra></extra>",showlegend=False))
    fig_to.add_vline(x=nat_avg,line_dash="dash",line_color=TEXT_MUTED,line_width=1.5,
        annotation=dict(text=f"Avg {nat_avg:.1f}%",font=dict(size=10,color=TEXT_MUTED),xanchor="left"))
    fig_to.update_layout(**CHART_LAYOUT,
        title=dict(text="Voter Turnout",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        xaxis=dict(range=[30,75],ticksuffix="%",color=TEXT_MUTED,showgrid=True,gridcolor=BORDER),
        yaxis=dict(showgrid=False,color=TEXT_MUTED),bargap=0.45,margin=dict(l=10,r=65,t=45,b=10))

    maj_a = float(ra["WINNING MAJORITY"]) if pd.notna(ra["WINNING MAJORITY"]) else 0
    maj_b = float(rb["WINNING MAJORITY"]) if pd.notna(rb["WINNING MAJORITY"]) else 0
    pct_a = float(ra["MAJORITY_PCT"])     if pd.notna(ra["MAJORITY_PCT"])     else 0
    pct_b = float(rb["MAJORITY_PCT"])     if pd.notna(rb["MAJORITY_PCT"])     else 0
    na_s = na if len(na)<=22 else na[:21]+"…"
    nb_s = nb if len(nb)<=22 else nb[:21]+"…"
    fig_maj = go.Figure(go.Bar(
        x=[na_s,nb_s],y=[maj_a,maj_b],marker_color=[COLOR_A,COLOR_B],
        text=[f"{int(maj_a):,} ({pct_a:.1f}%)",f"{int(maj_b):,} ({pct_b:.1f}%)"],
        textposition="outside",textfont=dict(size=11,color=TEXT_PRIMARY),
        hovertemplate="<b>%{x}</b><br>Majority: %{y:,}<extra></extra>",showlegend=False))
    fig_maj.update_layout(**CHART_LAYOUT,
        title=dict(text="Winning Majority",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,
                   tickformat=",",range=[0,max(maj_a,maj_b)*1.3]),
        bargap=0.45)

    elec_a = float(ra["TOTAL ELECTORATE"]) if pd.notna(ra["TOTAL ELECTORATE"]) else 0
    cast_a = float(ra["TOTAL VALID VOTES"]) if pd.notna(ra["TOTAL VALID VOTES"]) else 0
    elec_b = float(rb["TOTAL ELECTORATE"]) if pd.notna(rb["TOTAL ELECTORATE"]) else 0
    cast_b = float(rb["TOTAL VALID VOTES"]) if pd.notna(rb["TOTAL VALID VOTES"]) else 0
    fig_elec = go.Figure()
    fig_elec.add_trace(go.Bar(name="Registered Electorate",x=[na_s,nb_s],y=[elec_a,elec_b],
        marker=dict(color=BG_CARD2,line=dict(color=BORDER,width=1)),
        hovertemplate="<b>%{x}</b><br>Electorate: %{y:,}<extra></extra>"))
    fig_elec.add_trace(go.Bar(name="Votes Cast",x=[na_s,nb_s],y=[cast_a,cast_b],
        marker_color=[COLOR_A,COLOR_B],
        hovertemplate="<b>%{x}</b><br>Votes Cast: %{y:,}<extra></extra>"))
    fig_elec.update_layout(**CHART_LAYOUT,
        title=dict(text="Electorate vs Votes Cast",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        showlegend=True,barmode="overlay",bargap=0.4,
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,tickformat=","))

    return cards, fig_votes, fig_to, fig_maj, fig_elec
