# CloudJet 항공편 검색 서비스 (포트 5002)
# 항공편 조회, 검색, 스케줄 관리 담당
from flask import Flask, request
from routes import flight_bp
from werkzeug.middleware.proxy_fix import ProxyFix
import os

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
    
    # Istio 프록시 체인 신뢰 설정 (ingress gateway + sidecar = 2홉)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1)
    
    # CORS는 Istio에서 처리
    
    # SECRET_KEY 필수로 설정
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY 환경변수가 설정되지 않았습니다!")
    
    app.config['SECRET_KEY'] = secret_key
    app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'
    
    # 실제 클라이언트 IP 로깅 미들웨어 (Istio 환경 최적화)
    @app.before_request
    def log_request_info():
        if not request.path.endswith('/health'):
            # 모든 헤더 확인을 위한 디버깅
            print(f"[FLIGHT-SERVICE-DEBUG] Headers: {dict(request.headers)}")
            print(f"[FLIGHT-SERVICE-DEBUG] Remote addr: {request.remote_addr}")
            real_ip = get_client_ip(request)
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
#v2.0.1# Build trigger Thu, Sep 11, 2025  2:43:41 PM
