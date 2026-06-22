"""
app.py — Entry point & routing shell
Johor State Election (2022)
Sidebar navigation via hamburger. No circular dependencies.
"""

import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask_caching import Cache

from utils import BG_DARK, BG_CARD, BG_CARD2, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.title = "Johor 2022 — Tindak Malaysia"
server = app.server

Cache(app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})

from pages import (
    johor_overview, johor_comparison, johor_rankings, johor_demographics, johor_map,
    johor_simulation)

TINDAK_GITHUB = "https://github.com/TindakMalaysia/HISTORICAL-ELECTION-RESULTS/blob/main/2022-ELECTION-RESULTS/MALAYSIA_2022_PARLIAMENT_RESULTS.csv"
AUTHOR = "Justin Ng Wen Xuan (Tindak)"

NAV_PAGES = [
    {"label": "Overview",     "href": "/johor",               "icon": "📊"},
    {"label": "Comparison",   "href": "/johor/comparison",    "icon": "⚖️"},
    {"label": "Rankings",     "href": "/johor/rankings",      "icon": "🏆"},
    {"label": "Demographics", "href": "/johor/demographics",  "icon": "👥"},
    {"label": "Map",          "href": "/johor/map",           "icon": "🗺️"},
    {"label": "Simulation",   "href": "/johor/simulation",    "icon": "🔬"},
]

# Sidebar style constants
SIDEBAR_OPEN  = {
    "position":"fixed","top":"0","left":"0","width":"260px","height":"100vh",
    "background":BG_CARD,"borderRight":f"1px solid {BORDER}","zIndex":"500",
    "transition":"left 0.25s ease","overflowY":"auto",
    "boxShadow":"4px 0 20px rgba(0,0,0,0.4)",
}
SIDEBAR_CLOSE = {
    "position":"fixed","top":"0","left":"-280px","width":"260px","height":"100vh",
    "background":BG_CARD,"borderRight":f"1px solid {BORDER}","zIndex":"500",
    "transition":"left 0.25s ease","overflowY":"auto",
    "boxShadow":"4px 0 20px rgba(0,0,0,0.4)",
}
OVERLAY_SHOW = {
    "position":"fixed","top":"0","left":"0","width":"100vw","height":"100vh",
    "background":"rgba(0,0,0,0.5)","zIndex":"400","display":"block",
}
OVERLAY_HIDE = {
    "position":"fixed","top":"0","left":"0","width":"100vw","height":"100vh",
    "background":"rgba(0,0,0,0.5)","zIndex":"400","display":"none",
}


# ── Topbar ─────────────────────────────────────────────────────────────────────

def topbar():
    return html.Div([
        # Left: hamburger
        html.Button("☰", id="sidebar-toggle", n_clicks=0, style={
            "background":"transparent","border":f"1px solid {BORDER}",
            "color":TEXT_PRIMARY,"borderRadius":"6px","width":"36px","height":"36px",
            "cursor":"pointer","fontSize":"18px","display":"flex",
            "alignItems":"center","justifyContent":"center","flexShrink":"0",
        }),

        # Centre: brand
        html.Div([
            html.A([
                html.Img(src="/assets/tindak_logo.png",
                         style={"height":"30px","marginRight":"8px","borderRadius":"4px"}),
                html.Img(src="/assets/tindak_malaysia.png",
                         style={"height":"24px","marginRight":"10px"}),
                html.Span("GE15", style={
                    "background":ACCENT,"color":"white","borderRadius":"4px",
                    "padding":"2px 7px","fontSize":"12px","fontWeight":"800",
                    "letterSpacing":"0.06em","marginRight":"8px",
                }),
                html.Span("Johor 2022", style={
                    "color":TEXT_PRIMARY,"fontSize":"14px","fontWeight":"600",
                }),
            ], href="/", style={"textDecoration":"none","display":"flex","alignItems":"center",
                                "marginRight":"20px"}),
        ], style={"display":"flex","alignItems":"center"}),

        # Right: spacer to balance hamburger
        html.Div(style={"width":"36px"}),

    ], style={
        "background":BG_CARD,"borderBottom":f"1px solid {BORDER}",
        "height":"52px","display":"flex","alignItems":"center",
        "justifyContent":"space-between","padding":"0 16px",
        "position":"sticky","top":"0","zIndex":"300",
    })


# ── Sidebar ─────────────────────────────────────────────────────────────────────

def sidebar():
    return html.Div(id="sidebar", children=[
        html.Div([
            html.Button("✕", id="sidebar-close", n_clicks=0, style={
                "background":"transparent","border":"none","color":TEXT_MUTED,
                "fontSize":"16px","cursor":"pointer","padding":"4px 8px",
            }),
        ], style={"textAlign":"right","padding":"12px 12px 4px"}),

        html.Div(id="sidebar-section-label", style={
            "color":TEXT_MUTED,"fontSize":"10px","textTransform":"uppercase",
            "letterSpacing":"0.08em","padding":"0 16px 8px",
        }),

        html.Div(id="sidebar-nav-links"),

        html.Hr(style={"borderColor":BORDER,"margin":"12px 16px"}),

        html.Div([
            html.Div("Built by", style={"color":TEXT_MUTED,"fontSize":"10px"}),
            html.Div("Justin Ng Wen Xuan",
                     style={"color":TEXT_PRIMARY,"fontSize":"12px","fontWeight":"600"}),
            html.Div("(Tindak)", style={"color":TEXT_MUTED,"fontSize":"11px"}),
        ], style={"padding":"0 16px 16px"}),
    ], style=SIDEBAR_CLOSE)


