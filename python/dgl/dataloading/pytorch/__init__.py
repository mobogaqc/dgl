"""DGL PyTorch DataLoaders"""
import inspect
from torch.utils.data import DataLoader
from ..dataloader import NodeCollator, EdgeCollator

class NodeDataLoader(DataLoader):
    """PyTorch dataloader for batch-iterating over a set of nodes, generating the list
    of blocks as computation dependency of the said minibatch.

    Parameters
    ----------
    g : DGLHeteroGraph
        The graph.
    nids : Tensor or dict[ntype, Tensor]
        The node set to compute outputs.
    block_sampler : :py:class:`~dgl.dataloading.BlockSampler`
        The neighborhood sampler.
    kwargs : dict
        Arguments being passed to ``torch.utils.data.DataLoader``.

    Examples
    --------
    To train a 3-layer GNN for node classification on a set of nodes ``train_nid`` on
    a homogeneous graph where each node takes messages from all neighbors (assume
    the backend is PyTorch):

    >>> sampler = dgl.dataloading.NeighborSampler([None, None, None])
    >>> dataloader = dgl.dataloading.NodeDataLoader(
    ...     g, train_nid, sampler,
    ...     batch_size=1024, shuffle=True, drop_last=False, num_workers=4)
    >>> for input_nodes, output_nodes, blocks in dataloader:
    ...     train_on(input_nodes, output_nodes, blocks)
    """
    collator_arglist = inspect.getfullargspec(NodeCollator).args

    def __init__(self, g, nids, block_sampler, **kwargs):
        collator_kwargs = {}
        dataloader_kwargs = {}
        for k, v in kwargs.items():
            if k in self.collator_arglist:
                collator_kwargs[k] = v
            else:
                dataloader_kwargs[k] = v
        self.collator = NodeCollator(g, nids, block_sampler, **collator_kwargs)
        super().__init__(
            self.collator.dataset, collate_fn=self.collator.collate, **dataloader_kwargs)

