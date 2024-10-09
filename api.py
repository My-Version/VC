from pydub import AudioSegment
import numpy as np
import torch
import soundfile as sf
import argparse
import os
import time
from infer import svc

from modules.SVCNN import SVCNN

def merge_vocal(mr, filename):
    mr_removed_audio = AudioSegment.from_file("mr/mr.wav")
    cover_audio = AudioSegment.from_file(f"{filename}")
    combined_audio = mr_removed_audio.overlay(cover_audio)
    save_path = "outputs/combine_outputs/combined_output.wav"
    combined_audio.export(save_path, format="wav")
    return save_path

# 커버 생성하는 모델 실행 함수
def CreateCover(input_file_path):
    model_ckpt_path = 'pretrained/G_150k.pt'
    speech_enroll = True
    src_wav_path = input_file_path  # 입력된 파일 경로
    ref_wav_path = "ref_wav/test.wav"
    num_samples = 15000
    key_shift = 0
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print(f'using {device} for inference')
    
    f0factor = pow(2, key_shift / 12) if key_shift else 0.

    model = SVCNN(model_ckpt_path, device=device)

    t0 = time.time()
    
    # 커버 생성 수행
    cover_name = svc(model, src_wav_path, ref_wav_path, out_dir='outputs', device=device, f0_factor=f0factor, speech_enroll=speech_enroll, num_samples=num_samples)
    
    t1 = time.time()
    print(f"{t1-t0:.2f}s to perform the conversion")

    result = merge_vocal("", cover_name)
    
    if os.path.exists(result):
        return result
    else:
        raise FileNotFoundError("The combined output file was not created.")