# Testing Guide

## 개요

jsm_be 프로젝트의 API 통합 테스트 전략 및 실행 가이드입니다.

### 목표
- FastAPI 애플리케이션의 실제 동작을 HTTP 요청으로 검증
- 실제 PostgreSQL DB + Alembic 마이그레이션 적용
- 파일 업로드(암호화 Excel/CSV), 인증/권한, 비즈니스 로직 포함
- 테스트 간 상태 격리 및 재현성 보장
  - 각 테스트가 서로 영향을 주지 않고 독립적으로 실행
  - 동일한 테스트를 언제, 어디서, 몇 번을 실행해도 같은 결과가 출력

### 테스트 레벨
- **유닛 테스트**: 서비스/유틸리티 함수 (기존 test_file_parser.py 등)
- **통합 테스트**: FastAPI 앱 + DB + Redis + 파일 I/O (본 가이드 중점)
  - PostgreSQL: `jsmdb_test` (기존 서버 내 별도 DB)
  - Redis: `redis-stack:6379/2` (DB 2 사용, 개발은 DB 1, 배포는 DB 0 사용)
- **E2E 테스트**: 프론트엔드 포함 전체 플로우 (향후 추가)

---

## 테스트 스택

### 핵심 도구
- **테스트 러너**: pytest
- **HTTP 클라이언트**: httpx.AsyncClient (또는 fastapi.testclient.TestClient)
- **DB**: PostgreSQL (테스트 전용 DB)
- **마이그레이션**: Alembic
- **캐시**: 실제 Redis (테스트 환경은 DB 2 사용)
- **시간 고정**: freezegun (선택적)

### 의존성
현재 `requirements.txt`에 추가 필요:
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
freezegun>=1.2.0   # 선택적
```

---

## 환경 구성

### 기존 인프라 활용

현재 프로젝트는 다음 환경이 이미 구성되어 있습니다:
- **배포 DB**: `postgresql://postgres:jsmdb123!@jsmdb:5432/jsmdb`
- **배포 Redis**: `redis-stack:6379` (DB 0)
- **개발 DB**: `postgresql://postgres:jsmdb123!@jsmdb:5432/jsmdb_dev`
- **개발 Redis**: `redis-stack:6379` (DB 1)

테스트는 **별도 데이터베이스**를 사용하여 개발 환경과 격리합니다:
- **테스트 DB**: `jsmdb_test` (기존 PostgreSQL 서버 내)
- **테스트 Redis**: `redis-stack:6379/2` (DB 2)

### 1. 테스트 데이터베이스 설정

#### PostgreSQL 테스트 DB 생성
기존 `jsmdb` 서버에 테스트 전용 데이터베이스를 생성:

```bash
# PostgreSQL 컨테이너에 접속하여 테스트 DB 생성
docker exec -it jsmdb psql -U postgres -c "CREATE DATABASE jsmdb_test;"
```

또는 

```bash
psql -h jsmdb -U postgres -p 5432 -c "CREATE DATABASE jsmdb_test;"
```

#### 환경 변수 설정
`.env.test` 또는 pytest 설정에 추가:
```bash
DATABASE_URL_TEST=postgresql://postgres:jsmdb123!@jsmdb:5432/jsmdb_test
REDIS_URL_TEST=redis://redis-stack:6379/2
SECRET_KEY=test-secret-key-do-not-use-in-production
```

> **참고**: Redis DB 번호로 격리
> - DB 0: 배포 환경
> - DB 1: 개발 환경
> - DB 2: 테스트 환경
> - 테스트 종료 시 `FLUSHDB` 명령으로 DB 2만 초기화 가능

### 2. Alembic 마이그레이션
테스트 시작 시 자동으로 `alembic upgrade head` 실행
- 픽스처에서 DB 초기화 + 마이그레이션 적용
- 각 테스트는 트랜잭션 롤백으로 격리

---

## Pytest 픽스처 설계

