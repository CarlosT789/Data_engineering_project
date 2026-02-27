import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import math
import sys
import os

#Question 1
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'part_1'))


from Part1e import geodesic_distance_km
db_path = os.path.join(os.path.dirname(__file__), '..','..', 'data', 'flights_database.db')
connection = sqlite3.connect(db_path)

def distance_checking(connection):
    query = """
    SELECT f.origin, f.dest, f.distance,
            air1.lat as origin_lat, air1.lon as origin_lon,
            air2.lat as dest_lat, air2.lon as dest_lon
    FROM flights f
    JOIN airports air1 ON f.origin = air1.faa
    JOIN airports air2 ON f.dest = air2.faa
    """

    df = pd.read_sql_query(query, connection)

    df['distance_checked'] = df.apply(
        lambda row: geodesic_distance_km(
            row['origin_lat'], row['origin_lon'],
            row['dest_lat'], row['dest_lon']
        )*0.621371,
        axis=1        
    )
    return df

    
#Question 2
def obtain_airports_origin_NYC(connection):
    query = """
    SELECT DISTINCT airp.*
    FROM flights f
    JOIN airports airp ON f.origin = airp.faa
    """
    airports_origin_NYC_df = pd.read_sql_query(query, connection)
    return airports_origin_NYC_df

#Question 3
def plot_destinations_day(month, day, origin_airport, connection):
    query = """
    SELECT DISTINCT airp.faa, airp.name, airp.lat, airp.lon
    FROM flights fli
    JOIN airports airp ON fli.dest = airp.faa
    WHERE fli.month = ? AND fli.day = ? AND fli.origin = ?
    """ 

    df = pd.read_sql_query(query, connection, params = (month, day, origin_airport))

    if not df.empty:
        fig = px.scatter_geo(df, lat = 'lat', lon = 'lon', hover_name = 'name')
        fig.show()
    else:
        print("No flights were identified.")

#Question 4
def statistics_day(month, day, origin_airport, connection):
    query = """
    SELECT  fli.dest
    FROM flights fli
    WHERE fli.month = ? AND fli.day = ? AND fli.origin = ?
    """ 

    df = pd.read_sql_query(query, connection, params = (month, day, origin_airport))

    if df.empty:
        print("No flights were identified.")

    data = {
        'flights_total':len(df),
        'unique_dest': df['dest'].nunique(),
        'most_visit': df['dest'].value_counts().idxmax()
        }
    
    return data

#Question 5
def plane_types(origin_airport, destination_airport, connection):
    query = """
    SELECT pla.type, COUNT(*) as use
    FROM flights fli
    JOIN planes pla ON fli.tailnum = pla.tailnum
    WHERE fli.origin = ? AND fli.dest = ? AND pla.type IS NOT NULL
    GROUP BY pla.type
    """ 

    df = pd.read_sql_query(query, connection, params = (origin_airport, destination_airport))

    data = dict(zip(df['type'],df['use']))
    return data

#Question 6
def plot_delay_airline(connection):
    query = """
    SELECT air.name, AVG(fli.dep_delay) as delay
    FROM flights fli
    JOIN airlines air ON fli.carrier = air.carrier
    GROUP BY air.name
    """ 

    df = pd.read_sql_query(query, connection)

    fig = px.bar(df, x='name', y = 'delay',
                 title = "average delay",
                labels = {'name':"airline", 'delay':"average delay"})
    fig.update_layout(xaxis_tickangle=-45)
    fig.show()

#Question 7
def delay_flights(start, end, destination, connection):
    query = """
    SELECT COUNT(*) as delay
    FROM flights
    WHERE month BETWEEN ? AND ?
        AND dest = ?
        AND arr_delay>0
    """ 

    df = pd.read_sql_query(query, connection,params = (start, end, destination))
    return df['delay'].iloc[0]


#Question 8
def top_manufacturers(destination, connection):
    query = """
    SELECT pla.manufacturer, COUNT(*) as count
    FROM flights fli
    JOIN planes pla ON fli.tailnum = pla.tailnum
    WHERE fli.dest = ?
    GROUP BY pla.manufacturer
    ORDER BY count DESC
    """
    return pd.read_sql_query(query, connection,params = (destination,))

