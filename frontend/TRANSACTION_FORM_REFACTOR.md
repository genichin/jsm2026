# TransactionForm 리팩토링 완료

## 개요
거래 추가/수정 모달을 효율적인 구조로 리팩토링했습니다.

## 변경 사항

### 1. 새로운 컴포넌트 구조
```
frontend/src/components/TransactionForm/
├── types.ts              # 타입 정의
├── config.ts             # 거래 유형별 설정
├── FormFields.tsx        # 재사용 가능한 필드 컴포넌트들
├── DynamicTransactionForm.tsx  # 동적 폼 렌더러
└── index.ts              # Export 모듈
```

### 2. 주요 개선점

#### 선언적 설정 (config.ts)
- 각 거래 유형(deposit, withdraw, buy, sell, etc.)마다 필요한 필드 정의
- 필수 필드, 숨김 필드, 특수 동작을 명확히 선언
- 새로운 거래 유형 추가 시 설정만 수정하면 됨

```typescript
export const TRANSACTION_TYPE_CONFIGS: Record<TransactionType, TransactionTypeConfig> = {
  buy: {
    type: 'buy',
    label: '매수',
    fields: ['asset', 'quantity', 'price', 'fee', 'tax', 'date', 'cash_asset', 'category', ...],
    requiredFields: ['asset', 'quantity', 'price', 'date'],
    specialBehavior: ['cashAssetSelector'],
  },
  // ... 17개 거래 유형 모두 정의됨
}
```

#### 컴포넌트화된 필드 (FormFields.tsx)
- 각 입력 필드를 독립적인 컴포넌트로 분리
- 재사용 가능하고 테스트 용이
- Props를 통한 일관된 인터페이스

```typescript
- AssetField: 자산 선택
- TypeField: 거래 유형 선택
- QuantityField: 수량 입력 (음수 힌트 지원)
- PriceField: 가격 입력
- FeeField, TaxField: 수수료/세금
- DateField: 거래일시
- CategoryField: 카테고리 선택
- DescriptionField: 설명 (자동 추천 버튼 통합)
- MemoField: 메모
- ConfirmedField: 확정 체크박스
- CashAssetField: 현금 자산 선택 (buy/sell/dividend용)
- TargetAssetField: 환전 대상 자산
- ExchangeAmountFields: 환전 금액 입력 (환율 자동 계산)
```

#### 동적 렌더링 (DynamicTransactionForm.tsx)
- 거래 유형에 따라 필요한 필드만 동적으로 렌더링
- 특수 동작(환율 계산, 현금 자산 필터링 등) 자동 처리
- 편집/생성 모드 자동 전환

### 3. 기존 코드 정리
- 300+ 줄의 중복된 조건부 렌더링 제거
- 환전 관련 상태 관리를 폼 컴포넌트 내부로 이동
- 메인 페이지에서 폼 로직 분리

### 4. 장점

#### 유지보수성
- 새로운 거래 유형 추가: config.ts만 수정
- 필드 수정: 해당 컴포넌트만 수정
- 버그 수정 범위가 명확함

#### 가독성
- 각 거래 유형의 필드 구성이 한눈에 파악됨
- 컴포넌트 이름만으로 역할 이해 가능

#### 재사용성
- 필드 컴포넌트를 다른 폼에서도 사용 가능
- 특수 동작 로직을 다른 프로젝트에 이식 용이

#### 테스트 용이성
- 각 필드 컴포넌트를 독립적으로 테스트
- 설정 기반이므로 엣지 케이스 검증 간단

#### 타입 안정성
- TypeScript로 모든 타입 검증
- 필드 존재 여부 컴파일 타임에 체크

## 사용 예시

### 메인 페이지에서 사용
```typescript
<DynamicTransactionForm
  transactionType={selectedType as TransactionType}
  editing={editing}
  isEditMode={!!editing?.id}
  assets={assetsQuery.data?.items || []}
  categories={categoriesFlat}
  selectedAssetId={selectedAssetId}
  onAssetChange={setSelectedAssetId}
  onTypeChange={setSelectedType}
  onSubmit={submitForm}
  onCancel={cancelEdit}
  onSuggestCategory={suggestCategory}
  isSuggesting={isSuggesting}
  suggestedCategoryId={suggestedCategoryId}
/>
```

### 새로운 거래 유형 추가
```typescript
// config.ts에만 추가
interest: {
  type: 'interest',
  label: '이자',
  fields: ['asset', 'quantity', 'price', 'date', 'category', 'description', 'memo', 'confirmed'],
  requiredFields: ['asset', 'quantity', 'date'],
  specialBehavior: [],
}
```

## 향후 개선 가능 사항

1. **필드 검증 규칙**: 각 필드별 유효성 검사 함수 추가
2. **조건부 필드**: 다른 필드 값에 따라 동적으로 표시/숨김
3. **필드 그룹핑**: 시각적 구분을 위한 섹션 분리
4. **커스텀 렌더러**: 특정 유형만을 위한 완전히 다른 레이아웃
5. **폼 상태 관리**: React Hook Form 또는 Formik 통합

## 지원되는 거래 유형 (17개)

- deposit (입금)
- withdraw (출금)
- buy (매수)
- sell (매도)
- dividend (배당)
- interest (이자)
- fee (수수료)
- transfer_in (이체입금)
- transfer_out (이체출금)
- internal_transfer (내부이체)
- adjustment (수량조정)
- invest (투자)
- redeem (해지)
- card_payment (카드결제)
- promotion_deposit (프로모션입금)
- auto_transfer (자동이체)
- remittance (송금)
- exchange (환전)

## 테스트 확인 사항

- [x] TypeScript 컴파일 에러 없음
- [ ] 각 거래 유형별 필드 렌더링 확인
- [ ] 환전 거래의 환율 자동 계산 동작 확인
- [ ] 매수/매도 시 현금 자산 필터링 동작 확인
- [ ] 카테고리 자동 추천 기능 동작 확인
- [ ] 편집 모드에서 필드 고정/변경 가능 여부 확인
