# Flight Service Routes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify
from models import Flight, Airport

flight_bp = Blueprint('flights', __name__)

@flight_bp.route('/search', methods=['GET'])
def search_flights():
    """항공편 검색"""
    try:
        departure = request.args.get('departure')
        arrival = request.args.get('arrival')
        date = request.args.get('date')
        
        print(f"Flight search request: departure={departure}, arrival={arrival}, date={date}")
        
        if not all([departure, arrival, date]):
            return jsonify({'message': '출발지, 도착지, 날짜를 모두 입력해주세요.'}), 400
        
        flights, error = Flight.search_flights(departure, arrival, date)
        
        if error:
            return jsonify({'message': error}), 500
        
        print(f"Found {len(flights)} flights")
        
        return jsonify({
            'flights': flights,
            'total': len(flights)
        }), 200
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'message': f'예상치 못한 오류: {str(e)}'}), 500

@flight_bp.route('/airports', methods=['GET'])
def get_airports():
    """공항 목록 조회"""
    try:
        airports, error = Airport.get_all_airports()
        
        if error:
            return jsonify({'message': error}), 500
        
        return jsonify({'airports': airports}), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@flight_bp.route('/featured', methods=['GET'])
def get_featured_flights():
    """오늘의 특가 항공편 조회"""
    try:
        flights, error = Flight.get_featured_flights()
        
        if error:
            return jsonify({'message': error}), 500
        
        return jsonify({
            'flights': flights,
            'total': len(flights)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@flight_bp.route('/promotions', methods=['GET'])
def get_promotions():
    """프로모션 항공편 조회 (API용)"""
    try:
        promotions, error = Flight.get_promotions()
        
        if error:
            return jsonify({'message': error}), 500
        
        return jsonify({
            'promotions': promotions,
            'total': len(promotions)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

@flight_bp.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'service': 'flight-service',
        'port': 5002
    }), 200

# version 10.0.0