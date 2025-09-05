# CloudJet MSA Redis 캐시 서비스
# 항공편 검색 결과 캐싱, 세션 관리 등 성능 최적화용
import redis
import json
import os
from typing import Optional, List, Dict, Any

class CacheService:
    def __init__(self):
        # Redis 연결 설정 (환경변수 필수)
        self.redis_host = os.environ.get('REDIS_HOST')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))  # 표준 포트는 기본값 유지
        self.redis_db = int(os.environ.get('REDIS_DB', 0))         # DB 0은 표준이므로 기본값 유지
        self.redis_password = os.environ.get('REDIS_PASSWORD', None)
        
        # TLS/SSL 설정 (ElastiCache용)
        self.redis_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
        
        # 캐시 TTL 설정 (환경변수에서)
        self.default_ttl = int(os.environ.get('CACHE_TTL', 300))
        self.search_cache_ttl = int(os.environ.get('SEARCH_CACHE_TTL', 600))
        
        # Redis 연결 필수 환경변수 확인
        if not self.redis_host:
            print("❌ REDIS_HOST 환경변수가 설정되지 않았습니다.")
            self.is_available = False
            self.redis_client = None
            return
        
        # Redis 클라이언트 초기화
        try:
            # TLS 설정이 활성화된 경우 SSL 파라미터 추가
            redis_params = {
                'host': self.redis_host,
                'port': self.redis_port,
                'db': self.redis_db,
                'password': self.redis_password,
                'decode_responses': True,
                'socket_timeout': 30,
                'socket_connect_timeout': 30
            }
            
            # ElastiCache TLS 연결 설정
            print(f"🔍 SSL 설정 확인: redis_ssl={self.redis_ssl}, env_value='{os.environ.get('REDIS_SSL')}'")
            if self.redis_ssl:
                redis_params.update({
                    'ssl': True,
                    'ssl_check_hostname': False,
                    'ssl_cert_reqs': None
                })
                print(f"🔒 TLS 모드로 Redis 연결 시도: {self.redis_host}:{self.redis_port}")
            else:
                print(f"⚠️  일반 모드로 Redis 연결 시도: {self.redis_host}:{self.redis_port}")
            
            self.redis_client = redis.Redis(**redis_params)
            # 연결 테스트
            self.redis_client.ping()
            self.is_available = True
            print(f"✅ Redis 연결 성공: {self.redis_host}:{self.redis_port} (DB: {self.redis_db})")
        except Exception as e:
            print(f"❌ Redis 연결 실패: {e}")
            print("캐싱 없이 진행됩니다.")
            self.redis_client = None
            self.is_available = False
    
    def _generate_flight_cache_key(self, departure: str, arrival: str, date: str) -> str:
        """항공편 검색 캐시 키 생성"""
        return f"flights:{departure}:{arrival}:{date}"
    
    def get_flights_cache(self, departure: str, arrival: str, date: str) -> Optional[List[Dict]]:
        """항공편 검색 결과 캐시 조회"""
        if not self.is_available:
            return None
            
        try:
            key = self._generate_flight_cache_key(departure, arrival, date)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                flights = json.loads(cached_data)
                print(f"캐시 히트: {key} ({len(flights)}개 항공편)")
                return flights
            
            return None
        except Exception as e:
            print(f"캐시 조회 오류: {e}")
            return None
    
    def set_flights_cache(self, departure: str, arrival: str, date: str, 
                         flights: List[Dict], ttl: int = None) -> bool:
        """항공편 검색 결과 캐시 저장"""
        if not self.is_available:
            return False
        
        # TTL이 지정되지 않으면 환경변수에서 가져온 기본값 사용
        if ttl is None:
            ttl = self.search_cache_ttl
            
        try:
            key = self._generate_flight_cache_key(departure, arrival, date)
            cached_data = json.dumps(flights, ensure_ascii=False)
            
            result = self.redis_client.setex(key, ttl, cached_data)
            if result:
                print(f"캐시 저장: {key} ({len(flights)}개 항공편, TTL: {ttl}초)")
            return result
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
            return False
    
    def invalidate_flights_cache(self, departure: str = None, arrival: str = None, date: str = None):
        """항공편 캐시 무효화"""
        if not self.is_available:
            return
            
        try:
            if departure and arrival and date:
                # 특정 검색 결과 캐시 삭제
                key = self._generate_flight_cache_key(departure, arrival, date)
                self.redis_client.delete(key)
                print(f"캐시 무효화: {key}")
            else:
                # 모든 항공편 캐시 삭제
                pattern = "flights:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    print(f"모든 항공편 캐시 무효화: {len(keys)}개 키")
        except Exception as e:
            print(f"캐시 무효화 오류: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 상태 정보 조회"""
        if not self.is_available:
            return {"available": False, "message": "Redis 연결 불가"}
            
        try:
            info = self.redis_client.info()
            keys_count = len(self.redis_client.keys("flights:*"))
            
            return {
                "available": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "flight_cache_keys": keys_count,
                "connected_clients": info.get("connected_clients"),
                "default_ttl": self.default_ttl,
                "search_cache_ttl": self.search_cache_ttl
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

# 글로벌 캐시 서비스 인스턴스 (옵션)
cache_service = CacheService()