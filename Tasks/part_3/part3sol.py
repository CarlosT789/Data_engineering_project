#!/usr/bin/env python3

from __future__ import annotations

import math
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


#utilize for reading #Question 1
#sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'part_1'))
#

#from Part1e import geodesic_distance_km
#db_path = os.path.join(os.path.dirname(__file__), '..','..', 'data', 'flights_database.db')
#connection = sqlite3.connect(db_path)

DB_PATH = Path("flights_database.db")
OUT_DIR = Path("outputs_part3")

EARTH_RADIUS_KM = 6371.0
KM_TO_MILES = 0.621371


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

#use cursor to access .db
def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    #cursor = con.cursor()
    con.row_factory = sqlite3.Row
    return con


def qdf(con: sqlite3.Connection, query: str, params: Optional[Tuple[Any, ...]] = None) -> pd.DataFrame:
    """Query -> pandas DataFrame (recommended pattern in the lectures)."""
    if params is None:
        return pd.read_sql(query, con)
    return pd.read_sql(query, con, params=params)


def save_html(fig: go.Figure, filename: str) -> Path:
    ensure_out_dir()
    path = OUT_DIR / filename
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path


def deg2rad(x: float) -> float:
    return x * math.pi / 180.0


def approx_geodesic_km(lat1: float, lon1: float, lat2: float, lon2: float, R_km: float = EARTH_RADIUS_KM) -> float:
    phi1 = deg2rad(lat1)
    phi2 = deg2rad(lat2)
    lam1 = deg2rad(lon1)
    lam2 = deg2rad(lon2)

    dphi = phi2 - phi1
    dlam = lam2 - lam1
    phi_m = 0.5 * (phi1 + phi2)

    term1 = 2.0 * math.sin(dphi / 2.0) * math.cos(dlam / 2.0)
    term2 = 2.0 * math.cos(phi_m) * math.sin(dlam / 2.0)
    return R_km * math.sqrt(term1 * term1 + term2 * term2)


def bearing_rad(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = deg2rad(lat1)
    phi2 = deg2rad(lat2)
    lam1 = deg2rad(lon1)
    lam2 = deg2rad(lon2)

    dlam = lam2 - lam1
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return math.atan2(y, x)


def unit_vector_from_bearing(theta: float) -> Tuple[float, float]:
    return (math.cos(theta), math.sin(theta))


# Task 1
def task_verify_distance(con: sqlite3.Connection, sample_n: int = 5000) -> pd.DataFrame:
    q = f"""
    SELECT f.origin, f.dest, f.distance,
           ao.lat AS o_lat, ao.lon AS o_lon,
           ad.lat AS d_lat, ad.lon AS d_lon
    FROM flights f
    JOIN airports ao ON ao.faa = f.origin
    JOIN airports ad ON ad.faa = f.dest
    WHERE f.distance IS NOT NULL
      AND ao.lat IS NOT NULL AND ao.lon IS NOT NULL
      AND ad.lat IS NOT NULL AND ad.lon IS NOT NULL
    ORDER BY RANDOM()
    LIMIT {int(sample_n)};
    """
    df = qdf(con, q)

    # compute
    computed_miles = []
    for _, r in df.iterrows():
        km = approx_geodesic_km(float(r["o_lat"]), float(r["o_lon"]), float(r["d_lat"]), float(r["d_lon"]))
        computed_miles.append(km * KM_TO_MILES)
    df["computed_distance_miles"] = computed_miles
    df["abs_diff"] = (df["distance"] - df["computed_distance_miles"]).abs()
    df["pct_diff"] = df["abs_diff"] / df["distance"].replace(0, np.nan) * 100.0

    print("\n[Task] Verify distance vs flights.distance (sample)")
    print(f"Sample size: {len(df):,}")
    print(f"Mean abs diff (miles): {df['abs_diff'].mean():.2f}")
    print(f"Median abs diff (miles): {df['abs_diff'].median():.2f}")
    print(f"Mean % diff: {df['pct_diff'].mean():.2f}%")

    return df

# Task 2
def task_nyc_origins(con: sqlite3.Connection) -> pd.DataFrame:
    q = """
    SELECT DISTINCT origin AS faa
    FROM flights
    WHERE origin IS NOT NULL
    ORDER BY origin;
    """
    origins = qdf(con, q)

    q2 = """
    SELECT a.faa, a.name, a.lat, a.lon
    FROM airports a
    JOIN (
        SELECT DISTINCT origin AS faa
        FROM flights
        WHERE origin IS NOT NULL
    ) o
    ON o.faa = a.faa
    ORDER BY a.faa;
    """
    df = qdf(con, q2)

    print("\n[Task] NYC origin airports found in flights.origin")
    print(df.to_string(index=False))

    df.to_csv(OUT_DIR / "nyc_origin_airports.csv", index=False)
    return df

# Task 3
def task_day_destinations_map(con: sqlite3.Connection, year: int, month: int, day: int, origin: str) -> pd.DataFrame:
    q = """
    SELECT f.dest, COUNT(*) AS n_flights,
           a.lat, a.lon, a.name
    FROM flights f
    JOIN airports a ON a.faa = f.dest
    WHERE f.year = ?
      AND f.month = ?
      AND f.day = ?
      AND f.origin = ?
      AND f.dest IS NOT NULL
      AND a.lat IS NOT NULL AND a.lon IS NOT NULL
    GROUP BY f.dest
    ORDER BY n_flights DESC;
    """
    df = qdf(con, q, params=(year, month, day, origin))

    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        size="n_flights",
        hover_name="dest",
        hover_data={"name": True, "n_flights": True, "lat": False, "lon": False},
        title=f"Destinations from {origin} on {year}-{month:02d}-{day:02d}",
    )
    fig.update_geos(showland=True)
    save_html(fig, f"01_destinations_{origin}_{year}_{month:02d}_{day:02d}.html")

    return df

