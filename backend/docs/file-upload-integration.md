# 거래 파일 업로드 API 통합

## 개요
`upload_transactions_file` API 엔드포인트에 `file_parser.py` 서비스를 통합하여 다양한 금융기관의 거래 내역 파일을 자동으로 파싱하고 표준 형식으로 변환합니다.

**테이블**: `asset_transactions`

## 기능

### 자동 형식 감지 및 변환
- 토스뱅크, 미래에셋증권, KB증권 형식을 자동으로 감지
- 각 형식을 표준 형식으로 자동 변환
- 거래 유형 자동 매핑 (한글 → 영문)

### 암호화 파일 지원
- Excel 파일 암호를 `password` 파라미터로 받음
- msoffcrypto를 사용한 복호화 자동 처리
- 암호 오류 시 명확한 에러 메시지 제공

### 카테고리 검증
- 업로드 시 각 행의 거래 타입과 매핑된 카테고리의 `flow_type` 일관성을 검증
- 허용 규칙:
  - buy/sell → investment, neutral
  - deposit/interest/dividend → income, transfer, neutral
  - withdraw/fee → expense, transfer, neutral
  - transfer_in/transfer_out → transfer, neutral
  - adjustment → neutral
- 규칙 위반 시 해당 행은 실패 처리되며 `errors` 배열에 상세 사유가 포함

## API 엔드포인트

```
POST /api/v1/transactions/upload
```

### 요청 파라미터

### 1. 토스뱅크 (Toss Bank)
- **파일 형식**: Excel (.xlsx, 암호화 지원)
- **특징**: 
  - 다단 헤더 구조 (메타데이터 + 실제 헤더)
  - 한글 거래 유형 (체크카드결제, 이체 등)
  - 거래 후 잔액 정보 포함
- **컬럼 매핑**:
  - 거래 일시 → transaction_date
  - 거래 유형 → type (9가지 타입으로 자동 매핑)
  - 거래 금액 → quantity
  - 거래 후 잔액 → balance_after
  - 적요, 거래 기관, 계좌번호, 메모 → description, memo

### 2. 미래에셋증권 (Mirae Asset)
- **파일 형식**: CSV (UTF-8, CP949)
- **컬럼 매핑**:
  - 체결일 + 체결시간 → transaction_date
  - 구분 → type
  - 수량 → quantity
  - 체결가 → price

### 3. KB증권 (KB Securities)
- **파일 형식**: CSV (UTF-8, CP949)
- **컬럼 매핑**:
  - 거래일자 → transaction_date
  - 거래구분 → type
  - 수량 → quantity
  - 단가 → price

### 4. 표준 형식 (Standard)
- **파일 형식**: CSV 또는 Excel
- **필수 컬럼**: transaction_date, type, quantity, price
- **선택 컬럼**: fee, tax, realized_profit, description, memo, balance_after

## 거래 유형 매핑 (토스뱅크)

| 한글 거래 유형 | 영문 Type | 설명 |
|---------------|-----------|------|
| 체크카드결제 | card_payment | 체크카드 결제 |
| 내계좌간자동이체 | internal_transfer | 내 계좌 간 이체 |
| 프로모션입금 | promotion_deposit | 프로모션 입금 |
| 이자입금 | interest | 이자 수령 |
| 자동이체 | auto_transfer | 자동 이체 |
| 입금 | deposit | 일반 입금 |
| 출금 | withdraw | 일반 출금 |
| 송금 | remittance | 송금 |
| 이체 | transfer | 이체 |
| 환전 | exchange | 통화 교환 (KRW↔USD 등) — 동일 계좌 내 현금 자산 간만 허용 |

## API 사용 예시

### 1. 암호화된 토스뱅크 파일 업로드 (Dry Run)
```bash
curl -X POST "http://localhost:8000/api/transactions/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@토스뱅크_거래내역.xlsx" \
  -F "asset_id=asset-uuid" \
  -F "password=770819" \
  -F "dry_run=true"
```

**응답 예시**:
```json
{
  "success": true,
  "total": 105,
  "created": 105,
  "skipped": 0,
  "failed": 0,
  "errors": [],
  "preview": [
    {
      "transaction_date": "2024-01-15T09:30:00",
      "type": "card_payment",
      "quantity": -15000,
      "price": 1.0,
      "fee": 0,
      "tax": 0,
      "realized_profit": 0,
      "description": "편의점 결제",
      "memo": "적요: 편의점, 거래기관: GS25",
      "balance_after": 500000
    }
    // ... 더 많은 거래
  ]
}
```

### 2. 실제 저장 (Dry Run = false)
```bash
curl -X POST "http://localhost:8000/api/transactions/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@토스뱅크_거래내역.xlsx" \
  -F "asset_id=asset-uuid" \
  -F "password=770819" \
  -F "dry_run=false"
```

### 3. 암호화되지 않은 CSV 파일
```bash
curl -X POST "http://localhost:8000/api/transactions/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@미래에셋_거래내역.csv" \
  -F "asset_id=asset-uuid" \
  -F "dry_run=false"
```

## 에러 처리

### 1. 암호화된 파일인데 비밀번호 없음
```json
{
  "detail": "암호화된 파일입니다. 암호를 입력해주세요."
}
```

### 2. 잘못된 비밀번호
```json
{
  "detail": "암호가 올바르지 않거나 파일을 읽을 수 없습니다: [오류 메시지]"
}
```

### 3. 지원하지 않는 형식
```json
{
  "detail": "알 수 없는 파일 형식입니다. 토스뱅크, 미래에셋, KB증권 형식만 지원됩니다."
}
```

### 4. 잘못된 거래 유형
```json
{
  "detail": "잘못된 거래 유형: unknown_type. 지원하는 유형: buy, sell, deposit, ..."
}

### 5. 카테고리 불일치(flow_type 미호환)
```json
{
  "detail": "거래 유형 'withdraw' 에는 카테고리 flow_type 'income' 를 사용할 수 없습니다. 허용: expense, neutral, transfer"
}
```
```

## 테스트

### 단위 테스트
```bash
# file_parser 서비스 테스트
pytest tests/test_file_parser.py -v

# 결과: 27 passed
```

### API 통합 테스트
```bash
# API 엔드포인트 테스트 (TODO)
pytest tests/test_transactions_api.py::test_upload_file -v
```

## 향후 개선 사항

1. **추가 금융기관 지원**
   - 신한은행, 우리은행, 하나은행 등
   - 각 은행별 파싱 로직 추가

2. **거래 중복 체크**
   - external_id 기반 중복 감지
   - 이미 존재하는 거래는 건너뛰기

3. **배치 처리 최적화**
   - 대용량 파일 (10,000+ 거래) 처리 성능 개선
   - 청크 단위 커밋

4. **UI 개선**
   - 파일 업로드 진행률 표시
   - 드래그 앤 드롭 지원
   - 에러 상세 보기

5. **파일 히스토리**
   - 업로드된 파일 이력 저장
   - 재업로드 방지

## 관련 파일

- **서비스**: `/app/services/file_parser.py`
- **API**: `/app/api/transactions.py`
- **테스트**: `/tests/test_file_parser.py`
- **스키마**: `/app/schemas/transaction.py`
- **문서**: `/docs/file-upload-integration.md`

## 작성일
2024년 11월 7일
