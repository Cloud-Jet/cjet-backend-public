from flask import Flask, request
from routes import payment_bp
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

        print(f"[PAYMENT-SERVICE] {request.method} {request.path} - Client IP: {real_ip}")
    
    app.register_blueprint(payment_bp, url_prefix='/api/payments')
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PAYMENT_SERVICE_PORT', 5005))
    print(f"Payment Service starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
#v2.0.3# Build trigger Thu, Sep 11, 2025
