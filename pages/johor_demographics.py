"""
pages/johor_demographics.py — Johor 2022 Demographic Analysis
"""

from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from utils.johor_data import load_johor_results, load_johor_demographics, JOHOR_COALITION_COLORS
from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT

def coal_color(n): return JOHOR_COALITION_COLORS.get(str(n).upper(), "#9E9E9E")
def card_style():  return {"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"12px","padding":"4px"}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(color=TEXT_MUTED,size=11)),
)

ETH_COLS = {"MALAY (%)":"Malay","CHINESE (%)":"Chinese","INDIANS (%)":"Indian",
            "ORANG ASLI (%)":"Orang Asli"}

AGE_GROUPS = {
    "Under 30":    ["18-20 (%)","21-29 (%)"],
    "30–39":       ["30-39 (%)"],
    "40–49":       ["40-49 (%)"],
    "50–59":       ["50-59 (%)"],
    "60 and above":["60-69 (%)","70-79 (%)","80-89 (%)","ABOVE 90 (%)"],
}

_MERGED = {}

def load_merged():
    if "df" in _MERGED: return _MERGED["df"]
    results = load_johor_results()
    demo    = load_johor_demographics()
    df = results.merge(demo, on="UNIQUE CODE", how="left", suffixes=("","_demo"))
    df = df.loc[:,~df.columns.duplicated()]
    df["DOMINANT_ETH"] = df[list(ETH_COLS.keys())].idxmax(axis=1).map(ETH_COLS)
    df["URBAN_CLASS"]  = df.get("URBAN-RURAL CLASSIFICATION (2022)",
                                df.get("URBAN-RURAL CLASSIFICATION (2021)",
                                       pd.Series("UNKNOWN",index=df.index)))
    df["URBAN_CLASS"]  = df["URBAN_CLASS"].fillna("UNKNOWN").str.strip().str.upper()
    _MERGED["df"] = df
    return df

def _kpi(label, value, sub=None, color=ACCENT):
    return html.Div([
        html.Div(label,  style={"color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
                                "letterSpacing":"0.08em","marginBottom":"4px"}),
        html.Div(value,  style={"color":color,"fontSize":"22px","fontWeight":"700","lineHeight":"1.1"}),
        html.Div(sub or "",style={"color":TEXT_MUTED,"fontSize":"10px","marginTop":"2px"}),
    ], style={"background":BG_CARD,"border":f"1px solid {BORDER}","borderRadius":"10px",
              "padding":"14px 16px","flex":"1","minWidth":"130px"})

def layout():
    df = load_merged()
    coals = sorted([c for c in df["COALITION"].unique() if c not in ("OTHERS","INDEPENDENT")])

    return html.Div([
        html.Div([
            html.Div([
                html.Span("DEMOGRAPHICS", style={"background":"#8E24AA","color":"white","borderRadius":"4px",
                          "padding":"2px 8px","fontSize":"10px","fontWeight":"800",
                          "letterSpacing":"0.07em","marginRight":"10px"}),
                html.Span("Johor 2022 voter composition", style={"color":TEXT_MUTED,"fontSize":"13px"}),
            ], style={"marginBottom":"6px"}),
            html.H2("Demographic Analysis — Johor 2022", style={"color":TEXT_PRIMARY,
                "fontSize":"clamp(18px,3vw,26px)","fontWeight":"700","margin":"0 0 5px 0"}),
            html.Div("How ethnicity, age, urbanisation and gender shaped the Johor 2022 result.",
                     style={"color":TEXT_MUTED,"fontSize":"13px"}),
        ], style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"20px 28px"}),

        html.Div([html.Div([
            html.Div([
                html.Label("State", style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                                           "letterSpacing":"0.07em","marginBottom":"4px","display":"block"}),
                html.Div("Johor", style={"color":TEXT_PRIMARY,"fontSize":"13px","padding":"6px 0"}),
            ], style={"flex":"1"}),
            html.Div([
                html.Label("Urban / Rural", style={"color":TEXT_MUTED,"fontSize":"11px","textTransform":"uppercase",
                                                    "letterSpacing":"0.07em","marginBottom":"4px","display":"block"}),
                dcc.Dropdown(id="jhr-demo-urban",
                    options=[{"label":"Urban","value":"URBAN"},{"label":"Semi Urban","value":"SEMI URBAN"},
                             {"label":"Rural","value":"RURAL"}],
                    multi=True, placeholder="All", className="dash-dropdown-dark"),
            ], style={"flex":"2","minWidth":"180px"}),
            html.Button("↺ Reset", id="jhr-demo-reset", style={
                "background":"transparent","border":f"1px solid {BORDER}","color":TEXT_MUTED,
                "borderRadius":"6px","padding":"8px 16px","cursor":"pointer","fontSize":"12px",
                "fontFamily":"Inter","alignSelf":"flex-end","whiteSpace":"nowrap"}),
        ], style={"display":"flex","gap":"16px","alignItems":"flex-start","flexWrap":"wrap"})],
        style={"background":BG_CARD,"borderBottom":f"1px solid {BORDER}","padding":"14px 28px",
               "position":"sticky","top":"52px","zIndex":"100"}),

        html.Div(id="jhr-demo-kpis",
                 style={"display":"flex","gap":"12px","flexWrap":"wrap","padding":"20px 28px 0"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-demo-eth-coal",config={"displayModeBar":False},style={"height":"360px"})],
                     style={"flex":"2","minWidth":"340px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-demo-turnout-urban",config={"displayModeBar":False},style={"height":"360px"})],
                     style={"flex":"1","minWidth":"260px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"16px 28px","flexWrap":"wrap"}),

        html.Div([
            html.Div([dcc.Graph(id="jhr-demo-age",config={"displayModeBar":False},style={"height":"340px"})],
                     style={"flex":"2","minWidth":"340px",**card_style()}),
            html.Div([dcc.Graph(id="jhr-demo-gender",config={"displayModeBar":False},style={"height":"340px"})],
                     style={"flex":"1","minWidth":"260px",**card_style()}),
        ], style={"display":"flex","gap":"16px","padding":"0 28px 28px","flexWrap":"wrap"}),
    ])

