from flask import Flask, request, jsonify
import requests
import sys, os
from api import CreateCover
import base64

app = Flask(__name__)

# from infer import svc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# MR과 커버 음원을 합치는 함수

@app.route('/hello',methods = ['GET'])
def hello():
    print('hello')

# 커버 생성 요청 처리 함수
@app.route('/upload', methods=['POST'])
def getVoiceForCover():
        print('입력 실행')
        result = ''
        # result = CreateCover('default')
        # 파일이 정상적으로 생성됐는지 확인
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        file = request.files['file']  # 파일 가져오기
        file_name = request.form.get('file_name', 'received_file.mp3')  # 파일명 (필요시 기본 파일명 지정)

        # 파일을 서버에 저장할 경로 설정
        save_path = os.path.join('/temp', file_name)
        file.save(save_path)  # 파일 저장

        if os.path.exists(save_path):
        # 예: Spring 서버에 파일 전송
            with open(save_path, 'rb') as cover_file:
                files = {'file': (os.path.basename(save_path), cover_file, 'audio/mpeg')}
                response = requests.post('http://3.37.251.198:8080/upload', files=files)
                
                if response.status_code == 200:
                    return jsonify({'message': 'Cover file created and uploaded successfully.'})
                else:
                    return jsonify({'error': 'Failed to upload cover file to Spring server'}), 500
        else:
            return jsonify({'error': 'Failed to save file on server'}), 500


if __name__ == '__main__':
    CreateCover('src_wav/박효신_숨.wav')
    # if not os.path.exists('temp'):
    #     os.makedirs('temp')
    # app.run(host='0.0.0.0', port=8080, debug=True)
    

