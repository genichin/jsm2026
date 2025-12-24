daemon 서비스 개요
=================

`daemon`은 주식/가상화폐 계좌를 대상으로 **자동 거래(자동 매수·매도, 잔고 동기화, 정기 리밸런싱)** 를 수행하는 백그라운드 서비스입니다. 백엔드 API와 동일한 인증/권한 체계를 사용하며, 스케줄러와 브로커별 커넥터를 통해 거래를 실행합니다.

핵심 역할
---------
- 브로커 API 연동: 국내 증권사·거래소 API를 통해 주문/취소/잔고 조회 수행
- 전략 실행: 미리 정의된 전략(예: DCA, 목표 비중 리밸런싱, 손절/익절 트리거) 실행
- 상태 동기화: 실행 결과를 백엔드 `/api/v1`에 기록하여 자산/거래 이력을 일관되게 유지
- 모니터링: 실패/지연/재시도 로그를 수집하고 알림 채널(예: 이메일/텔레그램)로 전송

구성 요소
---------
- **Scheduler**: 주기적 작업(잔고 동기화, 전략 실행) 트리거
- **Broker Connector**: 증권사·거래소별 REST/WebSocket 어댑터
- **Strategy Runner**: 계좌/포트폴리오 단위로 전략을 실행하고 주문을 생성
- **Order Executor**: 주문 생성·체결 확인·취소 처리, 재시도 및 슬리피지 한도 관리
- **State Syncer**: 실행 결과를 백엔드 API(`/api/v1/assets`, `/api/v1/transactions`)와 동기화
- **Alerting**: 오류/지연/한도 초과 시 알림 발송

시나리오
-------

- 잔고 확인
  증권사/거래소 API를 통해 계좌의 잔고와 jsmdb의 잔고와 비교하여 동일한지 확인
  
- 전략 실행
  1. 미체결 거래 취소
  2. 잔고 가져오기(증권사/거래소 API를 통해 계좌의 잔고 가져오기)
  3. 계좌내의 모든 자산에 대해 다음의 과정 수행
    1. 설정된 자산 설정 가져오기
       - 엔드포인트: `GET /assets/{asset_id}` 또는 `GET /assets?account_id={account_id}`
       - 응답에서 `asset_metadata` 필드 확인 (브로커별 거래 설정 포함)
       - 예: `asset_metadata = {"broker": "kiwoom", "account": "12345678", "min_order": 1000}`
    2. 전략 실행
        1. 매수/매도 수량 확정
        2. 거래
        3. 거래 완료 확인
        4. 백엔드 API에 거래 기록: `POST /transactions`

- 가격 업데이트
  거래소/브로커 API에서 실시간 가격 데이터를 수집하여 Redis 캐시 및 백엔드 DB에 업데이트
  - 엔드포인트: `PUT /assets/{asset_id}/price?price=70000&change=2.5`
  - 심볼 기반 업데이트: `PUT /assets/{asset_id}/price?price=70000&change=2.5&use_symbol=true` (동일 심볼의 모든 자산 업데이트)
  - Redis 키: `asset:{asset_id}:current_price`, `asset:{asset_id}:change` 동기화
  - 빈도: 거래시간 중 1-5분마다 (설정 가능)
  - 목적: 프론트엔드 포트폴리오 평가액 실시간 계산, 손절/익절 트리거 판단

