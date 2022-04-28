import pandas as pd
import matplotlib.pylab as plt
import numpy as np

def makeScript(run_id, params):
    # write the doe script
    with open('scripts/execute.sh', 'r') as f:
        file = f.read()
    
    file_edited = file.replace('<<<ID>>>', str(run_id)).replace('<<<N_CPU>>>', str(params['threads']))
    
    with open('bashexecute_{}.sh'.format(run_id), 'w') as f:
        f.write(file_edited)

    print('If you are on a HPC, remember to mark the model to the slurm script: bashexecute_{}.sh.'.format(run_id))

def readCase(name, rel_path=''):
    # aux function
    def getValues(rows):
        data = {}
        for row in rows:
            key, *values = row.split()
            if len(values) == 1:
                data[int(key)] = int(values[0])
            else:
                data[int(key)] = [float(ele) for ele in values]
        return data
    
    # open the file
    with open(rel_path + '../data/hernandez_perez07/N2005t3/instances/{}.tsp'.format(name), 'r') as f:
        lines = f.read().split('\n')
        
    # read the data from the file
    for i, line in enumerate(lines):
        if line.startswith('DIMENSION'):
            dimension = int(''.join(filter(lambda x: x.isdigit(), line)))
        elif line.startswith('CAPACITY'):
            capacity = int(''.join(filter(lambda x: x.isdigit(), line)))
        elif line.startswith('NODE_COORD_SECTION'):
            locations = getValues(lines[i+1:i+1+dimension])
        elif line.startswith('DEMAND_SECTION'):
            demand = getValues(lines[i+1:i+1+dimension])
            break
    
    # put the data into a dataframe
    df = pd.DataFrame([[key] + locations[key] for key in range(1, dimension+1)])
    df.columns = ['Station ID', 'Longitude', 'Latitude']
    df.set_index('Station ID', inplace=True)
    df['demand'] = pd.DataFrame.from_dict(demand, orient='index')
    df.reset_index(inplace=True)
    df['Station ID'] = df['Station ID'].astype(int)
    return df, capacity

def setBounds(df, interval):
    # bounds
    df['s_min'] = -df.demand.min()
    df['s_max'] = df['s_min'] + interval
    
    # level
    for i in df.index:
        if df.loc[i, 'demand'] > 0:
            df.loc[i, 'level'] = df.loc[i, 'demand'] + df.loc[i, 's_max']
        elif df.loc[i, 'demand'] < 0:
            df.loc[i, 'level'] = df.loc[i, 's_min'] + df.loc[i, 'demand']
        elif df.loc[i, 'demand'] == 0:
            df.loc[i, 'level'] = np.floor((df.loc[i, 's_max'] + df.loc[i, 's_min']) / 2)
            
    df.level = df.level.astype(int)