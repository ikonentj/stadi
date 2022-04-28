from SBRP_DI.aux import getDmatrix
import numpy as np
from itertools import product

def getImpossibles(params):
    params['impossibles'] = []
    for i, (dem_min_1, dem_max_1) in enumerate(zip(params['demand_min'], params['demand_max'])):
        for j, (dem_min_2, dem_max_2) in enumerate(zip(params['demand_min'], params['demand_max'])):
            if i == j:
                continue
            if dem_min_1 * dem_max_1 <= 0 or dem_min_2 * dem_max_2 <= 0:
                continue
            
            cases = [abs(dem_min_1 + dem_min_2), abs(dem_min_1 + dem_max_2), 
                    abs(dem_max_1 + dem_min_2), abs(dem_max_1 + dem_max_2)]
            if min(cases) > params['Q']:
                params['impossibles'].append((i,j))

def getH(params):
    # define S(i,j) = {h \in V_0, h != i, h != j, |q_i + q_j + q_h| > Q}
    # used in separatiosn 1 and 2
    S = list(range(params['n']))
    S_excl_start = [i for i in range(params['n']) if i != params['locations_ord'][0]]
    I_J = [(i, j) for i, j in product(S_excl_start, S_excl_start) if i != j]

    params['H'] = {}
    S_array = np.array(S)
    demand_min_array = np.array(params['demand_min'])
    demand_max_array = np.array(params['demand_max'])

    def testIfExceeds(i_j_h):
        mask = np.isin(S_array, i_j_h)
        total_demand_min = demand_min_array[mask].sum()
        total_demand_max = demand_max_array[mask].sum()
        if total_demand_min * total_demand_max <= 0:
            return False
        else:
            return min(np.abs(total_demand_min), np.abs(total_demand_max)) > params['Q']

    for i_j in I_J:
        h_cands = np.delete(S_array, list(i_j) + [0])
        bools = np.array([testIfExceeds(list(i_j) + [h_cand]) for h_cand in h_cands])
        params['H'][i_j] = list(h_cands[bools])

def params_from_stations(stations, params):
    # add coordinates as units if not specified
    if 'units' not in params:
        params['units'] = 'coordinates'

    # include the model params
    stations = stations.reset_index()
    params.update({
            'S0'            : list(stations.index[stations['selfSufficient'] & stations['vehicleLoc'].isna()]),
            'S+'            : list(stations.index[~stations['level'].isna() & (stations['s_min'] > stations['level'])]),
            'S-'            : list(stations.index[~stations['level'].isna() & (stations['s_max'] < stations['level'])]),
            'n'             : stations.shape[0],
            'demand_min'    : (stations['s_min'].values - stations['level'].values)[:len(params['groups'])].tolist(),
            'demand_max'    : (stations['s_max'].values - stations['level'].values)[:len(params['groups'])].tolist(),
            'level'         : stations['level'].values[:len(params['groups'])].tolist(),
            'C'             : stations['# of Docks'].values.tolist(),
            'dist'          : getDmatrix(stations, detour_factor=params['detour_factor'], units=params['units'],
                                                   rounding=params['D_matrix_rounding']).values.tolist()
         })

    #getH(params)
    #getImpossibles(params)

def n_vehicles_required(S, params):
    total_demand_min = np.sum([params['demand_min'][i] for i in S])
    total_demand_max = np.sum([params['demand_max'][i] for i in S])    
    # if the bounds of total demand have different signs (or either of them is 0), one vehicle is sufficient
    if total_demand_min * total_demand_max <= 0:
        return 1.0
    # else determine the number of vehicles based on the bound that is more desirable
    else:
        return np.ceil(min(np.abs(total_demand_min), np.abs(total_demand_max))/params['Q'])

def getVehicNeeded(i, stations, params):
    '''Number of additional vehicles needed at a station'''
    bounds = [abs(stations.loc[i, 's_min'] - stations.loc[i, 'level']) / params['Q'],
              abs(stations.loc[i, 's_max'] - stations.loc[i, 'level']) / params['Q']]
    add_vehic_needed_min = int(np.ceil(min(bounds))) - 1
    add_vehic_needed_max = int(np.ceil(max(bounds))) - 1

    if stations.loc[i, 'selfSufficient']:
        add_vehic_needed_min = 0

    return add_vehic_needed_min, add_vehic_needed_max

