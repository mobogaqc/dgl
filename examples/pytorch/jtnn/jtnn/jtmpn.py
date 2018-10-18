import torch
import torch.nn as nn
from .nnutils import cuda
from .chemutils import get_mol
#from mpn import atom_features, bond_features, ATOM_FDIM, BOND_FDIM
import rdkit.Chem as Chem
from dgl import DGLGraph, line_graph, batch, unbatch
import dgl.function as DGLF
from .line_profiler_integration import profile
import os

ELEM_LIST = ['C', 'N', 'O', 'S', 'F', 'Si', 'P', 'Cl', 'Br', 'Mg', 'Na', 'Ca', 'Fe', 'Al', 'I', 'B', 'K', 'Se', 'Zn', 'H', 'Cu', 'Mn', 'unknown']

ATOM_FDIM = len(ELEM_LIST) + 6 + 5 + 1
BOND_FDIM = 5 
MAX_NB = 10

PAPER = os.getenv('PAPER', False)

def onek_encoding_unk(x, allowable_set):
    if x not in allowable_set:
        x = allowable_set[-1]
    return [x == s for s in allowable_set]

# Note that during graph decoding they don't predict stereochemistry-related
# characteristics (i.e. Chiral Atoms, E-Z, Cis-Trans).  Instead, they decode
# the 2-D graph first, then enumerate all possible 3-D forms and find the
# one with highest score.
def atom_features(atom):
    return cuda(torch.Tensor(onek_encoding_unk(atom.GetSymbol(), ELEM_LIST) 
            + onek_encoding_unk(atom.GetDegree(), [0,1,2,3,4,5]) 
            + onek_encoding_unk(atom.GetFormalCharge(), [-1,-2,1,2,0])
            + [atom.GetIsAromatic()]))

def bond_features(bond):
    bt = bond.GetBondType()
    return cuda(torch.Tensor([bt == Chem.rdchem.BondType.SINGLE, bt == Chem.rdchem.BondType.DOUBLE, bt == Chem.rdchem.BondType.TRIPLE, bt == Chem.rdchem.BondType.AROMATIC, bond.IsInRing()]))


@profile
def mol2dgl(cand_batch, mol_tree_batch):
    cand_graphs = []
    tree_mess_source_edges = [] # map these edges from trees to...
    tree_mess_target_edges = [] # these edges on candidate graphs
    tree_mess_target_nodes = []
    n_nodes = 0

    for mol, mol_tree, ctr_node_id in cand_batch:
        atom_feature_list = []
        bond_feature_list = []
        ctr_node = mol_tree.nodes[ctr_node_id]
        ctr_bid = ctr_node['idx']
        g = DGLGraph()

        for atom in mol.GetAtoms():
            atom_feature_list.append(atom_features(atom))
            g.add_node(atom.GetIdx())

        for bond in mol.GetBonds():
            a1 = bond.GetBeginAtom()
            a2 = bond.GetEndAtom()
            begin_idx = a1.GetIdx()
            end_idx = a2.GetIdx()
            features = bond_features(bond)

            g.add_edge(begin_idx, end_idx)
            bond_feature_list.append(features)
            g.add_edge(end_idx, begin_idx)
            bond_feature_list.append(features)

            x_nid, y_nid = a1.GetAtomMapNum(), a2.GetAtomMapNum()
            # Tree node ID in the batch
            x_bid = mol_tree.nodes[x_nid - 1]['idx'] if x_nid > 0 else -1
            y_bid = mol_tree.nodes[y_nid - 1]['idx'] if y_nid > 0 else -1
            if x_bid >= 0 and y_bid >= 0 and x_bid != y_bid:
                if (x_bid, y_bid) in mol_tree_batch.edge_list:
                    tree_mess_target_edges.append(
                            (begin_idx + n_nodes, end_idx + n_nodes))
                    tree_mess_source_edges.append((x_bid, y_bid))
                    tree_mess_target_nodes.append(end_idx + n_nodes)
                if (y_bid, x_bid) in mol_tree_batch.edge_list:
                    tree_mess_target_edges.append(
                            (end_idx + n_nodes, begin_idx + n_nodes))
                    tree_mess_source_edges.append((y_bid, x_bid))
                    tree_mess_target_nodes.append(begin_idx + n_nodes)

        n_nodes += len(g.nodes)

        atom_x = torch.stack(atom_feature_list)
        g.set_n_repr({'x': atom_x})
        if len(bond_feature_list) > 0:
            bond_x = torch.stack(bond_feature_list)
            g.set_e_repr({
                'x': bond_x,
                'src_x': atom_x.new(len(bond_feature_list), ATOM_FDIM).zero_()
            })
        cand_graphs.append(g)

    return cand_graphs, tree_mess_source_edges, tree_mess_target_edges, \
           tree_mess_target_nodes


mpn_loopy_bp_msg = DGLF.copy_src(src='msg', out='msg')
mpn_loopy_bp_reduce = DGLF.sum(msgs='msg', out='accum_msg')


class LoopyBPUpdate(nn.Module):
    def __init__(self, hidden_size):
        super(LoopyBPUpdate, self).__init__()
        self.hidden_size = hidden_size

        self.W_h = nn.Linear(hidden_size, hidden_size, bias=False)

    def forward(self, node):
        msg_input = node['msg_input']
        msg_delta = self.W_h(node['accum_msg'] + node['alpha'])
        msg = torch.relu(msg_input + msg_delta)
        return {'msg': msg}


