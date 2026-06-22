"""
utils/data.py — shared data loading and transformation
"""
import pandas as pd
import numpy as np

COALITION_COLORS = {
    "PH": "#E53935",
    "BN": "#1565C0",
    "PN": "#4CAF50",
    "GPS": "#F9A825",
    "GRS": "#8E24AA",
    "WARISAN": "#FB8C00",
    "OTHERS": "#9E9E9E",
    "INDEPENDENT": "#607D8B",
}

BG_DARK  = "#0D0F14"
BG_CARD  = "#161A23"
BG_CARD2 = "#1C2130"
BORDER   = "#2A2F3E"
TEXT_PRIMARY = "#F0F2F7"
TEXT_MUTED   = "#8892A4"
ACCENT       = "#4F8EF7"

CHART_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
    # showlegend=False,
    # margin=dict(l=10, r=10, t=45, b=10),
)

def coal_color(name):
    return COALITION_COLORS.get(str(name).upper(), "#9E9E9E")


def map_bounds_zoom(features):
    """Centre lat/lon + heuristic zoom level that frames a set of GeoJSON features."""
    lons, lats = [], []
    def _walk(coords):
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0]); lats.append(coords[1])
        else:
            for c in coords:
                _walk(c)
    for feat in features:
        _walk(feat["geometry"]["coordinates"])

    if not lons:
        return 4.0, 109.5, 4.5

    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)
    span = max(lat_span, lon_span, 0.01)

    if   span > 8:   zoom = 4.3
    elif span > 5:   zoom = 4.8
    elif span > 3:   zoom = 5.3
    elif span > 1.5: zoom = 6.2
    elif span > 0.8: zoom = 7.0
    elif span > 0.4: zoom = 7.8
    elif span > 0.2: zoom = 8.6
    else:            zoom = 9.2

    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2, zoom

def card_style(extra=None):
    base = {
        "background": BG_CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "padding": "4px",
    }
    if extra:
        base.update(extra)
    return base

_CACHE = {}

def load_data():
    if "df" in _CACHE:
        return _CACHE["df"]

    df = pd.read_csv("data/ge15_results.csv")

    def extract_coalition(p):
        if pd.isna(p):
            return "OTHERS"
        p = str(p).strip()
        for c in ["PH", "BN", "PN", "GPS", "GRS", "WARISAN"]:
            if p.startswith(c):
                return c
        return "INDEPENDENT" if p == "INDEPENDENT" else "OTHERS"

    df["COALITION"] = df["WINNING PARTY"].apply(extract_coalition)

    vote_cols = {"PH":"PH VOTE","BN":"BN VOTE","PN":"PN VOTE",
                 "GPS":"GPS VOTE","GRS":"GRS VOTE","WARISAN":"WARISAN VOTE"}
    for col in vote_cols.values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    main_sum = sum(df[v].fillna(0) for v in vote_cols.values() if v in df.columns)
    df["OTHERS VOTE"] = (df["TOTAL VALID VOTES"].fillna(0) - main_sum).clip(lower=0)

    for col in ["TURNOUT (%)", "WINNING MAJORITY", "TOTAL ELECTORATE", "TOTAL VALID VOTES"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive competitiveness score = majority / total valid votes * 100
    df["MAJORITY_PCT"] = (df["WINNING MAJORITY"] / df["TOTAL VALID VOTES"] * 100).round(2)

    # Derive urban proxy: electorate > 100k = urban, else rural (heuristic)
    df["URBAN_RURAL"] = df["TOTAL ELECTORATE"].apply(
        lambda x: "Urban" if pd.notna(x) and x >= 80_000 else "Rural"
    )

    # Short name for display
    df["SEAT_LABEL"] = df["PARLIAMENTARY CONSTITUENCY NAME"].str.title()
    df["STATE_TITLE"] = df["STATE"].str.title()

    _CACHE["df"] = df
    return df
