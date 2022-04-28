import numpy as np
import pandas as pd
from SBRP_DI.aux import getDmatrix
import SBRP_DI.convexHull as hull

def extractRates(mu, lamda, station, props):
    # create a dataframe of rates
    rates = pd.DataFrame({
            'time': np.arange(props['n_intervals']) * props['interval'],
            'mu'      : mu.loc[station, :].values,
            'lamda'   : lamda.loc[station, :].values
            })

    # close the transits
    rates.loc[props['n_intervals'], 'time'] = props['n_intervals'] * props['interval']

    # set time as index
    rates.set_index('time', inplace=True)

    return rates

def randomizeLevels(stations):
    stations['level'] = np.random.randint(0, stations['# of Docks'])

def getSelfSufficients(stations):
    stations['selfSufficient'] = (stations['level'] >= stations['s_min']) \
                               & (stations['level'] <= stations['s_max'])

def params_from_stations(stations, params, model='routing'):
    stations = stations.reset_index()
    params.update({
            'S0'            : list(stations.index[stations['selfSufficient'] & stations['vehicleLoc'].isna()]),
            's_0'           : stations['level'].values.tolist(),
            's_min'         : stations['s_min'].values.tolist(),
            's_max'         : stations['s_max'].values.tolist(),
            'C'             : stations['# of Docks'].values.tolist(),
            'dist'          : getDmatrix(stations, detour_factor=params['detour_factor'], units=params['units'], 
                                                   rounding=params['D_matrix_rounding']).values.tolist(),
            'n_vehicles'    : len(params['q_0'])
         })

    if model == 'clustering':
        params['S']       = list(stations.index)
        params['s_minus'] = stations['s_minus'].values.tolist()
        params['s_plus']  = stations['s_plus'].values.tolist()
    elif model == 'routing':
        params['n']       = stations.shape[0]

    # determine the starting station(s)
    if model == 'clustering':
        if stations.vehicleLoc.isna().all():
            params['locations_ord'] = [None for _ in params['q_0']]
        else:
            params['locations_ord'] = list(stations[stations.vehicleLoc.notna()].vehicleLoc.sort_values().index)
    elif model == 'routing':
        arr = stations[stations.vehicleLoc.notna()].index.values
        if len(arr) == 0:
            params['start'] = None
        else:
            params['start'] = arr[0]

def extra_timeSlots(stations, params):
    # maximum number of visits
    params['max_visits'] = []
    for i in stations.index:
        if not np.isnan(stations.loc[i, 'vehicleLoc']):
            params['max_visits'].append(1 + hull.tools.getVehicNeeded_start(i, stations, params)[1])
        else:
            params['max_visits'].append(1 + hull.tools.getVehicNeeded(i, stations, params)[1])

    # determine the additional time slots
    params['sch17_extra_timeSlots'] = 0
    bound = params['sch17_ts_bound']
    for i in stations.index:
        if not np.isnan(stations.loc[i, 'vehicleLoc']):
            params['sch17_extra_timeSlots'] += hull.tools.getVehicNeeded_start(i, stations, params)[bound]
        elif params['splitDemand']:
            params['sch17_extra_timeSlots'] += hull.tools.getVehicNeeded(i, stations, params)[bound]

def interpolate(data, index, newIndex):
    df = pd.DataFrame(data, index=index)
    # define the grid as a data frame
    grid = pd.DataFrame(index=newIndex)

    # concat, filter duplicates, sort index, and make the interpolation
    df_g = pd.concat([df, grid])
    df_g = df_g[~df_g.index.duplicated(keep='first')]
    df_g = df_g.sort_index()
    df_g = df_g.interpolate(method='index')[df_g.index.isin(newIndex)]
    return df_g.index, df_g.values