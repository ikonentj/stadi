import SBRP_DI.convexHull as hull
import numpy as np
import pandas as pd
import gurobipy as gp

def model2dict(m, modelName):

    sol = {}
    sol['x_vals'] = dict(m.getAttr('x', m._x))
    if modelName.startswith('hull'):
        sol['start'] = m._start
        sol['x_vals']        = dict(m.getAttr('x', m._x))
        sol['theta_vals']    = dict(m.getAttr('x', m._theta))
    else:
        sol['y_m_vals']      = dict(m.getAttr('x', m._y_m))
        sol['y_p_vals']      = dict(m.getAttr('x', m._y_p))
        sol['q_0']           = m._params['q_0']

    return sol

class tracker:
    def __init__(self, stations, model, singleVehic=False):
        assert model in ['hull', 'sch17']

        # initialize the tracker
        self.model = model
        self.op = {}
        self.assignment = stations[['Station ID', 'Station', 'vehicleLoc']].copy()

        # assign a single vehicle
        if singleVehic:
            self.assignment['vehicle'] = 0

    def importOperations(self, sol, vehicle_id, subset):
        if self.model == 'hull':
            self.import_from_hull(sol, vehicle_id, subset)
        elif self.model == 'sch17':
            self.import_from_sch17(sol, vehicle_id, subset)

    def importClustering(self, m):
        # import the assignment
        try:
            vals = m.getAttr('x', m._z)
            z_arr = np.array([[i, v] for (i, v), val in vals.items() if val > 0.5])
        except (AttributeError, gp.GurobiError):
            self.op['vehicle'] = self.op['vehicleLoc']
            print('Clustering was infeasible. Moving on.')
            return

        self.assignment['vehicle'] = np.nan
        for vehicle_id in np.unique(z_arr[:, 1]):
            station_ids = z_arr[z_arr[:,1]==vehicle_id][:,0]
            self.assignment.loc[station_ids, 'vehicle'] = vehicle_id

    def import_from_hull(self, sol, vehicle_id, subset):
        # move data from subset to op per vehicle
        self.op[vehicle_id] = subset[['Station ID', 'Station', 'Longitude', 'Latitude', 'vehicleLoc', 'vehicle']].copy()

        if sol['type'] == 'optimized':
            # determine the path with station subset indices
            selected = [edge for edge, val in  sol['x_vals'].items() if val > 0.5]
            path_subset = hull.tools.selectedEdges_to_path(selected, start=sol['start'])

            # determine the loads
            theta_vals = [(k, v) for k, v in sol['theta_vals'].items()]
            theta_vals_sorted = sorted(theta_vals, key=lambda x: x[0])
            theta = np.array(theta_vals_sorted)

            # determine operations with station subset indices
            load = theta[path_subset][:,1]

            # determine maps
            ord_map = {key: val for val, key in enumerate(path_subset)}
            load_map = {key: val for key, val in zip(path_subset, load)}

            # save to the operations
            self.op[vehicle_id].loc[:, 'ord'] = self.op[vehicle_id].index.map(ord_map)
            self.op[vehicle_id].loc[:, 'load'] = self.op[vehicle_id].index.map(load_map)

        elif sol['type'] == 'oneStation':
            self.op[vehicle_id].loc[:, 'ord'] = 0
            self.op[vehicle_id].loc[:, 'load'] = sol['q_0']

        elif sol['type'] == 'noSolution':
            self.op[vehicle_id] = pd.DataFrame(columns=['Station ID', 'Longitude', 'Latitude', 'ord', 'load'])

    def import_from_sch17(self, sol, vehicle_id, subset):
        if sol['type'] == 'optimized':
            # Obtain the loading of the vehicles
            y_m_nonZero = [(i, t, v, val) for (i, t, v), val in sol['y_m_vals'].items() if val > 0.5]
            y_p_nonZero = [(i, t, v, val) for (i, t, v), val in sol['y_p_vals'].items() if val > 0.5]
                
            # the above two lines could also be written as
            edges = [(i, j, t) for (i, j, t, veh), val in sol['x_vals'].items() if val > 0.5]
            edges.sort(key=(lambda x: x[2]))
            path_subset = [edge[0] for edge in edges] 
            
            # add the last station if it is not artificial
            last = edges[-1][1]
            if last <= subset.index[-1]:
                path_subset += [last]

            # extraxct the loads from vars
            y_m = {i:  val for i, t, veh, val in y_m_nonZero}
            y_p = {i: -val for i, t, veh, val in y_p_nonZero}

            # fill those that are missing by 0
            for i in path_subset:
                if not i in y_p:
                    y_p[i] = 0
                if not i in y_m:
                    y_m[i] = 0

            # cumsum for pickup/dropoff
            pickup_dropoff = np.array([y_m[i] + y_p[i] for i in path_subset])
            load = np.cumsum(pickup_dropoff) + sol['q_0'][0]
            
            self.op[vehicle_id] = pd.concat([subset.loc[i,:] for i in path_subset], axis=1).T.reset_index(drop=True)
            self.op[vehicle_id]['ord'] = range(self.op[vehicle_id].shape[0])
            self.op[vehicle_id].loc[1:,'vehicleLoc'] = np.nan
            self.op[vehicle_id]['load'] = load

        elif sol['type'] == 'oneStation':
            mask = self.op['vehicle'] == vehicle_id
            self.op[vehicle_id].loc[:, 'ord'] = 0
            self.op[vehicle_id].loc[:, 'load'] = sol['q_0']

        elif sol['type'] == 'noSolution':
            self.op[vehicle_id] = pd.DataFrame(columns=['Station ID', 'Longitude', 'Latitude', 'ord', 'load'])

    def saveOperations(self, path):
        for v in self.op.keys():
            self.op[v].to_csv(path + 'operations_{}.csv'.format(v), index=True)

    def saveClustering(self, path):
        self.assignment[['Station ID', 'Station', 'vehicle']].to_csv(path + 'clustering.csv', index=False)

    def clusteringFound(self, path):
        try:
            clust = pd.read_csv(path + 'clustering.csv')
            self.assignment['vehicle'] = clust['vehicle']
            return True
        except FileNotFoundError:
            return False

    def dropNotVisited(self):
        for v in self.op.keys():
            self.op[v].dropna(subset=['ord'], inplace=True)

    def dropArtificials(self):
        for v in self.op.keys():
            self.op[v].dropna(subset=['Longitude', 'Latitude'], inplace=True)