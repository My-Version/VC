from flask import Flask, request, jsonify
import requests
import sys,os

app = Flask(__name__)
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from infer import svc
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
from pydub import AudioSegment

# mr (노래제목) 설정해야함
def merge_vocal(mr,filename):
    # MR 제거된 음원과 커버 음원 불러오기
    mr_removed_audio = AudioSegment.from_file("mr/mr.wav")
    cover_audio = AudioSegment.from_file("outputs/"+filename)

    # 두 오디오 파일 합치기 (순서에 따라 다름)
    combined_audio = mr_removed_audio.overlay(cover_audio)

    # 합친 오디오 파일 저장
    save_path = "outputs/combine_outputs/combined_output.wav"
    combined_audio.export(save_path, format="wav")

    return save_path

@app.route('/upload', methods=['POST'] endpoin)
def getVoiceForCover():
    result = CreateCover("")
    print("heloo")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        temp_path = os.path.join('temp', file.filename)
        file.save(temp_path)

        result = CreateCover(temp_path)

        with open(result, 'rb') as cover_file:
            files = {'file': (os.path.basename(result), cover_file, 'audio/mpeg')}
            response = requests.post('http://localhost:8080/api/upload', files=files)
            if response.status_code == 200:
                return jsonify({'message': 'Cover file created and uploaded successfully.'})
            else:
                return jsonify({'error': 'Failed to upload cover file to Spring server'}), 500

    return jsonify(result), 200



def CreateCover(input_file_path):
    # parser = argparse.ArgumentParser()
    # default 에 들어가는 인자는 선택된 파일으로 선택되게 수정해야함
    # ref_wav -> input_file_path 로 설정해야함

    # parser.add_argument('--src_wav_path', default="src_wav/buzz2.wav")
    # parser.add_argument('--ref_wav_path', default="ref_wav/test.wav")
    # parser.add_argument('--model_ckpt_path',
    #                     default='pretrained/G_150k.pt')
    # parser.add_argument('--out_dir', default='outputs')
    # parser.add_argument(
    #     '--num_samples', type=int, default=15000,
    #     help="Specify the number of Self-Supervised Learning features to be expanded")
    # parser.add_argument(
    #     '--key_shift', type=int,
    #     help='Adjust the pitch of the source singing. Tone the song up or down in semitones.'
    # )
    # parser.add_argument(
    #     '--speech_enroll', action='store_true',default=True,
    #     help='When using speech as the reference audio, the pitch of the reference audio will be increased by 1.2 times \
    #         when performing pitch shift to cover the pitch gap between singing and speech. \
    #         Note: This option is invalid when key_shift is specified.'
    # )

    # a = parser.parse_args()
    
    model_ckpt_path = 'pretrained/G_150k.pt'
    speech_enroll = True
    src_wav_path = "src_wav/buzz2.wav"
    ref_wav_path = "ref_wav/test.wav"
    num_samples = 15000
    key_shift = 0
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # device = 'cpu'
    print(f'using {device} for inference')

    f0factor = pow(2, key_shift / 12) if key_shift else 0.

    print("check")
    model = SVCNN(model_ckpt_path, device=device)
    print("check2")
    t0 = time.time()
    cover_name = svc(model, src_wav_path, ref_wav_path, out_dir='outputs', device=device, f0_factor=f0factor, speech_enroll=speech_enroll, num_samples=num_samples)
    t1 = time.time()
    print("check3")
    print(f"{t1-t0:.2f}s to perfrom the conversion")

    result = merge_vocal("",cover_name)
    return result
    
    # except Exception as e:
    #     print("실패")
    #     return jsonify({'error': str(e)}), 400
    
    
if __name__ == '__main__':
        if not os.path.exists('temp'):
            os.makedirs('temp')
        app.run(debug=True)