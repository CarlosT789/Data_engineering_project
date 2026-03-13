#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flights_database.db"

"""
CO2 module Flights Dashboard
This file contains all calculations and data processing for the CO2 sub-dashboard.
It is separated from dashboard.py.
The database does not contain real fuel usage or CO2 emissions per flight.
Therefore, this module estimates these values based on the available data.
For each flight that matches the active dashboard filters:
- the flight distance is read from the flights table
- the aircraft model and seats are obtained from the planes table
- the aircraft model is mapped to a general aircraft family
- an estimated fuel burn per kilometre is assigned to that family
- fuel usage and CO2 emissions are calculated
- CO2 per passenger and an estimated compensation cost are derived
  using fixed project assumptions (load factor and carbon price)
Important:
All values are estimates based on assumptions,
not exact airline fuel or emissions reports.
"""

# constants/assumptions

MILES_TO_KM = 1.60934
JET_FUEL_CO2_KG_PER_KG = 3.16
JET_FUEL_DENSITY_KG_PER_L = 0.8
PASSENGER_LOAD_FACTOR = 0.82
CARBON_PRICE_EUR_PER_TONNE = 90.0


def _qdf(query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(str(DB_PATH)) as con:
        return pd.read_sql_query(query, con, params=params)


def _infer_aircraft_family(model: Optional[str]) -> str:
    if model is None or pd.isna(model):
        return "Unknown"

    m = str(model).upper().strip()

    if "BD-500" in m or "A220" in m:
        return "Airbus A220"

    if "ERJ 170" in m or "E170" in m or "E175" in m:
        return "Embraer E170/E175"
    if "ERJ 190" in m or "E190" in m or "E195" in m:
        return "Embraer E190/E195"

    if "CL-600-2D24" in m or "CRJ" in m:
        return "CRJ"

    if "717" in m:
        return "Boeing 717"

    if "737" in m:
        if "MAX" in m or "8M" in m or "9M" in m:
            return "Boeing 737 MAX"
        if "-7" in m or "7H4" in m:
            return "Boeing 737-700"
        if "-8" in m or "823" in m or "824" in m or "832" in m or "800" in m or "8H4" in m:
            return "Boeing 737-800"
        if "-9" in m or "924" in m or "932" in m or "900" in m or "990" in m or "890" in m:
            return "Boeing 737-900"
        return "Boeing 737"

    if "A319" in m:
        return "Airbus A319"
    if "A320" in m:
        if "251N" in m or "271N" in m or "NEO" in m:
            return "Airbus A320neo"
        return "Airbus A320"
    if "A321" in m:
        if "271N" in m or "253N" in m or "253NX" in m or "NEO" in m or "NX" in m:
            return "Airbus A321neo"
        return "Airbus A321"

    if "757" in m:
        return "Boeing 757"
    if "767" in m:
        return "Boeing 767"
    if "777" in m:
        return "Boeing 777"

    return "Unknown"


def _family_parameters(family: str) -> Tuple[float, int]:
    """
    Returns:
    - estimated fuel burn in kg per km
    - fallback seat count
    """
    mapping = {
        "Airbus A220":        (2.30, 130),
        "Embraer E170/E175":  (2.15, 76),
        "Embraer E190/E195":  (2.45, 100),
        "CRJ":                (2.35, 76),
        "Boeing 717":         (2.60, 110),
        "Boeing 737-700":     (2.85, 140),
        "Boeing 737-800":     (3.05, 160),
        "Boeing 737-900":     (3.30, 180),
        "Boeing 737 MAX":     (2.90, 175),
        "Boeing 737":         (3.00, 160),
        "Airbus A319":        (2.75, 126),
        "Airbus A320":        (3.00, 150),
        "Airbus A320neo":     (2.75, 150),
        "Airbus A321":        (3.35, 190),
        "Airbus A321neo":     (3.05, 200),
        "Boeing 757":         (4.60, 200),
        "Boeing 767":         (6.20, 230),
        "Boeing 777":         (8.30, 300),
        "Unknown":            (3.00, 150),
    }
    return mapping.get(family, mapping["Unknown"])


def _clean_seats(raw_seats: object, default_seats: int) -> int:
    try:
        seats = int(raw_seats)
        if 20 <= seats <= 400:
            return seats
    except Exception:
        pass
    return default_seats


def _timeline_granularity(start_date: date, end_date: date) -> str:
    days = (end_date - start_date).days + 1
    if days <= 45:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def _build_timeline(df: pd.DataFrame, start_date: date, end_date: date) -> Tuple[pd.DataFrame, str]:
    granularity = _timeline_granularity(start_date, end_date)

    timeline_df = df.copy()
    timeline_df["flight_date"] = pd.to_datetime(
        dict(year=timeline_df["year"], month=timeline_df["month"], day=timeline_df["day"]),
        errors="coerce",
    )
    timeline_df = timeline_df.dropna(subset=["flight_date"]).copy()

    if timeline_df.empty:
        return pd.DataFrame(columns=["period_label", "co2_tonnes"]), granularity

    if granularity == "day":
        grouped = (
            timeline_df.groupby("flight_date", as_index=False)["co2_kg"]
            .sum()
            .sort_values("flight_date")
        )
        grouped["co2_tonnes"] = grouped["co2_kg"] / 1000.0
        grouped["period_label"] = grouped["flight_date"].dt.strftime("%Y-%m-%d")
        return grouped[["period_label", "co2_tonnes"]], granularity

    if granularity == "week":
        timeline_df["week_start"] = timeline_df["flight_date"] - pd.to_timedelta(
            timeline_df["flight_date"].dt.weekday, unit="D"
        )
        grouped = (
            timeline_df.groupby("week_start", as_index=False)["co2_kg"]
            .sum()
            .sort_values("week_start")
        )
        grouped["co2_tonnes"] = grouped["co2_kg"] / 1000.0
        grouped["period_label"] = grouped["week_start"].dt.strftime("Week of %Y-%m-%d")
        return grouped[["period_label", "co2_tonnes"]], granularity

    grouped = (
        timeline_df.groupby(["year", "month"], as_index=False)["co2_kg"]
        .sum()
        .sort_values(["year", "month"])
    )
    grouped["co2_tonnes"] = grouped["co2_kg"] / 1000.0
    grouped["period_label"] = pd.to_datetime(
        dict(year=grouped["year"], month=grouped["month"], day=1)
    ).dt.strftime("%Y-%m")
    return grouped[["period_label", "co2_tonnes"]], granularity


def _empty_outputs():
    stats = {
        "total_fuel_kg": 0.0,
        "avg_fuel_kg": 0.0,
        "total_fuel_l": 0.0,
        "avg_fuel_l": 0.0,
        "total_co2_kg": 0.0,
        "avg_co2_kg": 0.0,
        "avg_co2_per_passenger_kg": 0.0,
        "avg_compensation_per_passenger_eur": 0.0,
        "n_flights": 0,
        "top_airline": None,
        "top_airline_co2_tonnes": 0.0,
        "top_family": None,
        "top_family_co2_tonnes": 0.0,
        "timeline_granularity": "month",
    }

    return (
        stats,
        pd.DataFrame(columns=["airline", "co2_tonnes"]),
        pd.DataFrame(columns=["airline", "avg_co2_kg"]),
        pd.DataFrame(columns=["family", "co2_tonnes"]),
        pd.DataFrame(columns=["period_label", "co2_tonnes"]),
    )


@st.cache_data(show_spinner=False)
def get_real_co2_data(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
):
    where_parts = [
        "date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) BETWEEN ? AND ?",
        "f.distance IS NOT NULL",
    ]
    params: List[object] = [start_date.isoformat(), end_date.isoformat()]

    if departure is not None:
        where_parts.append("f.origin = ?")
        params.append(departure)

    if arrival is not None:
        where_parts.append("f.dest = ?")
        params.append(arrival)

    where_sql = " AND ".join(where_parts)

    df = _qdf(
        f"""
        SELECT
            f.year,
            f.month,
            f.day,
            f.carrier,
            COALESCE(a.name, f.carrier) AS airline,
            f.tailnum,
            f.distance,
            p.model,
            p.seats
        FROM flights f
        LEFT JOIN planes p
            ON f.tailnum = p.tailnum
        LEFT JOIN airlines a
            ON f.carrier = a.carrier
        WHERE {where_sql}
        """,
        tuple(params),
    )

    if df.empty:
        return _empty_outputs()

    df["family"] = df["model"].apply(_infer_aircraft_family)

    family_info = df["family"].apply(_family_parameters)
    df["fuel_kg_per_km"] = family_info.apply(lambda x: x[0])
    df["default_seats"] = family_info.apply(lambda x: x[1])

    df["seat_estimate"] = [
        _clean_seats(raw_seats, default_seats)
        for raw_seats, default_seats in zip(df["seats"], df["default_seats"])
    ]

    df["occupied_passengers"] = (df["seat_estimate"] * PASSENGER_LOAD_FACTOR).clip(lower=1.0)

    df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce") * MILES_TO_KM
    df = df.dropna(subset=["distance_km"]).copy()

    df["fuel_kg"] = df["distance_km"] * df["fuel_kg_per_km"]
    df["fuel_l"] = df["fuel_kg"] / JET_FUEL_DENSITY_KG_PER_L
    df["co2_kg"] = df["fuel_kg"] * JET_FUEL_CO2_KG_PER_KG

    df["co2_per_passenger_kg"] = df["co2_kg"] / df["occupied_passengers"]
    df["compensation_per_passenger_eur"] = (
        df["co2_per_passenger_kg"] / 1000.0
    ) * CARBON_PRICE_EUR_PER_TONNE

    df_airlines_total = (
        df.groupby("airline", as_index=False)["co2_kg"]
        .sum()
        .rename(columns={"co2_kg": "co2_tonnes"})
        .sort_values("co2_tonnes", ascending=False)
    )
    df_airlines_total["co2_tonnes"] = df_airlines_total["co2_tonnes"] / 1000.0

    df_airlines_avg = (
        df.groupby("airline", as_index=False)["co2_kg"]
        .mean()
        .rename(columns={"co2_kg": "avg_co2_kg"})
        .sort_values("avg_co2_kg", ascending=False)
    )

    df_family = (
        df.groupby("family", as_index=False)["co2_kg"]
        .sum()
        .rename(columns={"co2_kg": "co2_tonnes"})
        .sort_values("co2_tonnes", ascending=False)
    )
    df_family["co2_tonnes"] = df_family["co2_tonnes"] / 1000.0

    df_timeline, timeline_granularity = _build_timeline(df, start_date, end_date)

    stats = {
        "total_fuel_kg": float(df["fuel_kg"].sum()),
        "avg_fuel_kg": float(df["fuel_kg"].mean()),
        "total_fuel_l": float(df["fuel_l"].sum()),
        "avg_fuel_l": float(df["fuel_l"].mean()),
        "total_co2_kg": float(df["co2_kg"].sum()),
        "avg_co2_kg": float(df["co2_kg"].mean()),
        "avg_co2_per_passenger_kg": float(df["co2_per_passenger_kg"].mean()),
        "avg_compensation_per_passenger_eur": float(df["compensation_per_passenger_eur"].mean()),
        "n_flights": int(len(df)),
        "top_airline": None,
        "top_airline_co2_tonnes": 0.0,
        "top_family": None,
        "top_family_co2_tonnes": 0.0,
        "timeline_granularity": timeline_granularity,
    }

    if not df_airlines_total.empty:
        stats["top_airline"] = str(df_airlines_total.iloc[0]["airline"])
        stats["top_airline_co2_tonnes"] = float(df_airlines_total.iloc[0]["co2_tonnes"])

    if not df_family.empty:
        stats["top_family"] = str(df_family.iloc[0]["family"])
        stats["top_family_co2_tonnes"] = float(df_family.iloc[0]["co2_tonnes"])

    return stats, df_airlines_total, df_airlines_avg, df_family, df_timeline