### conftest.py 구조
```
tests/
├── conftest.py              # 공통 픽스처 (engine, session, app)
├── api/
│   ├── conftest.py          # API 테스트용 (client, auth_header)
│   ├── test_auth.py
│   ├── test_transactions.py
│   └── ...
└── testdata/
    ├── 토스뱅크_거래내역.xlsx
    ├── mirae.csv
    └── kb.csv
```

### 주요 픽스처 개요

#### 1. `test_db_engine`
- 테스트 전용 PostgreSQL 엔진 생성
- Alembic 마이그레이션 적용 (upgrade head)
- 테스트 종료 시 스키마 드롭 또는 DB 재생성

#### 2. `db_session`
- 각 테스트마다 트랜잭션 시작
- 테스트 종료 시 자동 롤백 (상태 격리)

#### 3. `app`
- FastAPI 인스턴스
- `app.dependency_overrides[get_db]` → 테스트 세션 반환
- `app.dependency_overrides[get_current_user]` → 인증 우회 (선택)

#### 4. `client`
- `httpx.AsyncClient(app=app, base_url="http://test")`
- 또는 `TestClient(app)`

#### 5. `auth_header`
- 테스트 유저 생성 후 `/api/v1/auth/login` 호출
- Bearer 토큰 반환: `{"Authorization": "Bearer <token>"}`

#### 6. `sample_files` (또는 개별 픽스처)
- `tests/testdata/` 경로의 샘플 파일 제공
- 토스뱅크 암호화 xlsx, CSV UTF-8/CP949 등

#### 7. Redis 모킹
```python
@pytest.fixture
def mock_redis_functions(monkeypatch):
    """Redis 캐시 함수를 no-op으로 모킹"""
    monkeypatch.setattr("app.core.redis.calculate_and_update_balance", lambda *args: None)
    monkeypatch.setattr("app.core.redis.invalidate_user_cache", lambda *args: None)
```

---

## 테스트 시나리오

### 1. 인증 (test_auth.py)
- ✅ POST /api/v1/auth/register → 201 성공
- ✅ 중복 등록 → 409 또는 400
- ✅ POST /api/v1/auth/login → 200, 토큰 수령
- ✅ 잘못된 비밀번호 → 401

### 2. 계좌/자산 CRUD (test_assets.py)
- ✅ POST /api/v1/assets → 201, asset 생성
- ✅ GET /api/v1/assets → 페이지네이션, 필터링 동작
- ✅ GET /api/v1/assets/{id} → 200, 소유권 체크
- ✅ 남의 자산 조회 → 404

### 3. 거래 CRUD (test_transactions_crud.py)
- ✅ POST /api/v1/transactions
  - cash/stock 자산별 비즈니스 규칙 검증
  - buy/sell 시 현금 연결거래 자동 생성 확인
  - 매수 시 out_asset (자산매수출금) 타입으로 현금 감소 기록
  - 매도 시 in_asset (자산매도입금) 타입으로 현금 증가 기록
  - DB에 두 거래 존재, 타입/수량/수수료/세금/realized_profit 계산 검증
- ✅ PUT /api/v1/transactions/{id} → 수정 성공
- ✅ DELETE /api/v1/transactions/{id} → 삭제 성공
- ✅ 캐시 무효화 함수 호출 여부 (모킹 어설션)

### 4. 파일 업로드 (test_transactions_upload.py) ⭐ 핵심
- ✅ POST /api/v1/transactions/upload (dry_run=true)
  - 토스뱅크 암호화 xlsx
    - 비밀번호 없으면 → 400
    - 올바른 비밀번호 → 200, preview 데이터 길이/필드 검증
  - CSV UTF-8/CP949 → 각각 200, 표준 컬럼 확인
  - 잘못된 형식/필수 컬럼 누락 → 400 메시지 검증
