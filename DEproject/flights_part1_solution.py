
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



def plot_all_airports_world(df: pd.DataFrame, color_by_altitude: bool = False) -> go.Figure:
#World map with points for all airports
    color = "alt" if color_by_altitude else None
    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        hover_name="name",
        hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
        color=color,
        title="All airports (world map)" + (" — color coded by altitude" if color_by_altitude else ""),
    )
    fig.update_geos(showland=True)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return fig


def plot_airports_us_and_outside(df: pd.DataFrame, color_by_altitude: bool = False) -> Tuple[go.Figure, go.Figure]:
    #Identify airports outside the US
     # Map of outside-US airports world map
      # Map of US-only airports
    df = df.copy()
    df["in_us"] = df.apply(lambda r: is_us_airport(r["lat"], r["lon"]), axis=1)

    df_us = df[df["in_us"]].copy()
    df_out = df[~df["in_us"]].copy()

    color = "alt" if color_by_altitude else None

    fig_out = px.scatter_geo(
        df_out,
        lat="lat",
        lon="lon",
        hover_name="name",
        hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
        color=color,
        title="Airports outside the US (heuristic from lat/lon)" + (" — color coded by altitude" if color_by_altitude else ""),
    )
    fig_out.update_geos(showland=True)
    fig_out.update_layout(margin=dict(l=10, r=10, t=60, b=10))

    fig_us = px.scatter_geo(
        df_us,
        lat="lat",
        lon="lon",
        hover_name="name",
        hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
        color=color,
        scope="usa",
        title="Airports in the US (heuristic from lat/lon)" + (" — color coded by altitude" if color_by_altitude else ""),
    )
    fig_us.update_layout(margin=dict(l=10, r=10, t=60, b=10))

    return fig_out, fig_us


def _route_lines_trace(
    origin_lat: float, origin_lon: float, dest_lats: Sequence[float], dest_lons: Sequence[float]
) -> go.Scattergeo:

    #Create a single Scattergeo trace containing multiple independent line segments.
    #Plotly separates segments with None.

    lats: List[Union[float, None]] = []
    lons: List[Union[float, None]] = []
    for lat, lon in zip(dest_lats, dest_lons):
        lats.extend([origin_lat, lat, None])
        lons.extend([origin_lon, lon, None])

    return go.Scattergeo(
        lat=lats,
        lon=lons,
        mode="lines",
        line=dict(width=2),
        hoverinfo="skip",
        name="Routes",
    )


def plot_route_from_nyc(df: pd.DataFrame, faa: str, us_only_if_us: bool = True) -> go.Figure:

    #function that takes an FAA abbreviation and plots a world map and a line from NYC (JFK) to that airport

    #Note: If the airport is in the US, make a US-only map (scope='usa') when us_only_if_us=True.

    df = df.copy()
    faa = str(faa).upper()

    jfk = get_jfk(df)
    target = df.loc[df["faa"].astype(str).str.upper() == faa]
    if target.empty:
        raise ValueError(f"FAA code '{faa}' not found in airports.csv.")
    target = target.iloc[0]

    in_us = is_us_airport(float(target["lat"]), float(target["lon"]))
    use_usa_scope = bool(us_only_if_us and in_us)

    if use_usa_scope:
        base = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
            scope="usa",
            title=f"Route from NYC (JFK) to {faa} — US-only scope",
        )
    else:
        base = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
            title=f"Route from NYC (JFK) to {faa} — world scope",
        )
        base.update_geos(showland=True)

    # Routeline
    line = _route_lines_trace(float(jfk["lat"]), float(jfk["lon"]), [float(target["lat"])], [float(target["lon"])])
    base.add_trace(line)

    # points
    base.add_trace(
        go.Scattergeo(
            lat=[float(jfk["lat"])],
            lon=[float(jfk["lon"])],
            mode="markers",
            marker=dict(size=10),
            name="JFK",
            text=["JFK (NYC)"],
            hoverinfo="text",
        )
    )
    base.add_trace(
        go.Scattergeo(
            lat=[float(target["lat"])],
            lon=[float(target["lon"])],
            mode="markers",
            marker=dict(size=10),
            name=faa,
            text=[f"{faa}: {target['name']}"],
            hoverinfo="text",
        )
    )

    base.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return base


