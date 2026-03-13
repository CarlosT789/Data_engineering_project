#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flights_database.db"


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
    return df


def apply_plane_filters(
    df: pd.DataFrame,
    origin: Optional[str] = None,
    dest: Optional[str] = None,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """
    Apply dashboard filters to the plane dataframe.
    """
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
    """
    Top aircraft models by number of flights.
    """
    out = (
        df.dropna(subset=["model"])
        .groupby("model", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
        .head(n)
    )
    return out


def top_models_by_distance(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Top aircraft models by total distance flown.
    """
    out = (
        df.dropna(subset=["model", "distance"])
        .groupby("model", as_index=False)
        .agg(total_distance=("distance", "sum"))
        .sort_values("total_distance", ascending=False)
        .head(n)
    )
    return out


def top_models_by_avg_distance(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Top aircraft models by average distance per flight.
    """
    out = (
        df.dropna(subset=["model", "distance"])
        .groupby("model", as_index=False)
        .agg(avg_distance=("distance", "mean"))
        .sort_values("avg_distance", ascending=False)
        .head(n)
    )
    return out


def top_manufacturers(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Top manufacturers by number of flights.
    """
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
    """
    Average speed per aircraft model based on distance / air_time.
    Speed is in miles per hour.
    """
    x = df.dropna(subset=["model", "distance", "air_time"]).copy()
    x = x[x["air_time"] > 0]
    x["speed_mph"] = 60 * x["distance"] / x["air_time"]

    out = (
        x.groupby("model", as_index=False)
        .agg(
            avg_speed=("speed_mph", "mean"),
            n_flights=("speed_mph", "size"),
        )
    )

    out = out[out["n_flights"] >= min_flights]
    out = out.sort_values("avg_speed", ascending=False)

    return out


def average_flight_speed(df: pd.DataFrame) -> float:
    """
    Average flight speed across all filtered flights.
    """
    x = df.dropna(subset=["distance", "air_time"]).copy()
    x = x[x["air_time"] > 0]
    if x.empty:
        return float("nan")
    return float((60 * x["distance"] / x["air_time"]).mean())


def plane_type_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Distribution of aircraft types by number of flights.
    """
    out = (
        df.dropna(subset=["type"])
        .groupby("type", as_index=False)
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
        text="n_flights",
    )
    return fig


def plot_top_models_by_distance(df: pd.DataFrame, n: int = 5):
    stats = top_models_by_distance(df, n=n)
    fig = px.bar(
        stats,
        x="model",
        y="total_distance",
        title=f"Top {n} aircraft models by total distance flown",
        text="total_distance",
    )
    return fig


def plot_top_manufacturers(df: pd.DataFrame, n: int = 5):
    stats = top_manufacturers(df, n=n)
    fig = px.bar(
        stats,
        x="manufacturer",
        y="n_flights",
        title=f"Top {n} manufacturers",
        text="n_flights",
    )
    return fig


def plot_average_speed_by_model(df: pd.DataFrame, n: int = 10):
    stats = average_speed_by_model(df).head(n)
    fig = px.bar(
        stats,
        x="model",
        y="avg_speed",
        title=f"Top {n} aircraft models by average speed",
        text="avg_speed",
    )
    return fig


def plot_plane_type_distribution(df: pd.DataFrame):
    stats = plane_type_counts(df)
    fig = px.bar(
        stats,
        x="type",
        y="n_flights",
        title="Aircraft type distribution",
        text="n_flights",
    )
    return fig


def plane_type_usage(df: pd.DataFrame) -> dict:
    """
    Aircraft type usage as a dictionary.
    """
    stats = (
        df.dropna(subset=["type"])
        .groupby("type")
        .size()
        .sort_values(ascending=False)
    )
    return stats.to_dict()


def model_usage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aircraft model usage counts.
    """
    out = (
        df.dropna(subset=["model"])
        .groupby("model", as_index=False)
        .size()
        .rename(columns={"size": "n_flights"})
        .sort_values("n_flights", ascending=False)
    )
    return out