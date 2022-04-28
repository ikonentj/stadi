from gurobipy import GRB, quicksum
from graph_tool.all import *
from . import tools

def define_aux_graph(x_vals, params):
    aux_graph = Graph()
    cap = aux_graph.new_ep("double")
    edges = {k: min(v, 10) for k, v in x_vals.items() if v > 1e-5}

    aux_graph.add_vertex(params['n'])
    edge_list = [(start, end, c) for (start, end), c in edges.items()]
    aux_graph.add_edge_list(edge_list, eprops=[cap])

    return aux_graph, cap

def addCuts(model, where):
    # make a list of edges selected in the solution
    if where in [GRB.Callback.MIPNODE]:
        pass

    if where in [GRB.Callback.MIPSOL]:
        if where == GRB.Callback.MIPSOL:
            x_vals = model.cbGetSolution(model._x)

        # define the auxiliary graph
        aux_graph, cap = define_aux_graph(x_vals, model._params)

        # separations
        if 1 in model._separations:
            separation_1(model, aux_graph, x_vals, cap)

def separation_1(model, aux_graph, x_vals, cap):
    flow = aux_graph.new_ep("double")
    src = aux_graph.vertex(model._start)
    for s in model._D2_excl_ss:
        tgt = aux_graph.vertex(s)
        #res = edmonds_karp_max_flow(aux_graph, src, tgt, cap)
        #res = push_relabel_max_flow(aux_graph, src, tgt, cap)
        res = boykov_kolmogorov_max_flow(aux_graph, src, tgt, cap)
        flow.a = cap.a - res.a
        max_flow = sum(flow[e] for e in tgt.in_edges())
        
        if max_flow < 1.0 - 1e-5:
            part = min_st_cut(aux_graph, src, cap, res)
            P = [aux_graph.vertex_index[q] for q in find_vertex(aux_graph, part, 0) 
                    if q == tgt or q.in_degree()+q.out_degree()>0]
            if len(P) >= 2:
                D1_excl_P = [i for i in model._D1 if not i in P]
                model.cbLazy(quicksum(model._x[i, j] for i in D1_excl_P for j in P) >= 1)
                return