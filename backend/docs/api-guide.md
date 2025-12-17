# J's Money API 사용 가이드

## 개요

J's Money Backend API는 개인 자산관리를 위한 RESTful API입니다. 이 문서는 외부 개발자나 AI Agent가 API를 쉽게 사용할 수 있도록 작성되었습니다.

## 기본 정보

- **Base URL**: `https://jsfamily2.myds.me:40041`
- **API Version**: v1
- **API Prefix**: `/api/v1`
- **인증 방식**: JWT Bearer Token
- **응답 형식**: JSON

## API 문서

- **Swagger UI**: https://jsfamily2.myds.me:40041/docs
- **ReDoc**: https://jsfamily2.myds.me:40041/redoc
- **OpenAPI Spec**: https://jsfamily2.myds.me:40041/api/v1/openapi.json

## 빠른 시작

### 1. 관리자 계정으로 로그인

```bash
curl -X POST "https://jsfamily2.myds.me:40041/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@jsmoney.com",
    "password": "admin123"
  }'
```

**응답 예시:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. 인증 토큰 사용

이후 모든 요청에 Authorization 헤더를 포함:

```bash
curl -X GET "https://jsfamily2.myds.me:40041/api/v1/users/me" \
  -H "Authorization: Bearer {access_token}"
```

## 주요 엔드포인트

### 인증 (Authentication)

#### POST /api/v1/auth/register
새로운 사용자 등록

**요청:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "홍길동"
}
```

#### POST /api/v1/auth/login
로그인 및 토큰 발급

**요청:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

### 사용자 (Users)

#### GET /api/v1/users/me
현재 로그인한 사용자 정보 조회

**헤더:** `Authorization: Bearer {token}`

**응답:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "홍길동",
  "is_active": true,
  "created_at": "2025-10-28T12:00:00"
}
```

### 계좌 (Accounts)

#### GET /api/v1/accounts
사용자의 모든 계좌 조회

**응답:**
```json
[
  {
    "id": "uuid",
    "name": "신한은행 입출금",
    "account_type": "은행계좌",
    "balance": 1000000.00,
    "currency": "KRW",
    "is_active": true
  }
]
```

#### POST /api/v1/accounts
새 계좌 생성

**요청:**
```json
{
  "name": "신한은행 입출금",
  "account_type_id": 1,
  "institution": "신한은행",
  "balance": 1000000.00,
  "currency": "KRW"
}
```

#### GET /api/v1/accounts/{account_id}
특정 계좌 조회

#### PUT /api/v1/accounts/{account_id}
계좌 정보 수정

#### DELETE /api/v1/accounts/{account_id}
계좌 삭제 (비활성화)

#### POST /api/v1/accounts/{account_id}/shares
계좌 공유 생성

**요청:**
```json
{
  "user_id": "shared-user-uuid",
  "role": "viewer",
  "can_read": true,
  "can_write": false,
  "can_delete": false,
  "can_share": false
}
```

**응답:**
```json
{
  "id": "uuid",
  "account_id": "uuid",
  "user_id": "shared-user-uuid",
  "role": "viewer",
  "can_read": true,
  "can_write": false,
  "can_delete": false,
  "can_share": false,
  "shared_at": "2025-11-13T10:00:00"
}
```

#### GET /api/v1/accounts/{account_id}/shares
계좌 공유 목록 조회

#### PATCH /api/v1/accounts/{account_id}/shares/{share_id}
계좌 공유 권한 수정

#### DELETE /api/v1/accounts/{account_id}/shares/{share_id}
계좌 공유 삭제

### 거래 내역 (Transactions)

#### GET /api/v1/transactions
거래 내역 조회 (필터링 및 페이징 지원)

**쿼리 파라미터:**
- `asset_id`: 자산 ID로 필터링
- `account_id`: 계좌 ID로 필터링
- `type`: 거래 유형 (buy, sell, deposit, withdraw 등)
- `category_id`: 카테고리 ID로 필터링
- `flow_type`: 거래 흐름 필터 (expense, income, transfer, investment, neutral, undefined)
- `start_date`: 시작일 (YYYY-MM-DD)
- `end_date`: 종료일 (YYYY-MM-DD)
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지당 항목 수 (기본값: 20, 최대: 100)

