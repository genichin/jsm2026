# PostgreSQL Schema Design

**Database Version**: PostgreSQL 15+  
**Timezone Policy**: 모든 날짜/시간은 UTC로 저장, 애플리케이션 레벨에서 Asia/Seoul로 변환

---

## 목차

1. [공통 규칙](#공통-규칙)
2. [사용자 관리](#1-users-사용자)
3. [계좌 관리](#2-accounts-계좌)
4. [태그 시스템](#3-태그-시스템)
5. [알림 시스템](#4-알림-시스템)
6. [활동 시스템](#5-활동-시스템-댓글로그)
7. [자산 관리](#6-assets-자산)
8. [거래 관리](#7-transactions-자산-거래)
9. [카테고리 시스템](#8-카테고리-시스템)
10. [Enum 정의](#enum-타입-정의)
11. [성능 최적화](#성능-최적화)
12. [비즈니스 규칙](#비즈니스-규칙)

---

## 공통 규칙

### 모든 테이블의 기본 필드

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

### 데이터 타입 규칙

#### 금액 필드
- **타입**: `NUMERIC(15, 2)` (최대 999조 9,999억 9,999만 9,999원.99센트)
- **이유**: FLOAT/DOUBLE 사용 시 부동소수점 오차 발생 방지
- **예시**: `balance NUMERIC(15, 2) NOT NULL DEFAULT 0`

#### 수량 필드
- **타입**: `NUMERIC(20, 8)` (소수점 8자리까지 지원, 가상화폐 등)
- **예시**: `quantity NUMERIC(20, 8) NOT NULL`

### 외래키 규칙

- **CASCADE 삭제**: 부모 레코드 삭제 시 자식도 함께 삭제
- **SET NULL**: 참조 대상 삭제 시 NULL로 설정 (선택적 관계)
- **예시**: `user_id UUID REFERENCES users(id) ON DELETE CASCADE`

### 인덱스 규칙

- 외래키 컬럼은 기본적으로 인덱스 생성
- 검색/필터링/정렬이 빈번한 컬럼에 인덱스 추가
- 복합 인덱스는 쿼리 패턴에 따라 설정 (선행 컬럼 순서 중요)
- 조건부 인덱스(Partial Index)로 성능 최적화

---

## 핵심 테이블

### 1. users (사용자)

사용자 인증 및 기본 설정 정보를 관리합니다.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    
    
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
```

**필드 설명**:
- `hashed_password`: bcrypt로 해싱된 비밀번호
- `is_active`: 계정 활성화 상태 (소프트 삭제 용도)
- `is_superuser`: 관리자 권한 플래그

**비즈니스 규칙**:
- 이메일과 사용자명은 유니크해야 함
- 비밀번호는 최소 8자 이상 (애플리케이션 레벨 검증)

---

### 2. accounts (계좌)

사용자의 금융 계좌 정보를 관리합니다.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    
    
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

**설명**:
- 기본 인증 사용자 테이블
- `hashed_password`: bcrypt로 해싱된 비밀번호
- `is_active`: 계정 활성화 상태 (소프트 삭제 가능)
- `is_superuser`: 관리자 권한 플래그

**비즈니스 규칙**:
- 이메일과 사용자명은 유니크해야 함
- 비밀번호는 최소 8자 이상 (애플리케이션 레벨 검증)

### 2. accounts (계좌)

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 계좌 기본 정보
    name VARCHAR(100) NOT NULL,         -- 사용자 지정 이름 (예: "주 거래 계좌")
  account_type VARCHAR(50) NOT NULL,  -- AccountType Enum 값
  provider VARCHAR(100),              -- 은행/증권사/거래소 이름
  currency VARCHAR(3) NOT NULL DEFAULT 'KRW',  -- 통화 코드(ISO 4217, 3자리, 기본 KRW)
    account_number VARCHAR(100),        -- 계좌번호 (마스킹 또는 암호화)
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    
    -- API 연동 설정 (선택)
    api_config JSONB,                   -- API 인증에 필요한 설정
    daemon_config JSONB,                -- Daemon 프로세스 동작 설정
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_accounts_owner ON accounts(owner_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_provider ON accounts(provider);
```

---

### 2. accounts (계좌)

사용자의 금융 계좌 정보를 관리합니다.

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 계좌 기본 정보
    name VARCHAR(100) NOT NULL,         -- 사용자 지정 이름 (예: "주 거래 계좌")
  account_type VARCHAR(50) NOT NULL,  -- AccountType Enum 값
  provider VARCHAR(100),              -- 은행/증권사/거래소 이름
  currency VARCHAR(3) NOT NULL DEFAULT 'KRW',  -- 통화 코드(ISO 4217, 3자리, 기본 KRW)
    account_number VARCHAR(100),        -- 계좌번호 (마스킹 또는 암호화)
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    
    -- API 연동 설정 (선택)
    api_config JSONB,                   -- API 인증에 필요한 설정
    daemon_config JSONB,                -- Daemon 프로세스 동작 설정
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_accounts_owner ON accounts(owner_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_provider ON accounts(provider);
CREATE INDEX idx_accounts_is_active ON accounts(is_active);
```

**필드 설명**:
- `owner_id`: 계좌의 원 소유자 (계좌 생성자)
- `account_type`: AccountType Enum 값 (bank_account, securities 등)
- `provider`: 금융기관/거래소 식별자
- `currency`: 통화 코드(ISO 4217, 3자리, 기본 KRW)
- `api_config`: API 인증 정보 (키/토큰 등)
- `daemon_config`: 자동화 설정 (동기화 주기, 알림 설정 등)

**계좌 공유 기능**:
- 계좌는 여러 사용자와 공유 가능 (Many-to-Many)
- 소유자는 모든 권한 보유
- 공유받은 사용자는 권한에 따라 접근 제한
- 공유 관계는 `account_shares` 테이블에서 관리 (아래 참조)

#### API 설정 예시

**api_config 구조**:
```json
{
  "provider": "koreainvestment",
  "app_key": "encrypted_PSxxxxxxxx",
  "app_secret": "encrypted_xxxxxxxx",
  "account_number": "12345678-01",
  "endpoint": "https://openapi.koreainvestment.com:9443",
  "encrypted": true
}
```

**daemon_config 구조**:
```json
{
  "enabled": true,
  "sync_interval": 300,
  "sync_enabled": true,
  "auto_trading": false,
  "notifications": {
    "telegram": {
      "enabled": true,
      "bot_token": "encrypted_1234567890:ABCdefGHI...",
      "chat_id": "encrypted_123456789",
      "notify_on_trade": true,
      "notify_on_error": true,
      "notify_on_sync": false
    }
  }
}
```

**설정 필드 분리 이유**:
- ✅ **관심사 분리**: API 인증(api_config) vs Daemon 동작(daemon_config)
- ✅ **보안**: API 키와 알림 설정을 별도로 암호화 가능
- ✅ **유연성**: Daemon 설정만 수정 시 API 설정 영향 없음
- ✅ **확장성**: 각 설정을 독립적으로 확장 가능

**보안 고려사항**:
- ⚠️ **민감 정보 암호화 필수**:
  - `api_config`: app_key, app_secret, account_number
  - `daemon_config`: bot_token, chat_id
- 암호화 키는 환경변수 또는 Key Management Service(KMS) 사용
- API 키/토큰은 읽기 시에만 복호화, 로그에 절대 출력 금지
- `encrypted` 플래그로 암호화 여부 표시 권장

---

### 2-1. account_shares (계좌 공유)

계좌 공유 관계 및 권한을 관리합니다.

```sql
CREATE TABLE account_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 역할 및 권한
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- 'owner', 'editor', 'viewer'
    can_read BOOLEAN DEFAULT TRUE,
    can_write BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_share BOOLEAN DEFAULT FALSE,
    
    -- 공유 메타데이터
    shared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    shared_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_account_user_share UNIQUE(account_id, user_id),
    CONSTRAINT check_role CHECK (role IN ('owner', 'editor', 'viewer'))
);

CREATE INDEX idx_account_shares_user ON account_shares(user_id);
CREATE INDEX idx_account_shares_account ON account_shares(account_id);
CREATE INDEX idx_account_shares_role ON account_shares(role);
```

---

### 2-1. account_shares (계좌 공유)

계좌 공유 관계 및 권한을 관리합니다.

```sql
CREATE TABLE account_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 역할 및 권한
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- 'owner', 'editor', 'viewer'
    can_read BOOLEAN DEFAULT TRUE,
    can_write BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_share BOOLEAN DEFAULT FALSE,
    
    -- 공유 메타데이터
    shared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    shared_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_account_user_share UNIQUE(account_id, user_id),
    CONSTRAINT check_role CHECK (role IN ('owner', 'editor', 'viewer'))
);

CREATE INDEX idx_account_shares_user ON account_shares(user_id);
CREATE INDEX idx_account_shares_account ON account_shares(account_id);
CREATE INDEX idx_account_shares_role ON account_shares(role);
```

**필드 설명**:
- `role`: 미리 정의된 역할 (owner/editor/viewer)
- `can_*`: 세부 권한 플래그 (역할별 기본값 설정)
- `shared_by`: 공유를 수행한 사용자 (추적용)

**역할별 기본 권한**:
- **owner**: 모든 권한 (`can_read`, `can_write`, `can_delete`, `can_share` 모두 true)
  - 계좌 소유자는 자동으로 owner 역할 부여
  - 계좌당 여러 명의 owner 가능 (공동 소유)
- **editor**: 읽기/쓰기 가능 (`can_read`, `can_write` = true)
  - 거래 추가/수정 가능
  - 계좌 삭제 및 공유 불가
- **viewer**: 읽기 전용 (`can_read` = true)
  - 계좌 및 거래 조회만 가능
  - 어떠한 수정도 불가

**비즈니스 규칙**:
- 계좌 소유자(`owner_id`)는 자동으로 'owner' 역할로 `account_shares`에 등록
- 한 사용자가 동일 계좌에 중복 공유 불가 (`UNIQUE` 제약)
- 계좌 삭제 시 모든 공유 관계도 함께 삭제 (`CASCADE`)
- 공유한 사용자 삭제 시 `shared_by`는 NULL로 설정 (`SET NULL`)
- owner 역할만 다른 사용자와 계좌 공유 가능 (`can_share = true`)

**사용 예시**:
```sql
-- 가족 구성원에게 계좌 공유 (편집 권한)
INSERT INTO account_shares (account_id, user_id, role, can_read, can_write, shared_by)
VALUES ('account-uuid', 'spouse-uuid', 'editor', true, true, 'owner-uuid');

-- 회계사에게 읽기 전용 공유
INSERT INTO account_shares (account_id, user_id, role, can_read, shared_by)
VALUES ('account-uuid', 'accountant-uuid', 'viewer', true, 'owner-uuid');

-- 사용자가 접근 가능한 모든 계좌 조회
SELECT DISTINCT a.*
FROM accounts a
INNER JOIN account_shares s ON a.id = s.account_id
WHERE s.user_id = 'user-uuid' AND s.can_read = true;
```

---

### 3. 태그 시스템

자산, 계좌, 거래에 태그를 붙여 분류/검색/필터링할 수 있는 통합 태그 시스템입니다.

#### 3-1. tags (태그 정의)

```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 태그 정보
    name VARCHAR(50) NOT NULL,           -- 태그명 (예: "투자", "장기보유", "긴급")
    color VARCHAR(7),                    -- 색상 코드 (예: #FF5733)
    description TEXT,                    -- 태그 설명
    
    -- 엔티티 타입 제약 (옵션)
    allowed_types JSONB DEFAULT '["asset", "account", "transaction"]',  -- 사용 가능한 엔티티
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_tag_per_user UNIQUE(user_id, name)
);

CREATE INDEX idx_tags_user ON tags(user_id);
CREATE INDEX idx_tags_name ON tags(user_id, name);
```

**필드 설명**:
- `name`: 태그 이름 (사용자별 고유)
- `color`: UI 표시용 색상 코드 (Hex 형식)
- `allowed_types`: 특정 엔티티에만 사용 제한 가능 (선택적)

#### 3-2. taggables (태그 연결 - Polymorphic)

```sql
CREATE TABLE taggables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    
    -- Polymorphic 연결
    taggable_type VARCHAR(20) NOT NULL,  -- 'asset', 'account', 'transaction'
    taggable_id UUID NOT NULL,           -- 해당 엔티티의 ID
    
    -- 메타데이터
    tagged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tagged_by UUID REFERENCES users(id) ON DELETE SET NULL,  -- 태그를 붙인 사용자
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_tag_entity UNIQUE(tag_id, taggable_type, taggable_id),
    CONSTRAINT check_taggable_type CHECK (
        taggable_type IN ('asset', 'account', 'transaction')
    )
);

CREATE INDEX idx_taggables_tag ON taggables(tag_id);
CREATE INDEX idx_taggables_entity ON taggables(taggable_type, taggable_id);
CREATE INDEX idx_taggables_type_tag ON taggables(taggable_type, tag_id);
```

**필드 설명**:
- `taggable_type`: 어떤 엔티티에 태그가 붙었는지 (asset/account/transaction)
- `taggable_id`: 해당 엔티티의 UUID
- `tagged_by`: 태그를 붙인 사용자 (추적용)

**비즈니스 규칙**:
- 동일 태그를 동일 엔티티에 중복 적용 불가 (`UNIQUE` 제약)
- 태그 삭제 시 모든 연결 관계도 함께 삭제 (`CASCADE`)
- 엔티티 삭제 시 taggables 레코드도 삭제 (애플리케이션 레벨 처리)

**주의사항**:
- ⚠️ **참조 무결성**: `taggable_id`는 FK 제약이 없으므로 애플리케이션에서 검증 필수
- ⚠️ **엔티티 존재 확인**: 태그 추가 전 엔티티 존재 여부 검증
- ⚠️ **타입 제약**: `allowed_types` 검증 로직 구현 권장

#### 태그 시스템 사용 예시

```sql
-- 1) 태그 생성
INSERT INTO tags (user_id, name, color)
VALUES ('user-uuid', '투자', '#3B82F6');

-- 2) 자산 전용 태그
INSERT INTO tags (user_id, name, color, allowed_types)
VALUES ('user-uuid', '배당주', '#10B981', '["asset"]');

-- 3) 자산에 태그 추가
INSERT INTO taggables (tag_id, taggable_type, taggable_id, tagged_by)
VALUES ('tag-uuid', 'asset', 'asset-uuid', 'user-uuid');

-- 4) 특정 태그가 붙은 모든 자산 조회
SELECT a.*
FROM assets a
JOIN taggables t ON t.taggable_id = a.id AND t.taggable_type = 'asset'
JOIN tags tg ON t.tag_id = tg.id
WHERE tg.name = '투자' AND tg.user_id = 'user-uuid';

-- 5) 태그별 엔티티 개수 통계
SELECT 
    tg.name,
    tg.color,
    COUNT(CASE WHEN t.taggable_type = 'asset' THEN 1 END) as asset_count,
    COUNT(CASE WHEN t.taggable_type = 'account' THEN 1 END) as account_count,
    COUNT(CASE WHEN t.taggable_type = 'transaction' THEN 1 END) as transaction_count,
    COUNT(*) as total_count
FROM tags tg
LEFT JOIN taggables t ON tg.id = t.tag_id
WHERE tg.user_id = 'user-uuid'
GROUP BY tg.id, tg.name, tg.color
ORDER BY total_count DESC;

-- 6) 여러 태그가 모두 붙은 자산 검색 (AND 조건)
SELECT a.id, a.name
FROM assets a
WHERE a.user_id = 'user-uuid'
  AND EXISTS (
    SELECT 1 FROM taggables t1
    JOIN tags tg1 ON t1.tag_id = tg1.id
    WHERE t1.taggable_id = a.id 
      AND t1.taggable_type = 'asset'
      AND tg1.name = '투자'
  )
  AND EXISTS (
    SELECT 1 FROM taggables t2
    JOIN tags tg2 ON t2.tag_id = tg2.id
    WHERE t2.taggable_id = a.id 
      AND t2.taggable_type = 'asset'
      AND tg2.name = '장기보유'
  );

-- 7) 태그가 없는 자산 조회
SELECT a.*
FROM assets a
WHERE a.user_id = 'user-uuid'
  AND NOT EXISTS (
    SELECT 1 FROM taggables t
    WHERE t.taggable_id = a.id AND t.taggable_type = 'asset'
  );
```

**확장 가능성**:
- 태그 계층 구조: `tags` 테이블에 `parent_id` 추가
- 자동 태그: 조건에 따라 자동으로 태그 적용하는 규칙 테이블
- 태그 그룹: 관련 태그를 그룹화하는 기능
- 태그 공유: 계좌 공유와 유사하게 태그 공유 기능

---

### 4. 알림 시스템

자산, 계좌, 거래에 대한 검토 알림, 일정 알림 등을 관리하는 Polymorphic 알림 시스템입니다.

#### 4-1. reminders (알림)

```sql
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Polymorphic 연결
    remindable_type VARCHAR(20) NOT NULL,  -- 'asset', 'account', 'transaction'
    remindable_id UUID NOT NULL,           -- 해당 엔티티의 ID
    
    -- 알림 유형 및 내용
    reminder_type VARCHAR(20) NOT NULL DEFAULT 'review' CHECK (
        reminder_type IN ('review', 'dividend', 'rebalance', 'deadline', 'custom')
    ),
    title VARCHAR(100) NOT NULL,           -- 알림 제목
    description TEXT,                      -- 알림 상세 설명
    
    -- 시간 설정
    remind_at TIMESTAMP WITH TIME ZONE NOT NULL,           -- 알림 시각
    repeat_interval VARCHAR(20),           -- 'daily', 'weekly', 'monthly', 'yearly', null
    
    -- 우선순위
    priority INT DEFAULT 0,                -- 높을수록 우선 (0=보통, 1=중요, 2=긴급)
    
    -- 상태 관리
    is_active BOOLEAN DEFAULT TRUE,        -- 활성화 여부
    is_dismissed BOOLEAN DEFAULT FALSE,    -- 무시됨 여부
    dismissed_at TIMESTAMP WITH TIME ZONE, -- 무시한 시각
    snoozed_until TIMESTAMP WITH TIME ZONE, -- 스누즈 종료 시각
    last_notified_at TIMESTAMP WITH TIME ZONE, -- 마지막 알림 발송 시각
    
    -- 자동 완료 설정
    auto_complete_on_view BOOLEAN DEFAULT FALSE, -- 조회 시 자동 완료
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT check_remindable_type CHECK (
        remindable_type IN ('asset', 'account', 'transaction')
    ),
    CONSTRAINT check_repeat_interval CHECK (
        repeat_interval IS NULL OR 
        repeat_interval IN ('daily', 'weekly', 'monthly', 'yearly')
    )
);

CREATE INDEX idx_reminders_user ON reminders(user_id);
CREATE INDEX idx_reminders_entity ON reminders(remindable_type, remindable_id);
CREATE INDEX idx_reminders_due ON reminders(remind_at) 
    WHERE is_active = true AND is_dismissed = false AND (snoozed_until IS NULL OR snoozed_until < NOW());
CREATE INDEX idx_reminders_user_type ON reminders(user_id, reminder_type);
CREATE INDEX idx_reminders_priority ON reminders(user_id, priority DESC, remind_at);
```

**필드 설명**:
- `remindable_type`: 알림 대상 엔티티 타입 (asset/account/transaction)
- `remindable_id`: 해당 엔티티의 UUID
- `reminder_type`: 알림 종류 (review/dividend/rebalance/deadline/custom)
- `repeat_interval`: 반복 주기 (daily/weekly/monthly/yearly/null)
- `priority`: 0=보통, 1=중요, 2=긴급

**알림 유형**:
- **review**: 자산/계좌 정기 검토
- **dividend**: 배당락일, 배당 지급일 알림
- **rebalance**: 포트폴리오 리밸런싱 시기
- **deadline**: 만기일, 결산일 등
- **custom**: 사용자 정의 알림

**비즈니스 규칙**:
- 사용자별 독립적인 알림 관리
- 한 엔티티에 여러 알림 설정 가능
- 스누즈 중인 알림은 `snoozed_until` 시각까지 발송 중단
- 엔티티 삭제 시 관련 알림도 삭제 (애플리케이션 레벨 처리)

**주의사항**:
- ⚠️ **참조 무결성**: `remindable_id`는 FK 제약이 없으므로 애플리케이션에서 검증 필수
- ⚠️ **엔티티 존재 확인**: 알림 생성 전 엔티티 존재 여부 검증
- ⚠️ **권한 확인**: 공유 계좌의 경우 알림 생성/조회 권한 검증 필요

#### 알림 시스템 사용 예시

```sql
-- 1) 자산 검토 알림 생성 (1개월 후)
INSERT INTO reminders (user_id, remindable_type, remindable_id, reminder_type, title, remind_at)
VALUES ('user-uuid', 'asset', 'asset-uuid', 'review', '삼성전자 투자 검토', NOW() + INTERVAL '1 month');

-- 2) 반복 알림 (매월 1일 포트폴리오 리밸런싱)
INSERT INTO reminders (user_id, remindable_type, remindable_id, reminder_type, title, remind_at, repeat_interval, priority)
VALUES ('user-uuid', 'account', 'account-uuid', 'rebalance', '월간 포트폴리오 리밸런싱', '2025-12-01 09:00:00+00', 'monthly', 1);

