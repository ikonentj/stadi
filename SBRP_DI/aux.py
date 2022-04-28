from itertools import chain, combinations, tee, product
import pandas as pd
import numpy as np
import gurobipy as gp
from copy import deepcopy
from scipy.spatial.distance import cdist
from geopy.distance import geodesic
import os, json, subprocess
from SBRP_DI import fileOperations as fo

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def duplicateLast(series):
    row = deepcopy(series)
    if row.empty:
        return row
    else:
        row[series.index[-1]+1] = series.values[-1]
        return row

def isWithin(a, b, digits=4):
    epsilon = 10 ** -digits
    if b == 0.:
        return abs(a) < epsilon
    else:    
        return abs(a/b - 1) < epsilon

def getResults(m, path=None):
    # init
    attributes = ['Status', 'ObjVal', 'ObjBound', 'MIPGap', 'Runtime', 'NumVars', 'NumBinVars']
    results = {}
    
    # collect the attributes
    for attribute in attributes:
        try:
            results[attribute] = getattr(m, attribute)
        except (AttributeError, gp.GurobiError):
            results[attribute] = None

    # print or save
    if path == None:
        for key, val in results.items():
            print(key, ': ', val)
    else:
        fo.saveJson(path, results)

def getDmatrix(stations, detour_factor=1, units='coordinates', fillna=True, rounding=False):
    # define a helper function
    def geodesic_meters(sour, dest):
        try:
            return geodesic(sour, dest).meters
        except ValueError:
            return np.nan
    
    # determine the dmatrix using scipy's cdist function
    coords = stations[['Latitude', 'Longitude']].values
    if units == 'coordinates':
        c_dist_values = cdist(coords, coords, metric=geodesic_meters)
    else:
        c_dist_values = cdist(coords, coords)

    # round the elements
    if rounding:
        c_dist_values = np.round(c_dist_values)
    
    dmatrix = detour_factor * pd.DataFrame(c_dist_values, index=stations.index, columns=stations.index)

    if fillna:
        return dmatrix.fillna(0)
    else:
        return dmatrix


def fixBounds_in_props(props):
    for key in ['latitude_min', 'longitude_min']:
        if props[key] == None:
            props[key] = -np.inf

    for key in ['latitude_max', 'longitude_max']:
        if props[key] == None:
            props[key] = np.inf

def dt_to_hours(series):
    return (series.hour + series.minute/60 + series.second/3600)

def randomizeVehicleLocations(stations, params, exclSS=True):
    np.random.seed(1)
    if exclSS:
        index = stations[~stations.selfSufficient].index
    else:
        index = stations.index

    for vehicle_id, i in enumerate(np.random.permutation(index)[:len(params['q_0'])]):
        stations.loc[i, 'vehicleLoc'] = vehicle_id

def replaceColon(time):
    return time.__str__().replace(':', '_')

def recordGitCommit(path):
    commitId = subprocess.check_output(["git", "describe", "--always"]).decode().rstrip()
    if os.path.isfile(path + "commitId.txt"):
        with open(path + "commitId.txt", 'r') as f:
            lastCommitId = f.readlines()[0].rstrip()
        if commitId == lastCommitId:
            pass
        else:
            sys.exit('The run has been initiated from a different commit ({})'.format(lastCommitId))
    else:
        with open(path + "commitId.txt", 'w') as f:
            f.write(commitId)

def powerset(iterable, exclEmpty=False, n=None):
    # define the starting point
    if exclEmpty:
        start = 1
    else:
        start = 0

    # define the max number of vertices
    if n == None:
        n = len(iterable)
    
    # return the power set using itertools 'chain' and 'combinations'
    return list(chain.from_iterable(combinations(iterable, r) for r in range(start, n+1)))

def recordGitCommit(path):
    commitId = subprocess.check_output(["git", "describe", "--always"]).decode().rstrip()
    with open(path + "commitId.txt", 'w') as f:
        f.write(commitId)

def findStart(stations):
    # find the start
    arr = stations[stations.vehicleLoc.notna()].index.values
    if len(arr) == 0:
        return None
    else:
        return arr[0]

def pickStations(allStations, params):
    # flag selfSufficients means that all stations are included
    if params['selfSufficients']:
        return allStations
    
    # init
    ids = allStations[-allStations.selfSufficient].index
    picks = allStations[allStations.index.isin(ids)]
    selfsuffs = allStations[allStations.selfSufficient].copy()
    lack_of_bikes, too_many_bikes = True, True

    while lack_of_bikes or too_many_bikes:
        # test if lack of bikes
        lack_of_bikes = picks.s_min.sum() >= picks.level.sum() + sum(params['q_0'])
        if lack_of_bikes:
            # add the self-sufficient stations with the most free bikes
            tba = (selfsuffs.level - selfsuffs.s_min).sort_values().index[-1:]
            ids = ids.append(tba)
            selfsuffs.drop(tba, inplace=True)

        # test if too many bikes
        too_many_bikes = picks.level.sum() - picks.s_max.sum() >= sum([params['Q'] - q_0 for q_0 in params['q_0']])
        if too_many_bikes:
            # add the self-sufficient stations with the most free spaces
            tba = (selfsuffs.s_max - selfsuffs.level).sort_values().index[-1:]
            ids = ids.append(tba)
            selfsuffs.drop(tba, inplace=True)

        picks = allStations[allStations.index.isin(ids)]

        # break if all stations are added from selfsuffs
        if selfsuffs.empty:
            break

    return picks
