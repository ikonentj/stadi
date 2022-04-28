from argparse import ArgumentParser
import pandas as pd
import numpy as np
import json, os
from datetime import date

from SBRP_DI import visualization, aux, fileOperations as fo
from SBRP_DI.caseStudies import postprocessing as pp

def defineParser():
    parser = ArgumentParser(description="The function makes tables of the runtimes")
    parser.add_argument("case_id", type=str, help="Case identifier")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("--models", type=str, nargs='+', default=[], help="Methods to be included in the tables")

    return parser

def showRuntimes(path, args):
    # load the params
    params = fo.loadJson(path+'params.json')
    print(path.split('/')[-2])

    # define models
    if args.models == []:
        models = fo.folders_in_dir(path)
    else:
        models = args.models

    # fetch routing run times
    runtimes_routing = pd.DataFrame()
    for model in models:
        for i in range(len(params['q_0'])):
            try:
                results = fo.loadJson(path + '{}/results_routing_{}.json'.format(model, i))
                runtimes_routing.loc[i, model] = results['Runtime']
            except FileNotFoundError:
                runtimes_routing.loc[i, model] = np.nan

        # determine the sums
        try:
            runtimes_routing.loc['sum', model] = runtimes_routing[model].sum()
        except KeyError:
            pass

    # add problem sizes
    if params['clustering']:
        try:	
            clustering = pd.read_csv(path + 'clustering.csv')
            problem_sizes = clustering.vehicle.value_counts()
            problem_sizes.loc['sum'] = problem_sizes.sum()
            runtimes_routing['# of stations'] = problem_sizes.astype(int)
        except FileNotFoundError:
            print("Didn't find clustering results. Exiting.")

    if params['clustering']:
        for model in models:
            try:
                runtime_clustering = fo.loadJson(path + '{}/results_clustering.json'.format(model))['Runtime']
                print('Clustering time:', round(runtime_clustering, 6))
                break
            except FileNotFoundError:
                pass
    print(runtimes_routing)
    print()

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()

    # list paths to runs
    path_times = 'cases/case{}/runs/run{}/times/'.format(args.case_id, args.run_id)
    times = fo.folders_in_dir(path_times)[:args.limit]
    paths = [path_times + time + '/' for time in times]

    # verify the results
    for path in paths:
        pp.verifyResults(path)

    for path in paths:
        showRuntimes(path, args)
