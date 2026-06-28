"""
utils/johor2026_data.py — Johor 2026 candidate data + shared 2022/2026 long-format loaders
Melts the wide per-seat candidate-slot CSVs (BN/PH/PN/OTHER PARTY (1)/(2)/INDEPENDENT...)
into one row per candidate, classified by individual party (not lumped into OTHERS) and
by bloc (coalition-style grouping used for swing math).
"""

import re
import json
import os
import pandas as pd
import numpy as np

# ── Party taxonomy ──────────────────────────────────────────────────────────────
# Individual party -> bloc (used for swing/turnout grouping in the simulator).
# Every party gets its own bucket; only genuinely fringe parties fall to OTHERS.
PARTY_BLOC = {
    "UMNO": "BN", "MCA": "BN", "MIC": "BN", "GERAKAN": "BN",
    "PKR": "PH", "DAP": "PH", "AMANAH": "PH",
    "PAS": "PN", "PPBM": "PN", "BERSATU": "PN",
    "MUDA": "MUDA",
    "BERSAMA": "BERSAMA",
    "PEJUANG": "PEJUANG",
    "PBM": "PBM",
    "MIPP": "OTHERS", "POAM": "OTHERS", "PSM": "OTHERS",
    "PUTRA": "OTHERS", "WARISAN": "OTHERS",
    "INDEPENDENT": "INDEPENDENT",
}

# Distinct colour per individual party — never collapsed into a generic grey.
PARTY_COLORS = {
    "UMNO": "#1565C0", "MCA": "#1E88E5", "MIC": "#64B5F6", "GERAKAN": "#0D47A1",
    "PKR": "#C62828", "DAP": "#E53935", "AMANAH": "#EF5350",
    "PAS": "#2E7D32", "PPBM": "#66BB6A", "BERSATU": "#66BB6A",
    "MUDA": "#000000",
    "BERSAMA": "#FFEB3B",
    "PEJUANG": "#795548",
    "PBM": "#8D6E63",
    "MIPP": "#FDD835", "POAM": "#9CCC65", "PSM": "#EC407A",
    "PUTRA": "#26C6DA", "WARISAN": "#FFA726",
    "INDEPENDENT": "#607D8B",
    "OTHERS": "#9E9E9E",
}

BLOC_COLORS = {
    "BN": "#1565C0", "PH": "#E53935", "PN": "#4CAF50",
    "MUDA": "#000000", "BERSAMA": "#FFEB3B", "PEJUANG": "#795548",
    "PBM": "#8D6E63", "OTHERS": "#9E9E9E", "INDEPENDENT": "#607D8B",
}

BLOC_ORDER = ["BN", "PH", "PN", "MUDA", "BERSAMA", "PEJUANG", "PBM", "INDEPENDENT", "OTHERS"]


def party_color(party):
    return PARTY_COLORS.get(str(party).upper().strip(), "#9E9E9E")


def bloc_color(bloc):
    return BLOC_COLORS.get(str(bloc).upper().strip(), "#9E9E9E")


COALITION_BLOCS = ("BN", "PH", "PN")


def coalition_label(party, bloc):
    """'UMNO' + 'BN' -> 'BN-UMNO'. Parties with no coalition affiliation (MUDA, BERSAMA,
    PBM, OTHERS, INDEPENDENT, or a bloc that isn't BN/PH/PN) are returned unprefixed."""
    if party is None:
        return party
    if str(bloc).upper() in COALITION_BLOCS:
        return f"{bloc}-{party}"
    return party


def classify_party(raw):
    """Returns (clean_party_name, bloc, symbol). Handles 'INDEPENDENT - KEY' style values."""
    if pd.isna(raw):
        return None, None, None
    s = str(raw).strip()
    if s.upper().startswith("INDEPENDENT"):
        symbol = None
        if "-" in s:
            symbol = s.split("-", 1)[1].strip()
        return "INDEPENDENT", "INDEPENDENT", symbol
    bloc = PARTY_BLOC.get(s.upper(), "OTHERS")
    return s.upper(), bloc, None


def _norm_cols(df):
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", c).strip() for c in df.columns]
    return df


