import io
from flask import Flask, request, jsonify, send_file
import requests
import sys, os
from api import CreateCover

app = Flask(__name__)

# from infer import svc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# MR과 커버 음원을 합치는 함수

# Test용 함수
@app.route('/test', methods=['POST'])
def get_file_as_bytes():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    save_path = os.path.join('/home/ec2-user/', file.filename)
    file.save(save_path)
    try:
        # 파일을 byte[]로 읽음
        # file_bytes = file.read()
        return send_file(
            save_path,  # byte[] 데이터를 BytesIO로 래핑
            as_attachment=True,  # 다운로드로 전송
            mimetype='application/octet-stream'  # MIME 타입 설정 (적절한 MIME 타입으로 변경 가능)
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 커버 생성 요청 처리 함수
@app.route('/upload', methods=['POST'])
def getVoiceForCover():
        print('입력 실행')
        # result = ''
        result = CreateCover('default')
        # 파일이 정상적으로 생성됐는지 확인
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        file = request.files['file']  # 파일 가져오기
        file_name = request.form.get('file_name', 'received_file.mp3')  # 파일명 (필요시 기본 파일명 지정)

        # 파일을 서버에 저장할 경로 설정
        save_path = os.path.join('/temp', file_name)
        file.save(save_path)  # 파일 저장

        try:
        # 파일을 byte[]로 읽음
        # file_bytes = file.read()
            return send_file(
                save_path,  # byte[] 데이터를 BytesIO로 래핑
                as_attachment=True,  # 다운로드로 전송
                mimetype='application/octet-stream'  # MIME 타입 설정 (적절한 MIME 타입으로 변경 가능)
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # src_path = 'src_wav/박효신_숨.wav'
    # user = '김형석_교수님_노마스크.wav'
    # songname = '박효신_숨'
    # CreateCover(src_path,user,songname)
    if not os.path.exists('temp'):
        os.makedirs('temp')
    app.run(host='0.0.0.0', port=5000, debug=True)
