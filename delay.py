from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import pandas as pd
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "flights_database.db"


def _qdf(query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(str(DB_PATH)) as con:
        return pd.read_sql_query(query, con, params=params)


def get_real_delay_data(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
) -> Tuple[Dict[str, float], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    where_parts = [
        "date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) BETWEEN ? AND ?"
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
            f.origin,
            f.dest,
            f.arr_delay,
            f.hour
        FROM flights f
        WHERE {where_sql}
        """,
        tuple(params),
    )

    # for origin-comparison plot:
    # keep date range + arrival filter, but ignore departure filter
    where_origin_parts = [
        "date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) BETWEEN ? AND ?"
    ]
    origin_params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    if arrival is not None:
        where_origin_parts.append("f.dest = ?")
        origin_params.append(arrival)

    df_all_origin = _qdf(
        f"""
        SELECT
            f.year,
            f.month,
            f.day,
            f.origin,
            f.dest,
            f.arr_delay,
            f.hour
        FROM flights f
        WHERE {" AND ".join(where_origin_parts)}
        """,
        tuple(origin_params),
    )

    # for destination-comparison plots:
    # keep date range + departure filter, but ignore arrival filter
    where_dest_parts = [
        "date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) BETWEEN ? AND ?"
    ]
    dest_params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    if departure is not None:
        where_dest_parts.append("f.origin = ?")
        dest_params.append(departure)

    df_all_dest = _qdf(
        f"""
        SELECT
            f.year,
            f.month,
            f.day,
            f.origin,
            f.dest,
            f.arr_delay,
            f.hour
        FROM flights f
        WHERE {" AND ".join(where_dest_parts)}
        """,
        tuple(dest_params),
    )

    if df.empty or df["arr_delay"].dropna().empty:
        stats = {
            "delay_pct": 0.0,
            "average_delay": 0.0,
            "average_time_with_delay": 0.0,
        }
        return stats, df, df_all_origin, df_all_dest

    delayed = df[df["arr_delay"] > 0]
    valid_delay_count = df["arr_delay"].count()

    stats = {
        "delay_pct": float(delayed["arr_delay"].count() / valid_delay_count * 100) if valid_delay_count > 0 else 0.0,
        "average_delay": float(df["arr_delay"].mean()) if pd.notna(df["arr_delay"].mean()) else 0.0,
        "average_time_with_delay": float(delayed["arr_delay"].mean()) if not delayed.empty else 0.0,
    }
    return stats, df, df_all_origin, df_all_dest


def delay_pct_by(df: pd.DataFrame, by: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[by, "arr_delay", "delay_count", "delay_pct"])

    total = df.groupby(by, as_index=False)["arr_delay"].count()
    delays = (
        df[df["arr_delay"] > 0]
        .groupby(by, as_index=False)["arr_delay"]
        .count()
        .rename(columns={"arr_delay": "delay_count"})
    )

    out = total.merge(delays, on=by, how="left")
    out["delay_count"] = out["delay_count"].fillna(0)
    out["delay_pct"] = out["delay_count"] / out["arr_delay"] * 100
    return out

def plot_delay_time(df):
    x = df[df["arr_delay"] > 0]
    fig = px.histogram(x, 
                       x='arr_delay', 
                       nbins=400, 
                       range_x= [0, 200],
                       title="Total amount of delays per arrival delay time",
                       labels={'arr_delay': "Arrival delay", 'count': "Total amount of delays"})
    return fig

def plot_delay_month(df: pd.DataFrame):
    x = delay_pct_by(df, "month")
    fig = px.bar(
        x,
        x="month",
        y="delay_pct",
        title="Delay percentage for each month",
        labels={"month": "Month", "delay_pct": "Delay percentage"},
    )
    fig.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1))
    return fig


def plot_delay_hour(df: pd.DataFrame):
    x = delay_pct_by(df, "hour")
    fig = px.bar(
        x,
        x="hour",
        y="delay_pct",
        title="Delay percentage for each hour",
        labels={"hour": "Hour at departure", "delay_pct": "Delay percentage"},
    )
    fig.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1))
    return fig


def plot_delay_chance_dep(df: pd.DataFrame):
    x = delay_pct_by(df, "origin")
    fig = px.bar(
        x,
        x="origin",
        y="delay_pct",
        title="Delay percentage for each origin airport",
        labels={"origin": "Origin airport", "delay_pct": "Delay percentage"},
    )
    return fig


def plot_worst_delay_pct_dest(df: pd.DataFrame):
    x = delay_pct_by(df, "dest").sort_values(by="delay_pct", ascending=False)
    fig = px.bar(
        x.head(10),
        x="dest",
        y="delay_pct",
        title="Worst destination airports by delay percentage",
        labels={"dest": "Destination airport", "delay_pct": "Delay percentage"},
    )
    return fig


def plot_best_delay_pct_dest(df: pd.DataFrame):
    x = delay_pct_by(df, "dest").sort_values(by="delay_pct", ascending=True)
    fig = px.bar(
        x.head(10),
        x="dest",
        y="delay_pct",
        title="Best destination airports by delay percentage",
        labels={"dest": "Destination airport", "delay_pct": "Delay percentage"},
    )
    return fig
