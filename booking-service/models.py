# Booking Service Models - 수정됨
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_connection, safe_json_serialize
from mysql.connector import Error
import random
import string

def generate_booking_number():
    """예약 번호 생성"""
    return 'CJ' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Booking:
    @staticmethod
    def create_booking(user_id, schedule_id, passengers, contact_info, payment_method, total_amount, seats=None):
        """새 예약 생성"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor()
            
            # 트랜잭션 시작
            connection.start_transaction()
            
            try:
                # 항공편 좌석 확인
                cursor.execute("""
                    SELECT available_seats FROM flight_schedules 
                    WHERE schedule_id = %s AND status = 'ACTIVE'
                """, (schedule_id,))
                
                result = cursor.fetchone()
                if not result or result[0] < len(passengers):
                    connection.rollback()
                    return None, "선택한 항공편의 좌석이 부족합니다."
                
                # 예약 번호 생성
                booking_number = generate_booking_number()
                
                # 좌석 중복 확인 (단일 예약의 경우)
                selected_seat = None
                if seats and len(seats) == 1:
                    selected_seat = seats[0]
                    cursor.execute("""
                        SELECT p.seat_number 
                        FROM passengers p
                        JOIN bookings b ON p.booking_id = b.booking_id
                        JOIN flight_schedules fs ON b.schedule_id = fs.schedule_id
                        WHERE fs.flight_id = (SELECT flight_id FROM flight_schedules WHERE schedule_id = %s)
                        AND fs.flight_date = (SELECT flight_date FROM flight_schedules WHERE schedule_id = %s)
                        AND p.seat_number = %s
                        AND b.status = 'CONFIRMED'
                    """, (schedule_id, schedule_id, selected_seat))
                    
                    if cursor.fetchone():
                        connection.rollback()
                        return None, f"이미 선택된 좌석입니다: {selected_seat}"

                # 예약 생성
                booking_query = """
                    INSERT INTO bookings 
                    (booking_number, user_id, schedule_id, seat_number, total_amount, contact_email, contact_phone, payment_method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(booking_query, (
                    booking_number,
                    user_id,
                    schedule_id,
                    selected_seat,
                    total_amount,
                    contact_info['email'],
                    contact_info['phone'],
                    payment_method
                ))
                
                booking_id = cursor.lastrowid
                
                # 승객 정보 저장 (단일 예약의 경우)
                passenger_query = """
                    INSERT INTO passengers (booking_id, name_kor, name_eng, birth_date, gender, seat_number)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                for i, passenger in enumerate(passengers):
                    cursor.execute(passenger_query, (
                        booking_id,
                        passenger['name'],
                        passenger['nameEn'],
                        passenger['birth'],
                        passenger['gender'],
                        selected_seat  # 모든 승객이 같은 좌석 사용
                    ))
                
                # 좌석 수 업데이트
                cursor.execute("""
                    UPDATE flight_schedules 
                    SET available_seats = available_seats - %s 
                    WHERE schedule_id = %s
                """, (len(passengers), schedule_id))
                
                connection.commit()
                return { 'booking_number': booking_number, 'booking_id': booking_id }, None
                
            except Exception as e:
                connection.rollback()
                raise e
                
        except Error as e:
            return None, f"예약 처리 중 오류가 발생했습니다: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def get_user_bookings(user_id):
        """사용자의 예약 목록 조회"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            
            # 사용자의 예약 목록 조회
            booking_query = """
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
                    fs.flight_date,
                    f.flight_id,
                    f.airline,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.aircraft,
                    da.airport_name as departure_name,
                    aa.airport_name as arrival_name
                FROM bookings b
                JOIN flight_schedules fs ON b.schedule_id = fs.schedule_id
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports da ON f.departure_airport = da.airport_code
                JOIN airports aa ON f.arrival_airport = aa.airport_code
                WHERE b.user_id = %s
                ORDER BY b.created_at DESC
            """
            
            cursor.execute(booking_query, (user_id,))
            bookings = cursor.fetchall()
            
            # 각 예약의 승객 정보 조회
            for booking in bookings:
                cursor.execute("""
                    SELECT name_kor, name_eng, birth_date, gender, seat_number
                    FROM passengers
                    WHERE booking_id = %s
                """, (booking['booking_id'],))
                
                passengers = cursor.fetchall()
                booking['passengers'] = passengers
                
                # 날짜/시간 포맷 변환
                booking['flight_date'] = safe_json_serialize(booking['flight_date'])
                booking['departure_time'] = safe_json_serialize(booking['departure_time'])
                booking['arrival_time'] = safe_json_serialize(booking['arrival_time'])
                booking['duration'] = safe_json_serialize(booking['duration'])
                booking['created_at'] = safe_json_serialize(booking['created_at'])
            
            return bookings, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def get_booking_by_number(booking_number):
        """예약 번호로 예약 정보 조회"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor(dictionary=True)
            
            # 예약 번호로 예약 정보 조회
            booking_query = """
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
                    fs.flight_date,
                    f.flight_id,
                    f.airline,
                    f.departure_airport,
                    f.arrival_airport,
                    f.departure_time,
                    f.arrival_time,
                    f.duration,
                    f.aircraft,
                    da.airport_name as departure_name,
                    aa.airport_name as arrival_name,
                    u.name as user_name
                FROM bookings b
                JOIN flight_schedules fs ON b.schedule_id = fs.schedule_id
                JOIN flights f ON fs.flight_id = f.flight_id
                JOIN airports da ON f.departure_airport = da.airport_code
                JOIN airports aa ON f.arrival_airport = aa.airport_code
                JOIN users u ON b.user_id = u.user_id
                WHERE b.booking_number = %s
            """
            
            cursor.execute(booking_query, (booking_number,))
            booking = cursor.fetchone()
            
            if not booking:
                return None, "예약을 찾을 수 없습니다."
            
            # 승객 정보 조회
            cursor.execute("""
                SELECT name_kor, name_eng, birth_date, gender, seat_number
                FROM passengers
                WHERE booking_id = %s
            """, (booking['booking_id'],))
            
            passengers = cursor.fetchall()
            booking['passengers'] = passengers
            
            # 날짜/시간 포맷 변환
            booking['flight_date'] = safe_json_serialize(booking['flight_date'])
            booking['departure_time'] = safe_json_serialize(booking['departure_time'])
            booking['arrival_time'] = safe_json_serialize(booking['arrival_time'])
            booking['duration'] = safe_json_serialize(booking['duration'])
            booking['created_at'] = safe_json_serialize(booking['created_at'])
            
            return booking, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def get_occupied_seats(schedule_id):
        """특정 항공편의 예약된 좌석 조회 - 실제 예약된 좌석만 반환"""
        try:
            connection = get_db_connection()
            if not connection:
                return None, "데이터베이스 연결 오류"
            
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT DISTINCT p.seat_number 
                FROM passengers p
                JOIN bookings b ON p.booking_id = b.booking_id
                WHERE b.schedule_id = %s 
                AND b.status = 'CONFIRMED'
                AND p.seat_number IS NOT NULL
                ORDER BY p.seat_number
            """, (schedule_id,))
            
            occupied_seats = [row[0] for row in cursor.fetchall()]
            return occupied_seats, None
            
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def cancel_booking(user_id, booking_number):
        """예약 취소"""
        try:
            connection = get_db_connection()
            if not connection:
                return False, "데이터베이스 연결 오류"
            
            cursor = connection.cursor()
            
            # 트랜잭션 시작
            connection.start_transaction()
            
            try:
                # 예약 정보 확인
                cursor.execute("""
                    SELECT b.booking_id, b.schedule_id, COUNT(p.passenger_id) as passenger_count
                    FROM bookings b
                    LEFT JOIN passengers p ON b.booking_id = p.booking_id
                    WHERE b.booking_number = %s AND b.user_id = %s AND b.status = 'CONFIRMED'
                    GROUP BY b.booking_id, b.schedule_id
                """, (booking_number, user_id))
                
                result = cursor.fetchone()
                if not result:
                    connection.rollback()
                    return False, "취소 가능한 예약을 찾을 수 없습니다."
                
                booking_id, schedule_id, passenger_count = result
                
                # 예약 상태 업데이트
                cursor.execute("""
                    UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s
                """, (booking_id,))
                
                # 좌석 수 복구
                cursor.execute("""
                    UPDATE flight_schedules 
                    SET available_seats = available_seats + %s 
                    WHERE schedule_id = %s
                """, (passenger_count, schedule_id))
                
                connection.commit()
                return True, None
                
            except Exception as e:
                connection.rollback()
                raise e
                
        except Error as e:
            return False, f"예약 취소 중 오류가 발생했습니다: {str(e)}"
        finally:
            if connection:
                connection.close()
