# J's Money Backend (jsm_be)

자산관리 소프트웨어 "J's Money"의 백엔드 API 서버

## 📖 목차

- [기능](#기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작) ⭐
- [프로젝트 구조](#프로젝트-구조)
- [시작하기](#시작하기)
- [API 문서](#api-문서)
- [배포](#배포)

## 빠른 시작

처음 시작하시나요? **[Quick Start 가이드](QUICKSTART.md)**를 따라 5분 안에 서버를 실행하세요! 🚀

## 기능

1. **가계부 관리**: 계좌별 거래 내역 기록 및 자산 평가
2. **투자 자산 관리**: 주식, 가상화폐, 채권 등의 거래 내역 및 수익률 추적
3. **실물 자산 관리**: 부동산, 차량 등의 자산 관리

## 기술 스택

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0
- **Authentication**: JWT
- **Migration**: Alembic
- **Testing**: pytest
- **Containerization**: Docker & Docker Compose

## 프로젝트 구조

```
jsm_be/
├── app/
│   ├── api/              # API 엔드포인트
│   ├── core/             # 설정, 보안, 의존성
│   ├── models/           # SQLAlchemy 모델
│   ├── schemas/          # Pydantic 스키마
│   ├── services/         # 비즈니스 로직
│   └── main.py           # FastAPI 앱 엔트리포인트
├── alembic/              # 데이터베이스 마이그레이션
├── docs/
│   └── database-schema.md  # 📊 DB 스키마 설계 문서
├── tests/                # 테스트 코드
├── requirements.txt      # Python 의존성
├── Dockerfile
├── docker-compose.yml
└── .env.example          # 환경 변수 예시
```

## 시작하기

### 환경 설정

jsm_be는 개발/프로덕션 환경을 분리하여 관리합니다:

- **개발 환경**: `.env.development` → 데이터베이스 `jsmdb_dev` 사용
- **프로덕션 환경**: `.env.production` → 데이터베이스 `jsmdb` 사용

자세한 내용은 [환경별 설정 가이드](docs/environment-setup.md)를 참고하세요.

### 로컬 개발

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 환경 설정 (자동으로 .env.development 사용)
ln -sf .env.development .env

# 또는 ENV 환경 변수로 지정
export ENV=development

# 개발용 데이터베이스 생성 (PostgreSQL 실행 중이어야 함)
createdb jsmdb_dev
# 또는 Docker 사용 시
# docker-compose exec db psql -U postgres -c "CREATE DATABASE jsmdb_dev;"

# 데이터베이스 마이그레이션
alembic upgrade head

# 초기 관리자 계정 생성 및 데이터베이스 초기화
ENV=development python scripts/init_db.py

# 개발 서버 실행 (HTTP - 자동 리로드)
uvicorn app.main:app --reload

# HTTPS 서버 실행 (필요시)
# 1. SSL 인증서 생성 (자체 서명 - 개발용)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 2. HTTPS로 서버 실행
ENV=development uvicorn app.main:app --ssl-keyfile=./key.pem --ssl-certfile=./cert.pem --host 0.0.0.0 --port 8000 --reload
```

### Docker로 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

## API 문서

### 온라인 문서 (프로덕션)
- **API 가이드**: [docs/api-guide.md](docs/api-guide.md)
- **Swagger UI**: https://jsfamily2.myds.me:40041/docs
- **ReDoc**: https://jsfamily2.myds.me:40041/redoc
- **OpenAPI Spec**: https://jsfamily2.myds.me:40041/api/v1/openapi.json

### 로컬 개발 환경
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 기본 관리자 계정
- Email: `admin@jsmoney.com`
- Password: `admin123`
- ⚠️ 프로덕션 환경에서는 반드시 비밀번호를 변경하세요!

## 데이터베이스

### 초기화

```bash
# 데이터베이스 생성 및 마이그레이션
python scripts/init_db.py

# 기본 데이터 삽입 (계좌 유형, 거래 카테고리 등)
python scripts/seed_data.py
```

### 마이그레이션

```bash
# 새 마이그레이션 생성
ENV=development alembic revision --autogenerate -m "설명"

# 마이그레이션 실행
ENV=development alembic upgrade head

# 마이그레이션 되돌리기
ENV=development alembic downgrade -1
```

## 개발 가이드

AI Agent를 위한 개발 지침은 `.github/copilot-instructions.md` 참고

**주요 문서**:
- `.github/copilot-instructions.md` - AI Agent 개발 규칙 및 패턴
- `docs/database-schema.md` - 데이터베이스 스키마 설계 (테이블, 관계, 비즈니스 규칙)
- `docs/api-guide.md` - API 사용 가이드 (외부 개발자 및 AI Agent용)
- `docs/security-https.md` - HTTPS 보안 설정 가이드

## 배포 (Deployment)

### 현재 프로덕션 환경

- **URL**: https://jsfamily2.myds.me:40041
- **서버**: NAS (Synology) 또는 클라우드 서버
- **포트**: 40041 (HTTPS)
- **컨테이너**: Docker Compose

### Docker Compose로 배포

#### 1. 서버 준비

```bash
# 프로젝트 클론
git clone https://github.com/genichin/jsm_be.git
cd jsm_be

# 환경 변수 설정
cp .env.example .env
nano .env  # 프로덕션 설정으로 수정
```

#### 2. 환경 변수 설정 (.env)

프로덕션 환경에서 **반드시 변경**해야 할 항목:

```bash
# 앱 설정
APP_NAME="J's Money API"
APP_VERSION="1.0.0"
DEBUG=False  # ⚠️ 반드시 False로 설정

# 보안 (매우 중요!)
SECRET_KEY=your-super-secret-key-change-this-in-production  # ⚠️ 변경 필수
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 데이터베이스
DATABASE_URL=postgresql://postgres:your-password@db:5432/jsmdb  # ⚠️ 비밀번호 변경
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password  # ⚠️ 변경 필수
POSTGRES_DB=jsmdb

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 프로덕션에서는 비밀번호 설정 권장

# CORS (프론트엔드 도메인)
CORS_ORIGINS=["https://your-frontend-domain.com"]  # ⚠️ 실제 도메인으로 변경

# 외부 접속 허용
ALLOWED_HOSTS=["jsfamily2.myds.me", "localhost"]  # ⚠️ 실제 도메인으로 변경
```

#### 3. SSL 인증서 준비

**옵션 A: 자체 서명 인증서 (개발/테스트)**
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=YourOrg/CN=jsfamily2.myds.me"
```

**옵션 B: Let's Encrypt (프로덕션 권장)**
```bash
# Certbot 설치 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install certbot

# 인증서 발급
sudo certbot certonly --standalone -d your-domain.com

# 인증서 복사
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./key.pem
sudo chmod 644 cert.pem key.pem
```

**옵션 C: Cloudflare Tunnel (Zero Trust 방식)**
- 별도의 SSL 인증서 불필요
- Cloudflare가 자동으로 HTTPS 제공
- 자세한 내용: [Cloudflare Tunnel 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

#### 4. Docker Compose 실행

```bash
# 컨테이너 빌드 및 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 데이터베이스 마이그레이션 (최초 1회)
docker-compose exec api alembic upgrade head

# 관리자 계정 생성 (선택)
docker-compose exec api python scripts/init_db.py

# 상태 확인
docker-compose ps
```

#### 5. HTTPS 설정 (프로덕션)

`docker-compose.yml` 수정:
```yaml
services:
  api:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=/app/key.pem --ssl-certfile=/app/cert.pem
    ports:
      - "40041:8000"  # 호스트:컨테이너
```

재시작:
```bash
docker-compose down
docker-compose up -d
```

### 수동 배포 (Docker 없이)

```bash
# 1. Python 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 데이터베이스 마이그레이션
ENV=production alembic upgrade head

# 4. 프로덕션 서버 실행
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 40041 \
  --ssl-keyfile=./key.pem \
  --ssl-certfile=./cert.pem \
  --workers 4
```

### 업데이트 배포

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 컨테이너 재빌드 및 재시작
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. 마이그레이션 실행 (DB 스키마 변경이 있는 경우)
docker-compose exec api alembic upgrade head

# 4. 로그 확인
docker-compose logs -f api
```

### 백업

#### 데이터베이스 백업
```bash
# 백업 생성
docker-compose exec db pg_dump -U postgres jsmdb > backup_$(date +%Y%m%d_%H%M%S).sql

# 백업 복원
docker-compose exec -T db psql -U postgres jsmdb < backup_20250113_120000.sql
```

#### 전체 볼륨 백업
```bash
# PostgreSQL 데이터 볼륨 백업
docker run --rm -v jsm_be_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz /data
```

### 모니터링

```bash
# 실시간 로그
docker-compose logs -f

# 컨테이너 상태
docker-compose ps

# 리소스 사용량
docker stats

# API 헬스체크
curl https://jsfamily2.myds.me:40041/health
```

### 트러블슈팅

#### 컨테이너가 시작되지 않을 때
```bash
docker-compose logs api
docker-compose logs db
```

#### 데이터베이스 연결 실패
```bash
# DB 컨테이너 상태 확인
docker-compose exec db pg_isready -U postgres

# DB 컨테이너 접속
docker-compose exec db psql -U postgres -d jsmdb
```

#### 포트 충돌
```bash
# 사용 중인 포트 확인
sudo lsof -i :40041

# docker-compose.yml에서 포트 변경
ports:
  - "40042:8000"  # 다른 포트로 변경
```

### 보안 체크리스트

- [ ] `SECRET_KEY` 변경 (랜덤 문자열)
- [ ] 데이터베이스 비밀번호 변경
- [ ] Redis 비밀번호 설정
- [ ] `DEBUG=False` 설정
- [ ] CORS_ORIGINS에 실제 프론트엔드 도메인만 허용
- [ ] HTTPS 인증서 설정 (Let's Encrypt 권장)
- [ ] 기본 관리자 계정 비밀번호 변경
- [ ] 방화벽 설정 (필요한 포트만 개방)
- [ ] 정기 백업 설정
- [ ] 로그 모니터링 설정