-- 3) 사용자의 모든 대기 중 알림 조회
SELECT r.*, 
    CASE 
        WHEN r.remindable_type = 'asset' THEN a.name
        WHEN r.remindable_type = 'account' THEN acc.name
        ELSE NULL
    END as entity_name
FROM reminders r
LEFT JOIN assets a ON r.remindable_type = 'asset' AND r.remindable_id = a.id
LEFT JOIN accounts acc ON r.remindable_type = 'account' AND r.remindable_id = acc.id
WHERE r.user_id = 'user-uuid'
  AND r.is_active = true
  AND r.is_dismissed = false
  AND (r.snoozed_until IS NULL OR r.snoozed_until <= NOW())
  AND r.remind_at <= NOW() + INTERVAL '7 days'
ORDER BY r.priority DESC, r.remind_at;

-- 4) 알림 무시 처리
UPDATE reminders
SET is_dismissed = true, dismissed_at = NOW()
WHERE id = 'reminder-uuid' AND user_id = 'user-uuid';

-- 5) 알림 스누즈 (1시간 후)
UPDATE reminders
SET snoozed_until = NOW() + INTERVAL '1 hour'
WHERE id = 'reminder-uuid' AND user_id = 'user-uuid';

-- 6) 오늘 발송할 알림 목록 (배치 작업용)
SELECT r.id, r.user_id, r.remindable_type, r.remindable_id, r.title, r.priority
FROM reminders r
WHERE r.is_active = true
  AND r.is_dismissed = false
  AND (r.snoozed_until IS NULL OR r.snoozed_until <= NOW())
  AND r.remind_at <= NOW()
  AND (r.last_notified_at IS NULL OR r.last_notified_at < r.remind_at)