def overlay():
    return html.Div(id="sidebar-overlay", n_clicks=0, style=OVERLAY_HIDE)


# ── Footer ─────────────────────────────────────────────────────────────────────

def footer():
    return html.Div([
        html.Div([
            html.Img(src="/assets/tindak_logo.png",
                     style={"height":"34px","marginRight":"12px","opacity":"0.85"}),
            html.Img(src="/assets/tindak_malaysia.png",
                     style={"height":"26px","opacity":"0.85"}),
        ], style={"marginBottom":"10px","display":"flex","alignItems":"center","justifyContent":"center"}),
        html.Div([
            html.Span("Data Source: ", style={"color":TEXT_MUTED,"fontSize":"12px"}),
            html.A("Tindak Malaysia Historical Elections — GE15 Parliament Results",
                   href=TINDAK_GITHUB, target="_blank",
                   style={"color":ACCENT,"fontSize":"12px","textDecoration":"none"}),
        ], style={"marginBottom":"4px"}),
        html.Div([
            html.Span(f"Built by {AUTHOR}",
                      style={"color":TEXT_MUTED,"fontSize":"12px"}),
            html.Span(" · Built with Dash + Plotly",
                      style={"color":BORDER,"fontSize":"12px"}),
        ], style={"marginBottom":"8px"}),
        html.Div(
            "Disclaimer: If you publish, reuse, or screenshot results or content from this "
            "dashboard, please credit Tindak. Any views or analysis presented here "
            "beyond Tindak's original published data are independent and should not "
            "be taken as an endorsement by Tindak.",
            style={"color":TEXT_MUTED,"fontSize":"11px","fontStyle":"italic",
                   "maxWidth":"720px","margin":"0 auto","lineHeight":"1.5"},
        ),
    ], style={"borderTop":f"1px solid {BORDER}","padding":"20px 28px","textAlign":"center"})


# ── Root layout ───────────────────────────────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    topbar(),
    sidebar(),
    overlay(),
    html.Div(id="page-content"),
    footer(),
], style={"background":BG_DARK,"minHeight":"100vh",
          "fontFamily":"Inter, sans-serif","color":TEXT_PRIMARY})


# ── Sidebar open/close ────────────────────────────────────────────────────────
# Single callback handles all triggers — no allow_duplicate needed.

@app.callback(
    Output("sidebar",         "style"),
    Output("sidebar-overlay", "style"),
    Input("sidebar-toggle",   "n_clicks"),
    Input("sidebar-close",    "n_clicks"),
    Input("sidebar-overlay",  "n_clicks"),
    Input("url",              "pathname"),
    prevent_initial_call=True,
)
def toggle_sidebar(open_clicks, close_clicks, overlay_clicks, pathname):
    from dash import ctx
    if ctx.triggered_id == "sidebar-toggle":
        return SIDEBAR_OPEN, OVERLAY_SHOW
    return SIDEBAR_CLOSE, OVERLAY_HIDE


# ── Sidebar nav (reads URL only, never writes it) ──────────────────────────────

@app.callback(
    Output("sidebar-section-label", "children"),
    Output("sidebar-nav-links",     "children"),
    Input("url", "pathname"),
)
def update_sidebar_nav(pathname):
    p       = pathname or "/"
    section = "🏛️ Johor State 2022"

    links = []
    for page in NAV_PAGES:
        is_active = p == page["href"]
        links.append(dcc.Link(
            html.Div([
                html.Span(page["icon"], style={"marginRight":"10px","fontSize":"15px"}),
                html.Span(page["label"], style={"fontSize":"13px"}),
            ], style={"display":"flex","alignItems":"center"}),
            href=page["href"],
            style={
                "display":"block","padding":"10px 16px","margin":"2px 8px",
                "borderRadius":"8px","textDecoration":"none",
                "color": TEXT_PRIMARY if is_active else TEXT_MUTED,
                "background": BG_CARD2 if is_active else "transparent",
                "borderLeft": f"3px solid {ACCENT}" if is_active else "3px solid transparent",
                "fontWeight": "600" if is_active else "400",
                "transition":"all 0.15s",
            }
        ))

    return section, links


# ── Page routing ──────────────────────────────────────────────────────────────

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def route(pathname):
    if pathname == "/johor":              return johor_overview.layout()
    if pathname == "/johor/comparison":   return johor_comparison.layout()
    if pathname == "/johor/rankings":     return johor_rankings.layout()
    if pathname == "/johor/demographics": return johor_demographics.layout()
    if pathname == "/johor/map":          return johor_map.layout()
    if pathname == "/johor/simulation":   return johor_simulation.layout()
    return johor_overview.layout()


if __name__ == "__main__":
    app.run(debug=True, port=8051)
