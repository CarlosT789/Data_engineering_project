import math
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


DATA_PATH = Path("airports.csv")
OUT_DIR = Path("outputs")

def is_us_airport(lat: float, lon: float) -> bool:
#check if airport is us
    if pd.isna(lat) or pd.isna(lon):
        return False

    contiguous = (24.0 <= lat <= 50.5) and (-125.0 <= lon <= -66.0)

    # Alaska
    alaska = (51.0 <= lat <= 72.5) and (-170.0 <= lon <= -130.0)

    # Hawaii
    hawaii = (18.0 <= lat <= 23.5) and (-161.0 <= lon <= -154.0)

    return contiguous or alaska or hawaii

def get_jfk(df_airports: pd.DataFrame) -> pd.Series:
#Return the row for JFK from the airports table
    jfk = df_airports.loc[df_airports["faa"].astype(str).str.upper() == "JFK"]
    if jfk.empty:
        raise ValueError("Could not find JFK in airports.csv (faa == 'JFK').")
    return jfk.iloc[0]

def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
# <- check that output dir exist lol

def save_html(fig: go.Figure, name: str) -> Path:
#Save Plotly figure to HTML
    ensure_out_dir()
    out_path = OUT_DIR / f"{name}.html"
    fig.write_html(out_path, include_plotlyjs="cdn")
    return out_path

def analyze_timezones(df: pd.DataFrame) -> go.Figure:

    counts = (
        df.assign(tzone=df["tzone"].fillna("Unknown"))
          .groupby("tzone", as_index=False)
          .size()
          .sort_values("size", ascending=False)
    )

    fig = px.bar(
        counts,
        x="tzone",
        y="size",
        title="Time zones — number of airports per time zone (proxy for 'relative amount')",
    )
    fig.update_layout(xaxis_title="Time zone", yaxis_title="Number of airports", margin=dict(l=10, r=10, t=60, b=10))
    return fig
