from SBRP_DI import fileOperations as fo, aux
from SBRP_DI.benchmarks import preprocessing as pre
from argparse import ArgumentParser

def defineParser():
    parser = ArgumentParser(description="The function sets up a folder evaluating benchmarks")
    parser.add_argument("run_id", type=str, help="Run identifier")
    return parser

def main(args):
    path = 'runs/run{}/'.format(args.run_id)

    # record git commit
    aux.recordGitCommit(path)

    # load all benchmarks
    allBenchmarks = [item.replace('.tsp', '') for item in fo.files_in_dir('../data/hernandez_perez07/N2005t3/instances') 
                  if not 'mos' in item and not '1000' in item and not '100' in item]

    # choose the right benchmarks based on desired problem sizes
    problemSizes = fo.loadJson(path + 'info.json')['problemSizes']
    benchmarks = []
    for size in problemSizes:
        benchmarks += [item for item in allBenchmarks if item.startswith('n{}'.format(str(size)))]

    # make the folders
    fo.makeFolder(path)
    fo.makeFolder(path + 'benchmarks/')
    for benchmark in benchmarks:
        fo.makeFolder(path + 'benchmarks/{}/'.format(benchmark))

    # make the scripts
    params = fo.loadJson(path + 'info.json')['params']
    pre.makeScript(args.run_id, params)

if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    main(args)