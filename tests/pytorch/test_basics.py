import torch as th
from torch.autograd import Variable
import numpy as np
from dgl.graph import DGLGraph

D = 5
reduce_msg_shapes = set()

def check_eq(a, b):
    assert a.shape == b.shape
    assert th.sum(a == b) == int(np.prod(list(a.shape)))

def message_func(src, edge):
    assert len(src['h'].shape) == 2
    assert src['h'].shape[1] == D
    return {'m' : src['h']}

def reduce_func(node, msgs):
    msgs = msgs['m']
    reduce_msg_shapes.add(tuple(msgs.shape))
    assert len(msgs.shape) == 3
    assert msgs.shape[2] == D
    return {'accum' : th.sum(msgs, 1)}

def apply_node_func(node):
    return {'h' : node['h'] + node['accum']}

def generate_graph(grad=False):
    g = DGLGraph()
    g.add_nodes(10) # 10 nodes.
    # create a graph where 0 is the source and 9 is the sink
    # 17 edges
    for i in range(1, 9):
        g.add_edge(0, i)
        g.add_edge(i, 9)
    # add a back flow from 9 to 0
    g.add_edge(9, 0)
    ncol = Variable(th.randn(10, D), requires_grad=grad)
    accumcol = Variable(th.randn(10, D), requires_grad=grad)
    ecol = Variable(th.randn(17, D), requires_grad=grad)
    g.set_n_repr({'h' : ncol})
    g.set_n_initializer(lambda shape, dtype : th.zeros(shape))
    return g

def test_batch_setter_getter():
    def _pfc(x):
        return list(x.numpy()[:,0])
    g = generate_graph()
    # set all nodes
    g.set_n_repr({'h' : th.zeros((10, D))})
    assert _pfc(g.get_n_repr()['h']) == [0.] * 10
    # pop nodes
    old_len = len(g.get_n_repr())
    assert _pfc(g.pop_n_repr('h')) == [0.] * 10
    assert len(g.get_n_repr()) == old_len - 1
    g.set_n_repr({'h' : th.zeros((10, D))})
    # set partial nodes
    u = th.tensor([1, 3, 5])
    g.set_n_repr({'h' : th.ones((3, D))}, u)
    assert _pfc(g.get_n_repr()['h']) == [0., 1., 0., 1., 0., 1., 0., 0., 0., 0.]
    # get partial nodes
    u = th.tensor([1, 2, 3])
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
    g.set_e_repr({'l' : th.zeros((17, D))})
    assert _pfc(g.get_e_repr()['l']) == [0.] * 17
    # pop edges
    old_len = len(g.get_e_repr())
    assert _pfc(g.pop_e_repr('l')) == [0.] * 17
    assert len(g.get_e_repr()) == old_len - 1
    g.set_e_repr({'l' : th.zeros((17, D))})
    # set partial edges (many-many)
    u = th.tensor([0, 0, 2, 5, 9])
    v = th.tensor([1, 3, 9, 9, 0])
    g.set_e_repr({'l' : th.ones((5, D))}, u, v)
    truth = [0.] * 17
    truth[0] = truth[4] = truth[3] = truth[9] = truth[16] = 1.
    assert _pfc(g.get_e_repr()['l']) == truth
    # set partial edges (many-one)
    u = th.tensor([3, 4, 6])
    v = th.tensor([9])
    g.set_e_repr({'l' : th.ones((3, D))}, u, v)
    truth[5] = truth[7] = truth[11] = 1.
    assert _pfc(g.get_e_repr()['l']) == truth
    # set partial edges (one-many)
    u = th.tensor([0])
    v = th.tensor([4, 5, 6])
    g.set_e_repr({'l' : th.ones((3, D))}, u, v)
    truth[6] = truth[8] = truth[10] = 1.
    assert _pfc(g.get_e_repr()['l']) == truth
    # get partial edges (many-many)
    u = th.tensor([0, 6, 0])
    v = th.tensor([6, 9, 7])
    assert _pfc(g.get_e_repr(u, v)['l']) == [1., 1., 0.]
    # get partial edges (many-one)
    u = th.tensor([5, 6, 7])
    v = th.tensor([9])
    assert _pfc(g.get_e_repr(u, v)['l']) == [1., 1., 0.]
    # get partial edges (one-many)
    u = th.tensor([0])
    v = th.tensor([3, 4, 5])
    assert _pfc(g.get_e_repr(u, v)['l']) == [1., 1., 1.]