환경 변수 예시 (`.env.daemon`)
------------------------------
```
# 백엔드 API
API_BASE_URL=http://localhost:8000/api/v1
API_TOKEN=<service-account-jwt>

# 스케줄러 (APScheduler 기반)
# Cron 형식: 분 시 일 월 요일(0=일, 1=월, ..., 5=금, 6=토)
# 표준 Cron과 동일한 형식을 사용하나, 요일은 0-6 범위만 지원 (표준은 0-7)
SCHEDULE_BALANCE_CRON=0 8 * * 1-5      # 평일(월-금) 08:00 개장 전 잔고 동기화
SCHEDULE_STRATEGY_CRON=*/10 * * * *    # 10분마다 전략 실행
SCHEDULE_PRICE_UPDATE_CRON=*/5 9-15 * * 1-5  # 평일 09:00-16:00 5분마다 가격 업데이트 (거래시간)

# 브로커별 설정 (예시)
BROKER=demo
BROKER_APP_KEY=<app-key>
BROKER_APP_SECRET=<app-secret>
BROKER_ACCOUNT=12345678-01
# 처리 대상 계좌 (백엔드 accounts.id)
ACCOUNT_ID=8623e07e-0edf-4dc4-9ca2-6978acdb7c9f

# 리스크 한도
MAX_ORDER_VALUE_KRW=1000000
SLIPPAGE_BPS=50        # 0.50%
MAX_RETRY=3

# 계좌 설정 캐시 TTL (초)
# broker/main 모두 동일 값 사용, 기본값 600
ACCOUNT_CONFIG_TTL_SEC=600
```

**스케줄러 주의사항**:
- APScheduler는 `max_instances=1`로 설정되어 전략 실행 시간이 스케줄 간격보다 길면 **다음 실행을 스킵**합니다.
- 예: 전략 실행이 12분 소요 → 10분 주기 중 1회 스킵 → 이후 정상화
- 동시 실행을 방지하여 거래 중복 방지 및 상태 일관성 보장

개발 실행 방법
--------------
1. 파이썬 가상환경 활성화 후 의존성 설치
	```bash
	cd daemon
	python -m venv .venv && source .venv/bin/activate
	pip install -r requirements.txt
	```
	**필수 라이브러리**:
	- `apscheduler>=3.10.0` - 스케줄러
	- `requests>=2.31.0` - 백엔드 API 호출
	- `python-dotenv>=1.0.0` - 환경 변수 로드

2. 환경 변수 파일 준비: `.env.daemon` 생성 후 위 예시값을 채웁니다.

3. 로컬 실행
	```bash
	ENV=daemon python main.py
	```

**APScheduler 초기화 예시 코드** (main.py):
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os

scheduler = BackgroundScheduler()

# 잔고 동기화 (평일 08:00)
scheduler.add_job(
    sync_balance,
    CronTrigger.from_crontab(os.getenv("SCHEDULE_BALANCE_CRON")),
    id="balance_sync",
    max_instances=1,  # 중복 실행 방지
    replace_existing=True
)

# 전략 실행 (10분마다)
scheduler.add_job(
    execute_strategy,
    CronTrigger.from_crontab(os.getenv("SCHEDULE_STRATEGY_CRON")),
    id="strategy_runner",
    max_instances=1,  # 중복 실행 방지
    replace_existing=True
)

# 가격 업데이트 (거래시간 중 5분마다)
scheduler.add_job(
    update_asset_prices,
    CronTrigger.from_crontab(os.getenv("SCHEDULE_PRICE_UPDATE_CRON")),
    id="price_updater",
    max_instances=1,  # 중복 실행 방지
    replace_existing=True
)

