DGLBACKEND=mxnet python3 gcn_ns_sampler.py --ip 127.0.0.1 --port 2049 --num-sender=5 --dataset reddit-self-loop --num-neighbors 2 --batch-size 1000 --test-batch-size 500
