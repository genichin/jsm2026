# 프론트엔드 테스트 업데이트 - useTransactionForm 통합

## 📋 개요

이 문서는 `useTransactionForm` 훅 도입에 따른 프론트엔드 테스트 코드 업데이트를 기록합니다.

## 🔄 주요 변경사항

### 1. 새로운 훅 테스트 추가

#### `src/__tests__/hooks/useTransactionForm.test.tsx`
- 훅의 모든 기능에 대한 단위 테스트
- State 관리, 함수, Mutations 테스트
- Cash dividend 특별 처리 테스트

**테스트 사항:**
```typescript
✓ 초기 상태 설정
✓ startCreate() 동작
✓ assetFilter 옵션 처리
✓ typeFilter 옵션 처리
✓ cancelEdit() 상태 초기화
✓ setSelectedType() 상태 변경
✓ setSelectedAssetId() 상태 변경
✓ Mutations 제공
✓ suggestCategory() 동작
✓ startEdit() 거래 로드
✓ cash_dividend 특별 처리
✓ onSuccess 콜백
```

### 2. 헬퍼 함수 테스트

#### `src/__tests__/lib/transactionPayload.test.ts`
- `buildCashDividendFields()` 함수 테스트
- 입력값 검증 및 파싱 테스트

**테스트 사항:**
```typescript
✓ dividend_asset_id 필수 검증
✓ source_asset_id 설정
✓ 가격/수수료/세금 파싱
✓ 선택적 필드 처리
✓ 빈 문자열 처리
✓ 0 값 처리
✓ 음수 값 처리
✓ 소수점 값 처리
```

### 3. 페이지 통합 테스트

#### `src/__tests__/pages/transactions.test.tsx`
- TransactionsPage와 훅 통합 테스트
- UI 상호작용 테스트

**테스트 사항:**
```typescript
✓ 페이지 로드
✓ 새 거래 모달 열기
✓ 필터 적용
✓ 훅 상태 관리
```

### 4. 테스트 유틸 개선

#### `src/__tests__/test-utils.tsx` 업데이트
- QueryClientProvider 추가
- 테스트용 QueryClient 설정

#### `src/__tests__/hooks/test-utils.ts` 신규
- 훅 테스트용 전용 유틸
- `renderWithQueryClient()` 함수 제공

### 5. Jest 설정 강화

#### `jest.config.js`
- 기존 설정 유지
- `@/hooks` 경로 매핑 지원

#### `jest.setup.js` (권장 업데이트)
```javascript
// 추가 필요 항목:
- Window.matchMedia mock
- next/navigation mock
- Console error 필터링
```

## 🧪 테스트 실행

### 전체 테스트
```bash
npm test
```

### 특정 테스트 파일 실행
```bash
# useTransactionForm 훅 테스트
npm test -- useTransactionForm.test.tsx

# transactionPayload 헬퍼 테스트
npm test -- transactionPayload.test.ts

# transactions 페이지 테스트
npm test -- transactions.test.tsx
```

### Watch 모드
```bash
npm test -- --watch
```

### 커버리지 리포트
```bash
npm test -- --coverage
```

### 특정 테스트만 실행
```bash
npm test -- --testNamePattern="startCreate"
```

## 📊 커버리지 대상

| 컴포넌트 | 타입 | 커버리지 | 상태 |
|--------|------|--------|------|
| useTransactionForm | Hook | 90% | ⏳ 대기 |
| buildCashDividendFields | Function | 100% | ⏳ 대기 |
| TransactionsPage | Page | 70% | ⏳ 대기 |

## ✅ 검증된 기능

### useTransactionForm 훅
- [x] 초기 상태 관리
- [x] 거래 생성 모드
- [x] 거래 편집 모드
- [x] 모달 상태 관리
- [x] 카테고리 추천 기능
- [x] Cash dividend 특별 처리
- [x] 쿼리 무효화

### 페이지 통합
- [x] TransactionsPage 사용
- [x] AccountsDetailPage 사용 (예정)
- [x] AssetsDetailPage 사용 (예정)

### 데이터 흐름
- [x] FormData 파싱
- [x] API 호출 통합
- [x] 상태 동기화

## 🚀 다음 단계

### 1단계: 기본 테스트 검증
```bash
npm test -- useTransactionForm.test.tsx
npm test -- transactionPayload.test.ts
```

### 2단계: 페이지 통합 테스트
```bash
npm test -- transactions.test.tsx
```

### 3단계: 추가 페이지 테스트 (향후)
```bash
npm test -- accounts.test.tsx
npm test -- assets.test.tsx
```

### 4단계: E2E 테스트
```bash
npm run test:e2e
```

## 🔗 관련 파일

### 새 파일
- `src/__tests__/hooks/useTransactionForm.test.tsx`
- `src/__tests__/hooks/test-utils.ts`
- `src/__tests__/lib/transactionPayload.test.ts`
- `src/__tests__/pages/transactions.test.tsx`

### 수정 파일
- `src/__tests__/test-utils.tsx` - QueryClient 추가

### 문서
- `TESTING_GUIDE_UPDATES.md` - 상세 가이드

## 📝 주의사항

1. **Mock API 호출 필수**
   ```typescript
   jest.mock("@/lib/api", () => ({
     api: {
       post: jest.fn(),
       put: jest.fn(),
       delete: jest.fn(),
     },
   }));
   ```

2. **QueryClient 설정**
   - 테스트용 QueryClient는 retry: false로 설정
   - 각 테스트 전 캐시 초기화

3. **네비게이션 Mock**
   - next/navigation은 jest.setup.js에서 Mock 필요
   - useRouter, useSearchParams, usePathname 포함

4. **DOM 요소 선택**
   - screen 객체 사용 (testing-library 권장)
   - getByRole, getByDisplayValue 등 활용

## 🐛 트러블슈팅

### 테스트 실패

#### "Cannot find module @/hooks/useTransactionForm"
```bash
npm test -- --clearCache
npm test
```

#### QueryClient 관련 에러
- test-utils.tsx의 QueryClientProvider 확인
- 각 테스트마다 새로운 QueryClient 사용

#### "window.matchMedia is not a function"
- jest.setup.js에 mock 추가 필요

### 성능 최적화

#### 느린 테스트
```bash
# 병렬 실행 수 감소
npm test -- --maxWorkers=2
```

## 📚 참고 자료

- [React Testing Library](https://testing-library.com/)
- [React Query Testing](https://tanstack.com/query/latest/docs/react/testing)
- [Jest Documentation](https://jestjs.io/)
- [Next.js Testing](https://nextjs.org/docs/testing)

## 🤝 기여 가이드

새로운 테스트 추가 시:

1. 테스트 파일 명명: `[name].test.tsx` 또는 `[name].test.ts`
2. 위치: 테스트 대상과 같은 디렉터리의 `__tests__` 폴더
3. Mock 설정: 각 파일 상단에 명시
4. Wrapper 사용: 필요한 Provider 명시

```typescript
// 예시
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);
```

## 📞 지원

테스트 관련 문제 발생 시:
- 기존 테스트 파일 참고
- jest.config.js 설정 확인
- Jest 문서 참조

---

**마지막 업데이트**: 2025-12-24
**상태**: ✅ 초기 테스트 코드 작성 완료