class EdgeDataLoader(DataLoader):
    """PyTorch dataloader for batch-iterating over a set of edges, generating the list
    of blocks as computation dependency of the said minibatch for edge classification,
    edge regression, and link prediction.

    Parameters
    ----------
    g : DGLHeteroGraph
        The graph.
    nids : Tensor or dict[ntype, Tensor]
        The node set to compute outputs.
    block_sampler : :py:class:`~dgl.dataloading.BlockSampler`
        The neighborhood sampler.
    g_sampling : DGLHeteroGraph, optional
        The graph where neighborhood sampling is performed.

        One may wish to iterate over the edges in one graph while perform sampling in
        another graph.  This may be the case for iterating over validation and test
        edge set while perform neighborhood sampling on the graph formed by only
        the training edge set.

        If None, assume to be the same as ``g``.
    exclude : str, optional
        Whether and how to exclude dependencies related to the sampled edges in the
        minibatch.  Possible values are

        * None,
        * ``reverse``,
        * ``reverse_types``

        See the docstring in :py:class:`~dgl.dataloading.EdgeCollator`.
    reverse_edge_ids : Tensor or dict[etype, Tensor], optional
        See the docstring in :py:class:`~dgl.dataloading.EdgeCollator`.
    reverse_etypes : dict[etype, etype], optional
        See the docstring in :py:class:`~dgl.dataloading.EdgeCollator`.
    negative_sampler : callable, optional
        The negative sampler.

        See the docstring in :py:class:`~dgl.dataloading.EdgeCollator`.
    kwargs : dict
        Arguments being passed to `torch.utils.data.DataLoader`.

    Examples
    --------
    The following example shows how to train a 3-layer GNN for edge classification on a
    set of edges ``train_eid`` on a homogeneous undirected graph.  Each node takes
    messages from all neighbors.

    Say that you have an array of source node IDs ``src`` and another array of destination
    node IDs ``dst``.  One can make it bidirectional by adding another set of edges
    that connects from ``dst`` to ``src``:

    >>> g = dgl.graph((torch.cat([src, dst]), torch.cat([dst, src])))

    One can then know that the ID difference of an edge and its reverse edge is ``|E|``,
    where ``|E|`` is the length of your source/destination array.  The reverse edge
    mapping can be obtained by

    >>> E = len(src)
    >>> reverse_eids = torch.cat([torch.arange(E, 2 * E), torch.arange(0, E)])

    Note that the sampled edges as well as their reverse edges are removed from
    computation dependencies of the incident nodes.  This is a common trick to avoid
    information leakage.

    >>> sampler = dgl.dataloading.NeighborSampler([None, None, None])
    >>> dataloader = dgl.dataloading.EdgeDataLoader(
    ...     g, train_eid, sampler, exclude='reverse',
    ...     reverse_eids=reverse_eids,
    ...     batch_size=1024, shuffle=True, drop_last=False, num_workers=4)
    >>> for input_nodes, pair_graph, blocks in dataloader:
    ...     train_on(input_nodes, pair_graph, blocks)

    To train a 3-layer GNN for link prediction on a set of edges ``train_eid`` on a
    homogeneous graph where each node takes messages from all neighbors (assume the
    backend is PyTorch), with 5 uniformly chosen negative samples per edge:

    >>> sampler = dgl.dataloading.NeighborSampler([None, None, None])
    >>> neg_sampler = dgl.dataloading.negative_sampler.Uniform(5)
    >>> dataloader = dgl.dataloading.EdgeDataLoader(
    ...     g, train_eid, sampler, exclude='reverse',
    ...     reverse_eids=reverse_eids, negative_sampler=neg_sampler,
    ...     batch_size=1024, shuffle=True, drop_last=False, num_workers=4)
    >>> for input_nodes, pos_pair_graph, neg_pair_graph, blocks in dataloader:
    ...     train_on(input_nodse, pair_graph, neg_pair_graph, blocks)

    For heterogeneous graphs, the reverse of an edge may have a different edge type
    from the original edge.  For instance, consider that you have an array of
    user-item clicks, representated by a user array ``user`` and an item array ``item``.
    You may want to build a heterogeneous graph with a user-click-item relation and an
    item-clicked-by-user relation.

    >>> g = dgl.heterograph({
    ...     ('user', 'click', 'item'): (user, item),
    ...     ('item', 'clicked-by', 'user'): (item, user)})

    To train a 3-layer GNN for edge classification on a set of edges ``train_eid`` with
    type ``click``, you can write

    >>> sampler = dgl.dataloading.NeighborSampler([None, None, None])
    >>> dataloader = dgl.dataloading.EdgeDataLoader(
    ...     g, {'click': train_eid}, sampler, exclude='reverse_types',
    ...     reverse_etypes={'click': 'clicked-by', 'clicked-by': 'click'},
    ...     batch_size=1024, shuffle=True, drop_last=False, num_workers=4)
    >>> for input_nodes, pair_graph, blocks in dataloader:
    ...     train_on(input_nodes, pair_graph, blocks)

    To train a 3-layer GNN for link prediction on a set of edges ``train_eid`` with type
    ``click``, you can write

    >>> sampler = dgl.dataloading.NeighborSampler([None, None, None])
    >>> neg_sampler = dgl.dataloading.negative_sampler.Uniform(5)
    >>> dataloader = dgl.dataloading.EdgeDataLoader(
    ...     g, train_eid, sampler, exclude='reverse_types',
    ...     reverse_etypes={'click': 'clicked-by', 'clicked-by': 'click'},
    ...     negative_sampler=neg_sampler,
    ...     batch_size=1024, shuffle=True, drop_last=False, num_workers=4)
    >>> for input_nodes, pos_pair_graph, neg_pair_graph, blocks in dataloader:
    ...     train_on(input_nodse, pair_graph, neg_pair_graph, blocks)

    See also
    --------
    :py:class:`~dgl.dataloading.EdgeCollator`

    For end-to-end usages, please refer to the following tutorial/examples:

    * Edge classification on heterogeneous graph: GCMC

    * Link prediction on homogeneous graph: GraphSAGE for unsupervised learning

    * Link prediction on heterogeneous graph: RGCN for link prediction.
    """
    collator_arglist = inspect.getfullargspec(EdgeCollator).args

    def __init__(self, g, eids, block_sampler, **kwargs):
        collator_kwargs = {}
        dataloader_kwargs = {}
        for k, v in kwargs.items():
            if k in self.collator_arglist:
                collator_kwargs[k] = v
            else:
                dataloader_kwargs[k] = v
        self.collator = EdgeCollator(g, eids, block_sampler, **collator_kwargs)
        super().__init__(
            self.collator.dataset, collate_fn=self.collator.collate, **dataloader_kwargs)
