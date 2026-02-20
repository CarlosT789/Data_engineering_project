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


#Run code
if __name__== "__main__":
    df_result_1 = distance_checking(connection)
    print(df_result_1.head())
    
    df_result_2 = obtain_airports_origin_NYC(connection)
    print(df_result_2.head())
    
    connection.close()