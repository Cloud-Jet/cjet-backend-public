# Auth Service Routes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify

# 지연 임포트로 순환 참조 방지
def get_models():
    from models import User
    return User

def get_auth():
    from shared.auth import generate_token, token_required
    return generate_token, token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """회원가입"""
    try:
        User = get_models()
        data = request.get_json()
        
        required_fields = ['name', 'email', 'password', 'phone', 'birthDate']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'message': f'{field}는 필수 입력 항목입니다.'}), 400
        
        user_id, error = User.create_user(
            data['name'], data['email'], data['password'], 
            data['phone'], data['birthDate']
        )
        
        if error:
            return jsonify({'message': error}), 400
        
        return jsonify({
            'message': '회원가입이 성공적으로 완료되었습니다.',
            'success': True
        }), 201
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """로그인"""
    try:
        User = get_models()
        generate_token, _ = get_auth()
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'message': '이메일과 비밀번호를 입력해주세요.'}), 400
        
        user, error = User.authenticate_user(data['email'], data['password'])
        
        if error:
            return jsonify({'message': error}), 401
        
        token = generate_token(user['user_id'], user['role'])
        
        return jsonify({
            'message': '로그인 성공',
            'token': token,
            'user': {
                'id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_user_profile():
    """사용자 프로필 조회"""
    try:
        User = get_models()
        _, token_required = get_auth()
        
        # 토큰 검증
        from flask import request
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '토큰이 없습니다.'}), 401
            
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        import jwt
        from shared.auth import SECRET_KEY
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = data['user_id']
        
        user, error = User.get_user_profile(current_user_id)
        
        if error:
            if "찾을 수 없습니다" in error:
                return jsonify({'message': error}), 404
            return jsonify({'message': error}), 500
        
        return jsonify({'user': user}), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
def update_user_profile():
    """사용자 프로필 업데이트"""
    try:
        User = get_models()
        
        # 토큰 검증
        from flask import request
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '토큰이 없습니다.'}), 401
            
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        import jwt
        from shared.auth import SECRET_KEY
        data_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = data_token['user_id']
        
        data = request.get_json()
        
        success, error = User.update_user_profile(
            current_user_id, data.get('name'), data.get('phone')
        )
        
        if not success:
            if "찾을 수 없습니다" in error:
                return jsonify({'message': error}), 404
            return jsonify({'message': error}), 400
        
        return jsonify({
            'message': '프로필이 성공적으로 업데이트되었습니다.',
            'success': True
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@auth_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-service',
        'port': 5001
    }), 200

# 주석 한 줄 추가해서 테스트해보기
# 추가 주석
# 추가주석 2
# 추가주석 3 디버그 코드 추가하고 테스트
# Repository Dispatch 코드로 테스트
# main에서 테스트
# cd 자동화 테스트
# ecr 이미지 검증
# Argocd 테스트
# 0904 파이프라인 분리 테스트1
# 0904 파이프라인 분리 테스트2
# 0904 파이프라인 분리 테스트3
# 0904 파이프라인 분리 테스트4
# 0904 파이프라인 분리 테스트5
# 0904 파이프라인 분리 테스트6

# version 10.0.0