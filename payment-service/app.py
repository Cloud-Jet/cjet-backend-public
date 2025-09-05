from flask import Flask
from routes import payment_bp
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

    app.register_blueprint(payment_bp, url_prefix='/api/payments')
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PAYMENT_SERVICE_PORT', 5005))
    print(f"Payment Service starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
#v4.0