- ✅ dry_run=false 시 실제 DB insert 수량 확인
- ✅ 거래 유형 매핑 검증 (internal_transfer, card_payment 등)
- ✅ 권한: 토큰 없이 401

### 5. 조회/필터/페이지네이션 (test_transactions_query.py)
- ✅ GET /api/v1/transactions?asset_id=...&type=...&start_date=...&end_date=...
- ✅ 정렬, 페이지 수, 항목 수 검증

### 6. 포트폴리오/요약 (test_portfolio.py)
- ✅ GET /api/v1/transactions/portfolio
- ✅ 응답 구조, 계산 필드 존재 확인

### 7. 경계 조건 및 에러 처리 (test_edge_cases.py)
- ✅ 잘못된 데이터 형식 (날짜, 수량, 가격, 거래 유형, 자산 유형)
- ✅ 경계값 테스트 (0 수량/가격, 음수 수수료/세금, 매우 큰 값, 매우 작은 소수점)
- ✅ 필수 필드 누락
- ✅ 리소스 없음 (존재하지 않는 자산/거래/계좌)
- ✅ 파일 업로드 에러 (빈 파일, 잘못된 형식, 손상된 파일)
- ✅ 페이지네이션 경계 (0 페이지, 음수, 과도한 사이즈)
- ✅ 동시성/경합 조건 (삭제된 거래 수정 등)
- ✅ 특수 문자 처리 (유니코드, SQL 인젝션)

### 8. 계좌 관리 (test_accounts.py) ✅ 완료
- ✅ POST /api/v1/accounts → 계좌 생성
- ✅ GET /api/v1/accounts → 계좌 목록 조회 (페이지네이션, 필터링)
- ✅ GET /api/v1/accounts/{account_id} → 계좌 상세 조회
- ✅ PATCH /api/v1/accounts/{account_id} → 계좌 수정
- ✅ DELETE /api/v1/accounts/{account_id} → 계좌 삭제
- ✅ POST /api/v1/accounts/{account_id}/toggle-active → 활성화/비활성화
- ✅ GET /api/v1/accounts/{account_id}/shares → 계좌 공유 목록
- ✅ POST /api/v1/accounts/{account_id}/shares → 계좌 공유 생성
- ✅ PATCH /api/v1/accounts/{account_id}/shares/{share_id} → 공유 권한 수정
- ✅ DELETE /api/v1/accounts/{account_id}/shares/{share_id} → 공유 삭제
- **테스트 수**: 30개

### 9. 카테고리 관리 (test_categories.py) ✅ 완료
- ✅ GET /api/v1/categories → 카테고리 목록 (페이지네이션, 정렬)
- ✅ GET /api/v1/categories/tree → 트리 구조 조회
- ✅ POST /api/v1/categories → 카테고리 생성
- ✅ GET /api/v1/categories/{category_id} → 상세 조회
- ✅ PUT /api/v1/categories/{category_id} → 수정
- ✅ DELETE /api/v1/categories/{category_id} → 삭제
- ✅ POST /api/v1/categories/seed → 기본 카테고리 시드
- ✅ 계층 구조 검증 (parent_id)
- **테스트 수**: 37개

### 10. 태그 관리 (test_tags.py) ✅ 완료
- ✅ POST /api/v1/tags → 태그 생성
- ✅ GET /api/v1/tags → 태그 목록 (페이지네이션, 검색)
- ✅ GET /api/v1/tags/{tag_id} → 상세 조회
- ✅ PATCH /api/v1/tags/{tag_id} → 태그 수정
- ✅ DELETE /api/v1/tags/{tag_id} → 태그 삭제
- ✅ POST /api/v1/tags/attach → 엔티티에 태그 연결
- ✅ POST /api/v1/tags/attach-batch → 태그 일괄 연결
- ✅ DELETE /api/v1/tags/detach/{taggable_id} → 태그 연결 해제
- ✅ GET /api/v1/tags/entity/{taggable_type}/{taggable_id} → 엔티티의 태그 조회
- ✅ 중복 태그 방지 검증
- **테스트 수**: 42개

