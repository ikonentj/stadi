from itertools import combinations
from SBRP_DI import visualization, aux, fileOperations as fo
import pandas as pd
import numpy as np

def verifyResults(path):
    # load the params
    n_vehicles = len(fo.loadJson(path+'params.json')['q_0'])

    # make the verifications
    successful = True
    for i in range(n_vehicles):
        models = {}
        # load models and check that the runs are complete
        for m_name in fo.folders_in_dir(path):
            try:
                models[m_name] = fo.loadJson(path + '{}/results_routing_{}.json'.format(m_name, i))
                if models[m_name]['Status'] != 2 or models[m_name]['MIPGap'] > 1.e-4:
                    print('{}/{}/, vehicle {}: Incomplete run.'.format(path, m_name, i))
                    successful = False
            except FileNotFoundError:
                print('{}/{}/, vehicle {}: No solution.'.format(path, m_name, i))
                models[m_name] = {'ObjVal': None} 
                successful = False

        # check pairwise that the models have the same objective function value
        for key1, key2 in combinations(models.keys(), 2):
            if models[key1]['ObjVal'] == None or models[key2]['ObjVal'] == None or not aux.isWithin(models[key1]['ObjVal'], models[key2]['ObjVal'], 4):
                print('{}, vehicle {}, models {} and {}: Objective value mismatch.'.format(path, i, key1, key2))
                successful = False

    if successful:
        print('{}: verified {} runs.'.format(path, n_vehicles))

def loadData(model, path_root='times/', res_type='routing'):
    # load the results in to dicts
    times = fo.folders_in_dir(path_root)
    results_dict = {}
    for time in times:
        path = path_root + '{}/{}/'.format(time, model)
        for file in fo.files_in_dir(path):
            if file.startswith('results_{}'.format(res_type)):
                if res_type == 'routing':
                    i = int(''.join(filter(lambda x: x.isdigit(), file)))
                else:
                    i = 0
                results_dict[time,i]  = fo.loadJson(path + file)
    
    # put dicts into a dataframe and split the index
    df = pd.DataFrame.from_dict(results_dict, orient='index')
    df['time'] = df.index.get_level_values(0)
    df['sub'] = df.index.get_level_values(1)
    return df.reset_index(drop=True)

def count_no_solution(df):
    try:
        return df['ObjVal'].value_counts()[np.inf]
    except KeyError:
        return 0

def dropinf(df, inplace=False):
    return df.replace([np.inf, -np.inf], np.nan).dropna(subset=['ObjVal'], inplace=inplace)

def difference(model1, model2):
    differences = (model2.ObjVal - model1.ObjVal) / model1.ObjVal * 100
    return differences

def initTable(clustering_gb_max=None, family=None, S=None, S_S0=None):
    # init the table
    table = pd.DataFrame([family, S, S_S0]).T
    table.columns = ['family', 'S', 'S_S0']
    
    # add clustering results if they are given    
    if clustering_gb_max != None:
        table.loc[0, 'clustering_gap'] = clustering_gb_max.mean()['MIPGap'] * 100
        table.loc[0, 'clustering_time'] = clustering_gb_max.mean()['Runtime']

    return table

def rowToTable(table, gb_maxs, names, gb_max_ref=None, row=0, latex=False):
    if type(gb_max_ref) == type(None):
        gb_max_ref = gb_maxs[0]

    # import data
    for i, (gb_max, name) in enumerate(zip(gb_maxs, names)):
        table.loc[row, '{}_gap'.format(name)] = round(gb_max.mean()['MIPGap'] * 100, 2)
        table.loc[row, '{}_time'.format(name)] = round(gb_max.mean()['Runtime'], 1)
        if i >= 1:
            table.loc[row, '{}_rel_diff'.format(name)] = round(difference(gb_max_ref, gb_maxs[i]).mean(skipna=False), 2)

    if latex:
        print(table.to_latex(index=False))
    else:
        return table

def load_S_S0(root='times/'):
    S_S0_list = []
    times = fo.folders_in_dir(root)
    for time in times:
        stations = pd.read_csv(root + '{}/stations_details.csv'.format(time))
        S_S0_list.append(stations[~stations.selfSufficient].shape[0])
    
    return pd.Series(S_S0_list, index=times)