scheduler.start()
print("Scheduler started...")
```

**가격 업데이트 구현 참고**:
```python
async def update_asset_prices():
    """
    모든 활성 자산의 가격을 거래소 API에서 조회 후 업데이트
    
    처리 흐름:
    1. 활성 자산 목록 조회 (asset_type != CASH, SAVINGS, DEPOSIT)
    2. 각 자산별로 브로커 API에서 현재가 조회
    3. symbol별로 그룹화하여 한 번만 업데이트 (여러 계좌에서 동일 주식 보유 시 효율화)
    4. 백엔드 API PUT /assets/{asset_id}/price에 가격 전송
    5. 실패 시 로그 기록하고 계속 진행 (일부 실패가 전체 실패로 확산되지 않도록)
    
    예시 코드:
    """
    try:
        # 1. 활성 자산 목록 조회 (거래 가능한 자산만)
        assets = api.get("/assets?is_active=true&size=100").json()["items"]
        tradable_assets = [a for a in assets if a["asset_type"] not in ["cash", "savings", "deposit"]]
        
        # 2. symbol별로 그룹화 (효율성)
        symbol_to_assets = {}
        for asset in tradable_assets:
            if asset.get("symbol"):
                symbol = asset["symbol"]
                if symbol not in symbol_to_assets:
                    symbol_to_assets[symbol] = []
                symbol_to_assets[symbol].append(asset)
        
        # 3. 각 심볼별 가격 조회 후 업데이트
        for symbol, assets_group in symbol_to_assets.items():
            try:
                # 거래소 API에서 현재가 조회 (broker connector 활용)
                price_data = broker_connector.get_current_price(symbol)
                price = price_data["price"]
                change = price_data["change_percent"]
                
                # 동일 심볼의 모든 자산에 업데이트 (use_symbol=true)
                api.put(
                    f"/assets/{assets_group[0]['id']}/price",
                    params={
                        "price": price,
                        "change": change,
                        "use_symbol": True  # 동일 심볼의 모든 자산 업데이트
                    }
                )
                logger.info(f"Updated price for {symbol}: {price}")
            except Exception as e:
                logger.error(f"Failed to update price for {symbol}: {str(e)}")
                # 계속 진행 (다른 자산 업데이트에 영향 없음)
    except Exception as e:
        logger.error(f"Price update task failed: {str(e)}")
```

안전 가이드
-----------
- **드라이런**: 실제 주문 전 `dry_run=true` 옵션으로 전략 출력을 검증하십시오.
- **주문 한도**: `MAX_ORDER_VALUE_KRW`, `SLIPPAGE_BPS` 같은 리스크 한도를 반드시 설정하십시오.
- **API 키 보호**: 키/토큰은 `.env.daemon` 등 비공개 파일에만 저장하고 저장소에 커밋하지 않습니다.
- **로그 확인**: 비정상 응답, 체결 지연, 재시도 발생 시 로그와 알림 채널을 확인해 장애를 조치합니다.

오류 처리 및 재시도
-------------------
- **네트워크 실패**: 거래소 API 접근 불가 시 지수 백오프 재시도 (최대 `MAX_RETRY` 회)
- **체결 실패/체결 불가**: 주문이 거부되거나 체결되지 않으면 로그 기록 + 알림 후 다음 사이클에서 재평가
- **동기화 실패**: 백엔드 API 연결 실패 시 로컬 큐에 임시 저장 후 재시도
- **부분 체결**: 요청 수량의 일부만 체결된 경우 실제 체결 수량을 기록

상태 관리 및 체크포인트
----------------------
- daemon 프로세스 시작/종료 시 실행 중인 거래 상태 확인
- 장시간 미체결 거래는 주기적으로 폴링(2-3시간마다 취소 여부 판단)
- 백엔드 DB에 daemon 실행 로그를 기록하여 감사(audit) 가능하게 함

백엔드 API 통합 예시
-------------------

### 자산 상세 조회 (asset_metadata 포함)
```bash
GET /assets/{asset_id}
Authorization: Bearer <jwt_token>
```

**응답 예시**:
```json
{
  "id": "asset-uuid-1",
  "user_id": "user-uuid-1",
  "account_id": "account-uuid-1",
  "name": "삼성전자",
  "asset_type": "stock",
  "symbol": "005930",
  "currency": "KRW",
  "asset_metadata": {
    "broker": "kiwoom",
    "broker_code": "NH",
    "account_number": "12345678",
    "min_order_quantity": 1,
    "order_type": "limit",
    "trading_enabled": true
  },
  "is_active": true,
  "balance": 100.0,
  "price": 70000.0,
  "change": 2.5,
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-08T14:30:00Z",
  "account": {
    "id": "account-uuid-1",
    "name": "NH투자증권 주식계좌",
    "account_type": "brokerage"
  }
}
```

### 자산 목록 조회 (특정 계좌의 모든 자산)
```bash
GET /assets?account_id={account_id}&page=1&size=100
Authorization: Bearer <jwt_token>
```

**응답 예시**:
```json
{
  "items": [
    {
      "id": "asset-uuid-1",
      "name": "삼성전자",
      "asset_type": "stock",
      "symbol": "005930",
      "asset_metadata": { "broker": "kiwoom", "account_number": "12345678" },
      "balance": 100.0,
      "price": 70000.0,
      ...
    },
    {
      "id": "asset-uuid-2",
      "name": "비트코인",
      "asset_type": "crypto",
      "symbol": "BTC",
      "asset_metadata": { "exchange": "upbit", "withdrawal_enabled": true },
      "balance": 0.05,
      "price": 45000000.0,
      ...
    }
  ],
  "total": 2,
  "page": 1,
  "size": 100,
  "pages": 1
}
```

### 거래 기록 추가
```bash
POST /transactions
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "asset_id": "asset-uuid-1",
  "type": "buy",
  "quantity": 10.0,
  "price": 70000.0,
  "transaction_date": "2025-12-08T14:30:00Z",
  "category_id": "category-uuid-for-investment",
  "flow_type": "investment",
  "confirmed": true,
  "extras": {
    "broker_order_id": "ORD12345",
    "settlement_date": "2025-12-10"
  }
}
```

### 자산 가격 업데이트
```bash
# 개별 자산 가격 업데이트
PUT /assets/{asset_id}/price?price=70000&change=2.5
Authorization: Bearer <jwt_token>

