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
app.title = "Johor Elections — Tindak Malaysia"
server = app.server

Cache(app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})

from pages import (
    johor_overview, johor_comparison, johor_rankings, johor_demographics, johor_map,
    johor_simulation, johor2026_candidates, johor2026_demographics, johor2026_simulation)

TINDAK_GITHUB = "https://github.com/TindakMalaysia/HISTORICAL-ELECTION-RESULTS"
AUTHOR = "Justin Ng Wen Xuan (Tindak)"

NAV_PAGES_2022 = [
    {"label": "Overview",     "href": "/johor",               "icon": "📊"},
    {"label": "Comparison",   "href": "/johor/comparison",    "icon": "⚖️"},
    {"label": "Rankings",     "href": "/johor/rankings",      "icon": "🏆"},
    {"label": "Demographics", "href": "/johor/demographics",  "icon": "👥"},
    {"label": "Map",          "href": "/johor/map",           "icon": "🗺️"},
    {"label": "Simulation",   "href": "/johor/simulation",    "icon": "🔬"},
]

NAV_PAGES_2026 = [
    {"label": "Candidates",   "href": "/johor2026/candidates",   "icon": "🧑‍🤝‍🧑"},
    {"label": "Demographics", "href": "/johor2026/demographics", "icon": "👥"},
    {"label": "Simulation",   "href": "/johor2026/simulation",   "icon": "🔬"},
]

SECTIONS = {
    "2022": {"label": "🏛️ Johor State 2022", "home": "/johor",              "pages": NAV_PAGES_2022},
    "2026": {"label": "🏛️ Johor State 2026", "home": "/johor2026/candidates", "pages": NAV_PAGES_2026},
}


def section_for(pathname):
    p = pathname or "/"
    if p == "/" or p.startswith("/johor2026"):
        return "2026"
    return "2022"

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

        # Centre: brand + section switcher
        html.Div([
            html.A([
                html.Img(src="/assets/tindak_logo.png",
                         style={"height":"30px","marginRight":"8px","borderRadius":"4px"}),
                html.Img(src="/assets/tindak_malaysia.png",
                         style={"height":"24px","marginRight":"10px"}),
            ], href="/", style={"textDecoration":"none","display":"flex","alignItems":"center",
                                "marginRight":"14px"}),
            html.Span("Johor", style={"color":TEXT_PRIMARY,"fontSize":"14px","fontWeight":"600",
                                       "marginRight":"10px"}),
            html.Div([
                dcc.Link("2026", id="topbar-tab-2026", href=SECTIONS["2026"]["home"]),
                dcc.Link("2022", id="topbar-tab-2022", href=SECTIONS["2022"]["home"]),
            ], style={"display":"flex","gap":"4px","background":BG_CARD2,"borderRadius":"8px","padding":"3px"}),
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
            html.A("Tindak Malaysia Historical Elections",
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
    sec     = SECTIONS[section_for(p)]
    section = sec["label"]

    links = []
    for page in sec["pages"]:
        is_active = p == page["href"] or (p == "/" and page["href"] == sec["home"])
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


# ── Topbar section switcher (2022 / 2026) ──────────────────────────────────────

def _tab_style(is_active):
    return {
        "padding":"5px 14px","borderRadius":"6px","fontSize":"13px","fontWeight":"700" if is_active else "500",
        "textDecoration":"none","color":TEXT_PRIMARY if is_active else TEXT_MUTED,
        "background": ACCENT if is_active else "transparent","transition":"all 0.15s",
    }

@app.callback(
    Output("topbar-tab-2022", "style"),
    Output("topbar-tab-2026", "style"),
    Input("url", "pathname"),
)
def update_topbar_tabs(pathname):
    sec = section_for(pathname)
    return _tab_style(sec == "2022"), _tab_style(sec == "2026")


# ── Page routing ──────────────────────────────────────────────────────────────

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def route(pathname):
    if pathname == "/johor":                 return johor_overview.layout()
    if pathname == "/johor/comparison":      return johor_comparison.layout()
    if pathname == "/johor/rankings":        return johor_rankings.layout()
    if pathname == "/johor/demographics":    return johor_demographics.layout()
    if pathname == "/johor/map":             return johor_map.layout()
    if pathname == "/johor/simulation":      return johor_simulation.layout()
    if pathname == "/johor2026/candidates":   return johor2026_candidates.layout()
    if pathname == "/johor2026/demographics": return johor2026_demographics.layout()
    if pathname == "/johor2026/simulation":   return johor2026_simulation.layout()
    if pathname == "/johor2026":              return johor2026_candidates.layout()
    return johor2026_candidates.layout()


if __name__ == "__main__":
    app.run(debug=True, port=8051)
