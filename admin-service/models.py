# Admin Service Models - 스케줄 기반 할인 시스템으로 업데이트
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_connection, safe_json_serialize
from mysql.connector import Error
from datetime import datetime, date, time, timedelta

class Flight:
    @staticmethod
    def get_all_flights_admin():
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT f.*, 
                       dep.airport_name as departure_airport_name,
                       arr.airport_name as arrival_airport_name
                FROM flights f
                JOIN airports dep ON f.departure_airport = dep.airport_code
                JOIN airports arr ON f.arrival_airport = arr.airport_code
                WHERE f.is_active = TRUE
                ORDER BY f.departure_time
            """
            cursor.execute(query)
            flights = cursor.fetchall()
            
            # JSON 직렬화 가능하도록 데이터 변환
            for flight in flights:
                # 시간 필드 문자열로 변환
                if flight.get('departure_time'):
                    if isinstance(flight['departure_time'], time):
                        flight['departure_time'] = flight['departure_time'].strftime('%H:%M')
                    else:
                        flight['departure_time'] = str(flight['departure_time'])
                        
                if flight.get('arrival_time'):
                    if isinstance(flight['arrival_time'], time):
                        flight['arrival_time'] = flight['arrival_time'].strftime('%H:%M')
                    else:
                        flight['arrival_time'] = str(flight['arrival_time'])
                
                # 기타 필드 안전하게 변환
                for key, value in flight.items():
                    flight[key] = safe_json_serialize(value)
                
            return flights, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def _compute_duration_str(departure_time_str: str, arrival_time_str: str) -> str:
        try:
            dep = datetime.strptime(departure_time_str, '%H:%M').time()
            arr = datetime.strptime(arrival_time_str, '%H:%M').time()
            # 날짜는 임의 동일 날짜로 두고, 도착이 출발보다 이르면 +24h 처리
            base_day = date(2000, 1, 1)
            dep_dt = datetime.combine(base_day, dep)
            arr_dt = datetime.combine(base_day, arr)
            if arr_dt <= dep_dt:
                arr_dt = arr_dt + timedelta(days=1)
            delta = arr_dt - dep_dt
            total_minutes = int(delta.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours}시간 {minutes}분"
        except Exception:
            return '3시간 00분'

    @staticmethod
    def create_flight(flight_id, departure_airport, arrival_airport,
                      departure_time, arrival_time, aircraft, base_price,
                      airline='CloudJet', total_seats=180):
        """항공편 생성 (기존 라우트 호환). duration은 출발/도착 시간으로 계산."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # 공항 존재 확인
            cursor.execute("SELECT airport_code FROM airports WHERE airport_code = %s", (departure_airport,))
            if not cursor.fetchone():
                return None, '출발 공항 코드가 유효하지 않습니다.'
            cursor.execute("SELECT airport_code FROM airports WHERE airport_code = %s", (arrival_airport,))
            if not cursor.fetchone():
                return None, '도착 공항 코드가 유효하지 않습니다.'

            duration = Flight._compute_duration_str(str(departure_time), str(arrival_time))

            insert_sql = """
                INSERT INTO flights (flight_id, airline, departure_airport, arrival_airport,
                                     departure_time, arrival_time, duration, aircraft, base_price, total_seats, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """
            cursor.execute(insert_sql, (
                flight_id, airline, departure_airport, arrival_airport,
                departure_time, arrival_time, duration, aircraft, base_price, total_seats
            ))
            connection.commit()
            return flight_id, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def delete_flight(flight_id):
        """항공편 비활성화 (소프트 삭제)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("UPDATE flights SET is_active = FALSE WHERE flight_id = %s", (flight_id,))
            connection.commit()
            if cursor.rowcount == 0:
                return False, '항공편을 찾을 수 없습니다.'
            return True, None
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def create_flight_with_schedules(payload: dict):
        """항공편 + 스케줄을 하나의 트랜잭션으로 생성
        payload 예시:
        {
          "flight": {
            "flight_id": "CJ201",
            "departure_airport": "ICN",
            "arrival_airport": "NRT",
            "departure_time": "09:00",
            "arrival_time": "11:45",
            "aircraft": "Boeing 737-800",
            "base_price": 320000,
            "total_seats": 180,
            "airline": "CloudJet"
          },
          "schedule": {
            "mode": "single" | "range",
            "date": "2025-08-20",
            "start_date": "2025-08-20",
            "end_date": "2025-08-27",
            "current_price": 300000,
            "available_seats": 180,
            "overwrite": false
          }
        }
        """
        try:
            connection = get_db_connection()
            if not connection:
                return None, '데이터베이스 연결 오류'
            cursor = connection.cursor()

            flight = payload.get('flight') or {}
            schedule = payload.get('schedule') or {}

            # 필수값 검증
            required_f = ['flight_id', 'departure_airport', 'arrival_airport', 'departure_time', 'arrival_time', 'aircraft', 'base_price']
            for f in required_f:
                if f not in flight:
                    return None, f"flight.{f}는 필수입니다."

            mode = (schedule.get('mode') or 'single').lower()
            if mode not in ('single', 'range'):
                return None, 'schedule.mode는 single 또는 range여야 합니다.'

            # 공항 검증
            cursor.execute("SELECT 1 FROM airports WHERE airport_code=%s", (flight['departure_airport'],))
            if not cursor.fetchone():
                return None, '출발 공항 코드가 유효하지 않습니다.'
            cursor.execute("SELECT 1 FROM airports WHERE airport_code=%s", (flight['arrival_airport'],))
            if not cursor.fetchone():
                return None, '도착 공항 코드가 유효하지 않습니다.'

            # 트랜잭션은 autocommit=False 환경에서 첫 쿼리 실행 시 자동 시작됨
            # 별도의 start_transaction 호출은 "Transaction already in progress"를 유발할 수 있어 호출하지 않음

            # flights upsert (존재하면 업데이트, 없으면 생성)
            duration = Flight._compute_duration_str(str(flight['departure_time']), str(flight['arrival_time']))
            total_seats = int(flight.get('total_seats') or 180)
            airline = flight.get('airline') or 'CloudJet'

            upsert_sql = (
                "INSERT INTO flights (flight_id, airline, departure_airport, arrival_airport, departure_time, arrival_time, duration, aircraft, base_price, total_seats, is_active) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE) "
                "ON DUPLICATE KEY UPDATE airline=VALUES(airline), departure_airport=VALUES(departure_airport), arrival_airport=VALUES(arrival_airport), "
                "departure_time=VALUES(departure_time), arrival_time=VALUES(arrival_time), duration=VALUES(duration), aircraft=VALUES(aircraft), base_price=VALUES(base_price), total_seats=VALUES(total_seats), is_active=TRUE"
            )
            cursor.execute(upsert_sql, (
                flight['flight_id'], airline, flight['departure_airport'], flight['arrival_airport'],
                flight['departure_time'], flight['arrival_time'], duration, flight['aircraft'], int(flight['base_price']), total_seats
            ))

            # 스케줄 생성 날짜 집합 계산
            overwrite = bool(schedule.get('overwrite', False))
            if mode == 'single':
                if not schedule.get('date'):
                    connection.rollback()
                    return None, 'schedule.date는 필수입니다.'
                start_d = end_d = datetime.strptime(schedule['date'], '%Y-%m-%d').date()
            else:
                if not schedule.get('start_date') or not schedule.get('end_date'):
                    connection.rollback()
                    return None, 'schedule.start_date, schedule.end_date는 필수입니다.'
                start_d = datetime.strptime(schedule['start_date'], '%Y-%m-%d').date()
                end_d = datetime.strptime(schedule['end_date'], '%Y-%m-%d').date()
                if end_d < start_d:
                    connection.rollback()
                    return None, '종료일이 시작일보다 빠릅니다.'
                # 최대 90일 제한
                if (end_d - start_d).days > 90:
                    connection.rollback()
                    return None, '스케줄 생성 기간은 최대 90일까지만 허용됩니다.'

            current_price = int(schedule.get('current_price') or flight['base_price'])
            available_seats = int(schedule.get('available_seats') or total_seats)

            created = 0
            skipped = 0
            dates = []
            d = start_d
            while d <= end_d:
                dates.append(d)
                d += timedelta(days=1)

            for d in dates:
                if overwrite:
                    insert_sql = (
                        "INSERT INTO flight_schedules (flight_id, flight_date, current_price, available_seats, status) "
                        "VALUES (%s, %s, %s, %s, 'ACTIVE') "
                        "ON DUPLICATE KEY UPDATE current_price=VALUES(current_price), available_seats=VALUES(available_seats), status='ACTIVE'"
                    )
                    cursor.execute(insert_sql, (flight['flight_id'], d.strftime('%Y-%m-%d'), current_price, available_seats))
                    created += 1
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO flight_schedules (flight_id, flight_date, current_price, available_seats, status) VALUES (%s, %s, %s, %s, 'ACTIVE')",
                            (flight['flight_id'], d.strftime('%Y-%m-%d'), current_price, available_seats)
                        )
                        created += 1
                    except Error as ie:
                        # 중복 등으로 실패 시 스킵
                        skipped += 1

            connection.commit()
            return {
                'flight_id': flight['flight_id'],
                'created_schedules': created,
                'skipped': skipped,
                'total_requested': len(dates)
            }, None
        except Error as e:
            if 'connection' in locals() and connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if 'connection' in locals() and connection:
                connection.close()

class Promotion:
    @staticmethod
    def get_available_schedules():
        """할인 가능한 스케줄 목록 조회"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 미래 항공편 스케줄 조회 (할인 정보 포함)
            query = """
                SELECT 
                    fs.schedule_id,
                    fs.flight_id,
                    fs.flight_date,
                    fs.current_price,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.airline,
                    f.aircraft,
                    dep.airport_name as departure_name,
                    arr.airport_name as arrival_name,
                    fd.discount_percentage,
                    fd.status as discount_status
                FROM flight_schedules fs
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports dep ON f.departure_airport = dep.airport_code
                JOIN airports arr ON f.arrival_airport = arr.airport_code
                LEFT JOIN flight_discounts fd ON fs.schedule_id = fd.schedule_id AND fd.status = 'ACTIVE'
                WHERE fs.flight_date >= CURDATE()
                AND fs.status = 'ACTIVE'
                ORDER BY fs.flight_date, f.departure_time
            """
            
            cursor.execute(query)
            schedules = cursor.fetchall()
            
            # JSON 직렬화 가능하도록 데이터 변환
            for schedule in schedules:
                for key, value in schedule.items():
                    schedule[key] = safe_json_serialize(value)
                    
            return schedules, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_discounts():
        """현재 할인 목록 조회 (스케줄 기반)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    fd.discount_id,
                    fd.schedule_id,
                    fd.discount_percentage,
                    fd.status,
                    fd.created_at,
                    fs.flight_id,
                    fs.flight_date,
                    fs.current_price,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.airline,
                    dep.airport_name as departure_name,
                    arr.airport_name as arrival_name,
                    ROUND(fs.current_price * (1 - fd.discount_percentage / 100)) as discounted_price
                FROM flight_discounts fd
                JOIN flight_schedules fs ON fd.schedule_id = fs.schedule_id
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports dep ON f.departure_airport = dep.airport_code
                JOIN airports arr ON f.arrival_airport = arr.airport_code
                WHERE fd.status = 'ACTIVE'
                ORDER BY fd.created_at DESC
            """
            
            cursor.execute(query)
            discounts = cursor.fetchall()
            
            # JSON 직렬화 가능하도록 데이터 변환
            for discount in discounts:
                for key, value in discount.items():
                    discount[key] = safe_json_serialize(value)
                    
            return discounts, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def create_discount(schedule_id, discount_percentage):
        """스케줄별 할인 생성"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # 스케줄 존재 확인
            cursor.execute("SELECT schedule_id FROM flight_schedules WHERE schedule_id = %s", (schedule_id,))
            if not cursor.fetchone():
                return None, "항공편 스케줄을 찾을 수 없습니다."
            
            # 중복 할인 확인
            cursor.execute("""
                SELECT discount_id FROM flight_discounts 
                WHERE schedule_id = %s AND status = 'ACTIVE'
            """, (schedule_id,))
            
            if cursor.fetchone():
                return None, "해당 스케줄에 이미 할인이 설정되어 있습니다."
            
            # 할인 생성
            query = """
                INSERT INTO flight_discounts (schedule_id, discount_percentage, status)
                VALUES (%s, %s, 'ACTIVE')
            """
            
            cursor.execute(query, (schedule_id, discount_percentage))
            connection.commit()
            
            discount_id = cursor.lastrowid
            print(f"할인 생성 완료: ID {discount_id}, 스케줄 {schedule_id}, 할인율 {discount_percentage}%")
            
            return discount_id, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def delete_discount(discount_id):
        """할인 삭제"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # 할인 비활성화 (삭제 대신)
            cursor.execute("""
                UPDATE flight_discounts 
                SET status = 'INACTIVE' 
                WHERE discount_id = %s
            """, (discount_id,))
            connection.commit()
            
            if cursor.rowcount == 0:
                return False, "할인을 찾을 수 없습니다."
            
            print(f"할인 삭제 완료: {discount_id}")
            return True, None
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

