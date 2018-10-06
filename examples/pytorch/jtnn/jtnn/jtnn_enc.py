import torch
import torch.nn as nn
from collections import deque
from .mol_tree import Vocab
from .nnutils import GRUUpdate, cuda
import itertools
import networkx as nx
from dgl import batch, unbatch, line_graph
import dgl.function as DGLF
from .line_profiler_integration import profile

MAX_NB = 8

def level_order(forest, roots):
    '''
    Given the forest and the list of root nodes,
    returns iterator of list of edges ordered by depth, first in bottom-up
    and then top-down
    '''
    edge_list = []
    node_depth = {}

    edge_list.append([])

    for root in roots:
        node_depth[root] = 0
        for u, v in nx.bfs_edges(forest, root):
            node_depth[v] = node_depth[u] + 1
            if len(edge_list) == node_depth[u]:
                edge_list.append([])
            edge_list[node_depth[u]].append((u, v))

    for edges in reversed(edge_list):
        u, v = zip(*edges)
        yield v, u
    for edges in edge_list:
        u, v = zip(*edges)
        yield u, v


enc_tree_msg = [DGLF.copy_src(src='m', out='m'), DGLF.copy_src(src='rm', out='rm')]
enc_tree_reduce = [DGLF.sum(msgs='m', out='s'), DGLF.sum(msgs='rm', out='accum_rm')]
enc_tree_gather_msg = DGLF.copy_edge(edge='m', out='m')
enc_tree_gather_reduce = DGLF.sum(msgs='m', out='m')

class EncoderGatherUpdate(nn.Module):
    def __init__(self, hidden_size):
        nn.Module.__init__(self)
        self.hidden_size = hidden_size

        self.W = nn.Linear(2 * hidden_size, hidden_size)

    def forward(self, node):
        x = node['x']
        m = node['m']
        return {
            'h': torch.relu(self.W(torch.cat([x, m], 1))),
        }


class DGLJTNNEncoder(nn.Module):
    def __init__(self, vocab, hidden_size, embedding=None):
        nn.Module.__init__(self)
        self.hidden_size = hidden_size
        self.vocab_size = vocab.size()
        self.vocab = vocab
        
        if embedding is None:
            self.embedding = nn.Embedding(self.vocab_size, hidden_size)
        else:
            self.embedding = embedding

        self.enc_tree_update = GRUUpdate(hidden_size)
        self.enc_tree_gather_update = EncoderGatherUpdate(hidden_size)

    @profile
    def forward(self, mol_trees):
        mol_tree_batch = batch(mol_trees)
        
        # Build line graph to prepare for belief propagation
        mol_tree_batch_lg = line_graph(mol_tree_batch, no_backtracking=True)

        return self.run(mol_tree_batch, mol_tree_batch_lg)

    @profile
    def run(self, mol_tree_batch, mol_tree_batch_lg):
        # Since tree roots are designated to 0.  In the batched graph we can
        # simply find the corresponding node ID by looking at node_offset
        root_ids = mol_tree_batch.node_offset[:-1]
        n_nodes = len(mol_tree_batch.nodes)
        edge_list = mol_tree_batch.edge_list
        n_edges = len(edge_list)

        # Assign structure embeddings to tree nodes
        mol_tree_batch.set_n_repr({
            'x': self.embedding(mol_tree_batch.get_n_repr()['wid']),
            'h': cuda(torch.zeros(n_nodes, self.hidden_size)),
        })

        # Initialize the intermediate variables according to Eq (4)-(8).
        # Also initialize the src_x and dst_x fields.
        # TODO: context?
        mol_tree_batch.set_e_repr({
            's': cuda(torch.zeros(n_edges, self.hidden_size)),
            'm': cuda(torch.zeros(n_edges, self.hidden_size)),
            'r': cuda(torch.zeros(n_edges, self.hidden_size)),
            'z': cuda(torch.zeros(n_edges, self.hidden_size)),
            'src_x': cuda(torch.zeros(n_edges, self.hidden_size)),
            'dst_x': cuda(torch.zeros(n_edges, self.hidden_size)),
            'rm': cuda(torch.zeros(n_edges, self.hidden_size)),
            'accum_rm': cuda(torch.zeros(n_edges, self.hidden_size)),
        })

        # Send the source/destination node features to edges
        mol_tree_batch.update_edge(
            #*zip(*edge_list),
            edge_func=lambda src, dst, edge: {'src_x': src['x'], 'dst_x': dst['x']},
            batchable=True,
        )

        # Message passing
        # I exploited the fact that the reduce function is a sum of incoming
        # messages, and the uncomputed messages are zero vectors.  Essentially,
        # we can always compute s_ij as the sum of incoming m_ij, no matter
        # if m_ij is actually computed or not.
        for u, v in level_order(mol_tree_batch, root_ids):
            eid = mol_tree_batch.get_edge_id(u, v)
            mol_tree_batch_lg.pull(
                eid,
                enc_tree_msg,
                enc_tree_reduce,
                self.enc_tree_update,
                batchable=True,
            )

        # Readout
        mol_tree_batch.update_all(
            enc_tree_gather_msg,
            enc_tree_gather_reduce,
            self.enc_tree_gather_update,
            batchable=True,
        )

        root_vecs = mol_tree_batch.get_n_repr(root_ids)['h']

        return mol_tree_batch, root_vecs