**응답:**
```json
{
  "items": [
    {
      "id": "uuid",
      "asset_id": "uuid",
      "type": "buy",
      "quantity": 10.0,
      "transaction_date": "2025-10-25T09:30:00Z",
      "description": "삼성전자 매수",
      "memo": "장기 투자",
      "flow_type": "investment",
      "category_id": "uuid",
      "category": {
        "id": "uuid",
        "name": "투자",
        "flow_type": "investment"
      },
      "extras": {
        "price": 67000,
        "fee": 335,
        "tax": 0
      },
      "asset": {
        "id": "uuid",
        "name": "삼성전자",
        "asset_type": "stock",
        "symbol": "005930",
        "currency": "KRW"
      }
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

#### POST /api/v1/transactions
새 거래 기록

**요구 사항**
- 거래 생성/업로드 시 transactions.description(또는 memo 등)을 검사하여 특정 문자열(키워드)이 포함되면 자동으로 해당 카테고리(category_id)를 지정한다.
- 카테고리 지정 시 자동으로 해당 카테고리의 flow_type이 거래에 할당된다. (사용자 확인 불필요)
- flow_type이 명시적으로 제공되지 않으면 카테고리의 flow_type으로 설정되며, 카테고리 미지정 시 'undefined'로 설정된다.

**요청:**
```json
{
  "account_id": "uuid",
  "type": "expense",
  "amount": 50000.00,
  "description": "마트 장보기",
  "category_id": 5,
  "transaction_date": "2025-10-28"
}
```

#### POST /api/v1/transactions/upload
파일 업로드를 통한 거래 일괄 등록

**요청 (multipart/form-data):**
- `file`: Excel 또는 CSV 파일
- `asset_id`: 자산 ID
- `password`: (선택) 암호화된 Excel 파일의 비밀번호
- `dry_run`: (선택) true일 경우 실제 저장 없이 검증만 수행

**지원 형식:**
- 토스뱅크 (.xlsx)
- 미래에셋증권 (.csv)
- KB증권 (.csv)
- 표준 형식 (.csv, .xlsx)

**응답:**
```json
{
  "success_count": 150,
  "error_count": 2,
  "errors": [
    {
      "row": 5,
      "error": "Invalid transaction type"
    }
  ],
  "transactions": [...]
}
```

### 자산 (Assets)

#### POST /api/v1/assets
자산 생성

**요청:**
```json
{
  "account_id": "uuid",
  "name": "삼성전자",
  "asset_type": "stock",
  "symbol": "005930",
  "currency": "KRW"
}
```

#### GET /api/v1/assets
자산 목록 조회

**쿼리 파라미터:**
- `account_id`: 계좌별 필터링
- `asset_type`: 자산 유형별 필터링
- `is_active`: 활성화 상태 필터링
- `symbol`: 심볼 부분 검색 (account_id와 함께 전달 시 해당 계좌의 특정 심볼만)

**응답:**
```json
{
  "items": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "name": "삼성전자",
      "asset_type": "stock",
      "symbol": "005930",
      "balance": 100.0,
      "currency": "KRW",
      "is_active": true
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

#### GET /api/v1/assets/{asset_id}
특정 자산 조회

응답 예시 (Redis 기반 실시간 필드 포함):
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "account_id": "uuid",
  "name": "삼성전자",
  "asset_type": "stock",
  "symbol": "005930",
  "market": "KOSPI",
  "currency": "KRW",
  "asset_metadata": {"strategy": {"type": "target_value"}},
  "is_active": true,
  "created_at": "2025-12-17T12:34:56Z",
  "updated_at": "2025-12-17T12:34:56Z",
  "balance": 100.0,
  "price": 68000.0,
  "change": 0.74,
  "need_trade": {
    "price": 67500.0,
    "quantity": 10.0,
    "ttl": 540
  },
  "account": {"id": "uuid", "name": "증권계좌", "account_type": "securities"}
}
```

#### PUT /api/v1/assets/{asset_id}
자산 정보 수정

#### DELETE /api/v1/assets/{asset_id}
자산 삭제

#### GET /api/v1/assets/{asset_id}/summary
자산 요약 정보 조회 (거래 내역, 수익률 포함)

#### POST /api/v1/assets/{asset_id}/recalculate-balance
자산 잔고 재계산

#### PUT /api/v1/assets/{asset_id}/need_trade
수동 거래 필요 정보를 설정 (Redis 저장, TTL=600초)

요청:
```json
{
  "price": 67500.0,
  "quantity": 10
}
```

응답:
```json
{
  "asset_id": "uuid",
  "need_trade": {"price": 67500.0, "quantity": 10.0, "ttl": 600},
  "updated": true
}
```

### 카테고리 (Categories)

#### GET /api/v1/categories
카테고리 목록 조회

**쿼리 파라미터:**
- `flow_type`: 유형별 필터링 (expense, income, transfer, investment, neutral)
- `is_active`: 활성화 상태 필터링

**응답:**
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "식비",
      "parent_id": null,
      "flow_type": "expense",
      "is_active": true
    }
  ],
  "total": 30
}
```

