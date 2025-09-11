# Booking Service Main Application
from flask import Flask, request
from routes import booking_bp
import os
import sys

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
            print(f"[BOOKING-SERVICE] {request.method} {request.path} - Client IP: {real_ip}")
    
    # 블루프린트 등록
    app.register_blueprint(booking_bp, url_prefix='/api/bookings')
    
    return app

if __name__ == '__main__':
    try:
        print("[BOOKING-SERVICE] 서비스 초기화 시작...")
        print(f"[BOOKING-SERVICE] 현재 작업 디렉토리: {os.getcwd()}")
        print(f"[BOOKING-SERVICE] 파이썬 경로: {sys.path}")
        
        app = create_app()
        port = int(os.environ.get('BOOKING_SERVICE_PORT', 5003))
        
        print(f"[BOOKING-SERVICE] Booking Service starting on port {port}")
        print(f"[BOOKING-SERVICE] Debug mode: {app.config['DEBUG']}")
        print(f"[BOOKING-SERVICE] 서비스 준비 완료")
        
        app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
        
    except Exception as e:
        print(f"[BOOKING-SERVICE] 서비스 시작 오류: {e}")
        import traceback
        print(f"[BOOKING-SERVICE] 스택 트레이스: {traceback.format_exc()}")
        raise
#v2.0.1# Build trigger Thu, Sep 11, 2025  2:43:41 PM