ORDER BY r.priority DESC, r.remind_at
LIMIT 1000;
```

**확장 가능성**:
- 알림 템플릿: 자주 사용하는 알림 패턴을 템플릿으로 저장
- 알림 채널: 이메일, 푸시, SMS, 텔레그램 등 발송 채널 설정
- 알림 그룹: 여러 알림을 그룹화하여 일괄 관리
- 스마트 알림: AI 기반 최적 알림 시간 추천
- 알림 히스토리: 발송된 알림 이력 추적 테이블 분리

---

### 5. 활동 시스템 (댓글+로그)

자산/계좌/거래에 대한 사용자 댓글과 시스템 감사 로그를 통합 관리하는 Polymorphic 시스템입니다.

#### 5-1. activities (활동)
CREATE TABLE activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- 작성자(행위자)

  -- Polymorphic 연결 대상
  target_type VARCHAR(20) NOT NULL,   -- 'asset', 'account', 'transaction'
  target_id UUID NOT NULL,            -- 대상 엔티티의 ID

  -- 활동 유형 및 내용
  activity_type VARCHAR(20) NOT NULL CHECK (
    activity_type IN ('comment', 'log')
  ),
  content TEXT,                       -- 댓글 본문 (comment 전용)
  payload JSONB,                      -- 구조화된 로그 데이터 (log 전용)

  -- 스레드(댓글 쓰레딩)
  parent_id UUID REFERENCES activities(id) ON DELETE CASCADE,   -- 부모 댓글
  thread_root_id UUID REFERENCES activities(id) ON DELETE CASCADE, -- 스레드 루트

  -- 표시/보존 정책
  visibility VARCHAR(20) NOT NULL DEFAULT 'private' CHECK (
    visibility IN ('private', 'shared', 'public')
  ),
  is_immutable BOOLEAN NOT NULL DEFAULT FALSE, -- 로그는 TRUE, 댓글은 FALSE
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,   -- 소프트 삭제(댓글용)
  deleted_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  CONSTRAINT check_target_type CHECK (
    target_type IN ('asset', 'account', 'transaction')
  )
);

-- 조회 최적화 인덱스
CREATE INDEX idx_activities_target ON activities(target_type, target_id, created_at DESC);
CREATE INDEX idx_activities_user ON activities(user_id, created_at DESC);
CREATE INDEX idx_activities_thread ON activities(thread_root_id, created_at);
CREATE INDEX idx_activities_parent ON activities(parent_id);
CREATE INDEX idx_activities_active ON activities(target_type, target_id)
  WHERE is_deleted = false;

-- 선택: payload 검색 최적화 (pg_trgm/jsonb_path_ops 등)
-- CREATE INDEX idx_activities_payload_gin ON activities USING GIN (payload);
```

