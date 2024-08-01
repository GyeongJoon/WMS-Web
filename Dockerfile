# Dockerfile
# 베이스 이미지로 Python 3.8 사용
FROM python:3.8-slim-buster

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 파일을 작업 디렉토리로 복사
COPY requirements.txt requirements.txt

# 종속성 설치
RUN pip install -r requirements.txt

# 애플리케이션 파일을 작업 디렉토리로 복사
COPY app.py app.py

# 애플리케이션 실행
CMD ["python", "app.py"]
