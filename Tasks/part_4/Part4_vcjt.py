import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import math
import sys
import os


sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'part_1'))


from Part1e import geodesic_distance_km
db_path = os.path.join(os.path.dirname(__file__), '..','..', 'data', 'flights_database.db')
connection = sqlite3.connect(db_path)

flights_df = pd.read_sql_query("SELECT * FROM FLiGHTS", connection)


#Task Missing values
    
print("Task Missing values")
print('\n')

missing_values = flights_df.isnull().sum()
print("missing values:\n", missing_values)
print('\n')
flights_clean = flights_df.dropna(subset = ['dep_time', 'arr_time']).copy()

#Task duplicates

print("Task duplicates")
print('\n')

filter_duplicate = flights_clean.duplicated(subset = ['year','month', 'day','carrier', 'flight'],
                                            keep=False)

print(f"duplicate flights: {filter_duplicate.sum()}")
print('\n')

flights_clean = flights_clean.drop_duplicates(subset = ['year','month', 'day','carrier', 'flight'])


#Task datetime objects

print("Task datetime objects")
print('\n')

def convert_datetime_obj(df, time_col):
    time_str = df[time_col].fillna(0).astype(int).astype(str).str.zfill(4)

    hours = time_str[:-2].replace('','0')
    minutes = time_str[-2:]
    
    hours = hours.replace('24','00')
    
    dt_str = df['year'].astype(str) + '-' + df['month'].astype(str) + '-' + \
        df['day'].astype(str) + ' ' + hours + ':' + minutes
        
    return pd.to_datetime(dt_str, format = '%Y-%m-%d %H:%M', errors='coerce')

flights_clean['dep_datetime'] = convert_datetime_obj(flights_clean, 'dep_time')
flights_clean['sched_dep_datetime'] = convert_datetime_obj(flights_clean, 'sched_dep_time')
flights_clean['arr_datetime'] = convert_datetime_obj(flights_clean, 'arr_time')
flights_clean['sched_arr_datetime'] = convert_datetime_obj(flights_clean, 'sched_arr_time')

#Task Flight order

print("Task Flight order")
print('\n')

def flight_order(df):
    calculated_delay = (df['dep_datetime'] - df['sched_dep_datetime']).dt.total_seconds() / 60
    is_in_order = (calculated_delay == df['dep_delay'])

    print(f"ordered flights: {is_in_order.sum()} / {len(df)}")
    print('\n')
    
    df['is_consistent'] = is_in_order
    return df

flights_clean = flight_order(flights_clean)


#Task Arrival time computation

print("Arrival time computation")
print('\n')

airports_tz = pd.read_sql_query("SELECT faa, tz FROM airports", connection)

flights_clean = flights_clean.merge(airports_tz, left_on='origin', right_on='faa', how='left')
flights_clean = flights_clean.rename(columns={'tz':'origin_tz'}).drop(columns=['faa'])

flights_clean = flights_clean.merge(airports_tz, left_on='dest', right_on='faa', how='left')
flights_clean = flights_clean.rename(columns={'tz':'dest_tz'}).drop(columns=['faa'])

flights_clean['tz_diff'] = flights_clean['dest_tz'] - flights_clean['origin_tz']

flights_clean['calculated_local_arr'] = (flights_clean['dep_datetime'] +
                                         pd.to_timedelta(flights_clean['air_time'], unit='m') +
                                         pd.to_timedelta(flights_clean['tz_diff'], unit='h')
)

#Task Other - Airport stats

print("Other - Airport stats")
print('\n')

def get_airport_stats(df, airport_col='origin', airport_code='JFK'):
    filtered_df = df[df[airport_col] == airport_code]
    
    stats = {
        'total_flights': len(filtered_df),
        'avg_dep_delay':filtered_df['dep_delay'].mean(),
        'avg_arr_delay':filtered_df['arr_delay'].mean(),
        'avg_air_time':filtered_df['air_time'].mean()        
    }
    
    return pd.DataFrame([stats])

#Task Other - Analyze weather

print("Other - Analyze weather")
print('\n')

def analyze_weather_plane(connection):
    query = """
    SELECT p.type as plane_type, w.precip, w.wind_speed, f.dep_delay
    FROM flights f
    JOIN planes p ON f.tailnum = p.tailnum
    JOIN weather w ON f.origin = w.origin
        AND f.year = w.year
        AND f.month = w.month
        AND f.day = w.day
        AND f.hour = w.hour
    """ 
    joined_df = pd.read_sql_query(query, connection)
    summary = joined_df.groupby('plane_type').agg(
        avg_delay = ('dep_delay', 'mean'),
        avg_precip = ('precip', 'mean'),
        avg_wind = ('wind_speed', 'mean'),
        flight_count = ('dep_delay', 'size')
    ).reset_index()

    return summary

connection.close()