def test_batch_setter_autograd():
    g = generate_graph(grad=True)
    h1 = g.get_n_repr()['h']
    # partial set
    v = th.tensor([1, 2, 8])
    hh = Variable(th.zeros((len(v), D)), requires_grad=True)
    g.set_n_repr({'h' : hh}, v)
    h2 = g.get_n_repr()['h']
    h2.backward(th.ones((10, D)) * 2)
    check_eq(h1.grad[:,0], th.tensor([2., 0., 0., 2., 2., 2., 2., 2., 0., 2.]))
    check_eq(hh.grad[:,0], th.tensor([2., 2., 2.]))

def test_batch_send():
    g = generate_graph()
    def _fmsg(src, edge):
        assert src['h'].shape == (5, D)
        return {'m' : src['h']}
    g.register_message_func(_fmsg)
    # many-many send
    u = th.tensor([0, 0, 0, 0, 0])
    v = th.tensor([1, 2, 3, 4, 5])
    g.send(u, v)
    # one-many send
    u = th.tensor([0])
    v = th.tensor([1, 2, 3, 4, 5])
    g.send(u, v)
    # many-one send
    u = th.tensor([1, 2, 3, 4, 5])
    v = th.tensor([9])
    g.send(u, v)

def test_batch_recv():
    # basic recv test
    g = generate_graph()
    g.register_message_func(message_func)
    g.register_reduce_func(reduce_func)
    g.register_apply_node_func(apply_node_func)
    u = th.tensor([0, 0, 0, 4, 5, 6])
    v = th.tensor([1, 2, 3, 9, 9, 9])
    reduce_msg_shapes.clear()
    g.send(u, v)
    g.recv(th.unique(v))
    assert(reduce_msg_shapes == {(1, 3, D), (3, 1, D)})
    reduce_msg_shapes.clear()

def test_update_routines():
    g = generate_graph()
    g.register_message_func(message_func)
    g.register_reduce_func(reduce_func)
    g.register_apply_node_func(apply_node_func)

    # send_and_recv
    reduce_msg_shapes.clear()
    u = th.tensor([0, 0, 0, 4, 5, 6])
    v = th.tensor([1, 2, 3, 9, 9, 9])
    g.send_and_recv(u, v)
    assert(reduce_msg_shapes == {(1, 3, D), (3, 1, D)})
    reduce_msg_shapes.clear()

    # pull
    v = th.tensor([1, 2, 3, 9])
    reduce_msg_shapes.clear()
    g.pull(v)
    assert(reduce_msg_shapes == {(1, 8, D), (3, 1, D)})
    reduce_msg_shapes.clear()

    # push
    v = th.tensor([0, 1, 2, 3])
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
    def _message(src, edge):
        return {'m' : src['h']}
    def _reduce(node, msgs):
        return {'h' : node['h'] + msgs['m'].sum(1)}
    old_repr = th.randn(5, 5)
    g.set_n_repr({'h' : old_repr})
    g.update_all(_message, _reduce)
    new_repr = g.get_n_repr()['h']

    assert th.allclose(new_repr[1:], old_repr[1:])
    assert th.allclose(new_repr[0], old_repr.sum(0))

