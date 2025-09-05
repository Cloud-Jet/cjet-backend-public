# Flight Service Models - 수정된 버전
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_connection, safe_json_serialize
from mysql.connector import Error
from shared.redis_client import CacheService

class Flight:
    @staticmethod
    def search_flights(departure, arrival, date):
        """캐싱이 적용된 항공편 검색"""
        
        # 캐시 확인 (새로 추가)
        cache_service = CacheService()
        cached_flights = cache_service.get_flights_cache(departure, arrival, date)
        
        if cached_flights:
            print(f"캐시에서 항공편 조회: {departure} -> {arrival}, {date}")
            return cached_flights, None
    
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            
            # 항공편 검색 쿼리 (할인 정보 포함)
            search_query = """
                SELECT 
                    fs.schedule_id,
                    f.flight_id,
                    f.airline,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.aircraft,
                    fs.current_price as original_price,
                    CASE 
                        WHEN fd.discount_percentage IS NOT NULL THEN 
                            ROUND(fs.current_price * (1 - fd.discount_percentage / 100))
                        ELSE fs.current_price
                    END as price,
                    fs.available_seats,
                    fs.flight_date as date,
                    da.airport_name as departure_name,
                    aa.airport_name as arrival_name,
                    fd.discount_percentage,
                    CASE WHEN fd.discount_percentage IS NOT NULL THEN TRUE ELSE FALSE END as has_discount
                FROM flight_schedules fs
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports da ON f.departure_airport = da.airport_code
                JOIN airports aa ON f.arrival_airport = aa.airport_code
                LEFT JOIN flight_discounts fd ON fs.schedule_id = fd.schedule_id AND fd.status = 'ACTIVE'
                WHERE f.departure_airport = %s 
                AND f.arrival_airport = %s 
                AND fs.flight_date = %s
                AND fs.status = 'ACTIVE'
                AND fs.available_seats > 0
                ORDER BY price, f.departure_time
            """
            
            cursor.execute(search_query, (departure, arrival, date))
            flights = cursor.fetchall()
            
            # 데이터 변환
            for flight in flights:
                for key, value in flight.items():
                    flight[key] = safe_json_serialize(value)
            
            # 시간 포맷 변환 및 timedelta 처리
            for flight in flights:
                flight['departureTime'] = safe_json_serialize(flight['departure_time'])
                flight['arrivalTime'] = safe_json_serialize(flight['arrival_time'])
                flight['duration'] = safe_json_serialize(flight['duration'])
                flight['date'] = safe_json_serialize(flight['date'])
                
                # 프론트엔드 호환성을 위한 별칭 추가
                flight['flightId'] = flight['flight_id']
                flight['departureAirport'] = flight['departure_airport']
                flight['arrivalAirport'] = flight['arrival_airport']
                # 원본 필드는 유지 (API 응답에서 사용)
                
            # 결과를 캐시에 저장 (새로 추가)
            if flights:
                cache_service.set_flights_cache(departure, arrival, date, flights, 300)  # 5분 캐시
                print(f"항공편 검색 결과 캐시 저장: {len(flights)}개")
            
            return flights, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def get_featured_flights():
        """오늘의 특가 항공편 조회 (할인된 항공편만)"""
        try:
            connection = get_db_connection()
            if not connection:
                print("Featured flights: 데이터베이스 연결 실패")
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            if not cursor:
                print("Featured flights: 커서 생성 실패")
                return None, "커서 생성 오류"
            
            query = """
                SELECT DISTINCT
                    fs.schedule_id,
                    f.flight_id,
                    f.airline,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.aircraft,
                    fs.current_price as original_price,
                    fs.available_seats,
                    fs.flight_date as date,
                    da.airport_name as departure_name,
                    aa.airport_name as arrival_name,
                    fd.discount_percentage
                FROM flight_schedules fs
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports da ON f.departure_airport = da.airport_code
                JOIN airports aa ON f.arrival_airport = aa.airport_code
                JOIN flight_discounts fd ON fs.schedule_id = fd.schedule_id
                WHERE fs.status = 'ACTIVE'
                AND fs.available_seats > 0
                AND fd.status = 'ACTIVE'
                AND fs.flight_date >= CURDATE()
                ORDER BY fd.discount_percentage DESC, fs.flight_date
                LIMIT 6
            """
            
            cursor.execute(query)
            flights = cursor.fetchall()
            
            # 할인 가격 계산 및 데이터 변환
            for flight in flights:
                discount_percentage = flight['discount_percentage']
                original_price = flight['original_price']
                discounted_price = int(original_price * (100 - discount_percentage) / 100)
                
                flight['price'] = discounted_price
                flight['discounted_price'] = discounted_price
                flight['has_discount'] = True
                
                # 시간 데이터 변환
                flight['departureTime'] = safe_json_serialize(flight['departure_time'])
                flight['arrivalTime'] = safe_json_serialize(flight['arrival_time'])
                flight['date'] = safe_json_serialize(flight['date'])
                flight['duration'] = safe_json_serialize(flight['duration'])
                
                # 프론트엔드 호환성
                flight['flightId'] = flight['flight_id']
                flight['departureAirport'] = flight['departure_airport']
                flight['arrivalAirport'] = flight['arrival_airport']
                
                # 원본 필드 제거
                flight.pop('departure_time', None)
                flight.pop('arrival_time', None)
            
            return flights, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_promotions():
        """프로모션 항공편 조회 (API용)"""
        try:
            connection = get_db_connection()
            if not connection:
                print("Promotions: 데이터베이스 연결 실패")
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            if not cursor:
                print("Promotions: 커서 생성 실패")
                return None, "커서 생성 오류"
            
            query = """
                SELECT DISTINCT
                    fs.schedule_id,
                    f.flight_id,
                    f.airline,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.aircraft,
                    fs.current_price as original_price,
                    fs.available_seats,
                    fs.flight_date,
                    da.airport_name as departure_name,
                    aa.airport_name as arrival_name,
                    fd.discount_percentage,
                    ROUND(fs.current_price * (1 - fd.discount_percentage / 100)) as discounted_price
                FROM flight_schedules fs
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports da ON f.departure_airport = da.airport_code
                JOIN airports aa ON f.arrival_airport = aa.airport_code
                JOIN flight_discounts fd ON fs.schedule_id = fd.schedule_id
                WHERE fs.status = 'ACTIVE'
                AND fs.available_seats > 0
                AND fd.status = 'ACTIVE'
                AND fs.flight_date >= CURDATE()
                ORDER BY fd.discount_percentage DESC, fs.flight_date
                LIMIT 6
            """
            
            cursor.execute(query)
            promotions = cursor.fetchall()
            
            # 데이터 변환
            for promo in promotions:
                for key, value in promo.items():
                    promo[key] = safe_json_serialize(value)
            
            return promotions, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

class Airport:
    @staticmethod
    def get_all_airports():
        """모든 공항 정보 조회"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT airport_code, airport_name, city, country FROM airports ORDER BY airport_name")
            airports = cursor.fetchall()
            
            return airports, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
