import numpy as np
import pandas as pd
from scipy.integrate import RK45
from . import tools
from tqdm import tqdm
from SBRP_DI.aux import isWithin, pairwise, dt_to_hours
from copy import deepcopy

class kolmogorovForward:
    def __init__(self, method):
        self.method = method           # 'forloop', 'matrix', 'schuijbroek'
        self.mu = None
        self.lamda = None

    def probs(self, t, p):
        assert self.mu != None and self.lamda != None
        
        func = getattr(self, self.method)
        return func(t, p)
        
    def forloop(self, t, p):
        # define the array
        p_dot = np.zeros(p.shape[0])
        
        # first element
        p_dot[0] = -self.lamda * p[0] + self.mu * p[1]
        
        # middle elements
        for i in range(1, p.shape[0]-1):
            p_dot[i] = self.lamda * p[i-1] - (self.mu + self.lamda) * p[i] + self.mu * p[i+1]  

        # last element
        C = p.shape[0] - 1
        p_dot[C] = self.lamda * p[C-1] - self.mu * p[C]
        
        return p_dot

    def matrix(self, t, p):
        # form matrix
        A = self.get_A(p)

        # matrix operation
        p_dot = np.matmul(p, A)

        return p_dot

    def get_A(self, p):
        # diag elements
        diag = np.ones(p.shape[0]) * -(self.mu + self.lamda)
        diag[0] = -self.lamda
        diag[-1] = -self.mu
        A = np.diag(diag)

        # diag plus one elements
        diag_p1 = np.ones(p.shape[0]-1) * self.lamda
        A += np.diag(diag_p1, 1)

        # diag minus one elements
        diag_m1 = np.ones(p.shape[0]-1) * self.mu
        A += np.diag(diag_m1, -1)

        return A
    
    def schuijbroek(self, t, p):
        # define the array
        p_dot = np.zeros(p.shape[0])
        
        # first element
        p_dot[0] = self.mu * p[1] - self.lamda * p[0]
        
        # middle elements
        for sigma in range(1, p.shape[0]-1):
            p_dot[sigma] = self.mu * p[sigma+1] - self.lamda * p[sigma-1]   
        
        # last element
        C = p.shape[0] - 1
        p_dot[C] = self.lamda * p[C-1] - self.mu * p[C] 

        return p_dot

def serviceLevelReq(stations, mu, lamda, props, includeBest=False):
    # auxiliary function
    def determineBest(station, capacity):
        slr_min = [min(
                    solver.serviceLevel('pickup', level, props['hour_start'], props['hour_end']),
                    solver.serviceLevel('return', level, props['hour_start'], props['hour_end'])
                            ) for level in range(capacity+1)]

        # return level where the worst slr is the best
        best = slr_min.index(max(slr_min))
        return best

    # looping over stations
    for station in tqdm(stations.index):
        rates = tools.extractRates(mu, lamda, station, props)
        capacity = stations.loc[station, '# of Docks']
        solver = numericalSolver(rates, capacity, props['interval'], kf_method='forloop')
        lb, ub = solver.get_bounds(props['beta_minus'], props['beta_plus'], props['hour_start'], props['hour_end'])
        if not None in [lb, ub] and lb <= ub: 
            stations.loc[station, 's_min'] = lb
            stations.loc[station, 's_max'] = ub
            if includeBest:
                stations.loc[station, 'best'] = determineBest(station, capacity)

        else:
            # determine first the worst of the service levels, for all possible levels 
            best = determineBest(station, capacity)
            stations.loc[station, 's_min'] = best
            stations.loc[station, 's_max'] = best
            if includeBest:
                stations.loc[station, 'best'] = best
            print('SLR cannot be fulfilled at station {}. \
                LB and UB set to the best possible value of {}/{}.'.format(station, best, capacity))

