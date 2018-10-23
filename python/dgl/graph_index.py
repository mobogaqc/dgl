from __future__ import absolute_import

import ctypes
import numpy as np
import networkx as nx
import scipy

from ._ffi.base import c_array
from ._ffi.function import _init_api
from . import backend as F
from . import utils

GraphIndexHandle = ctypes.c_void_p

class GraphIndex(object):
    """Graph index object.

    Parameters
    ----------
    handle : GraphIndexHandle
        Handler
    """
    def __init__(self, handle):
        self._handle = handle
        self._cache = {}

    def __del__(self):
        """Free this graph index object."""
        _CAPI_DGLGraphFree(self._handle)

    def add_nodes(self, num):
        """Add nodes.
        
        Parameters
        ----------
        num : int
            Number of nodes to be added.
        """
        _CAPI_DGLGraphAddVertices(self._handle, num);
        self._cache.clear()

    def add_edge(self, u, v):
        """Add one edge.
        
        Parameters
        ----------
        u : int
            The src node.
        v : int
            The dst node.
        """
        _CAPI_DGLGraphAddEdge(self._handle, u, v);
        self._cache.clear()

    def add_edges(self, u, v):
        """Add many edges.
        
        Parameters
        ----------
        u : utils.Index
            The src nodes.
        v : utils.Index
            The dst nodes.
        """
        u_array = u.todgltensor()
        v_array = v.todgltensor()
        _CAPI_DGLGraphAddEdges(self._handle, u_array, v_array)
        self._cache.clear()

    def clear(self):
        """Clear the graph."""
        _CAPI_DGLGraphClear(self._handle)
        self._cache.clear()

    def is_multigraph(self):
        """Return whether the graph is a multigraph

        Returns
        -------
        bool
            True if it is a multigraph, False otherwise.
        """
        return bool(_CAPI_DGLGraphIsMultigraph(self._handle))

    def number_of_nodes(self):
        """Return the number of nodes.

        Returns
        -------
        int
            The number of nodes
        """
        return _CAPI_DGLGraphNumVertices(self._handle)

    def number_of_edges(self):
        """Return the number of edges.

        Returns
        -------
        int
            The number of edges
        """
        return _CAPI_DGLGraphNumEdges(self._handle)

    def has_node(self, vid):
        """Return true if the node exists.

        Parameters
        ----------
        vid : int
            The nodes

        Returns
        -------
        bool
            True if the node exists, False otherwise.
        """
        return bool(_CAPI_DGLGraphHasVertex(self._handle, vid))

    def has_nodes(self, vids):
        """Return true if the nodes exist.

        Parameters
        ----------
        vid : utils.Index
            The nodes

        Returns
        -------
        utils.Index
            0-1 array indicating existence
        """
        vid_array = vids.todgltensor()
        return utils.toindex(_CAPI_DGLGraphHasVertices(self._handle, vid_array))

    def has_edge_between(self, u, v):
        """Return true if the edge exists.

        Parameters
        ----------
        u : int
            The src node.
        v : int
            The dst node.

        Returns
        -------
        bool
            True if the edge exists, False otherwise
        """
        return bool(_CAPI_DGLGraphHasEdgeBetween(self._handle, u, v))

    def has_edges_between(self, u, v):
        """Return true if the edge exists.

        Parameters
        ----------
        u : utils.Index
            The src nodes.
        v : utils.Index
            The dst nodes.

        Returns
        -------
        utils.Index
            0-1 array indicating existence
        """
        u_array = u.todgltensor()
        v_array = v.todgltensor()
        return utils.toindex(_CAPI_DGLGraphHasEdgesBetween(self._handle, u_array, v_array))

    def predecessors(self, v, radius=1):
        """Return the predecessors of the node.

        Parameters
        ----------
        v : int
            The node.
        radius : int, optional
            The radius of the neighborhood.

        Returns
        -------
        utils.Index
            Array of predecessors
        """
        return utils.toindex(_CAPI_DGLGraphPredecessors(self._handle, v, radius))

    def successors(self, v, radius=1):
        """Return the successors of the node.

        Parameters
        ----------
        v : int
            The node.
        radius : int, optional
            The radius of the neighborhood.

        Returns
        -------
        utils.Index
            Array of successors
        """
        return utils.toindex(_CAPI_DGLGraphSuccessors(self._handle, v, radius))

    def edge_id(self, u, v):
        """Return the id array of all edges between u and v.

        Parameters
        ----------
        u : int
            The src node.
        v : int
            The dst node.

        Returns
        -------
        utils.Index
            The edge id array.
        """
        return utils.toindex(_CAPI_DGLGraphEdgeId(self._handle, u, v))

    def edge_ids(self, u, v):
        """Return a triplet of arrays that contains the edge IDs.

        Parameters
        ----------
        u : utils.Index
            The src nodes.
        v : utils.Index
            The dst nodes.

        Returns
        -------
        utils.Index
            The src nodes.
        utils.Index
            The dst nodes.
        utils.Index
            The edge ids.
        """
        u_array = u.todgltensor()
        v_array = v.todgltensor()
        edge_array = _CAPI_DGLGraphEdgeIds(self._handle, u_array, v_array)

        src = utils.toindex(edge_array(0))
        dst = utils.toindex(edge_array(1))
        eid = utils.toindex(edge_array(2))

        return src, dst, eid

    def find_edges(self, eid):
        """Return a triplet of arrays that contains the edge IDs.

        Parameters
        ----------
        eid : utils.Index
            The edge ids.

        Returns
        -------
        utils.Index
            The src nodes.
        utils.Index
            The dst nodes.
        utils.Index
            The edge ids.
        """
        eid_array = eid.todgltensor()
        edge_array = _CAPI_DGLGraphFindEdges(self._handle, eid_array)

        src = utils.toindex(edge_array(0))
        dst = utils.toindex(edge_array(1))
        eid = utils.toindex(edge_array(2))

        return src, dst, eid

    def in_edges(self, v):
        """Return the in edges of the node(s).

        Parameters
        ----------
        v : utils.Index
            The node(s).
        
        Returns
        -------
        utils.Index
            The src nodes.
        utils.Index
            The dst nodes.
        utils.Index
            The edge ids.
        """
        if len(v) == 1:
            edge_array = _CAPI_DGLGraphInEdges_1(self._handle, v[0])
        else:
            v_array = v.todgltensor()
            edge_array = _CAPI_DGLGraphInEdges_2(self._handle, v_array)
        src = utils.toindex(edge_array(0))
        dst = utils.toindex(edge_array(1))
        eid = utils.toindex(edge_array(2))
        return src, dst, eid

    def out_edges(self, v):
        """Return the out edges of the node(s).

        Parameters
        ----------
        v : utils.Index
            The node(s).
        
        Returns
        -------
        utils.Index
            The src nodes.
        utils.Index
            The dst nodes.
        utils.Index
            The edge ids.
        """
        if len(v) == 1:
            edge_array = _CAPI_DGLGraphOutEdges_1(self._handle, v[0])
        else:
            v_array = v.todgltensor()
            edge_array = _CAPI_DGLGraphOutEdges_2(self._handle, v_array)
        src = utils.toindex(edge_array(0))
        dst = utils.toindex(edge_array(1))
        eid = utils.toindex(edge_array(2))
        return src, dst, eid

    def edges(self, sorted=False):
        """Return all the edges

        Parameters
        ----------
        sorted : bool
            True if the returned edges are sorted by their src and dst ids.
        
        Returns
        -------
        utils.Index
            The src nodes.
        utils.Index
            The dst nodes.
        utils.Index
            The edge ids.
        """
        edge_array = _CAPI_DGLGraphEdges(self._handle, sorted)
        src = utils.toindex(edge_array(0))
        dst = utils.toindex(edge_array(1))
        eid = utils.toindex(edge_array(2))
        return src, dst, eid

    def in_degree(self, v):
        """Return the in degree of the node.

        Parameters
        ----------
        v : int
            The node.

        Returns
        -------
        int
            The in degree.
        """
        return _CAPI_DGLGraphInDegree(self._handle, v)

    def in_degrees(self, v):
        """Return the in degrees of the nodes.

        Parameters
        ----------
        v : utils.Index
            The nodes.

        Returns
        -------
        int
            The in degree array.
        """
        v_array = v.todgltensor()
        return utils.toindex(_CAPI_DGLGraphInDegrees(self._handle, v_array))

    def out_degree(self, v):
        """Return the out degree of the node.

        Parameters
        ----------
        v : int
            The node.

        Returns
        -------
        int
            The out degree.
        """
        return _CAPI_DGLGraphOutDegree(self._handle, v)

    def out_degrees(self, v):
        """Return the out degrees of the nodes.

        Parameters
        ----------
        v : utils.Index
            The nodes.

        Returns
        -------
        int
            The out degree array.
        """
        v_array = v.todgltensor()
        return utils.toindex(_CAPI_DGLGraphOutDegrees(self._handle, v_array))

    def node_subgraph(self, v):
        """Return the induced node subgraph.

        Parameters
        ----------
        v : utils.Index
            The nodes.

        Returns
        -------
        SubgraphIndex
            The subgraph index.
        """
        v_array = v.todgltensor()
        rst = _CAPI_DGLGraphVertexSubgraph(self._handle, v_array)
        induced_edges = utils.toindex(rst(2))
        return SubgraphIndex(rst(0), self, v, induced_edges)

    def edge_subgraph(self, e):
        """Return the induced edge subgraph.

        Parameters
        ----------
        e : utils.Index
            The edges.

        Returns
        -------
        SubgraphIndex
            The subgraph index.
        """
        e_array = e.todgltensor()
        rst = _CAPI_DGLGraphEdgeSubgraph(self._handle, e_array)
        gi = GraphIndex(rst(0))
        induced_nodes = utils.toindex(rst(1))
        return SubgraphIndex(rst(0), self, induced_nodes, e)

    def adjacency_matrix(self):
        """Return the adjacency matrix representation of this graph.

        Returns
        -------
        utils.CtxCachedObject
            An object that returns tensor given context.
        """
        if not 'adj' in self._cache:
            src, dst, _ = self.edges(sorted=False)
            src = F.unsqueeze(src.tousertensor(), 0)
            dst = F.unsqueeze(dst.tousertensor(), 0)
            idx = F.pack([dst, src])
            n = self.number_of_nodes()
            dat = F.ones((self.number_of_edges(),))
            mat = F.sparse_tensor(idx, dat, [n, n])
            self._cache['adj'] = utils.CtxCachedObject(lambda ctx: F.to_context(mat, ctx))
        return self._cache['adj']

    def incidence_matrix(self, oriented=False):
        """Return the incidence matrix representation of this graph.
        
        Parameters
        ----------
        oriented : bool, optional (default=False)
          Whether the returned incidence matrix is oriented.

        Returns
        -------
        utils.CtxCachedObject
            An object that returns tensor given context.
        """
        key = ('oriented ' if oriented else '') + 'incidence matrix'
        if not key in self._cache:
            src, dst, _ = self.edges(sorted=False)
            src = src.tousertensor()
            dst = dst.tousertensor()
            m = self.number_of_edges()
            eid = F.arange(m, dtype=F.int64)
            row = F.pack([src, dst])
            col = F.pack([eid, eid])
            idx = F.stack([row, col])

            diagonal = (src == dst)
            if oriented:
                x = -F.ones((m,))
                y = F.ones((m,))
                x[diagonal] = 0
                y[diagonal] = 0
                dat = F.pack([x, y])
            else:
                x = F.ones((m,))
                x[diagonal] = 0
                dat = F.pack([x, x])
            n = self.number_of_nodes()
            mat = F.sparse_tensor(idx, dat, [n, m])
            self._cache[key] = utils.CtxCachedObject(lambda ctx: F.to_context(mat, ctx))

        return self._cache[key]

    def to_networkx(self):
        """Convert to networkx graph.

        The edge id will be saved as the 'id' edge attribute.

        Returns
        -------
        networkx.DiGraph
            The nx graph
        """
        src, dst, eid = self.edges()
        ret = nx.MultiDiGraph() if self.is_multigraph() else nx.DiGraph()
        ret.add_nodes_from(range(self.number_of_nodes()))
        for u, v, id in zip(src, dst, eid):
            ret.add_edge(u, v, id=id)
        return ret

    def from_networkx(self, nx_graph):
        """Convert from networkx graph.

        If 'id' edge attribute exists, the edge will be added follows
        the edge id order. Otherwise, order is undefined.
        
        Parameters
        ----------
        nx_graph : networkx.DiGraph
            The nx graph
        """
        self.clear()

        if not isinstance(nx_graph, nx.Graph):
            nx_graph = (nx.MultiDiGraph(nx_graph) if self.is_multigraph()
                    else nx.DiGraph(nx_graph))
        else:
            nx_graph = nx_graph.to_directed()

        num_nodes = nx_graph.number_of_nodes()
        self.add_nodes(num_nodes)

        if nx_graph.number_of_edges() == 0:
            return

        # nx_graph.edges(data=True) returns src, dst, attr_dict
        has_edge_id = 'id' in next(iter(nx_graph.edges(data=True)))[-1]
        if has_edge_id:
            num_edges = nx_graph.number_of_edges()
            src = np.zeros((num_edges,), dtype=np.int64)
            dst = np.zeros((num_edges,), dtype=np.int64)
            for u, v, attr in nx_graph.edges(data=True):
                eid = attr['id']
                src[eid] = u
                dst[eid] = v
        else:
            src = []
            dst = []
            for e in nx_graph.edges:
                src.append(e[0])
                dst.append(e[1])
        src = utils.toindex(src)
        dst = utils.toindex(dst)
        self.add_edges(src, dst)

    def from_scipy_sparse_matrix(self, adj):
        """Convert from scipy sparse matrix.

        Parameters
        ----------
        adj : scipy sparse matrix
        """
        self.clear()
        self.add_nodes(adj.shape[0])
        adj_coo = adj.tocoo()
        src = utils.toindex(adj_coo.row)
        dst = utils.toindex(adj_coo.col)
        self.add_edges(src, dst)

    def line_graph(self, backtracking=True):
        """Return the line graph of this graph.

        Parameters
        ----------
        backtracking : bool, optional (default=False)
          Whether (i, j) ~ (j, i) in L(G).
          (i, j) ~ (j, i) is the behavior of networkx.line_graph.

        Returns
        -------
        GraphIndex
            The line graph of this graph.
        """
        handle = _CAPI_DGLGraphLineGraph(self._handle, backtracking)
        return GraphIndex(handle)