**설명**:
- 단일 테이블에서 댓글(`comment`)과 로그(`log`)를 함께 보관
- 댓글은 `content`를, 로그는 `payload`(JSONB)로 구조화 데이터 저장 권장
- 대상 엔티티는 Polymorphic(`target_type`, `target_id`)로 연결
- 댓글 쓰레딩: `parent_id`로 계층 구조, `thread_root_id`로 같은 스레드 묶음
- 로그 불변성: 생성 후 수정/삭제 불가(`is_immutable = true`), 댓글은 정책 내 수정 허용

**비즈니스 규칙**:
- 대상 엔티티 존재/권한은 애플리케이션에서 검증 필수
  - asset: 본인 소유 또는 연결 계좌 공유 범위 내
  - account: 소유자 또는 `account_shares`를 통한 접근 권한 보유자
  - transaction: 상위 자산 접근 권한 보유 시 가능
- 댓글 수정/삭제 정책(권장): 작성자 본인만, 생성 후 N분 이내 수정 허용; 삭제는 소프트 삭제만 허용(`is_deleted=true`)
- 로그는 불변(Immutable)으로, 생성 이후 Update/Delete 금지. 숨김은 클라이언트 필터로 처리

#### 불변성(Immutable) 트리거 (권장)

```sql
-- 로그 레코드에 대해 UPDATE/DELETE를 차단하는 트리거
CREATE OR REPLACE FUNCTION trg_block_mutation_on_immutable()
RETURNS trigger AS $$
BEGIN
  IF OLD.is_immutable THEN
    RAISE EXCEPTION 'Immutable activity cannot be %', TG_OP;
  END IF;
  IF TG_OP = 'UPDATE' THEN
    RETURN NEW;
  ELSE
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER activities_prevent_update
BEFORE UPDATE ON activities
FOR EACH ROW
WHEN (OLD.is_immutable)
EXECUTE FUNCTION trg_block_mutation_on_immutable();

CREATE TRIGGER activities_prevent_delete
BEFORE DELETE ON activities
FOR EACH ROW
WHEN (OLD.is_immutable)
EXECUTE FUNCTION trg_block_mutation_on_immutable();
```

#### 스레드 루트 자동 설정 트리거 (권장)

```sql
-- parent_id가 없으면 본인이 루트, 있으면 부모의 thread_root_id를 상속
CREATE OR REPLACE FUNCTION trg_set_thread_root()
RETURNS trigger AS $$
DECLARE
  root_id UUID;
BEGIN
  IF NEW.parent_id IS NULL THEN
    NEW.thread_root_id := NEW.id; -- INSERT 후 UPDATE로 보정하거나, DB에서 DEFAULT NULL 허용 후 별도 UPDATE 수행
  ELSE
    SELECT COALESCE(a.thread_root_id, a.id) INTO root_id
    FROM activities a WHERE a.id = NEW.parent_id;
    NEW.thread_root_id := root_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER activities_set_thread_root
BEFORE INSERT ON activities
FOR EACH ROW
EXECUTE FUNCTION trg_set_thread_root();
```

주의: 일부 DB에서는 INSERT 시점에 `NEW.id` 접근 시 DEFAULT가 아직 배정되지 않을 수 있습니다. 위 방식이 어려우면 INSERT 후 `thread_root_id`를 애플리케이션에서 업데이트하는 방식을 사용하세요.

**사용 예시**:

```sql
-- 1) 자산에 댓글 작성
INSERT INTO activities (user_id, target_type, target_id, activity_type, content)
VALUES ('user-uuid', 'asset', 'asset-uuid', 'comment', '이번 분기 실적 확인 예정');

-- 2) 댓글에 대한 답글
INSERT INTO activities (user_id, target_type, target_id, activity_type, content, parent_id)
VALUES ('user-uuid', 'asset', 'asset-uuid', 'comment', '자료 링크 공유 부탁드립니다', 'parent-activity-uuid');

-- 3) 거래에 대한 시스템 로그(불변)
INSERT INTO activities (user_id, target_type, target_id, activity_type, payload, is_immutable)
VALUES (
  'system-user-uuid', 'transaction', 'txn-uuid', 'log',
  '{"event":"reconciled","by":"daemon","diff":0.00}', true
);

-- 4) 댓글 소프트 삭제
UPDATE activities
SET is_deleted = true, deleted_at = NOW()
WHERE id = 'activity-uuid' AND activity_type = 'comment' AND user_id = 'user-uuid';

-- 5) 특정 자산의 댓글 스레드 조회 (루트 댓글 + 답글)
SELECT *
FROM activities
WHERE target_type = 'asset' AND target_id = 'asset-uuid'
  AND activity_type = 'comment'
  AND is_deleted = false
```sql
CREATE TABLE activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- 작성자(행위자)

  -- Polymorphic 연결 대상
  target_type VARCHAR(20) NOT NULL,   -- 'asset', 'account', 'transaction'
  target_id UUID NOT NULL,            -- 대상 엔티티의 ID

  -- 활동 유형 및 내용
  activity_type VARCHAR(20) NOT NULL CHECK (
    activity_type IN ('comment', 'log')
  ),
  content TEXT,                       -- 댓글 본문 (comment 전용)
  payload JSONB,                      -- 구조화된 로그 데이터 (log 전용)

  -- 스레드(댓글 쓰레딩)
  parent_id UUID REFERENCES activities(id) ON DELETE CASCADE,   -- 부모 댓글
  thread_root_id UUID REFERENCES activities(id) ON DELETE CASCADE, -- 스레드 루트

  -- 표시/보존 정책
  visibility VARCHAR(20) NOT NULL DEFAULT 'private' CHECK (
    visibility IN ('private', 'shared', 'public')
  ),
  is_immutable BOOLEAN NOT NULL DEFAULT FALSE, -- 로그는 TRUE, 댓글은 FALSE
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,   -- 소프트 삭제(댓글용)
  deleted_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  CONSTRAINT check_target_type CHECK (
    target_type IN ('asset', 'account', 'transaction')
  )
);

