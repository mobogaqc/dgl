"""
Semi-Supervised Classification with Graph Convolutional Networks
Paper: https://arxiv.org/abs/1609.02907
Code: https://github.com/tkipf/gcn
"""
import argparse
import numpy as np
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from dgl import DGLGraph
from dgl.data import load_cora, load_citeseer, load_pubmed

def gcn_msg(src, edge):
    return src['h']

def gcn_reduce(node, msgs):
    return sum(msgs)

class NodeUpdateModule(nn.Module):
    def __init__(self, in_feats, out_feats, activation=None):
        super(NodeUpdateModule, self).__init__()
        self.linear = nn.Linear(in_feats, out_feats)
        self.activation = activation

    def forward(self, node, accum):
        h = self.linear(accum)
        if self.activation:
            h = self.activation(h)
        return {'h' : h}

class GCN(nn.Module):
    def __init__(self,
                 nx_graph,
                 in_feats,
                 n_hidden,
                 n_classes,
                 n_layers,
                 activation,
                 dropout):
        super(GCN, self).__init__()
        self.g = DGLGraph(nx_graph)
        self.dropout = dropout
        # input layer
        self.layers = nn.ModuleList([NodeUpdateModule(in_feats, n_hidden, activation)])
        # hidden layers
        for i in range(n_layers - 1):
            self.layers.append(NodeUpdateModule(n_hidden, n_hidden, activation))
        # output layer
        self.layers.append(NodeUpdateModule(n_hidden, n_classes))

    def forward(self, features, train_nodes):
        for n, feat in features.items():
            self.g.nodes[n]['h'] = feat
        for layer in self.layers:
            # apply dropout
            if self.dropout:
                self.g.nodes[n]['h'] = F.dropout(g.nodes[n]['h'], p=self.dropout)
            self.g.update_all(gcn_msg, gcn_reduce, layer)
        return torch.cat([self.g.nodes[n]['h'] for n in train_nodes])

def main(args):
    # load and preprocess dataset
    if args.dataset == 'cora':
        data = load_cora()
    elif args.dataset == 'citeseer':
        data = load_citeseer()
    elif args.dataset == 'pubmed':
        data = load_pubmed()
    else:
        raise RuntimeError('Error dataset: {}'.format(args.dataset))

    # features of each samples
    features = {}
    labels = []
    train_nodes = []
    for n in data.graph.nodes():
        features[n] = torch.FloatTensor(data.features[n, :])
        if data.train_mask[n] == 1:
            train_nodes.append(n)
            labels.append(data.labels[n])
    labels = torch.LongTensor(labels)
    in_feats = data.features.shape[1]
    n_classes = data.num_labels
    n_edges = data.graph.number_of_edges()

    if args.gpu < 0:
        cuda = False
    else:
        cuda = True
        torch.cuda.set_device(args.gpu)
        features = features.cuda()
        labels = labels.cuda()
        mask = mask.cuda()

    # create GCN model
    model = GCN(data.graph,
                in_feats,
                args.n_hidden,
                n_classes,
                args.n_layers,
                F.relu,
                args.dropout)

    if cuda:
        model.cuda()

    # use optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # initialize graph
    dur = []
    for epoch in range(args.n_epochs):
        if epoch >= 3:
            t0 = time.time()
        # forward
        logits = model(features, train_nodes)
        logp = F.log_softmax(logits, 1)
        loss = F.nll_loss(logp, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch >= 3:
            dur.append(time.time() - t0)

        print("Epoch {:05d} | Loss {:.4f} | Time(s) {:.4f} | ETputs(KTEPS) {:.2f}".format(
            epoch, loss.item(), np.mean(dur), n_edges / np.mean(dur) / 1000))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GCN')
    parser.add_argument("--dataset", type=str, required=True,
            help="dataset")
    parser.add_argument("--dropout", type=float, default=0,
            help="dropout probability")
    parser.add_argument("--gpu", type=int, default=-1,
            help="gpu")
    parser.add_argument("--lr", type=float, default=1e-3,
            help="learning rate")
    parser.add_argument("--n-epochs", type=int, default=20,
            help="number of training epochs")
    parser.add_argument("--n-hidden", type=int, default=16,
            help="number of hidden gcn units")
    parser.add_argument("--n-layers", type=int, default=1,
            help="number of hidden gcn layers")
    args = parser.parse_args()
    print(args)

    main(args)