class numericalSolver:
    def __init__(self, rates, capacity, delta_t, kf_method='forloop'):
        self.rates = rates
        self.kf = kolmogorovForward(kf_method)
        self.capacity = capacity
        self.delta_t = delta_t

    def solve(self, diff_model):
        # collect data
        t_ = []
        y_ = []
        while diff_model.status != 'finished':
            # get solution step state
            diff_model.step()
            if t_ == [] or diff_model.t > t_[-1] + 1e-10:
                t_.append(diff_model.t)
                y_.append(diff_model.y)

        return np.array(t_), np.array(y_)

    def determine_probs(self, starting_level, time_start, time_end):
        # extract hours
        if not type(time_start) in [int, float]:
            hours_start = dt_to_hours(time_start)
            hours_end   = dt_to_hours(time_end)
            if hours_start >= hours_end:
                hours_end += 24
        else:
            hours_start, hours_end = time_start, time_end

        # pick the interval from rates
        rates = self.getRates(hours_start, hours_end)

        # in the begining, the level is known precisely
        starting_probs = np.zeros(self.capacity + 1)
        starting_probs[starting_level] = 1

        # collect data
        t_vals = np.array(hours_start)
        p_vals = np.array([starting_probs])

        for interval_start, interval_end in pairwise(rates.index):
            # define mu and lamda
            self.kf.mu = rates.loc[interval_start, 'mu']
            self.kf.lamda = rates.loc[interval_start, 'lamda']

            # integrate the interval
            diff_model = RK45(
                            self.kf.probs, 
                            interval_start, 
                            starting_probs, 
                            interval_end, 
                            max_step=self.delta_t, 
                            rtol=0.0001, 
                            #first_step=self.delta_t/10
                            first_step=None
                           )

            # save results
            t_vals_new, p_vals_new = self.solve(diff_model)
            t_vals = np.append(t_vals, t_vals_new)
            p_vals = np.concatenate((p_vals, p_vals_new), axis=0)

            # save state for the the next iteration 
            starting_probs = p_vals[-1,:]

        return t_vals, p_vals

    def getRates(self, time_start, time_end):
        # copy the rates
        rates = deepcopy(self.rates)

        # add start and end times if they are not in the index of rates
        for t_stamp in [time_start, time_end]:
            if not t_stamp in rates.index:
                rates.loc[t_stamp, :] = np.nan
        
        # forward-fill the values
        rates.sort_index(inplace=True)
        rates.ffill(inplace=True)
        rates.loc[rates.index[-1], :] = np.nan

        # return the requested range of rates
        return rates[(rates.index >= time_start) & (rates.index <= time_end)]

    def serviceLevel(self, direction, starting_level, time_start, time_end):
        # get p_vals and t_vals from determine_probs
        t_vals, p_vals = self.determine_probs(starting_level, time_start, time_end)

        # direction parameters
        if direction == 'pickup':
            rate = 'mu'
            sigma = 0
        elif direction == 'return':
            rate = 'lamda'
            sigma = self.capacity
        else:
            print('Direction is invalid... exiting.')
            return

        # pick the interval from rates
        rates = self.getRates(t_vals[0], t_vals[-1])

        nom = 0
        denom = 0
        for interval_start, interval_end in pairwise(rates.index):
            # identify the section from the t_vals
            mask = (t_vals >= interval_start) & (t_vals <= interval_end)
            
            # take the section from t_vals and p_vals
            p = p_vals[:,sigma][mask]
            t = t_vals[mask]
            
            # discretization
            p_ave = (p[:-1] + p[1:]) / 2
            dt = t[1:] - t[:-1]
            
            # addition to nominator and denominator
            nom += rates.loc[interval_start, rate] * np.dot(1 - p_ave, dt)
            denom += rates.loc[interval_start, rate] * (interval_end - interval_start)

        if denom == 0.:
            return 1
        else:
            return nom / denom

    def get_lowerBound(self, beta_minus, *args):
        s = 0
        while s <= self.capacity:
            g_0 = self.serviceLevel('pickup', s, *args)
            #print(s, g_0)
            if g_0 >= beta_minus:
                return s
            else:
                s += 1

    def get_upperBound(self, beta_plus, *args):
        s = self.capacity
        while s >= 0:
            g_C = self.serviceLevel('return', s, *args)
            #print(s, g_C)
            if g_C >= beta_plus:
                return s
            else:
                s -= 1
                
    def get_bounds(self, beta_minus, beta_plus, *args):
        return self.get_lowerBound(beta_minus, *args), self.get_upperBound(beta_plus, *args)
