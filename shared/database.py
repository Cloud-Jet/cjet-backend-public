# CloudJet MSA Database 연결 모듈
# AWS RDS MySQL 커넥션 풀 관리, 모든 마이크로서비스에서 공유 사용
import mysql.connector
from mysql.connector import Error, pooling
import os
import json
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 커넥션 풀 글로벌 변수
connection_pool = None

def init_connection_pool():
    """AWS RDS MySQL 커넥션 풀 초기화"""
    global connection_pool
    
    try:
        pool_config = {
            'pool_name': 'cloudjet_pool',
            'pool_size': int(os.environ.get('DB_POOL_SIZE', 5)),
            'pool_reset_session': True,
            'host': os.environ.get('DB_HOST'),
            'database': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'autocommit': False,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'connect_timeout': 10,
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
        }
        
        # 필수 환경변수 확인 (DB_NAME 추가)
        required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(f"필수 환경변수가 누락되었습니다: {', '.join(missing_vars)}")
        
        connection_pool = pooling.MySQLConnectionPool(**pool_config)
        print(f"✅ AWS RDS 커넥션 풀 초기화 완료 (Host: {pool_config['host']}, DB: {pool_config['database']})")
        
        # 연결 테스트
        test_connection = connection_pool.get_connection()
        if test_connection.is_connected():
            cursor = test_connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"   MySQL 버전: {version[0]}")
            cursor.close()
            test_connection.close()
            
    except Error as e:
        print(f"❌ 커넥션 풀 초기화 실패: {e}")
        connection_pool = None
    except Exception as e:
        print(f"❌ 설정 오류: {e}")
        connection_pool = None

def get_db_connection():
    """AWS RDS 데이터베이스 연결 (커넥션 풀 사용)"""
    global connection_pool
    
    # 커넥션 풀이 초기화되지 않았다면 초기화
    if connection_pool is None:
        init_connection_pool()
    
    if connection_pool is None:
        print("❌ 커넥션 풀을 사용할 수 없습니다. 직접 연결을 시도합니다.")
        return get_direct_connection()
    
    try:
        connection = connection_pool.get_connection()
        if connection.is_connected():
            return connection
        else:
            print("❌ 커넥션 풀에서 유효하지 않은 연결을 받았습니다.")
            return None
            
    except Error as e:
        print(f"❌ 커넥션 풀 연결 오류: {e}")
        return get_direct_connection()

def get_direct_connection():
    """직접 데이터베이스 연결 (풀을 사용할 수 없을 때)"""
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            autocommit=False,
            charset='utf8mb4',
            use_unicode=True,
            connect_timeout=10
        )
        
        if connection.is_connected():
            print("✅ 직접 AWS RDS 연결 성공")
            return connection
        else:
            print("❌ AWS RDS 연결 실패")
            return None
            
    except Error as e:
        print(f"❌ 직접 연결 오류: {e}")
        return None

def safe_json_serialize(obj):
    """JSON 직렬화 안전하게 처리"""
    if obj is None:
        return None
    
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.strftime('%H:%M:%S')
    elif isinstance(obj, timedelta):
        # timedelta를 시간:분:초 형식으로 변환
        total_seconds = int(obj.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return obj

def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("AWS RDS 연결 테스트 시작...")
    
    try:
        connection = get_db_connection()
        if not connection:
            print("❌ 데이터베이스 연결 실패")
            return False
        
        cursor = connection.cursor(dictionary=True)
        
        # 기본 연결 테스트
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ 기본 연결 테스트: {result}")
        
        # 현재 데이터베이스 확인
        cursor.execute("SELECT DATABASE() as current_db")
        db_result = cursor.fetchone()
        print(f"✅ 현재 데이터베이스: {db_result['current_db']}")
        
        # 데이터베이스 목록 확인
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        db_names = [db['Database'] for db in databases]
        print(f"✅ 사용 가능한 데이터베이스: {db_names}")
        
        connection.close()
        print("✅ AWS RDS 연결 테스트 성공!")
        return True
        
    except Error as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

# 모듈 로드 시 환경변수 확인
if __name__ == "__main__":
    test_database_connection()