def _first_existing(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


# Slots named BN/PH/PN/PEJUANG are coalition seat-allocation slots: the data assigns
# whichever actual party contested under that bloc's banner in a given seat (e.g. GERAKAN
# or PPBM may fill the "PN" slot). Bloc identity therefore comes from the SLOT, not the
# party name — matching the convention already used by utils/johor_data.py. Only the
# wildcard "OTHER PARTY"/"INDEPENDENT" slots derive bloc from the actual party name.
SLOT_BLOC = {"BN": "BN", "PH": "PH", "PN": "PN", "PEJUANG": "PEJUANG"}


# Each slot: (slot_id, party_col, candidate_col, sex_col, age_col, vote_col_candidates, lost_col)
def _slots_for(df, slot_ids):
    slots = []
    for slot_id in slot_ids:
        party_col = slot_id
        cand_col  = f"{slot_id} CANDIDATE"
        sex_col   = f"{slot_id} CANDIDATE SEX"
        age_col   = f"{slot_id} CANDIDATE AGE"
        vote_col  = _first_existing(df, [f"{slot_id} VOTE", f"{slot_id} CANDIDATE VOTE"])
        lost_col  = _first_existing(df, [f"{slot_id} CANDIDATE LOST DEPOSIT"])
        if party_col in df.columns:
            slots.append(dict(party_col=party_col, cand_col=cand_col, sex_col=sex_col,
                               age_col=age_col, vote_col=vote_col, lost_col=lost_col,
                               slot_bloc=SLOT_BLOC.get(slot_id)))
    return slots


SEAT_META_COLS = ["UNIQUE CODE", "STATE CONSTITUENCY NAME", "STATE CONSTITUENCY CODE",
                   "PARLIAMENTARY NAME", "TOTAL ELECTORATE", "TURNOUT (%)",
                   "TOTAL VALID VOTES", "WINNING MAJORITY", "WINNING PARTY"]


def _melt(df, slot_ids, has_votes):
    df = _norm_cols(df)
    slots = _slots_for(df, slot_ids)
    meta_cols = [c for c in SEAT_META_COLS if c in df.columns]

    records = []
    for _, row in df.iterrows():
        for slot in slots:
            raw_party = row.get(slot["party_col"])
            if pd.isna(raw_party) or str(raw_party).strip() == "":
                continue
            party, bloc, symbol = classify_party(raw_party)
            bloc = slot["slot_bloc"] or bloc
            votes = np.nan
            if has_votes and slot["vote_col"]:
                votes = pd.to_numeric(row.get(slot["vote_col"]), errors="coerce")
            rec = {m: row.get(m) for m in meta_cols}
            rec.update({
                "PARTY": party,
                "BLOC": bloc,
                "SYMBOL": symbol,
                "CANDIDATE": row.get(slot["cand_col"]),
                "SEX": row.get(slot["sex_col"]),
                "AGE": pd.to_numeric(row.get(slot["age_col"]), errors="coerce"),
                "VOTES": votes,
                "LOST_DEPOSIT": str(row.get(slot["lost_col"])).strip().upper() == "LOST DEPOSIT"
                                if slot["lost_col"] else False,
            })
            records.append(rec)

    long_df = pd.DataFrame.from_records(records)
    if long_df.empty:
        return long_df

    long_df["SEX"] = long_df["SEX"].astype(str).str.strip().str.upper().replace({"NAN": np.nan})
    long_df["SEAT_LABEL"] = long_df["STATE CONSTITUENCY NAME"].str.title()
    long_df["SEAT_NUM"] = long_df["STATE CONSTITUENCY CODE"].str.extract(r"(\d+)").astype(float)

    # A seat can field 2-3 independents at once (each with a distinct ballot symbol), so
    # PARTY alone isn't a unique row key. PARTY_KEY disambiguates independents by symbol —
    # use this (not PARTY) wherever per-seat uniqueness matters (e.g. the swing simulator).
    long_df["PARTY_KEY"] = long_df.apply(
        lambda r: f"INDEPENDENT ({r['SYMBOL']})" if r["PARTY"] == "INDEPENDENT" and pd.notna(r["SYMBOL"])
                  else r["PARTY"], axis=1)

    if has_votes:
        long_df["VOTES"] = long_df["VOTES"].fillna(0)
        max_votes = long_df.groupby("UNIQUE CODE")["VOTES"].transform("max")
        long_df["IS_WINNER"] = (long_df["VOTES"] == max_votes) & (long_df["VOTES"] > 0)
    else:
        long_df["IS_WINNER"] = False

    return long_df


_CACHE = {}

JOHOR_2022_SLOTS = ["BN", "PH", "PN", "PEJUANG", "OTHER PARTY (1)", "OTHER PARTY (2)",
                     "INDEPENDENT (1)", "INDEPENDENT (2)", "INDEPENDENT (3)"]
JOHOR_2026_SLOTS = ["BN", "PH", "PN", "OTHER PARTY (1)", "OTHER PARTY (2)", "INDEPENDENT (1)"]


def load_2022_candidates():
    if "c2022" in _CACHE:
        return _CACHE["c2022"]
    df = pd.read_csv("data/JOHOR_2022_ELECTION_RESULTS.csv")
    long_df = _melt(df, JOHOR_2022_SLOTS, has_votes=True)
    _CACHE["c2022"] = long_df
    return long_df


def load_2026_candidates():
    if "c2026" in _CACHE:
        return _CACHE["c2026"]
    df = pd.read_csv("data/2026_JOHOR_DUN_RESULTS.csv")
    long_df = _melt(df, JOHOR_2026_SLOTS, has_votes=False)
    _CACHE["c2026"] = long_df
    return long_df


def seat_options():
    """List of {label, value} sorted by DUN seat number, value = UNIQUE CODE."""
    df = load_2026_candidates()
    seats = df[["UNIQUE CODE", "SEAT_LABEL", "SEAT_NUM", "PARLIAMENTARY NAME"]].drop_duplicates()
    seats = seats.sort_values("SEAT_NUM")
    return [
        {"label": f"N{int(r['SEAT_NUM']):02d} {r['SEAT_LABEL']}", "value": r["UNIQUE CODE"]}
        for _, r in seats.iterrows()
    ]


def seat_code_label(seat_num):
    """e.g. 1 -> 'N01', 41 -> 'N41'."""
    return f"N{int(seat_num):02d}"


def get_seat_2022(unique_code):
    df = load_2022_candidates()
    return df[df["UNIQUE CODE"] == unique_code].copy()


def get_seat_2026(unique_code):
    df = load_2026_candidates()
    return df[df["UNIQUE CODE"] == unique_code].copy()


def bloc_votes_for_seat_2022(unique_code):
    """dict: bloc -> total 2022 votes in this seat."""
    sub = get_seat_2022(unique_code)
    return sub.groupby("BLOC")["VOTES"].sum().to_dict()


def blocs_contesting_2026(unique_code):
    """Set of blocs that field a candidate in this seat in 2026."""
    sub = get_seat_2026(unique_code)
    return set(sub["BLOC"].unique())


_GEO_CACHE = {}
GEOJSON_PATH = "data/JOHOR_2022_DUN_BOUNDARIES.geojson"


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