#Question 9
def distance_vs_delay(connection):
    query = """
    SELECT distance, arr_delay
    FROM flights fli
    WHERE arr_delay IS NOT NULL AND distance Is NOT NULL
    """
    df= pd.read_sql_query(query, connection)
    fig = px.scatter(df, x='distance', y = 'arr_delay',
                title = "distance vs arrival delay")
    fig.show()

#Question 10
def update_plane_speeds(connection):
    query = """
    WITH AvgSpeeds AS(
        SELECT tailnum, AVG(distance / (air_time / 60.0)) as avg_speed
        FROM flights
        WHERE distance IS NOT NULL AND air_time IS NOT NULL AND air_time>0
        GROUP BY tailnum
        )
    UPDATE planes
    SET speed =(
        SELECT avg_speed
        FROM AvgSpeeds
        WHERE AvgSpeeds.tailnum = planes.tailnum
    )
    WHERE EXISTS(
        SELECT 1
        FROM AvgSpeeds
        WHERE AvgSpeeds.tailnum = planes.tailnum
    );
    """
    cursor =connection.cursor()
    cursor.execute(query)
    connection.commit()
    print("database updated")


#Question 11 and 12
def inner_product(connection):
    query = """
    SELECT f.air_time, w.wind_dir, w.wind_speed,
        a1.lat as lat_origin, a1.lon as lon_origin,
        a2.lat as lat_dest, a2.lon as lon_dest
    FROM flights f
    JOIN weather w ON f.origin = w.origin
        AND f.year = w.year AND f.month = w.month
        AND f.day = w.day AND f.hour = w.hour
        
    JOIN airports a1 ON f.origin = a1.faa
    JOIN airports a2 ON f.dest = a2.faa
    WHERE w.wind_dir IS NOT NULL AND w.wind_speed IS NOT NULL
    AND f.air_time IS NOT NULL
    """
    df = pd. read_sql_query(query, connection)

    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2-lon1
        x = np.sin(dlon)*np.cos(lat2)
        y=np.cos(lat1)*np.sin(lat2)-np.sin(lat1)*np.cos(lat2)*np.cos(dlon)
        initial_bearing = np.arctan2(x,y)
        return (np.degrees(initial_bearing)*360) % 360

        
    df['flight_dir'] = df.apply(lambda row: calculate_bearing(row['lat_origin'], row['lon_origin'], row['lat_dest'], row['lon_dest']), axis=1)
    
    df['angle_diff_rad']=np.radians(df['flight_dir']-df['wind_dir'])
    df['inner_product']=df['wind_speed']*np.cos(df['angle_diff_rad'])
    
    df['inner_product_sign']=np.sign(df['inner_product']).map({1.0: 'Tailwind (+)', -1.0: 'Headwind (-)', 0.0: 'Neutral'})

    fig = px.box(df, x='inner_product_sign', y = 'air_time',
                title = "Relation")
    fig.show()


#Run code
if __name__== "__main__":
    df_result_1 = distance_checking(connection)
    print("Question 1")
    print(df_result_1.head())
    print('\n')
    
    df_result_2 = obtain_airports_origin_NYC(connection)
    print("Question 2")
    print(df_result_2.head())
    print('\n')
    
    df_result_3 = plot_destinations_day(12, 31, 'EWR', connection)
    print("Question 3")
    print('\n')
    
    df_result_4 = statistics_day(12, 31, 'EWR', connection)
    print("Question 4")
    print(df_result_4)
    print('\n')
    
    df_result_5 = plane_types('EWR', 'LAX', connection)
    print("Question 5")
    print(df_result_5)
    print('\n')
    
    df_result_6 = plot_delay_airline(connection)
    print("Question 6")
    print(df_result_6)
    print('\n')
    
    df_result_7 = delay_flights(1,3, 'DTW',connection)
    print("Question 7")
    print(df_result_7)
    print('\n')
    
    df_result_8 = top_manufacturers('LAX',connection)
    print("Question 8")
    print(df_result_8)
    print('\n')
    
    df_result_9 = distance_vs_delay(connection)
    print("Question 9")
    print(df_result_9)
    print('\n')
    
    df_result_10 = update_plane_speeds(connection)
    print("Question 10")
    print(df_result_10)
    print('\n')
    
    df_result_11 = inner_product(connection)
    print("Questions 11 and 12")
    print(df_result_11)
    print('\n')
    
    connection.close()