# 심볼 기반 업데이트 (동일 심볼의 모든 자산에 적용, 예: 동일 주식을 여러 계좌에서 보유 시)
PUT /assets/{asset_id}/price?price=70000&change=2.5&use_symbol=true
Authorization: Bearer <jwt_token>
```

**응답 예시**:
```json
{
  "message": "가격이 업데이트되었습니다",
  "asset_id": "asset-uuid-1",
  "symbol": "005930",
  "price": 70000.0,
  "change": 2.5,
  "use_symbol": false
}
```

**Redis 반영**:
- `asset:{asset_id}:current_price` → `"70000"`
- `asset:{asset_id}:change` → `"2.5"`
- `use_symbol=true` 시 동일 symbol을 가진 모든 자산 업데이트

브로커 통합 가이드
-----------------
각 브로커별 커넥터는 다음을 구현해야 합니다:
```python
# 예시 인터페이스
class BrokerConnector:
    def get_balance(self) -> Dict[str, float]:
        """현재 계좌 잔고 조회"""
        pass
    
    def get_pending_orders(self) -> List[Order]:
        """미체결 주문 목록"""
        pass
    
    def place_order(self, symbol: str, side: str, qty: float, price: float = None) -> Order:
        """주문 접수"""
        pass
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        pass
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """주문 상태 확인"""
        pass
```

전략 템플릿 예시
----------------
### 1. DCA (Dollar-Cost Averaging)
- 매월 정해진 금액으로 자산 매수
- 가격 변동성과 무관하게 정기적으로 투자

### 2. 목표 비중 유지 (Rebalancing)
- 포트폴리오의 자산별 목표 비중(예: 주식 60%, 암호화폐 30%, 현금 10%) 설정
- 실제 비중이 목표에서 벗어나면(오차 ±5%) 자동 리밸런싱

### 3. 손절/익절
- 특정 자산의 손실률/수익률 도달 시 자동 매도
- 예: -10% 손절, +20% 익절

모니터링 대시보드 항목
---------------------
- 최근 실행 시간, 다음 예약 실행 시간
- 최근 거래 이력 (일자, 자산, 수량, 금액, 상태)
- 오류 로그 및 경고 (재시도 횟수, 실패 사유)
- 포트폴리오 현황 (자산별 보유 수량, 평가액)

로드맵 (초안)
-------------
- 브로커 커넥터 다중화: 국내 증권사/거래소 커넥터 추가
- 전략 템플릿: DCA, 목표 비중 리밸런싱, 손절/익절 트리거 기본 제공
- 백테스트/시뮬레이션: 동일 전략의 과거 데이터 검증 지원
- 웹훅 알림: 체결/실패/한도 초과 이벤트를 텔레그램/슬랙으로 발송
