from flask import Flask, request, jsonify
import requests
import sys, os
import time
import torch
from pydub import AudioSegment
from modules.SVCNN import SVCNN

app = Flask(__name__)

# from infer import svc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# MR과 커버 음원을 합치는 함수
def merge_vocal(mr, filename):
    mr_removed_audio = AudioSegment.from_file("mr/mr.wav")
    cover_audio = AudioSegment.from_file(f"outputs/{filename}")
    combined_audio = mr_removed_audio.overlay(cover_audio)
    save_path = "outputs/combine_outputs/combined_output.wav"
    combined_audio.export(save_path, format="wav")
    return save_path

# 커버 생성 요청 처리 함수
@app.route('/upload', methods=['POST'])
def getVoiceForCover():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        temp_path = os.path.join('temp', file.filename)
        file.save(temp_path)

        # 동기적으로 모델 처리 후 결과 반환
        result = CreateCover(temp_path)

        # 파일이 정상적으로 생성됐는지 확인
        if os.path.exists(result):
            with open(result, 'rb') as cover_file:
                files = {'file': (os.path.basename(result), cover_file, 'audio/mpeg')}
                response = requests.post('http://221.146.39.168:8081/api/upload', files=files)
                
                if response.status_code == 200:
                    return jsonify({'message': 'Cover file created and uploaded successfully.'})
                else:
                    return jsonify({'error': 'Failed to upload cover file to Spring server'}), 500
        else:
            return jsonify({'error': 'Cover file was not created properly.'}), 500

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

if __name__ == '__main__':
    if not os.path.exists('temp'):
        os.makedirs('temp')
    app.run('0.0.0.0',port=8080, debug=True)
