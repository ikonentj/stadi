import gurobipy as gp
from gurobipy import GRB, quicksum
from itertools import product

def routing(params):
    # init the model
    m = gp.Model()

    # sets
    V = [i for i, _ in enumerate(params['q_0'])]
    S = list(range(params['n']))
    N = list(range(params['n'] + 1))
    T = list(range(params['n'] + params['sch17_extra_timeSlots']))

    # variables
    x           = m.addVars(product(S,N,T,V), vtype=GRB.BINARY, name='x')
    y_m         = m.addVars(product(S,T,V), lb=0, ub=params['Q'], vtype=GRB.CONTINUOUS, name='y_m')
    y_p         = m.addVars(product(S,T,V), lb=0, ub=params['Q'], vtype=GRB.CONTINUOUS, name='y_p')
    h           = m.addVars(V, lb=0, vtype=GRB.CONTINUOUS, name='h')
    H           = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name='H')

    # constraints
    m.addConstrs((params['s_0'][i] + quicksum(y_p[i, t, v] - y_m[i, t, v] for t in T for v in V) >= params['s_min'][i] for i in S), name='eq1')
    m.addConstrs((params['s_0'][i] + quicksum(y_p[i, t, v] - y_m[i, t, v] for t in T for v in V) <= params['s_max'][i] for i in S), name='eq2')

    m.addConstrs((x.sum('*', '*', 0, v) <= 1 for v in V), name='eq3')
    m.addConstrs((x.sum(i, '*', t, v) <= x.sum('*', i, t-1, v) for i in S for t in T[1:] for v in V), name='eq4')
    m.addConstr(quicksum(x[i, i, t, v] for i in S for t in T for v in V) == 0, name='eq5')

    m.addConstrs((y_m[i, t, v] <= params['Q'] * x.sum(i, '*', t, v) for i in S for t in T for v in V), name='eq6')

    assert params['sch17_eq7'] in ['original', 'modified'] 
    if params['sch17_eq7'] == 'original':
        # Capacity constraint can be violated (?) 
        m.addConstrs((y_p[i, t, v] <= params['Q'] * x.sum('*', i, t, v)
                      for i in S for t in T for v in V), name='eq7')
    elif params['sch17_eq7'] == 'modified':
        m.addConstrs((y_p[i, t, v] <= params['Q'] * x.sum(i, '*', t, v)
                      for i in S for t in T for v in V), name='eq7')

    m.addConstrs((y_m.sum(i, '*', '*') <= params['s_0'][i] for i in S), name='eq8')
    m.addConstrs((y_p.sum(i, '*', '*') <= params['C'][i] - params['s_0'][i] for i in S), name='eq9')

    assert params['sch17_eq10_11'] in ['original', 'modified'] 
    if params['sch17_eq10_11'] == 'original':
        m.addConstrs((params['q_0'][v] + quicksum(y_m[i, t, v] - y_p[i, t, v] for i in S for t in T[t_tilde:]) >= 0 
                                                                                        for t_tilde in T for v in V), name='eq10')
        m.addConstrs((params['q_0'][v] + quicksum(y_m[i, t, v] - y_p[i, t, v] for i in S for t in T[t_tilde:]) <= params['Q']
                                                                                        for t_tilde in T for v in V), name='eq11')
    elif params['sch17_eq10_11'] == 'modified':
        m.addConstrs((params['q_0'][v] + quicksum(y_m[i, t_tilde, v] - y_p[i, t_tilde, v] for i in S for t_tilde in range(t+1)) >= 0 
                                                                                        for t in T for v in V), name='eq10')
        m.addConstrs((params['q_0'][v] + quicksum(y_m[i, t_tilde, v] - y_p[i, t_tilde, v] for i in S for t_tilde in range(t+1)) <= params['Q']
                                                                                        for t in T for v in V), name='eq11')

    m.addConstrs((h[v] == quicksum(params['dist'][i][j] * x[i, j, t, v] for i in S for j in S for t in T)
                  + params['d_m'] * y_m.sum('*', '*', v)
                  + params['d_p'] * y_p.sum('*', '*', v)
                  for v in V), name='eq12')

    if 'h_0' in params:
      m.addConstrs((H >= h[v] + params['h_0'][v] for v in V), name='eq13')
    else:
      m.addConstrs((H >= h[v] for v in V), name='eq13')

    # add initial locations
    if params['start'] != None:
        m.addConstrs((x.sum(params['start'], '*', 0, v) == 1 for v in V), name='eq_initLocations')

    # a station can be visited only once
    if params['sch17_limitVisits']:
        m.addConstrs((x.sum(i, '*', '*', v) <= params['max_visits'][i] for i in S for v in V), name='eq_limitVisits1')
        m.addConstrs((x.sum('*', j, '*', v) <= params['max_visits'][j] for j in S for v in V), name='eq_limitVisits2')

    m.setObjective(H, GRB.MINIMIZE);

    m._x = x
    m._y_m = y_m
    m._y_p = y_p
    m._params = params
    
    return m

