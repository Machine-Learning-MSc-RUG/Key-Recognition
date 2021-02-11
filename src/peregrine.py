from key_recognition import run_key_recognition
from argparse import Namespace, ArgumentParser
from tabulate import tabulate
import numpy as np
import multiprocessing 

# Function to run on 1 fold
def run_fold(fold, args):
    print(f"[Split {fold}]")
    error, results_table, confusion_matrix = run_key_recognition(\
        args, verbose=True, test_split_index=fold)
    print("Overall error: %5.2f%%" % (error*100))
    if args.table:
        print(tabulate(results_table,\
            headers=["Song ID", "Label key","Predicted key"]))
        print(confusion_matrix)
    if args.csv is not False:
        filename = 'logs/n_components={},n_iter={},fold={}.csv'\
            .format(args.n_components, args.n_iter, fold)
        np.savetxt(filename, confusion_matrix)

if __name__ == '__main__':
    # Get hyperargs
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--n_components', default=3, type=int, help='''
        Amount of components ('hidden states') to use for HMM training.
        ''')
    arg_parser.add_argument('--n_iter', default=100, type=int, help='''
        (Maximum) amount of iterations used in HMM training.
        ''')
    arg_parser.add_argument('--subset', default=1000, type=int, help='''
        Samples to use.
        ''')
    arg_parser.add_argument('--min_conf', default=0, type=int, help='''
        Minimum confidence level for the predicted key of the samples in the 
        data.Expressed in a percentage integer, i.e. between 0 and 100.
        ''')
    hyperargs = arg_parser.parse_args()

    # Get args - manually create Namespace object
    args = Namespace()
    args.data_dir = 'dataset'
    args.dry = False
    args.table = False
    args.verbose = True
    args.give_mode = True
    args.method = 'hmm'
    args.mixture = False
    args.cross_validation = True
    args.test_split = 10
    args.n_components = hyperargs.n_components
    args.n_iter = hyperargs.n_iter
    args.subset = hyperargs.subset
    args.min_conf = hyperargs.min_conf
    args.csv = True

    # Run k-fold CV in parallel
    print(f"Running {args.test_split}-fold CV in parallel.")
    print(f"[n_components={args.n_components}, n_iter={args.n_iter}]")
    cpus = multiprocessing.cpu_count()
    processes = cpus if cpus < 10 else 10
    pool = multiprocessing.Pool(processes=processes,)
    run_fold_args = [(fold, args) for fold in range(args.test_split)]
    pool.starmap(run_fold, run_fold_args)
    pool.close()
    pool.join()
    print('Done!')