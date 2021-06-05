import torch
import os
import numpy as np
import pandas as pd
import scipy.sparse as sp

from .dgl_dataset import DGLBuiltinDataset
from .utils import save_graphs, load_graphs, _get_dgl_url
from .utils import save_info, load_info
from ..convert import graph


class FakeNewsDataset(DGLBuiltinDataset):
    r"""Fake News Graph Classification dataset.

    The dataset is composed of two sets of tree-structured fake/real
    news propagation graphs extracted from Twitter. Different from
    most of the benchmark datasets for the graph classification task,
    the graphs in this dataset are directed tree-structured graphs where
    the root node represents the news, the leaf nodes are Twitter users
    who retweeted the root news. Besides, the node features are encoded
    user historical tweets using different pretrained language models:
        bert: the 768-dimensional node feature composed of Twitter user
              historical tweets encoded by the bert-as-service
        content: the 310-dimensional node feature composed of a
                 300-dimensional “spacy” vector plus a 10-dimensional
                 “profile” vector
        profile: the 10-dimensional node feature composed of ten Twitter
                 user profile attributes.
        spacy: the 300-dimensional node feature composed of Twitter user
               historical tweets encoded by the spaCy word2vec encoder.

    Statistics:

        Politifact:

        - Graphs: 314
        - Nodes: 41,054
        - Edges: 40,740
        - Classes:
            Fake: 157
            Real: 157
        - Node feature size:
            bert: 768
            content: 310
            profile: 10
            spacy: 300

        Gossipcop:

        - Graphs: 5464
        - Nodes: 314,262
        - Edges: 308,798
        - Classes:
            Fake: 2732
            Real: 2732
        - Node feature size:
            bert: 768
            content: 310
            profile: 10
            spacy: 300

    Parameters
    ----------
    name : str
        Name of the dataset (gossipcop, or politifact)
    feature_name : str
        Name of the feature (bert, content, profile, or spacy)
    raw_dir : str
        Specifying the directory that will store the
        downloaded data or the directory that
        already stores the input data.
        Default: ~/.dgl/

    Attributes
    ----------
    name : str
        Name of the dataset (gossipcop, or politifact)
    num_classes : int
        Number of label classes
    num_graphs : int
        Number of graphs
    graphs : list
        A list of DGLGraph objects
    labels : Tensor
        Graph labels
    feature_name : str
        Name of the feature (bert, content, profile, or spacy)
    feature : scipy.sparse.csr.csr_matrix
        Node features
    train_mask : Tensor
        Mask of training set
    val_mask : Tensor
        Mask of validation set
    test_mask : Tensor
        Mask of testing set

    Examples
    --------
    >>> dataset = FakeNewsDataset('gossipcop', 'bert')
    >>> graph, label = dataset[0]
    >>> num_classes = dataset.num_classes
    >>> feat = dataset.feature
    >>> labels = dataset.labels
    """
    file_urls = {
        'gossipcop': 'dataset/FakeNewsGOS.zip',
        'politifact': 'dataset/FakeNewsPOL.zip'
    }

    def __init__(self, name, feature_name, raw_dir=None):
        assert name in ['gossipcop', 'politifact'], \
            "Only supports 'gossipcop' or 'politifact'."
        url = _get_dgl_url(self.file_urls[name])

        assert feature_name in ['bert', 'content', 'profile', 'spacy'], \
            "Only supports 'bert', 'content', 'profile', or 'spacy'"
        self.feature_name = feature_name
        super(FakeNewsDataset, self).__init__(name=name,
                                              url=url,
                                              raw_dir=raw_dir)

    def process(self):
        """process raw data to graph, labels and masks"""
        self.labels = np.load(os.path.join(self.raw_path, 'graph_labels.npy'))
        self.labels = torch.LongTensor(self.labels)
        num_graphs = self.labels.shape[0]

        node_graph_id = np.load(os.path.join(self.raw_path, 'node_graph_id.npy'))
        edges = pd.read_csv(os.path.join(self.raw_path, 'A.txt'), header=None)
        src = edges[0].to_numpy()
        dst = edges[1].to_numpy()
        g = graph((src, dst))

        node_idx_list = []
        for idx in range(np.max(node_graph_id) + 1):
            node_idx = np.where(node_graph_id == idx)
            node_idx_list.append(node_idx[0])

        self.graphs = [g.subgraph(node_idx) for node_idx in node_idx_list]

        train_idx = np.load(os.path.join(self.raw_path, 'train_idx.npy'))
        val_idx = np.load(os.path.join(self.raw_path, 'val_idx.npy'))
        test_idx = np.load(os.path.join(self.raw_path, 'test_idx.npy'))
        train_mask = torch.zeros(num_graphs, dtype=torch.bool)
        val_mask = torch.zeros(num_graphs, dtype=torch.bool)
        test_mask = torch.zeros(num_graphs, dtype=torch.bool)
        train_mask[train_idx] = True
        val_mask[val_idx] = True
        test_mask[test_idx] = True
        self.train_mask = train_mask
        self.val_mask = val_mask
        self.test_mask = test_mask

        feature_file = 'new_' + self.feature_name + '_feature.npz'
        self.feature = sp.load_npz(os.path.join(self.raw_path, feature_file))

    def save(self):
        """save the graph list and the labels"""
        graph_path = os.path.join(self.save_path, self.name + '_dgl_graph.bin')
        info_path = os.path.join(self.save_path, self.name + '_dgl_graph.pkl')
        save_graphs(str(graph_path), self.graphs)
        save_info(info_path, {'label': self.labels,
                              'feature': self.feature,
                              'train_mask': self.train_mask,
                              'val_mask': self.val_mask,
                              'test_mask': self.train_mask})

    def has_cache(self):
        """ check whether there are processed data in `self.save_path` """
        graph_path = os.path.join(self.save_path, self.name + '_dgl_graph.bin')
        info_path = os.path.join(self.save_path, self.name + '_dgl_graph.pkl')
        return os.path.exists(graph_path) and os.path.exists(info_path)

    def load(self):
        """load processed data from directory `self.save_path`"""
        graph_path = os.path.join(self.save_path, self.name + '_dgl_graph.bin')
        info_path = os.path.join(self.save_path, self.name + '_dgl_graph.pkl')

        graphs, _ = load_graphs(str(graph_path))
        info = load_info(str(info_path))
        self.graphs = graphs
        self.labels = info['label']
        self.feature = info['feature']

        self.train_mask = info['train_mask']
        self.val_mask = info['val_mask']
        self.test_mask = info['test_mask']

    @property
    def num_classes(self):
        """Number of classes for each graph, i.e. number of prediction tasks."""
        return 2

    @property
    def num_graphs(self):
        """Number of graphs."""
        return self.labels.shape[0]

    def __getitem__(self, i):
        r""" Get graph and label by index

        Parameters
        ----------
        i : int
            Item index

        Returns
        -------
        (:class:`dgl.DGLGraph`, Tensor)
        """
        return self.graphs[i], self.labels[i]

    def __len__(self):
        r"""Number of graphs in the dataset.

        Return
        -------
        int
        """
        return len(self.graphs)
