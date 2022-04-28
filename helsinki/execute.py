from argparse import ArgumentParser
import pandas as pd
import json
from datetime import date
from tqdm import tqdm
from time import sleep

from SBRP_DI import tracker, optimizer, visualization, aux
from SBRP_DI import fileOperations as fo, convexHull as hull, schuijbroek17 as sch17

def defineParser():
    parser = ArgumentParser(description="The function executes a routing problem(s)")
    parser.add_argument("case_id", type=str, help="Case identifier")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("model", type=str, help="The model to be used in routing (hull_pm_general or sch17)")
    parser.add_argument("--limit", type=int, help="Maximum number of times")
    parser.add_argument("--log", action="store_true", help="Show the log output of the optimizers")
    parser.add_argument("--time", type=str, help="Specific time to be executed")
    parser.add_argument("-l", "--ord", type=int, help="The ordinal of the batch (used in HPC)")
    parser.add_argument("-b", "--batch", type=int, default=4, help="The batch size (used in HPC)")

    return parser

def main(args):
    # wait a bit to avoid parallel runs accessing the disk at the same time 
    if args.ord != None:
        sleep(0.2 * args.ord)

    # check if ord or time override exists, otherwise take all in the folder
    if args.ord != None:
        start = args.batch * args.ord
        end   = args.batch * (args.ord + 1)
        times = fo.folders_in_dir('cases/case{}/runs/run{}/times/'.format(args.case_id, args.run_id))[start:end]
    elif args.time in ['all', None]:
        times = fo.folders_in_dir('cases/case{}/runs/run{}/times/'.format(args.case_id, args.run_id))[:args.limit]
    else:
        times = [args.time]

    # loop over the times
    for time in tqdm(times):
        # path to run
        args.path_run = 'cases/case{}/runs/run{}/times/{}/'.format(args.case_id, args.run_id, time)

        # load params
        params = fo.loadJson(args.path_run + 'params.json')

        # load stations
        path_stations = 'cases/case{}/'.format(args.case_id)
        allStations = pd.read_csv(path_stations + 'stations.csv')

        # ensure that the results folder exists
        fo.makeFolder(args.path_run + '{}/'.format(args.model))

        # load snapshots
        file_name = date.fromisoformat(time.split(' ')[0]).strftime("%Y-%m")
        snapshots = fo.loadDF('snapshots/{}.csv'.format(file_name), time_to_index=True)

        sch17.analytics.fetchLevels(allStations, snapshots, params['time'], clip=True)

        # identify parameters
        allStations['s_plus'] = (allStations['s_min'] - allStations['level']).clip(0, None)
        allStations['s_minus'] = (allStations['level'] - allStations['s_max']).clip(0, None)
        sch17.tools.getSelfSufficients(allStations)

        # determine the vehicle locations
        if params['locations'] == 'randomize':
            aux.randomizeVehicleLocations(allStations, params)
        else:
            for i, loc in enumerate(params['locations']):
                mask = allStations['Station ID'] == loc
                allStations.loc[mask, 'vehicleLoc'] = i

        allStations[['Station ID', 'Station', 's_min', 's_max', 'level', 'selfSufficient']].to_csv(args.path_run + 'stations_details.csv', index=False)

        # filter the self-sufficient stations
        stations = aux.pickStations(allStations, params).copy()
        stations.reset_index(inplace=True, drop=True)

        # solve the routing problem
        tr = optimizer.runRouting(stations, params, args)
        selfsuf = allStations[allStations['selfSufficient']]
        visualization.makePlots(tr, selfsuf, stations, params, args)

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()
    main(args)