# CloudJet 인증 서비스 (포트 5001)
# JWT 토큰 기반 회원가입, 로그인, 토큰 검증 담당
# CD 경로수정했음 
# v3.0.0 테스트
# v5.0 테스트 
from flask import Flask
from routes import auth_bp
import os

def create_app():
    app = Flask(__name__)
    
    # CORS는 Istio에서 처리
    
    # SECRET_KEY 필수로 설정
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY 환경변수가 설정되지 않았습니다!")
    
    app.config['SECRET_KEY'] = secret_key
    app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'
    
    # 블루프린트 등록
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('AUTH_SERVICE_PORT', 5001))
    
    print(f"Auth Service starting on port {port}")
    # debug는 환경변수에 따라 결정되도록 수정
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
#v4.0