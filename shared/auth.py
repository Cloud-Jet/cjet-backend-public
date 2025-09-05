# Authentication Module - 하드코딩 제거 버전
import jwt
import os
import hashlib
import hmac
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta

# SECRET_KEY 환경변수 필수 설정
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 환경변수가 설정되지 않았습니다!")

def generate_token(user_id, role='USER'):
    """JWT 토큰 생성 - Python 3.13 호환"""
    try:
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        # PyJWT 2.x 호환
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        
        # 토큰이 bytes로 반환될 경우 string으로 변환
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        return token
    except Exception as e:
        print(f"토큰 생성 오류: {e}")
        print(f"오류 타입: {type(e)}")
        import traceback
        traceback.print_exc()
        return None

def token_required(f):
    """JWT 토큰 검증 데코레이터"""
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': '토큰이 없습니다.'}), 401
        
        try:
            # Bearer 토큰에서 실제 토큰 추출
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            # 토큰 디코드
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '토큰이 만료되었습니다.'}), 401
        except jwt.InvalidTokenError as e:
            print(f"토큰 검증 오류: {e}")
            return jsonify({'message': '유효하지 않은 토큰입니다.'}), 401
        except Exception as e:
            print(f"토큰 처리 오류: {e}")
            return jsonify({'message': '토큰 처리 중 오류가 발생했습니다.'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorator

def admin_required(f):
    """관리자 권한 검증 데코레이터"""
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': '토큰이 없습니다.'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            user_role = data.get('role', 'USER')
            
            # role이 ADMIN이 아니면 거부
            if user_role != 'ADMIN':
                return jsonify({'message': '관리자 권한이 필요합니다.'}), 403
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '토큰이 만료되었습니다.'}), 401
        except jwt.InvalidTokenError as e:
            print(f"관리자 토큰 검증 오류: {e}")
            return jsonify({'message': '유효하지 않은 토큰입니다.'}), 401
        except Exception as e:
            print(f"관리자 토큰 처리 오류: {e}")
            return jsonify({'message': '토큰 처리 중 오류가 발생했습니다.'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorator