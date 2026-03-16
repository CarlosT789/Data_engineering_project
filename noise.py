#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flights_database.db"


def _qdf(query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(str(DB_PATH)) as con:
        return pd.read_sql_query(query, con, params=params)


@st.cache_data(show_spinner=False)
def get_real_noise_data(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
) -> Tuple[pd.DataFrame, pd.DataFrame, float, int]:

    # EPNdB values from Table 1 of the research study
    epndb_mapping = """
        CASE
            WHEN p.model LIKE '%747-4%' THEN 299.1
            WHEN p.model LIKE '%777-3%' THEN 289.1
            WHEN p.model LIKE '%A330%' THEN 287.0
            WHEN p.model LIKE '%777-2%' THEN 285.7
            WHEN p.model LIKE '%767-3%' THEN 283.7
            WHEN p.model LIKE '%A321%' AND p.model NOT LIKE '%neo%' THEN 279.3
            WHEN p.model LIKE '%737-8%' THEN 275.3
            WHEN p.model LIKE '%737-4%' THEN 274.9
            WHEN p.model LIKE '%787-9%' THEN 273.8
            WHEN p.model LIKE '%737-3%' THEN 273.5
            WHEN p.model LIKE '%737-7%' THEN 272.3
            WHEN p.model LIKE '%A320%' AND p.model NOT LIKE '%neo%' THEN 272.3
            WHEN p.model LIKE '%A350%' THEN 272.0
            WHEN p.model LIKE '%737-5%' THEN 271.2
            WHEN p.model LIKE '%E170%' OR p.model LIKE '%E175%' THEN 269.7
            WHEN p.model LIKE '%E190%' OR p.model LIKE '%E195%' THEN 269.2
            WHEN p.model LIKE '%A319%' THEN 269.0
            WHEN p.model LIKE '%A321neo%' THEN 268.0
            WHEN p.model LIKE '%F100%' THEN 266.3
            WHEN p.model LIKE '%737 MAX%' THEN 265.0
            WHEN p.model LIKE '%A320neo%' THEN 258.0
            WHEN p.model LIKE '%E295%' THEN 257.0
            WHEN p.model LIKE '%F70%' THEN 255.7
            ELSE 275.0
        END
    """

    date_filter = "date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) BETWEEN ? AND ?"

    # Departures
    dep_parts = ["f.origin IN ('JFK','EWR','LGA')", date_filter]
    dep_params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    if departure is not None:
        dep_parts.append("f.origin = ?")
        dep_params.append(departure)
    if arrival is not None:
        dep_parts.append("f.dest = ?")
        dep_params.append(arrival)

    # Arrivals
    arr_parts = ["f.dest IN ('JFK','EWR','LGA')", date_filter]
    arr_params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    if departure is not None:
        arr_parts.append("f.origin = ?")
        arr_params.append(departure)
    if arrival is not None:
        arr_parts.append("f.dest = ?")
        arr_params.append(arrival)

    dep_where = " AND ".join(dep_parts)
    arr_where = " AND ".join(arr_parts)

    # UNION ALL: departures (airport = origin) + arrivals (airport = dest)
    union_sql = f"""
        SELECT f.carrier, f.tailnum, CAST(f.hour AS INTEGER) AS hour, f.origin AS airport,
               {epndb_mapping} AS epndb
        FROM flights f
        LEFT JOIN planes p ON f.tailnum = p.tailnum
        WHERE {dep_where}
        UNION ALL
        SELECT f.carrier, f.tailnum, CAST(f.arr_time / 100 AS INTEGER) AS hour, f.dest AS airport,
               {epndb_mapping} AS epndb
        FROM flights f
        LEFT JOIN planes p ON f.tailnum = p.tailnum
        WHERE {arr_where}
    """
    union_params = tuple(dep_params + arr_params)

    # Query 1: Ranking by Airport (includes flight count for per-flight average)
    df_ranking = _qdf(
        f"SELECT airport, SUM(epndb) AS noise, COUNT(*) AS flight_count FROM ({union_sql}) GROUP BY airport ORDER BY noise DESC",
        union_params,
    )

    total_noise = df_ranking["noise"].sum() if not df_ranking.empty else 0.0
    total_flights = int(df_ranking["flight_count"].sum()) if not df_ranking.empty else 0

    # Query 2: Timeline by Hour
    df_timeline = _qdf(
        f"SELECT CAST(hour AS INTEGER) AS hour, SUM(epndb) AS noise FROM ({union_sql}) WHERE hour IS NOT NULL GROUP BY hour ORDER BY hour",
        union_params,
    )

    return df_ranking, df_timeline, total_noise, total_flights
