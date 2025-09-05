# CloudJet 데이터베이스 설정 가이드

## 🗃️ MySQL Workbench에서 실행하기

**순서대로 실행하세요:**

### 1️⃣ 데이터베이스 생성
```sql
-- sql/01-database-setup.sql 실행
```
- cloudjet_airline 데이터베이스 생성
- cloudjet_user 사용자 생성
- 권한 설정

### 2️⃣ 기본 테이블 생성
```sql
-- sql/02-basic-tables.sql 실행
```
- users (회원)
- airlines (항공사)
- airports (공항)
- aircraft_types (항공기)

### 3️⃣ 항공편/예약 테이블 생성
```sql
-- sql/03-flight-booking-tables.sql 실행
```
- flights (항공편)
- bookings (예약)
- passengers (승객)
- payments (결제)

### 4️⃣ 시스템 관리 테이블 생성
```sql
-- sql/04-system-tables.sql 실행
```
- user_sessions (세션)
- system_logs (로그)

### 5️⃣ 기본 데이터 삽입
```sql
-- sql/05-basic-data.sql 실행
```
- 항공사 15개
- 공항 20개
- 항공기 기종 8개

### 6️⃣ 샘플 데이터 삽입
```sql
-- sql/06-sample-data.sql 실행
```
- 샘플 회원 5명
- 샘플 항공편 15개
- 샘플 예약 5건

### 7️⃣ 뷰 및 인덱스 생성
```sql
-- sql/07-views-indexes.sql 실행
```
- flight_details 뷰
- booking_details 뷰
- user_statistics 뷰
- 성능 최적화 인덱스

## ✅ 완료 확인

```sql
-- 테이블 확인
SHOW TABLES;

-- 데이터 확인
SELECT * FROM flight_details LIMIT 5;
SELECT * FROM booking_details LIMIT 5;
SELECT * FROM user_statistics;
```

## 🔗 접속 정보

- **데이터베이스**: cloudjet_airline
- **사용자**: cloudjet_user
- **비밀번호**: cloudjet_pass
- **호스트**: localhost
- **포트**: 3306

---

**모든 스크립트를 순서대로 실행하면 완전한 항공사 데이터베이스가 구성됩니다!** ✈️