-- 조회 최적화 인덱스
CREATE INDEX idx_activities_target ON activities(target_type, target_id, created_at DESC);
CREATE INDEX idx_activities_user ON activities(user_id, created_at DESC);
CREATE INDEX idx_activities_thread ON activities(thread_root_id, created_at);
CREATE INDEX idx_activities_parent ON activities(parent_id);
CREATE INDEX idx_activities_active ON activities(target_type, target_id)
  WHERE is_deleted = false;
```

**필드 설명**:
- `target_type`, `target_id`: Polymorphic 연결 (asset/account/transaction)
- `activity_type`: 댓글(`comment`) 또는 로그(`log`)
- `content`: 댓글 본문 (댓글 전용)
- `payload`: 구조화된 로그 데이터 (로그 전용, JSONB)
- `parent_id`, `thread_root_id`: 댓글 쓰레딩 지원
- `is_immutable`: 로그는 true (수정/삭제 불가), 댓글은 false

**비즈니스 규칙**:
- 댓글은 수정/삭제 가능 (작성자 본인만, 생성 후 일정 시간 내)
- 로그는 불변(Immutable), 생성 후 수정/삭제 금지
- 대상 엔티티 존재 및 접근 권한은 애플리케이션에서 검증
- 소프트 삭제만 허용 (`is_deleted = true`)

#### 5-2. 불변성 트리거 (로그 보호)

```sql
-- 로그 레코드에 대해 UPDATE/DELETE를 차단하는 트리거
CREATE OR REPLACE FUNCTION trg_block_mutation_on_immutable()
RETURNS trigger AS $$
BEGIN
  IF OLD.is_immutable THEN
    RAISE EXCEPTION 'Immutable activity cannot be %', TG_OP;
  END IF;
  IF TG_OP = 'UPDATE' THEN
    RETURN NEW;
  ELSE
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER activities_prevent_update
BEFORE UPDATE ON activities
FOR EACH ROW
WHEN (OLD.is_immutable)
EXECUTE FUNCTION trg_block_mutation_on_immutable();

CREATE TRIGGER activities_prevent_delete
BEFORE DELETE ON activities
FOR EACH ROW
WHEN (OLD.is_immutable)
EXECUTE FUNCTION trg_block_mutation_on_immutable();
```

#### 5-3. 스레드 루트 자동 설정 트리거

```sql
-- parent_id가 없으면 본인이 루트, 있으면 부모의 thread_root_id를 상속
CREATE OR REPLACE FUNCTION trg_set_thread_root()
RETURNS trigger AS $$
DECLARE
  root_id UUID;
BEGIN
  IF NEW.parent_id IS NULL THEN
    NEW.thread_root_id := NEW.id;
  ELSE
    SELECT COALESCE(a.thread_root_id, a.id) INTO root_id
    FROM activities a WHERE a.id = NEW.parent_id;
    NEW.thread_root_id := root_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER activities_set_thread_root
BEFORE INSERT ON activities
FOR EACH ROW
EXECUTE FUNCTION trg_set_thread_root();
```

**주의**: 일부 DB에서는 INSERT 시점에 `NEW.id` 접근 시 DEFAULT가 아직 배정되지 않을 수 있습니다. 위 방식이 어려우면 INSERT 후 `thread_root_id`를 애플리케이션에서 업데이트하는 방식을 사용하세요.

#### 활동 시스템 사용 예시

```sql
-- 1) 자산에 댓글 작성
INSERT INTO activities (user_id, target_type, target_id, activity_type, content)
VALUES ('user-uuid', 'asset', 'asset-uuid', 'comment', '이번 분기 실적 확인 예정');

-- 2) 댓글에 대한 답글
INSERT INTO activities (user_id, target_type, target_id, activity_type, content, parent_id)
VALUES ('user-uuid', 'asset', 'asset-uuid', 'comment', '자료 링크 공유 부탁드립니다', 'parent-activity-uuid');

-- 3) 거래에 대한 시스템 로그(불변)
INSERT INTO activities (user_id, target_type, target_id, activity_type, payload, is_immutable)
VALUES (
  'system-user-uuid', 'transaction', 'txn-uuid', 'log',
  '{"event":"reconciled","by":"daemon","diff":0.00}', true
);

-- 4) 댓글 소프트 삭제
UPDATE activities
SET is_deleted = true, deleted_at = NOW()
WHERE id = 'activity-uuid' AND activity_type = 'comment' AND user_id = 'user-uuid';

-- 5) 특정 자산의 댓글 스레드 조회 (루트 댓글 + 답글)
SELECT *
FROM activities
WHERE target_type = 'asset' AND target_id = 'asset-uuid'
  AND activity_type = 'comment'
  AND is_deleted = false
ORDER BY thread_root_id, created_at;
```

**확장 가능성**:
- 리액션(좋아요/이모지) 테이블 `activity_reactions` 추가
- 멘션(@user) 및 구독자 알림 연동
- 파일 첨부(별도 `attachments` 테이블) 및 미디어 썸네일
- 시스템 이벤트 카테고리화(`payload.event` 표준화, 인덱싱)
- Moderation 기능(스팸/욕설 필터, 신고/숨김)

---

### 6. assets (자산)

사용자의 금융 자산 정보를 관리합니다.

```sql
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    
    -- 자산 기본 정보
    name VARCHAR(100) NOT NULL,         -- 사용자 지정 이름 (예: "삼성전자", "비트코인")
    asset_type VARCHAR(50) NOT NULL,    -- AssetType Enum 값
    symbol VARCHAR(20),                 -- 거래 심볼 (예: "005930", "BTC")
    
    -- 메타데이터
    currency VARCHAR(3) DEFAULT 'KRW',  -- 기준 통화
    metadata JSONB,                     -- 추가 정보 (ISIN, 상장국가 등)
    
    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_assets_user ON assets(user_id);