def test_pull_0deg():
    g = DGLGraph()
    g.add_nodes(2)
    g.add_edge(0, 1)
    def _message(src, edge):
        return {'m' : src['h']}
    def _reduce(node, msgs):
        return {'h' : msgs['m'].sum(1)}
    old_repr = th.randn(2, 5)
    g.set_n_repr({'h' : old_repr})

    g.pull(0, _message, _reduce)
    new_repr = g.get_n_repr()['h']
    assert th.allclose(new_repr[0], old_repr[0])
    assert th.allclose(new_repr[1], old_repr[1])

    g.pull(1, _message, _reduce)
    new_repr = g.get_n_repr()['h']
    assert th.allclose(new_repr[1], old_repr[0])

    old_repr = th.randn(2, 5)
    g.set_n_repr({'h' : old_repr})
    g.pull([0, 1], _message, _reduce)
    new_repr = g.get_n_repr()['h']
    assert th.allclose(new_repr[0], old_repr[0])
    assert th.allclose(new_repr[1], old_repr[0])

def _disabled_test_send_twice():
    # TODO(minjie): please re-enable this unittest after the send code problem is fixed.
    g = DGLGraph()
    g.add_nodes(3)
    g.add_edge(0, 1)
    g.add_edge(2, 1)
    def _message_a(src, edge):
        return {'a': src['a']}
    def _message_b(src, edge):
        return {'a': src['a'] * 3}
    def _reduce(node, msgs):
        assert msgs is not None
        return {'a': msgs['a'].max(1)[0]}

    old_repr = th.randn(3, 5)
    g.set_n_repr({'a': old_repr})
    g.send(0, 1, _message_a)
    g.send(0, 1, _message_b)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], old_repr[0] * 3)

    g.set_n_repr({'a': old_repr})
    g.send(0, 1, _message_a)
    g.send(2, 1, _message_b)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], th.stack([old_repr[0], old_repr[2] * 3], 0).max(0)[0])

def test_send_multigraph():
    g = DGLGraph(multigraph=True)
    g.add_nodes(3)
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(0, 1)
    g.add_edge(2, 1)

    def _message_a(src, edge):
        return {'a': edge['a']}
    def _message_b(src, edge):
        return {'a': edge['a'] * 3}
    def _reduce(node, msgs):
        assert msgs is not None
        return {'a': msgs['a'].max(1)[0]}

    def answer(*args):
        return th.stack(args, 0).max(0)[0]

    # send by eid
    old_repr = th.randn(4, 5)
    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send(eid=[0, 2], message_func=_message_a)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], answer(old_repr[0], old_repr[2]))

    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send(eid=[0, 2, 3], message_func=_message_a)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], answer(old_repr[0], old_repr[2], old_repr[3]))

    # send on multigraph
    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send([0, 2], [1, 1], _message_a)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], old_repr.max(0)[0])

    # consecutive send and send_on
    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send(2, 1, _message_a)
    g.send(eid=[0, 1], message_func=_message_b)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], answer(old_repr[0] * 3, old_repr[1] * 3, old_repr[3]))

    # consecutive send_on
    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send(eid=0, message_func=_message_a)
    g.send(eid=1, message_func=_message_b)
    g.recv([1], _reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], answer(old_repr[0], old_repr[1] * 3))

    # send_and_recv_on
    g.set_n_repr({'a': th.zeros(3, 5)})
    g.set_e_repr({'a': old_repr})
    g.send_and_recv(eid=[0, 2, 3], message_func=_message_a, reduce_func=_reduce)
    new_repr = g.get_n_repr()['a']
    assert th.allclose(new_repr[1], answer(old_repr[0], old_repr[2], old_repr[3]))
    assert th.allclose(new_repr[[0, 2]], th.zeros(2, 5))


if __name__ == '__main__':
    test_batch_setter_getter()
    test_batch_setter_autograd()
    test_batch_send()
    test_batch_recv()
    test_update_routines()
    test_reduce_0deg()
    test_pull_0deg()
    test_send_multigraph()
