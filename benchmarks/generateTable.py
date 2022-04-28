import SBRP_DI.benchmarks.postprocessing as post 
from argparse import ArgumentParser
import pandas as pd
import numpy as np

def defineParser():
    parser = ArgumentParser(description="The function generates a table of the results")
    parser.add_argument("run_ids", nargs='+', type=str, help="Run identifiers")
    parser.add_argument("model", type=str, help="The results of a model (hull_pm_general or sch17) to be included in the table")
    return parser

def main(args):
	quantities = ['MIPGap', 'Runtime']

	# collect the data into the table
	for i, run_id in enumerate(args.run_ids):

		data = post.loadResults(run_id, args.model)
		data_gb = data.groupby(['n', 'q'])

		# make sure that the experiment is finished
		assert (data_gb.count()['Runtime'].values == 10).all()
		
		# if the first, keep metadata
		if i == 0:
			table = data_gb.mean()[quantities]
			table.columns = [run_id + '_' + str(q) for q in table.columns]
		else:
			data_gb = data_gb.mean()[quantities]
			for quantity in quantities:
				table[run_id + '_' + quantity] = data_gb[quantity]

	# post process the table
	table.reset_index(inplace=True)
	table.index = ['n{}q{}'.format(n, q) for n, q in zip(table['n'], table['q'])] 
	table_ave = pd.concat([table, pd.DataFrame(table.mean(), columns=['average']).T])
	table_ave.loc['average', 'n'] = np.nan
	table_ave.loc['average', 'q'] = np.nan

	# mip gaps into percentage
	for column in table_ave.columns:
		if column.endswith('MIPGap'):
			table_ave[column] *= 100

	# print as a latex table
	print(table_ave.to_latex(float_format="%.2f"))

if __name__ == '__main__':
    parser = defineParser()
    args = parser.parse_args()
    main(args)