CREATE INDEX idx_assets_account ON assets(account_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_symbol ON assets(symbol);
CREATE INDEX idx_assets_is_active ON assets(is_active);
```

**필드 설명**:
- `user_id`: 자산 소유자
- `account_id`: 자산이 속한 계좌
- `asset_type`: AssetType Enum 값 (stock, crypto, bond 등)
- `symbol`: 외부 API 연동용 식별자 (티커, 코드 등)
- `metadata`: 확장 가능한 추가 정보 (ISIN, 상장국가 등)

**자산 유형별 예시**:
```json
// 현금 자산
{
  "name": "NH투자증권 예수금",
  "asset_type": "cash",
  "symbol": null,
  "currency": "KRW"
}

// 주식 자산
{
  "name": "삼성전자",
  "asset_type": "stock",
  "symbol": "005930",
  "metadata": {"market": "KOSPI", "isin": "KR7005930003"}
}

// 가상화폐
{
  "name": "비트코인",
  "asset_type": "crypto",
  "symbol": "BTC",
  "metadata": {"exchange": "upbit"}
}
```

---

### 7. transactions (자산 거래)

모든 자산 거래 내역을 관리합니다.

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    
    -- 거래 유형
    type VARCHAR(20) NOT NULL,          -- 거래 유형(TransactionType Enum 값)
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,  -- (옵션) 카테고리
    
    -- 자산 수량 변화 (핵심)
    quantity NUMERIC(20, 8) NOT NULL,   -- 양수=증가, 음수=감소
    extras JSONB,                       -- 거래 추가 정보 저장
                                        -- 환전(exchange) : 'rate'(환율), 'fee'(수수료), 'tax'(세금)
                                        -- 매수/매도 : 'price'(가격)
                                        -- 기타 : 'balance_after'(거래 후 잔액)

    -- 거래 정보
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    description TEXT,                   -- 거래 설명
    memo TEXT,                          -- 사용자 메모
    
    -- 연결
    related_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,  -- 쌍 거래 ID
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_transaction_type CHECK (
       type IN ('buy', 'sell', 'deposit', 'withdraw', 'dividend', 'interest', 'fee', 
                'transfer_in', 'transfer_out', 'adjustment', 'invest', 'redeem', 
                'internal_transfer', 'card_payment', 'promotion_deposit', 'auto_transfer', 'remittance', 'exchange')
    )
);

CREATE INDEX idx_transactions_asset ON transactions(asset_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_category ON transactions(category_id);

```

**필드 설명**:
- `type`: 거래 유형 (TransactionType Enum 값, 아래 표 참고)
- `quantity`: 자산 수량 변화 (양수=증가, 음수=감소, 0=마커)
- `extras`: 거래 추가 정보를 담는 JSONB 필드
  - `price`: 거래 단가 (매수/매도 시)
  - `rate`: 환율 (환전 시)
  - `fee`: 수수료
  - `tax`: 세금
  - `balance_after`: 거래 후 잔액
- `related_transaction_id`: 복식부기 연결 (교환 거래 시 쌍)
- `transaction_date`: 거래 발생 일시
- `description`: 거래 설명 (자동 생성 또는 파싱)
- `memo`: 사용자 메모

**거래 유형 설명 (TransactionType Enum)**:

> **수량 부호 규칙**: `quantity`는 거래 유형에 따라 부호가 결정됩니다.  
> - **증가 거래**: 항상 **양수** (예: buy, deposit, dividend)  
> - **감소 거래**: 항상 **음수** (예: sell, withdraw, fee)  
> - **양방향 거래**: 상황에 따라 ± (예: exchange, adjustment)  
> 
> 이 규칙으로 `SUM(quantity)` 집계만으로 잔액을 계산할 수 있으며, 복식부기 차변/대변 개념과 일치합니다.

| Type                | 설명                | quantity 부호 |  예시 |
|---------------------|---------------------|----------|------|
| `buy`               | 매수                | **+** (양수 필수)                  | 주식 매수, 코인 매수 |
| `sell`              | 매도                | **-** (음수 필수)                     | 주식 매도, 코인 매도 |
| `deposit`           | 입금                | **+** (양수 필수)                     | 현금 입금, 증권 입금 |
| `withdraw`          | 출금                | **-** (음수 필수)                     | 현금 출금, 증권 출금 |
| `dividend`          | 배당                | **+** (양수 필수)                     | 현금/주식 배당 |
| `interest`          | 이자                | **+** (양수 필수)                      | 예금 이자, 채권 이자 |
| `fee`               | 수수료              | **-** (음수 필수)                      | 거래 수수료, 송금 수수료 |
| `transfer_in`       | 이체 입금           | **+** (양수 필수)                      | 계좌간 이체 입금 |
| `transfer_out`      | 이체 출금           | **-** (음수 필수)                      | 계좌간 이체 출금 |
| `adjustment`        | 수량 조정           | **±** (양방향)                      | 주식분할, 오류수정 |
| `invest`            | 투자                | **+** (양수 필수)                     | 펀드/ETF 매수 |
| `redeem`            | 해지                | **-** (음수 필수)                   | 펀드/ETF 환매 |
| `internal_transfer` | 내계좌간이체        | **±** (양방향)                  | 내 계좌간 이동 |
| `card_payment`      | 카드결제            | **-** (음수 필수)                    | 체크/신용카드 결제 |
| `promotion_deposit` | 프로모션입금        | **+** (양수 필수)                    | 이벤트 입금 |
| `auto_transfer`     | 자동이체            | **±** (양방향)                     | 정기 자동이체 |
| `remittance`        | 송금                | **-** (음수 필수)                    | 타인 송금 |
| `exchange`          | 환전                | **±** (양방향)                    | KRW↔USD, 통화간 교환 |

**특수 거래 패턴**:
- **현금 배당**: 주식측 마커(quantity=0) + 현금 증가
- **현물 배당**: 주식측 마커(quantity=0) + 수령 자산 증가
- **주식 분할**: 소멸(-) + 생성(+) 또는 순증가분만 기록
- **환전**: 출발 통화 감소(quantity<0) + 도착 통화 증가(quantity>0), `related_transaction_id`로 쌍 연결
  - 예: KRW 현금 -1,300,000 (type=exchange) ↔ USD 현금 +1,000 (type=exchange)
  - 환율 정보는 `extras.rate`에 저장
  - 제약: 동일 계좌(account_id)가 같은 현금 자산 간에만 허용
- **복식부기**: 자산 교환 시 2개 거래 레코드 생성, `related_transaction_id`로 연결

---

### 8. 카테고리 시스템

거래를 의미/용처별로 분류하기 위한 카테고리 시스템입니다.

#### 8-1. categories (카테고리)
- **현물 배당**: 주식측 마커(quantity=0) + 수령 자산 증가
- **주식 분할**: 소멸(-) + 생성(+) 또는 순증가분만 기록

### 카테고리(Category)

가계부/분석 목적의 “거래 구분(식비/교통/주거/…)”은 회계적 사건을 나타내는 `type`과 별도로 관리합니다. 

- `type`은 수량/현금 흐름 규칙과 직결되는 회계 이벤트입니다(입금/출금/매수/매도/이체/조정 등).
- `category`는 사용자의 의미/용처 분류로 리포트·예산·필터링에 사용합니다.

권장 설계는 아래와 같습니다.

1) 카테고리 테이블 추가

```sql
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  name VARCHAR(50) NOT NULL,           -- 카테고리명 (예: 식비, 교통)
  parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,  -- 상위 카테고리 (옵션)
  flow_type VARCHAR(20) NOT NULL CHECK (
    flow_type IN ('expense', 'income', 'transfer', 'investment', 'neutral')
  ),                                    -- 집계 분류(지출/수입/이동/투자/중립)
  is_active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  CONSTRAINT uq_categories_per_user UNIQUE (user_id, name, parent_id)
);

CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_categories_parent ON categories(parent_id);
```

2) 거래에 카테고리 참조 컬럼 추가(선택적)

```sql
ALTER TABLE transactions
  ADD COLUMN category_id UUID REFERENCES categories(id) ON DELETE SET NULL;

-- 조회 최적화 인덱스
CREATE INDEX idx_transactions_category ON transactions(category_id);
```

3) 타입(type) ↔ 카테고리(category) 관계 권장 규칙

실제 구현에서는 거래 타입별로 허용되는 `flow_type` 집합을 아래와 같이 검증합니다 (서버단 로직 적용 완료):

