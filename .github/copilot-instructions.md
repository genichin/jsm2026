# AI Agent 개발 가이드 (J's Money Backend)

프로젝트에 특화된 규칙만 간결하게 정리했습니다. 일반론은 배제하고, 이 저장소(workspace)에서 바로 쓸 수 있는 지침만 제시합니다.

## 아키텍처 핵심
- 스택: FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL + Redis(실시간) + JWT 인증.
- 자산 중심 & 복식부기(double-entry): 모든 교환 거래는 반드시 2개의 `asset_transactions` 레코드이며 `related_transaction_id`로 연결합니다(현금 감소/자산 증가 등). 하나로 합치지 않습니다.
- 수량 규칙: `quantity > 0` 증가, `< 0` 감소, `= 0` 마커(예: 배당). 서비스/파서 전반에서 일관 유지.
- 하이브리드 저장소: PostgreSQL=권위 이력, Redis=실시간 잔고/평단/매수 큐(FIFO/LIFO/AVG). 쓰기 순서: DB 커밋 → Redis 반영(실패 시 복구 큐 등록 TODO 주석 남김).
- 다형 시스템: 태그, 리마인더, 액티비티는 동일 패턴(엔티티 타입 + 엔티티 ID). 기존 헬퍼/서비스 재사용, 중복 구현 금지.

## 주요 디렉터리
- `app/api/` 라우터들(프리픽스는 `settings.API_V1_PREFIX` 유지). 새로운 도메인 추가 시 `router` 생성 후 `main.py`에 태그와 함께 등록.
- `app/core/` 설정(`config.py`), 보안, DB 세션. 설정 접근은 `from app.core.config import settings`.
- `app/models/` SQLAlchemy 모델. 네이밍 유지(`asset_transactions` 사용, `transactions` 금지). 모델 변경 시 마이그레이션 동반.
- `app/schemas/` Pydantic 스키마. create/update/detail 분리 유지.
- `app/services/` 비즈니스 로직. DB+Redis 동기화 등 부수효과는 여기서 처리하고 라우터는 얇게 유지.
- `scripts/` 운영 스크립트(`init_db.py`, `seed_data.py`, `check_env.py`).
- `tests/` 통합/API 테스트. 공용 픽스처는 루트와 `tests/api/`의 `conftest.py`.

## 환경/설정
- 활성 환경은 `ENV`로 선택(development|production|test). `.env.development`/`.env.production` 심볼릭 링크 또는 명시 사용. 검증은 `scripts/check_env.py`.
- 시크릿 하드코딩 금지. `settings.SECRET_KEY`, `settings.DATABASE_URL` 등으로 접근.

## 데이터베이스/마이그레이션
- 모델 수정 후 자동 생성: `alembic revision --autogenerate -m "메모"` → `alembic upgrade head`.
- 과거 마이그레이션 파일은 수정하지 말고 새 리비전만 추가.
- 자산 교환 타입 추가 시 서비스 레이어에서 반드시 양쪽 레그(2건) 생성.

## Redis 패턴(`docs/redis-schema.md` 참고)
- 자산 키: `asset:{asset_id}:balance`, `avg_price`, `current_price`.
- 매수 큐: FIFO/LIFO는 Sorted Set(`purchase_queue:{asset_id}:FIFO`), AVG는 Hash(`:AVG`). 부분 매도 시 `remaining` 수량 갱신.
- 사용자 요약 캐시: `user:{user_id}:summary:{timeframe}` TTL≈300s. 새 거래 시 무효화.

## 테스트 워크플로
- 테스트 DB: `DATABASE_URL_TEST` 설정. 로컬 Postgres 또는 Docker 사용 후 `pytest` / `pytest tests/api/ -v` 실행.
- 비동기 테스트: `pytest-asyncio`, HTTP는 `httpx.AsyncClient` 픽스처 재사용.
- 신규 기능은 API 근접 통합 테스트 위주 + 계산/파서 최소 단위 테스트.

## 파일 업로드 파싱
- 지원: XLSX(토스 암호화 `msoffcrypto`), CSV(UTF-8/CP949). 행 정규화 → 내부 트랜잭션 스키마로 변환 후 저장.
- `dry_run` 모드로 카테고리 매핑/잔고를 커밋 없이 검증(`tests/test_transaction_file_upload.py` 패턴 참조).

## 컨벤션/주의사항
- 테이블명은 항상 `asset_transactions`(복수) 사용. `transactions` 금지.
- 카테고리 흐름 타입: expense, income, transfer, investment, neutral. 시드 구조의 계층 유지.
- 보안 미들웨어(HTTPSRedirect, TrustedHost, CORS)는 조건부 적용. 신규 미들웨어도 `settings.DEBUG`/허용 호스트 정책 준수.
- 라우터 태그/설명은 `main.py`의 OpenAPI 태그 메타데이터와 정합 유지.

## 새로운 도메인 추가 예시
1. `app/models/` 모델 추가 + 마이그레이션 생성.
2. `app/schemas/`에 Pydantic 스키마 추가.
3. `app/services/`에 DB 커밋 + Redis 동기화 서비스 구현.
4. `app/api/{domain}.py` 라우터로 CRUD 등록.
5. `main.py`에 `f"{settings.API_V1_PREFIX}/{domain}"` 프리픽스로 라우터/태그 등록.
6. `tests/api/test_{domain}.py`에 통합 테스트 추가(기존 인증 픽스처 재사용).

## 안전 변경 체크리스트
- 모델 변경 여부 → Alembic 새 리비전 생성/적용.
- Redis 영향 여부 → DB 커밋과 Redis 업데이트 모두 보장, 실패 시 롤백/복구 처리.
- 신규 엔드포인트 → 테스트 추가 + 라우터 등록 + OpenAPI 태그 정합성 확인.
- 민감 로직(손익/잔고) → 수량 부호 규칙 및 복식부기 페어링 준수.

피드백: 누락된 패턴/더 깊은 예제가 필요하면 알려주세요. 이 가이드는 의도적으로 간결합니다.

## 데이터베이스가 수정되는 경우 작업 리스트
데이터베이스 스키마가 수정되는 경우, 다음 작업들을 수행해야 합니다:
1. **모델 수정**: `app/models/` 디렉터리 내 관련 모델 파일을 수정합니다.
2. **마이그레이션 생성**: 터미널에서 다음 명령어를 실행하여 Alembic 마이그레이션 파일을 생성합니다:
   ```bash
   cd {workspace folder}/backend && .venv/bin/alembic revision --autogenerate -m "설명 메시지"
   ```
3. **마이그레이션 적용**: 생성된 마이그레이션을 데이터베이스에 적용합니다:
   ```bash
   .venv/bin/alembic upgrade head
   ```
4. **서비스 레이어 수정**: `app/services/` 디렉터리 내 관련 서비스 파일을 수정하여 데이터베이스 변경 사항을 반영합니다.
5. **API 라우터 수정**: `app/api/` 디렉터리 내 관련 라우터 파일을 수정하여 새로운 엔드포인트를 추가하거나 기존 엔드포인트를 업데이트합니다.
6. **테스트 추가/수정**: `tests/` 디렉터리 내 관련 테스트 파일을 추가하거나 수정하여 변경된 스키마에 대한 테스트를 작성합니다.
7. **문서 업데이트**: `backend/docs/database-schema.md` 파일을 수정하여 데이터베이스 스키마 변경 사항을 문서화합니다. 변경된 부분을 명확히 설명하고, 필요한 경우 예시도 추가합니다. `backend/docs/`의 다른 문서들도 필요에 따라 업데이트합니다.