@callback(Output("jhr-demo-urban","value"), Input("jhr-demo-reset","n_clicks"), prevent_initial_call=True)
def reset(_): return None

@callback(
    Output("jhr-demo-kpis","children"),
    Output("jhr-demo-eth-coal","figure"),
    Output("jhr-demo-turnout-urban","figure"),
    Output("jhr-demo-age","figure"),
    Output("jhr-demo-gender","figure"),
    Input("jhr-demo-urban","value"),
)
def update(urban):
    df = load_merged()
    if urban: df = df[df["URBAN_CLASS"].isin([u.upper() for u in urban])]

    avg_malay   = df["MALAY (%)"].mean()
    avg_chinese = df["CHINESE (%)"].mean()
    avg_youth   = df["YOUTH_PCT"].mean()
    avg_female  = df["WOMEN ELECTORS (%)"].mean() if "WOMEN ELECTORS (%)" in df.columns else 0
    total = len(df)

    kpis = [
        _kpi("Constituencies", str(total), "in selection"),
        _kpi("Avg Malay %",    f"{avg_malay:.1f}%",   "of electorate", color="#F9A825"),
        _kpi("Avg Chinese %",  f"{avg_chinese:.1f}%", "of electorate", color="#E53935"),
        _kpi("Youth 18–29",    f"{avg_youth:.1f}%",   "avg per seat",  color="#4CAF50"),
        _kpi("Women Electors", f"{avg_female:.1f}%",  "avg per seat",  color="#8E24AA"),
    ]

    # Ethnicity × Coalition heatmap
    main_coals = [c for c in ["BN","PH","PN","MUDA","PEJUANG"] if c in df["COALITION"].unique()]
    z_data, y_labels = [], []
    for coal in main_coals:
        sub = df[df["COALITION"]==coal]
        if len(sub)==0: continue
        row = [sub[col].mean() for col in ETH_COLS.keys()]
        z_data.append(row); y_labels.append(f"{coal} ({len(sub)})")
    fig_eth = go.Figure(go.Heatmap(
        z=z_data, x=list(ETH_COLS.values()), y=y_labels,
        colorscale=[[0,BG_CARD2],[0.2,"#A8D4FF"],[0.5,"#4F8EF7"],[0.75,"#1565C0"],[1,"#1a3a5c"]],
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT_MUTED,size=10),thickness=12,ticksuffix="%"),
        text=[[f"{v:.1f}%" for v in row] for row in z_data],
        texttemplate="%{text}", textfont=dict(size=10,color="white"),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>",
    ))
    fig_eth.update_layout(**CHART_LAYOUT,
        title=dict(text="Avg Ethnic Composition of Seats Won",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=False,color=TEXT_MUTED,autorange="reversed"),
        showlegend=False, margin=dict(l=10,r=10,t=45,b=10))

    # Turnout by urban class
    URBAN_COLORS = {"URBAN":ACCENT,"SEMI URBAN":"#F9A825","RURAL":"#4CAF50"}
    urban_stats = df.groupby("URBAN_CLASS")["TURNOUT (%)"].agg(["mean","median","std","count"]).reset_index()
    fig_urban = go.Figure()
    for _, row in urban_stats.iterrows():
        uc = row["URBAN_CLASS"]
        fig_urban.add_trace(go.Bar(
            x=[uc.title()], y=[row["mean"]],
            marker_color=URBAN_COLORS.get(uc,ACCENT),
            error_y=dict(type="data",array=[row["std"]],color=TEXT_MUTED,thickness=1.5,width=6),
            text=[f"{row['mean']:.1f}%"], textposition="outside",
            textfont=dict(size=12,color=TEXT_PRIMARY),
            hovertemplate=f"<b>{uc.title()}</b><br>Avg: {row['mean']:.1f}%<br>Seats: {int(row['count'])}<extra></extra>",
            showlegend=False,
        ))
    nat_avg = df["TURNOUT (%)"].mean()
    fig_urban.add_hline(y=nat_avg, line_dash="dash", line_color=TEXT_MUTED, line_width=1.5,
        annotation=dict(text=f"Avg {nat_avg:.1f}%",font=dict(size=10,color=TEXT_MUTED),xanchor="right"))
    fig_urban.update_layout(**CHART_LAYOUT,
        title=dict(text="Turnout by Urbanisation",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,range=[30,80],ticksuffix="%"),
        bargap=0.35,showlegend=False,margin=dict(l=10,r=10,t=45,b=10))

    # Age profile
    age_display = list(AGE_GROUPS.keys())
    fig_age = go.Figure()
    for coal in main_coals:
        sub = df[df["COALITION"]==coal]
        if len(sub)==0: continue
        vals = []
        for grp_cols in AGE_GROUPS.values():
            vals.append(sum(sub[c].fillna(0).mean() for c in grp_cols if c in sub.columns))
        fig_age.add_trace(go.Bar(
            name=f"{coal} ({len(sub)})", x=age_display, y=vals,
            marker_color=coal_color(coal),
            hovertemplate=f"<b>{coal}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig_age.update_layout(**CHART_LAYOUT,
        title=dict(text="Voters' Age Group Distribution by Coalition",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        barmode="group",showlegend=True,
        xaxis=dict(showgrid=False,color=TEXT_MUTED),
        yaxis=dict(showgrid=True,gridcolor=BORDER,zeroline=False,color=TEXT_MUTED,ticksuffix="%"),
        bargap=0.15,margin=dict(l=10,r=10,t=45,b=10))

    # Gender split
    gender_rows = []
    for coal in main_coals:
        sub = df[df["COALITION"]==coal]
        if len(sub)==0: continue
        female_col = "WOMEN ELECTORS (%)" if "WOMEN ELECTORS (%)" in sub.columns else "FEMALE ELECTORS (%)"
        male_col   = "MALE ELECTORS (%)"
        gender_rows.append({"Coalition":coal,
                             "Male":  sub[male_col].mean()  if male_col  in sub.columns else 50,
                             "Female":sub[female_col].mean() if female_col in sub.columns else 50,
                             "Seats": len(sub)})
    gdf = pd.DataFrame(gender_rows).sort_values("Female",ascending=True)
    fig_gender = go.Figure()
    fig_gender.add_trace(go.Bar(name="Male",y=gdf["Coalition"],x=gdf["Male"],orientation="h",
        marker_color="#4F8EF7",text=[f"{v:.1f}%" for v in gdf["Male"]],textposition="inside",
        textfont=dict(size=10,color="white"),
        hovertemplate="<b>%{y}</b><br>Male: %{x:.1f}%<extra></extra>"))
    fig_gender.add_trace(go.Bar(name="Female",y=gdf["Coalition"],x=gdf["Female"],orientation="h",
        marker_color="#E91E63",text=[f"{v:.1f}%" for v in gdf["Female"]],textposition="inside",
        textfont=dict(size=10,color="white"),
        hovertemplate="<b>%{y}</b><br>Female: %{x:.1f}%<extra></extra>"))
    fig_gender.update_layout(**CHART_LAYOUT,
        title=dict(text="Gender Split by Coalition",font=dict(size=14,color=TEXT_PRIMARY),x=0.01),
        barmode="stack",showlegend=True,
        xaxis=dict(range=[0,100],ticksuffix="%",showgrid=True,gridcolor=BORDER,color=TEXT_MUTED),
        yaxis=dict(showgrid=False,color=TEXT_MUTED),
        bargap=0.3,margin=dict(l=10,r=10,t=45,b=10))

    return kpis, fig_eth, fig_urban, fig_age, fig_gender