### 11. 리마인더 관리 (test_reminders.py) ✅ 완료
- ✅ POST /api/v1/reminders → 리마인더 생성
- ✅ GET /api/v1/reminders → 리마인더 목록 (필터링, 정렬)
- ✅ GET /api/v1/reminders/pending → 대기 중인 리마인더
- ✅ GET /api/v1/reminders/stats → 리마인더 통계
- ✅ GET /api/v1/reminders/{reminder_id} → 상세 조회
- ✅ PATCH /api/v1/reminders/{reminder_id} → 수정
- ✅ DELETE /api/v1/reminders/{reminder_id} → 삭제
- ✅ PATCH /api/v1/reminders/{reminder_id}/dismiss → 완료 처리
- ✅ PATCH /api/v1/reminders/{reminder_id}/snooze → 스누즈
- ✅ GET /api/v1/reminders/entity/{remindable_type}/{remindable_id} → 엔티티 리마인더
- **테스트 수**: 41개

### 12. 활동 로그 관리 (test_activities.py) ✅ 완료
- ✅ POST /api/v1/activities → 댓글/로그 생성
- ✅ GET /api/v1/activities → 활동 목록 (필터링, 정렬)
- ✅ GET /api/v1/activities/{activity_id} → 상세 조회
- ✅ GET /api/v1/activities/thread/{thread_root_id} → 스레드 조회
- ✅ PATCH /api/v1/activities/{activity_id} → 수정 (댓글만)
- ✅ DELETE /api/v1/activities/{activity_id} → 삭제
- **테스트 수**: 26개

### 13. 자동 규칙 관리 (test_auto_rules.py) ✅ 완료
- ✅ POST /api/v1/category-auto-rules → 규칙 생성
- ✅ GET /api/v1/category-auto-rules → 규칙 목록
- ✅ PUT /api/v1/category-auto-rules/{rule_id} → 규칙 수정
- ✅ DELETE /api/v1/category-auto-rules/{rule_id} → 규칙 삭제
- ✅ POST /api/v1/category-auto-rules/simulate → 시뮬레이션
- **테스트 수**: 23개

---

## 실행 방법

### 전체 테스트 실행
```bash
# 모든 테스트
pytest

# API 테스트만
pytest tests/api/

# 특정 파일
pytest tests/api/test_transactions_upload.py -v

# 특정 테스트 함수
pytest tests/api/test_auth.py::test_register_success -v
```

### 옵션
```bash
# 상세 출력
pytest -v

# 빠른 실패 (첫 에러에서 중단)
pytest -x

# 병렬 실행 (pytest-xdist 필요)
pytest -n auto

# 커버리지 측정 (pytest-cov 필요)
pytest --cov=app --cov-report=html
```

---

## 모범 사례

### 1. 테스트 격리
- 각 테스트는 독립적으로 실행 가능해야 함
- DB 트랜잭션 롤백으로 상태 격리
- 파일 업로드 시 임시 경로 사용 (pytest tmp_path)

### 2. 명확한 어설션
```python
# Good
assert response.status_code == 201
assert "id" in response.json()
assert response.json()["name"] == "Test Asset"

# Better
data = response.json()
assert response.status_code == 201, f"Unexpected response: {data}"
assert data["name"] == "Test Asset"
assert data["asset_type"] == "stock"
```

### 3. 고정된 시간
날짜 의존 로직은 freezegun으로 고정:
```python
@freeze_time("2025-11-13 12:00:00")
def test_transaction_date():
    # now()가 항상 2025-11-13 12:00:00
    ...
```

### 4. 재사용 가능한 헬퍼
공통 패턴은 헬퍼 함수로:
```python
# tests/api/helpers.py
def create_test_asset(client, auth_header, **kwargs):
    """테스트용 자산 생성 헬퍼"""
    payload = {"name": "Test", "asset_type": "stock", **kwargs}
    response = client.post("/api/v1/assets", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()
```

