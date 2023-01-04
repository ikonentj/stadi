import gurobipy as gp
from gurobipy import GRB, quicksum
from itertools import product
from SBRP_DI.aux import powerset, pairwise
import numpy as np

def excl(array, ind):
    return array[:ind] + array[ind+1:]

def hull_pm_general(params):
    # init the model
    m = gp.Model()

    # sets and parameters
    init_load = params['q_0'][0]
    start     = params['start']
    end       = params['end']
    Q         = params['Q']

    D     = list(range(params['n']))
    S0    = params['S0']

    D1           = [s for s in D if s != end]
    D2           = [s for s in D if s != start]
    D1_cap_D2    = [s for s in D if s != start and s != end]
    D_excl_ss    = [s for s in D if s not in params['S0']]
    D1_excl_ss   = [s for s in D if s != end and s not in params['S0']]
    D2_excl_ss   = [s for s in D if s != start and s not in params['S0']]

    S0_multi = [k for k in S0 if k in params['groups'].keys() and len(params['groups'][k]) >= 2]

    # variables
    x = m.addVars(product(D1,D2), vtype=GRB.BINARY, name='x')
    z = m.addVars(S0_multi, vtype=GRB.BINARY, name='z')
    if params['hull_var_y']:
        y = m.addVars(S0, vtype=GRB.BINARY, name='y')

    theta_lbs = [max(0, -params['demand_max'][j])  if j in params['groups'].keys() and len(params['groups'][j]) == 1 else 0 for j in D]
    theta_ubs = [min(Q, Q-params['demand_min'][j]) if j in params['groups'].keys() and len(params['groups'][j]) == 1 else Q for j in D]
    if params['locations'][0] != None and params['openEnded'] == False:
        theta_ubs[start] = min(init_load+params['level'][start], Q)
    theta = m.addVars(D, lb=theta_lbs, ub=theta_ubs, vtype=GRB.INTEGER, name='theta')
    theta_bar = m.addVars(product(D1,D2), lb=0, ub=[ub for _ in D1 for ub in excl(theta_ubs,start)], vtype=GRB.CONTINUOUS, name='theta_bar')
    theta_hat = m.addVars(product(D1,D2), lb=0, ub=[ub for ub in excl(theta_ubs,end) for _ in D2], vtype=GRB.CONTINUOUS, name='theta_hat')

    delta_p_lbs = [max(0, params['demand_min'][j]) if j in params['groups'].keys() and len(params['groups'][j]) == 1 else 0 for j in D]
    delta_p_ubs = [max(0, params['demand_max'][j]) if j in params['groups'].keys() and len(params['groups'][j]) == 1 else Q for j in D]
    delta_p_ubs[start] = min(delta_p_ubs[start], init_load)
    delta_p = m.addVars(D, lb=delta_p_lbs, ub=delta_p_ubs, vtype=GRB.INTEGER, name='delta_p')
    delta_p_sub = m.addVars(product(D1,D2), lb=0, ub=[ub for _ in D1 for ub in excl(delta_p_ubs,start)], vtype=GRB.CONTINUOUS, name='delta_p_sub')

    delta_m_lbs = [max(0, -params['demand_max'][j]) if j in params['groups'].keys() and len(params['groups'][j]) == 1 else 0 for j in D]
    delta_m_ubs = [max(0, -params['demand_min'][j]) if j in params['groups'].keys() and len(params['groups'][j]) == 1 else Q for j in D]
    if params['locations'][0] != None and params['openEnded'] == False:
        delta_m_ubs[start] = min(params['level'][start], Q)
    delta_m = m.addVars(D, lb=delta_m_lbs, ub=delta_m_ubs, vtype=GRB.INTEGER, name='delta_m')
    delta_m_sub = m.addVars(product(D1,D2), lb=0, ub=[ub for _ in D1 for ub in excl(delta_m_ubs,start)], vtype=GRB.CONTINUOUS, name='delta_m_sub')

    # bounds
    for i in D1_cap_D2:
        x[i,i].ub = 0

    # forbid temporary operations, if demand splitting is used
    for i in params['S+']:
        if i == start and not params['openEnded'] and not params['splitDemand']:
            continue
        for k in params['groups'][i]:
            delta_m[k].ub = 0

    for i in params['S-']:
        if i == start and not params['openEnded'] and not params['splitDemand']:
            continue
        for k in params['groups'][i]:
            delta_p[k].ub = 0

    # prevent (un)loading at artificial start/end stations
    if params['locations'][0] == None:
        delta_p[start].ub = 0
        delta_m[start].ub = 0

    if params['openEnded']:
        delta_p[end].ub = 0
        delta_m[end].ub = 0

    # within_group_archs_forbidden
    for vals in params['groups'].values():
        for i in vals:
            for j in vals:
                if i != end and j != start and i != j:
                    x[i,j].ub = 0

    # objective
    m.setObjective(quicksum(params['dist'][i][j] * x[i,j] for i in D1 for j in D2) 
        + params['d_p'] * delta_p.sum('*') 
        + params['d_m'] * delta_m.sum('*'), GRB.MINIMIZE)

    # constraints
    # initial load
    m.addConstr(delta_p[start] - delta_m[start] == init_load - theta[start],                        name='initial_load')

    # demand
    m.addConstrs((params['demand_min'][j] <= quicksum(delta_p[i] - delta_m[i] for i in params['groups'][j]) for j in params['groups'].keys()), name='demand_min')
    m.addConstrs((params['demand_max'][j] >= quicksum(delta_p[i] - delta_m[i] for i in params['groups'][j]) for j in params['groups'].keys()), name='demand_max')

    # routing
    m.addConstrs((x.sum('*',j) == 1 for j in D2_excl_ss),                                           name='arrival_to_compul_station')
    m.addConstrs((x.sum(i,'*') == 1 for i in D1_excl_ss),                                           name='departure_from_compul_station')
    if params['hull_var_y']:
        m.addConstrs((x.sum('*',j) == y[j] for j in S0),                                            name='arrival_to_opt_station')
        m.addConstrs((x.sum(i,'*') == y[i] for i in S0),                                            name='departure_from_opt_station')
    else:
        m.addConstrs((x.sum('*',j) <= 1 for j in S0),                                               name='arrival_to_opt_station')
        m.addConstrs((x.sum('*',j) == x.sum(j, '*') for j in S0),                                   name='departure_from_opt_station')
    m.addConstrs((x[i,j] + x[j,i] <= 1 for i in D1_cap_D2 for j in D1_cap_D2 if i != j),            name='no_cycles_two_stations')
    
    # big-M reformulation
    m.addConstrs((delta_m[i] <= Q * z[k]                      for k in S0_multi for i in params['groups'][k]),  name='source_or_sink_1')
    m.addConstrs((delta_p[i] <= Q * (1 - z[k])                for k in S0_multi for i in params['groups'][k]),  name='source_or_sink_2')
    
    # hull reformulation: aggregated
    m.addConstrs((theta[i] == theta_hat.sum(i, '*')           for i in D1),                             name='aggr_theta_i')
    m.addConstrs((theta[j] == theta_bar.sum('*',j)            for j in D2),                             name='aggr_theta_j')
    m.addConstrs((delta_p[j] == delta_p_sub.sum('*',j)        for j in D2),                             name='aggr_delta_p')
    m.addConstrs((delta_m[j] == delta_m_sub.sum('*',j)        for j in D2),                             name='aggr_delta_m')
    
    # hull reformulation: equations
    m.addConstrs((theta_hat[i,j] - theta_bar[i,j] == delta_p_sub[i,j] - delta_m_sub[i,j] for i in D1 for j in D2), name='chr_equation')
    
    # hull reformulation: bounds
    m.addConstrs((delta_p_sub[i,j] >= delta_p_lbs[j] * x[i,j] for i in D1 for j in D2),                 name='delta_p_bound_min')
    m.addConstrs((delta_p_sub[i,j] <= delta_p_ubs[j] * x[i,j] for i in D1 for j in D2),                 name='delta_p_bound_max')

    m.addConstrs((delta_m_sub[i,j] >= delta_m_lbs[j] * x[i,j] for i in D1 for j in D2),                 name='delta_m_bound_min')
    m.addConstrs((delta_m_sub[i,j] <= delta_m_ubs[j] * x[i,j] for i in D1 for j in D2),                 name='delta_m_bound_max')
    
    m.addConstrs((theta_hat[i,j] >= theta_lbs[i] * x[i,j]     for i in D1 for j in D2),                 name='theta_hat_bound_min')
    m.addConstrs((theta_hat[i,j] <= theta_ubs[i] * x[i,j]     for i in D1 for j in D2),                 name='theta_hat_bound_max')

    m.addConstrs((theta_bar[i,j] >= theta_lbs[j] * x[i,j]     for i in D1 for j in D2),                 name='theta_bar_bound_min')
    m.addConstrs((theta_bar[i,j] <= theta_ubs[j] * x[i,j]     for i in D1 for j in D2),                 name='theta_bar_bound_max')

    # settings
    m._x = x
    m._theta = theta
    m._theta_bar = theta_bar
    m._theta_hat = theta_hat
    m._delta_p = delta_p
    m._delta_m = delta_m
    m._delta_p_sub = delta_p_sub
    m._delta_m_sub = delta_m_sub
    m._start      = start
    m._D          = D
    m._S0         = S0
    m._D1         = D1
    m._D1_excl_ss = D1_excl_ss
    m._D2         = D2
    m._D2_excl_ss = D2_excl_ss
    m._params = params
    m.Params.lazyConstraints = 1

    # separations
    m._separations = [1]

    return m