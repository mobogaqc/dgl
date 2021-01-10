.. DGL documentation master file, created by
   sphinx-quickstart on Fri Oct  5 14:18:01 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Overview of DGL
===============

Deep Graph Library (DGL) is a Python package built for easy implementation of
graph neural network model family, on top of existing DL frameworks (e.g.
PyTorch, MXNet, Gluon etc.).

DGL reduces the implementation of graph neural networks into declaring a set
of *functions* (or *modules* in PyTorch terminology).  In addition, DGL
provides:

* Versatile controls over message passing, ranging from low-level operations
  such as sending along selected edges and receiving on specific nodes, to
  high-level control such as graph-wide feature updates.
* Transparent speed optimization with automatic batching of computations and
  sparse matrix multiplication.
* Seamless integration with existing deep learning frameworks.
* Easy and friendly interfaces for node/edge feature access and graph
  structure manipulation.
* Good scalability to graphs with tens of millions of vertices.

To begin with, we have prototyped 10 models across various domains:
semi-supervised learning on graphs (with potentially billions of nodes/edges),
generative models on graphs, (previously) difficult-to-parallelize tree-based
models like TreeLSTM, etc. We also implement some conventional models in DGL
from a new graphical perspective yielding simplicity.

Getting Started
---------------

* :doc:`Installation<install/index>`.
* :doc:`Quickstart tutorial<tutorials/basics/1_first>` for absolute beginners.
* :doc:`User guide<guide/index>`.
* :doc:`用户指南(User guide)中文版<guide_cn/index>`.
* :doc:`API reference manual<api/python/index>`.
* :doc:`End-to-end model tutorials<tutorials/models/index>` for learning DGL by popular models on graphs.

..
  Follow the :doc:`instructions<install/index>` to install DGL.
  :doc:`<new-tutorial/1_introduction>` is the most common place to get started with.
  It offers a broad experience of using DGL for deep learning on graph data.

  API reference document lists more endetailed specifications of each API and GNN modules,
  a useful manual for in-depth developers.

  You can learn other basic concepts of DGL through the dedicated tutorials.

  * Learn constructing, saving and loading graphs with node and edge features :doc:`here<new-tutorial/2_dglgraph>`.
  * Learn performing computation on graph using message passing :doc:`here<new-tutorial/3_message_passing>`.
  * Learn link prediction with DGL :doc:`here<new-tutorial/4_link_predict>`.
  * Learn graph classification with DGL :doc:`here<new-tutorial/5_graph_classification>`.
  * Learn creating your own dataset for DGL :doc:`here<new-tutorial/6_load_data>`.
  * Learn working with heterogeneous graph data :doc:`here<tutorials/basics/5_hetero>`.

  End-to-end model tutorials are other good starting points for learning DGL and popular
  models on graphs. The model tutorials are categorized based on the way they utilize DGL APIs.

  * :ref:`Graph Neural Network and its variant <tutorials1-index>`: Learn how to use DGL to train
    popular **GNN models** on one input graph.
  * :ref:`Dealing with many small graphs <tutorials2-index>`: Learn how to train models for
    many graph samples such as sentence parse trees.
  * :ref:`Generative models <tutorials3-index>`: Learn how to deal with **dynamically-changing graphs**.
  * :ref:`Old (new) wines in new bottle <tutorials4-index>`: Learn how to combine DGL with tensor-based
    DGL framework in a flexible way. Explore new perspective on traditional models by graphs.
  * :ref:`Training on giant graphs <tutorials5-index>`: Learn how to train graph neural networks
    on giant graphs.

  Each tutorial is accompanied with a runnable python script and jupyter notebook that
  can be downloaded. If you would like the tutorials improved, please raise a github issue.

.. toctree::
   :maxdepth: 1
   :caption: Get Started
   :hidden:
   :glob:

   install/index
   install/backend
   new-tutorial/1_introduction

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   :hidden:
   :titlesonly:
   :glob:

   guide/graph
   guide/message
   guide/nn
   guide/data
   guide/training
   guide/minibatch
   guide/distributed

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:
   :glob:

   api/python/dgl
   api/python/dgl.data
   api/python/dgl.dataloading
   api/python/dgl.DGLGraph
   api/python/dgl.distributed
   api/python/dgl.function
   api/python/nn
   api/python/dgl.ops
   api/python/dgl.sampling
   api/python/udf

.. toctree::
   :maxdepth: 3
   :caption: Model Tutorials
   :hidden:
   :glob:

   tutorials/models/index

.. toctree::
   :maxdepth: 1
   :caption: Developer Notes
   :hidden:
   :glob:

   contribute
   developer/ffi

.. toctree::
   :maxdepth: 1
   :caption: Misc
   :hidden:
   :glob:

   faq
   env_var
   resources

Relationship of DGL to other frameworks
---------------------------------------
DGL is designed to be compatible and agnostic to the existing tensor
frameworks. It provides a backend adapter interface that allows easy porting
to other tensor-based, autograd-enabled frameworks.


Free software
-------------
DGL is free software; you can redistribute it and/or modify it under the terms
of the Apache License 2.0. We welcome contributions.
Join us on `GitHub <https://github.com/dmlc/dgl>`_ and check out our
:doc:`contribution guidelines <contribute>`.

History
-------
Prototype of DGL started in early Spring, 2018, at NYU Shanghai by Prof. `Zheng
Zhang <https://shanghai.nyu.edu/academics/faculty/directory/zheng-zhang>`_ and
Quan Gan. Serious development began when `Minjie
<https://jermainewang.github.io/>`_, `Lingfan <https://cs.nyu.edu/~lingfan/>`_
and Prof. `Jinyang Li <http://www.news.cs.nyu.edu/~jinyang/>`_ from NYU's
system group joined, flanked by a team of student volunteers at NYU Shanghai,
Fudan and other universities (Yu, Zihao, Murphy, Allen, Qipeng, Qi, Hao), as
well as early adopters at the CILVR lab (Jake Zhao). Development accelerated
when AWS MXNet Science team joined force, with Da Zheng, Alex Smola, Haibin
Lin, Chao Ma and a number of others. For full credit, see `here
<https://www.dgl.ai/ack>`_.

Index
-----
* :ref:`genindex`