| 거래 타입 | 허용 flow_type | 설명 |
|-----------|----------------|------|
| buy / sell | investment, neutral | 투자 매수/매도는 투자 혹은 중립 (분류 미정) |
| deposit / interest / dividend | income, transfer, neutral | 수입 또는 계좌로 유입되는 이동, 미분류 |
| withdraw / fee | expense, transfer, neutral | 지출/비용 혹은 이동, 미분류 |
| transfer_in / transfer_out | transfer, neutral | 순수 이동 또는 미분류 |
| adjustment | neutral | 조정은 집계 제외 중립만 허용 |
| 기타(INVEST, REDEEM 등 확장 타입) | 모든 flow_type | 현재 제한 없음 (향후 정책 적용 가능) |

검증 실패 시 400 에러(`HTTPException`)가 반환되며 메시지에 허용 가능한 flow_type 목록이 포함됩니다.

4) 업로드/미리보기 반영

- CSV/Excel 업로드 시 `category`(이름) 또는 `category_id` 컬럼을 허용
- 이름 기준 매핑 실패 시 에러로 반환하거나 “기타”로 폴백(프로덕트 정책에 따라 선택)
 - 현재 구현: 잘못된 ID/이름 또는 거래 타입과 호환되지 않는 flow_type 사용 시 해당 행이 실패(`errors` 배열에 누적)하고 전체는 계속 처리

5) 리포팅/집계 기본 규칙

- 예산/소비 리포트에는 `flow_type IN ('expense','income')`만 기본 포함
- `transfer`/`investment`/`neutral`은 기본 제외(필요 시 토글로 포함)
 - 투자(buy/sell)는 `investment`로 표시되어 소비/수입 집계에 영향을 주지 않음
 - 조정(adjustment)은 `neutral`로만 가능하여 집계에서 제외 처리 일관성 유지

이 설계로 회계 규칙은 `type`에 고정하고, 분석/분류는 `category`로 유연하게 확장할 수 있습니다.

#### 자동 분류 규칙 (category_auto_rules)

거래 설명/메모 등 텍스트에 기반해 카테고리를 자동 지정하기 위한 규칙을 별도 테이블로 관리합니다. 규칙은 사용자별로 독립되며, 우선순위와 패턴 유형(정확 일치/부분 포함/정규식)을 지원합니다.

1) 테이블 정의

```sql
CREATE TABLE category_auto_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,

  pattern_type VARCHAR(20) NOT NULL CHECK (
    pattern_type IN ('exact', 'contains', 'regex')
  ),                               -- 매칭 유형: 정확일치/부분포함/정규식
  pattern_text TEXT NOT NULL,       -- 매칭 문자열 또는 정규식 패턴
  priority INT NOT NULL DEFAULT 100, -- 낮을수록 먼저 적용
  is_active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- 동일 사용자 내 동일 패턴 중복 방지
  CONSTRAINT uq_rules_per_user UNIQUE (user_id, pattern_type, pattern_text)
);

CREATE INDEX idx_car_user_category ON category_auto_rules(user_id, category_id);
CREATE INDEX idx_car_active_priority ON category_auto_rules(user_id, is_active, priority);

-- 선택: 부분 문자열 탐색 최적화 (pg_trgm 확장 필요)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE INDEX idx_car_pattern_trgm ON category_auto_rules USING GIN (pattern_text gin_trgm_ops);
```

2) 매칭/적용 규칙 (권장)

- 적용 조건: 클라이언트가 `category_id`를 지정하지 않았고 서버 설정 `AUTO_CATEGORY=true`인 경우 자동 분류 시도
- 전처리: 소문자 변환, 공백 정리, 유니코드 정규화(NFC) 등 기본 normalize 권장
- 매칭 순서:
  1. `priority` 오름차순
  2. 동순위일 때 Specificity: `exact` > `regex` > `contains`
  3. 최종 다수 매칭 시 첫 규칙 적용(또는 최근 사용자 교정 히스토리 반영)
- 안전장치: `regex`는 실행시간/길이 제한, 관리자 권한에만 허용 권장

3) 동작 예시

```text
pattern_type=contains, pattern_text='스타벅스', category=식비/커피, priority=10
pattern_type=regex,    pattern_text='^GS25\\s', category=식비/편의점, priority=20
pattern_type=exact,    pattern_text='국민연금',  category=지출/보험,   priority=5
```

트랜잭션 설명이 "[KB]스타벅스 강남점 승인"이면 contains 규칙이 매칭되어 커피 카테고리 자동 지정.

4) 관리/검증

- 규칙 CRUD UI 제공(미리보기 테스트 포함)
- 비활성화(`is_active=false`)로 임시 중단 가능
- 충돌/과잉 매칭 모니터링: 히트율, 사용자 교정(수동 변경) 로그로 튜닝

5) 향후 확장

- `pattern_type='keyword'`(토큰 교집합 스코어링) 지원
- 다국어 alias(예: Starbucks/스타벅스) 묶음 규칙
- 규칙 히스토리/감사 로그 테이블 분리
- ML 분류기 도입 전 규칙 기반 튜너로 활용

---

## Enum 타입 정의

### TransactionType Enum (거래 유형)

**Backend Python Enum**
```python
from enum import Enum

class TransactionType(str, Enum):
    BUY = "buy"               # 매수
    SELL = "sell"             # 매도
    DEPOSIT = "deposit"       # 입금
    WITHDRAW = "withdraw"     # 출금
    DIVIDEND = "dividend"     # 배당
    INTEREST = "interest"     # 이자
    FEE = "fee"               # 수수료
    TRANSFER_IN = "transfer_in"    # 이체 입금
    TRANSFER_OUT = "transfer_out"  # 이체 출금
    ADJUSTMENT = "adjustment" # 수량 조정
    INVEST = "invest"         # 투자
    REDEEM = "redeem"         # 해지
    INTERNAL_TRANSFER = "internal_transfer"  # 내계좌간이체
    CARD_PAYMENT = "card_payment"  # 카드결제
    PROMOTION_DEPOSIT = "promotion_deposit"  # 프로모션입금
    AUTO_TRANSFER = "auto_transfer"  # 자동이체
    REMITTANCE = "remittance"  # 송금
    EXCHANGE = "exchange"  # 환전
```

**TypeScript Frontend Enum**
```typescript
export enum TransactionType {
  BUY = 'buy',
  SELL = 'sell',
  DEPOSIT = 'deposit',
  WITHDRAW = 'withdraw',
  DIVIDEND = 'dividend',
  INTEREST = 'interest',
  FEE = 'fee',
  TRANSFER_IN = 'transfer_in',
  TRANSFER_OUT = 'transfer_out',
  ADJUSTMENT = 'adjustment',
  INVEST = 'invest',
  REDEEM = 'redeem',
  INTERNAL_TRANSFER = 'internal_transfer',
  CARD_PAYMENT = 'card_payment',
  PROMOTION_DEPOSIT = 'promotion_deposit',
  AUTO_TRANSFER = 'auto_transfer',
  REMITTANCE = 'remittance',
  EXCHANGE = 'exchange',
}
```

---

### AccountType Enum (계좌 유형)

**설계 근거**: 개인 자산관리에서 계좌 유형은 고정적이므로 DB 테이블보다 Enum이 효율적

