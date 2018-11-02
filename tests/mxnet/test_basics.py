import os
os.environ['DGLBACKEND'] = 'mxnet'
import mxnet as mx
import numpy as np
from dgl.graph import DGLGraph

D = 5
reduce_msg_shapes = set()

def check_eq(a, b):
    assert a.shape == b.shape
    assert mx.nd.sum(a == b).asnumpy() == int(np.prod(list(a.shape)))

def message_func(edges):
    assert len(edges.src['h'].shape) == 2
    assert edges.src['h'].shape[1] == D
    return {'m' : edges.src['h']}

def reduce_func(nodes):
    msgs = nodes.mailbox['m']
    reduce_msg_shapes.add(tuple(msgs.shape))
    assert len(msgs.shape) == 3
    assert msgs.shape[2] == D
    return {'m' : mx.nd.sum(msgs, 1)}

def apply_node_func(nodes):
    return {'h' : nodes.data['h'] + nodes.data['m']}

def generate_graph(grad=False):
    g = DGLGraph()
    g.add_nodes(10) # 10 nodes.
    # create a graph where 0 is the source and 9 is the sink
    for i in range(1, 9):
        g.add_edge(0, i)
        g.add_edge(i, 9)
    # add a back flow from 9 to 0
    g.add_edge(9, 0)
    ncol = mx.nd.random.normal(shape=(10, D))
    if grad:
        ncol.attach_grad()
    g.ndata['h'] = ncol
    return g

def test_batch_setter_getter():
    def _pfc(x):
        return list(x.asnumpy()[:,0])
    g = generate_graph()
    # set all nodes
    g.set_n_repr({'h' : mx.nd.zeros((10, D))})
    assert _pfc(g.ndata['h']) == [0.] * 10
    # pop nodes
    assert _pfc(g.pop_n_repr('h')) == [0.] * 10
    assert len(g.ndata) == 0
    g.set_n_repr({'h' : mx.nd.zeros((10, D))})
    # set partial nodes
    u = mx.nd.array([1, 3, 5], dtype='int64')
    g.set_n_repr({'h' : mx.nd.ones((3, D))}, u)
    assert _pfc(g.ndata['h']) == [0., 1., 0., 1., 0., 1., 0., 0., 0., 0.]
    # get partial nodes
    u = mx.nd.array([1, 2, 3], dtype='int64')
    assert _pfc(g.get_n_repr(u)['h']) == [1., 0., 1.]

    '''
    s, d, eid
    0, 1, 0
    1, 9, 1
    0, 2, 2
    2, 9, 3
    0, 3, 4
    3, 9, 5
    0, 4, 6
    4, 9, 7
    0, 5, 8
    5, 9, 9
    0, 6, 10
    6, 9, 11
    0, 7, 12
    7, 9, 13
    0, 8, 14
    8, 9, 15
    9, 0, 16
    '''
    # set all edges
    g.edata['l'] = mx.nd.zeros((17, D))
    assert _pfc(g.edata['l']) == [0.] * 17
    # pop edges
    assert _pfc(g.pop_e_repr('l')) == [0.] * 17
    assert len(g.edata) == 0
    g.edata['l'] = mx.nd.zeros((17, D))
    # set partial edges (many-many)
    u = mx.nd.array([0, 0, 2, 5, 9], dtype='int64')
    v = mx.nd.array([1, 3, 9, 9, 0], dtype='int64')
    g.edges[u, v].data['l'] = mx.nd.ones((5, D))
    truth = [0.] * 17
    truth[0] = truth[4] = truth[3] = truth[9] = truth[16] = 1.
    assert _pfc(g.edata['l']) == truth
    # set partial edges (many-one)
    u = mx.nd.array([3, 4, 6], dtype='int64')
    v = mx.nd.array([9], dtype='int64')
    g.edges[u, v].data['l'] = mx.nd.ones((3, D))
    truth[5] = truth[7] = truth[11] = 1.
    assert _pfc(g.edata['l']) == truth
    # set partial edges (one-many)
    u = mx.nd.array([0], dtype='int64')
    v = mx.nd.array([4, 5, 6], dtype='int64')
    g.edges[u, v].data['l'] = mx.nd.ones((3, D))
    truth[6] = truth[8] = truth[10] = 1.
    assert _pfc(g.edata['l']) == truth
    # get partial edges (many-many)
    u = mx.nd.array([0, 6, 0], dtype='int64')
    v = mx.nd.array([6, 9, 7], dtype='int64')
    assert _pfc(g.edges[u, v].data['l']) == [1., 1., 0.]
    # get partial edges (many-one)
    u = mx.nd.array([5, 6, 7], dtype='int64')
    v = mx.nd.array([9], dtype='int64')
    assert _pfc(g.edges[u, v].data['l']) == [1., 1., 0.]
    # get partial edges (one-many)
    u = mx.nd.array([0], dtype='int64')
    v = mx.nd.array([3, 4, 5], dtype='int64')
    assert _pfc(g.edges[u, v].data['l']) == [1., 1., 1.]

