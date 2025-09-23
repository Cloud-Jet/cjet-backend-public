import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify
from models import Payment
from shared.auth import token_required
import hmac
import hashlib
import base64
import uuid

payment_bp = Blueprint('payments', __name__)

@payment_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'payment-service',
        'port': 5005
    }), 200

@payment_bp.route('/init', methods=['POST'])
@token_required
def init_payment(current_user_id):
    try:
        from app import get_client_ip
        client_ip = get_client_ip(request)
        data = request.get_json() or {}
        required = ['amount']
        for f in required:
            if f not in data:
                print(f"[PAYMENT-SERVICE] 결제 초기화 실패 - 누락된 필드: {f} | 사용자 ID: {current_user_id} | IP: {client_ip}")
                return jsonify({'message': f'{f}는 필수입니다.'}), 400

        # 충돌 없는 고유 order_id 생성
        suffix = uuid.uuid4().hex[:8]
        order_id = data.get('orderId') or f"CJ-ORD-{current_user_id}-{data.get('scheduleId', 'NA')}-{suffix}"

        # 결제 파라미터 결정(기본: CARD/NICEPAY)
        method_val = 'CARD' if str(data.get('method', 'CARD')).upper() == 'CARD' else 'KAKAO'
        provider_val = 'NICEPAY' if str(data.get('provider', 'NICEPAY')).upper() == 'NICEPAY' else 'KAKAO'

        # 사전 결제 레코드 생성
        payment_id, error = Payment.create_payment(
            user_id=current_user_id,
            booking_id=None,  # 예약 확정 후 attach API로 연결 예정
            method=method_val,
            provider=provider_val,
            amount=data['amount'],
            order_id=order_id,
            raw_payload=None
        )

        if error:
            print(f"[PAYMENT-SERVICE] 결제 초기화 실패 - 사용자 ID: {current_user_id} | 주문 ID: {order_id} | 금액: {data['amount']}원 | 오류: {error} | IP: {client_ip}")
            return jsonify({'message': error}), 400

        print(f"[PAYMENT-SERVICE] 결제 초기화 성공 - 사용자 ID: {current_user_id} | 주문 ID: {order_id} | 결제 ID: {payment_id} | 금액: {data['amount']}원 | 방법: {method_val} | 제공업체: {provider_val} | IP: {client_ip}")

        # 프론트로 부트페이 빌링에 필요한 파라미터 반환 (간단화)
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'order_id': order_id,
            'bootpay': {
                'application_id': os.environ.get('BOOTPAY_REST_API_KEY'),  # JS Key
                'price': data['amount'],
                'order_name': data.get('orderName', 'CloudJet 항공권 결제'),
                'pg': 'nicepay' if provider_val == 'NICEPAY' else 'kakao',
                'method': 'card' if method_val == 'CARD' else 'kakao'
            }
        }), 200

    except Exception as e:
        print(f"[PAYMENT-SERVICE] 결제 초기화 서버 오류: {str(e)} | 사용자 ID: {current_user_id} | IP: {get_client_ip(request)}")
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500

def verify_webhook_signature(private_key: str, body_bytes: bytes, signature: str) -> bool:
    try:
        mac = hmac.new(private_key.encode('utf-8'), body_bytes, hashlib.sha256)
        expected = base64.b64encode(mac.digest()).decode('utf-8')
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

