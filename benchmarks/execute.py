import pandas as pd
import matplotlib.pylab as plt
import numpy as np
import SBRP_DI.benchmarks.preprocessing as pre

from argparse import ArgumentParser
from SBRP_DI import tracker, visualization, aux, fileOperations as fo, schuijbroek17 as sch17, convexHull as hull, optimizer

def defineParser():
    parser = ArgumentParser(description="The function executes a routing problem")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("benchmark_id", type=str, help="Benchmark identifier")
    parser.add_argument("model", type=str, help="The model to be used in routing (hull_pm_general or sch17)")
    parser.add_argument("--log", action="store_true", help="Show the log output of the optimizers")

    return parser

def main(args):
    # load case and params
    path_lobby = 'runs/run{}/'.format(args.run_id)
    args.path_run = 'runs/run{}/benchmarks/{}/'.format(args.run_id, args.benchmark_id)
    stations, capacity = pre.readCase(args.benchmark_id)
    params = fo.loadJson(path_lobby + 'info.json')['params']
    params["Q"] = capacity

    # elaborate stations
    pre.setBounds(stations, params['bikeDelta'])
    sch17.tools.getSelfSufficients(stations)
    stations['Station'] = np.nan
    for i, loc in enumerate(params['locations']):
        mask = stations['Station ID'] == loc
        stations.loc[mask, 'vehicleLoc'] = i
    stations['# of Docks'] = stations[['level', 's_max']].max(axis=1)

    # ensure that the results folder exists
    fo.makeFolder(args.path_run + '{}/'.format(args.model))

    # solve the routing problem
    tr = optimizer.runRouting(stations, params, args)

    # save the results
    selfsuf = stations[stations['selfSufficient']]
    visualization.makePlots(tr, selfsuf, stations, params, args)

if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    main(args)