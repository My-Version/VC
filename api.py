from pydub import AudioSegment
import numpy as np
import torch
import soundfile as sf

import os
import time
from infer import svc

from modules.SVCNN import SVCNN

def merge_vocal(mr, filename):
    mr_removed_audio = AudioSegment.from_file(mr)
    cover_audio = AudioSegment.from_file(f"{filename}")
    combined_audio = mr_removed_audio.overlay(cover_audio)
    save_path = f"outputs/combine_outputs/{filename.split('/')[1]}"
    combined_audio.export(save_path, format="wav")
    return save_path

# 커버 생성하는 모델 실행 함수
def CreateCover(input_file_path,user,songname):
    model_ckpt_path = 'pretrained/G_150k.pt'
    speech_enroll = True
    src_wav_path = input_file_path  # 입력된 파일 경로
    ref_wav_path = 'ref_wav/'+user
    # ref_wav_path = "ref_wav/김형석_교수님_노마스크.wav"
    # ref_wav_path = "ref_wav/천송현.wav"
    # num_samples = 15000
    num_samples = 40000
    key_shift = 0
    mr_path = 'mr/'+songname+'_mr.wav' 
    # mr_path = 'mr/성시경_차마_mr.wav'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print(f'using {device} for inference')
    
    f0factor = pow(2, key_shift / 12) if key_shift else 0.

    model = SVCNN(model_ckpt_path, device=device)

    t0 = time.time()
    
    # 커버 생성 수행
    cover_name = svc(model, src_wav_path, ref_wav_path, out_dir='outputs', device=device, f0_factor=f0factor, speech_enroll=speech_enroll, num_samples=num_samples)
    
    t1 = time.time()
    print(f"{t1-t0:.2f}s to perform the conversion")

    result = merge_vocal(mr_path, cover_name)
    
    if os.path.exists(result):
        return result
    else:
        raise FileNotFoundError("The combined output file was not created.")