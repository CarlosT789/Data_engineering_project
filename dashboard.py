#!/usr/bin/env python3
"""
Part 5 Streamlit Dashboard (NYC flights 2023)

What this app does:
- Loads flight/airport/weather data from flights_database.db (SQLite).
- Provides an opening page with general NYC-flight KPIs + charts.
- Lets the user select departure + arrival airports in the sidebar and shows stats for that combination.
- Performs delay analysis and explores possible causes (time of day + weather variables with good coverage:
  wind_speed, wind_dir, visib).
- Provides a date picker to show airport/route statistics for a specific day.

Notes about missing data:
- Flights: small missingness in dep/arr delays and times (~2–3%): treated as "incomplete/cancel-like" records
  for a simple cancellation proxy.
- Weather: many variables are almost entirely missing (pressure/temp/humid/precip). We primarily use
  wind_speed/wind_dir/visib because they have much better coverage.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional, Tuple, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = Path("flights_database.db")
NYC_ORIGINS = ["EWR", "JFK", "LGA"]


# -----------------------------
# DB helpers
# -----------------------------
def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def qdf(con: sqlite3.Connection, query: str, params: Optional[Tuple[Any, ...]] = None) -> pd.DataFrame:
    if params is None:
        return pd.read_sql(query, con)
    return pd.read_sql(query, con, params=params)


@st.cache_resource
def get_con() -> sqlite3.Connection:
    return connect(DB_PATH)


# -----------------------------
# Cached “dimension” tables
# -----------------------------
@st.cache_data
def load_airports(con: sqlite3.Connection) -> pd.DataFrame:
    return qdf(con, "SELECT faa, name, lat, lon, tz, tzone FROM airports;")

@st.cache_data
def list_destinations(_con):

    query = "SELECT DISTINCT destination FROM flights"
    import pandas as pd
    df = pd.read_sql_query(query, _con)
    return df['destination'].tolist()





# -----------------------------
# KPI / Aggregation queries
# -----------------------------
@st.cache_data
def kpis_overall(con: sqlite3.Connection, origin: Optional[str] = None, dest: Optional[str] = None) -> dict:
    where = ["year = 2023", "origin IN ('EWR','JFK','LGA')"]
    params: List[Any] = []
    if origin and origin != "ALL":
        where.append("origin = ?")
        params.append(origin)
    if dest and dest != "ALL":
        where.append("dest = ?")
        params.append(dest)

    where_sql = " AND ".join(where)

    q = f"""
    SELECT
        COUNT(*) AS n_flights,
        AVG(dep_delay) AS avg_dep_delay,
        AVG(arr_delay) AS avg_arr_delay,
        SUM(CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_dep_delayed_15,
        SUM(CASE WHEN arr_delay > 15 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_arr_delayed_15,
        SUM(CASE WHEN dep_time IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS cancellation_proxy
    FROM flights
    WHERE {where_sql};
    """
    df = qdf(con, q, params=tuple(params) if params else None)
    row = df.iloc[0].to_dict()
    return {
        "n_flights": int(row["n_flights"]) if row["n_flights"] is not None else 0,
        "avg_dep_delay": float(row["avg_dep_delay"]) if row["avg_dep_delay"] is not None else np.nan,
        "avg_arr_delay": float(row["avg_arr_delay"]) if row["avg_arr_delay"] is not None else np.nan,
        "pct_dep_delayed_15": float(row["pct_dep_delayed_15"]) if row["pct_dep_delayed_15"] is not None else np.nan,
        "pct_arr_delayed_15": float(row["pct_arr_delayed_15"]) if row["pct_arr_delayed_15"] is not None else np.nan,
        "cancellation_proxy": float(row["cancellation_proxy"]) if row["cancellation_proxy"] is not None else np.nan,
    }


@st.cache_data
def monthly_delay_trend(con: sqlite3.Connection, origin: Optional[str] = None, dest: Optional[str] = None) -> pd.DataFrame:
    where = ["year = 2023", "origin IN ('EWR','JFK','LGA')"]
    params: List[Any] = []
    if origin and origin != "ALL":
        where.append("origin = ?")
        params.append(origin)
    if dest and dest != "ALL":
        where.append("dest = ?")
        params.append(dest)

    where_sql = " AND ".join(where)

    q = f"""
    SELECT
        month,
        COUNT(*) AS n_flights,
        AVG(dep_delay) AS avg_dep_delay,
        AVG(arr_delay) AS avg_arr_delay,
        SUM(CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_dep_delayed_15
    FROM flights
    WHERE {where_sql}
    GROUP BY month
    ORDER BY month;
    """
    df = qdf(con, q, params=tuple(params) if params else None)
    if not df.empty:
        df["month"] = df["month"].astype(int)
    return df


@st.cache_data
def top_destinations(con: sqlite3.Connection, origin: str, top_n: int = 10) -> pd.DataFrame:
    q = """
    SELECT dest, COUNT(*) AS n_flights, AVG(arr_delay) AS avg_arr_delay
    FROM flights
    WHERE year=2023 AND origin=? AND dest IS NOT NULL
    GROUP BY dest
    ORDER BY n_flights DESC
    LIMIT ?;
    """
    return qdf(con, q, params=(origin, int(top_n)))


@st.cache_data
def hourly_delay_profile(con: sqlite3.Connection, origin: Optional[str], dest: Optional[str]) -> pd.DataFrame:
    where = ["year=2023", "origin IN ('EWR','JFK','LGA')", "hour IS NOT NULL"]
    params: List[Any] = []
    if origin and origin != "ALL":
        where.append("origin = ?")
        params.append(origin)
    if dest and dest != "ALL":
        where.append("dest = ?")
        params.append(dest)

    where_sql = " AND ".join(where)

    q = f"""
    SELECT
        CAST(hour AS INTEGER) AS hour,
        COUNT(*) AS n_flights,
        AVG(dep_delay) AS avg_dep_delay,
        AVG(arr_delay) AS avg_arr_delay,
        SUM(CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_dep_delayed_15
    FROM flights
    WHERE {where_sql}
    GROUP BY CAST(hour AS INTEGER)
    ORDER BY CAST(hour AS INTEGER);
    """
    df = qdf(con, q, params=tuple(params) if params else None)
    if not df.empty:
        df["hour"] = df["hour"].astype(int)
    return df


@st.cache_data
def weather_delay_relation(con: sqlite3.Connection, origin: str) -> pd.DataFrame:
    """
    Join flights with weather at origin/hour resolution.
    Uses wind_speed and visib (good coverage); ignores pressure/temp/etc.
    """
    q = """
    SELECT
        f.month, f.day, CAST(f.hour AS INTEGER) AS hour,
        f.dep_delay, f.arr_delay,
        w.wind_speed, w.wind_dir, w.visib
    FROM flights f
    JOIN weather w
      ON w.origin = f.origin
     AND w.year   = f.year
     AND w.month  = f.month
     AND w.day    = f.day
     AND w.hour   = CAST(f.hour AS INTEGER)
    WHERE f.year = 2023
      AND f.origin = ?
      AND f.hour IS NOT NULL
      AND (f.dep_delay IS NOT NULL OR f.arr_delay IS NOT NULL)
      AND (w.wind_speed IS NOT NULL OR w.visib IS NOT NULL OR w.wind_dir IS NOT NULL);
    """
    df = qdf(con, q, params=(origin,))
    return df


@st.cache_data
def day_stats(con: sqlite3.Connection, date: pd.Timestamp, origin: str, dest: Optional[str]) -> dict:
    y, m, d = int(date.year), int(date.month), int(date.day)

    where = ["year = ?", "month = ?", "day = ?", "origin = ?"]
    params: List[Any] = [y, m, d, origin]
    if dest and dest != "ALL":
        where.append("dest = ?")
        params.append(dest)

    where_sql = " AND ".join(where)

    q = f"""
    SELECT
        COUNT(*) AS n_flights,
        COUNT(DISTINCT dest) AS n_unique_destinations,
        AVG(dep_delay) AS avg_dep_delay,
        AVG(arr_delay) AS avg_arr_delay,
        SUM(CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END) AS dep_delayed_15,
        SUM(CASE WHEN arr_delay > 15 THEN 1 ELSE 0 END) AS arr_delayed_15,
        SUM(CASE WHEN dep_time IS NULL THEN 1 ELSE 0 END) AS cancellation_proxy_n
    FROM flights
    WHERE {where_sql};
    """
    df = qdf(con, q, params=tuple(params))
    row = df.iloc[0].to_dict()

    q2 = f"""
    SELECT dest, COUNT(*) AS n
    FROM flights
    WHERE {where_sql} AND dest IS NOT NULL
    GROUP BY dest
    ORDER BY n DESC
    LIMIT 1;
    """
    top = qdf(con, q2, params=tuple(params))
    top_dest = None if top.empty else (str(top.loc[0, "dest"]), int(top.loc[0, "n"]))

    return {
        "date": f"{y}-{m:02d}-{d:02d}",
        "origin": origin,
        "dest_filter": dest if dest else "ALL",
        "n_flights": int(row["n_flights"]) if row["n_flights"] is not None else 0,
        "n_unique_destinations": int(row["n_unique_destinations"]) if row["n_unique_destinations"] is not None else 0,
        "avg_dep_delay": float(row["avg_dep_delay"]) if row["avg_dep_delay"] is not None else np.nan,
        "avg_arr_delay": float(row["avg_arr_delay"]) if row["avg_arr_delay"] is not None else np.nan,
        "dep_delayed_15": int(row["dep_delayed_15"]) if row["dep_delayed_15"] is not None else 0,
        "arr_delayed_15": int(row["arr_delayed_15"]) if row["arr_delayed_15"] is not None else 0,
        "cancellation_proxy_n": int(row["cancellation_proxy_n"]) if row["cancellation_proxy_n"] is not None else 0,
        "top_destination": top_dest,
    }


@st.cache_data
def day_destinations(con: sqlite3.Connection, date: pd.Timestamp, origin: str) -> pd.DataFrame:
    y, m, d = int(date.year), int(date.month), int(date.day)
    q = """
    SELECT f.dest, COUNT(*) AS n_flights, a.lat, a.lon, a.name
    FROM flights f
    JOIN airports a ON a.faa = f.dest
    WHERE f.year = ?
      AND f.month = ?
      AND f.day = ?
      AND f.origin = ?
      AND f.dest IS NOT NULL
      AND a.lat IS NOT NULL
      AND a.lon IS NOT NULL
    GROUP BY f.dest
    ORDER BY n_flights DESC;
    """
    return qdf(con, q, params=(y, m, d, origin))


# -----------------------------
# Streamlit UI
# -----------------------------
def fmt_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{100.0 * x:.1f}%"


def fmt_min(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:.1f} min"


def main() -> None:
    st.set_page_config(page_title="NYC Flights 2023 Dashboard", layout="wide", initial_sidebar_state="expanded")
    con = get_con()

    # Sidebar controls (minimal requirement)
    st.sidebar.title("Filters")
    origin = st.sidebar.selectbox("Departure (NYC)", ["ALL"] + NYC_ORIGINS, index=1)
    dests = ["ALL"] + list_destinations(con)
    dest = st.sidebar.selectbox("Arrival (destination)", dests, index=0)

    st.sidebar.markdown("---")
    picked_date = st.sidebar.date_input("Pick a date (2023)", value=pd.Timestamp("2023-01-15").date())
    picked_date = pd.Timestamp(picked_date)

    # Main navigation
    st.title("Monitoring Flight Information — NYC (2023)")
    tab_overview, tab_route, tab_delays, tab_day = st.tabs(
        ["Overview", "Route stats (origin+dest)", "Delay analysis", "Day view"]
    )

    # -----------------------------
    # Overview tab (minimal requirement: numeric + chart)
    # -----------------------------
    with tab_overview:
        st.header("Overview")
        k = kpis_overall(con, origin=origin, dest=dest)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Flights", f"{k['n_flights']:,}")
        c2.metric("Avg dep delay", fmt_min(k["avg_dep_delay"]))
        c3.metric("Avg arr delay", fmt_min(k["avg_arr_delay"]))
        c4.metric("Dep delayed >15", fmt_pct(k["pct_dep_delayed_15"]))
        c5.metric("Cancel proxy (dep_time missing)", fmt_pct(k["cancellation_proxy"]))

        st.subheader("Monthly trend")
        df_m = monthly_delay_trend(con, origin=origin, dest=dest)
        if df_m.empty:
            st.info("No data for the current filter.")
        else:
            fig = px.line(
                df_m,
                x="month",
                y="avg_dep_delay",
                markers=True,
                title="Average departure delay by month",
                labels={"month": "Month", "avg_dep_delay": "Avg dep delay (min)"},
            )
            st.plotly_chart(fig, use_container_width=True)

            fig2 = px.bar(
                df_m,
                x="month",
                y="n_flights",
                title="Number of flights by month",
                labels={"month": "Month", "n_flights": "Flights"},
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Top destinations from NYC airports")
        if origin == "ALL":
            st.caption("Pick a specific NYC origin in the sidebar to see top destinations.")
        else:
            df_top = top_destinations(con, origin=origin, top_n=10)
            fig3 = px.bar(
                df_top,
                x="dest",
                y="n_flights",
                title=f"Top 10 destinations from {origin}",
                hover_data={"avg_arr_delay": True},
            )
            st.plotly_chart(fig3, use_container_width=True)

    # -----------------------------
    # Route stats tab (origin+dest combination)
    # -----------------------------
    with tab_route:
        st.header("Route statistics (departure + arrival combination)")
        st.caption("These KPIs and charts update based on the sidebar selection of origin + destination.")

        k2 = kpis_overall(con, origin=origin, dest=dest)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Flights", f"{k2['n_flights']:,}")
        r2.metric("Avg dep delay", fmt_min(k2["avg_dep_delay"]))
        r3.metric("Avg arr delay", fmt_min(k2["avg_arr_delay"]))
        r4.metric("Arr delayed >15", fmt_pct(k2["pct_arr_delayed_15"]))

        st.subheader("Hour-of-day profile")
        df_h = hourly_delay_profile(con, origin=origin, dest=dest)
        if df_h.empty:
            st.info("No hour-level data for the current filter.")
        else:
            fig_h = px.line(
                df_h,
                x="hour",
                y="avg_dep_delay",
                markers=True,
                title="Average departure delay by hour",
                labels={"hour": "Hour", "avg_dep_delay": "Avg dep delay (min)"},
            )
            st.plotly_chart(fig_h, use_container_width=True)

            fig_h2 = px.bar(
                df_h,
                x="hour",
                y="pct_dep_delayed_15",
                title="Share of flights delayed > 15 min by hour",
                labels={"hour": "Hour", "pct_dep_delayed_15": "Share"},
            )
            st.plotly_chart(fig_h2, use_container_width=True)

    # -----------------------------
    # Delay analysis tab (minimal requirement)
    # -----------------------------
    with tab_delays:
        st.header("Delay analysis and possible causes")
        st.caption("Because weather columns like pressure/temp/humidity are mostly missing, we focus on wind and visibility.")

        if origin == "ALL":
            st.info("Pick a specific NYC departure airport (EWR/JFK/LGA) in the sidebar for weather analysis.")
        else:
            with st.spinner("Joining flights with weather (cached after first run)..."):
                df_w = weather_delay_relation(con, origin=origin)

            if df_w.empty:
                st.warning("No weather-joined data available for this origin.")
            else:
                # Clean
                for col in ["dep_delay", "arr_delay", "wind_speed", "visib", "wind_dir"]:
                    if col in df_w.columns:
                        df_w[col] = pd.to_numeric(df_w[col], errors="coerce")

                st.subheader("Wind speed vs departure delay")
                df_plot = df_w.dropna(subset=["wind_speed", "dep_delay"]).copy()
                if df_plot.empty:
                    st.info("Not enough data for wind_speed vs dep_delay.")
                else:
                    # Bin wind speed to avoid huge scatter
                    df_plot["wind_bin"] = pd.cut(df_plot["wind_speed"], bins=8)
                    df_bin = df_plot.groupby("wind_bin", dropna=True)["dep_delay"].agg(["count", "mean", "median"]).reset_index()
                    fig_ws = px.bar(
                        df_bin,
                        x="wind_bin",
                        y="mean",
                        title="Mean departure delay by wind-speed bin",
                        labels={"wind_bin": "Wind speed bin", "mean": "Mean dep delay (min)"},
                        hover_data={"count": True, "median": True},
                    )
                    st.plotly_chart(fig_ws, use_container_width=True)

                st.subheader("Visibility vs departure delay")
                df_plot2 = df_w.dropna(subset=["visib", "dep_delay"]).copy()
                if df_plot2.empty:
                    st.info("Not enough data for visib vs dep_delay.")
                else:
                    df_plot2["visib_bin"] = pd.cut(df_plot2["visib"], bins=8)
                    df_bin2 = df_plot2.groupby("visib_bin", dropna=True)["dep_delay"].agg(["count", "mean", "median"]).reset_index()
                    fig_vis = px.bar(
                        df_bin2,
                        x="visib_bin",
                        y="mean",
                        title="Mean departure delay by visibility bin",
                        labels={"visib_bin": "Visibility bin", "mean": "Mean dep delay (min)"},
                        hover_data={"count": True, "median": True},
                    )
                    st.plotly_chart(fig_vis, use_container_width=True)

                st.subheader("Time-of-day effect (again, but focused on delays)")
                df_h = hourly_delay_profile(con, origin=origin, dest=dest)
                if not df_h.empty:
                    fig = px.line(
                        df_h,
                        x="hour",
                        y="pct_dep_delayed_15",
                        markers=True,
                        title="Share delayed >15 min by hour",
                        labels={"hour": "Hour", "pct_dep_delayed_15": "Share"},
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Day tab (minimal requirement: date-based stats)
    # -----------------------------
    with tab_day:
        st.header("Day view (date-based statistics)")
        if origin == "ALL":
            st.info("Pick a specific NYC departure airport in the sidebar to use the day view.")
        else:
            stats = day_stats(con, picked_date, origin=origin, dest=dest)
            a1, a2, a3, a4, a5 = st.columns(5)
            a1.metric("Date", stats["date"])
            a2.metric("Flights", f"{stats['n_flights']:,}")
            a3.metric("Unique destinations", f"{stats['n_unique_destinations']:,}")
            a4.metric("Avg dep delay", fmt_min(stats["avg_dep_delay"]))
            a5.metric("Cancel proxy (count)", f"{stats['cancellation_proxy_n']:,}")

            if stats["top_destination"] is not None:
                st.write(f"Top destination: **{stats['top_destination'][0]}** ({stats['top_destination'][1]:,} flights)")

            st.subheader("Destinations map (bubble size = flights to destination)")
            df_map = day_destinations(con, picked_date, origin=origin)
            if df_map.empty:
                st.info("No destination data for this day.")
            else:
                fig = px.scatter_geo(
                    df_map.head(200),  # keep browser responsive
                    lat="lat",
                    lon="lon",
                    size="n_flights",
                    hover_name="dest",
                    hover_data={"name": True, "n_flights": True, "lat": False, "lon": False},
                    title=f"Destinations from {origin} on {stats['date']}",
                )
                fig.update_geos(showland=True)
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Top 15 destinations (table)")
                st.dataframe(df_map[["dest", "n_flights", "name"]].head(15), use_container_width=True)


if __name__ == "__main__":
    main()