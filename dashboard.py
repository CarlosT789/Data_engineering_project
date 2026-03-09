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


# directory config might need to change it

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "flights_database.db"


# DB helper functions

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
    """
    Airports that appear anywhere in flights, either as origin or destination,
    and that have coordinates for the map.
    """
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
            AVG(arr_delay) AS avg_arr_delay
        FROM flights
        WHERE {where_sql}
        """,
        tuple(params),
    )

    row = df.iloc[0].to_dict()

    return {
        "total_flights": int(row["total_flights"]) if pd.notna(row["total_flights"]) else 0,
        "avg_duration": float(row["avg_duration"]) if pd.notna(row["avg_duration"]) else None,
        "avg_dep_delay": float(row["avg_dep_delay"]) if pd.notna(row["avg_dep_delay"]) else None,
        "avg_arr_delay": float(row["avg_arr_delay"]) if pd.notna(row["avg_arr_delay"]) else None,
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


# more helper functions

def normalize_timeframe(value, default_start: date, default_end: date) -> Tuple[date, date]:
    """
    Streamlit date_input can return:
    - one date
    - tuple/list of 2 dates
    """
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
    """
    Great-circle interpolation on a sphere.
    This gives a nice curved geodesic-looking route line.
    """
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



# PLACEHOLDERS FOR LOWER TABS (Careful only placeholders atm)

def placeholder_delay_hist() -> pd.DataFrame:
    bins = ["00–03", "03–06", "06–09", "09–12", "12–15", "15–18", "18–21", "21–24"]
    vals = [70, 55, 240, 380, 450, 520, 600, 280]
    return pd.DataFrame({"time_bin": bins, "n_delayed_flights": vals})


def placeholder_delay_relation() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": list(range(1, 13)),
            "n_delayed_flights": [900, 850, 910, 980, 1100, 1230, 1300, 1270, 1090, 970, 940, 1000],
        }
    )


def placeholder_top_airports() -> pd.DataFrame:
    return pd.DataFrame(
        {"airport": ["JFK", "EWR", "LGA", "LAX", "ORD"], "delays": [5100, 4300, 3900, 2700, 2500]}
    )


def placeholder_top_airlines() -> pd.DataFrame:
    return pd.DataFrame(
        {"airline": ["UA", "AA", "DL", "B6", "WN"], "delays": [7200, 6900, 6500, 6100, 5400]}
    )


def placeholder_planes_data() -> Dict[str, pd.DataFrame]:
    return {
        "top_used": pd.DataFrame(
            {"plane": ["A320", "B737-800", "E190", "CRJ-900", "A321"], "value": [14000, 13200, 9800, 8700, 8200]}
        ),
        "top_fuel": pd.DataFrame(
            {"plane": ["B777", "A330", "B767", "A321", "B737-800"], "value": [5400, 5100, 4700, 4200, 3900]}
        ),
        "top_distance": pd.DataFrame(
            {"plane": ["B777", "A330", "B767", "A321", "B737-800"], "value": [8900, 8600, 8100, 7200, 6800]}
        ),
        "top_manufacturers": pd.DataFrame(
            {"manufacturer": ["Boeing", "Airbus", "Embraer", "Bombardier", "Cessna"], "count": [22000, 19000, 8700, 5100, 600]}
        ),
    }


def placeholder_co2_data() -> Dict[str, float]:
    return {
        "Total fuel usage": 2450000,
        "Average fuel usage": 563.1,
        "Total CO2 emissions": 7742000,
        "Average CO2 emissions": 1779.4,
        "Average CO2 per passenger": 112.8,
        "Average compensation": 11.3,
    }


def placeholder_co2_airlines() -> pd.DataFrame:
    return pd.DataFrame(
        {"airline": ["AA", "DL", "UA", "B6", "WN"], "co2": [1400000, 1250000, 1190000, 980000, 720000]}
    )


def placeholder_noise_ranking() -> pd.DataFrame:
    return pd.DataFrame({"airport": ["JFK", "EWR", "LGA"], "noise": [3100000, 2850000, 2470000]})


def placeholder_noise_timeline() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hour": list(range(24)),
            "noise": [120, 90, 70, 60, 55, 80, 180, 350, 520, 610, 680, 720, 740, 760, 780, 810, 860, 900, 880, 760, 610, 420, 250, 160],
        }
    )


@st.cache_data(show_spinner=False)
def get_real_noise_data(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
) -> Tuple[pd.DataFrame, pd.DataFrame, float]:

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

    # --- Departures leg ---
    # A flight counts as a departure noise event at a NYC airport when origin IN NYC.
    # The sidebar "departure" filter restricts which NYC origin; "arrival" restricts dest.
    dep_parts = [f"f.origin IN ('JFK','EWR','LGA')", date_filter]
    dep_params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    if departure is not None:
        dep_parts.append("f.origin = ?")
        dep_params.append(departure)
    if arrival is not None:
        dep_parts.append("f.dest = ?")
        dep_params.append(arrival)

    # --- Arrivals leg ---
    # A flight counts as an arrival noise event at a NYC airport when dest IN NYC.
    # The sidebar "departure" filter restricts origin; "arrival" restricts which NYC dest.
    arr_parts = [f"f.dest IN ('JFK','EWR','LGA')", date_filter]
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
    # Arrivals use arr_time/100 to get the correct local arrival hour,
    # since f.hour always refers to the scheduled departure hour.
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

    # Query 1: Ranking by Airport
    df_ranking = qdf(
        f"SELECT airport, SUM(epndb) AS noise FROM ({union_sql}) GROUP BY airport ORDER BY noise DESC",
        union_params,
    )

    total_noise = df_ranking["noise"].sum() if not df_ranking.empty else 0.0

    # Query 2: Timeline by Hour
    df_timeline = qdf(
        f"SELECT CAST(hour AS INTEGER) AS hour, SUM(epndb) AS noise FROM ({union_sql}) WHERE hour IS NOT NULL GROUP BY hour ORDER BY hour",
        union_params,
    )

    return df_ranking, df_timeline, total_noise


# dashboard session state

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


# map top right corner

def make_map(
    departure: Optional[str],
    arrival: Optional[str],
    start_date: date,
    end_date: date,
    height: int = 250,
) -> go.Figure:
    # initial state: no filters show all airports, focused on North America
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


# UI render

def render_filter_panel() -> None:
    st.markdown("#### Filters")

    min_date, max_date = get_date_bounds()

    airports_df = get_all_filter_airports()
    airport_faas = airports_df["faa"].tolist()
    airport_lookup = {
        row["faa"]: f"{row['faa']} — {row['name']}"
        for _, row in airports_df.iterrows()
    }

    st.selectbox(
        "Departure",
        options=[None] + airport_faas,
        format_func=lambda x: "All" if x is None else airport_lookup.get(x, x),
        key="draft_departure",
    )

    st.selectbox(
        "Arrival",
        options=[None] + airport_faas,
        format_func=lambda x: "All" if x is None else airport_lookup.get(x, x),
        key="draft_arrival",
    )

    timeframe_raw = st.date_input(
        "Timeframe",
        value=st.session_state["draft_timeframe"],
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
        st.markdown("#### General Info")
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
        st.metric("Ratio of delays", "27.4%")

        df_hist = placeholder_delay_hist()
        fig_hist = px.bar(df_hist, x="time_bin", y="n_delayed_flights", title="Delayed flights by time interval")
        st.plotly_chart(fig_hist, use_container_width=True)

        df_rel = placeholder_delay_relation()
        fig_rel = px.line(df_rel, x="month", y="n_delayed_flights", markers=True, title="Delayed flights vs month")
        st.plotly_chart(fig_rel, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Top airports by delays")
            st.dataframe(placeholder_top_airports(), use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### Top airlines by delays")
            st.dataframe(placeholder_top_airlines(), use_container_width=True, hide_index=True)

    elif page == "Planes":
        st.markdown("### Planes")
        data = placeholder_planes_data()

        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.bar(data["top_used"], x="plane", y="value", title="Top 5 by number of flights")
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.bar(data["top_fuel"], x="plane", y="value", title="Top 5 by fuel usage")
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            fig3 = px.bar(data["top_distance"], x="plane", y="value", title="Top 5 by distance")
            st.plotly_chart(fig3, use_container_width=True)
        with c4:
            fig4 = px.bar(data["top_manufacturers"], x="manufacturer", y="count", title="Top manufacturers")
            st.plotly_chart(fig4, use_container_width=True)

        st.metric("Average flight speed", "742.3 km/h")

    elif page == "CO2":
        st.markdown("### CO2")
        stats = placeholder_co2_data()

        st.markdown(f"**Total fuel usage:** {stats['Total fuel usage']:,.1f}")
        st.markdown(f"**Average fuel usage:** {stats['Average fuel usage']:.1f}")
        st.markdown(f"**Total CO2 emissions:** {stats['Total CO2 emissions']:,.1f}")
        st.markdown(f"**Average CO2 emissions:** {stats['Average CO2 emissions']:.1f}")
        st.markdown(f"**Average CO2 per passenger:** {stats['Average CO2 per passenger']:.1f}")
        st.markdown(f"**Average compensation:** € {stats['Average compensation']:.2f}")

        fig = px.bar(placeholder_co2_airlines(), x="airline", y="co2", title="Emissions by airline")
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Noise":
        st.markdown("### Noise")

        filters = st.session_state["submitted_filters"]
        dep = filters["departure"]
        arr = filters["arrival"]
        start_date, end_date = filters["timeframe"]

        df_ranking, df_timeline, total_noise = get_real_noise_data(dep, arr, start_date, end_date)

        if dep and not arr:
            noise_label = "departures only"
        elif arr and not dep:
            noise_label = "arrivals only"
        elif dep and arr:
            noise_label = "route specific"
        else:
            noise_label = "arrivals + departures"

        st.metric(
            f"Total noise produced by NYC airports (Cumulative EPNdB, {noise_label})",
            f"{total_noise:,.1f}",
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Ranking of NYC airports by noise")
            if df_ranking.empty:
                st.info("No data available for the selected filters.")
            else:
                display_ranking = df_ranking.copy()
                display_ranking.columns = ["Airport", "Noise (EPNdB)"]
                display_ranking["Noise (EPNdB)"] = display_ranking["Noise (EPNdB)"].map("{:,.1f}".format)
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


# main

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
