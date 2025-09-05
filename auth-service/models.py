# Auth Service Models - 구문 오류 수정
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_connection
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

class User:
    @staticmethod
    def create_user(name, email, password, phone, birth_date):
        """새 사용자 생성"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor()
            
            # 이메일 중복 검사
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return None, "이미 존재하는 이메일입니다."
            
            # 비밀번호 해시화 - scrypt 방식 사용
            password_hash = generate_password_hash(password, method='scrypt')
            
            # 사용자 등록
            insert_query = """
                INSERT INTO users (name, email, password_hash, phone, birth_date)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (name, email, password_hash, phone, birth_date))
            connection.commit()
            
            user_id = cursor.lastrowid
            return user_id, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def get_user_profile(user_id):
        """사용자 프로필 조회"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT user_id, name, email, phone, birth_date, role
                FROM users WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return None, "사용자를 찾을 수 없습니다."
            
            return user, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def update_user_profile(user_id, name, phone):
        """사용자 프로필 업데이트"""
        try:
            connection = get_db_connection()
            if not connection:
                return False, "데이터베이스 연결 오류"
            
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users SET name = %s, phone = %s 
                WHERE user_id = %s
            """, (name, phone, user_id))
            
            connection.commit()
            
            if cursor.rowcount == 0:
                return False, "사용자를 찾을 수 없습니다."
            
            return True, None
            
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def verify_password(stored_password, input_password):
        """다양한 해시 방식 호환 비밀번호 검증"""
        try:
            # 0. 단순 텍스트 비밀번호 (테스트용)
            if stored_password == input_password:
                return True
                
            # 1. Werkzeug 방식 (pbkdf2, scrypt 등)
            if '$' in stored_password and (':' in stored_password or stored_password.startswith('scrypt:')):
                return check_password_hash(stored_password, input_password)
            
            # 2. 사용자 정의 해시 방식 (64자 hex)
            elif len(stored_password) == 64 and all(c in '0123456789abcdef' for c in stored_password):
                # 단순 SHA256 방식
                input_hash = hashlib.sha256(input_password.encode('utf-8')).hexdigest()
                return stored_password == input_hash
            
            # 3. Salt + Hash 방식 (32자 salt + 64자 hash)
            elif len(stored_password) == 96:
                salt = stored_password[:32]
                stored_hash = stored_password[32:]
                password_hash = hashlib.pbkdf2_hmac('sha256', input_password.encode('utf-8'), salt.encode('utf-8'), 100000)
                return stored_hash == password_hash.hex()
            
            # 4. 기타 Werkzeug 호환 시도
            else:
                try:
                    return check_password_hash(stored_password, input_password)
                except:
                    return False
                    
        except Exception as e:
            print(f"비밀번호 검증 오류: {e}")
            return False
    
    @staticmethod
    def authenticate_user(email, password):
        """사용자 인증 - 모든 해시 방식 호환"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            
            # 사용자 조회
            cursor.execute("""
                SELECT user_id, name, email, password_hash, phone, role
                FROM users 
                WHERE email = %s
            """, (email,))
            
            user = cursor.fetchone()
            
            if not user:
                return None, "이메일 또는 비밀번호가 잘못되었습니다."
            
            # 다양한 해시 방식으로 비밀번호 검증
            if not User.verify_password(user['password_hash'], password):
                return None, "이메일 또는 비밀번호가 잘못되었습니다."
            
            # 비밀번호 해시 제거하고 필요한 정보만 반환
            user_data = {
                'user_id': user['user_id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'role': user['role'] or 'USER'
            }
            return user_data, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        except Exception as e:
            return None, f"인증 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
