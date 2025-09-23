# Booking Service Routes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify

def get_models():
    from models import Booking
    return Booking

def get_auth():
    from shared.auth import token_required
    return token_required

booking_bp = Blueprint('bookings', __name__)

@booking_bp.route('', methods=['POST'])
def create_booking():
    """예약 생성"""
    try:
        from app import get_client_ip
        Booking = get_models()
        client_ip = get_client_ip(request)

        # 토큰 검증
        token = request.headers.get('Authorization')
        if not token:
            print(f"[BOOKING-SERVICE] 예약 생성 실패 - 토큰 없음 | IP: {client_ip}")
            return jsonify({'message': '토큰이 없습니다.'}), 401

        if token.startswith('Bearer '):
            token = token.split(' ')[1]

        import jwt
        from shared.auth import SECRET_KEY
        data_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = data_token['user_id']

        data = request.get_json()

        required_fields = ['scheduleId', 'passengers', 'contactInfo', 'paymentMethod', 'totalAmount']
        for field in required_fields:
            if field not in data:
                print(f"[BOOKING-SERVICE] 예약 생성 실패 - 누락된 필드: {field} | 사용자 ID: {current_user_id} | IP: {client_ip}")
                return jsonify({'message': f'{field}는 필수 입력 항목입니다.'}), 400

        booking_result, error = Booking.create_booking(
            current_user_id, data['scheduleId'],
            data['passengers'], data['contactInfo'],
            data['paymentMethod'], data['totalAmount'],
            data.get('seats')
        )

        if error:
            print(f"[BOOKING-SERVICE] 예약 생성 실패 - 사용자 ID: {current_user_id} | 항공편 ID: {data.get('scheduleId', 'N/A')} | 오류: {error} | IP: {client_ip}")
            return jsonify({'message': error}), 400

        # 예약 성공 로깅
        passengers_info = ', '.join([f"{p.get('name', 'N/A')}" for p in data['passengers']])
        print(f"[BOOKING-SERVICE] 예약 생성 성공 - 예약번호: {booking_result['booking_number']} | 사용자 ID: {current_user_id} | 항공편 ID: {data['scheduleId']} | 승객: {passengers_info} | 총 금액: {data['totalAmount']}원 | 결제방법: {data['paymentMethod']} | IP: {client_ip}")

        return jsonify({
            'message': '예약이 성공적으로 생성되었습니다.',
            'booking_number': booking_result['booking_number'],
            'booking_id': booking_result['booking_id'],
            'success': True
        }), 201

    except Exception as e:
        print(f"[BOOKING-SERVICE] 예약 생성 서버 오류: {str(e)} | IP: {get_client_ip(request)}")
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@booking_bp.route('/occupied-seats/<int:schedule_id>', methods=['GET'])
def get_occupied_seats(schedule_id):
    """특정 항공편의 예약된 좌석 조회"""
    try:
        Booking = get_models()
        occupied_seats, error = Booking.get_occupied_seats(schedule_id)
        
        if error:
            return jsonify({'message': error}), 500
        
        return jsonify({'occupied_seats': occupied_seats}), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@booking_bp.route('', methods=['GET'])
def get_user_bookings():
    """사용자 예약 목록 조회"""
    try:
        Booking = get_models()
        
        # 토큰 검증
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '토큰이 없습니다.'}), 401
            
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        import jwt
        from shared.auth import SECRET_KEY
        data_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = data_token['user_id']
        
        bookings, error = Booking.get_user_bookings(current_user_id)
        
        if error:
            return jsonify({'message': error}), 500
        
        return jsonify({'bookings': bookings}), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@booking_bp.route('/<booking_number>/cancel', methods=['POST'])
def cancel_booking(booking_number):
    """예약 취소"""
    try:
        from app import get_client_ip
        Booking = get_models()
        client_ip = get_client_ip(request)

        # 토큰 검증
        token = request.headers.get('Authorization')
        if not token:
            print(f"[BOOKING-SERVICE] 예약 취소 실패 - 토큰 없음 | 예약번호: {booking_number} | IP: {client_ip}")
            return jsonify({'message': '토큰이 없습니다.'}), 401

        if token.startswith('Bearer '):
            token = token.split(' ')[1]

        import jwt
        from shared.auth import SECRET_KEY
        data_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = data_token['user_id']

        success, error = Booking.cancel_booking(current_user_id, booking_number)

        if not success:
            if "찾을 수 없습니다" in error:
                print(f"[BOOKING-SERVICE] 예약 취소 실패 - 예약번호 찾을 수 없음: {booking_number} | 사용자 ID: {current_user_id} | IP: {client_ip}")
                return jsonify({'message': error}), 404
            print(f"[BOOKING-SERVICE] 예약 취소 실패 - 예약번호: {booking_number} | 사용자 ID: {current_user_id} | 오류: {error} | IP: {client_ip}")
            return jsonify({'message': error}), 400

        print(f"[BOOKING-SERVICE] 예약 취소 성공 - 예약번호: {booking_number} | 사용자 ID: {current_user_id} | IP: {client_ip}")

        return jsonify({
            'message': '예약이 성공적으로 취소되었습니다.',
            'success': True,
            'booking_number': booking_number
        }), 200

    except Exception as e:
        print(f"[BOOKING-SERVICE] 예약 취소 서버 오류: {str(e)} | 예약번호: {booking_number} | IP: {get_client_ip(request)}")
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@booking_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'service': 'booking-service',
        'port': 5003
    }), 200

# version 10.0.0