def plot_routes_from_nyc(df: pd.DataFrame, faas: Sequence[str], us_only_if_us: bool = False) -> go.Figure:

    df = df.copy()
    faas = [str(x).upper() for x in faas]

    jfk = get_jfk(df)
    targets = df[df["faa"].astype(str).str.upper().isin(faas)].copy()

    missing = sorted(set(faas) - set(targets["faa"].astype(str).str.upper()))
    if missing:
        raise ValueError(f"FAA codes not found in airports.csv: {missing}")

    targets["in_us"] = targets.apply(lambda r: is_us_airport(r["lat"], r["lon"]), axis=1)

    use_usa_scope = bool(us_only_if_us and targets["in_us"].all())

    if use_usa_scope:
        fig = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
            scope="usa",
            title=f"Routes from NYC (JFK) to {len(faas)} airports — US-only scope",
        )
    else:
        fig = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={"faa": True, "alt": True, "tzone": True, "lat": False, "lon": False},
            title=f"Routes from NYC (JFK) to {len(faas)} airports — world scope",
        )
        fig.update_geos(showland=True)

    #multi-segment line trace
    line = _route_lines_trace(float(jfk["lat"]), float(jfk["lon"]), targets["lat"].astype(float), targets["lon"].astype(float))
    fig.add_trace(line)

    #JFK marker
    fig.add_trace(
        go.Scattergeo(
            lat=[float(jfk["lat"])],
            lon=[float(jfk["lon"])],
            mode="markers",
            marker=dict(size=10),
            name="JFK",
            text=["JFK (NYC)"],
            hoverinfo="text",
        )
    )

    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return fig


def euclidean_distance_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float, R_km: float = 6371.0) -> float:

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lam1 = math.radians(lon1)
    lam2 = math.radians(lon2)

    dphi = phi2 - phi1
    dlam = lam2 - lam1
    phi_m = 0.5 * (phi1 + phi2)

    term1 = 2.0 * math.sin(dphi / 2.0) * math.cos(dlam / 2.0)
    term2 = 2.0 * math.cos(phi_m) * math.sin(dlam / 2.0)

    return R_km * math.sqrt(term1 * term1 + term2 * term2)


def plot_distance_distributions(df: pd.DataFrame) -> Tuple[pd.DataFrame, go.Figure, go.Figure]:

    df = df.copy()
    jfk = get_jfk(df)

    lat0 = float(jfk["lat"])
    lon0 = float(jfk["lon"])

    df["dist_euclid_deg"] = df.apply(lambda r: euclidean_distance_deg(lat0, lon0, float(r["lat"]), float(r["lon"])), axis=1)
    df["dist_geodesic_km"] = df.apply(lambda r: geodesic_distance_km(lat0, lon0, float(r["lat"]), float(r["lon"])), axis=1)

    # Basic stats
    stats = df[["dist_euclid_deg", "dist_geodesic_km"]].describe(percentiles=[0.25, 0.5, 0.75]).T
    stats = stats.rename(columns={"50%": "median"})

    fig_e = px.histogram(
        df,
        x="dist_euclid_deg",
        nbins=50,
        title="Distribution of Euclidean distances from JFK (in degree space)",
    )
    fig_e.update_layout(margin=dict(l=10, r=10, t=60, b=10))

    fig_g = px.histogram(
        df,
        x="dist_geodesic_km",
        nbins=50,
        title="Distribution of geodesic distances from JFK (km, R=6371)",
    )
    fig_g.update_layout(margin=dict(l=10, r=10, t=60, b=10))

    return stats, fig_e, fig_g


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



def main() -> None:
    # Load
    df = pd.read_csv(DATA_PATH)

    print("Loaded airports.csv")
    print(df.head())
    print(f"Rows: {len(df):,}  Columns: {list(df.columns)}")

    # Task 1
    fig_all = plot_all_airports_world(df, color_by_altitude=False)
    save_html(fig_all, "01_all_airports_world")

    # Extra color coded by altitude
    fig_all_alt = plot_all_airports_world(df, color_by_altitude=True)
    save_html(fig_all_alt, "01b_all_airports_world_altitude")

    # 2 outside US + US-only map
    fig_out, fig_us = plot_airports_us_and_outside(df, color_by_altitude=False)
    save_html(fig_out, "02_airports_outside_us")
    save_html(fig_us, "03_airports_us_only")

    # Extra altitude coloring
    fig_out_alt, fig_us_alt = plot_airports_us_and_outside(df, color_by_altitude=True)
    save_html(fig_out_alt, "02b_airports_outside_us_altitude")
    save_html(fig_us_alt, "03b_airports_us_only_altitude")

    # 3 function route map for one FAA code
    example_faa = "LAX"
    fig_route = plot_route_from_nyc(df, example_faa, us_only_if_us=True)
    save_html(fig_route, f"04_route_JFK_to_{example_faa}")

    #4 routes to multiple FAA codes (example)
    example_faas = ["LAX", "ORD", "MIA", "SEA"]
    fig_routes = plot_routes_from_nyc(df, example_faas, us_only_if_us=False)
    save_html(fig_routes, "05_routes_JFK_to_multiple")

    # 5 Euclidean distance distribution from JFK
    stats, fig_euclid, fig_geo = plot_distance_distributions(df)
    print("\nDistance summary statistics (from JFK):")
    print(stats)

    save_html(fig_euclid, "06_distribution_euclidean_degree_space")
    save_html(fig_geo, "07_distribution_geodesic_km")

    # 6 time zones analysis
    fig_tz = analyze_timezones(df)
    save_html(fig_tz, "08_timezones_airport_counts_proxy")

    print(f"\nSaved all interactive plots to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
