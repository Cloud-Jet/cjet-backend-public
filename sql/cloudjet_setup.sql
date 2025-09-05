-- CloudJet 항공사 서비스 통합 데이터베이스
-- 생성일: 2025-08-07

DROP DATABASE IF EXISTS cloudjet_simple;
CREATE DATABASE cloudjet_simple CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cloudjet_simple;

-- 1. 회원 테이블
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL COMMENT '이름',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '이메일',
    password_hash VARCHAR(255) NOT NULL COMMENT '암호화된 비밀번호',
    phone VARCHAR(20) COMMENT '휴대폰',
    birth_date DATE COMMENT '생년월일',
    role ENUM('USER', 'ADMIN') DEFAULT 'USER' COMMENT '권한',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 공항 테이블
CREATE TABLE airports (
    airport_code VARCHAR(3) PRIMARY KEY COMMENT 'IATA 공항 코드',
    airport_name VARCHAR(100) NOT NULL COMMENT '공항명',
    city VARCHAR(50) NOT NULL COMMENT '도시명',
    country VARCHAR(50) NOT NULL COMMENT '국가명'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 항공편 테이블
CREATE TABLE flights (
    flight_id VARCHAR(10) PRIMARY KEY COMMENT '항공편 번호',
    airline VARCHAR(50) DEFAULT 'CloudJet' COMMENT '항공사',
    departure_airport VARCHAR(3) NOT NULL COMMENT '출발 공항',
    arrival_airport VARCHAR(3) NOT NULL COMMENT '도착 공항',
    departure_time TIME NOT NULL COMMENT '출발 시간',
    arrival_time TIME NOT NULL COMMENT '도착 시간',
    duration VARCHAR(20) NOT NULL COMMENT '비행 시간',
    aircraft VARCHAR(50) NOT NULL COMMENT '항공기 기종',
    base_price INT NOT NULL COMMENT '기본 요금',
    total_seats INT DEFAULT 180 COMMENT '총 좌석 수',
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (departure_airport) REFERENCES airports(airport_code),
    FOREIGN KEY (arrival_airport) REFERENCES airports(airport_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 항공편 스케줄 테이블
CREATE TABLE flight_schedules (
    schedule_id INT PRIMARY KEY AUTO_INCREMENT,
    flight_id VARCHAR(10) NOT NULL,
    flight_date DATE NOT NULL,
    current_price INT NOT NULL COMMENT '당일 요금',
    available_seats INT NOT NULL COMMENT '남은 좌석',
    status ENUM('ACTIVE', 'CANCELLED', 'DELAYED') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
    UNIQUE KEY unique_flight_date (flight_id, flight_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 예약 테이블
CREATE TABLE bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_number VARCHAR(20) NOT NULL UNIQUE COMMENT '예약 번호',
    user_id INT NOT NULL,
    schedule_id INT NOT NULL,
    seat_number VARCHAR(5) COMMENT '좌석 번호',
    total_amount INT NOT NULL COMMENT '총 결제 금액',
    contact_email VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    status ENUM('CONFIRMED', 'CANCELLED', 'COMPLETED') DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (schedule_id) REFERENCES flight_schedules(schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 승객 테이블
CREATE TABLE passengers (
    passenger_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    name_kor VARCHAR(50) NOT NULL COMMENT '한글 이름',
    name_eng VARCHAR(100) NOT NULL COMMENT '영문 이름',
    birth_date DATE NOT NULL,
    gender ENUM('M', 'F') NOT NULL,
    seat_number VARCHAR(5) COMMENT '좌석 번호',
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 결제 테이블
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NULL,
    user_id INT NOT NULL,
    method ENUM('CARD', 'KAKAO') NOT NULL,
    provider ENUM('NICEPAY', 'KAKAO') NOT NULL,
    amount INT NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    status ENUM('REQUESTED', 'PAID', 'FAILED', 'CANCELLED') DEFAULT 'REQUESTED',
    bootpay_receipt_id VARCHAR(64) UNIQUE,
    order_id VARCHAR(64) UNIQUE,
    raw_payload JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_payment_order_id (order_id),
    INDEX idx_payment_receipt_id (bootpay_receipt_id),
    INDEX idx_payment_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 할인 테이블
CREATE TABLE flight_discounts (
    discount_id INT PRIMARY KEY AUTO_INCREMENT,
    schedule_id INT NOT NULL COMMENT '항공편 스케줄 ID',
    discount_percentage INT NOT NULL COMMENT '할인율 (%)',
    status ENUM('ACTIVE', 'INACTIVE', 'EXPIRED') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES flight_schedules(schedule_id),
    INDEX idx_schedule_id (schedule_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======== 기본 데이터 삽입 ========

-- 관리자 계정 (ID: admin@cloudjet.com, PW: admin123)
INSERT INTO users (name, email, password_hash, phone, birth_date, role) VALUES
('관리자', 'admin@cloudjet.com', 'admin123', '010-0000-0000', '1980-01-01', 'ADMIN');

-- 공항 데이터
INSERT INTO airports (airport_code, airport_name, city, country) VALUES
('ICN', '인천국제공항', '서울', '대한민국'),
('GMP', '김포국제공항', '서울', '대한민국'),
('NRT', '나리타국제공항', '도쿄', '일본'),
('KIX', '간사이국제공항', '오사카', '일본'),
('BKK', '수완나품국제공항', '방콕', '태국'),
('SYD', '킹스포드스미스공항', '시드니', '호주'),
('LAX', '로스앤젤레스국제공항', '로스앤젤레스', '미국'),
('CDG', '샤를드골국제공항', '파리', '프랑스');

-- 항공편 데이터
INSERT INTO flights (flight_id, departure_airport, arrival_airport, departure_time, arrival_time, duration, aircraft, base_price) VALUES
('CJ101', 'ICN', 'NRT', '06:30:00', '09:15:00', '2시간 45분', 'Boeing 737-800', 320000),
('CJ102', 'ICN', 'NRT', '09:30:00', '12:15:00', '2시간 45분', 'Airbus A320', 320000),
('CJ111', 'ICN', 'KIX', '07:00:00', '09:30:00', '2시간 30분', 'Boeing 737-800', 350000),
('CJ121', 'ICN', 'BKK', '08:00:00', '12:30:00', '6시간 30분', 'Boeing 787-9', 450000),
('CJ131', 'ICN', 'SYD', '10:00:00', '22:30:00', '9시간 30분', 'Boeing 787-9', 720000),
('CJ141', 'ICN', 'LAX', '11:00:00', '06:30:00', '11시간 30분', 'Boeing 787-9', 850000),
('CJ151', 'ICN', 'CDG', '13:00:00', '18:30:00', '12시간 30분', 'Boeing 787-9', 950000);

-- 향후 30일 스케줄 생성
DELIMITER //
CREATE PROCEDURE CreateSchedules()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE flight_code VARCHAR(10);
    DECLARE base_cost INT;
    DECLARE schedule_date DATE;
    DECLARE days_count INT DEFAULT 0;
    
    DECLARE flight_cursor CURSOR FOR 
        SELECT flight_id, base_price FROM flights WHERE is_active = TRUE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    WHILE days_count < 30 DO
        SET schedule_date = DATE_ADD(CURDATE(), INTERVAL days_count DAY);
        SET done = FALSE;
        
        OPEN flight_cursor;
        flight_loop: LOOP
            FETCH flight_cursor INTO flight_code, base_cost;
            IF done THEN
                LEAVE flight_loop;
            END IF;
            
            SET @price_variation = base_cost * (0.8 + (RAND() * 0.4));
            SET @available_seats = 150 + FLOOR(RAND() * 30);
            
            INSERT IGNORE INTO flight_schedules (flight_id, flight_date, current_price, available_seats)
            VALUES (flight_code, schedule_date, FLOOR(@price_variation), @available_seats);
        END LOOP;
        CLOSE flight_cursor;
        
        SET days_count = days_count + 1;
    END WHILE;
END //
DELIMITER ;

CALL CreateSchedules();
DROP PROCEDURE CreateSchedules;

-- 인덱스 생성
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_number ON bookings(booking_number);
CREATE INDEX idx_passengers_booking ON passengers(booking_id);
CREATE INDEX idx_schedules_date ON flight_schedules(flight_date);
CREATE INDEX idx_schedules_route ON flight_schedules(flight_id, flight_date);

SELECT 'CloudJet 데이터베이스 설치 완료!' AS message;
SELECT 'admin / admin123 으로 관리자 로그인 가능' AS login_info;