def test_batch_setter_autograd():
    with mx.autograd.record():
        g = generate_graph(grad=True)
        h1 = g.ndata['h']
        h1.attach_grad()
        # partial set
        v = mx.nd.array([1, 2, 8], dtype='int64')
        hh = mx.nd.zeros((len(v), D))
        hh.attach_grad()
        g.set_n_repr({'h' : hh}, v)
        h2 = g.ndata['h']
    h2.backward(mx.nd.ones((10, D)) * 2)
    check_eq(h1.grad[:,0], mx.nd.array([2., 0., 0., 2., 2., 2., 2., 2., 0., 2.]))
    check_eq(hh.grad[:,0], mx.nd.array([2., 2., 2.]))

def test_batch_send():
    g = generate_graph()
    def _fmsg(edges):
        assert edges.src['h'].shape == (5, D)
        return {'m' : edges.src['h']}
    g.register_message_func(_fmsg)
    # many-many send
    u = mx.nd.array([0, 0, 0, 0, 0], dtype='int64')
    v = mx.nd.array([1, 2, 3, 4, 5], dtype='int64')
    g.send((u, v))
    # one-many send
    u = mx.nd.array([0], dtype='int64')
    v = mx.nd.array([1, 2, 3, 4, 5], dtype='int64')
    g.send((u, v))
    # many-one send
    u = mx.nd.array([1, 2, 3, 4, 5], dtype='int64')
    v = mx.nd.array([9], dtype='int64')
    g.send((u, v))

def test_batch_recv():
    # basic recv test
    g = generate_graph()
    g.register_message_func(message_func)
    g.register_reduce_func(reduce_func)
    g.register_apply_node_func(apply_node_func)
    u = mx.nd.array([0, 0, 0, 4, 5, 6], dtype='int64')
    v = mx.nd.array([1, 2, 3, 9, 9, 9], dtype='int64')
    reduce_msg_shapes.clear()
    g.send((u, v))
    #g.recv(th.unique(v))
    #assert(reduce_msg_shapes == {(1, 3, D), (3, 1, D)})
    #reduce_msg_shapes.clear()

def test_update_routines():
    g = generate_graph()
    g.register_message_func(message_func)
    g.register_reduce_func(reduce_func)
    g.register_apply_node_func(apply_node_func)

    # send_and_recv
    reduce_msg_shapes.clear()
    u = mx.nd.array([0, 0, 0, 4, 5, 6], dtype='int64')
    v = mx.nd.array([1, 2, 3, 9, 9, 9], dtype='int64')
    g.send_and_recv((u, v))
    assert(reduce_msg_shapes == {(1, 3, D), (3, 1, D)})
    reduce_msg_shapes.clear()

    # pull
    v = mx.nd.array([1, 2, 3, 9], dtype='int64')
    reduce_msg_shapes.clear()
    g.pull(v)
    assert(reduce_msg_shapes == {(1, 8, D), (3, 1, D)})
    reduce_msg_shapes.clear()

    # push
    v = mx.nd.array([0, 1, 2, 3], dtype='int64')
    reduce_msg_shapes.clear()
    g.push(v)
    assert(reduce_msg_shapes == {(1, 3, D), (8, 1, D)})
    reduce_msg_shapes.clear()

    # update_all
    reduce_msg_shapes.clear()
    g.update_all()
    assert(reduce_msg_shapes == {(1, 8, D), (9, 1, D)})
    reduce_msg_shapes.clear()

def test_reduce_0deg():
    g = DGLGraph()
    g.add_nodes(5)
    g.add_edge(1, 0)
    g.add_edge(2, 0)
    g.add_edge(3, 0)
    g.add_edge(4, 0)
    def _message(edges):
        return {'m' : edges.src['h']}
    def _reduce(nodes):
        return {'h' : nodes.data['h'] + nodes.mailbox['m'].sum(1)}
    old_repr = mx.nd.random.normal(shape=(5, 5))
    g.set_n_repr({'h': old_repr})
    g.update_all(_message, _reduce)
    new_repr = g.ndata['h']

    assert np.allclose(new_repr[1:].asnumpy(), old_repr[1:].asnumpy())
    assert np.allclose(new_repr[0].asnumpy(), old_repr.sum(0).asnumpy())

def test_pull_0deg():
    g = DGLGraph()
    g.add_nodes(2)
    g.add_edge(0, 1)
    def _message(edges):
        return {'m' : edges.src['h']}
    def _reduce(nodes):
        return {'h' : nodes.mailbox['m'].sum(1)}

    old_repr = mx.nd.random.normal(shape=(2, 5))
    g.set_n_repr({'h' : old_repr})
    g.pull(0, _message, _reduce)
    new_repr = g.ndata['h']
    assert np.allclose(new_repr[0].asnumpy(), old_repr[0].asnumpy())
    assert np.allclose(new_repr[1].asnumpy(), old_repr[1].asnumpy())
    g.pull(1, _message, _reduce)
    new_repr = g.ndata['h']
    assert np.allclose(new_repr[1].asnumpy(), old_repr[0].asnumpy())

    old_repr = mx.nd.random.normal(shape=(2, 5))
    g.set_n_repr({'h' : old_repr})
    g.pull([0, 1], _message, _reduce)
    new_repr = g.ndata['h']
    assert np.allclose(new_repr[0].asnumpy(), old_repr[0].asnumpy())
    assert np.allclose(new_repr[1].asnumpy(), old_repr[0].asnumpy())

if __name__ == '__main__':
    test_batch_setter_getter()
    test_batch_setter_autograd()
    test_batch_send()
    test_batch_recv()
    test_update_routines()
    test_reduce_0deg()
    test_pull_0deg()
