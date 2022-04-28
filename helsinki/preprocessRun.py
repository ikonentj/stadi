from argparse import ArgumentParser
import os, sys
import pandas as pd
import numpy as np
from copy import deepcopy
from SBRP_DI import aux, fileOperations as fo
from SBRP_DI.caseStudies import preprocessing as pre


def defineParser():
    parser = ArgumentParser(description="The function preprocesses a run folder")
    parser.add_argument("case_id", type=str, help="Case identifier")
    parser.add_argument("run_id", type=str, help="Run identifier")
    return parser

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()

    # load props
    path_props = 'cases/case{}/'.format(args.case_id)
    props = fo.loadJson(path_props + 'props.json')

    # load parameters
    path_parameters = 'cases/case{}/runs/run{}/'.format(args.case_id, args.run_id)
    parameters = fo.loadJson(path_parameters + 'parameters.json')

    parameters['weekdaysOnly'] = props['weekdaysOnly']

    # record git commit
    aux.recordGitCommit(path_parameters)

    # loop over the times in the time range
    times = pd.date_range(parameters['time_start'], parameters['time_end'], freq='d')

    # filter weekends
    if props['weekdaysOnly']:
        times = times[times.weekday<=4]

    # add the starting hour
    times += pd.Timedelta(props['hour_level'], unit='h')
    
    # lists of times
    times_short = times.strftime("%Y-%m-%d").tolist()
    times_long = times.strftime("%Y-%m-%d %H:00:00").tolist()

    # ensure that the times folder exists
    fo.makeFolder(path_parameters + 'times/')

    # make the batch the script file
    n_batches = int(np.ceil(len(times_short) / 4))
    pre.makeScript(args, parameters['params'], n_batches)

    for t_short, t_long in zip(times_short, times_long):
        # create params
        params = deepcopy(parameters['params'])
        params['time'] = t_long

        # determine the path for params
        path_params = path_parameters + 'times/' + t_short + '/'

        # ensure that the folder exists
        fo.makeFolder(path_params)

        # save the params to the folder
        fo.saveJson(path_params + 'params.json', params)