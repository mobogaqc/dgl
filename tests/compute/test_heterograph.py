
import dgl
import dgl.function as fn
from collections import Counter
import numpy as np
import scipy.sparse as ssp
import itertools
import backend as F
import networkx as nx

def create_test_heterograph():
    # test heterograph from the docstring, plus a user -- wishes -- game relation
    mg = nx.MultiDiGraph([
        ('user', 'user', 'follows'),
        ('user', 'game', 'plays'),
        ('user', 'game', 'wishes'),
        ('developer', 'game', 'develops')])

    plays_spmat = ssp.coo_matrix(([1, 1, 1, 1], ([0, 1, 2, 1], [0, 0, 1, 1])))
    g = dgl.DGLHeteroGraph((mg, {
        ('user', 'follows', 'user'): [(0, 1), (1, 2)],
        ('user', 'plays', 'game'): plays_spmat,
        ('user', 'wishes', 'game'): [(0, 1), (2, 0)],
        ('developer', 'develops', 'game'): [(0, 0), (1, 1)],
        }))

    return g

def test_query():
    g = create_test_heterograph()

    ntypes = ['user', 'game', 'developer']
    etypes = [
        ('user', 'follows', 'user'),
        ('user', 'plays', 'game'),
        ('user', 'wishes', 'game'),
        ('developer', 'develops', 'game')]
    edges = {
        ('user', 'follows', 'user'): ([0, 1], [1, 2]),
        ('user', 'plays', 'game'): ([0, 1, 1, 2], [0, 0, 1, 1]),
        ('user', 'wishes', 'game'): ([0, 2], [1, 0]),
        ('developer', 'develops', 'game'): ([0, 1], [0, 1]),
        }
    # edges that does not exist in the graph
    negative_edges = {
        ('user', 'follows', 'user'): ([0, 1], [0, 1]),
        ('user', 'plays', 'game'): ([0, 2], [1, 0]),
        ('user', 'wishes', 'game'): ([0, 1], [0, 1]),
        ('developer', 'develops', 'game'): ([0, 1], [1, 0]),
        }

    # node & edge types
    assert set(ntypes) == set(g.all_node_types)
    assert set(etypes) == set(g.all_edge_types)

    # metagraph
    mg = g.metagraph
    assert set(g.all_node_types) == set(mg.nodes)
    etype_triplets = [(u, v, e) for u, v, e in mg.edges(keys=True)]
    assert set([
        ('user', 'user', 'follows'),
        ('user', 'game', 'plays'),
        ('user', 'game', 'wishes'),
        ('developer', 'game', 'develops')]) == set(etype_triplets)

    # number of nodes
    assert [g.number_of_nodes(ntype) for ntype in ntypes] == [3, 2, 2]

    # number of edges
    assert [g.number_of_edges(etype) for etype in etypes] == [2, 4, 2, 2]

    # has_node & has_nodes
    for ntype in ntypes:
        n = g.number_of_nodes(ntype)
        for i in range(n):
            assert g.has_node(ntype, i)
        assert not g.has_node(ntype, n)
        assert np.array_equal(
            F.asnumpy(g.has_nodes(ntype, [0, n])).astype('int32'), [1, 0])

    for etype in etypes:
        srcs, dsts = edges[etype]
        for src, dst in zip(srcs, dsts):
            assert g.has_edge_between(etype, src, dst)
        assert F.asnumpy(g.has_edges_between(etype, srcs, dsts)).all()

        srcs, dsts = negative_edges[etype]
        for src, dst in zip(srcs, dsts):
            assert not g.has_edge_between(etype, src, dst)
        assert not F.asnumpy(g.has_edges_between(etype, srcs, dsts)).any()

        srcs, dsts = edges[etype]
        n_edges = len(srcs)

        # predecessors & in_edges & in_degree
        pred = [s for s, d in zip(srcs, dsts) if d == 0]
        assert set(F.asnumpy(g.predecessors(etype, 0)).tolist()) == set(pred)
        u, v = g.in_edges(etype, [0])
        assert F.asnumpy(v).tolist() == [0] * len(pred)
        assert set(F.asnumpy(u).tolist()) == set(pred)
        assert g.in_degree(etype, 0) == len(pred)

        # successors & out_edges & out_degree
        succ = [d for s, d in zip(srcs, dsts) if s == 0]
        assert set(F.asnumpy(g.successors(etype, 0)).tolist()) == set(succ)
        u, v = g.out_edges(etype, [0])
        assert F.asnumpy(u).tolist() == [0] * len(succ)
        assert set(F.asnumpy(v).tolist()) == set(succ)
        assert g.out_degree(etype, 0) == len(succ)

        # edge_id & edge_ids
        for i, (src, dst) in enumerate(zip(srcs, dsts)):
            assert g.edge_id(etype, src, dst) == i
            assert F.asnumpy(g.edge_id(etype, src, dst, force_multi=True)).tolist() == [i]
        assert F.asnumpy(g.edge_ids(etype, srcs, dsts)).tolist() == list(range(n_edges))
        u, v, e = g.edge_ids(etype, srcs, dsts, force_multi=True)
        assert F.asnumpy(u).tolist() == srcs
        assert F.asnumpy(v).tolist() == dsts
        assert F.asnumpy(e).tolist() == list(range(n_edges))

        # find_edges
        u, v = g.find_edges(etype, list(range(n_edges)))
        assert F.asnumpy(u).tolist() == srcs
        assert F.asnumpy(v).tolist() == dsts

        # all_edges.  edges are already in srcdst order
        for order in ['srcdst', 'eid']:
            u, v, e = g.all_edges(etype, 'all', order)
            assert F.asnumpy(u).tolist() == srcs
            assert F.asnumpy(v).tolist() == dsts
            assert F.asnumpy(e).tolist() == list(range(n_edges))

        # in_degrees & out_degrees
        in_degrees = F.asnumpy(g.in_degrees(etype))
        out_degrees = F.asnumpy(g.out_degrees(etype))
        src_count = Counter(srcs)
        dst_count = Counter(dsts)
        utype, _, vtype = etype
        for i in range(g.number_of_nodes(utype)):
            assert out_degrees[i] == src_count[i]
        for i in range(g.number_of_nodes(vtype)):
            assert in_degrees[i] == dst_count[i]