# Task 4
def task_day_stats(con: sqlite3.Connection, year: int, month: int, day: int, origin: str) -> Dict[str, Any]:
    q = """
    SELECT
        COUNT(*) AS n_flights,
        COUNT(DISTINCT dest) AS n_unique_destinations,
        AVG(dep_delay) AS avg_dep_delay,
        AVG(arr_delay) AS avg_arr_delay,
        SUM(CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END) AS dep_delayed_15,
        SUM(CASE WHEN arr_delay > 15 THEN 1 ELSE 0 END) AS arr_delayed_15
    FROM flights
    WHERE year = ?
      AND month = ?
      AND day = ?
      AND origin = ?;
    """
    df = qdf(con, q, params=(year, month, day, origin))
    stats = df.iloc[0].to_dict()

    q2 = """
    SELECT dest, COUNT(*) AS n
    FROM flights
    WHERE year = ?
      AND month = ?
      AND day = ?
      AND origin = ?
      AND dest IS NOT NULL
    GROUP BY dest
    ORDER BY n DESC
    LIMIT 1;
    """
    top = qdf(con, q2, params=(year, month, day, origin))
    top_dest = (None, None) if top.empty else (top.loc[0, "dest"], int(top.loc[0, "n"]))

    stats_out = {
        "date": f"{year}-{month:02d}-{day:02d}",
        "origin": origin,
        "n_flights": int(stats["n_flights"]),
        "n_unique_destinations": int(stats["n_unique_destinations"]),
        "top_destination": top_dest,
        "avg_dep_delay": float(stats["avg_dep_delay"]) if stats["avg_dep_delay"] is not None else None,
        "avg_arr_delay": float(stats["avg_arr_delay"]) if stats["avg_arr_delay"] is not None else None,
        "dep_delayed_15": float(stats["dep_delayed_15"]) if stats["dep_delayed_15"] is not None else None,
        "arr_delayed_15": float(stats["arr_delayed_15"]) if stats["arr_delayed_15"] is not None else None,
    }

    print("\n[Task] Example day stats")
    for k, v in stats_out.items():
        print(f"{k}: {v}")

    return stats_out

