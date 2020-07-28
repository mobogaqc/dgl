import dgl
import unittest
import os
from dgl.data import CitationGraphDataset
from dgl.distributed import sample_neighbors
from dgl.distributed import partition_graph, load_partition, load_partition_book
import sys
import multiprocessing as mp
import numpy as np
import time
from utils import get_local_usable_addr
from pathlib import Path
from dgl.distributed import DistGraphServer, DistGraph, DistDataLoader
import pytest


class NeighborSampler(object):
    def __init__(self, g, fanouts, sample_neighbors):
        self.g = g
        self.fanouts = fanouts
        self.sample_neighbors = sample_neighbors

    def sample_blocks(self, seeds):
        import torch as th
        seeds = th.LongTensor(np.asarray(seeds))
        blocks = []
        for fanout in self.fanouts:
            # For each seed node, sample ``fanout`` neighbors.
            frontier = self.sample_neighbors(self.g, seeds, fanout, replace=True)
            # Then we compact the frontier into a bipartite graph for message passing.
            block = dgl.to_block(frontier, seeds)
            # Obtain the seed nodes for next layer.
            seeds = block.srcdata[dgl.NID]

            blocks.insert(0, block)
        return blocks

def start_server(rank, tmpdir, disable_shared_mem, num_clients):
    import dgl
    print('server: #clients=' + str(num_clients))
    g = DistGraphServer(rank, "mp_ip_config.txt", num_clients,
                        tmpdir / 'test_sampling.json', disable_shared_mem=disable_shared_mem)
    g.start()


def start_client(rank, tmpdir, disable_shared_mem, num_workers):
    import dgl
    import torch as th
    os.environ['DGL_DIST_MODE'] = 'distributed'
    dgl.distributed.init_rpc("mp_ip_config.txt", num_workers=4)
    gpb = None
    if disable_shared_mem:
        _, _, _, gpb, _ = load_partition(tmpdir / 'test_sampling.json', rank)
    train_nid = th.arange(202)
    dist_graph = DistGraph("mp_ip_config.txt", "test_mp", gpb=gpb)

    # Create sampler
    sampler = NeighborSampler(dist_graph, [5, 10],
                              dgl.distributed.sample_neighbors)

    # Create PyTorch DataLoader for constructing blocks
    dataloader = DistDataLoader(
        dataset=train_nid.numpy(),
        batch_size=32,
        collate_fn=sampler.sample_blocks,
        shuffle=True,
        drop_last=False,
        num_workers=4) 
    
    dist_graph._init()
    for epoch in range(3):
        for idx, blocks in enumerate(dataloader):
            print(blocks)
            print(blocks[1].edges())
            print(idx)

    dataloader.close()
    dgl.distributed.exit_client()

def main(tmpdir, num_server):
    ip_config = open("mp_ip_config.txt", "w")
    for _ in range(num_server):
        ip_config.write('{} 1\n'.format(get_local_usable_addr()))
    ip_config.close()

    g = CitationGraphDataset("cora")[0]
    g.readonly()
    print(g.idtype)
    num_parts = num_server
    num_hops = 1

    partition_graph(g, 'test_sampling', num_parts, tmpdir,
                    num_hops=num_hops, part_method='metis', reshuffle=False)

    num_workers = 4
    pserver_list = []
    ctx = mp.get_context('spawn')
    for i in range(num_server):
        p = ctx.Process(target=start_server, args=(
            i, tmpdir, num_server > 1, num_workers+1))
        p.start()
        time.sleep(1)
        pserver_list.append(p)

    time.sleep(3)
    sampled_graph = start_client(0, tmpdir, num_server > 1, num_workers)
    for p in pserver_list:
        p.join()

# Wait non shared memory graph store
@unittest.skipIf(os.name == 'nt', reason='Do not support windows yet')
@unittest.skipIf(dgl.backend.backend_name == 'tensorflow', reason='Not support tensorflow for now')
def test_dist_dataloader(tmpdir):
    main(Path(tmpdir), 3)

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdirname:
        main(Path(tmpdirname), 3)
