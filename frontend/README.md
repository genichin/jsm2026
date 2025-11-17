# J's Money Frontend

Next.js (App Router) + TypeScript + Tailwind 기반 프론트엔드. FastAPI 백엔드(`/api/v1`)와 연동됩니다.

## 배포 (Production)

### 1. 환경 변수 설정

프로덕션 환경 변수 파일 생성:

```bash
# .env.production 파일 생성
cat > .env.production << EOF
NEXT_PUBLIC_API_BASE_URL=http://jsfamily2.myds.me:40041/api/v1
EOF
```

### 2. 빌드

```bash
cd frontend
npm install
npm run build
```

빌드 결과물은 `.next/` 디렉토리에 생성됩니다.

### 3. 배포 방법

#### 옵션 A: Node.js 서버로 직접 실행 (권장)

```bash
# 프로덕션 모드로 실행 (포트 8080)
npm run start -- -p 8080 -H 0.0.0.0

# 또는 백그라운드 실행
nohup npm run start -- -p 8080 -H 0.0.0.0 > /tmp/frontend.log 2>&1 &
```

#### 옵션 B: PM2로 프로세스 관리

```bash
# PM2 설치 (전역)
npm install -g pm2

# PM2로 실행
pm2 start npm --name "jsmoney-frontend" -- start -- -p 8080 -H 0.0.0.0

# 자동 시작 설정
pm2 startup
pm2 save

# 상태 확인
pm2 status
pm2 logs jsmoney-frontend

# 재시작
pm2 restart jsmoney-frontend
```

#### 옵션 C: Docker로 배포

`Dockerfile` 생성:

```dockerfile
FROM node:18-alpine AS base

# 의존성 설치
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# 빌드
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# 프로덕션 실행
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 8080
ENV PORT=8080

CMD ["node", "server.js"]
```

`next.config.mjs`에 standalone 출력 설정 추가:

```javascript
const nextConfig = {
  output: 'standalone',
  // ... 기존 설정
};
```

Docker 빌드 및 실행:

```bash
# 빌드
docker build -t jsmoney-frontend .

# 실행
docker run -d \
  --name jsmoney-frontend \
  -p 40042:8080 \
  -e NEXT_PUBLIC_API_BASE_URL=http://jsfamily2.myds.me:40041/api/v1 \
  jsmoney-frontend
```

#### 옵션 D: 정적 파일로 내보내기 (Static Export)

**주의**: API rewrites가 작동하지 않으므로 클라이언트에서 직접 백엔드 URL로 요청합니다.

`next.config.mjs`에 추가:

```javascript
const nextConfig = {
  output: 'export',
  // rewrites는 static export에서 지원 안 됨
};
```

빌드 및 배포:

```bash
npm run build
# 결과물: out/ 디렉토리

# Nginx/Apache 등 웹서버에 배포
cp -r out/* /var/www/html/
```

### 4. 리버스 프록시 설정 (선택)

Nginx를 프론트에 두면 SSL 종료, 캐싱, 로드 밸런싱 등을 처리할 수 있습니다:

```nginx
# /etc/nginx/sites-available/jsmoney
server {
    listen 80;
    server_name jsfamily2.myds.me;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. 업데이트 배포

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 의존성 업데이트 (필요시)
npm install

# 3. 리빌드
npm run build

# 4. 서버 재시작
# Node.js 직접 실행인 경우
pkill -f "next start" && npm run start -- -p 8080 -H 0.0.0.0 &

# PM2인 경우
pm2 restart jsmoney-frontend

# Docker인 경우
docker stop jsmoney-frontend
docker rm jsmoney-frontend
docker build -t jsmoney-frontend .
docker run -d --name jsmoney-frontend -p 40042:8080 \
  -e NEXT_PUBLIC_API_BASE_URL=http://jsfamily2.myds.me:40041/api/v1 \
  jsmoney-frontend
```

### 6. 환경별 URL 설정

개발/프로덕션에서 다른 API URL을 사용:

```bash
# 개발
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# 프로덕션
NEXT_PUBLIC_API_BASE_URL=http://jsfamily2.myds.me:40041/api/v1
```

### 7. 배포 체크리스트

- [ ] 백엔드 API URL이 올바른지 확인 (`.env.production`)
- [ ] `npm run build`가 에러 없이 완료되는지 확인
- [ ] 프로덕션 환경에서 로그인/로그아웃 테스트
- [ ] 모든 주요 페이지 동작 확인 (Accounts, Assets, Transactions 등)
- [ ] 네트워크 탭에서 API 요청이 올바른 URL로 가는지 확인
- [ ] 콘솔 에러 없는지 확인
- [ ] 모바일/데스크톱 반응형 확인

## 빠른 시작 (개발)

```bash
cd frontend
# 환경 변수 설정 (개발)
cp .env.example .env.local

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
npm run dev -- -p 8080  # starts dev on :8080
# → http://localhost:3000
```

백엔드가 로컬에서 실행 중이어야 합니다. HTTPS 전용 프론트에서는 혼합 콘텐츠를 피하기 위해 `/api` 경유(Next.js rewrites) 방식을 사용합니다. 외부 백엔드 주소는 `.env.local`의 `NEXT_PUBLIC_API_BASE_URL`로 설정하세요.




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

## HTTPS 개발 환경 (선택사항)

**주의**: 현재는 HTTP 개발 모드를 사용합니다. HTTPS가 필요한 경우에만 참고하세요.

개발 중에도 HTTPS를 사용하려면:

1) 로컬 인증서 생성(예: mkcert)

```bash
mkcert -install
mkcert -key-file ./certs/localhost-key.pem -cert-file ./certs/localhost-cert.pem localhost 127.0.0.1 ::1
```

2) Next.js HTTPS 옵션으로 실행

```bash
npm run dev -- -p 8080 --experimental-https --experimental-https-key ./certs/localhost-key.pem --experimental-https-cert ./certs/localhost-cert.pem
```

참고: 백엔드가 HTTP만 제공해도, 프론트는 `/api`를 같은 오리진으로 호출하고 서버 측 리라이트로 연결하므로 혼합 콘텐츠 경고가 발생하지 않습니다.

## TODO
- CRUD 폼 및 상세 페이지 추가 (계좌/자산/거래/카테고리 등)
- 차트/리포트 강화 (손익, 자산 배분 등)
- 글로벌 상태 최소화 유지(Zustand 필요 시 한정 사용)
- 테스트 (Jest/RTL, E2E는 Playwright)
