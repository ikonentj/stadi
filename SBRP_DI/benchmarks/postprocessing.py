from SBRP_DI import fileOperations as fo
import pandas as pd
import matplotlib.pylab as plt

def loadResults(run, model):
    path = 'runs/run{}/'.format(run)
    results = {}
    for benchmark in fo.folders_in_dir(path + 'benchmarks/'):
        try:
            results[benchmark] = fo.loadJson(path + 'benchmarks/{}/{}/results_routing_0.json'.format(benchmark, model))
        except FileNotFoundError:
            pass

    data = pd.DataFrame(results).T
    data.index = data.index.str.replace('n', '')
    data.index = data.index.str[:-1] + 'q' + data.index.str[-1]
    data.index = pd.MultiIndex.from_tuples(list(data.index.str.split('q')),
                                      names=['n', 'q', 'letter'])
    data.reset_index(inplace=True)
    data['n'] = data['n'].astype(int)
    data['q'] = data['q'].astype(int)
    return data

def loadResults_multi(runs, deltas, model):
    sections = []

    for run, delta in zip(runs, deltas):
        # load the results
        path = '../run{}/benchmarks/'.format(run)
        dicts = {}
        for case in fo.folders_in_dir(path):
            dicts[case] = fo.loadJson(path + '{}/{}/results_routing_0.json'.format(case, model))

        # transform the results into a dataframe
        data = pd.DataFrame.from_dict(dicts, orient='index')[['ObjVal', 'ObjBound', 'Runtime', 'MIPGap']]
        data.columns = [col + '_{}'.format(delta) for col in data.columns]

        sections.append(data.copy())

    return pd.concat(sections, axis=1)

def loadReference(table):
    # load the data
    reference = pd.read_excel('../../../data/hernandez_perez04/N2005t3/tables_2_and_7_expanded.xls', sheet_name='Table{}'.format(table), skiprows=1)
    
    # preprocess
    if table == 2:
        reference.columns = [
             'Name',
             'ObjVal_1', 'Runtime_1',
             'ObjVal_2', 'Runtime_2'
             ]
        reference.dropna(subset=['Name'], inplace=True)
        reference['Name'] = reference['Name'].str.replace('.tsp', '')
    elif table == 7:
        reference.columns = [
                 'Name', 'n', 'Q', 
                 'ObjVal_1', 'ObjBound_1', 'Runtime_1', 'MIPGap_1',
                 'ObjVal_2', 'ObjBound_2', 'Runtime_2', 'MIPGap_2',
                 'ObjVal_3', 'ObjBound_3', 'Runtime_3', 'MIPGap_3',
                 'ObjVal_4', 'ObjBound_4', 'Runtime_4', 'MIPGap_4',
                 'ObjVal_5', 'ObjBound_5', 'Runtime_5', 'MIPGap_5'    
                 ]
    
    # reset index
    reference.set_index('Name', drop=True, inplace=True)
    
    return reference

def plot_ref_results_comparison(reference, results, case):
    scatter_props = {'s': 200, 'marker': '_', 'alpha': 0.5}
    for low, high in [(0, 40), (40, None)]:
        plt.figure(figsize=(16, 8))
        plt.scatter(range(40), reference['ObjVal_{}'.format(case)].values[low:high], c='tab:blue', **scatter_props, label='reference')
        if 'ObjBound_{}'.format(case) in reference.columns:
            plt.scatter(range(40), reference['ObjBound_{}'.format(case)].values[low:high], c='tab:blue', **scatter_props)
            plt.vlines(range(40), reference['ObjBound_{}'.format(case)].values[low:high], 
                                  reference['ObjVal_{}'.format(case)].values[low:high], alpha=0.5)
        
        plt.scatter(range(40), results['ObjVal_{}'.format(case)].values[low:high], c='tab:orange', **scatter_props, label='CHRM')
        plt.scatter(range(40), results['ObjBound_{}'.format(case)].values[low:high], c='tab:orange', **scatter_props)        
        plt.vlines(range(40), results['ObjBound_{}'.format(case)].values[low:high], 
                              results['ObjVal_{}'.format(case)].values[low:high], colors='tab:orange', alpha=0.5)        
        
        plt.xticks(range(40), reference.index[low:high], rotation='vertical')
        plt.xlim(-1, 40)
        plt.xlabel('case')
        plt.ylabel('cost [m]')
        plt.grid()
        plt.legend()

def detDiffs(reference, results, deltas):
    for case in deltas:
        results['diff_{}'.format(case)] = results['ObjVal_{}'.format(case)] - reference['ObjVal_{}'.format(case)]
        results['diff_rel_{}'.format(case)] = results['diff_{}'.format(case)] / reference['ObjVal_{}'.format(case)]
        if 'ObjBound_{}'.format(case) in reference.columns:
            results['diff_bound_{}'.format(case)] = results['ObjVal_{}'.format(case)] - reference['ObjBound_{}'.format(case)]
            results['diff_bound_rel_{}'.format(case)] = results['diff_bound_{}'.format(case)] / reference['ObjBound_{}'.format(case)]