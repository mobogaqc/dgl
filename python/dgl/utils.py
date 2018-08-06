"""Utility module."""
from __future__ import absolute_import

from collections import Mapping
import dgl.backend as F
from dgl.backend import Tensor, SparseTensor

def is_id_tensor(u):
    return isinstance(u, Tensor) and F.isinteger(u) and len(F.shape(u)) == 1

def is_id_container(u):
    return isinstance(u, list)

def node_iter(n):
    n = convert_to_id_container(n)
    for nn in n:
        yield nn

def edge_iter(u, v):
    u = convert_to_id_container(u)
    v = convert_to_id_container(v)
    if len(u) == len(v):
        # many-many
        for uu, vv in zip(u, v):
            yield uu, vv
    elif len(v) == 1:
        # many-one
        for uu in u:
            yield uu, v[0]
    elif len(u) == 1:
        # one-many
        for vv in v:
            yield u[0], vv
    else:
        raise ValueError('Error edges:', u, v)

def convert_to_id_container(x):
    if is_id_container(x):
        return x
    elif is_id_tensor(x):
        return F.asnumpy(x)
    else:
        try:
            return [int(x)]
        except:
            raise TypeError('Error node: %s' % str(x))
    return None

def convert_to_id_tensor(x, ctx=None):
    if is_id_container(x):
        ret = F.tensor(x, dtype=F.int64)
    elif is_id_tensor(x):
        ret = x
    else:
        try:
            ret = F.tensor([int(x)], dtype=F.int64)
        except:
            raise TypeError('Error node: %s' % str(x))
    ret = F.to_context(ret, ctx)
    return ret

class LazyDict(Mapping):
    """A readonly dictionary that does not materialize the storage."""
    def __init__(self, fn, keys):
        self._fn = fn
        self._keys = keys

    def keys(self):
        return self._keys

    def __getitem__(self, key):
        assert key in self._keys
        return self._fn(key)

    def __contains__(self, key):
        return key in self._keys

    def __iter__(self):
        for key in self._keys:
            yield key, self._fn(key)

    def __len__(self):
        return len(self._keys)
