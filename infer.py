import os
import time

import numpy as np
import torch
import soundfile as sf
import argparse


from modules.SVCNN import SVCNN
from utils.spectrogram import extract_voiced_area
from utils.pitch_extraction import extract_pitch_ref as extract_pitch, coarse_f0

import logging
import warnings
import absl.logging

absl.logging.set_verbosity(absl.logging.ERROR)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('torch').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)
logging.getLogger('h5py').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore')


SPEAKER_INFORMATION_WEIGHTS = [
    0, 0, 0, 0, 0, 0,  # layer 0-5
    1.0, 0, 0, 0,
    0, 0, 0, 0, 0, 0,  # layer 15
    0, 0, 0, 0, 0, 0,  # layer 16-21
    0,  # layer 22
    0, 0  # layer 23-24
]
SPEAKER_INFORMATION_LAYER = 6


APPLIED_INFORMATION_WEIGHTS = [
    0, 0, 0, 0, 0, 0,  # layer 0-5
    0, 0, 0, 0,
    0, 0, 0, 0, 0, 0,  # layer 15
    0, 0, 0, 0, 0.2, 0.2,  # layer 16-21
    0.2,  # layer 22
    0.2, 0.2  # layer 23-24
]


def svc(model, src_wav_path, ref_wav_path, synth_set_path=None, f0_factor=0., speech_enroll=False, out_dir="output", hallucinated_set_path=None, num_samples=15000, device='cpu'):
    """
    Perform singing voice conversion and save the resulting waveform to `out_dir`.

    Args:
        src_wav_path (str): Path to the source singing waveform (24kHz, single-channel).
        ref_wav_path (str): Path to the reference waveform from the target speaker (single-channel, not less than 16kHz).
        out_dir (str): Directory to save the converted singing audio.
        model (SVCNN): Loaded SVC model.
        f0_factor (float): F0 shift factor.
        speech_enroll (bool, optional): Whether the reference audio is a speech clip or a singing clip. Defaults to False.
        hallucinated_set_path (str): Path to the hallucinated set. If specified, it will be directly read. Otherwise, the matching set will be computed first, and then the hallucinator will be executed to obtain the hallucinated set.
        num_samples(int): Specifies the number of frames to be expanded for SSL features.
        device (torch.device, optional): Device to perform the conversion on. Defaults to cpu.

    """
    wav_name = os.path.basename(src_wav_path).split('.')[0]
    ref_name = os.path.basename(ref_wav_path).split('.')[0]

    f0_src, f0_factor = extract_pitch(src_wav_path, ref_wav_path, predefined_factor=f0_factor, speech_enroll=speech_enroll)

    pitch_src = coarse_f0(f0_src)

    query_mask = extract_voiced_area(src_wav_path, hop_size=480, energy_thres=0.1)
    query_mask = torch.from_numpy(query_mask).to(device)

    synth_weights = torch.tensor(
        SPEAKER_INFORMATION_WEIGHTS, device=device)[:, None]
    query_seq = model.get_features(
        src_wav_path, weights=synth_weights)

    if synth_set_path:
        synth_set = torch.load(synth_set_path).to(device)
    else:
        synth_set_path = f"matching_set/{ref_name}.pt"
        synth_set = model.get_matching_set(ref_wav_path, out_path=synth_set_path).to(device)

    if hallucinated_set_path is None:
        hallucinated_set_path = f"matching_set/{ref_name}_hallucinated_{num_samples//1000}k.npy"
        os.system(f"python modules/Phoneme_Hallucinator_v2/scripts/speech_expansion_ins.py --cfg_file modules/Phoneme_Hallucinator_v2/exp/speech_XXL_cond/params.json --num_samples {num_samples} --path {synth_set_path} --out_path {hallucinated_set_path}")

    hallucinated_set = np.load(hallucinated_set_path)
    hallucinated_set = torch.from_numpy(hallucinated_set).to(device)

    synth_set = torch.cat([synth_set, hallucinated_set], dim=0)

    query_len = query_seq.shape[0]
    if len(query_mask) > query_len:
        query_mask = query_mask[:query_len]
    else:
        p = query_len - len(query_mask)
        query_mask = np.pad(query_mask, (0, p))

    f0_len = query_len*2
    if len(f0_src) > f0_len:
        f0_src = f0_src[:f0_len]
        pitch_src = pitch_src[:f0_len]
    else:
        p = f0_len-len(f0_src)
        f0_src = np.pad(f0_src, (0, p), mode='edge')
        pitch_src = np.pad(pitch_src, (0, p), mode='edge')
    
    print(query_seq.shape)
    print(synth_set.shape)

    f0_src = torch.from_numpy(f0_src).float().to(device)
    pitch_src = torch.from_numpy(pitch_src).to(device)

    out_wav = model.match(query_seq, f0_src, pitch_src, synth_set, topk=4, query_mask=query_mask)
    # out_wav is (T,) tensor converted 16kHz output wav using k=4 for kNN.
    os.makedirs(out_dir, exist_ok=True)
    wfname = f'{out_dir}/{wav_name}_{ref_name}_{f0_factor:.2f}_NeuCoSVCv2.wav'

    sf.write(wfname, out_wav.numpy(), 24000)

    return wfname




def main(a):
    model_ckpt_path = a.model_ckpt_path
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # device = 'cpu'
    print(f'using {device} for inference')

    f0factor = pow(2, a.key_shift / 12) if a.key_shift else 0.

    speech_enroll = a.speech_enroll
    model = SVCNN(model_ckpt_path, device=device)

    t0 = time.time()
    svc(model, a.src_wav_path, a.ref_wav_path, out_dir=a.out_dir, device=device, f0_factor=f0factor, speech_enroll=speech_enroll, num_samples=a.num_samples)
    t1 = time.time()
    print(f"{t1-t0:.2f}s to perfrom the conversion")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--src_wav_path', required=True)
    parser.add_argument('--ref_wav_path', required=True)
    parser.add_argument('--model_ckpt_path',
                        default='pretrained/G_150k.pt')
    parser.add_argument('--out_dir', default='output')
    parser.add_argument(
        '--num_samples', type=int, default=15000,
        help="Specify the number of Self-Supervised Learning features to be expanded")
    parser.add_argument(
        '--key_shift', type=int,
        help='Adjust the pitch of the source singing. Tone the song up or down in semitones.'
    )
    parser.add_argument(
        '--speech_enroll', action='store_true',
        help='When using speech as the reference audio, the pitch of the reference audio will be increased by 1.2 times \
            when performing pitch shift to cover the pitch gap between singing and speech. \
            Note: This option is invalid when key_shift is specified.'
    )

    a = parser.parse_args()

    main(a)