---

## CI/CD 통합

### 개요
GitHub Actions 등 CI 환경에서는 외부 PostgreSQL/Redis 서버에 접속할 수 없는 경우가 많습니다.  
이 경우 **임시 서비스 컨테이너**를 사용하여 격리된 테스트 환경을 구성합니다.

### GitHub Actions 예시 (임시 PostgreSQL/Redis 사용)

`.github/workflows/test.yml` 파일을 생성:

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      # 임시 PostgreSQL 서비스 (외부 DB 접속 불필요)
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: jsmdb_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      # 임시 Redis 서비스 (외부 Redis 접속 불필요)
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx freezegun
      
      - name: Run Alembic migrations
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/jsmdb_test
        run: alembic upgrade head
      
      - name: Run tests
        env:
          DATABASE_URL_TEST: postgresql://testuser:testpass@localhost:5432/jsmdb_test
          REDIS_URL_TEST: redis://localhost:6379/0
          SECRET_KEY: github-actions-test-secret-key
        run: pytest -v --cov=app --cov-report=term-missing
      
      - name: Upload coverage reports
        if: success()
        uses: codecov/codecov-action@v3
        with:
          fail_ci_if_error: false
```

### 주요 포인트

1. **services 섹션**: GitHub이 자동으로 PostgreSQL/Redis 컨테이너를 시작합니다.
2. **격리된 환경**: 테스트마다 새로운 컨테이너가 생성되어 깨끗한 상태에서 시작합니다.
3. **외부 접속 불필요**: 모든 인프라가 GitHub 서버 내부에서 실행됩니다.
4. **health check**: 서비스가 준비될 때까지 대기 후 테스트를 시작합니다.
5. **환경 변수**: 테스트용 DB/Redis 주소를 `localhost`로 설정합니다.

### 로컬 Docker Compose 테스트 환경

로컬에서도 동일한 격리 환경을 사용하려면 `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  db_test:
    image: postgres:15
    environment:
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
      POSTGRES_DB: jsmdb_test
    ports:
      - "5433:5432"  # 기존 DB(5432)와 충돌 방지
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser"]
      interval: 5s
      timeout: 5s
      retries: 5
  
  redis_test:
    image: redis:7-alpine
    ports:
      - "6380:6379"  # 기존 Redis(6379)와 충돌 방지
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

**실행:**
```bash
# 테스트 인프라 시작
docker-compose -f docker-compose.test.yml up -d

# 테스트 실행
DATABASE_URL_TEST=postgresql://testuser:testpass@localhost:5433/jsmdb_test \
REDIS_URL_TEST=redis://localhost:6380/0 \
alembic upgrade head && pytest -v

# 종료 및 정리
docker-compose -f docker-compose.test.yml down -v
```

---

## 트러블슈팅

### 문제: 테스트 간 데이터 간섭
**해결**: 각 테스트마다 트랜잭션 롤백 확인. `db_session` 픽스처가 제대로 rollback하는지 검증.

### 문제: Alembic 마이그레이션 충돌
**해결**: 테스트 시작 시 스키마 완전 드롭 후 재생성. 또는 별도 DB 사용.

### 문제: 비동기 테스트 오류
**해결**: `pytest-asyncio` 설치 및 `@pytest.mark.asyncio` 데코레이터 사용.

### 문제: 파일 업로드 인코딩 오류
**해결**: 샘플 파일을 `tests/testdata/`에 바이너리 모드로 저장. Git LFS 고려.

---

## 참고 자료

- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Documentation](https://docs.pytest.org/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

---

## 다음 단계

### ✅ 완료된 항목 (Phase 1: Core API)
1. ✅ 테스트 환경 구성 (DB, 환경변수)
2. ✅ `tests/conftest.py` 픽스처 작성
3. ✅ 인증 테스트 (test_auth.py) - 11개
4. ✅ 자산 CRUD 테스트 (test_assets.py) - 15개
5. ✅ 거래 CRUD 테스트 (test_transactions_crud.py) - 26개
6. ✅ 파일 업로드 테스트 (test_transactions_upload.py) - 16개
7. ✅ 조회/필터 테스트 (test_transactions_query.py) - 24개
8. ✅ 포트폴리오 테스트 (test_portfolio.py) - 14개
9. ✅ 경계 조건 및 에러 처리 (test_edge_cases.py) - 34개
**Phase 1 소계**: 140개 테스트 완료

### ✅ 완료된 항목 (Phase 2: Extended Features - 진행 중)
10. ✅ 계좌 관리 테스트 (test_accounts.py) - 30개
    - 계좌 CRUD, 활성화/비활성화, 공유 관리
    - 스키마 검증 (owner_id 필드 수정)
    - 권한 체크 및 AccountShare 관계 테스트
11. ✅ 카테고리 관리 테스트 (test_categories.py) - 37개
    - 카테고리 CRUD, 트리 구조, 시드 데이터
    - 계층 구조 및 parent_id 검증
    - flow_type 필터링 및 검색
12. ✅ 태그 관리 테스트 (test_tags.py) - 42개
    - 태그 CRUD, 엔티티 연결/해제, 일괄 작업
    - 중복 태그 방지 및 allowed_types 검증
    - 자산, 계좌, 거래에 태그 연결
13. ✅ 리마인더 테스트 (test_reminders.py) - 41개
    - 리마인더 CRUD, 스누즈, 완료 처리, 통계
    - 대기 중인 리마인더 조회
    - 자동 완료(auto_complete_on_view) 기능
14. ✅ 활동 로그 테스트 (test_activities.py) - 26개
    - 댓글/로그 생성 및 관리
    - 스레드 조회 및 필터링
    - visibility 설정 및 검증
15. ✅ 자동 규칙 테스트 (test_auto_rules.py) - 23개
    - 규칙 CRUD, 패턴 매칭 (exact/contains/regex)
    - 시뮬레이션 및 우선순위 검증
    - UniqueConstraint 검증
**Phase 2 소계**: 199개 테스트 완료

### 🎉 완료된 항목 (Phase 2: Extended Features - 완료!)

**총 테스트 수**: 339개 (Phase 1: 140 + Phase 2: 199)

### 🚀 DevOps & Quality (Phase 3)
16. ⬜ CI/CD 파이프라인 구성 (GitHub Actions)
    - 자동 테스트 실행
    - PostgreSQL/Redis 서비스 컨테이너
    - 커버리지 리포트
17. ⬜ 코드 커버리지 측정 및 개선
    - 목표: 80%+ 커버리지
    - pytest-cov 통합
    - 커버리지 뱃지 추가
18. ⬜ 성능 테스트
    - 대량 데이터 처리 (1000+ 거래)
    - 동시 요청 처리
    - 응답 시간 벤치마크

### 📋 우선순위 권장사항
**High Priority** (Phase 2 먼저 완료):
- 계좌 관리 (accounts) - 자산과 밀접한 연관
- 카테고리 관리 (categories) - 거래 분류에 필수

**Medium Priority**:
- 태그 관리 (tags) - 조직화 기능
- 리마인더 (reminders) - 사용자 경험 향상

**Low Priority**:
- 활동 로그 (activities) - 감사/모니터링 용도
- 자동 규칙 (auto_rules) - 고급 기능

**DevOps** (병렬 진행 가능):
- CI/CD 파이프라인은 현재 테스트만으로도 구성 가능
- 커버리지 측정으로 누락된 영역 파악

---

**작성일**: 2025-11-13  
**최종 업데이트**: 2025-11-13 (140개 테스트 완료, 6개 엔드포인트 그룹 추가)
