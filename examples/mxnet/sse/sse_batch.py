"""
Learning Steady-States of Iterative Algorithms over Graphs
Paper: http://proceedings.mlr.press/v80/dai18a.html

"""
import argparse
import numpy as np
import time
import math
import mxnet as mx
from mxnet import gluon
import dgl
import dgl.function as fn
from dgl import DGLGraph
from dgl.data import register_data_args, load_data

def gcn_msg(edges):
    # TODO should we use concat?
    return {'m': mx.nd.concat(edges.src['in'], edges.src['h'], dim=1)}

def gcn_reduce(nodes):
    return {'accum': mx.nd.sum(nodes.mailbox['m'], 1)}

class NodeUpdate(gluon.Block):
    def __init__(self, out_feats, activation=None, alpha=0.9, **kwargs):
        super(NodeUpdate, self).__init__(**kwargs)
        self.linear1 = gluon.nn.Dense(out_feats, activation=activation)
        # TODO what is the dimension here?
        self.linear2 = gluon.nn.Dense(out_feats)
        self.alpha = alpha

    def forward(self, nodes):
        hidden = mx.nd.concat(nodes.data['in'], nodes.data['accum'], dim=1)
        hidden = self.linear2(self.linear1(hidden))
        return {'h': nodes.data['h'] * (1 - self.alpha) + self.alpha * hidden}

class SSEUpdateHidden(gluon.Block):
    def __init__(self,
                 n_hidden,
                 activation,
                 dropout,
                 use_spmv,
                 **kwargs):
        super(SSEUpdateHidden, self).__init__(**kwargs)
        with self.name_scope():
            self.layer = NodeUpdate(n_hidden, activation)
        self.dropout = dropout
        self.use_spmv = use_spmv

    def forward(self, g, vertices):
        if self.use_spmv:
            feat = g.ndata['in']
            h = g.ndata['h']
            g.ndata['cat'] = mx.nd.concat(feat, h, dim=1)

            msg_func = fn.copy_src(src='cat', out='tmp')
            reduce_func = fn.sum(msg='tmp', out='accum')
        else:
            msg_func = gcn_msg
            reduce_func = gcn_reduce
        if vertices is None:
            g.update_all(msg_func, reduce_func, None)
            if self.use_spmv:
                g.ndata.pop('cat')
            batch_size = 100000
            num_batches = int(math.ceil(g.number_of_nodes() / batch_size))
            for i in range(num_batches):
                vs = mx.nd.arange(i * batch_size, min((i + 1) * batch_size, g.number_of_nodes()), dtype=np.int64)
                g.apply_nodes(self.layer, vs, inplace=True)
            g.ndata.pop('accum')
            ret = g.ndata['h']
        else:
            # We don't need dropout for inference.
            if self.dropout:
                # TODO here we apply dropout on all vertex representation.
                val = mx.nd.Dropout(g.ndata['h'], p=self.dropout)
                g.ndata['h'] = val
            g.pull(vertices, msg_func, reduce_func, self.layer)
            ctx = g.ndata['h'].context
            ret = mx.nd.take(g.ndata['h'], vertices.tousertensor().as_in_context(ctx))
            if self.use_spmv:
                g.ndata.pop('cat')
            g.ndata.pop('accum')
        return ret

class SSEPredict(gluon.Block):
    def __init__(self, update_hidden, out_feats, dropout, **kwargs):
        super(SSEPredict, self).__init__(**kwargs)
        with self.name_scope():
            self.linear1 = gluon.nn.Dense(out_feats, activation='relu')
            self.linear2 = gluon.nn.Dense(out_feats)
        self.update_hidden = update_hidden
        self.dropout = dropout

    def forward(self, g, vertices):
        hidden = self.update_hidden(g, vertices)
        if self.dropout:
            hidden = mx.nd.Dropout(hidden, p=self.dropout)
        return self.linear2(self.linear1(hidden))

def copy_to_gpu(subg, ctx):
    frame = subg.ndata
    for key in frame:
        subg.ndata[key] = frame[key].as_in_context(ctx)

