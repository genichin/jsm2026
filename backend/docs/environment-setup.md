# 환경별 설정 가이드

## 개요

jsm_be는 개발 환경과 프로덕션 환경에서 서로 다른 설정을 사용할 수 있도록 환경별 `.env` 파일을 지원합니다.

## 환경 구분

| 환경 | ENV 변수 | .env 파일 | 데이터베이스 |
|------|----------|-----------|--------------|
| **개발** | `development` | `.env.development` | `jsmdb_dev` |
| **프로덕션** | `production` | `.env.production` | `jsmdb` |
| **기본** | 미설정 | `.env` | 설정에 따름 |

## 사용 방법

### 1. 개발 환경에서 실행

```bash
# 방법 1: ENV 환경 변수 설정
export ENV=development
python -m uvicorn app.main:app --reload

# 방법 2: 한 줄로 실행
ENV=development uvicorn app.main:app --reload

# 방법 3: .env 파일 심볼릭 링크 (권장)
ln -sf .env.development .env
uvicorn app.main:app --reload
```

### 2. 프로덕션 환경에서 실행

```bash
# 방법 1: ENV 환경 변수 설정
export ENV=production
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 방법 2: 한 줄로 실행
ENV=production uvicorn app.main:app --host 0.0.0.0 --port 8000

# 방법 3: .env 파일 심볼릭 링크 (권장)
ln -sf .env.production .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Docker Compose에서 사용

#### docker-compose.yml 수정

```yaml
services:
  api:
    build: .
    environment:
      - ENV=development  # 또는 production
    # ...
```

또는 env_file 사용:

```yaml
services:
  api:
    build: .
    env_file:
      - .env.development  # 개발용
    # ...
```

프로덕션:
```yaml
services:
  api:
    build: .
    env_file:
      - .env.production  # 프로덕션용
    # ...
```

### 4. 데이터베이스 초기 설정

#### 개발 데이터베이스 생성

```bash
# PostgreSQL 접속
docker-compose exec db psql -U postgres

# 개발용 데이터베이스 생성
CREATE DATABASE jsmdb_dev;

# 종료
\q
```

#### 마이그레이션 실행

```bash
# 개발 환경
ENV=development alembic upgrade head

# 프로덕션 환경
ENV=production alembic upgrade head
```

#### 초기 관리자 계정 생성

마이그레이션 후 초기 관리자 계정을 생성합니다:

```bash
# 개발 환경
ENV=development python scripts/init_db.py

# 프로덕션 환경  
ENV=production python scripts/init_db.py
```

**자동 생성되는 관리자 계정**:
- 이메일: `admin@jsmoney.com`
- 비밀번호: `admin123`
- 권한: Superuser

⚠️ **보안 주의사항**:
- 첫 로그인 후 반드시 비밀번호를 변경하세요
- 프로덕션 환경에서는 더 강력한 비밀번호를 사용하세요

**관리자 계정 확인**:
```bash
ENV=development python scripts/check_admin.py
```

## 설정 파일 상세

### .env.development (개발 환경)

```bash
# 주요 차이점
DEBUG=True                    # 디버그 모드 활성화
DATABASE_URL="...jsmdb_dev"   # 개발 DB 사용
CORS_ORIGINS=*                # 모든 origin 허용
SECRET_KEY=dev-key            # 개발용 키
```

### .env.production (프로덕션 환경)

```bash
# 주요 차이점
DEBUG=False                   # 디버그 모드 비활성화
DATABASE_URL="...jsmdb"       # 프로덕션 DB 사용
CORS_ORIGINS=https://...      # 특정 도메인만 허용
SECRET_KEY=random-secure-key  # 안전한 랜덤 키
```

## 환경 확인 방법

### Python에서 확인

```python
from app.core.config import settings

print(f"Environment: {settings.environment}")
print(f"Database: {settings.DATABASE_URL}")
print(f"Debug Mode: {settings.DEBUG}")
```

### API 엔드포인트로 확인

```bash
# Health check 엔드포인트 (추가 필요)
curl http://localhost:8000/health

# 응답 예시
{
  "status": "ok",
  "environment": "development",
  "database": "jsmdb_dev"
}
```

## 베스트 프랙티스

### 1. .env 파일 관리

```bash
# .env 파일은 Git에 커밋하지 않음
.env
.env.local

# 템플릿 파일은 커밋
.env.example
.env.development  # 개발 기본값
.env.production   # 프로덕션 기본값
```

### 2. 로컬 개발자별 설정

개발자마다 다른 설정이 필요한 경우:

```bash
# .env.development를 복사
cp .env.development .env.local

# .env.local을 수정 (개인 설정)
nano .env.local

# .env.local 사용
ln -sf .env.local .env
```

### 3. CI/CD 파이프라인

```yaml
# GitHub Actions 예시
jobs:
  test:
    steps:
      - name: Run tests
        env:
          ENV: development
        run: pytest

  deploy:
    steps:
      - name: Deploy to production
        env:
          ENV: production
        run: docker-compose up -d
```

## 문제 해결

### 잘못된 데이터베이스에 연결되는 경우

```bash
# 현재 사용 중인 .env 파일 확인
ls -la .env

# ENV 변수 확인
echo $ENV

# 강제로 환경 변수 설정
export ENV=development
```

### 마이그레이션이 잘못된 DB에 적용되는 경우

```bash
# 마이그레이션 전 DB 확인
ENV=development python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# 올바른 환경으로 마이그레이션
ENV=development alembic upgrade head
```

## 추가 환경

필요시 추가 환경을 만들 수 있습니다:

```bash
# 스테이징 환경
.env.staging

# 테스트 환경
.env.test

# config.py에 추가
elif environment == "staging":
    env_file = ".env.staging"
elif environment == "test":
    env_file = ".env.test"
```

## 보안 주의사항

1. ⚠️ `.env.production`에는 **절대** 실제 프로덕션 비밀번호를 커밋하지 마세요
2. 프로덕션 배포 시 서버에서 직접 안전한 값으로 수정하세요
3. 환경 변수로 덮어쓰기 가능합니다:
   ```bash
   export SECRET_KEY="actual-production-secret"
   export DATABASE_URL="postgresql://..."
   ```
