import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database import get_db_connection, safe_json_serialize
from mysql.connector import Error


class Payment:
    @staticmethod
    def create_payment(user_id, booking_id, method, provider, amount, order_id, raw_payload=None):
        try:
            connection = get_db_connection()
            if not connection:
                return None, '데이터베이스 연결 오류'

            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO payments (booking_id, user_id, method, provider, amount, order_id, status, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s, 'REQUESTED', %s)
                """,
                (booking_id, user_id, method, provider, amount, order_id, raw_payload)
            )
            connection.commit()

            return cursor.lastrowid, None
        except Error as e:
            return None, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def mark_paid(order_id, receipt_id, raw_payload=None):
        try:
            connection = get_db_connection()
            if not connection:
                return False, '데이터베이스 연결 오류'

            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE payments
                SET status = 'PAID', bootpay_receipt_id = %s, raw_payload = %s
                WHERE order_id = %s
                """,
                (receipt_id, raw_payload, order_id)
            )
            connection.commit()
            return cursor.rowcount > 0, None
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def attach_booking(order_id, booking_id):
        try:
            connection = get_db_connection()
            if not connection:
                return False, '데이터베이스 연결 오류'

            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE payments
                SET booking_id = %s
                WHERE order_id = %s
                """,
                (booking_id, order_id)
            )
            connection.commit()
            return cursor.rowcount > 0, None
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()

    @staticmethod
    def mark_failed(order_id, raw_payload=None):
        try:
            connection = get_db_connection()
            if not connection:
                return False, '데이터베이스 연결 오류'

            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE payments
                SET status = 'FAILED', raw_payload = %s
                WHERE order_id = %s
                """,
                (raw_payload, order_id)
            )
            connection.commit()
            return cursor.rowcount > 0, None
        except Error as e:
            return False, f"데이터베이스 오류: {str(e)}"
        finally:
            if connection:
                connection.close()


