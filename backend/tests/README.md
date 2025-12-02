# Tests

jsm_be 프로젝트의 API 통합 테스트입니다.

## 빠른 시작

### 1. 의존성 설치
```bash
pip install pytest pytest-asyncio httpx fakeredis freezegun
```

### 2. 테스트 DB 설정
```bash
# Docker로 PostgreSQL 실행
docker run -d \
  --name jsm_test_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=jsm_test \
  -p 5432:5432 \
  postgres:15

# 환경변수 설정 (.env.test 또는 export)
export DATABASE_URL_TEST=postgresql://user:password@localhost:5432/jsm_test
export SECRET_KEY=test-secret-key
```

### 3. 테스트 실행
```bash
# 모든 테스트
pytest

# API 테스트만
pytest tests/api/ -v

# 특정 파일
pytest tests/api/test_transactions_upload.py -v

# 커버리지 포함
pytest --cov=app --cov-report=html
```

## 테스트 구조

```
tests/
├── README.md                    # 이 파일
├── conftest.py                  # 공통 픽스처 (DB, app)
├── test_file_parser.py          # 파일 파싱 유닛 테스트
├── api/
│   ├── conftest.py              # API 테스트 픽스처 (client, auth)
│   ├── test_auth.py             # 인증 API
│   ├── test_assets.py           # 자산 CRUD
│   ├── test_transactions.py     # 거래 CRUD
│   └── test_transactions_upload.py  # 파일 업로드 ⭐
└── testdata/
    ├── 토스뱅크_거래내역.xlsx   # 암호화 샘플 파일
    ├── mirae.csv                # 미래에셋 샘플
    └── kb.csv                   # KB증권 샘플
```

## 주요 테스트 시나리오

- ✅ **인증**: 회원가입, 로그인, 토큰 검증
- ✅ **자산 CRUD**: 생성, 조회, 수정, 삭제, 권한 체크
- ✅ **거래 CRUD**: 생성, 수정, 삭제, 비즈니스 규칙 검증
  - 매수/매도 시 자동 현금 거래 생성 (`out_asset`, `in_asset` 타입)
  - 복식부기 패턴 검증 (`related_transaction_id` 연결)
- ✅ **거래 메타데이터**: extras JSONB 필드 (환율, 외부 시스템 데이터 등)
- ✅ **파일 업로드**: 토스뱅크 암호화 xlsx, CSV (UTF-8/CP949), dry_run 모드
- ✅ **조회/필터**: 페이지네이션, 날짜 범위, 거래 유형 필터
- ✅ **포트폴리오**: 요약 데이터, 수익률 계산

## 상세 가이드

전체 테스트 전략, 픽스처 설계, CI/CD 통합 등 자세한 내용은 다음 문서를 참고하세요:

📖 **[Testing Guide](../docs/testing-guide.md)**

---

**마지막 업데이트**: 2025-11-27

주요 변경사항:
- 테이블명 변경: `asset_transactions` → `transactions`
- 필드명 변경: `transaction_metadata` → `extras`
- 모델 클래스명 변경: `AssetTransaction` → `Transaction`
