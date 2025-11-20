from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings

# OpenAPI 메타데이터
tags_metadata = [
    {
        "name": "health",
        "description": "서버 상태 확인 엔드포인트",
    },
    {
        "name": "auth",
        "description": "사용자 인증 및 권한 관리. JWT 토큰 기반 인증을 사용합니다.",
    },
    {
        "name": "users",
        "description": "사용자 계정 관리",
    },
    {
        "name": "accounts",
        "description": "계좌 관리. 은행계좌, 현금, 카드 등의 자산 계좌를 관리합니다.",
    },
    {
        "name": "assets",
        "description": "자산 관리. 주식, 가상화폐, 채권 등의 투자 자산 정보를 관리합니다.",
    },
    {
        "name": "transactions",
        "description": "자산 거래 관리. 자산별 매수/매도, 배당, 조정 등의 거래를 기록하고 추적합니다.",
    },
    {
        "name": "categories",
        "description": "거래 카테고리 관리. 지출/수입/이동/투자 분류 및 계층 구조 제공.",
    },
    {
        "name": "investments",
        "description": "투자 자산 관리. 주식, 가상화폐, 채권 등의 투자 자산을 추적합니다.",
    },
    {
        "name": "real-assets",
        "description": "실물 자산 관리. 부동산, 차량 등의 실물 자산을 관리합니다.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# J's Money Backend API

개인 자산관리 소프트웨어 백엔드 API

## 주요 기능

* **인증**: JWT 토큰 기반 인증
* **계좌 관리**: 은행계좌, 현금, 카드 등의 자산 계좌 관리
* **거래 관리**: 수입, 지출, 이체 내역 기록 및 조회
* **투자 자산**: 주식, 가상화폐, 채권 등의 투자 자산 추적
* **실물 자산**: 부동산, 차량 등의 실물 자산 관리

## 인증 방법

대부분의 API는 JWT 토큰 인증이 필요합니다:

1. `/api/v1/auth/login` 엔드포인트로 로그인
2. 응답으로 받은 `access_token` 사용
3. 이후 모든 요청 헤더에 `Authorization: Bearer {access_token}` 포함

## 기본 관리자 계정

* Email: admin@jsmoney.com
* Password: admin123

⚠️ 프로덕션 환경에서는 반드시 비밀번호를 변경하세요.
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    contact={
        "name": "J's Money Support",
        "email": "admin@jsmoney.com",
    },
    license_info={
        "name": "Private",
    },
)

# HTTPS Redirect - HTTP 요청을 HTTPS로 리다이렉트
# 프로덕션에서 리버스 프록시(Nginx/Caddy)가 SSL 처리하는 경우 비활성화
# if not settings.DEBUG:
#     app.add_middleware(HTTPSRedirectMiddleware)

# Trusted Host - 허용된 호스트만 접근 가능
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
async def root():
    """
    루트 엔드포인트
    
    서버가 정상적으로 실행 중인지 확인합니다.
    
    Returns:
        dict: 서버 정보 및 상태
    """
    return {
        "message": "J's Money Backend API",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["health"])
async def health_check():
    """
    헬스 체크 엔드포인트
    
    모니터링 시스템에서 서버 상태를 확인하는데 사용됩니다.
    
    Returns:
        dict: 서버 상태
    """
    return {"status": "healthy"}


# 보안 헤더 추가
@app.middleware("http")
async def add_security_headers(request, call_next):
    """보안 헤더 추가"""
    response = await call_next(request)
    
    # HSTS - 브라우저가 항상 HTTPS를 사용하도록 강제
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # 기타 보안 헤더
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Register API routers
from app.api import auth, accounts, assets, transactions, categories
from app.api import auto_rules, tags, reminders, activities

app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"]
)

app.include_router(
    accounts.router,
    prefix=f"{settings.API_V1_PREFIX}/accounts",
    tags=["accounts"]
)

app.include_router(
    assets.router,
    prefix=f"{settings.API_V1_PREFIX}/assets",
    tags=["assets"]
)

app.include_router(
    transactions.router,
    prefix=f"{settings.API_V1_PREFIX}/transactions",
    tags=["transactions"]
)

app.include_router(
    categories.router,
    prefix=f"{settings.API_V1_PREFIX}/categories",
    tags=["categories"]
)

app.include_router(
    auto_rules.router,
    prefix=f"{settings.API_V1_PREFIX}/auto-rules",
    tags=["categories"]
)

app.include_router(
    tags.router,
    prefix=f"{settings.API_V1_PREFIX}/tags",
    tags=["tags"]
)
app.include_router(
    reminders.router,
    prefix=f"{settings.API_V1_PREFIX}/reminders",
    tags=["reminders"]
)

app.include_router(
    activities.router,
    prefix=f"{settings.API_V1_PREFIX}/activities",
    tags=["activities"]
)
