# 프론트엔드 테스트 가이드

## 개요

이 프로젝트는 Jest와 React Testing Library를 사용하여 포괄적인 테스트 환경을 제공합니다.

## 설치된 테스트 도구

- **Jest**: JavaScript 테스트 프레임워크
- **React Testing Library**: React 컴포넌트 테스트 라이브러리
- **@testing-library/jest-dom**: Jest 매처 확장
- **@testing-library/user-event**: 사용자 상호작용 시뮬레이션
- **ts-jest**: TypeScript 지원

## 테스트 실행

### 모든 테스트 실행
```bash
npm test
```

### Watch 모드 (코드 변경 시 자동 재실행)
```bash
npm run test:watch
```

### 커버리지 보고서 생성
```bash
npm run test:coverage
```

## 테스트 작성 방법

### 1. 유틸리티 함수 테스트

`src/__tests__/utils/format.test.ts` 예제:

```typescript
describe('formatCurrency', () => {
  it('숫자를 원화 형식으로 포맷해야 함', () => {
    expect(formatCurrency(1000)).toBe('₩1,000')
  })
})
```

### 2. React 컴포넌트 테스트

`src/__tests__/components/Button.test.tsx` 예제:

```typescript
import { render, screen } from '../test-utils'

describe('Button 컴포넌트', () => {
  it('텍스트를 렌더링해야 함', () => {
    render(<Button>클릭하세요</Button>)
    expect(screen.getByText('클릭하세요')).toBeInTheDocument()
  })

  it('클릭 이벤트를 처리해야 함', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>클릭</Button>)
    
    const button = screen.getByRole('button')
    button.click()
    
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

## 디렉토리 구조

```
src/
├── __tests__/
│   ├── test-utils.tsx       # 테스트 유틸리티 (Provider 래퍼)
│   ├── components/
│   │   └── Button.test.tsx   # 컴포넌트 테스트
│   └── utils/
│       └── format.test.ts    # 유틸 함수 테스트
└── [다른 파일들]
```

## 테스트 파일 위치 규칙

테스트 파일은 다음 패턴으로 자동으로 인식됩니다:

- `src/__tests__/**/*.test.{ts,tsx}`
- `src/**/*.test.{ts,tsx}`

## Jest 설정

### jest.config.js
- `testEnvironment`: jsdom (브라우저 환경 시뮬레이션)
- `setupFilesAfterEnv`: jest.setup.js (테스트 초기화)
- `moduleNameMapper`: `@/*` → `src/*` (경로 별칭)

### jest.setup.js
- `@testing-library/jest-dom` 임포트
- 추가 설정 필요 시 여기에 추가

## 주요 Testing Library 메서드

### 렌더링
```typescript
import { render, screen } from '../test-utils'

render(<Component />)
```

### 쿼리
```typescript
// getBy: 요소 찾기 (없으면 에러)
screen.getByText('텍스트')
screen.getByRole('button')
screen.getByPlaceholderText('입력...')

// queryBy: 요소 찾기 (없으면 null)
screen.queryByText('텍스트')

// findBy: 비동기 요소 찾기 (없으면 에러)
await screen.findByText('텍스트')
```

### 상호작용
```typescript
import { userEvent } from '@testing-library/user-event'

const user = userEvent.setup()
await user.click(button)
await user.type(input, 'text')
```

## 모킹

### API 모킹
```typescript
jest.mock('axios')
import axios from 'axios'

axios.get.mockResolvedValue({ data: [] })
```

### 컴포넌트 모킹
```typescript
jest.mock('../Component', () => ({
  Component: () => <div>Mock</div>
}))
```

## 베스트 프랙티스

1. **사용자 관점에서 테스트**: 구현 세부사항이 아닌 사용자 행동에 초점
2. **의미 있는 테스트 이름**: `it('should render button when clicked')` O / `it('test 1')` X
3. **테스트 격리**: 각 테스트는 독립적으로 실행되어야 함
4. **커버리지 목표**: 80% 이상 유지
5. **빠른 테스트**: 단위 테스트는 빨라야 함

## CI/CD 통합

### GitHub Actions 예제
```yaml
- name: Run tests
  run: npm test -- --coverage
```

## 문제 해결

### "ReferenceError: document is not defined"
→ `jest.config.js`에서 `testEnvironment: 'jest-environment-jsdom'` 확인

### "Cannot find module '@/...'"
→ `jest.config.js`의 `moduleNameMapper` 확인

### "Warning: ReactDOM.render..."
→ React 18 변경사항, 필요 시 테스트 코드 업데이트

## 참고 자료

- [Jest 공식 문서](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
