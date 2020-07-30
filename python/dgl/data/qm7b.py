from scipy import io
import numpy as np
import os

from .utils import get_download_dir, download
from ..utils import retry_method_with_fix
from .. import convert

class QM7b(object):
    """
    This dataset consists of 7,211 molecules with 14 regression targets.
    Nodes means atoms and edges means bonds. Edge data 'h' means 
    the entry of Coulomb matrix.

    Reference:
    - `QM7b Dataset <http://quantum-machine.org/datasets/>`_

    """
    _url = 'http://deepchem.io.s3-website-us-west-1.amazonaws.com/' \
        'datasets/qm7b.mat'

    def __init__(self):
        self.dir = get_download_dir()
        self.path = os.path.join(self.dir, 'qm7b', "qm7b.mat")
        self.graphs = []
        self._load(self.path)

    def _download(self):
        download(self._url, path=self.path)

    @retry_method_with_fix(_download)
    def _load(self, filename):
        data = io.loadmat(self.path)
        labels = data['T']
        feats = data['X']
        num_graphs = labels.shape[0]
        self.label = labels
        for i in range(num_graphs):
            edge_list = feats[i].nonzero()
            g = convert.graph(edge_list)
            g.edata['h'] = feats[i][edge_list[0], edge_list[1]].reshape(-1, 1)
            self.graphs.append(g)
        
    def __getitem__(self, idx):
        return self.graphs[idx], self.label[idx]
    
    def __len__(self):
        return len(self.graphs)
