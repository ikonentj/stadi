from argparse import ArgumentParser
import pandas as pd
import numpy as np

def defineParser():
    parser = ArgumentParser(description="The function preprocesses snapshot data from a certaion year.")
    parser.add_argument("year", type=str, help="Year")
    return parser

if __name__ == "__main__":
    parser = defineParser()
    args = parser.parse_args()

    # read snapshot data
    snapshots = pd.read_csv('snapshots/data_{}.csv'.format(args.year), 
        sep=';', usecols=['id', 'time', 'bikesAvailable'])

    # exclude snapshots from Vantaa (Vantaa's OD data is not available)
    snapshots = snapshots[snapshots.id < 1000]

    # preprocessing
    snapshots['time'] = pd.to_datetime(snapshots['time'])
    snapshots.sort_values(by='time', inplace=True)
    snapshots.set_index('time', inplace=True)
    snapshots.rename(columns={"id": "Station ID"}, inplace=True)

    # save the snapshots
    snapshots.to_csv('snapshots/data_{}_pre.csv'.format(args.year))