def main(args, data):
    if isinstance(data.features, mx.nd.NDArray):
        features = data.features
    else:
        features = mx.nd.array(data.features)
    if isinstance(data.labels, mx.nd.NDArray):
        labels = data.labels
    else:
        labels = mx.nd.array(data.labels)
    train_size = len(labels) * args.train_percent
    train_vs = np.arange(train_size, dtype='int64')
    eval_vs = np.arange(train_size, len(labels), dtype='int64')
    print("train size: " + str(len(train_vs)))
    print("eval size: " + str(len(eval_vs)))
    labels = data.labels
    in_feats = features.shape[1]
    n_classes = data.num_labels
    n_edges = data.graph.number_of_edges()

    # create the SSE model
    try:
        graph = data.graph.get_graph()
    except AttributeError:
        graph = data.graph
    g = DGLGraph(graph, readonly=True)
    g.ndata['in'] = features
    g.ndata['h'] = mx.nd.random.normal(shape=(g.number_of_nodes(), args.n_hidden),
            ctx=mx.cpu(0))

    update_hidden_infer = SSEUpdateHidden(args.n_hidden, 'relu',
            args.update_dropout, args.use_spmv, prefix='sse')
    update_hidden_infer.initialize(ctx=mx.cpu(0))

    train_ctxs = []
    update_hidden_train = SSEUpdateHidden(args.n_hidden, 'relu',
            args.update_dropout, args.use_spmv, prefix='sse')
    model = SSEPredict(update_hidden_train, args.n_hidden, args.predict_dropout, prefix='app')
    if args.gpu <= 0:
        model.initialize(ctx=mx.cpu(0))
        train_ctxs.append(mx.cpu(0))
    else:
        for i in range(args.gpu):
            train_ctxs.append(mx.gpu(i))
        model.initialize(ctx=train_ctxs)

    # use optimizer
    num_batches = int(g.number_of_nodes() / args.batch_size)
    scheduler = mx.lr_scheduler.CosineScheduler(args.n_epochs * num_batches,
            args.lr * 10, 0, 0, args.lr/5)
    trainer = gluon.Trainer(model.collect_params(), 'adam', {'learning_rate': args.lr,
        'lr_scheduler': scheduler}, kvstore=mx.kv.create('device'))

    # compute vertex embedding.
    update_hidden_infer(g, None)

    # initialize graph
    dur = []
    for epoch in range(args.n_epochs):
        t0 = time.time()
        train_loss = 0
        i = 0
        for subg, seeds in dgl.sampling.NeighborSampler(g, args.batch_size, g.number_of_nodes(),
                neighbor_type='in', num_workers=args.num_parallel_subgraphs, seed_nodes=train_vs,
                shuffle=True):
            subg.copy_from_parent()

            losses = []
            if args.gpu > 0:
                ctx = mx.gpu(i % args.gpu)
                copy_to_gpu(subg, ctx)

            subg_seeds = subg.map_to_subgraph_nid(seeds)
            with mx.autograd.record():
                logits = model(subg, subg_seeds)
                batch_labels = mx.nd.array(labels[seeds.asnumpy()], ctx=logits.context)
                loss = mx.nd.softmax_cross_entropy(logits, batch_labels)
            loss.backward()
            losses.append(loss)
            i = i + 1
            if i % args.gpu == 0:
                trainer.step(len(seeds) * len(losses))
                for loss in losses:
                    train_loss += loss.asnumpy()[0]
                losses = []

        #logits = model(eval_vs)
        #eval_loss = mx.nd.softmax_cross_entropy(logits, eval_labels)
        #eval_loss = eval_loss.asnumpy()[0]
        eval_loss = 0

        # compute vertex embedding.
        infer_params = update_hidden_infer.collect_params()
        for key in infer_params:
            idx = trainer._param2idx[key]
            trainer._kvstore.pull(idx, out=infer_params[key].data())
        update_hidden_infer(g, None)

        dur.append(time.time() - t0)
        print("Epoch {:05d} | Train Loss {:.4f} | Eval Loss {:.4f} | Time(s) {:.4f} | ETputs(KTEPS) {:.2f}".format(
            epoch, train_loss, eval_loss, np.mean(dur), n_edges / np.mean(dur) / 1000))

class MXNetGraph(object):
    """A simple graph object that uses scipy matrix."""
    def __init__(self, mat):
        self._mat = mat

    def get_graph(self):
        return self._mat

    def number_of_nodes(self):
        return self._mat.shape[0]

    def number_of_edges(self):
        return mx.nd.contrib.getnnz(self._mat)

class GraphData:
    def __init__(self, csr, num_feats):
        num_edges = mx.nd.contrib.getnnz(csr).asnumpy()[0]
        edge_ids = mx.nd.arange(0, num_edges, step=1, repeat=1, dtype=np.int64)
        csr = mx.nd.sparse.csr_matrix((edge_ids, csr.indices, csr.indptr), shape=csr.shape, dtype=np.int64)
        self.graph = MXNetGraph(csr)
        self.features = mx.nd.random.normal(shape=(csr.shape[0], num_feats))
        self.labels = mx.nd.floor(mx.nd.random.normal(loc=0, scale=10, shape=(csr.shape[0])))
        self.num_labels = 10

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GCN')
    register_data_args(parser)
    parser.add_argument("--graph-file", type=str, default="",
            help="graph file")
    parser.add_argument("--num-feats", type=int, default=10,
            help="the number of features")
    parser.add_argument("--gpu", type=int, default=-1,
            help="gpu")
    parser.add_argument("--lr", type=float, default=1e-3,
            help="learning rate")
    parser.add_argument("--batch-size", type=int, default=128,
            help="number of vertices in a batch")
    parser.add_argument("--n-epochs", type=int, default=20,
            help="number of training epochs")
    parser.add_argument("--n-hidden", type=int, default=16,
            help="number of hidden gcn units")
    parser.add_argument("--warmup", type=int, default=10,
            help="number of iterations to warm up with large learning rate")
    parser.add_argument("--update-dropout", type=float, default=0.5,
            help="the dropout rate for updating vertex embedding")
    parser.add_argument("--predict-dropout", type=float, default=0.5,
            help="the dropout rate for prediction")
    parser.add_argument("--train_percent", type=float, default=0.5,
            help="the percentage of data used for training")
    parser.add_argument("--use-spmv", type=bool, default=False,
            help="use SpMV for faster speed.")
    parser.add_argument("--num-parallel-subgraphs", type=int, default=1,
            help="the number of subgraphs to construct in parallel.")
    args = parser.parse_args()

    # load and preprocess dataset
    if args.graph_file != '':
        csr = mx.nd.load(args.graph_file)[0]
        data = GraphData(csr, args.num_feats)
        csr = None
    else:
        data = load_data(args)
    main(args, data)