def test_frame():
    g = create_test_heterograph()

    f1 = F.randn((3, 6))
    g.ndata['user']['h'] = f1       # ok
    f2 = g.ndata['user']['h']
    assert F.array_equal(f1, f2)
    assert F.array_equal(g.nodes['user'][0].data['h'], f1[0:1])

    f3 = F.randn((2, 4))
    g.edata['user', 'follows', 'user']['h'] = f3
    f4 = g.edata['user', 'follows', 'user']['h']
    assert F.array_equal(f3, f4)
    assert F.array_equal(g.edges['user', 'follows', 'user'][0].data['h'], f3[0:1])

def test_apply():
    def node_udf(nodes):
        return {'h': nodes.data['h'] * 2}
    def edge_udf(edges):
        return {'h': edges.data['h'] * 2 + edges.src['h']}

    g = create_test_heterograph()
    g.ndata['user']['h'] = F.ones((3, 5))
    g.apply_nodes({'user': node_udf})
    assert F.array_equal(g.ndata['user']['h'], F.ones((3, 5)) * 2)

    g.edata['user', 'plays', 'game']['h'] = F.ones((4, 5))
    g.apply_edges({('user', 'plays', 'game'): edge_udf})
    assert F.array_equal(g.edata['user', 'plays', 'game']['h'], F.ones((4, 5)) * 4)

def test_updates():
    def msg_func(edges):
        return {'m': edges.src['h']}
    def reduce_func(nodes):
        return {'y': F.sum(nodes.mailbox['m'], 1)}
    def apply_func(nodes):
        return {'y': nodes.data['y'] * 2}
    g = create_test_heterograph()
    x = F.randn((3, 5))
    g.ndata['user']['h'] = x

    for msg, red, apply in itertools.product(
            [fn.copy_u('h', 'm'), msg_func], [fn.sum('m', 'y'), reduce_func],
            [None, apply_func]):
        multiplier = 1 if apply is None else 2

        g['user', 'plays', 'game'].update_all(msg, red, apply)
        y = g.ndata['game']['y']
        assert F.array_equal(y[0], (x[0] + x[1]) * multiplier)
        assert F.array_equal(y[1], (x[1] + x[2]) * multiplier)
        del g.ndata['game']['y']

        g['user', 'plays', 'game'].send_and_recv(([0, 1, 2], [0, 1, 1]), msg, red, apply)
        y = g.ndata['game']['y']
        assert F.array_equal(y[0], x[0] * multiplier)
        assert F.array_equal(y[1], (x[1] + x[2]) * multiplier)
        del g.ndata['game']['y']

        g['user', 'plays', 'game'].send(([0, 1, 2], [0, 1, 1]), msg)
        g['user', 'plays', 'game'].recv([0, 1], red, apply)
        y = g.ndata['game']['y']
        assert F.array_equal(y[0], x[0] * multiplier)
        assert F.array_equal(y[1], (x[1] + x[2]) * multiplier)
        del g.ndata['game']['y']

        # pulls from destination (game) node 0
        g['user', 'plays', 'game'].pull(0, msg, red, apply)
        y = g.ndata['game']['y']
        assert F.array_equal(y[0], (x[0] + x[1]) * multiplier)
        del g.ndata['game']['y']

        # pushes from source (user) node 0
        g['user', 'plays', 'game'].push(0, msg, red, apply)
        y = g.ndata['game']['y']
        assert F.array_equal(y[0], x[0] * multiplier)
        del g.ndata['game']['y']

if __name__ == '__main__':
    test_query()
    test_frame()
    test_apply()
    test_updates()
