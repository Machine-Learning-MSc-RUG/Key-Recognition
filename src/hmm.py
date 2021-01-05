from argparse import ArgumentParser
from meta import Meta
from data import load_analysis
import numpy as np
from hmmlearn import hmm
from tabulate import tabulate
import pickle
import copy

key_nums = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
modes = ["Minor", "Major"]

def format_sequence(audio_analysis):
    num_segments = len(audio_analysis["segments"])
    seq = np.zeros((num_segments, 12))
    i = 0
    for segment in audio_analysis["segments"]:
        seq[i,:] = segment["pitches"]
        i += 1
    return seq

def run_hmm_method_all_tracks(data_dir, test_split=0.2):
    ''' Trains the HMM 
    '''

    meta = Meta.load(data_dir)
    all_tracks = meta.get_track_ids()
    n = len(all_tracks)
    print(f"N={n}")
    train_n = int(n*(1-test_split))

    print("Collecting training data...")
    minor_sequences        = np.zeros((0,12))
    minor_sequence_lengths = []
    major_sequences        = np.zeros((0,12))
    major_sequence_lengths = []
    for track_id in all_tracks[:train_n]:
        analysis = load_analysis(data_dir, track_id)
        
        # Format sequence
        seq = format_sequence(analysis)
        seq = np.roll(seq, -analysis["key"])
        
        # Add sequence to set of all sequences within mode
        if analysis["mode"] == 1:
            major_sequences = np.concatenate((major_sequences, seq))
            major_sequence_lengths.append(seq.shape[0])
        else:
            minor_sequences = np.concatenate((minor_sequences, seq))
            minor_sequence_lengths.append(seq.shape[0])

    minor_sequence_lengths = np.array(minor_sequence_lengths)
    major_sequence_lengths = np.array(major_sequence_lengths)
    
    model_minor = hmm.GaussianHMM(n_components=args.hidden_states, covariance_type="full", n_iter=args.iterations)
    model_major = hmm.GaussianHMM(n_components=args.hidden_states, covariance_type="full", n_iter=args.iterations)
    print("Training minor model...")
    model_minor.fit(minor_sequences, minor_sequence_lengths)
    print("Trained minor model. Converged: %s" % str(model_minor.monitor_.converged))
    print("Training major model...")
    model_major.fit(major_sequences, major_sequence_lengths)
    print("Trained major model. Converged: %s" % str(model_major.monitor_.converged))
    print("Done.")

    print("Copying models")
    models = []
    for i in range(0, 12):
        key_model = copy.deepcopy(model_minor)
        key_model.means_ = np.roll(key_model.means_, i, axis=1)
        key_model.covars_ = np.roll(np.roll(key_model.covars_, i, axis=1), i, axis=2)
        models.append(key_model)
    for i in range(0, 12):
        key_model = copy.deepcopy(model_major)
        key_model.means_ = np.roll(key_model.means_, i, axis=1)
        key_model.covars_ = np.roll(np.roll(key_model.covars_, i, axis=1), i, axis=2)
        models.append(key_model)

    print("Testing models...")
    print("")

    results = []
    test_n = 0
    errors = 0
    errors_given = 0
    for track_id in all_tracks[train_n:]:
        analysis = load_analysis(data_dir, track_id)
        seq = format_sequence(analysis)
        top_model = np.argmax([mdl.score(seq) for mdl in models])
        if analysis["mode"] == 1:
            top_model_given = np.argmax([mdl.score(seq) for mdl in models[12:]])
        else:
            top_model_given = np.argmax([mdl.score(seq) for mdl in models[:12]])
        results.append([track_id, 
            "%s %s"% (key_nums[analysis["key"]], modes[analysis["mode"]]), 
            "%s %s"% (key_nums[top_model % 12], modes[top_model // 12]), 
            "%s %s"% (key_nums[top_model_given], modes[analysis["mode"]])
        ])

        # Count errors
        test_n += 1
        if not (analysis["key"] == top_model % 12 and analysis["mode"] == top_model // 12):
            errors += 1
        if not (analysis["key"] == top_model_given):
            errors_given += 1
    #print(tabulate(results, headers=["Song ID", "Key label", "Predicted", "Predicted if mode is given"]))
    return errors/test_n, errors_given/test_n

        


def get_args():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--data-dir', default='dataset', type=str, help='''
        The directory where the track data is stored to use for the analysis
        ''')
    arg_parser.add_argument('--model-file', default=False, type=str, help='''
        Optional filename of a CSV file to store the resulting HMM model.
        ''')
    arg_parser.add_argument('--hidden-states', default=3, type=int, help='''
        Set the number of hidden states for the HMM.
        ''')
    arg_parser.add_argument('--iterations', default=100, type=int, help='''
        Set the number of iterations for training the HMM.
        ''')
    return arg_parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    error, error_given = run_hmm_method_all_tracks(args.data_dir)
    print("%26s %7.2f%%" % ("Error:", error*100) )
    print("%26s %7.2f%%" % ("Error [mode given]:", error_given*100) )
    