class SubgraphIndex(GraphIndex):
    """Graph index for subgraph.

    Parameters
    ----------
    handle : GraphIndexHandle
        The capi handle.
    paranet : GraphIndex
        The parent graph index.
    induced_nodes : utils.Index
        The parent node ids in this subgraph.
    induced_edges : utils.Index
        The parent edge ids in this subgraph.
    """
    def __init__(self, handle, parent, induced_nodes, induced_edges):
        super(SubgraphIndex, self).__init__(handle)
        self._parent = parent
        self._induced_nodes = induced_nodes
        self._induced_edges = induced_edges

    def add_nodes(self, num):
        """Add nodes. Disabled because SubgraphIndex is read-only."""
        raise RuntimeError('Readonly graph. Mutation is not allowed.')

    def add_edge(self, u, v):
        """Add edges. Disabled because SubgraphIndex is read-only."""
        raise RuntimeError('Readonly graph. Mutation is not allowed.')

    def add_edges(self, u, v):
        """Add edges. Disabled because SubgraphIndex is read-only."""
        raise RuntimeError('Readonly graph. Mutation is not allowed.')

    @property
    def induced_nodes(self):
        """Return parent node ids.

        Returns
        -------
        utils.Index
            The parent node ids.
        """
        return self._induced_nodes

    @property
    def induced_edges(self):
        """Return parent edge ids.

        Returns
        -------
        utils.Index
            The parent edge ids.
        """
        return self._induced_edges

