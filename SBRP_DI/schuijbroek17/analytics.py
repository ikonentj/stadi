import pandas as pd
import numpy as np
from copy import deepcopy

def preprocessTrips_boston(trips):
    trips['Duration'] = trips['Duration'] / 1e3   # duration to seconds (was milliseconds)
    trips['Start date'] = pd.to_datetime(trips['Start date'])
    trips['End date'] = pd.to_datetime(trips['End date'])
    trips.sort_values(by='Start date', inplace=True)

    trips.set_index('Start date', inplace=True, drop=False)
    trips.drop(columns=['Bike number', 'Member type', 'Zip code', 'Gender'], inplace=True)

def preprocessTrips_helsinki(trips):
    # time time stamps to datetime
    trips['Departure'] = pd.to_datetime(trips['Departure'])
    trips['Return'] = pd.to_datetime(trips['Return'])
    
    # rename the columns
    trips.columns = ['Start date', 'End date', 
                     'Start station number', 'Start station name', 
                     'End station number', 'End station name',
                     'Distance', 'Duration']
    
    # sort by the start date
    trips.sort_values(by='Start date', inplace=True)
    
    # sort the columns
    col_order = ['Duration', 'Start date', 'End date', 
                 'Start station number', 'Start station name', 
                 'End station number', 'End station name']
    trips = trips.reindex(columns=col_order)
    
    # set 'Start date' as the index
    trips.set_index('Start date', inplace=True, drop=False)
    
    # drop trips with nans
    trips.dropna(inplace=True)
    
    # ensure that station numbers are ints
    for col in ['Start station number', 'End station number']:
        trips[col] = trips[col].astype(np.int)

    return trips

def preprocessStations_helsinki(stations):
    stations.drop(columns=['FID', 'Nimi', 'Namn', 'Osoite', 'Adress', 'Stad', 'Operaattor'], inplace=True)

    stations.columns = ['Station ID', 'Station', 'City', '# of Docks', 'Longitude', 'Latitude']
    stations = stations.reindex(columns=['Station ID', 'Station', 'Longitude', 'Latitude', '# of Docks', 'City'])
    stations.sort_values(by='Station ID', inplace=True)
    stations.set_index('Station ID', inplace=True)
    
    return stations

def add_n_intervals(props):
	props['n_intervals'] = int(24 / props['interval'])

def add_dates(props, df):
	props['dates'] = list(set(df.index.date))
	props['dates'].sort()

def get_pickup_return_datasets(train, props):
    # determine if only weekdays are considered 
    if props['weekdaysOnly']:
        weekday_ub = 4
    else:
        weekday_ub = 6
    
    # get the pickup training set
    train_pickup = deepcopy(train[(train.index.weekday <= weekday_ub) 
#                                       & (train.index.hour >= props['hour_start']) 
#                                       & (train.index.hour < props['hour_end'])
                                    ])

    # get the return training set
    train.set_index('End date', inplace=True, drop=False)
    train_return = deepcopy(train[(train.index.weekday <= weekday_ub) 
#                                       & (train.index.hour >= props['hour_start']) 
#                                       & (train.index.hour < props['hour_end'])
                                    ])
    train.set_index('Start date', inplace=True, drop=False)
    
    return train_pickup, train_return

def includeDates(df, props):
    # create {date: ord} dictionary
    dates_dict = {k: int(v) for v, k in enumerate(props['dates'])}

    # day ordinal of day
    df['day'] = df.index.date
    df['day_ord'] = df.day.map(dates_dict)

    # intervals
    df['interval'] = (
                     df.index.hour / props['interval'] \
                    + df.index.minute / 60 // props['interval']
                        ).astype(np.int64)

def extract_rate(stations, df, props):
    # determine the station key ('Start station number' or 'End station number')
    station_key = df.index.name.replace('date', 'station number')
    
    # init counts dataframe
    counts = pd.DataFrame(columns = [i for i in range(props['n_intervals'])])

    # count pickups or returns separately at each station
    for station in stations.index:
        counts.loc[station, :] = \
            df[(df[station_key] == station)].groupby(
            by='interval', dropna=True).count()[df.index.name]

    # if pickup or return does not appear at a station, mark it as zero
    counts.fillna(0, inplace=True)

    # return the the rate per hour
    return counts / len(props['dates']) / props['interval']

def fetchLevels(stations, snapshots, time, clip=False):
    # set station id as the index
    stations.set_index('Station ID', inplace=True)

    # fetch the level individually for all stations
    for station_id in stations.index:
        level = snapshots[snapshots['Station ID'] == station_id].loc[:time, 'bikesAvailable'].values[-1]
        stations.loc[station_id, 'level'] = level
        
    # reset the index
    stations.reset_index(inplace=True)

    # clip the levels of overfull stations
    if clip:
        stations['level'] = stations['level'].clip(None, stations['# of Docks'])