#### GET /api/v1/categories/tree
카테고리 계층 구조 조회

**응답:**
```json
[
  {
    "id": "uuid",
    "name": "생활비",
    "flow_type": "expense",
    "children": [
      {
        "id": "uuid",
        "name": "식비",
        "flow_type": "expense",
        "children": []
      },
      {
        "id": "uuid",
        "name": "교통비",
        "flow_type": "expense",
        "children": []
      }
    ]
  }
]
```

#### POST /api/v1/categories
카테고리 생성

**요청:**
```json
{
  "name": "식비",
  "parent_id": null,
  "flow_type": "expense",
  "is_active": true
}
```

#### GET /api/v1/categories/{category_id}
특정 카테고리 조회

#### PUT /api/v1/categories/{category_id}
카테고리 수정

#### DELETE /api/v1/categories/{category_id}
카테고리 삭제

#### POST /api/v1/categories/seed
기본 카테고리 생성 (시드 데이터)

### 카테고리 자동 분류 규칙 (Auto Rules)

#### GET /api/v1/auto-rules
카테고리 자동 분류 규칙 목록 조회

**응답:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "category_id": "uuid",
    "pattern_type": "contains",
    "pattern_text": "스타벅스",
    "priority": 100,
    "is_active": true
  }
]
```

#### POST /api/v1/auto-rules
자동 분류 규칙 생성

**요청:**
```json
{
  "category_id": "uuid",
  "pattern_type": "contains",
  "pattern_text": "스타벅스",
  "priority": 100,
  "is_active": true
}
```

**pattern_type 옵션:**
- `exact`: 정확히 일치
- `contains`: 포함
- `regex`: 정규식

#### PUT /api/v1/auto-rules/{rule_id}
자동 분류 규칙 수정

#### DELETE /api/v1/auto-rules/{rule_id}
자동 분류 규칙 삭제

#### POST /api/v1/auto-rules/simulate
규칙 시뮬레이션 (적용 결과 미리보기)

**요청:**
```json
{
  "description": "스타벅스 강남점",
  "memo": "커피 구매"
}
```

**응답:**
```json
{
  "matched_rule_id": "uuid",
  "category_id": "uuid",
  "category_name": "카페/음료",
  "confidence": "high"
}
```

### 태그 (Tags)

#### POST /api/v1/tags
태그 생성

**요청:**
```json
{
  "name": "장기투자",
  "color": "#FF5733",
  "description": "5년 이상 보유 예정",
  "allowed_types": ["asset", "account", "transaction"]
}
```

#### GET /api/v1/tags
태그 목록 조회

**응답:**
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "장기투자",
      "color": "#FF5733",
      "description": "5년 이상 보유 예정",
      "allowed_types": ["asset", "account", "transaction"]
    }
  ],
  "total": 10
}
```

#### GET /api/v1/tags/{tag_id}
특정 태그 조회

#### PATCH /api/v1/tags/{tag_id}
태그 수정

