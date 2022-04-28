import pandas as pd
import gurobipy as gp
import os, time
from datetime import date
from copy import deepcopy
from multiprocessing import Pool
from itertools import starmap

import SBRP_DI.schuijbroek17 as sch17
import SBRP_DI.convexHull as hull
from SBRP_DI import tracker
from SBRP_DI import visualization, aux, fileOperations as fo


def routing(subset, params_routing, args, i, save):
    # determine the vehicle specific params
    params_routing['q_0']   = [params_routing['q_0'][i]]

    while True:
        # define the model
        if args.model.startswith('hull'):
            hull.tools.params_from_stations(subset, params_routing)
            model = getattr(hull.models, args.model)
            m = model(params_routing)
        elif args.model == 'sch17':
            sch17.tools.params_from_stations(subset, params_routing)
            m = sch17.models.routing(params_routing)

        # if the model has only one station, return without performing an optimization
        if params_routing['n'] <= 1:
            sol = {'type': 'oneStation', 'q_0': params_routing['q_0']}
            return sol

        # model settings
        if params_routing['parallelRouting']:
            m.Params.Threads = params_routing['threads'] // len(params_routing['q_0'])
        else:
            m.Params.Threads = params_routing['threads']
        m.Params.LogToConsole = int(args.log)

        # specification of the log file
        fileName = args.path_run + '{}/log_routing_{}.dat'.format(args.model, i)
        if save:
            if os.path.isfile(fileName):
                os.remove(fileName)
            m.Params.LogFile = fileName

        # define the time limit
        m.Params.TimeLimit = params_routing['timeRemaining']

        # run the optimization
        if args.model.startswith('hull'):
            m.optimize(hull.separations.addCuts)
        else:
            m.optimize()
        params_routing['timeRemaining'] -= m.Runtime

        # if the schuijbroek17 is infeasible, increment the number of the time slots
        if args.model == 'sch17' and m.Status == 3:
            params_routing['sch17_extra_timeSlots'] += 1
            print('Adding a time slot. Now {} additional slots.'.format(params_routing['sch17_extra_timeSlots']))
            if params_routing['sch17_extra_timeSlots'] == 50:
                sol = {'type': 'noSolution', 'q_0': params_routing['q_0']}
                return sol
        else:
            break

    # save routing results
    if save:
        aux.getResults(m, path=args.path_run + '{}/results_routing_{}.json'.format(args.model, i))
       
    # else, try to fetch the solution
    try:
        sol = tracker.model2dict(m, args.model)
        sol['type'] = 'optimized'
    except (AttributeError, gp.GurobiError):
        sol = {'type': 'noSolution', 'q_0': params_routing['q_0']}

    return sol

def runRouting(stations, params, args, save=True):
    # identify if setting 'loop' is required (to be removed at some point)
    loop = args.model == 'hull_pm_loop'

    # init the computing budget
    params['timeRemaining'] = params['timeLimit']

    # run clustering if necessary
    if params['clustering']:
        tr = tracker.tracker(stations, args.model.split('_')[0])
        if not tr.clusteringFound(args.path_run):
            sch17.tools.params_from_stations(stations, params, model='clustering')
            c = sch17.models.clustering(params)
            c.Params.Threads = params['threads']
            c.Params.LogToConsole = int(args.log)
            c.Params.TimeLimit = params['timeLimit'] * params['clustTimeFrac']
            if save:
                c.Params.LogFile = args.path_run + '{}/log_clustering.dat'.format(args.model)
            c.optimize()
            params['timeRemaining'] -= c.Runtime
            fo.saveJson(args.path_run + 'clusteringTime.json', c.Runtime)
            tr.importClustering(c)

            # save clustering results
            if save:
                tr.saveClustering(args.path_run)
                aux.getResults(c, path=args.path_run + '{}/results_clustering.json'.format(args.model))
        else:
            params['timeRemaining'] -= fo.loadJson(args.path_run + 'clusteringTime.json')

    else:
        tr = tracker.tracker(stations, args.model.split('_')[0], singleVehic=True)
    
    # allocate stations to vehicles and split demand
    subsets = [stations[tr.assignment['vehicle']==i].copy() for i, _ in enumerate(params['q_0'])]
    params_subsets = {}
    for i, subset in enumerate(subsets):
        subset.reset_index(inplace=True, drop=True)
        params_subsets[i] = deepcopy(params)
        params_subsets[i]['start'] = aux.findStart(subset)
        if args.model == 'hull_pm_general':
            hull.tools.demandSplitting(subset, params_subsets[i])
        elif args.model == 'sch17':
            sch17.tools.extra_timeSlots(subset, params_subsets[i])
        subset['vehicle'] = i

    # save the duplicated stations
    if args.model == 'hull_pm_general':
        for i, subset in enumerate(subsets):
            subset.to_csv(args.path_run + '{}/stations_duplicated_{}.csv'.format(args.model, i), index=True)

    # create tasks
    tasks = [(subsets[i], params_subsets[i], args, i, save) for i, q_0 in enumerate(params['q_0'])]

    # run the routing
    if params['parallelRouting']:
        with Pool(len(params['q_0'])) as pool:
            sols = pool.starmap(routing, tasks)
    else:
        sols = starmap(routing, tasks)

    # collect the operations from the solutions
    for i, sol in enumerate(sols):    
        tr.importOperations(sol, i, subsets[i])

    # drop stations that were not visited from operations
    tr.dropNotVisited()

    return tr