import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
csv_path = project_root/'data'/'airports.csv'


df = pd.read_csv(csv_path)

#Task 1 - Map with airports

fig_world = px.scatter_geo(df, lat = 'lat', lon='lon', hover_name='faa',
                           title='Airports')
fig_world.show()

#Task 2 - Airports plotting
us_airports = df[(df['lat'] >=19) & (df['lat']<=72) & (df['lon'] >=-167) & (df['lon']<=-66)]  
non_us_airports = df[~df.index.isin(us_airports.index)]                  

fig_us = px.scatter_geo(
    us_airports, lat='lat', lon='lon', hover_name='faa',
    color='alt', scope='usa',
    projection='albers usa',
    title='Airports in the US'
)
fig_us.update_geos(
    visible=True,
    resolution=50,
    showcountries=True,
    countrycolor="RebeccaPurple"
)
fig_us.show()

fig_non_us = px.scatter_geo(
    non_us_airports, lat='lat', lon='lon', hover_name='faa',
    title='Airports not in the US',
)
fig_non_us.update_geos(
    showcountries=True,
    countrycolor="LightGrey",
    showland=True,
    landcolor="White",
    showocean=True,
    oceancolor="LightBlue"
)
fig_non_us.show()

#Task 3 - Flights from NYC (JFK)

jfk_lat, jfk_lon = 40.6398, -73.7789

def plot_flights_from_nyc(faa_list):
     
    destinations = df[df['faa'].isin(faa_list)]
    
    if destinations.empty:
        print('None of the FAA codes were identified in the dataset')
        return
    
    all_in_us = all((dest['lat'] >= 19) and (dest['lat'] <= 72) and
                (dest['lon'] >= -167) and (dest['lon'] <= -66)
                for _, dest in destinations.iterrows())

    map_scope = 'usa' if all_in_us else 'world'

    fig=go.Figure()

    target_airports = us_airports if all_in_us else df

    fig.add_trace(go.Scattergeo(
        lon=target_airports['lon'],
        lat=target_airports['lat'],
        hoverinfo='text',
        text=target_airports['faa'],
        mode='markers', marker=dict(size=2, color='gray', opacity=0.3),
        name="Airports"  
    ))


    for _, dest in destinations.iterrows():
        fig.add_trace(go.Scattergeo(
            lon=[jfk_lon, dest['lon']],
            lat=[jfk_lat, dest['lat']],
            mode='lines+markers',
            line=dict(width=2, color='red'),
            name=f"JFK to {dest['faa']}"
        ))

    if all_in_us:
        fig.update_layout(
            title_text='Flights from NYC (JFK)',
            geo=dict(scope='usa', projection_type='albers usa',
            showland=True,
            landcolor="White",
            
            showcoastlines=True,
            coastlinecolor="Black",
            coastlinewidth=2,
            showcountries=True,
            countrycolor="Black",
            countrywidth=2,
            showsubunits=True,
            subunitcolor="DimGray",
            subunitwidth=1
            )
        )
    else:
        fig.update_layout(
            title_text='Flights from NYC (JFK)',
            geo=dict(scope='world',
                projection_type='equirectangular',
                showland=True,
                landcolor="White",
                
                showcoastlines=True,
                coastlinecolor="Black",
                coastlinewidth=1.5,
                showcountries=True,
                countrycolor="Black",
                countrywidth=1.5
            )
        )
    fig.show()


plot_flights_from_nyc(['LAX','ORD','MIA','SFO'])

plot_flights_from_nyc(['TZR'])


#Task 4 - Euclidean and Geodesic distances

#Euclidean distance
df['euclidean_dist'] = np.sqrt((df['lat'] - jfk_lat)**2 + (df['lon']-jfk_lon)**2)

#Geodesic distance
def calc_geodesic(lat1, lon1, lat2, lon2, R=6371):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    delta_phi = lat2 - lat1
    delta_lambda = lon2 - lon1
    phi_m = (lat1 - lat2) / 2.0
    
    term1 = (2 * np.sin(delta_phi / 2) * np.cos(delta_lambda / 2)) **2
    term2 = (2 * np.cos(phi_m) * np.sin(delta_lambda / 2)) **2
    return R * np.sqrt(term1+term2)

df['geodesic_dist'] = calc_geodesic(jfk_lat, jfk_lon, df['lat'], df['lon'])

fid_dist, axes = plt.subplots(1,2, figsize=(14,5))

axes[0].hist(df['euclidean_dist'].dropna(), bins=50, color='skyblue', edgecolor='black')
axes[0].set_title('Distribution of Euclidean distances from JFK')
axes[0].set_xlabel('Euclidean distance')
axes[0].set_ylabel('Frequency')


axes[1].hist(df['geodesic_dist'].dropna(), bins=50, color='lightgreen', edgecolor='black')
axes[1].set_title('Distribution of geodesic distances from JFK')
axes[1].set_xlabel('Geodesic distance')
axes[1].set_ylabel('Frequency')

plt.tight_layout()
plt.show()


#Task 5 - Timezones
if 'tzone' in df.columns:
    tz_counts = df['tzone'].value_counts().reset_index()
    tz_counts.columns = ['Timezone', "Airport Count"]
    
    fig_tz = px.bar(
            tz_counts.head(15), x='Timezone', y='Airport Count',
            title='Top 15 time zones by airport density',
            color='Airport Count', color_continuous_scale='Viridis'
    )
    fig_tz.show()
else:
    print("Timezone column not found.")
    