#### DELETE /api/v1/tags/{tag_id}
태그 삭제

#### POST /api/v1/tags/attach
태그 연결

**요청:**
```json
{
  "tag_id": "uuid",
  "taggable_type": "asset",
  "taggable_id": "uuid"
}
```

**taggable_type 옵션:**
- `asset`: 자산
- `account`: 계좌
- `transaction`: 거래

#### POST /api/v1/tags/attach-batch
태그 일괄 연결

**요청:**
```json
{
  "tag_id": "uuid",
  "taggable_type": "asset",
  "taggable_ids": ["uuid1", "uuid2", "uuid3"]
}
```

#### DELETE /api/v1/tags/detach/{taggable_id}
태그 연결 해제

#### GET /api/v1/tags/entity/{taggable_type}/{taggable_id}
특정 엔티티의 모든 태그 조회

**응답:**
```json
{
  "taggable_type": "asset",
  "taggable_id": "uuid",
  "tags": [
    {
      "id": "uuid",
      "name": "장기투자",
      "color": "#FF5733"
    }
  ]
}
```

### 알림 (Reminders)

#### POST /api/v1/reminders
알림 생성

**요청:**
```json
{
  "remindable_type": "asset",
  "remindable_id": "uuid",
  "reminder_type": "review",
  "title": "삼성전자 보유 검토",
  "description": "3개월마다 투자 전략 검토",
  "remind_at": "2025-12-01T09:00:00Z",
  "repeat_interval": "monthly",
  "priority": 1
}
```

**reminder_type 옵션:**
- `review`: 검토
- `dividend`: 배당
- `rebalance`: 리밸런싱
- `deadline`: 마감일
- `custom`: 커스텀

**repeat_interval 옵션:**
- `daily`: 매일
- `weekly`: 매주
- `monthly`: 매월
- `yearly`: 매년
- `null`: 반복 없음

#### GET /api/v1/reminders
알림 목록 조회

**쿼리 파라미터:**
- `is_active`: 활성화 상태
- `is_dismissed`: 무시 상태
- `reminder_type`: 알림 유형

**응답:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "remindable_type": "asset",
    "remindable_id": "uuid",
    "reminder_type": "review",
    "title": "삼성전자 보유 검토",
    "remind_at": "2025-12-01T09:00:00Z",
    "repeat_interval": "monthly",
    "priority": 1,
    "is_active": true,
    "is_dismissed": false
  }
]
```

#### GET /api/v1/reminders/pending
대기 중인 알림 조회 (현재 시각 기준)

#### GET /api/v1/reminders/stats
알림 통계 조회

**응답:**
```json
{
  "total": 50,
  "active": 45,
  "dismissed": 5,
  "pending": 10,
  "overdue": 2
}
```

#### GET /api/v1/reminders/{reminder_id}
특정 알림 조회

#### PATCH /api/v1/reminders/{reminder_id}
알림 수정

#### DELETE /api/v1/reminders/{reminder_id}
알림 삭제

#### PATCH /api/v1/reminders/{reminder_id}/dismiss
알림 무시

**응답:**
```json
{
  "id": "uuid",
  "is_dismissed": true,
  "dismissed_at": "2025-11-13T10:30:00Z"
}
```

#### PATCH /api/v1/reminders/{reminder_id}/snooze
알림 스누즈 (미루기)

**요청:**
```json
{
  "snooze_until": "2025-11-14T09:00:00Z"
}
```

#### GET /api/v1/reminders/entity/{remindable_type}/{remindable_id}
특정 엔티티의 모든 알림 조회

### 활동 (Activities)

활동 시스템은 댓글과 로그를 통합 관리합니다.

#### POST /api/v1/activities
활동 생성 (댓글 또는 로그)

**댓글 생성 예시:**
```json
{
  "target_type": "asset",
  "target_id": "uuid",
  "activity_type": "comment",
  "content": "장기 보유 예정",
  "visibility": "private",
  "parent_id": null
}
```

**로그 생성 예시:**
```json
{
  "target_type": "transaction",
  "target_id": "uuid",
  "activity_type": "log",
  "payload": {
    "action": "modified",
    "field": "amount",
    "old_value": 10000,
    "new_value": 15000
  },
  "visibility": "private",
  "is_immutable": true
}
```

**activity_type 옵션:**
- `comment`: 댓글
- `log`: 로그

**visibility 옵션:**
- `private`: 본인만
- `shared`: 공유된 사용자
- `public`: 모두

#### GET /api/v1/activities
활동 목록 조회

**쿼리 파라미터:**
- `target_type`: 대상 유형
- `target_id`: 대상 ID
- `activity_type`: 활동 유형
- `visibility`: 가시성

**응답:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "target_type": "asset",
    "target_id": "uuid",
    "activity_type": "comment",
    "content": "장기 보유 예정",
    "visibility": "private",
    "is_deleted": false,
    "created_at": "2025-11-13T10:00:00Z"
  }
]
```

