# Auth Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 프로젝트 파일들 복사 (루트에서 빌드할 때)
COPY auth-service/ /app/
COPY shared/ /app/shared/

# Python 의존성 설치 + Redis 라이브러리
RUN pip install --no-cache-dir -r requirements.txt

# 환경변수 설정
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV AUTH_SERVICE_PORT=5001

# 포트 노출
EXPOSE 5001

CMD ["python", "app.py"]