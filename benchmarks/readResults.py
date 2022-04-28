import SBRP_DI.benchmarks.postprocessing as post 
from argparse import ArgumentParser

def defineParser():
    parser = ArgumentParser(description="The function fetches the results")
    parser.add_argument("run_id", type=str, help="Run identifier")
    parser.add_argument("model", type=str, help="The model used in routing (hull_pm_general or sch17")
    return parser

def main(args):
	data = post.loadResults(args.run_id, args.model)

	print('---------------------------------------------------------------------------------')
	print(data.groupby(['n', 'q']).mean())
	print()
	print(data.groupby(['n', 'q']).count()['Runtime'])
	print()
	print('Total average runtime: {}'.format(data.mean()['Runtime']))
	print('---------------------------------------------------------------------------------')


if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    main(args)