# Task 5
def task_most_common_route_and_plane_types(con: sqlite3.Connection) -> Tuple[str, str, pd.DataFrame]:
    q = """
    SELECT origin, dest, COUNT(*) AS n
    FROM flights
    WHERE origin IS NOT NULL AND dest IS NOT NULL
    GROUP BY origin, dest
    ORDER BY n DESC
    LIMIT 1;
    """
    r = qdf(con, q).iloc[0]
    origin, dest = str(r["origin"]), str(r["dest"])

    q2 = """
    SELECT p.engine AS plane_type, COUNT(*) AS n_flights
    FROM flights f
    JOIN planes p ON p.tailnum = f.tailnum
    WHERE f.origin = ?
      AND f.dest = ?
      AND p.engine IS NOT NULL
    GROUP BY p.engine
    ORDER BY n_flights DESC;
    """
    df = qdf(con, q2, params=(origin, dest))

    print("\n[Task] Example plane types for most common route")
    print(f"Route: {origin} -> {dest}")
    print(dict(zip(df["plane_type"].tolist(), df["n_flights"].tolist())))

    return origin, dest, df

# Task 6
def task_delayed_flights_to_dest_in_months(
    con: sqlite3.Connection,
    dest: str,
    months: Iterable[int] = (6, 7, 8),
    delay_threshold: int = 15,
) -> int:
    months = tuple(int(m) for m in months)
    placeholders = ",".join(["?"] * len(months))

    q = f"""
    SELECT COUNT(*) AS n
    FROM flights
    WHERE dest = ?
      AND month IN ({placeholders})
      AND (
            (dep_delay IS NOT NULL AND dep_delay > ?)
         OR (arr_delay IS NOT NULL AND arr_delay > ?)
      );
    """
    params: Tuple[Any, ...] = (dest, *months, delay_threshold, delay_threshold)
    df = qdf(con, q, params=params)
    n = int(df.iloc[0]["n"])

    print(f"\n[Task] Example delayed flights count")
    print(f"Destination: {dest}, months {months[0]}–{months[-1]}, delayed (dep or arr > {delay_threshold}): {n:,}")
    return n

# Task 7
def task_top_manufacturers_for_dest(con: sqlite3.Connection, dest: str, top_n: int = 5) -> pd.DataFrame:
    q = f"""
    SELECT p.manufacturer, COUNT(*) AS n_flights
    FROM flights f
    JOIN planes p ON p.tailnum = f.tailnum
    WHERE f.dest = ?
      AND p.manufacturer IS NOT NULL
    GROUP BY p.manufacturer
    ORDER BY n_flights DESC
    LIMIT {int(top_n)};
    """
    df = qdf(con, q, params=(dest,))

    print("\n[Task] Top 5 manufacturers for destination (example)")
    print(f"Destination: {dest}")
    print(df.to_string(index=False))

    fig = px.bar(df, x="manufacturer", y="n_flights", title=f"Top {top_n} manufacturers for flights to {dest}")
    save_html(fig, f"02_top_{top_n}_manufacturers_{dest}.html")
    return df

