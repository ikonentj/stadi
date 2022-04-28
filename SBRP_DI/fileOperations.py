import os, json, shutil
import pandas as pd

def makeFolder(path):
    if not os.path.isdir(path):
        os.mkdir(path)

def loadJson(path):
    with open(path, 'r') as f:
        obj = json.load(f)
    return obj

def saveJson(path, obj):
    with open(path, 'w') as f:
        json.dump(obj, f, indent=4)

def loadDF(path, time_to_index=False):
    df = pd.read_csv(path)
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        if time_to_index:
            df.set_index('time', inplace=True)

    return df

def folders_in_dir(path):
    return [folder for folder in sorted(os.listdir(path)) if os.path.isdir(path + folder)]

def files_in_dir(path):
    return [file for file in sorted(os.listdir(path)) if not os.path.isdir(path + file)]

def loadTrips(start, end, city):
	# define the months to be loaded
    months = pd.date_range(start, end, freq='MS', closed='left').strftime("%Y-%m").tolist()
    if months == []:
    	months = [pd.to_datetime(start).strftime("%Y-%m")]
    
	# load the files
    if city.lower() == 'espoo':
        city = 'helsinki'
    dfs = []
    for month in months:
        dfs.append(pd.read_csv('../data/{}/trips/{}.csv'.format(city.lower(), month))) 
    
    # joint them together
    trips = pd.concat(dfs)
    print('Loaded trips from months: {}'.format(months))

    return trips

def loadResults(path):
    # load the result data
    results_dict = {}
    i = 0

    print('Result not found:')
    for run in folders_in_dir(path + 'runs/'):
        for day in folders_in_dir(path + 'runs/{}/days/'.format(run)):
            try:
                results_dict[i] = {'run': int(run.replace('run', '')), 'day': day}
                results_dict[i].update(loadJson(path + 'runs/{}/days/{}/result.json'.format(run, day)))
            except FileNotFoundError:
                print('{},{}'.format(run.replace('run', ''), day))
                pass
            i += 1

    # put results into a dataframe
    df = pd.DataFrame(results_dict).T
    for column in df.columns:
        if column.startswith('hours') or column == 'totalDistance':
            df[column] = df[column].astype(float)

    results = df.dropna().groupby('run').mean()
    n = df.dropna().groupby('run').count()['hours_total']

    # load the result data
    params_dict = {}
    i = 0
    for run in folders_in_dir(path + 'runs/'):
        params_dict[i] = {'run': int(run.replace('run', ''))}
        params_dict[i].update(loadJson(path + 'runs/{}/parameters.json'.format(run))['params'])
        i += 1

    # put parameters into a dataframe
    params = pd.DataFrame(params_dict).T
    params.set_index('run', inplace=True)
    params.sort_index(inplace=True)

    # merge the dataframes
    data = pd.concat([results, params[['slr', 'beta', 'horizon', 'reschInterval', 'slr_trigger', 'infillIter']].astype(float)], axis=1)
    data['n'] = n.fillna(0)
    
    return data

def fetchSolverMetrics(path):
    # unpack the zip files
    for day in folders_in_dir(path + 'days/'):
        shutil.unpack_archive(path + 'days/{}/sch17.zip'.format(day), 
                              path + 'days/{}/sch17'.format(day), 'zip')

    # make a dataframe of the results files
    results_dict = {}
    notFound = 0
    for day in folders_in_dir(path + 'days/'):
        try:
            for file in files_in_dir(path + 'days/{}/sch17/'.format(day)):
                if file.startswith('results'):
                    results_dict[file] = loadJson(path + 'days/{}/sch17/{}'.format(day, file))
        except FileNotFoundError:
            notFound += 1

    # put results into a dataframe
    df = pd.DataFrame(results_dict).T
    for column in df.columns:
        if column == 'Status':
            df[column] = df[column].astype(int)
        else:
            df[column] = df[column].astype(float)

    # determine the solver metrics
    solverMetrics = {}
    solverMetrics['mean'] = dict(df.drop(columns=['Status']).mean())
    solverMetrics['status'] = {k: int(v) for k, v in dict(df['Status'].value_counts()).items()}
    solverMetrics['notFound'] = notFound

    # save the metrics
    saveJson(path + '/solverMetrics.json', solverMetrics)

    # delete the unpacked folder
    for day in folders_in_dir(path + 'days/'):
        try:
            shutil.rmtree(path + 'days/{}/sch17'.format(day))
        except:
            pass
