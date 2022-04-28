import pandas as pd
from SBRP_DI import fileOperations as fo, visualization, aux, convexHull as hull
from SBRP_DI.benchmarks import postprocessing as post, preprocessing as pre 
import matplotlib.pylab as plt
from argparse import ArgumentParser

def defineParser():
    parser = ArgumentParser(description="The function verifies benchmark problem(s) solved by hull_pm_general")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("benchmark_id", type=str, help="Benchmark identifier. 'all' verifies all problems in the run." )
    parser.add_argument("--plot", action="store_true", help="Make a plot of the verification (included in the folder of the benchmark).")

    return parser

def main(args, benchmark_id):
    # load benchmark
    df, capacity = pre.readCase(benchmark_id)
    params = fo.loadJson('runs/run{}/info.json'.format(args.run_id))['params']
    params["Q"] = capacity
    pre.setBounds(df, params['bikeDelta'])
    for i, loc in enumerate(params['locations']):
        mask = df['Station ID'] == loc
        df.loc[mask, 'vehicleLoc'] = i
    params['start'] = aux.findStart(df)
    hull.tools.demandSplitting(df, params)

    # load operations
    op = pd.read_csv('runs/run{}/benchmarks/{}/{}/operations_0.csv'.format(args.run_id, benchmark_id, args.model), index_col=0)

    # determine objective function value
    route = op.sort_values(by='ord').index.values
    dmatrix = aux.getDmatrix(df, units='meters', rounding=params['D_matrix_rounding'])
    ObjVal = 0
    for sour, dest in aux.pairwise(route):
        ObjVal += dmatrix.loc[sour, dest]

    # determine loading
    load = op.sort_values(by='ord')['load']
    loading = -load.diff()
    loading.loc[params['start']] = params['q_0'][0] - load.loc[params['start']]
    loading = loading.reindex(df.index, fill_value=0)

    # map the loading to stations
    loading_grouped = pd.Series({j: sum([loading.loc[i] for i in params['groups'][j]]) for j in params['groups'].keys()})

    # drop levels of duplicated stations
    df.dropna(subset=['level'], inplace=True)

    # plot levels before and after rebalancing
    if args.plot:
        visualization.setFont(16)
        plt.figure(figsize=(16, 8))
        plt.hlines([df['s_min'].iloc[0], df['s_max'].iloc[0]], 1, df.shape[0], colors='k', alpha=0.5)
        plt.scatter(df['Station ID'], df['level'], c='tab:blue', alpha=0.5, label='before rebalancing')
        plt.scatter(df['Station ID'], df['level'] + loading_grouped, marker='x', s=100, c='tab:orange', alpha=0.5, 
                                                                    label='after rebalancing')
        plt.legend()
        plt.xlabel('Station ID')
        plt.ylabel('number of bikes [-]')
        plt.xlim(0, None)
        plt.grid()
        plt.savefig('runs/run{}/benchmarks/{}/{}/levels.pdf'.format(args.run_id, benchmark_id, args.model))

    ### verifications ###
    # check that capacity is not violated
    tol = 1e-4
    assert load.min() >= -tol
    assert load.min() <= capacity + tol

    # the cost of the path matches that reported
    assert aux.isWithin(ObjVal, fo.loadJson('runs/run{}/benchmarks/{}/{}/results_routing_0.json'.format(args.run_id, benchmark_id, args.model))['ObjVal'])

    # demand is met
    assert (df['level'] + loading_grouped >= df['s_min'] - tol).all()
    assert (df['level'] + loading_grouped <= df['s_max'] + tol).all()

    # bikes do not flow through the depot
    if not params['openEnded']:
        assert load.loc[params['start']] <= df.loc[params['start'], 'level'] + tol

    # bikes do not dissappear or appear
    load_at_last_station = load.loc[params['end']]
    assert -loading_grouped.sum() >= load_at_last_station - tol
    assert -loading_grouped.sum() <= load_at_last_station + tol

    print('{}: Verification completed.'.format(benchmark_id))

if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    args.model = 'hull_pm_general'
    if args.benchmark_id == 'all':
        for benchmark_id in fo.folders_in_dir('runs/run{}/benchmarks/'.format(args.run_id)):
            main(args, benchmark_id)
    else:
        main(args, args.benchmark_id)