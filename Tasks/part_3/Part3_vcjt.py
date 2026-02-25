import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import math
import sys
import os

#with sqlite3.connect('flights_database.db') as connection:
#    cursor = connection.cursor()
#    query = "SELECT * FROM airlines;"
#    cursor.execute(query)
#    output=cursor.fetchall()
#    for item in output:
#        print(item)


#connection = sqlite3.connect("flights_database.db")
#variable = "\"A321-211\""
#query = f"SELECT tailnum FROM planes WHERE model = {variable}"
#cursor = connection.execute(query)
#output = cursor.fetchall()
#df = pd.DataFrame(output, columns = [x[0] for x in cursor.description])
#print(df)


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
    
    
    connection.close()