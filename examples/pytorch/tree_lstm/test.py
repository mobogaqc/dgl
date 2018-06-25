import argparse
import torch as th
import torch.optim as optim
import nx_SST
import tree_lstm

parser = argparse.ArgumentParser()
parser.add_argument('--batch-size', type=int, default=25)
parser.add_argument('--gpu', type=int, default=0)
parser.add_argument('--h-size', type=int, default=512)
parser.add_argument('--log-every', type=int, default=1)
parser.add_argument('--lr', type=float, default=0.05)
parser.add_argument('--n-ary', type=int, default=2)
parser.add_argument('--n-iterations', type=int, default=1000)
parser.add_argument('--weight-decay', type=float, default=1e-4)
parser.add_argument('--x-size', type=int, default=256)
args = parser.parse_args()

if args.gpu < 0:
    cuda = False
else:
    cuda = True
    th.cuda.set_device(args.gpu)

reader = nx_SST.nx_BCT_Reader(cuda)
loader = reader.generator()

network = tree_lstm.NAryTreeLSTM(len(reader.vocab) + 1,
                                 args.x_size, args.h_size, args.n_ary, 5)
if cuda:
    network.cuda()
adagrad = optim.Adagrad(network.parameters(), args.lr)

for i in range(args.n_iterations):
    nll = 0
    for j in range(args.batch_size):
        g = next(loader)
        nll += network(g, train=True)
    nll /= args.batch_size

    adagrad.zero_grad()
    nll.backward()
    adagrad.step()

    if (i + 1) % args.log_every == 0:
        print('[iteration %d]cross-entropy loss: %f' % ((i + 1), nll))
