from argparse import ArgumentParser
import sys, os, json

import pandas as pd
import numpy as np
from SBRP_DI.schuijbroek17 import visu, algorithms, tools, analytics
from SBRP_DI import aux, fileOperations as fo

def defineParser():
    parser = ArgumentParser(description="The function fetches snapshots for a given range of months")
    parser.add_argument("window_start", type=str, help="Start month of the range in format yyyy-mm")
    parser.add_argument("window_end", type=str, help="End month of the range in format yyyy-mm")
    return parser

def extractYears(months):
    years = np.unique([month.split('-')[0] for month in months])
    return years 

def loadSnapshots_annual(years):
    dfs = []
    for year in years:
        df = fo.loadDF('../data/helsinki/snapshots/data_{}_pre.csv'.format(year), time_to_index=True)
        dfs.append(df)

    return pd.concat(dfs)

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()

    # month range
    months = pd.date_range(args.window_start, args.window_end, freq='MS').strftime("%Y-%m").tolist()
    
    # load data
    years = extractYears(months)
    snapshots = loadSnapshots_annual(years)

    # pick the desired snapshots from the data and save to a separate file
    fo.makeFolder('snapshots')
    for start, end in aux.pairwise(months):
        snapshots[start:end].to_csv('snapshots/{}.csv'.format(start))

    print('Fetched snapshots from the following months:')
    print(months[:-1])

