from __future__ import annotations
import numpy as np
import sqlite3
from datetime import date
from typing import Dict, List, Optional, Tuple
import pandas as pd
import plotly.express as px
import os

DB_PATH = os.path.join(os.path.dirname(__file__),'data', 'flights_database.db')
connection = sqlite3.connect(DB_PATH)

def _qdf(query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(str(DB_PATH)) as con:
        return pd.read_sql_query(query, con, params=params)

#@st.cache_data(show_spinner=False)
# function to get the real delay data
def get_real_delay_data(
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

    if departure is not None:
        df_all_dest = df[df["origin"]== departure]
    else: df_all_dest = df

    if arrival is not None:
        df_all_origin = df[df["dest"]== arrival]
    else: df_all_origin = df

    if departure is not None:
        df = df[df["dest"]== departure]

    if arrival is not None:
        df = df[df["dest"]== arrival]
    if df.empty:
        return 0
    stats = {
        "delay_pct": float(df[df["arr_delay"]> 0].count().iloc[0]/df["arr_delay"].count() * 100),
        "average_delay": float(df["arr_delay"].mean()),
        "average_time_with_delay": float(df[df["arr_delay"]>0]["arr_delay"].mean()),
    }
    return stats, df, df_all_origin, df_all_dest

# helper function for finding delay percentage for a given index
def delay_pct_by(df, by):
    total = df.groupby(by, as_index=False)["arr_delay"].count()
    delays = df[df["arr_delay"] > 0].groupby(by, as_index=False)["arr_delay"].count().rename(
        columns={"arr_delay": "delay_count"})

    df = total.merge(delays, on=by, how="left")
    df["delay_count"] = df["delay_count"].fillna(0)

    df["delay_pct"] = df["delay_count"] / df["arr_delay"] * 100
    return df
# temp stuff
# def delay_chance(df):
#    return df[df["arr_delay"]> 0].count().iloc[0]/df["arr_delay"].count() * 100
# average delay V
# def average_delay(df):
#    return df["arr_delay"].mean()
# average delay if there is a delay V
# def average_time_with_delay(df):
#    return df[df["arr_delay"]>0]["arr_delay"].mean()
# plot total amount a delay occurred to arrival delay
#def plot_delay_time(df):
#    delays = df[df["arr_delay"] > 0]
#    fig = px.histogram(delays, x='arr_delay', nbins=400, range_x= [0, 200],
#                       title="total amount of delays per delay time period",
#                       labels={'arr_delay': "arrival delay", 'delay': "total amount of delays"})
#    return fig

# plot total delay percentage for time periods (month, hour)
def plot_delay_month(df):
    df = delay_pct_by(df, "month")
    fig = px.bar(df, x='month', y = 'delay_pct',
                 title = "delay percentage for each month",
                labels = {'month':"month", 'delay_pct':"delay percentage"})
    return fig

def plot_delay_hour(df):
    df = delay_pct_by(df, "hour")
    fig = px.bar(df, x='hour', y = 'delay_pct',
                 title = "delay percentage for each hour",
                labels = {'hour':"hour at departure", 'delay_pct':"delay percentage"})
    return fig

# plot delay percentage to dep airport which needs a df that has all deps
def plot_delay_chance_dep(df):
    df = delay_pct_by(df, "origin")
    fig = px.bar(df, x='origin', y='delay_pct',
                 title="delay percentage for each origin airport",
                 labels={'origin': "origin airport", 'delay_pct': "delay percentage"})
    return fig
# plot delay percentage by destination for worst and best needs a df that has all dest
def plot_worst_delay_pct_dest(df):
    df = delay_pct_by(df, "dest").sort_values(by = "delay_pct", ascending= False)
    fig = px.bar(df.head(10), x='dest', y='delay_pct',
                 title="delay percentage for destination",
                 labels={'dest': "destination airport", 'delay_pct': "delay percentage"})
    return fig

def plot_best_delay_pct_dest(df):
    df = delay_pct_by(df, "dest").sort_values(by = "delay_pct", ascending= True)
    fig = px.bar(df.head(10), x='dest', y='delay_pct',
                 title="delay percentage for destination",
                 labels={'dest': "destination airport", 'delay_pct': "delay percentage"})
    return fig

# temp things for streamlit in dashboard
# st.markdown("### Delay")
#
#        filters = st.session_state["submitted_filters"]
#        dep = filters["departure"]
#        arr = filters["arrival"]
#        start_date, end_date = filters["timeframe"]
#        (
#            stats,
#            df,
#            df_all_origin,
#            df_all_dest
#        ) = get_real_delay_data(dep, arr, start_date, end_date)
#        r1c1, r1c2, r1c3 = st.columns(3)
#        with r1c1:
#            st.metric("Delay percentage", f"{stats['delay_pct']:,.2f} kg")
#        with r1c2:
#            st.metric("Average delay time", f"{stats['average_delay']:,.1f} kg / flight")
#        with r1c3:
#            st.metric("Average delay time if there is a delay", f"{stats['average_time_with_delay']:,}")
#            c1, c2 = st.columns(2)
#            with c1:
#                st.plotly_chart(
#                    plot_delay_time(df),
#                    use_container_width=True
#                )
#            with c2:
#                st.plotly_chart(
#                    plot_delay_chance_dep(df_all_origin),
#                    use_container_width=True
#                )
#
#            c3, c4 = st.columns(2)
#            with c3:
#                st.plotly_chart(
#                    plot_delay_month(df),
#                    use_container_width=True
#                )
#            with c4:
#                st.plotly_chart(
#                    plot_delay_hour(df),
#                    use_container_width=True
#                )
#
#            c5, c6 = st.columns(2)
#            with c5:
#                st.plotly_chart(
#                    plot_worst_delay_pct_dest(df_all_dest),
#                    use_container_width=True
#                )
#            with c6:
#                st.plotly_chart(
#                    plot_best_delay_pct_dest(df_all_dest)
#                    use_container_width=True
#                )