def clustering(params):
    # init the model
    m = gp.Model()

    # sets 
    S = params['S']
    S0 = params['S0']
    V = list(range(params['n_vehicles']))

    # parameters
    Q = params['Q']

    # variables
    z = m.addVars(product(S,V), vtype=GRB.BINARY, name='z')
    h = m.addVars(V, lb=0, vtype=GRB.CONTINUOUS, name='h')
    H = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name='H')

    # constraints
    m.addConstrs((z.sum(i, '*') == 1 for i in S if i not in S0), name='eq14')
    m.addConstrs((z.sum(i, '*') <= 1 for i in S0), name='eq15')
    m.addConstrs((params['q_0'][v] + quicksum(params['s_0'][i] * z[i,v] for i in S) 
              >= quicksum(params['s_min'][i] * z[i,v] for i in S) 
              for v in V), name='eq16')
    m.addConstrs((-(Q - params['q_0'][v]) + quicksum(params['s_0'][i] * z[i,v] for i in S) 
              <= quicksum(params['s_max'][i] * z[i,v] for i in S)
              for v in V), name='eq17')

    m.addConstrs((h[v] >= quicksum(params['dist'][i][j] * (z[i,v] + z[j,v] - 1) for j in S) 
              + quicksum((params['d_p'] * params['s_plus'][j] + params['d_m'] * params['s_minus'][j]) * z[j,v] for j in S)
              for i in S for v in V), name='eq18')
    m.addConstrs((h[v] >= quicksum(params['dist'][i][j] * (z[i,v] + z[j,v] - 1) for j in S) 
              + quicksum((params['d_p'] * params['s_plus'][j] + params['d_m'] * params['s_plus'][j]) * z[j,v] for j in S)
              - params['d_m'] * params['q_0'][v]
              for i in S for v in V), name='eq19')
    m.addConstrs((h[v] >= quicksum(params['dist'][i][j] * (z[i,v] + z[j,v] - 1) for j in S) 
              + quicksum((params['d_p'] * params['s_minus'][j] + params['d_m'] * params['s_minus'][j]) * z[j,v] for j in S)
              - params['d_p'] * (Q - params['q_0'][v])
              for i in S for v in V), name='eq20')

    if 'h_0' in params:
      m.addConstrs((H >= h[v] + params['h_0'][v] for v in V), name='eq21')
    else:
      m.addConstrs((H >= h[v] for v in V), name='eq21')

    # add initial locations
    if params['locations_ord'][0] != None:
        m.addConstrs((z[params['locations_ord'][v],v] == 1 for v in V), name='eq_initLocations')

    m._z = z
    m._h = h
    m._H = H

    # objective
    m.setObjective(H, GRB.MINIMIZE)

    return m