def getVehicNeeded_start(i, stations, params):
    '''Number of additional vehicles needed at the stating station'''
    v_id = int(stations.loc[i, 'vehicleLoc'])
    if stations.loc[i, 's_min'] > stations.loc[i, 'level']:  # demand of bikes on the vehicle
        bounds = [(stations.loc[i, 's_min'] - stations.loc[i, 'level'] - params['q_0'][v_id]) / params['Q'],
                  (stations.loc[i, 's_max'] - stations.loc[i, 'level'] - params['q_0'][v_id]) / params['Q']]
    elif stations.loc[i, 's_max'] < stations.loc[i, 'level']:   # demand of slots on the vehicle
        bounds = [(-stations.loc[i, 's_min'] + stations.loc[i, 'level'] - (params['Q'] - params['q_0'][v_id])) / params['Q'],
                  (-stations.loc[i, 's_max'] + stations.loc[i, 'level'] - (params['Q'] - params['q_0'][v_id])) / params['Q']]
    else:
        return [0, 0]

    add_vehic_needed_min = int(np.ceil(min(bounds))) 
    add_vehic_needed_max = int(np.ceil(max(bounds)))
    return add_vehic_needed_min, add_vehic_needed_max

def demandSplitting(stations, params):
    def duplicate(i, stations, selfSufficient):
        newIndex = len(stations.index)
        stations.loc[newIndex, 'Station ID']        = stations.loc[i, 'Station ID']
        stations.loc[newIndex, 'Longitude']         = stations.loc[i, 'Longitude']
        stations.loc[newIndex, 'Latitude']          = stations.loc[i, 'Latitude']
        stations.loc[newIndex, 'selfSufficient']    = selfSufficient
        return [newIndex]

    # form groups and split the demand
    params['groups'] = {}
    for i in stations.index:
        # record indices
        indices = [i]

        # determine the minimum and maximum of additional visits
        if params['splitDemand']:
            if i == params['start']:
                add_vehic_needed_min, add_vehic_needed_max = getVehicNeeded_start(i, stations, params)
            else:
                add_vehic_needed_min, add_vehic_needed_max = getVehicNeeded(i, stations, params)

            # add visits if needed
            if add_vehic_needed_max > 0:
                selfsuf_flags = [True] * (add_vehic_needed_max - add_vehic_needed_min) + [False] * add_vehic_needed_min
                for flag in selfsuf_flags:
                    indices += duplicate(i, stations, flag)

        # include the grouping of stations
        params['groups'][i] = indices
    
    if not params['openEnded']:
        # duplicate the depot
        start = params['start']
        lastAdded = params['groups'][start][-1]
        # depot duplicated now
        if lastAdded == start:
            params['groups'][start] += duplicate(start, stations, False)
            params['end'] = params['groups'][start][-1]
        # depot duplicated earlier
        else:
            stations.loc[lastAdded, 'selfSufficient'] = False
            params['end'] = lastAdded
    else:
        # open ended
        newIndex = len(stations.index)
        stations.loc[newIndex, 'Station ID']        = -2
        stations.loc[newIndex, 'selfSufficient']    = False
        params['end'] = newIndex

    # open started
    if params['start'] == None:
        newIndex = len(stations.index)
        stations.loc[newIndex, 'Station ID']        = -1
        stations.loc[newIndex, 'selfSufficient']    = False
        params['start'] = newIndex

    stations['Station ID'] = stations['Station ID'].astype(int)

def selectedEdges_to_path(selectedEdges, start=None):
    if start == None:
        start = 0
        
    path = np.array([start])

    count = 0
    while selectedEdges != []:
        for i, edge in enumerate(selectedEdges):
            if edge[0] == path[-1]:
                path = np.append(path, edge[1])
                del selectedEdges[i]
                break
        
        count += 1
        # If the while loop is endless, give up
        if count > 1e6:
            print('These were left out: ', selectedEdges)
            return None

    return path

def reversedGroups(groups):
    # dict to determine to which group a station belongs
    groups_reversed = {}
    for original, stations in groups.items():
        for station in stations:
            groups_reversed[station] = original

    return groups_reversed