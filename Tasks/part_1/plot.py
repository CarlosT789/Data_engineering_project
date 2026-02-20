
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Iterable, List, Sequence, Tuple, Union
import temp
import dist

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
    df["in_us"] = df.apply(lambda r: temp.is_us_airport(r["lat"], r["lon"]), axis=1)

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


def plot_routes_from_nyc(df: pd.DataFrame, faas: Sequence[str], us_only_if_us: bool = False) -> go.Figure:

    df = df.copy()
    faas = [str(x).upper() for x in faas]

    jfk = temp.get_jfk(df)
    targets = df[df["faa"].astype(str).str.upper().isin(faas)].copy()

    missing = sorted(set(faas) - set(targets["faa"].astype(str).str.upper()))
    if missing:
        raise ValueError(f"FAA codes not found in airports.csv: {missing}")

    targets["in_us"] = targets.apply(lambda r: temp.is_us_airport(r["lat"], r["lon"]), axis=1)

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

def plot_distance_distributions(df: pd.DataFrame) -> Tuple[pd.DataFrame, go.Figure, go.Figure]:

    df = df.copy()
    jfk = temp.get_jfk(df)

    lat0 = float(jfk["lat"])
    lon0 = float(jfk["lon"])

    df["dist_euclid_deg"] = df.apply(lambda r: dist.euclidean_distance_deg(lat0, lon0, float(r["lat"]), float(r["lon"])), axis=1)
    df["dist_geodesic_km"] = df.apply(lambda r: dist.geodesic_distance_km(lat0, lon0, float(r["lat"]), float(r["lon"])), axis=1)

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