# Bootpay Webhook (application/x-www-form-urlencoded)
@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    try:
        from app import get_client_ip
        client_ip = get_client_ip(request)

        # 부트페이 Webhook은 보통 JSON이지만, 요청에 맞춰 form-urlencoded도 처리
        content_type = request.headers.get('Content-Type', '')

        # 원문 바디 (서명 검증용)
        raw_body = request.get_data() or b''
        signature = request.headers.get('Bootpay-Signature') or request.headers.get('X-Bootpay-Signature') or ''
        private_key = os.environ.get('BOOTPAY_PRIVATE_KEY', '')

        # 서명 검증 (선택적으로 강제)
        verified = verify_webhook_signature(private_key, raw_body, signature) if signature else True
        if not verified:
            print(f"[PAYMENT-SERVICE] 웹훅 서명 검증 실패 | IP: {client_ip}")
            return jsonify({'message': '서명 검증 실패'}), 401

        # payload 파싱
        payload = request.form.to_dict() if 'application/x-www-form-urlencoded' in content_type else (request.get_json() or {})

        status = str(payload.get('status') or payload.get('status_en') or '').upper()
        order_id = payload.get('order_id') or payload.get('orderId')
        receipt_id = payload.get('receipt_id') or payload.get('receiptId')
        amount = payload.get('price') or payload.get('amount')

        if not order_id:
            print(f"[PAYMENT-SERVICE] 웹훅 실패 - order_id 누락 | IP: {client_ip}")
            return jsonify({'message': 'order_id 누락'}), 400

        # 상태 반영
        if status in ('PAID', 'COMPLETE', 'SUCCESS') and receipt_id:
            ok, err = Payment.mark_paid(order_id, receipt_id, raw_payload=str(payload))
            if ok:
                print(f"[PAYMENT-SERVICE] 결제 성공 웹훅 - 주문 ID: {order_id} | 영수증 ID: {receipt_id} | 금액: {amount} | 상태: {status} | IP: {client_ip}")
            else:
                print(f"[PAYMENT-SERVICE] 결제 성공 웹훅 처리 실패 - 주문 ID: {order_id} | 오류: {err} | IP: {client_ip}")
        else:
            ok, err = Payment.mark_failed(order_id, raw_payload=str(payload))
            if ok:
                print(f"[PAYMENT-SERVICE] 결제 실패 웹훅 - 주문 ID: {order_id} | 상태: {status} | IP: {client_ip}")
            else:
                print(f"[PAYMENT-SERVICE] 결제 실패 웹훅 처리 실패 - 주문 ID: {order_id} | 오류: {err} | IP: {client_ip}")

        if not ok:
            return jsonify({'message': err or '업데이트 실패'}), 400

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"[PAYMENT-SERVICE] 웹훅 처리 서버 오류: {str(e)} | IP: {get_client_ip(request)}")
        return jsonify({'message': f'웹훅 처리 오류: {str(e)}'}), 500

@payment_bp.route('/attach-booking', methods=['POST'])
@token_required
def attach_booking(current_user_id):
    try:
        from app import get_client_ip
        client_ip = get_client_ip(request)
        data = request.get_json() or {}
        order_id = data.get('orderId')
        booking_id = data.get('bookingId')
        if not order_id or not booking_id:
            print(f"[PAYMENT-SERVICE] 결제-예약 연결 실패 - 누락된 필드 | 사용자 ID: {current_user_id} | IP: {client_ip}")
            return jsonify({'message': 'orderId, bookingId는 필수입니다.'}), 400

        success, error = Payment.attach_booking_to_payment(order_id, booking_id)
        if not success:
            print(f"[PAYMENT-SERVICE] 결제-예약 연결 실패 - 사용자 ID: {current_user_id} | 주문 ID: {order_id} | 예약 ID: {booking_id} | 오류: {error} | IP: {client_ip}")
            return jsonify({'message': error or '연결 실패'}), 400

        print(f"[PAYMENT-SERVICE] 결제-예약 연결 성공 - 사용자 ID: {current_user_id} | 주문 ID: {order_id} | 예약 ID: {booking_id} | IP: {client_ip}")

        return jsonify({'success': True, 'message': '예약과 결제가 연결되었습니다.'}), 200

    except Exception as e:
        print(f"[PAYMENT-SERVICE] 결제-예약 연결 서버 오류: {str(e)} | 사용자 ID: {current_user_id} | IP: {get_client_ip(request)}")
        return jsonify({'message': f'서버 오류: {str(e)}'}), 500
    

# version 10.0.0