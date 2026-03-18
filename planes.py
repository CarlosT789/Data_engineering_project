#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flights_database.db"


def classify_body_type(row: pd.Series) -> str:
    """
    Classify aircraft as narrow-body / wide-body.

    Practical rule:
    - wide-body if seats >= 250
    - narrow-body otherwise
    - other for non fixed-wing multi-engine aircraft
    - unknown if seats are missing
    """
    seats = row.get("seats")
    aircraft_type = row.get("type")

    if pd.isna(seats):
        return "unknown"

    if pd.notna(aircraft_type) and aircraft_type != "Fixed wing multi engine":
        return "other"

    if seats >= 250:
        return "wide-body"
    return "narrow-body"


def load_plane_data(db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Load flight + plane information needed for the Planes dashboard.
    """
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                f.year,
                f.month,
                f.day,
                f.origin,
                f.dest,
                f.carrier,
                f.tailnum,
                f.distance,
                f.air_time,
                p.type,
                p.manufacturer,
                p.model,
                p.engines,
                p.seats,
                p.speed
            FROM flights f
            LEFT JOIN planes p
                ON f.tailnum = p.tailnum
            """,
            conn,
        )

    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]),
        errors="coerce",
    )
    df["body_type"] = df.apply(classify_body_type, axis=1)
    return df


def apply_plane_filters(
    df: pd.DataFrame,
    origin: Optional[str] = None,
    dest: Optional[str] = None,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    x = df.copy()

    if origin:
        origin = str(origin).upper().strip()
        x = x[x["origin"] == origin]

    if dest:
        dest = str(dest).upper().strip()
        x = x[x["dest"] == dest]

    if start_date is not None:
        x = x[x["date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        x = x[x["date"] <= pd.to_datetime(end_date)]

    return x


def top_models_by_flights(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    out = (
        df.dropna(subset=["model"])
        .groupby("model", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
        .head(n)
    )
    return out


def top_models_by_total_distance(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    out = (
        df.dropna(subset=["model", "distance"])
        .groupby("model", as_index=False)
        .agg(total_distance=("distance", "sum"))
        .sort_values("total_distance", ascending=False)
        .head(n)
    )
    return out


def top_models_by_distance(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Alias kept for dashboard compatibility.
    """
    return top_models_by_total_distance(df, n=n)


def top_models_by_avg_distance(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    out = (
        df.dropna(subset=["model", "distance"])
        .groupby("model", as_index=False)
        .agg(avg_distance=("distance", "mean"))
        .sort_values("avg_distance", ascending=False)
        .head(n)
    )
    return out


def top_manufacturers(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    out = (
        df.dropna(subset=["manufacturer"])
        .groupby("manufacturer", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
        .head(n)
    )
    return out


def average_speed_by_model(df: pd.DataFrame, min_flights: int = 20) -> pd.DataFrame:
    x = df.dropna(subset=["model", "distance", "air_time"]).copy()
    x = x[x["air_time"] > 0]
    x["speed_mph"] = 60 * x["distance"] / x["air_time"]

    out = x.groupby("model", as_index=False).agg(
        avg_speed=("speed_mph", "mean"),
        n_flights=("speed_mph", "size"),
    )

    out = out[out["n_flights"] >= min_flights].copy()
    out["avg_speed"] = out["avg_speed"].round(0).astype(int)
    out = out.sort_values("avg_speed", ascending=False)

    return out


def average_flight_speed(df: pd.DataFrame) -> float:
    x = df.dropna(subset=["distance", "air_time"]).copy()
    x = x[x["air_time"] > 0]
    if x.empty:
        return float("nan")
    avg_speed = (60 * x["distance"] / x["air_time"]).mean()
    return float(round(avg_speed))


def plane_type_counts(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.dropna(subset=["type"])
        .groupby("type", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
    )
    return out


def body_type_counts(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.dropna(subset=["body_type"])
        .groupby("body_type", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
    )
    return out


def plot_top_models_by_flights(df: pd.DataFrame, n: int = 5):
    stats = top_models_by_flights(df, n=n)
    fig = px.bar(
        stats,
        x="model",
        y="n_flights",
        title=f"Top {n} aircraft models by number of flights",
    )
    return fig


def plot_top_models_by_distance(df: pd.DataFrame, n: int = 5):
    stats = top_models_by_total_distance(df, n=n)
    fig = px.bar(
        stats,
        x="model",
        y="total_distance",
        title=f"Top {n} aircraft models by total distance flown",
    )
    return fig


def plot_top_manufacturers(df: pd.DataFrame, n: int = 5):
    stats = top_manufacturers(df, n=n)
    fig = px.bar(
        stats,
        x="manufacturer",
        y="n_flights",
        title=f"Top {n} manufacturers",
    )
    return fig


def plot_average_speed_by_model(df: pd.DataFrame, n: int = 10):
    stats = average_speed_by_model(df).head(n)
    fig = px.bar(
        stats,
        x="model",
        y="avg_speed",
        title=f"Top {n} aircraft models by average speed",
    )
    return fig


def plot_plane_type_distribution(df: pd.DataFrame):
    stats = plane_type_counts(df)
    fig = px.bar(
        stats,
        x="type",
        y="n_flights",
        title="Aircraft type distribution",
    )
    return fig


def plot_body_type_distribution(df: pd.DataFrame):
    stats = body_type_counts(df)
    fig = px.bar(
        stats,
        x="body_type",
        y="n_flights",
        title="Aircraft body type distribution",
    )
    return fig


def plane_type_usage(df: pd.DataFrame) -> dict:
    stats = (
        df.dropna(subset=["type"])
        .groupby("type")
        .size()
        .sort_values(ascending=False)
    )
    return stats.to_dict()


def model_usage(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.dropna(subset=["model"])
        .groupby("model", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
    )
    return out
