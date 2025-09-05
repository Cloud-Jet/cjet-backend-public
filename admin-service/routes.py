# Admin Service Routes - DB 구조에 맞게 수정
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify
from models import Flight, Promotion, Booking, User
from shared.auth import token_required, admin_required

admin_bp = Blueprint('admin', __name__)

# 항공편 관리
@admin_bp.route('/flights', methods=['GET'])
@admin_required
def get_all_flights(current_user_id):
    """모든 항공편 조회"""
    try:
        flights, error = Flight.get_all_flights_admin()
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'flights': flights}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/flights', methods=['POST'])
@admin_required
def add_flight(current_user_id):
    """항공편 추가"""
    try:
        data = request.get_json()
        required_fields = ['flight_id', 'departure_airport', 'arrival_airport',
                          'departure_time', 'arrival_time', 'aircraft', 'base_price']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'{field}는 필수 입력 항목입니다.'}), 400
        
        flight_id, error = Flight.create_flight(
            data['flight_id'], data['departure_airport'], data['arrival_airport'],
            data['departure_time'], data['arrival_time'],
            data['aircraft'], data['base_price']
        )
        
        if error:
            return jsonify({'message': error}), 400
        
        return jsonify({'message': '항공편이 추가되었습니다.', 'flight_id': flight_id, 'success': True}), 201
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/flights-with-schedules', methods=['POST'])
@admin_required
def add_flight_with_schedules(current_user_id):
    """항공편 + 스케줄 동시 생성(트랜잭션)"""
    try:
        payload = request.get_json()
        result, error = Flight.create_flight_with_schedules(payload)
        if error:
            return jsonify({'message': error}), 400
        return jsonify({'success': True, 'result': result}), 201
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/flights/<string:flight_id>', methods=['DELETE'])
@admin_required
def delete_flight(current_user_id, flight_id):
    """항공편 삭제"""
    try:
        success, error = Flight.delete_flight(flight_id)
        if not success:
            return jsonify({'message': error}), 400
        return jsonify({'message': '항공편이 삭제되었습니다.', 'success': True}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/schedules', methods=['GET'])
@admin_required
def get_available_schedules(current_user_id):
    """할인 가능한 스케줄 목록 조회"""
    try:
        schedules, error = Promotion.get_available_schedules()
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'schedules': schedules}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

# 할인 관리
@admin_bp.route('/discounts', methods=['GET'])
@admin_required
def get_discounts(current_user_id):
    """할인 목록 조회"""
    try:
        discounts, error = Promotion.get_discounts()
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'discounts': discounts}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/discounts', methods=['POST'])
@admin_required
def create_discount(current_user_id):
    """할인 생성 (스케줄 기반)"""
    try:
        data = request.get_json()
        required_fields = ['schedule_id', 'discount_percentage']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'{field}는 필수 입력 항목입니다.'}), 400
        
        discount_id, error = Promotion.create_discount(
            data['schedule_id'], data['discount_percentage']
        )
        
        if error:
            return jsonify({'message': error}), 400
        
        return jsonify({'message': '할인이 생성되었습니다.', 'discount_id': discount_id, 'success': True}), 201
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/discounts/<int:discount_id>', methods=['DELETE'])
@admin_required
def delete_discount(current_user_id, discount_id):
    """할인 삭제"""
    try:
        success, error = Promotion.delete_discount(discount_id)
        if not success:
            return jsonify({'message': error}), 400
        return jsonify({'message': '할인이 삭제되었습니다.', 'success': True}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

# 예약 관리
@admin_bp.route('/bookings', methods=['GET'])
@admin_required
def get_all_bookings(current_user_id):
    """모든 예약 조회"""
    try:
        bookings, error = Booking.get_all_bookings_admin()
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'bookings': bookings}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/bookings/<string:booking_number>/cancel', methods=['PUT'])
@admin_required
def cancel_booking(current_user_id, booking_number):
    """예약 취소 (관리자)"""
    try:
        success, error = Booking.cancel_booking_admin(booking_number)
        if not success:
            return jsonify({'message': error}), 400
        return jsonify({'message': '예약이 취소되었습니다.', 'success': True}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/bookings/search', methods=['GET'])
@admin_required
def search_bookings(current_user_id):
    """예약 검색"""
    try:
        search_term = request.args.get('term', '')
        if not search_term:
            return jsonify({'message': '검색어를 입력해주세요.'}), 400
            
        bookings, error = Booking.search_bookings_admin(search_term)
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'bookings': bookings}), 200
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@admin_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'service': 'admin-service',
        'port': 5004
    }), 200

# version 10.0.0