#### GET /api/v1/activities/{activity_id}
특정 활동 조회

#### GET /api/v1/activities/thread/{thread_root_id}
스레드 조회 (댓글과 대댓글)

**응답:**
```json
[
  {
    "id": "thread-root-uuid",
    "content": "원본 댓글",
    "parent_id": null,
    "created_at": "2025-11-13T10:00:00Z"
  },
  {
    "id": "reply-uuid",
    "content": "대댓글",
    "parent_id": "thread-root-uuid",
    "created_at": "2025-11-13T10:05:00Z"
  }
]
```

#### PATCH /api/v1/activities/{activity_id}
활동 수정

**주의:** `is_immutable=true`인 로그는 수정 불가

#### DELETE /api/v1/activities/{activity_id}
활동 삭제 (소프트 삭제)

### 투자 자산 (Investment Assets)

#### GET /api/v1/investments/assets
투자 자산 목록 조회

**응답:**
```json
[
  {
    "id": "uuid",
    "asset_type": "국내주식",
    "symbol": "005930",
    "name": "삼성전자",
    "quantity": 10.0,
    "average_price": 70000.00,
    "current_price": 75000.00,
    "total_value": 750000.00,
    "profit_loss": 50000.00,
    "profit_loss_rate": 7.14
  }
]
```

#### POST /api/v1/investments/assets
투자 자산 추가

**요청:**
```json
{
  "asset_type_id": 1,
  "symbol": "005930",
  "name": "삼성전자",
  "quantity": 10.0,
  "average_price": 70000.00,
  "currency": "KRW"
}
```

#### POST /api/v1/investments/transactions
투자 거래 기록

**요청:**
```json
{
  "asset_id": "uuid",
  "type": "buy",
  "quantity": 5.0,
  "price": 72000.00,
  "fee": 1000.00,
  "transaction_date": "2025-10-28"
}
```

### 실물 자산 (Real Assets)

#### GET /api/v1/real-assets
실물 자산 목록 조회

**응답:**
```json
[
  {
    "id": "uuid",
    "asset_type": "자동차",
    "name": "현대 아이오닉5",
    "purchase_date": "2023-05-10",
    "purchase_price": 50000000.00,
    "current_value": 40000000.00,
    "currency": "KRW"
  }
]
```

#### POST /api/v1/real-assets
실물 자산 추가

**요청:**
```json
{
  "asset_type_id": 5,
  "name": "현대 아이오닉5",
  "purchase_date": "2023-05-10",
  "purchase_price": 50000000.00,
  "current_value": 40000000.00,
  "currency": "KRW",
  "description": "2023년식 롱레인지"
}
```

## 참조 데이터

### 계좌 유형 (Account Types)

#### GET /api/v1/account-types

```json
[
  {"id": 1, "name": "은행계좌"},
  {"id": 2, "name": "증권계좌"},
  {"id": 3, "name": "현금"},
  {"id": 4, "name": "체크카드"},
  {"id": 5, "name": "신용카드"},
  {"id": 6, "name": "저축예금"},
  {"id": 7, "name": "적금"},
  {"id": 8, "name": "가상화폐지갑"}
]
```

### 거래 카테고리 (Transaction Categories)

#### GET /api/v1/transaction-categories