if PAPER:
    mpn_gather_msg = [
        DGLF.copy_edge(edge='msg', out='msg'),
        DGLF.copy_edge(edge='alpha', out='alpha')
    ]
else:
    mpn_gather_msg = DGLF.copy_edge(edge='msg', out='msg')


if PAPER:
    mpn_gather_reduce = [
        DGLF.sum(msgs='msg', out='m'),
        DGLF.sum(msgs='alpha', out='accum_alpha'),
    ]
else:
    mpn_gather_reduce = DGLF.sum(msgs='msg', out='m')


class GatherUpdate(nn.Module):
    def __init__(self, hidden_size):
        super(GatherUpdate, self).__init__()
        self.hidden_size = hidden_size

        self.W_o = nn.Linear(ATOM_FDIM + hidden_size, hidden_size)

    def forward(self, node):
        if PAPER:
            #m = node['m']
            m = node['m'] + node['accum_alpha']
        else:
            m = node['m'] + node['alpha']
        return {
            'h': torch.relu(self.W_o(torch.cat([node['x'], m], 1))),
        }


class DGLJTMPN(nn.Module):
    def __init__(self, hidden_size, depth):
        nn.Module.__init__(self)

        self.depth = depth

        self.W_i = nn.Linear(ATOM_FDIM + BOND_FDIM, hidden_size, bias=False)

        self.loopy_bp_updater = LoopyBPUpdate(hidden_size)
        self.gather_updater = GatherUpdate(hidden_size)
        self.hidden_size = hidden_size

        self.n_samples_total = 0
        self.n_nodes_total = 0
        self.n_edges_total = 0
        self.n_passes = 0

    @profile
    def forward(self, cand_batch, mol_tree_batch):
        cand_graphs, tree_mess_src_edges, tree_mess_tgt_edges, tree_mess_tgt_nodes = \
                mol2dgl(cand_batch, mol_tree_batch)

        n_samples = len(cand_graphs)

        cand_graphs = batch(cand_graphs)
        cand_line_graph = line_graph(cand_graphs, no_backtracking=True)

        n_nodes = len(cand_graphs.nodes)
        n_edges = len(cand_graphs.edges)

        cand_graphs = self.run(
                cand_graphs, cand_line_graph, tree_mess_src_edges, tree_mess_tgt_edges,
                tree_mess_tgt_nodes, mol_tree_batch)

        cand_graphs = unbatch(cand_graphs)
        g_repr = torch.stack([g.get_n_repr()['h'].mean(0) for g in cand_graphs], 0)

        self.n_samples_total += n_samples
        self.n_nodes_total += n_nodes
        self.n_edges_total += n_edges
        self.n_passes += 1

        return g_repr

    @profile
    def run(self, cand_graphs, cand_line_graph, tree_mess_src_edges, tree_mess_tgt_edges,
            tree_mess_tgt_nodes, mol_tree_batch):
        n_nodes = len(cand_graphs.nodes)

        cand_graphs.update_edge(
            #*zip(*cand_graphs.edge_list),
            edge_func=lambda src, dst, edge: {'src_x': src['x']},
            batchable=True,
        )

        bond_features = cand_line_graph.get_n_repr()['x']
        source_features = cand_line_graph.get_n_repr()['src_x']
        features = torch.cat([source_features, bond_features], 1)
        msg_input = self.W_i(features)
        cand_line_graph.set_n_repr({
            'msg_input': msg_input,
            'msg': torch.relu(msg_input),
            'accum_msg': torch.zeros_like(msg_input),
        })
        zero_node_state = bond_features.new(n_nodes, self.hidden_size).zero_()
        cand_graphs.set_n_repr({
            'm': zero_node_state.clone(),
            'h': zero_node_state.clone(),
        })

        if PAPER:
            cand_graphs.set_e_repr({
                'alpha': cuda(torch.zeros(len(cand_graphs.edge_list), self.hidden_size))
            })

            alpha = mol_tree_batch.get_e_repr(*zip(*tree_mess_src_edges))['m']
            cand_graphs.set_e_repr({'alpha': alpha}, *zip(*tree_mess_tgt_edges))
        else:
            alpha = mol_tree_batch.get_e_repr(*zip(*tree_mess_src_edges))['m']
            node_idx = (torch.LongTensor(tree_mess_tgt_nodes)
                        .to(device=zero_node_state.device)[:, None]
                        .expand_as(alpha))
            node_alpha = zero_node_state.clone().scatter_add(0, node_idx, alpha)
            cand_graphs.set_n_repr({'alpha': node_alpha})
            cand_graphs.update_edge(
                #*zip(*cand_graphs.edge_list),
                edge_func=lambda src, dst, edge: {'alpha': src['alpha']},
                batchable=True,
            )

        for i in range(self.depth - 1):
            cand_line_graph.update_all(
                mpn_loopy_bp_msg,
                mpn_loopy_bp_reduce,
                self.loopy_bp_updater,
                True
            )

        cand_graphs.update_all(
            mpn_gather_msg,
            mpn_gather_reduce,
            self.gather_updater,
            True
        )

        return cand_graphs
