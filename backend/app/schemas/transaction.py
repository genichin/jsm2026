"""
Pydantic schemas for transactions and assets
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from enum import Enum
from app.schemas.account import AccountType as AccountTypeSchema


class AssetType(str, Enum):
    """자산 유형 Enum"""
    STOCK = "stock"
    CRYPTO = "crypto"
    BOND = "bond"
    FUND = "fund"
    ETF = "etf"
    CASH = "cash"
    SAVINGS = "savings"    # 예금
    DEPOSIT = "deposit"    # 적금


class TransactionType(str, Enum):
    """거래 유형"""
    BUY = "buy"               # 매수
    SELL = "sell"             # 매도
    DEPOSIT = "deposit"       # 입금
    WITHDRAW = "withdraw"     # 출금
    CASH_DIVIDEND = "cash_dividend"     # 현금배당
    STOCK_DIVIDEND = "stock_dividend"   # 주식배당
    INTEREST = "interest"     # 이자
    FEE = "fee"              # 수수료
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
    OUT_ASSET = "out_asset"   # 자산매수출금
    IN_ASSET = "in_asset"     # 자산매도입금
    PAYMENT_CANCEL = "payment_cancel"  # 결제취소


class FlowType(str, Enum):
    """거래 흐름 타입"""
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    INVESTMENT = "investment"
    NEUTRAL = "neutral"
    UNDEFINED = "undefined"


# Asset Schemas
class AssetBase(BaseModel):
    """자산 기본 스키마"""
    name: str = Field(..., max_length=100, description="사용자 지정 자산 이름")
    asset_type: AssetType = Field(..., description="자산 유형")
    symbol: Optional[str] = Field(None, max_length=20, description="거래 심볼")
    market: Optional[str] = Field(None, max_length=20, description="거래소 (KOSPI, KOSDAQ, KRW, 등)")
    currency: str = Field(default="KRW", max_length=3, description="기준 통화")
    asset_metadata: Optional[dict] = Field(None, description="추가 메타데이터")
    is_active: bool = Field(default=True, description="활성 상태")
    review_interval_days: Optional[int] = Field(30, ge=1, le=365, description="검토 주기 (일)")


class AssetCreate(AssetBase):
    """자산 생성 요청"""
    account_id: str = Field(..., description="계좌 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "account_id": "account-uuid-here",
                    "name": "삼성전자",
                    "asset_type": "stock",
                    "symbol": "005930",
                    "currency": "KRW",
                    "asset_metadata": {"market": "KOSPI", "isin": "KR7005930003"}
                }
            ]
        }
    }


class AssetUpdate(BaseModel):
    """자산 업데이트 요청"""
    name: Optional[str] = Field(None, max_length=100)
    symbol: Optional[str] = Field(None, max_length=20)
    market: Optional[str] = Field(None, max_length=20, description="거래소 (KOSPI, KOSDAQ, KRW, 등)")
    currency: Optional[str] = Field(None, max_length=3, description="기준 통화")
    asset_metadata: Optional[dict] = None
    is_active: Optional[bool] = None
    review_interval_days: Optional[int] = Field(None, ge=1, le=365, description="검토 주기 (일)")


class AssetResponse(AssetBase):
    """자산 응답"""
    id: str
    user_id: str
    account_id: str
    created_at: datetime
    updated_at: datetime
    last_reviewed_at: Optional[datetime] = Field(None, description="마지막 검토 일시")
    next_review_date: Optional[datetime] = Field(None, description="다음 검토 예정일")
    balance: Optional[float] = Field(None, description="현재 보유 수량 (Redis)")
    price: Optional[float] = Field(None, description="현재 가격 (Redis)")
    change: Optional[float] = Field(None, description="가격 변화량 퍼센트 (Redis)")
    
    class NeedTrade(BaseModel):
        price: Optional[float] = None
        quantity: Optional[float] = None
        ttl: Optional[int] = None

    need_trade: Optional[NeedTrade] = Field(None, description="수동 거래 필요 정보 (Redis, TTL 포함)")
    
    # Nested, lightweight account info for convenience in detail/list views
    class AccountBrief(BaseModel):
        id: str
        name: str
        account_type: AccountTypeSchema

    account: Optional[AccountBrief] = Field(None, description="간단한 계좌 정보")

    model_config = {
        "from_attributes": True
    }


# Transaction Schemas
class TransactionBase(BaseModel):
    """거래 기본 스키마"""
    type: TransactionType = Field(..., description="거래 유형")
    category_id: Optional[str] = Field(None, description="카테고리 ID")
    quantity: float = Field(..., description="수량 변화 (양수=증가, 음수=감소)")
    price: Optional[float] = Field(None, description="거래 단가")
    fee: Optional[float] = Field(None, ge=0, description="수수료 (음수 불가)")
    tax: Optional[float] = Field(None, ge=0, description="세금 (음수 불가)")
    realized_profit: Optional[float] = Field(None, description="실현 손익")
    extras: Optional[dict] = Field(None, description="추가 정보 (price, fee, tax, rate, balance_after 등)")
    transaction_date: datetime = Field(..., description="거래 일시")
    description: Optional[str] = Field(None, description="거래 설명")
    memo: Optional[str] = Field(None, description="사용자 메모")
    flow_type: FlowType = Field(default=FlowType.UNDEFINED, description="거래 흐름 타입")

    model_config = {
        "from_attributes": True
    }


class TransactionCreate(TransactionBase):
    """거래 생성 요청"""
    asset_id: str = Field(..., description="자산 ID")
    related_transaction_id: Optional[str] = Field(None, description="관련 거래 ID (복식부기)")
    cash_asset_id: Optional[str] = Field(None, description="매수/매도 시 사용할 현금 자산 ID (지정하지 않으면 자동 선택)")
    skip_auto_cash_transaction: bool = Field(False, description="매수/매도 시 현금 거래 자동 생성 건너뛰기 (out_asset/in_asset 수동 생성용)")
    # 환전(exchange) 거래용 필드
    target_asset_id: Optional[str] = Field(None, description="환전 대상 자산 ID (type=exchange일 때)")
    target_amount: Optional[float] = Field(None, description="환전 대상 금액 (type=exchange일 때)")

    @model_validator(mode='after')
    def validate_type_quantity_consistency(self):
        """거래 타입과 수량 방향 일관성 검증"""
        extras_dict = self.extras or {}
        # extras 기반 값 채우기
        if self.price is None and extras_dict.get("price") is not None:
            try:
                self.price = float(extras_dict.get("price"))
            except (TypeError, ValueError):
                raise ValueError("price는 숫자여야 합니다.")
        if self.fee is None and extras_dict.get("fee") is not None:
            try:
                self.fee = float(extras_dict.get("fee"))
            except (TypeError, ValueError):
                raise ValueError("fee는 숫자여야 합니다.")
        if self.tax is None and extras_dict.get("tax") is not None:
            try:
                self.tax = float(extras_dict.get("tax"))
            except (TypeError, ValueError):
                raise ValueError("tax는 숫자여야 합니다.")
        if self.realized_profit is None and extras_dict.get("realized_profit") is not None:
            try:
                self.realized_profit = float(extras_dict.get("realized_profit"))
            except (TypeError, ValueError):
                raise ValueError("realized_profit는 숫자여야 합니다.")
        if self.type == TransactionType.BUY:
            if self.quantity <= 0:
                raise ValueError("매수(BUY) 거래의 수량은 양수여야 합니다.")
        elif self.type == TransactionType.SELL:
            if self.quantity >= 0:
                raise ValueError("매도(SELL) 거래의 수량은 음수여야 합니다.")
        elif self.type == TransactionType.DEPOSIT:
            if self.quantity <= 0:
                raise ValueError("입금(DEPOSIT) 거래의 수량은 양수여야 합니다.")
        elif self.type == TransactionType.WITHDRAW:
            if self.quantity >= 0:
                raise ValueError("출금(WITHDRAW) 거래의 수량은 음수여야 합니다.")
        elif self.type == TransactionType.TRANSFER_IN:
            if self.quantity <= 0:
                raise ValueError("이체 입금(TRANSFER_IN) 거래의 수량은 양수여야 합니다.")
        elif self.type == TransactionType.TRANSFER_OUT:
            if self.quantity >= 0:
                raise ValueError("이체 출금(TRANSFER_OUT) 거래의 수량은 음수여야 합니다.")
        # 배당: 현금배당은 수량=0(마커), 주식배당은 양수
        elif self.type == TransactionType.CASH_DIVIDEND:
            if self.quantity <= 0:
                raise ValueError("현금배당(CASH_DIVIDEND)은 수량이 양수여야 합니다.")
        elif self.type == TransactionType.STOCK_DIVIDEND:
            if self.quantity <= 0:
                raise ValueError("주식배당(STOCK_DIVIDEND)은 수량이 양수여야 합니다.")
        elif self.type == TransactionType.INTEREST:
            if self.quantity <= 0:
                raise ValueError("이자(INTEREST) 거래의 수량은 양수여야 합니다.")
        elif self.type == TransactionType.FEE:
            if self.quantity >= 0:
                raise ValueError("수수료(FEE) 거래의 수량은 음수여야 합니다.")
        elif self.type == TransactionType.OUT_ASSET:
            if self.quantity >= 0:
                raise ValueError("자산매수출금(OUT_ASSET) 거래의 수량은 음수여야 합니다.")
        elif self.type == TransactionType.IN_ASSET:
            if self.quantity <= 0:
                raise ValueError("자산매도입금(IN_ASSET) 거래의 수량은 양수여야 합니다.")
        elif self.type == TransactionType.PAYMENT_CANCEL:
            if self.quantity <= 0:
                raise ValueError("결제취소(PAYMENT_CANCEL) 거래의 수량은 양수여야 합니다.")
        # ADJUSTMENT는 양수/음수 모두 허용 (수량 조정)

        # 가격 필수/부호 검증
        if self.price is not None and self.price < 0:
            raise ValueError("price는 0 이상이어야 합니다.")
        if self.fee is not None and self.fee < 0:
            raise ValueError("fee는 0 이상이어야 합니다.")
        if self.tax is not None and self.tax < 0:
            raise ValueError("tax는 0 이상이어야 합니다.")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "asset_id": "asset-uuid-here",
                    "type": "buy",
                    "quantity": "100.00000000",
                    "price": "67000.00",
                    "fee": "3350.00",
                    "tax": "0.00",
                    "realized_profit": "-3350.00",
                    "transaction_date": "2024-01-15T09:30:00Z",
                    "description": "삼성전자 100주 매수",
                    "memo": "첫 번째 매수"
                }
            ]
        }
    }


class TransactionUpdate(BaseModel):
    """거래 업데이트 요청"""
    type: Optional[TransactionType] = Field(None, description="거래 유형 (수정 가능)")
    quantity: Optional[float] = Field(None, description="수량 변화 (수정 가능)")
    description: Optional[str] = None
    memo: Optional[str] = None
    flow_type: Optional[FlowType] = Field(None, description="거래 흐름 타입")
    transaction_date: Optional[datetime] = Field(None, description="거래 일시 (수정 가능)")
    extras: Optional[dict] = Field(None, description="추가 정보 (예: 환율, 외부 시스템 데이터 등)")
    category_id: Optional[str] = Field(None, description="카테고리 ID (변경/해제)")
    related_transaction_id: Optional[str] = Field(None, description="연결된 거래 ID (변경/해제)")


class TransactionResponse(TransactionBase):
    """거래 응답"""
    id: str
    asset_id: str
    related_transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    category_id: Optional[str] = Field(None, description="카테고리 ID")
    confirmed: bool = Field(False, description="확정 여부")
    price: Optional[float] = None
    fee: Optional[float] = None
    tax: Optional[float] = None
    realized_profit: Optional[float] = None

    # 선택: 응답에 카테고리 요약 포함
    category: Optional[dict] = None  # {id, name, flow_type}

    model_config = {
        "from_attributes": True
    }


class TransactionWithAsset(TransactionResponse):
    """자산 정보 포함 거래 응답"""
    asset: Optional[dict] = None  # Temporarily use dict instead of AssetResponse
    related_asset_name: Optional[str] = Field(None, description="연결된 거래의 자산명 (out_asset/in_asset용)")
    category_id: Optional[str] = Field(None, description="카테고리 ID")

    model_config = {
        "from_attributes": True
    }


# List Schemas
class AssetListResponse(BaseModel):
    """자산 목록 응답"""
    items: List[AssetResponse]
    total: int
    page: int
    size: int
    pages: int


class TransactionListResponse(BaseModel):
    """거래 목록 응답"""
    items: List[TransactionWithAsset]
    total: int
    page: int
    size: int
    pages: int


# Query Schemas
class AssetFilter(BaseModel):
    """자산 필터"""
    account_id: Optional[str] = None
    asset_type: Optional[AssetType] = None
    is_active: Optional[bool] = None
    symbol: Optional[str] = None


class TransactionFilter(BaseModel):
    """거래 필터"""
    asset_id: Optional[str] = None
    account_id: Optional[str] = None
    type: Optional[TransactionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    flow_type: Optional[FlowType] = Field(None, description="거래 흐름 타입 필터")
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    category_id: Optional[str] = None


# Summary Schemas
class AssetSummary(BaseModel):
    """자산 요약"""
    asset_id: str
    asset_name: str
    asset_type: AssetType
    symbol: Optional[str] = None
    current_quantity: Decimal
    total_cost: Decimal
    realized_profit: Decimal
    unrealized_profit: Optional[Decimal] = None
    # 통화별 평가액 (KRW 외 통화일 때 사용)
    foreign_value: Optional[Decimal] = None
    foreign_currency: Optional[str] = None
    krw_value: Optional[Decimal] = None


class PortfolioSummary(BaseModel):
    """포트폴리오 요약"""
    total_assets_value: Decimal
    total_cash: Decimal
    total_realized_profit: Decimal
    total_unrealized_profit: Decimal
    asset_summaries: List[AssetSummary]


# Bulk Operation Schemas
class BulkTransactionCreate(BaseModel):
    """대량 거래 생성 요청"""
    transactions: List[TransactionCreate]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transactions": [
                        {
                            "asset_id": "cash-asset-id",
                            "type": "exchange",
                            "quantity": "-6703350.00",
                            "price": "1.00",
                            "fee": "0.00",
                            "transaction_date": "2024-01-15T09:30:00Z",
                            "description": "삼성전자 매수 - 현금 출금"
                        },
                        {
                            "asset_id": "stock-asset-id", 
                            "type": "exchange",
                            "quantity": "100.00000000",
                            "price": "67000.00",
                            "fee": "3350.00",
                            "realized_profit": "-3350.00",
                            "transaction_date": "2024-01-15T09:30:00Z",
                            "description": "삼성전자 100주 매수"
                        }
                    ]
                }
            ]
        }
    }


class BulkTransactionResponse(BaseModel):
    """대량 거래 생성 응답"""
    created_count: int
    transactions: List[TransactionResponse]
    errors: List[str] = []


class ExchangeCreate(BaseModel):
    """환전 거래 생성 요청 (쌍 레코드 생성)"""
    source_asset_id: str = Field(..., description="출발 자산 ID (현금, 수량은 감소)")
    target_asset_id: str = Field(..., description="도착 자산 ID (현금, 수량은 증가)")
    source_amount: float = Field(..., gt=0, description="출발 통화 금액 (양수) → 내부적으로 음수 반영")
    target_amount: float = Field(..., gt=0, description="도착 통화 금액 (양수)")
    fee: float = Field(default=0.0, ge=0, description="환전 수수료 (출발 거래의 fee에 기록)")
    transaction_date: datetime = Field(..., description="거래 일시")
    description: Optional[str] = Field(None, description="설명")
    memo: Optional[str] = Field(None, description="메모")
    flow_type: FlowType = Field(default=FlowType.TRANSFER, description="거래 흐름 타입")
    external_id: Optional[str] = Field(None, max_length=100, description="외부 ID")


class FileUploadError(BaseModel):
    """파일 업로드 오류 정보"""
    row: int
    error: str
    data: Optional[dict] = None


class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    success: bool
    total: int
    created: int
    skipped: int
    failed: int
    errors: List[FileUploadError] = []
    preview: Optional[List[dict]] = None  # dry_run일 때만
    transactions: Optional[List[TransactionResponse]] = None  # 실제 생성 시
