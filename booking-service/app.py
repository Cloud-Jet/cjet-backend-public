# Booking Service Main Application
# 블루그린 시연8
from flask import Flask, request
from routes import booking_bp
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import sys

def get_client_ip(req):
    # Istio/Envoy가 넣어주는 실제 IP 헤더 우선 사용
    ip = req.headers.get('X-Envoy-External-Address')
    if not ip:
        xff = req.headers.get('X-Forwarded-For')
        if xff:
            ip = xff.split(',')[0].strip()
    return ip or req.remote_addr

def create_app():
    app = Flask(__name__)
    
    # Istio 프록시 체인 신뢰 설정
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1)
    
    # CORS는 Istio에서 처리
    
    # SECRET_KEY 필수로 설정
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY 환경변수가 설정되지 않았습니다!")
    
    app.config['SECRET_KEY'] = secret_key
    app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'
    
    # Health check IP 필터링을 위한 설정
    HEALTH_CHECK_IPS = {'127.0.0.6', '127.0.0.1', '::1'}

    # 실제 클라이언트 IP 로깅 미들웨어 (Istio 환경 최적화)
    @app.before_request
    def log_request_info():
        real_ip = get_client_ip(request)

        # Health check 요청은 로깅하지 않음
        if request.path.endswith('/health') or real_ip in HEALTH_CHECK_IPS:
            return

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
#v2.0.3# Build trigger Thu, Sep 11, 2025 
# 테스트