def disjoint_union(graphs):
    """Return a disjoint union of the input graphs.

    The new graph will include all the nodes/edges in the given graphs.
    Nodes/Edges will be relabled by adding the cumsum of the previous graph sizes
    in the given sequence order. For example, giving input [g1, g2, g3], where
    they have 5, 6, 7 nodes respectively. Then node#2 of g2 will become node#7
    in the result graph. Edge ids are re-assigned similarly.

    Parameters
    ----------
    graphs : iterable of GraphIndex
        The input graphs

    Returns
    -------
    GraphIndex
        The disjoint union
    """
    inputs = c_array(GraphIndexHandle, [gr._handle for gr in graphs])
    inputs = ctypes.cast(inputs, ctypes.c_void_p)
    handle = _CAPI_DGLDisjointUnion(inputs, len(graphs))
    return GraphIndex(handle)

def disjoint_partition(graph, num_or_size_splits):
    """Partition the graph disjointly.
   
    This is a reverse operation of DisjointUnion. The graph will be partitioned
    into num graphs. This requires the given number of partitions to evenly
    divides the number of nodes in the graph. If the a size list is given,
    the sum of the given sizes is equal.

    Parameters
    ----------
    graph : GraphIndex
        The graph to be partitioned
    num_or_size_splits : int or utils.Index
        The partition number of size splits

    Returns
    -------
    list of GraphIndex
        The partitioned graphs
    """
    if isinstance(num_or_size_splits, utils.Index):
        rst = _CAPI_DGLDisjointPartitionBySizes(
                graph._handle,
                num_or_size_splits.todgltensor())
    else:
        rst = _CAPI_DGLDisjointPartitionByNum(
                graph._handle,
                int(num_or_size_splits))
    graphs = []
    for val in rst.asnumpy():
        handle = ctypes.cast(int(val), ctypes.c_void_p)
        graphs.append(GraphIndex(handle))
    return graphs

def create_graph_index(graph_data=None, multigraph=False):
    """Create a graph index object.

    Parameters
    ----------
    graph_data : graph data, optional
        Data to initialize graph. Same as networkx's semantics.
    multigraph : bool, optional
        Whether the graph is multigraph (default is False)
    """
    if isinstance(graph_data, GraphIndex):
        return graph_data

    handle = _CAPI_DGLGraphCreate(multigraph)
    gi = GraphIndex(handle)

    if graph_data is None:
        return gi

    # scipy format
    if isinstance(graph_data, scipy.sparse.spmatrix):
        try:
            gi.from_scipy_sparse_matrix(graph_data)
            return gi
        except:
            raise Exception('Graph data is not a valid scipy sparse matrix.')

    # networkx - any format
    try:
        gi.from_networkx(graph_data)
    except:
        raise Exception('Error while creating graph from input of type "%s".'
                         % type(graph_data))

    return gi

_init_api("dgl.graph_index")
