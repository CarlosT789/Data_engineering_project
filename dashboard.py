#!/usr/bin/env python3
from __future__ import annotations

import math
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from noise import get_real_noise_data
from co2 import get_real_co2_data
from delay import (
    get_real_delay_data,
    plot_delay_time,
    plot_delay_month,
    plot_delay_hour,
    plot_delay_chance_dep,
    plot_worst_delay_pct_dest,
    plot_best_delay_pct_dest,
)
from planes import (
    load_plane_data,
    apply_plane_filters,
    average_flight_speed,
    plot_top_models_by_flights,
    plot_top_models_by_distance,
    plot_top_manufacturers,
    plot_average_speed_by_model,
    plot_plane_type_distribution,
    plot_body_type_distribution,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "flights_database.db"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database file not found at: {DB_PATH}\n"
            f"Put flights_database.db in the same folder as dashboard.py "
            f"or change DB_PATH."
        )
    return sqlite3.connect(str(DB_PATH))


def qdf(query: str, params: tuple = ()) -> pd.DataFrame:
    with get_connection() as con:
        return pd.read_sql_query(query, con, params=params)


@st.cache_data(show_spinner=False)
def get_table_names() -> List[str]:
    with get_connection() as con:
        df = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """,
            con,
        )
    return df["name"].tolist()


@st.cache_data(show_spinner=False)
def get_plane_data() -> pd.DataFrame:
    return load_plane_data(DB_PATH)


def validate_database() -> None:
    tables = get_table_names()
    required = {"flights", "airports"}
    missing = required - set(tables)

    if missing:
        raise RuntimeError(
            f"Connected to database file: {DB_PATH}\n"
            f"But required tables are missing: {sorted(missing)}\n"
            f"Tables actually found: {tables}"
        )


@st.cache_data(show_spinner=False)
def get_date_bounds() -> Tuple[date, date]:
    df = qdf(
        """
        SELECT
            MIN(date(printf('%04d-%02d-%02d', year, month, day))) AS min_date,
            MAX(date(printf('%04d-%02d-%02d', year, month, day))) AS max_date
        FROM flights
        """
    )

    if df.empty or pd.isna(df.loc[0, "min_date"]) or pd.isna(df.loc[0, "max_date"]):
        raise RuntimeError("Could not read min/max dates from flights table.")

    min_date = pd.to_datetime(df.loc[0, "min_date"]).date()
    max_date = pd.to_datetime(df.loc[0, "max_date"]).date()
    return min_date, max_date


@st.cache_data(show_spinner=False)
def get_all_airports() -> pd.DataFrame:
    return qdf(
        """
        SELECT faa, name, lat, lon, alt, tz, dst, tzone
        FROM airports
        WHERE faa IS NOT NULL
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        ORDER BY faa
        """
    )


@st.cache_data(show_spinner=False)
def get_all_filter_airports() -> pd.DataFrame:
    return qdf(
        """
        SELECT DISTINCT a.faa, a.name, a.lat, a.lon
        FROM airports a
        WHERE a.faa IN (
            SELECT origin FROM flights WHERE origin IS NOT NULL
            UNION
            SELECT dest FROM flights WHERE dest IS NOT NULL
        )
          AND a.lat IS NOT NULL
          AND a.lon IS NOT NULL
        ORDER BY a.faa
        """
    )


@st.cache_data(show_spinner=False)
def get_departure_filter_airports() -> pd.DataFrame:
    return qdf(
        """
        SELECT DISTINCT a.faa, a.name, a.lat, a.lon
        FROM airports a
        WHERE a.faa IN (
            SELECT origin
            FROM flights
            WHERE origin IS NOT NULL
        )
          AND a.lat IS NOT NULL
          AND a.lon IS NOT NULL
        ORDER BY a.faa
        """
    )


@st.cache_data(show_spinner=False)
def get_airport_by_faa(faa: str) -> Optional[Dict]:
    df = qdf(
        """
        SELECT faa, name, lat, lon
        FROM airports
        WHERE faa = ?
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        LIMIT 1
        """,
        (faa,),
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def get_summary_stats(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
) -> Dict[str, Optional[float]]:
    where_parts = [
        "date(printf('%04d-%02d-%02d', year, month, day)) BETWEEN ? AND ?"
    ]
    params: List[object] = [start_date.isoformat(), end_date.isoformat()]

    if departure is not None:
        where_parts.append("origin = ?")
        params.append(departure)

    if arrival is not None:
        where_parts.append("dest = ?")
        params.append(arrival)

    where_sql = " AND ".join(where_parts)

    df = qdf(
        f"""
        SELECT
            COUNT(*) AS total_flights,
            AVG(air_time) AS avg_duration,
            AVG(dep_delay) AS avg_dep_delay,
            AVG(arr_delay) AS avg_arr_delay,
            SUM(distance) AS total_distance_miles
        FROM flights
        WHERE {where_sql}
        """,
        tuple(params),
    )

    row = df.iloc[0].to_dict()

    total_distance_miles = float(row["total_distance_miles"]) if pd.notna(row["total_distance_miles"]) else 0.0
    total_distance_km = total_distance_miles * 1.60934
    earth_circumference_km = 40075.0
    around_earth = total_distance_km / earth_circumference_km if earth_circumference_km > 0 else 0.0

    return {
        "total_flights": int(row["total_flights"]) if pd.notna(row["total_flights"]) else 0,
        "avg_duration": float(row["avg_duration"]) if pd.notna(row["avg_duration"]) else None,
        "avg_dep_delay": float(row["avg_dep_delay"]) if pd.notna(row["avg_dep_delay"]) else None,
        "avg_arr_delay": float(row["avg_arr_delay"]) if pd.notna(row["avg_arr_delay"]) else None,
        "total_distance_km": total_distance_km,
        "around_earth_trips": around_earth,
    }


@st.cache_data(show_spinner=False)
def route_exists(
    departure: str,
    arrival: str,
    start_date: date,
    end_date: date,
) -> bool:
    df = qdf(
        """
        SELECT COUNT(*) AS n
        FROM flights
        WHERE origin = ?
          AND dest = ?
          AND date(printf('%04d-%02d-%02d', year, month, day)) BETWEEN ? AND ?
        """,
        (departure, arrival, start_date.isoformat(), end_date.isoformat()),
    )
    return int(df.loc[0, "n"]) > 0


@st.cache_data(show_spinner=False)
def route_flight_count(
    departure: str,
    arrival: str,
    start_date: date,
    end_date: date,
) -> int:
    df = qdf(
        """
        SELECT COUNT(*) AS n
        FROM flights
        WHERE origin = ?
          AND dest = ?
          AND date(printf('%04d-%02d-%02d', year, month, day)) BETWEEN ? AND ?
        """,
        (departure, arrival, start_date.isoformat(), end_date.isoformat()),
    )
    return int(df.loc[0, "n"])


def normalize_timeframe(value, default_start: date, default_end: date) -> Tuple[date, date]:
    if isinstance(value, date):
        return value, value

    if isinstance(value, (tuple, list)):
        if len(value) == 2 and isinstance(value[0], date) and isinstance(value[1], date):
            start_date = value[0]
            end_date = value[1]
            if start_date <= end_date:
                return start_date, end_date
            return end_date, start_date

        if len(value) == 1 and isinstance(value[0], date):
            return value[0], value[0]

    return default_start, default_end


def deg2rad(x: float) -> float:
    return x * math.pi / 180.0


def rad2deg(x: float) -> float:
    return x * 180.0 / math.pi


def interpolate_geodesic(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    n_points: int = 80,
) -> Tuple[List[float], List[float]]:
    phi1, lam1 = deg2rad(lat1), deg2rad(lon1)
    phi2, lam2 = deg2rad(lat2), deg2rad(lon2)

    def to_xyz(phi: float, lam: float) -> Tuple[float, float, float]:
        x = math.cos(phi) * math.cos(lam)
        y = math.cos(phi) * math.sin(lam)
        z = math.sin(phi)
        return x, y, z

    p1 = to_xyz(phi1, lam1)
    p2 = to_xyz(phi2, lam2)

    dot = max(-1.0, min(1.0, p1[0] * p2[0] + p1[1] * p2[1] + p1[2] * p2[2]))
    omega = math.acos(dot)

    if abs(omega) < 1e-12:
        return [lat1, lat2], [lon1, lon2]

    lats: List[float] = []
    lons: List[float] = []

    for i in range(n_points):
        t = i / (n_points - 1)
        a = math.sin((1 - t) * omega) / math.sin(omega)
        b = math.sin(t * omega) / math.sin(omega)

        x = a * p1[0] + b * p2[0]
        y = a * p1[1] + b * p2[1]
        z = a * p1[2] + b * p2[2]

        norm = math.sqrt(x * x + y * y + z * z)
        x, y, z = x / norm, y / norm, z / norm

        phi = math.asin(z)
        lam = math.atan2(y, x)

        lats.append(rad2deg(phi))
        lons.append(rad2deg(lam))

    return lats, lons


def init_session_state() -> None:
    min_date, max_date = get_date_bounds()

    defaults = {
        "active_page": "Delays",
        "submitted_filters": {
            "departure": None,
            "arrival": None,
            "timeframe": (min_date, max_date),
        },
        "show_no_results": False,
        "draft_departure": None,
        "draft_arrival": None,
        "draft_timeframe": (min_date, max_date),
        "show_large_map": False,
        "do_reset_filters": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def request_reset_dashboard() -> None:
    st.session_state["do_reset_filters"] = True


def apply_reset_if_requested() -> None:
    if st.session_state.get("do_reset_filters", False):
        min_date, max_date = get_date_bounds()

        st.session_state["active_page"] = "Delays"
        st.session_state["show_no_results"] = False
        st.session_state["submitted_filters"] = {
            "departure": None,
            "arrival": None,
            "timeframe": (min_date, max_date),
        }
        st.session_state["draft_departure"] = None
        st.session_state["draft_arrival"] = None
        st.session_state["draft_timeframe"] = (min_date, max_date)
        st.session_state["show_large_map"] = False
        st.session_state["do_reset_filters"] = False


def make_map(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
    height: int = 250,
) -> go.Figure:
    if departure is None and arrival is None:
        df = get_all_airports()

        fig = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="faa",
            hover_data={"name": True, "lat": False, "lon": False},
            title="All airports",
        )

        fig.update_traces(marker=dict(size=4))

        fig.update_geos(
            projection_type="natural earth",
            showland=True,
            showcountries=True,
            showcoastlines=True,
            lataxis_range=[10, 75],
            lonaxis_range=[-170, -40],
        )

        fig.update_layout(
            height=height,
            margin=dict(l=5, r=5, t=35, b=5),
        )
        return fig

    dep_airport = get_airport_by_faa(departure) if departure else None
    arr_airport = get_airport_by_faa(arrival) if arrival else None

    points = []
    if dep_airport is not None:
        points.append(dep_airport)
    if arr_airport is not None:
        points.append(arr_airport)

    if not points:
        df = get_all_airports()
        fig = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="faa",
            hover_data={"name": True, "lat": False, "lon": False},
            title="All airports",
        )
        fig.update_traces(marker=dict(size=4))
        fig.update_geos(
            projection_type="natural earth",
            showland=True,
            showcountries=True,
            showcoastlines=True,
            lataxis_range=[10, 75],
            lonaxis_range=[-170, -40],
        )
        fig.update_layout(height=height, margin=dict(l=5, r=5, t=35, b=5))
        return fig

    points_df = pd.DataFrame(points)

    fig = px.scatter_geo(
        points_df,
        lat="lat",
        lon="lon",
        hover_name="faa",
        hover_data={"name": True, "lat": False, "lon": False},
        title="Selected route",
    )

    fig.update_traces(marker=dict(size=10))

    if dep_airport is not None and arr_airport is not None:
        line_lats, line_lons = interpolate_geodesic(
            dep_airport["lat"], dep_airport["lon"],
            arr_airport["lat"], arr_airport["lon"],
            n_points=80,
        )
        n_flights = route_flight_count(departure, arrival, start_date, end_date)

        fig.add_trace(
            go.Scattergeo(
                lat=line_lats,
                lon=line_lons,
                mode="lines",
                line=dict(width=3),
                name=f"Route ({n_flights:,} flights)",
                hoverinfo="skip",
            )
        )

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        showcountries=True,
        showcoastlines=True,
        fitbounds="locations",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=5, r=5, t=35, b=5),
    )
    return fig


def render_filter_panel() -> None:
    st.markdown("#### Filters")

    min_date, max_date = get_date_bounds()

    dep_df = get_departure_filter_airports()
    dep_faas = dep_df["faa"].tolist()
    dep_lookup = {
        row["faa"]: f"{row['faa']} — {row['name']}"
        for _, row in dep_df.iterrows()
    }

    arr_df = get_all_filter_airports()
    arr_faas = arr_df["faa"].tolist()
    arr_lookup = {
        row["faa"]: f"{row['faa']} — {row['name']}"
        for _, row in arr_df.iterrows()
    }

    st.selectbox(
        "Departure",
        options=[None] + dep_faas,
        format_func=lambda x: "All" if x is None else dep_lookup.get(x, x),
        key="draft_departure",
    )

    st.selectbox(
        "Arrival",
        options=[None] + arr_faas,
        format_func=lambda x: "All" if x is None else arr_lookup.get(x, x),
        key="draft_arrival",
    )

    timeframe_raw = st.date_input(
        "Timeframe",
        min_value=min_date,
        max_value=max_date,
        key="draft_timeframe",
    )

    start_date, end_date = normalize_timeframe(timeframe_raw, min_date, max_date)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    if st.button("Submit", use_container_width=True):
        dep = st.session_state["draft_departure"]
        arr = st.session_state["draft_arrival"]

        ok = True
        if dep is not None and arr is not None:
            ok = route_exists(dep, arr, start_date, end_date)

        st.session_state["submitted_filters"] = {
            "departure": dep,
            "arrival": arr,
            "timeframe": (start_date, end_date),
        }
        st.session_state["show_no_results"] = not ok
        st.rerun()

    if st.button("Clear", use_container_width=True):
        request_reset_dashboard()
        st.rerun()


def render_top_area() -> None:
    filters = st.session_state["submitted_filters"]
    dep = filters["departure"]
    arr = filters["arrival"]
    start_date, end_date = filters["timeframe"]

    stats = get_summary_stats(dep, arr, start_date, end_date)

    info_col, map_col = st.columns([2.1, 1.35])

    with info_col:
        st.markdown(f"**Total flights:** {stats['total_flights']:,}")

        if stats["avg_duration"] is None:
            st.markdown("**Average duration:** —")
        else:
            st.markdown(f"**Average duration:** {stats['avg_duration']:.1f} min")

        if stats["avg_dep_delay"] is None:
            st.markdown("**Average dep delay:** —")
        else:
            st.markdown(f"**Average dep delay:** {stats['avg_dep_delay']:.1f} min")

        if stats["avg_arr_delay"] is None:
            st.markdown("**Average arr delay:** —")
        else:
            st.markdown(f"**Average arr delay:** {stats['avg_arr_delay']:.1f} min")

        st.markdown(f"**Total distance flown:** {stats['total_distance_km']:,.0f} km")
        st.markdown(f"**Equivalent around-Earth trips:** {stats['around_earth_trips']:.2f}")

        if dep is None and arr is None:
            st.caption("Initial state: all airports are shown, focused on North America.")
        elif dep is not None and arr is not None:
            st.caption(f"Selected route: {dep} → {arr} | {start_date} to {end_date}")
        elif dep is not None:
            st.caption(f"Selected departure: {dep} | {start_date} to {end_date}")
        else:
            st.caption(f"Selected arrival: {arr} | {start_date} to {end_date}")

    with map_col:
        st.markdown("#### Map")
        st.plotly_chart(
            make_map(dep, arr, start_date, end_date, height=260),
            use_container_width=True,
            config={"displayModeBar": False},
        )

        button_label = "Hide larger map" if st.session_state["show_large_map"] else "Open larger map"
        if st.button(button_label, use_container_width=True):
            st.session_state["show_large_map"] = not st.session_state["show_large_map"]
            st.rerun()

    if st.session_state["show_large_map"]:
        st.markdown("#### Larger Map View")
        st.plotly_chart(
            make_map(dep, arr, start_date, end_date, height=700),
            use_container_width=True,
        )


def render_navigation_bar() -> None:
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("Delay", use_container_width=True):
            st.session_state["active_page"] = "Delays"
    with c2:
        if st.button("Planes", use_container_width=True):
            st.session_state["active_page"] = "Planes"
    with c3:
        if st.button("CO2", use_container_width=True):
            st.session_state["active_page"] = "CO2"
    with c4:
        if st.button("Noise", use_container_width=True):
            st.session_state["active_page"] = "Noise"


def render_main_content() -> None:
    page = st.session_state["active_page"]

    if st.session_state["show_no_results"]:
        st.warning("No results found for the selected route and date range.")
        return

    if page == "Delays":
        st.markdown("### Delays")

        filters = st.session_state["submitted_filters"]
        dep = filters["departure"]
        arr = filters["arrival"]
        start_date, end_date = filters["timeframe"]

        stats, df, df_all_origin, df_all_dest = get_real_delay_data(dep, arr, start_date, end_date)

        if df.empty:
            st.info("No delay data available for the selected filters.")
        else:
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                st.metric("Delay percentage", f"{stats['delay_pct']:.2f}%")
            with r1c2:
                st.metric("Average delay time", f"{stats['average_delay']:.1f} min")
            with r1c3:
                st.metric("Average delay time if there is a delay", f"{stats['average_time_with_delay']:.1f} min")

            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(
                    plot_delay_chance_dep(df_all_origin),
                    use_container_width=True
                )
            with c2:
                st.plotly_chart(
                    plot_delay_time(df),
                    use_container_width=True
                )

            c3, c4 = st.columns(2)
            with c3:
                st.plotly_chart(
                    plot_delay_hour(df),
                    use_container_width=True
                )
            with c4:
                st.plotly_chart(
                    plot_delay_month(df),
                    use_container_width=True
                )
            
            c5, c6 = st.columns(2)
            with c5:    
                st.plotly_chart(
                    plot_best_delay_pct_dest(df_all_dest),
                    use_container_width=True
                )
            with c6:
                st.plotly_chart(
                    plot_worst_delay_pct_dest(df_all_dest),
                    use_container_width=True
                )

    elif page == "Planes":
        st.markdown("### Planes")

        filters = st.session_state["submitted_filters"]
        dep = filters["departure"]
        arr = filters["arrival"]
        start_date, end_date = filters["timeframe"]

        plane_df = get_plane_data()
        filtered_planes = apply_plane_filters(
            plane_df,
            origin=dep,
            dest=arr,
            start_date=start_date,
            end_date=end_date,
        )

        avg_speed = average_flight_speed(filtered_planes)

        if filtered_planes.empty:
            st.info("No plane data available for the selected filters.")
        else:
            if pd.isna(avg_speed):
                st.metric("Average flight speed", "—")
            else:
                st.metric("Average flight speed", f"{avg_speed:.1f} mph")

            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(
                    plot_top_models_by_flights(filtered_planes),
                    use_container_width=True
                )
            with c2:
                st.plotly_chart(
                    plot_top_models_by_distance(filtered_planes),
                    use_container_width=True
                )

            c3, c4 = st.columns(2)
            with c3:
                st.plotly_chart(
                    plot_top_manufacturers(filtered_planes),
                    use_container_width=True
                )
            with c4:
                st.plotly_chart(
                    plot_average_speed_by_model(filtered_planes),
                    use_container_width=True
                )

            c5, c6 = st.columns(2)
            with c5:
                st.plotly_chart(
                    plot_plane_type_distribution(filtered_planes),
                    use_container_width=True
                )
            with c6:
                st.plotly_chart(
                    plot_body_type_distribution(filtered_planes),
                    use_container_width=True
                )

    elif page == "CO2":
        st.markdown("### CO2")

        filters = st.session_state["submitted_filters"]
        dep = filters["departure"]
        arr = filters["arrival"]
        start_date, end_date = filters["timeframe"]

        (
            stats,
            df_airlines_total,
            df_airlines_avg,
            df_family,
            df_timeline,
        ) = get_real_co2_data(dep, arr, start_date, end_date)

        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            st.metric("Total fuel usage", f"{stats['total_fuel_kg']:,.0f} kg")
        with r1c2:
            st.metric("Average fuel usage", f"{stats['avg_fuel_kg']:,.1f} kg / flight")
        with r1c3:
            st.metric("Number of flights", f"{stats['n_flights']:,}")

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            st.metric("Total CO2 emissions", f"{stats['total_co2_kg']:,.0f} kg")
        with r2c2:
            st.metric("Average CO2 emissions", f"{stats['avg_co2_kg']:,.1f} kg / flight")
        with r2c3:
            st.metric("Average CO2 per passenger", f"{stats['avg_co2_per_passenger_kg']:,.1f} kg")

        st.markdown("---")

        c_highlight = st.columns([1.5, 2])
        with c_highlight[0]:
            st.metric(
                "Estimated compensation per passenger",
                f"€ {stats['avg_compensation_per_passenger_eur']:,.2f}",
            )

        c1, c2 = st.columns(2)

        with c1:
            if df_airlines_total.empty:
                st.info("No airline emissions data available.")
            else:
                fig_total = px.bar(
                    df_airlines_total.head(10),
                    x="airline",
                    y="co2_tonnes",
                    title="Top airlines by total CO2 emissions",
                    labels={"airline": "Airline", "co2_tonnes": "CO2 emissions (tonnes)"},
                )
                st.plotly_chart(fig_total, use_container_width=True)

        with c2:
            if df_airlines_avg.empty:
                st.info("No airline average-emissions data available.")
            else:
                fig_avg = px.bar(
                    df_airlines_avg.head(10),
                    x="airline",
                    y="avg_co2_kg",
                    title="Average CO2 emissions per flight by airline",
                    labels={"airline": "Airline", "avg_co2_kg": "Average CO2 per flight (kg)"},
                )
                st.plotly_chart(fig_avg, use_container_width=True)

        c3, c4 = st.columns(2)

        with c3:
            df_family_plot = df_family[df_family["family"] != "Unknown"]

            if df_family_plot.empty:
                st.info("No aircraft-family data available.")
            else:
                fig_family = px.bar(
                    df_family_plot.head(10),
                    x="family",
                    y="co2_tonnes",
                    title="CO2 emissions by aircraft family",
                    labels={"family": "Aircraft family", "co2_tonnes": "CO2 emissions (tonnes)"},
                )
                fig_family.update_layout(xaxis_tickangle=-25)
                st.plotly_chart(fig_family, use_container_width=True)

        with c4:
            if df_timeline.empty:
                st.info("No timeline data available.")
            else:
                granularity_label = {
                    "day": "day",
                    "week": "week",
                    "month": "month",
                }.get(stats["timeline_granularity"], "period")

                fig_timeline = px.line(
                    df_timeline,
                    x="period_label",
                    y="co2_tonnes",
                    markers=True,
                    title=f"CO2 emissions over time (grouped by {granularity_label})",
                    labels={"period_label": "Time period", "co2_tonnes": "CO2 emissions (tonnes)"},
                )
                fig_timeline.update_layout(xaxis_title="Time period")
                st.plotly_chart(fig_timeline, use_container_width=True)

        with st.expander("Assumptions and interpretation"):
            st.markdown(
                """
                - Fuel usage is estimated from flight distance and aircraft assumptions.
                - CO2 emissions are derived from estimated fuel burn.
                - Per passenger values use an assumed average load factor.
                - Compensation is an estimate based on a fixed carbon price assumption and is set at 90 euros per tonne CO2.
                - This means the CO2 dashboard is an estimate and not exact reported fuel data.
                - The average annual carbon footprint of a person in the Netherlands is approximately 9 tonnes of CO2 (equivalent)
                """
            )

    elif page == "Noise":
        st.markdown("### Noise")

        filters = st.session_state["submitted_filters"]
        dep = filters["departure"]
        arr = filters["arrival"]
        start_date, end_date = filters["timeframe"]

        df_ranking, df_timeline, total_noise, total_flights = get_real_noise_data(dep, arr, start_date, end_date)

        if dep and not arr:
            noise_label = "departures only"
        elif arr and not dep:
            noise_label = "arrivals only"
        elif dep and arr:
            noise_label = "route specific"
        else:
            noise_label = "arrivals + departures"

        total_days = (end_date - start_date).days + 1
        avg_daily_noise_total = total_noise / total_days if total_days > 0 else 0.0
        avg_noise_per_flight = total_noise / total_flights if total_flights > 0 else 0.0

        st.markdown(f"#### Key Noise Indicators ({noise_label})")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total noise (Cumulative EPNdB)", f"{total_noise:,.1f}")
        with m2:
            st.metric("Average noise per flight (EPNdB)", f"{avg_noise_per_flight:,.1f}")
        with m3:
            st.metric("Average daily noise (EPNdB)", f"{avg_daily_noise_total:,.1f}")

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Ranking of NYC airports by noise")
            if df_ranking.empty:
                st.info("No data available for the selected filters.")
            else:
                display_ranking = df_ranking[["airport", "noise"]].copy()
                display_ranking["daily_avg"] = display_ranking["noise"] / total_days
                display_ranking.columns = ["Airport", "Total Noise (EPNdB)", "Daily Avg (EPNdB)"]
                display_ranking["Total Noise (EPNdB)"] = display_ranking["Total Noise (EPNdB)"].map("{:,.1f}".format)
                display_ranking["Daily Avg (EPNdB)"] = display_ranking["Daily Avg (EPNdB)"].map("{:,.1f}".format)
                st.dataframe(display_ranking, use_container_width=True, hide_index=True)
        with c2:
            if df_timeline.empty:
                st.info("No timeline data available for the selected filters.")
            else:
                fig = px.bar(
                    df_timeline,
                    x="hour",
                    y="noise",
                    title=f"Noise production by hour of day ({noise_label})",
                    labels={"hour": "Hour of Day", "noise": "Cumulative EPNdB"},
                )
                fig.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1))
                st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Flights Dashboard", layout="wide")
    validate_database()
    init_session_state()
    apply_reset_if_requested()

    st.title("Flights Dashboard")

    left_panel, right_panel = st.columns([1.0, 3.8])

    with left_panel:
        render_filter_panel()

    with right_panel:
        render_top_area()
        render_navigation_bar()
        st.markdown("---")
        render_main_content()


if __name__ == "__main__":
    main()
