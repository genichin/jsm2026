# 프론트엔드 테스트 가이드 - useTransactionForm 훅

## 개요

이 문서는 `useTransactionForm` 훅 통합 후 추가된 테스트 코드에 대해 설명합니다.

## 작성된 테스트 파일

### 1. `src/__tests__/hooks/useTransactionForm.test.tsx`

**목적**: `useTransactionForm` 훅의 모든 기능을 테스트

**테스트 항목**:
- ✅ 초기 상태 검증
- ✅ `startCreate()` 함수 동작
- ✅ `assetFilter`, `typeFilter` 옵션 처리
- ✅ `cancelEdit()` 함수로 상태 초기화
- ✅ `setSelectedType()` 상태 변경
- ✅ `setSelectedAssetId()` 상태 변경
- ✅ Mutations 제공 확인
- ✅ `suggestCategory()` 함수 동작
- ✅ `startEdit()` 함수로 거래 데이터 로드
- ✅ `cash_dividend` 타입 특별 처리
- ✅ `onSuccess` 콜백 설정

**실행 방법**:
```bash
npm test -- useTransactionForm.test.tsx
```

### 2. `src/__tests__/lib/transactionPayload.test.ts`

**목적**: `buildCashDividendFields()` 헬퍼 함수 테스트

**테스트 항목**:
- ✅ 배당 자산 ID 필수 검증
- ✅ `source_asset_id` 올바른 설정
- ✅ 가격, 수수료, 세금 파싱
- ✅ 선택적 필드 처리
- ✅ 빈 문자열 처리
- ✅ 0 값 처리
- ✅ 음수 값 처리
- ✅ 소수점 값 처리

**실행 방법**:
```bash
npm test -- transactionPayload.test.ts
```

### 3. `src/__tests__/pages/transactions.test.tsx`

**목적**: TransactionsPage의 `useTransactionForm` 훅 통합 테스트

**테스트 항목**:
- ✅ 페이지 로드
- ✅ 새 거래 모달 열기
- ✅ 필터 기능
- ✅ 훅 상태 관리

**실행 방법**:
```bash
npm test -- transactions.test.tsx
```

## 업데이트된 유틸 파일

### `src/__tests__/test-utils.tsx`

**변경 사항**:
- `QueryClientProvider` 추가로 React Query 테스트 환경 지원
- 테스트용 QueryClient 설정 (retry: false)

### `src/__tests__/hooks/test-utils.ts`

**목적**: 훅 테스트용 전용 유틸

**제공 함수**:
- `createTestQueryClient()`: 테스트용 QueryClient 생성
- `renderWithQueryClient()`: QueryClient와 함께 컴포넌트 렌더링

**사용 예**:
```typescript
const { result, queryClient } = renderWithQueryClient(<YourHook />);
```

## Jest 설정

### `jest.config.js`
- 모듈 경로 매핑 설정 (`@/*`)
- 테스트 파일 패턴 설정
- 코드 커버리지 설정

### `jest.setup.js`
- `@testing-library/jest-dom` import
- Window.matchMedia mock
- next/navigation mock (필요시 추가)

## 테스트 실행 명령어

```bash
# 모든 테스트 실행
npm test

# 특정 테스트 파일 실행
npm test -- useTransactionForm.test.tsx

# Watch 모드
npm test -- --watch

# 커버리지 리포트
npm test -- --coverage

# 특정 패턴 테스트
npm test -- --testNamePattern="startCreate"
```

## 마이그레이션 체크리스트

### 완료 항목 ✅
- [x] `useTransactionForm` 훅 테스트 작성
- [x] `buildCashDividendFields` 헬퍼 테스트 작성
- [x] TransactionsPage 통합 테스트 작성
- [x] test-utils.tsx 업데이트 (QueryClient 추가)
- [x] hooks용 전용 test-utils 생성
- [x] jest.setup.js 셈업 강화

### 향후 작업 📋
- [ ] accounts/[id]/page.tsx 통합 테스트
- [ ] assets/[id]/page.tsx 통합 테스트
- [ ] DynamicTransactionForm 컴포넌트 테스트
- [ ] E2E 테스트 (Cypress/Playwright)

## 테스트 커버리지 목표

| 항목 | 커버리지 목표 | 현재 |
|------|----------|------|
| useTransactionForm 훅 | 90% | ⏳ |
| transactionPayload 헬퍼 | 100% | ⏳ |
| 페이지 통합 | 70% | ⏳ |

## 의존성

추가된 테스트 코드는 다음 라이브러리를 사용합니다:

- `@testing-library/react`: UI 컴포넌트 테스트
- `@testing-library/jest-dom`: Jest 커스텀 매처
- `@tanstack/react-query`: React Query 테스트 유틸
- `jest`: 테스트 러너

## 문제 해결

### 모듈 찾기 오류
```bash
# jest 캐시 초기화
npm test -- --clearCache
```

### QueryClient 관련 에러
- `test-utils.tsx`의 QueryClientProvider가 올바르게 설정되었는지 확인
- 테스트에서 `renderWithQueryClient` 사용

### 타입 에러
```bash
# TypeScript 재컴파일
npm run build
```

## 참고 자료

- [React Testing Library 문서](https://testing-library.com/docs/react-testing-library/intro/)
- [React Query 테스팅 가이드](https://tanstack.com/query/latest/docs/react/testing)
- [Jest 문서](https://jestjs.io/docs/getting-started)
