from nltk.tree import Tree
from nltk.corpus.reader import BracketParseCorpusReader as CorpusReader
import networkx as nx
import torch as th

class nx_BCT_Reader:
    # Binary Constituency Tree constructor for networkx
    def __init__(self, cuda=False,
                 fnames=['trees/train.txt', 'trees/dev.txt', 'trees/test.txt']):
        # fnames must be three items which means the file path of train, validation, test set, respectively.
        self.corpus = CorpusReader('.', fnames)
        self.train = self.corpus.parsed_sents(fnames[0])
        self.dev = self.corpus.parsed_sents(fnames[1])
        self.test = self.corpus.parsed_sents(fnames[2])

        self.vocab = {}
        def _rec(node):
            for child in node:
                if isinstance(child[0], str) and child[0] not in self.vocab:
                    self.vocab[child[0]] = len(self.vocab)
                elif isinstance(child, Tree):
                    _rec(child)
        for sent in self.train:
            _rec(sent)
        self.default = len(self.vocab) + 1

        self.LongTensor = th.cuda.LongTensor if cuda else th.LongTensor
        self.FloatTensor = th.cuda.FloatTensor if cuda else th.FloatTensor

    def create_BCT(self, root):
        self.node_cnt = 0
        self.G = nx.DiGraph()
        def _rec(node, nx_node, depth=0):
            for child in node:
                node_id = str(self.node_cnt) + '_' + str(depth+1)
                self.node_cnt += 1
#               if isinstance(child[0], str) or isinstance(child[0], unicode):
                if isinstance(child[0], str):
                    word = self.LongTensor([self.vocab.get(child[0], self.default)])
                    self.G.add_node(node_id, x=word, y=None)
                else:
                    label = self.FloatTensor([[0] * 5])
                    label[0, int(child.label())] = 1
                    self.G.add_node(node_id, x=None, y=label)
                    if isinstance(child, Tree): #check illegal trees
                        _rec(child, node_id)
                self.G.add_edge(node_id, nx_node)

        self.G.add_node('0_0', x=None, y=None) # add root into nx Graph
        _rec(root, '0_0')

        return self.G

    def generator(self, mode='train'):
        assert mode in ['train', 'dev', 'test']
        for s in self.__dict__[mode]:
            yield self.create_BCT(s)
