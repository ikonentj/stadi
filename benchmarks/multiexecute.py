from SBRP_DI import fileOperations as fo
from argparse import ArgumentParser
import execute
import time

from string import ascii_uppercase

def defineParser():
    parser = ArgumentParser(description="The function sets up a folder evaluating benchmarks")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("model", type=str, help="The model to be used in routing (hull_pm_general or sch17)")
    parser.add_argument("-l", "--letter_ord", type=int, help="The ordinal of the letter to be run (used in HPC)")
    parser.add_argument("-r", "--reverse", action="store_true", help="Starts from the cases with the largest Q")
    parser.add_argument("--log", action="store_true", help="Show the log output of the optimizers")
    return parser

def main(args):
    path = 'runs/run{}/'.format(args.run_id)

    # pick the benchmarks
    if args.letter_ord != None:
        time.sleep(0.2 * args.letter_ord)
    benchmarks = fo.files_in_dir(path + 'benchmarks')
    if args.letter_ord != None:
        benchmarks = [bench for bench in benchmarks if bench.endswith(ascii_uppercase[args.letter_ord])]
    if args.reverse:
        benchmarks = reversed(benchmarks)

    # excute the benchmarks
    for benchmark in benchmarks:
        try:
            if 'results_routing_0.json' in fo.files_in_dir(path + 'benchmarks/{}/{}/'.format(benchmark, args.model)):
                continue
        except FileNotFoundError:
            pass
        print(benchmark)
        args.benchmark_id = benchmark
        execute.main(args)

if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    main(args)
