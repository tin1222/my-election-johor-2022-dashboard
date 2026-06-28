"""
utils/johor_data.py — Johor 2022 DUN election data loader
Mirrors the structure of utils/__init__.py load_data() so all pages
can call get_data(election) and get a consistent DataFrame.
"""

import pandas as pd
import numpy as np

# ── Coalition colours (Johor-specific + shared) ───────────────────────────────

JOHOR_COALITION_COLORS = {
    "PH":       "#E53935",
    "BN":       "#1565C0",
    "PN":       "#4CAF50",
    "MUDA":     "#000000",
    "PEJUANG":  "#795548",
    "BERSAMA":  "#FFEB3B",
    "PBM":      "#8D6E63",
    "OTHERS":   "#9E9E9E",
    "INDEPENDENT": "#607D8B",
}

_JOHOR_CACHE = {}


def load_johor_results():
    if "df" in _JOHOR_CACHE:
        return _JOHOR_CACHE["df"]

    df = pd.read_csv("data/JOHOR_2022_ELECTION_RESULTS.csv")

    # ── Coalition extraction ──────────────────────────────────────────────────
    def extract_coalition(p):
        if pd.isna(p):
            return "OTHERS"
        p = str(p).strip()
        if p.startswith("BN"):       return "BN"
        if p.startswith("PH"):       return "PH"
        if p.startswith("PN"):       return "PN"
        if p.startswith("MUDA"):     return "MUDA"
        if p.startswith("PEJUANG"): return "PEJUANG"
        if p == "INDEPENDENT":      return "INDEPENDENT"
        return "OTHERS"

    df["COALITION"] = df["WINNING PARTY"].apply(extract_coalition)

    # ── Normalise vote columns to match GE15 naming convention ───────────────
    # PN uses "PN CANDIDATE VOTE" in this dataset
    if "PN CANDIDATE VOTE" in df.columns and "PN VOTE" not in df.columns:
        df["PN VOTE"] = pd.to_numeric(df["PN CANDIDATE VOTE"], errors="coerce").fillna(0)

    vote_cols = ["BN VOTE", "PH VOTE", "PN VOTE", "PEJUANG VOTE"]
    for col in vote_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Aggregate OTHERS = all remaining valid votes
    main_sum = sum(df[c].fillna(0) for c in vote_cols if c in df.columns)
    df["OTHERS VOTE"] = (df["TOTAL VALID VOTES"].fillna(0) - main_sum).clip(lower=0)

    # ── Numeric conversions ───────────────────────────────────────────────────
    for col in ["TURNOUT (%)", "WINNING MAJORITY", "TOTAL ELECTORATE", "TOTAL VALID VOTES"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["MAJORITY_PCT"] = (df["WINNING MAJORITY"] / df["TOTAL VALID VOTES"] * 100).round(2)
    df["URBAN_RURAL"]  = df["TOTAL ELECTORATE"].apply(
        lambda x: "Urban" if pd.notna(x) and x >= 50_000 else "Rural"
    )

    # ── Seat label columns ────────────────────────────────────────────────────
    df["SEAT_LABEL"]   = df["STATE CONSTITUENCY NAME"].str.title()
    df["STATE_TITLE"]  = df["STATE"].str.title()
    # Alias so shared page code works (pages use PARLIAMENTARY CONSTITUENCY NAME)
    df["PARLIAMENTARY CONSTITUENCY NAME"] = df["STATE CONSTITUENCY NAME"]
    df["STATE"] = "JOHOR"

    _JOHOR_CACHE["df"] = df
    return df


def load_johor_demographics():
    demo = pd.read_csv("data/JOHOR_2022_DUN_COMPOSITION.csv")
    # Normalise age column names to match GE15 demographics
    rename = {
        "18 - 20 (%)":    "18-20 (%)",
        "21 - 29 (%)":    "21-29 (%)",
        "30 - 39 (%)":    "30-39 (%)",
        "40 - 49 (%)":    "40-49 (%)",
        "50 - 59 (%)":    "50-59 (%)",
        "60 - 69 (%)":    "60-69 (%)",
        "70 - 79 (%)":    "70-79 (%)",
        "80 - 89 (%)":    "80-89 (%)",
        "90 AND ABOVE (%)": "ABOVE 90 (%)",
        "FEMALE ELECTORS (%)": "WOMEN ELECTORS (%)",
        "URBAN-RURAL CLASSIFICATION (2021)": "URBAN-RURAL CLASSIFICATION (2022)",
    }
    demo = demo.rename(columns=rename)
    demo["YOUTH_PCT"] = demo["18-20 (%)"].fillna(0) + demo["21-29 (%)"].fillna(0)
    return demo