```python
# Backend Python Enum
from enum import Enum

class AccountType(str, Enum):
    BANK_ACCOUNT = "bank_account"     # 은행계좌
    SECURITIES = "securities"         # 증권계좌  
    CASH = "cash"                     # 현금
    DEBIT_CARD = "debit_card"        # 체크카드
    CREDIT_CARD = "credit_card"      # 신용카드 (부채)
    SAVINGS = "savings"               # 저축예금
    DEPOSIT = "deposit"               # 적금
    CRYPTO_WALLET = "crypto_wallet"   # 가상화폐지갑

# 유형별 속성 매핑
ACCOUNT_TYPE_INFO = {
    AccountType.BANK_ACCOUNT: {"name": "은행계좌", "is_asset": True},
    AccountType.SECURITIES: {"name": "증권계좌", "is_asset": True},
    AccountType.CASH: {"name": "현금", "is_asset": True},
    AccountType.DEBIT_CARD: {"name": "체크카드", "is_asset": True},
    AccountType.CREDIT_CARD: {"name": "신용카드", "is_asset": False},
    AccountType.SAVINGS: {"name": "저축예금", "is_asset": True},
    AccountType.DEPOSIT: {"name": "적금", "is_asset": True},
    AccountType.CRYPTO_WALLET: {"name": "가상화폐지갑", "is_asset": True},
}
```

```typescript
// TypeScript Frontend Enum
export enum AccountType {
  BANK_ACCOUNT = 'bank_account',
  SECURITIES = 'securities',
  CASH = 'cash',
  DEBIT_CARD = 'debit_card',
  CREDIT_CARD = 'credit_card',
  SAVINGS = 'savings',
  DEPOSIT = 'deposit',
  CRYPTO_WALLET = 'crypto_wallet',
}

// 유형별 표시명 매핑
export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  [AccountType.BANK_ACCOUNT]: '은행계좌',
  [AccountType.SECURITIES]: '증권계좌',
  [AccountType.CASH]: '현금',
  [AccountType.DEBIT_CARD]: '체크카드',
  [AccountType.CREDIT_CARD]: '신용카드',
  [AccountType.SAVINGS]: '저축예금',
  [AccountType.DEPOSIT]: '적금',
  [AccountType.CRYPTO_WALLET]: '가상화폐지갑',
};

// 자산/부채 구분
export const ACCOUNT_TYPE_IS_ASSET: Record<AccountType, boolean> = {
  [AccountType.BANK_ACCOUNT]: true,
  [AccountType.SECURITIES]: true,
  [AccountType.CASH]: true,
  [AccountType.DEBIT_CARD]: true,
  [AccountType.CREDIT_CARD]: false,  // 신용카드만 부채
  [AccountType.SAVINGS]: true,
  [AccountType.DEPOSIT]: true,
  [AccountType.CRYPTO_WALLET]: true,
};
```

### AssetType Enum (자산 유형)

**자산 유형은 코드 레벨 Enum으로 관리** (DB 테이블 사용 안 함)

```python
# Python Backend Enum
from enum import Enum

class AssetType(str, Enum):
    """자산 유형 Enum"""
    STOCK = "stock"        # 주식
    CRYPTO = "crypto"      # 가상화폐
    BOND = "bond"          # 채권
    FUND = "fund"          # 펀드
    ETF = "etf"            # ETF
    CASH = "cash"          # 현금 (예수금, 잔고 등)

# 유형별 속성 매핑
ASSET_TYPE_INFO = {
    AssetType.STOCK: {"name": "주식", "tradable": True},
    AssetType.CRYPTO: {"name": "가상화폐", "tradable": True},
    AssetType.BOND: {"name": "채권", "tradable": True},
    AssetType.FUND: {"name": "펀드", "tradable": True},
    AssetType.ETF: {"name": "ETF", "tradable": True},
    AssetType.CASH: {"name": "현금", "tradable": False},
}
```

```typescript
// TypeScript Frontend Enum
export enum AssetType {
  STOCK = 'stock',
  CRYPTO = 'crypto',
  BOND = 'bond',
  FUND = 'fund',
  ETF = 'etf',
  CASH = 'cash',
}

// 유형별 표시명 매핑
export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  [AssetType.STOCK]: '주식',
  [AssetType.CRYPTO]: '가상화폐',
  [AssetType.BOND]: '채권',
  [AssetType.FUND]: '펀드',
  [AssetType.ETF]: 'ETF',
  [AssetType.CASH]: '현금',
};

// 거래 가능 여부
export const ASSET_TYPE_TRADABLE: Record<AssetType, boolean> = {
  [AssetType.STOCK]: true,
  [AssetType.CRYPTO]: true,
  [AssetType.BOND]: true,
  [AssetType.FUND]: true,
  [AssetType.ETF]: true,
  [AssetType.CASH]: false,  // 현금은 직접 거래 불가 (입출금만)
};
```

**설계 근거**:
- ✅ **고정된 도메인**: 자산 유형은 거의 변하지 않음 (AccountType과 동일한 이유)
- ✅ **단순성**: DB 테이블, 외래키, 시드 데이터 관리 불필요
- ✅ **타입 안정성**: 컴파일 타임에 잘못된 값 방지
- ✅ **성능**: JOIN 없이 빠른 조회

---

## 성능 고려사항

### 인덱스 전략

```sql
-- 사용자별 조회 최적화
CREATE INDEX idx_assets_user_account ON assets(user_id, account_id, id);

-- 거래 조회 최적화
CREATE INDEX idx_transactions_asset_date ON transactions(asset_id, transaction_date DESC);

-- extras JSONB 필드 내 realized_profit 조회 최적화 (선택적)
-- CREATE INDEX idx_transactions_realized_profit ON transactions 
--     USING GIN ((extras -> 'realized_profit')) 
--     WHERE extras ? 'realized_profit';
```

### 쿼리 패턴

```sql
-- 특정 사용자의 모든 거래 조회
SELECT t.*, a.user_id, a.account_id
FROM transactions t
JOIN assets a ON t.asset_id = a.id
WHERE a.user_id = :user_id;

-- 특정 계좌의 모든 거래 조회
SELECT t.*, a.account_id
FROM transactions t
JOIN assets a ON t.asset_id = a.id
WHERE a.account_id = :account_id;

-- 특정 시점의 자산 수량 계산 (부호 규칙 활용)
SELECT SUM(quantity) as quantity_at_time
FROM transactions
WHERE asset_id = :asset_id
  AND transaction_date <= :target_date;

-- 거래 흐름 추적 (Running Balance)
SELECT 
    transaction_date,
    type,
    quantity,
    SUM(quantity) OVER (
        PARTITION BY asset_id 
        ORDER BY transaction_date, created_at
    ) as running_balance
FROM transactions
WHERE asset_id = :asset_id
ORDER BY transaction_date;

-- extras JSONB에서 가격 정보 조회
SELECT 
    id,
    type,
    quantity,
    extras->>'price' as price,
    extras->>'fee' as fee,
    (extras->>'realized_profit')::numeric as realized_profit
FROM transactions
WHERE asset_id = :asset_id
  AND type IN ('buy', 'sell')
  AND extras ? 'price';
```

### 파티셔닝 고려사항

대규모 트래픽 시 `transactions` 테이블 파티셔닝:

```sql
-- 월별 파티션 예시 (PostgreSQL 11+)
CREATE TABLE transactions_y2025m11 PARTITION OF transactions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

---

## 감사 추적 (Audit Trail)

- 모든 거래는 불변(Immutable)으로 기록됨
- `transaction_date`와 `created_at`으로 시간 순서 추적
- 과거 시점의 잔액/수량은 거래 내역을 집계하여 계산
- 실시간 잔액은 Redis에서 관리
- 필요 시 Materialized View로 스냅샷 생성 가능

## 비즈니스 규칙

- 사용자는 여러 계좌를 보유할 수 있음
- 계좌는 여러 자산을 포함할 수 있음  
- 자산 교환 거래는 반드시 2개 레코드로 기록 (복식부기)
- 수수료/세금은 매수 시 취득원가에 반영, 매도 시 realized_profit에서 차감
- 배당/이자는 income 타입으로 기록하되, 복식부기 적용 (배당 출처 추적용)