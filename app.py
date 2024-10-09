from flask import Flask, request, jsonify
import requests
import sys, os
from api import CreateCover

app = Flask(__name__)

# from infer import svc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# MR과 커버 음원을 합치는 함수


# 커버 생성 요청 처리 함수
@app.route('/upload', methods=['GET'])
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
                response = requests.post('http://3.37.251.198:8080/upload', files=files)
                
                if response.status_code == 200:
                    return jsonify({'message': 'Cover file created and uploaded successfully.'})
                else:
                    return jsonify({'error': 'Failed to upload cover file to Spring server'}), 500
        else:
            return jsonify({'error': 'Cover file was not created properly.'}), 500


if __name__ == '__main__':
    #CreateCover('src_wav/buzz.wav')
    if not os.path.exists('temp'):
        os.makedirs('temp')
    app.run(host='0.0.0.0', port=5000, debug=True)
