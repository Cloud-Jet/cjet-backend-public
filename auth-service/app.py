# CloudJet 인증 서비스 (포트 5001)
# JWT 토큰 기반 회원가입, 로그인, 토큰 검증 담당
# CD 경로수정했음 
# v3.0.0 테스트
# v5.0 테스트
# 슬랙알림 테스트 3
# 롤아웃 설정 후 슬랙알람까지 설정
# 슬랙 알림 롤아웃 오는지 테스트
# CI/CD 테스트 09-16
# 버전 테스트
# 버전 테스트2
# 버전 테스트3
# 헬스체크 성공 이제 슬랙알람이랑 블루그린 모니터링
# 슬랙 알림 테스트 v4
# 슬랙 알림 테스트 v5

from flask import Flask, request
from routes import auth_bp
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import logging

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
    
    # 실제 클라이언트 IP 로깅 미들웨어 (Istio 환경 최적화)
    @app.before_request
    def log_request_info():
        if not request.path.endswith('/health'):
            real_ip = get_client_ip(request)
            print(f"[AUTH-SERVICE] {request.method} {request.path} - Client IP: {real_ip}")
    
    # 블루프린트 등록
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('AUTH_SERVICE_PORT', 5001))
    
    print(f"Auth Service starting on port {port}")
    # debug는 환경변수에 따라 결정되도록 수정
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
#v2.0.3# Build trigger Thu, Sep 11, 2025 