**수입:**
- 급여, 부수입, 이자, 배당

**지출:**
- 식비, 교통비, 통신비, 주거비, 의료비, 쇼핑, 문화생활, 교육, 경조사, 기타지출

**이체:**
- 계좌이체, 저축

### 투자 자산 유형 (Asset Types)

#### GET /api/v1/asset-types

```json
[
  {"id": 1, "name": "국내주식"},
  {"id": 2, "name": "해외주식"},
  {"id": 3, "name": "가상화폐"},
  {"id": 4, "name": "채권"},
  {"id": 5, "name": "펀드"},
  {"id": 6, "name": "금"},
  {"id": 7, "name": "기타투자"}
]
```

### 실물 자산 유형 (Real Asset Types)

#### GET /api/v1/real-asset-types

```json
[
  {"id": 1, "name": "아파트"},
  {"id": 2, "name": "주택"},
  {"id": 3, "name": "상가"},
  {"id": 4, "name": "토지"},
  {"id": 5, "name": "자동차"},
  {"id": 6, "name": "오토바이"},
  {"id": 7, "name": "귀금속"},
  {"id": 8, "name": "예술품"},
  {"id": 9, "name": "기타자산"}
]
```

## 에러 처리

### 표준 에러 응답

```json
{
  "detail": "Error message here"
}
```

### HTTP 상태 코드

- `200 OK`: 성공
- `201 Created`: 리소스 생성 성공
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스를 찾을 수 없음
- `422 Unprocessable Entity`: 유효성 검증 실패
- `500 Internal Server Error`: 서버 에러

### 유효성 검증 에러 예시

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## 데이터 제약사항

### 금액 (Numeric)
- 정밀도: 소수점 2자리
- 최대값: 9,999,999,999,999.99

### 날짜 형식
- ISO 8601: `YYYY-MM-DD`
- 예시: `2025-10-28`

### 통화 코드
- ISO 4217 형식 (3자리)
- 기본값: `KRW`
- 지원: KRW, USD, EUR, JPY 등

## 페이징

목록 조회 API는 페이징을 지원합니다:

**요청:**
```
GET /api/v1/transactions?page=2&per_page=20
```

**응답:**
```json
{
  "items": [...],
  "total": 100,
  "page": 2,
  "per_page": 20,
  "total_pages": 5
}
```

## 보안

### HTTPS Only
- 모든 API는 HTTPS를 통해서만 접근 가능
- HTTP 요청은 자동으로 HTTPS로 리다이렉트

### 토큰 만료
- Access Token 유효기간: 30분
- 만료된 토큰 사용 시 401 Unauthorized 응답

### 비밀번호 정책
- 최소 길이: 8자
- 권장: 영문, 숫자, 특수문자 조합

## AI Agent 사용 예시

### Python 예시

```python
import requests

BASE_URL = "https://jsfamily2.myds.me:40041/api/v1"

# 1. 로그인
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "admin@jsmoney.com", "password": "admin123"}
)
token = response.json()["access_token"]

# 2. 헤더 설정
headers = {"Authorization": f"Bearer {token}"}

# 3. 계좌 조회
accounts = requests.get(f"{BASE_URL}/accounts", headers=headers).json()

# 4. 거래 기록
transaction = requests.post(
    f"{BASE_URL}/transactions",
    headers=headers,
    json={
        "account_id": accounts[0]["id"],
        "type": "expense",
        "amount": 10000.00,
        "description": "점심식사",
        "transaction_date": "2025-10-28"
    }
)
```

### JavaScript 예시

```javascript
const BASE_URL = "https://jsfamily2.myds.me:40041/api/v1";

// 1. 로그인
const loginResponse = await fetch(`${BASE_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@jsmoney.com',
    password: 'admin123'
  })
});
const { access_token } = await loginResponse.json();

