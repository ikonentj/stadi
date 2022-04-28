from argparse import ArgumentParser
import sys, os

import pandas as pd
import numpy as np
import matplotlib.pylab as plt
import copy
from SBRP_DI.schuijbroek17 import visu, algorithms, tools, analytics
from SBRP_DI import aux, fileOperations as fo

def defineParser():
    parser = ArgumentParser(description="The function fetches station data and determines the bounds for the number of bikes")
    parser.add_argument("case", type=str, help="Case id")
    return parser

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()
    path = 'cases/case{}/'.format(args.case)

    # make folder for the runs
    fo.makeFolder(path + 'runs/')

    # load properties
    props = fo.loadJson(path + 'props.json')
    analytics.add_n_intervals(props)

    # load trips
    trips = fo.loadTrips(props['window_start'], props['window_end'], props['city'])

    # preprocess trips
    trips = analytics.preprocessTrips_helsinki(trips)
    train = trips[props['window_start']:props['window_end']]
    train_pickup, train_return = analytics.get_pickup_return_datasets(train, props)
    analytics.add_dates(props, train_pickup)

    # add helpful columns
    analytics.includeDates(train_pickup, props)
    analytics.includeDates(train_return, props)

    # load station locations
    starting_year = props['window_start'].split('-')[0]
    stations = pd.read_csv('../data/helsinki/locations/{}.csv'.format(starting_year))
    stations.set_index('Station ID', inplace=True)

    # station specific users
    mu = analytics.extract_rate(stations, train_pickup, props)
    lamda = analytics.extract_rate(stations, train_return, props)

    # filter stations that are not used
    notUsed = lamda.index[(lamda.sum(axis=1) + mu.sum(axis=1) == 0).values]
    stations = stations[~stations.index.isin(notUsed)]
    print('Not used stations in the data (filtered): {}'.format(notUsed.values))

    # specify the stations to be included
    aux.fixBounds_in_props(props)
    stations = stations[
                        (stations['City'] == props['city']) & 
                        (stations['Latitude']  >= props['latitude_min']) &
                        (stations['Latitude']  <= props['latitude_max']) &
                        (stations['Longitude'] >= props['longitude_min']) &
                        (stations['Longitude'] <= props['longitude_max'])
                        ]

    # determine service level requirements
    algorithms.serviceLevelReq(stations, mu, lamda, props)

    # save results
    stations.to_csv(path + 'stations.csv')
    mu.to_csv(      path + 'mu.csv', index_label='Station ID')
    lamda.to_csv(   path + 'lamda.csv', index_label='Station ID')
    print('Saved the stations data to "{}"'.format(path))

    # plot capacities and inventory bounds
    fig = visu.plotCapacities(stations, annotate='id')
    fig.savefig(path + 'capacities.pdf')
