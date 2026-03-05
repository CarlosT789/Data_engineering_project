#!/usr/bin/env python3
"""
Part 5 – Streamlit dashboard skeleton (placeholders only)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = Path("flights_database.db")  # keep for later integration
NYC_ORIGINS = ["EWR", "JFK", "LGA"]


# -----------------------------
# Placeholder data generators
# (replace with your real query/aggregation results later)
# -----------------------------
def placeholder_kpis() -> dict:
    return {
        "n_flights": 123456,
        "avg_dep_delay": 12.3,
        "avg_arr_delay": 5.6,
        "pct_dep_delayed_15": 0.27,
        "pct_arr_delayed_15": 0.18,
        "cancellation_proxy": 0.03,
    }


def placeholder_monthly_trend() -> pd.DataFrame:
    months = np.arange(1, 13)
    df = pd.DataFrame(
        {
            "month": months,
            "n_flights": (np.sin(months / 2) + 2) * 1000,
            "avg_dep_delay": (np.cos(months / 2) + 2) * 5,
            "avg_arr_delay": (np.sin(months / 3) + 2) * 4,
        }
    )
    return df


def placeholder_top_destinations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dest": ["LAX", "BOS", "MIA", "SFO", "ORD", "ATL", "DFW", "DEN", "SEA", "IAD"],
            "n_flights": [1200, 1100, 980, 930, 900, 870, 860, 820, 800, 760],
            "avg_arr_delay": [8.2, 4.1, 10.3, 6.8, 7.4, 5.2, 9.0, 6.1, 8.7, 4.9],
        }
    )


def placeholder_hourly_profile() -> pd.DataFrame:
    hours = np.arange(0, 24)
    return pd.DataFrame(
        {
            "hour": hours,
            "n_flights": (np.maximum(0, np.sin((hours - 6) / 3)) + 0.2) * 500,
            "avg_dep_delay": (np.maximum(0, np.sin((hours - 8) / 4)) + 0.3) * 20,
            "pct_dep_delayed_15": np.clip((np.maximum(0, np.sin((hours - 9) / 4)) + 0.1) / 2, 0, 1),
        }
    )


def placeholder_weather_delay() -> pd.DataFrame:
    n = 500
    rng = np.random.default_rng(0)
    wind = rng.normal(12, 5, size=n).clip(0)
    visib = rng.normal(8, 1.5, size=n).clip(0)
    dep_delay = rng.normal(10, 15, size=n) + 0.3 * (wind - 10) - 0.8 * (visib - 8)
    return pd.DataFrame({"wind_speed": wind, "visib": visib, "dep_delay": dep_delay})


def placeholder_day_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dest": ["MCO", "BOS", "LAX", "ATL", "ORD"],
            "n_flights": [20, 18, 15, 14, 12],
            "avg_dep_delay": [25.0, 10.0, 18.0, 7.0, 12.0],
        }
    )


def fmt_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{100.0 * x:.1f}%"


def fmt_min(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:.1f} min"



def main() -> None:
    st.set_page_config(page_title="NYC Flights Dashboard (Skeleton)", layout="wide")
    st.title("NYC Flights 2023 — Dashboard (Skeleton / Placeholders)")
    st.caption(
        "This version contains UI + placeholders only. "
        "Replace each placeholder section with your real functions/queries from previous weeks."
    )

    st.sidebar.header("Filters (placeholders)")

    origin = st.sidebar.selectbox("Departure airport (NYC)", ["ALL"] + NYC_ORIGINS, index=1)

    dest_list: List[str] = ["ALL", "LAX", "BOS", "MIA", "SFO", "ORD", "ATL", "DFW"]
    dest = st.sidebar.selectbox("Arrival airport", dest_list, index=0)

    date = st.sidebar.date_input("Date", value=pd.Timestamp("2023-01-15").date())
    date = pd.Timestamp(date)

    st.sidebar.markdown("---")
    st.sidebar.info(
        "TODO: Connect filters to your data.\n\n"
        "- origin/dest should filter the DB queries\n"
        "- date should filter day-level stats"
    )

    tab_overview, tab_airport, tab_delays, tab_weather, tab_co2, tab_data = st.tabs(
        ["Overview", "Airport/Route", "Delays", "Weather", "CO₂", "Data/Notes"]
    )

    with tab_overview:
        st.subheader("Overview KPIs")
        k = placeholder_kpis()

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Flights", f"{k['n_flights']:,}")
        c2.metric("Avg dep delay", fmt_min(k["avg_dep_delay"]))
        c3.metric("Avg arr delay", fmt_min(k["avg_arr_delay"]))
        c4.metric("Dep delayed >15", fmt_pct(k["pct_dep_delayed_15"]))
        c5.metric("Arr delayed >15", fmt_pct(k["pct_arr_delayed_15"]))
        c6.metric("Cancel proxy", fmt_pct(k["cancellation_proxy"]))

        st.markdown("### Monthly trends (placeholder)")
        df_m = placeholder_monthly_trend()

        fig1 = px.line(df_m, x="month", y="avg_dep_delay", markers=True, title="Avg departure delay by month")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.bar(df_m, x="month", y="n_flights", title="Flights by month")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### Top destinations (placeholder)")
        df_top = placeholder_top_destinations()
        fig3 = px.bar(df_top, x="dest", y="n_flights", title="Top destinations", hover_data=["avg_arr_delay"])
        st.plotly_chart(fig3, use_container_width=True)

        st.info(
            "TODO: Replace placeholders with real outputs:\n"
            "- kpis_overall(origin, dest)\n"
            "- monthly_delay_trend(origin, dest)\n"
            "- top_destinations(origin)"
        )

    # Airport/Route
    with tab_airport:
        st.subheader("Airport / Route statistics")
        st.write(f"Current selection (placeholder): **{origin} → {dest}**, date: **{date.date()}**")

        st.markdown("### Hour-of-day profile (placeholder)")
        df_h = placeholder_hourly_profile()
        fig_h = px.line(df_h, x="hour", y="avg_dep_delay", markers=True, title="Avg departure delay by hour")
        st.plotly_chart(fig_h, use_container_width=True)

        fig_h2 = px.bar(df_h, x="hour", y="pct_dep_delayed_15", title="Share delayed >15 min by hour")
        st.plotly_chart(fig_h2, use_container_width=True)

        st.info(
            "TODO: Plug in your real functions:\n"
            "- hourly_delay_profile(origin, dest)\n"
            "- route popularity / reliability tables\n"
            "- heatmap origin×dest for avg delay (top N destinations)"
        )

    # Delays
    with tab_delays:
        st.subheader("Delay distributions and comparisons (placeholders)")

        # Placeholder distribution sample
        rng = np.random.default_rng(1)
        df_delay = pd.DataFrame({"dep_delay": rng.normal(10, 20, 1000), "carrier": rng.choice(["AA", "DL", "UA"], 1000)})

        fig_box = px.box(df_delay, x="carrier", y="dep_delay", title="Departure delay distribution by carrier")
        st.plotly_chart(fig_box, use_container_width=True)

        st.info(
            "TODO: Replace with real analyses:\n"
            "- delay distributions per carrier\n"
            "- percent delayed >15 per airport / carrier / month\n"
            "- cancellation proxy rate per airport/carrier"
        )

    # Weather
    with tab_weather:
        st.subheader("Weather vs delays (placeholders)")
        st.caption("Use variables with good coverage: wind_speed, wind_dir, visib.")

        df_w = placeholder_weather_delay()
        fig_sc = px.scatter(df_w, x="wind_speed", y="dep_delay", opacity=0.4, title="Wind speed vs dep_delay")
        st.plotly_chart(fig_sc, use_container_width=True)

        df_w2 = df_w.copy()
        df_w2["wind_bin"] = pd.cut(df_w2["wind_speed"], bins=8).astype(str)
        df_bin = df_w2.groupby("wind_bin", observed=False)["dep_delay"].mean().reset_index()
        fig_bin = px.bar(df_bin, x="wind_bin", y="dep_delay", title="Mean dep_delay by wind-speed bin")
        st.plotly_chart(fig_bin, use_container_width=True)

        st.info(
            "TODO: Replace placeholders with your real merged table:\n"
            "- weather_delay_relation(origin)\n"
            "- compute bins safely (cast to str)\n"
            "- show correlation / regression / summary tables"
        )

    # CO2
    with tab_co2:
        st.subheader("CO₂ / fuel / compensation (placeholders)")
        st.caption("This tab is meant for your CO₂ functions from Part 4/5 extension.")

        st.markdown("### Inputs (placeholders)")
        colA, colB, colC = st.columns(3)
        with colA:
            carbon_price = st.number_input("Carbon price (€/ton CO₂)", min_value=0.0, value=100.0, step=5.0)
        with colB:
            passengers = st.number_input("Passengers (optional)", min_value=0, value=150, step=1)
        with colC:
            load_factor = st.slider("Load factor (if estimating passengers)", min_value=0.1, max_value=1.0, value=0.85)

        st.markdown("### Outputs (placeholders)")
        co1, co2, co3, co4 = st.columns(4)
        co1.metric("Fuel used (kg)", "—")
        co2.metric("Total CO₂ flight (kg)", "—")
        co3.metric("CO₂ per passenger (kg)", "—")
        co4.metric("Compensation per passenger (€)", "—")

        st.info(
            "TODO: Plug in your CO₂ pipeline:\n"
            "- add fuel burn to planes table\n"
            "- fuel_used_for_flight_kg(...)\n"
            "- passenger_co2_for_flight_kg(...)\n"
            "- passenger_compensation_eur(...)"
        )

    # Data/Notes
    with tab_data:
        st.subheader("Data / notes / QA (placeholders)")
        st.markdown(
            "- Missing flights values (~2–3%) can be treated as cancellation proxy.\n"
            "- Weather coverage is poor for many vars; focus on wind_speed/wind_dir/visib.\n"
            "- Add any interesting insights for the report/dashboard here."
        )

        st.markdown("### Day table (placeholder)")
        st.dataframe(placeholder_day_table(), use_container_width=True)

        st.info(
            "TODO: "
        )


if __name__ == "__main__":
    main()