class Booking:
    @staticmethod
    def get_all_bookings_admin():
        """관리자용 예약 목록 조회 - 상세 정보 포함"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT 
                    b.booking_id,
                    b.booking_number,
                    b.seat_number,
                    b.total_amount,
                    b.contact_email,
                    b.contact_phone,
                    b.payment_method,
                    b.status,
                    b.created_at,
                    u.name as customer_name,
                    u.email as user_email,
                    fs.flight_id,
                    fs.flight_date,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.airline,
                    dep.airport_name as departure_name,
                    arr.airport_name as arrival_name
                FROM bookings b
                JOIN users u ON b.user_id = u.user_id
                JOIN flight_schedules fs ON b.schedule_id = fs.schedule_id
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports dep ON f.departure_airport = dep.airport_code
                JOIN airports arr ON f.arrival_airport = arr.airport_code
                ORDER BY b.created_at DESC
            """
            cursor.execute(query)
            bookings = cursor.fetchall()
            
            # 각 예약의 승객 정보 추가
            for booking in bookings:
                cursor.execute("""
                    SELECT name_kor, name_eng, birth_date, gender, seat_number
                    FROM passengers
                    WHERE booking_id = %s
                """, (booking['booking_id'],))
                
                passengers = cursor.fetchall()
                booking['passengers'] = passengers
                
                # JSON 직렬화 가능하도록 데이터 변환
                for key, value in booking.items():
                    if key != 'passengers':
                        booking[key] = safe_json_serialize(value)
                    
            return bookings, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

class User:
    @staticmethod
    def get_user_profile(user_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, name, email, phone FROM users WHERE user_id = %s", 
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None, "사용자를 찾을 수 없습니다."
            return user, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