// 2. 계좌 조회
const accountsResponse = await fetch(`${BASE_URL}/accounts`, {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const accounts = await accountsResponse.json();

// 3. 거래 기록
const transactionResponse = await fetch(`${BASE_URL}/transactions`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    account_id: accounts[0].id,
    type: 'expense',
    amount: 10000.00,
    description: '점심식사',
    transaction_date: '2025-10-28'
  })
});
```

## 자주 묻는 질문

### Q: 테스트 계정은 어떻게 만드나요?
A: `/api/v1/auth/register` 엔드포인트를 사용하여 새 계정을 생성할 수 있습니다.

### Q: 토큰이 만료되면 어떻게 하나요?
A: 다시 로그인하여 새 토큰을 발급받아야 합니다.

### Q: 계좌를 삭제하면 거래 내역도 삭제되나요?
A: 네, 계좌 삭제 시 관련된 모든 거래 내역도 함께 삭제됩니다 (CASCADE).

### Q: 통화를 변환할 수 있나요?
A: 현재 버전에서는 통화 변환을 지원하지 않습니다. 각 계좌/자산은 독립적인 통화를 사용합니다.

### Q: 카테고리 자동 분류는 어떻게 작동하나요?
A: `/api/v1/auto-rules`에서 규칙을 등록하면, 거래 생성 시 description/memo 필드를 검사하여 자동으로 카테고리를 지정합니다. 우선순위(priority)가 낮을수록 먼저 적용됩니다.

### Q: 태그는 어떤 엔티티에 적용할 수 있나요?
A: 자산(asset), 계좌(account), 거래(transaction)에 태그를 적용할 수 있습니다. 태그 생성 시 `allowed_types`로 적용 가능한 엔티티를 제한할 수 있습니다.

### Q: 알림 반복 설정은 어떻게 하나요?
A: 알림 생성 시 `repeat_interval`을 설정하면 자동으로 반복됩니다. daily(매일), weekly(매주), monthly(매월), yearly(매년) 중 선택 가능하며, null이면 일회성 알림입니다.

### Q: 활동(Activity)의 댓글과 로그 차이는?
A: 댓글(`activity_type="comment"`)은 사용자가 작성하는 메모이고, 로그(`activity_type="log"`)는 시스템이 자동으로 기록하는 변경 이력입니다. 로그는 `is_immutable=true`로 설정하여 수정을 방지할 수 있습니다.

### Q: 거래 타입(TransactionType)은 어떤 것들이 있나요?
A: 다음 거래 타입을 지원합니다:
- **매수/매도**: `buy` (매수), `sell` (매도)
- **입출금**: `deposit` (입금), `withdraw` (출금)
- **자산거래 현금흐름**: `out_asset` (자산매수출금), `in_asset` (자산매도입금)
- **배당/이자**: `cash_dividend` (현금배당), `stock_dividend` (주식배당), `interest` (이자)
- **수수료**: `fee` (수수료)
- **이체**: `transfer_in` (이체입금), `transfer_out` (이체출금), `internal_transfer` (내부이체)
- **투자**: `invest` (투자), `redeem` (해지)
- **카드/자동이체**: `card_payment` (카드결제), `auto_transfer` (자동이체)
- **기타**: `adjustment` (수량조정), `promotion_deposit` (프로모션입금), `remittance` (송금), `exchange` (환전)

**복식부기 패턴**:
- 자산 매수: `buy` (자산 증가) + `out_asset` (현금 감소)가 `related_transaction_id`로 연결
- 자산 매도: `sell` (자산 감소) + `in_asset` (현금 증가)가 `related_transaction_id`로 연결

### Q: API 사용량 제한이 있나요?
A: 현재 버전에서는 rate limiting이 없지만, 향후 추가될 수 있습니다.

## 지원

문의사항이나 버그 리포트는 admin@jsmoney.com으로 연락주세요.

## 변경 이력

### v0.2.0 (2025-11-13)
- 카테고리 시스템 추가
- 카테고리 자동 분류 규칙 추가
- 태그 시스템 추가
- 알림 시스템 추가
- 활동(댓글/로그) 시스템 추가
- 계좌 공유 기능 추가
- 자산 관리 API 확장
- 파일 업로드 API 추가

### v0.1.0 (2025-10-28)
- 초기 API 릴리즈
- 기본 CRUD 기능
- JWT 인증
- 계좌, 거래, 투자자산, 실물자산 관리