# Task 8
def task_distance_vs_arrival_delay(con: sqlite3.Connection, sample_n: int = 20000) -> pd.DataFrame:
    """
    Investigate relationship between distance and arrival delay.

    Note:
    Plotly's built-in `trendline="ols"` requires the external `statsmodels` package.
    To keep the project dependency-light, we fit and draw a simple linear trendline
    using NumPy instead.
    """
    query = f"""
    SELECT distance, arr_delay
    FROM flights
    WHERE distance IS NOT NULL AND arr_delay IS NOT NULL
    ORDER BY RANDOM()
    LIMIT {int(sample_n)};
    """
    df = qdf(con, query)
    corr = df["distance"].corr(df["arr_delay"])

    print("\n[Task] Distance vs arrival delay")
    print(f"Sample size: {len(df):,}")
    print(f"Pearson correlation(distance, arr_delay): {corr:.4f}")

    fig = px.scatter(
        df,
        x="distance",
        y="arr_delay",
        title=f"Distance vs arrival delay (sample={len(df):,}, corr={corr:.3f})",
        opacity=0.5,
    )

    x = df["distance"].to_numpy(dtype=float)
    y = df["arr_delay"].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) >= 2:
        m, b = np.polyfit(x, y, 1)
        x_line = np.array([x.min(), x.max()])
        y_line = m * x_line + b
        fig.add_trace(go.Scatter(x=x_line, y=y_line, mode="lines", name="Linear fit (NumPy)"))

    save_html(fig, "03_distance_vs_arrival_delay.html")
    return df

# Task 9
def task_update_planes_speed(con: sqlite3.Connection) -> pd.DataFrame:

    q = """
    SELECT p.model,
           MAX( (f.distance * 60.0) / f.air_time ) AS max_mph
    FROM flights f
    JOIN planes p ON p.tailnum = f.tailnum
    WHERE f.distance IS NOT NULL
      AND f.air_time IS NOT NULL
      AND f.air_time > 0
      AND p.model IS NOT NULL
    GROUP BY p.model;
    """
    df = qdf(con, q)
    df = df.dropna(subset=["model", "max_mph"]).copy()
    df["max_mph"] = df["max_mph"].astype(float)

    cur = con.cursor()
    updated = 0
    for _, r in df.iterrows():
        model = str(r["model"])
        speed = float(r["max_mph"])
        cur.execute("UPDATE planes SET speed = ? WHERE model = ?;", (speed, model))
        updated += cur.rowcount
    con.commit()

    print("\n[Task] Update planes.speed")
    print(f"Computed max mph for {len(df):,} models.")
    print(f"Rows updated in planes table: {updated:,}")

    df_out = df.sort_values("max_mph", ascending=False).head(20)
    df_out.to_csv(OUT_DIR / "planes_model_max_mph_top20.csv", index=False)

    fig = px.bar(df_out, x="model", y="max_mph", title="Top 20 plane models by max observed mph")
    fig.update_layout(xaxis_tickangle=-45)
    save_html(fig, "04_top20_models_max_mph.html")

    return df


@dataclass(frozen=True)
class FlightKey:
    year: int
    month: int
    day: int
    origin: str
    dest: str
    carrier: str
    flight: int
    hour: int


def inner_product_flight_wind(con: sqlite3.Connection, key: FlightKey) -> float:

    # Get airports coords
    q_air = """
    SELECT ao.lat AS o_lat, ao.lon AS o_lon,
           ad.lat AS d_lat, ad.lon AS d_lon
    FROM airports ao
    JOIN airports ad
      ON ad.faa = ?
    WHERE ao.faa = ?;
    """
    df_air = qdf(con, q_air, params=(key.dest, key.origin))
    if df_air.empty:
        raise ValueError("Could not find airport coordinates for origin/dest.")
    r = df_air.iloc[0]
    o_lat, o_lon, d_lat, d_lon = float(r["o_lat"]), float(r["o_lon"]), float(r["d_lat"]), float(r["d_lon"])

    # Bearing and flight unit vector
    theta = bearing_rad(o_lat, o_lon, d_lat, d_lon)
    fx, fy = unit_vector_from_bearing(theta)

    # Weather row: hour-level (origin airport)
    q_w = """
    SELECT wind_dir, wind_speed
    FROM weather
    WHERE year = ?
      AND month = ?
      AND day = ?
      AND hour = ?
      AND origin = ?
      AND wind_dir IS NOT NULL
      AND wind_speed IS NOT NULL
    LIMIT 1;
    """
    df_w = qdf(con, q_w, params=(key.year, key.month, key.day, key.hour, key.origin))
    if df_w.empty:
        raise ValueError("No wind data for flight key.")
    wdir_from = float(df_w.loc[0, "wind_dir"])
    wspeed = float(df_w.loc[0, "wind_speed"])


    wdir_to = (wdir_from + 180.0) % 360.0
    wx, wy = unit_vector_from_bearing(deg2rad(wdir_to))

    return (fx * wx + fy * wy) * wspeed


