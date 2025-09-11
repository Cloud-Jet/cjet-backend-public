# CloudJet 항공편 검색 서비스 (포트 5002)
# 항공편 조회, 검색, 스케줄 관리 담당
from flask import Flask, request
from routes import flight_bp
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
    
    # 실제 클라이언트 IP 로깅 미들웨어
    @app.before_request
    def log_request_info():
        real_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if real_ip and ',' in real_ip:
            real_ip = real_ip.split(',')[0].strip()
        
        if request.endpoint and not request.path.endswith('/health'):
            print(f"[FLIGHT-SERVICE] {request.method} {request.path} - Client IP: {real_ip}")
    
    # 블루프린트 등록
    app.register_blueprint(flight_bp, url_prefix='/api/flights')
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('FLIGHT_SERVICE_PORT', 5002))
    
    print(f"Flight Service starting on port {port}")
    # debug는 환경변수에 따라 결정되도록 수정
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
#v4.0