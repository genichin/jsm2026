# J's Money Frontend

Next.js (App Router) + TypeScript + Tailwind 기반 프론트엔드. FastAPI 백엔드(`/api/v1`)와 연동됩니다.

## 빠른 시작

```bash
cd frontend
# 환경 변수 설정 (개발)
cp .env.example .env.local

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
npm run dev:8080  # starts dev on :8080
# → http://localhost:3000
```

백엔드가 로컬에서 실행 중이어야 합니다. HTTPS 전용 프론트에서는 혼합 콘텐츠를 피하기 위해 `/api` 경유(Next.js rewrites) 방식을 사용합니다. 외부 백엔드 주소는 `.env.local`의 `NEXT_PUBLIC_API_BASE_URL`로 설정하세요.

## 배포

cd frontend
npm run build
npm run start:8080


## 스택
- Next.js 14 (App Router) + React 18 + TypeScript
- Tailwind CSS
- TanStack Query (서버 상태) + Axios (API 클라이언트)
- React Hook Form + Zod (폼/검증)
- TanStack Table (테이블)
- Recharts (차트)

## 구조
```
src/
  app/
    (auth)/login        # 로그인 페이지 (앱 쉘 없이)
    dashboard           # 대시보드 (차트/요약)
    accounts            # 계좌 목록
    assets              # 자산 목록
    transactions        # 거래 목록 (최근 50건)
    categories          # 카테고리 목록
    tags                # 태그 목록
    reminders           # 리마인더 목록
    activities          # 액티비티 목록
  components/           # Sidebar, Topbar, Card, DataTable 등
  lib/                  # api.ts(axios), auth.ts(token), queryClient.tsx
```

## 인증
- `/auth/login`으로 로그인하면 `access_token`을 `localStorage`에 저장합니다.
- 모든 API 요청은 Axios 인터셉터가 `Authorization: Bearer <token>`을 자동으로 첨부합니다.
- 401 응답 시 토큰을 삭제하고 `/login`으로 리다이렉트합니다.

## 프록시/리라이트
`next.config.mjs`의 rewrites로 `/api/*` 요청을 `NEXT_PUBLIC_API_BASE_URL`로 전달합니다. (외부 도메인으로 서버 사이드 리라이트되어 브라우저 혼합 콘텐츠가 발생하지 않습니다)

## HTTPS 전용 개발 서버

개발 중에도 프론트는 HTTPS로만 서비스됩니다.

1) 로컬 인증서 생성(예: mkcert)

```bash
mkcert -install
mkcert -key-file ./certs/localhost-key.pem -cert-file ./certs/localhost-cert.pem localhost 127.0.0.1 ::1
```

2) `.env.local` 설정

`.env.local.example`를 복사/수정:

```bash
cp .env.local.example .env.local
```

3) HTTPS 개발 서버 실행

```bash
npm run dev:https
```

동작 방식: Next dev 서버를 8081에서 구동하고, 8080에서 HTTPS 리버스 프록시가 웹소켓(HMR) 포함해 중계합니다. 브라우저는 항상 `https://localhost:8080`으로 접속하세요.

참고: 백엔드가 HTTP만 제공해도, 프론트는 `/api`를 같은 오리진(HTTPS)으로 호출하고 서버 측 리라이트로 외부 백엔드에 연결하기 때문에 브라우저 혼합 콘텐츠 경고가 발생하지 않습니다. 외부 백엔드가 자체 서명(셀프사인) 인증서라면 유효한 인증서를 권장합니다.

## TODO
- CRUD 폼 및 상세 페이지 추가 (계좌/자산/거래/카테고리 등)
- 차트/리포트 강화 (손익, 자산 배분 등)
- 글로벌 상태 최소화 유지(Zustand 필요 시 한정 사용)
- 테스트 (Jest/RTL, E2E는 Playwright)