def task_inner_product_vs_air_time(con: sqlite3.Connection, sample_n: int = 15000) -> pd.DataFrame:

    q = f"""
    SELECT year, month, day, origin, dest, carrier, flight, CAST(hour AS INTEGER) AS hour, air_time
    FROM flights
    WHERE year=2023
      AND origin IS NOT NULL AND dest IS NOT NULL
      AND carrier IS NOT NULL AND flight IS NOT NULL
      AND hour IS NOT NULL
      AND air_time IS NOT NULL AND air_time > 0
    ORDER BY RANDOM()
    LIMIT {int(sample_n)};
    """
    df = qdf(con, q)

    inners: List[Optional[float]] = []
    for _, r in df.iterrows():
        try:
            key = FlightKey(
                year=int(r["year"]),
                month=int(r["month"]),
                day=int(r["day"]),
                origin=str(r["origin"]),
                dest=str(r["dest"]),
                carrier=str(r["carrier"]),
                flight=int(r["flight"]),
                hour=int(r["hour"]),
            )
            inners.append(inner_product_flight_wind(con, key))
        except Exception:
            inners.append(None)

    df["wind_inner"] = inners
    df = df.dropna(subset=["wind_inner"]).copy()

    if df.empty:
        print("\n[Task] Inner product vs air_time: no rows with wind data after filtering.")
        return df

    df["wind_inner_sign"] = pd.cut(
        df["wind_inner"],
        bins=[-1e9, -1e-9, 1e-9, 1e9],
        labels=["headwind (neg)", "near zero", "tailwind (pos)"],
    )

    summary = df.groupby("wind_inner_sign")["air_time"].agg(["count", "mean", "median"])
    print("\n[Task] Inner product sign vs air_time (sample)")
    print(summary.to_string())

    fig = px.box(
        df,
        x="wind_inner_sign",
        y="air_time",
        title="Air time by wind inner-product sign (headwind vs tailwind)",
    )
    save_html(fig, "05_air_time_by_wind_inner_sign.html")

    fig2 = px.scatter(
        df,
        x="wind_inner",
        y="air_time",
        title="Air time vs wind inner product (tailwind component)",
        opacity=0.5,
    )


    x2 = df["wind_inner"].to_numpy(dtype=float)
    y2 = df["air_time"].to_numpy(dtype=float)
    mask2 = np.isfinite(x2) & np.isfinite(y2)
    x2 = x2[mask2]
    y2 = y2[mask2]
    if len(x2) >= 2:
        m2, b2 = np.polyfit(x2, y2, 1)
        x2_line = np.array([x2.min(), x2.max()])
        y2_line = m2 * x2_line + b2
        fig2.add_trace(go.Scatter(x=x2_line, y=y2_line, mode="lines", name="Linear fit (NumPy)"))

    save_html(fig2, "06_air_time_vs_wind_inner.html")
    return df


def main() -> None:
    ensure_out_dir()
    con = connect()

    task_verify_distance(con)

    nyc_airports = task_nyc_origins(con)

    y, m, d, o = 2023, 1, 15, "EWR"
    task_day_destinations_map(con, y, m, d, o)
    task_day_stats(con, y, m, d, o)

    task_most_common_route_and_plane_types(con)

    task_delayed_flights_to_dest_in_months(con, dest="BOS", months=(6, 7, 8), delay_threshold=15)

    task_top_manufacturers_for_dest(con, dest="BOS", top_n=5)

    task_distance_vs_arrival_delay(con, sample_n=20000)

    task_update_planes_speed(con)

    task_inner_product_vs_air_time(con, sample_n=15000)

    con.close()
    print(f"\nDone. Outputs saved to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
