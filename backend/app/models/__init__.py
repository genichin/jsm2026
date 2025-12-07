"""
SQLAlchemy models for J's Money
Based on docs/database-schema.md
"""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text, Date, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from enum import Enum
import uuid



def generate_uuid():
    """Generate UUID for primary keys"""
    return str(uuid.uuid4())


class AccountType(str, Enum):
    """계좌 유형 Enum"""
    BANK_ACCOUNT = "bank_account"      # 은행계좌
    SECURITIES = "securities"          # 증권계좌
    CASH = "cash"                      # 현금
    DEBIT_CARD = "debit_card"         # 체크카드
    CREDIT_CARD = "credit_card"       # 신용카드 (부채)
    SAVINGS = "savings"                # 저축예금
    DEPOSIT = "deposit"                # 적금
    CRYPTO_WALLET = "crypto_wallet"   # 가상화폐 지갑


# 유형별 속성 매핑
ACCOUNT_TYPE_INFO = {
    AccountType.BANK_ACCOUNT: {"name": "은행계좌", "is_asset": True},
    AccountType.SECURITIES: {"name": "증권계좌", "is_asset": True},
    AccountType.CASH: {"name": "현금", "is_asset": True},
    AccountType.DEBIT_CARD: {"name": "체크카드", "is_asset": True},
    AccountType.CREDIT_CARD: {"name": "신용카드", "is_asset": False},
    AccountType.SAVINGS: {"name": "저축예금", "is_asset": True},
    AccountType.DEPOSIT: {"name": "적금", "is_asset": True},
    AccountType.CRYPTO_WALLET: {"name": "가상화폐지갑", "is_asset": True},
}


class User(Base):
    """사용자 계정"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = ()

    # Relationships
    owned_accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Account.owner_id")
    shared_accounts = relationship("AccountShare", back_populates="user", cascade="all, delete-orphan", foreign_keys="AccountShare.user_id")
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    """계좌"""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_type = Column(String(50), nullable=False)  # AccountType Enum 값
    name = Column(String(100), nullable=False)
    provider = Column(String(100))
    account_number = Column(String(50))
    currency = Column(String(3), nullable=False, default="KRW")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # API and Daemon configuration (JSONB for flexibility)
    api_config = Column(JSONB)  # API credentials and settings
    daemon_config = Column(JSONB)  # Daemon-specific settings
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('bank_account', 'securities', 'cash', 'debit_card', 'credit_card', 'savings', 'deposit', 'crypto_wallet')",
            name='valid_account_type'
        ),
    )

    # Relationships
    owner = relationship("User", back_populates="owned_accounts", foreign_keys=[owner_id])
    shares = relationship("AccountShare", back_populates="account", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="account", cascade="all, delete-orphan")


class AccountShare(Base):
    """계좌 공유 (Many-to-Many)"""
    __tablename__ = "account_shares"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 역할 및 권한
    role = Column(String(20), nullable=False, default='viewer')
    can_read = Column(Boolean, nullable=False, default=True)
    can_write = Column(Boolean, nullable=False, default=False)
    can_delete = Column(Boolean, nullable=False, default=False)
    can_share = Column(Boolean, nullable=False, default=False)
    
    # 공유 메타데이터
    shared_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    shared_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('account_id', 'user_id', name='uq_account_user_share'),
        CheckConstraint("role IN ('owner', 'editor', 'viewer')", name='check_role'),
    )

    # Relationships
    account = relationship("Account", back_populates="shares")
    user = relationship("User", back_populates="shared_accounts", foreign_keys=[user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by])


class Category(Base):
    """카테고리 (사용자별, 계층 지원)"""
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    parent_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))
    flow_type = Column(String(20), nullable=False)  # expense, income, transfer, investment, neutral
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "flow_type IN ('expense','income','transfer','investment','neutral')",
            name='check_category_flow_type'
        ),
        UniqueConstraint('user_id', 'name', 'parent_id', name='uq_categories_per_user')
    )

    # Relationships
    children = relationship("Category", remote_side=[id])
    transactions = relationship("Transaction", back_populates="category")
    auto_rules = relationship("CategoryAutoRule", back_populates="category", cascade="all, delete-orphan")


class AssetType(str, Enum):
    """자산 유형 Enum"""
    STOCK = "stock"        # 주식
    CRYPTO = "crypto"      # 가상화폐
    BOND = "bond"          # 채권
    FUND = "fund"          # 펀드
    ETF = "etf"            # ETF
    CASH = "cash"          # 현금 (예수금, 잔고 등)
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


# 유형별 속성 매핑
ASSET_TYPE_INFO = {
    AssetType.STOCK: {"name": "주식", "tradable": True},
    AssetType.CRYPTO: {"name": "가상화폐", "tradable": True},
    AssetType.BOND: {"name": "채권", "tradable": True},
    AssetType.FUND: {"name": "펀드", "tradable": True},
    AssetType.ETF: {"name": "ETF", "tradable": True},
    AssetType.CASH: {"name": "현금", "tradable": False},
}


class Asset(Base):
    """자산"""
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 자산 기본 정보
    name = Column(String(100), nullable=False)         # 사용자 지정 이름
    asset_type = Column(String(50), nullable=False)    # AssetType Enum 값
    symbol = Column(String(20))                        # 거래 심볼
    
    # 메타데이터
    currency = Column(String(3), nullable=False, default='KRW')  # 기준 통화
    asset_metadata = Column(JSONB)                     # 추가 정보
    
    # 상태
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('stock', 'crypto', 'bond', 'fund', 'etf', 'cash')",
            name='valid_asset_type'
        ),
    )

    # Relationships
    user = relationship("User", back_populates="assets")
    account = relationship("Account", back_populates="assets")
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")


class Transaction(Base):
    """거래 (transactions)"""
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # TransactionType enum 값
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))
    quantity = Column(Numeric(20, 8), nullable=False)  # 양수=증가, 음수=감소, 0=마커
    extras = Column(JSONB)  # 추가 정보: price, fee, tax, rate, balance_after, realized_profit 등
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text)
    memo = Column(Text)
    related_transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"))
    confirmed = Column(Boolean, nullable=False, server_default='false')  # 사용자 확인 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "type IN ('buy', 'sell', 'deposit', 'withdraw', 'cash_dividend', 'stock_dividend', 'interest', 'fee', "
            "'transfer_in', 'transfer_out', 'adjustment', 'invest', 'redeem', "
            "'internal_transfer', 'card_payment', 'promotion_deposit', 'auto_transfer', 'remittance', 'exchange', "
            "'out_asset', 'in_asset')",
            name='valid_transaction_type'
        ),
    )

    # Relationships
    asset = relationship("Asset", back_populates="transactions")
    related_transaction = relationship("Transaction", remote_side=[id])
    category = relationship("Category", back_populates="transactions")


class CategoryAutoRule(Base):
    """카테고리 자동 분류 규칙
    설명/메모 문자열을 기반으로 트랜잭션 생성 시 카테고리 자동 지정.
    pattern_type: exact / contains / regex
    priority: 낮을수록 먼저 적용
    """
    __tablename__ = "category_auto_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern_type = Column(String(20), nullable=False)
    pattern_text = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("pattern_type IN ('exact','contains','regex')", name='check_auto_rule_pattern_type'),
        UniqueConstraint('user_id','pattern_type','pattern_text', name='uq_auto_rule_unique_per_user'),
    )

    category = relationship("Category", back_populates="auto_rules")


class TaggableType(str, Enum):
    """태그 가능한 엔티티 타입"""
    ASSET = "asset"
    ACCOUNT = "account"
    TRANSACTION = "transaction"


class Tag(Base):
    """태그 정의"""
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 태그 정보
    name = Column(String(50), nullable=False)
    color = Column(String(7))  # 색상 코드 (예: #FF5733)
    description = Column(Text)
    
    # 엔티티 타입 제약 (옵션)
    allowed_types = Column(JSONB, server_default='["asset", "account", "transaction"]')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_tag_per_user'),
    )

    # Relationships
    taggables = relationship("Taggable", back_populates="tag", cascade="all, delete-orphan")


class Taggable(Base):
    """태그 연결 (Polymorphic Many-to-Many)"""
    __tablename__ = "taggables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Polymorphic 연결
    taggable_type = Column(String(20), nullable=False)  # 'asset', 'account', 'transaction'
    taggable_id = Column(String(36), nullable=False)    # 해당 엔티티의 ID
    
    # 메타데이터
    tagged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tagged_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('tag_id', 'taggable_type', 'taggable_id', name='uq_tag_entity'),
        CheckConstraint("taggable_type IN ('asset', 'account', 'transaction')", name='check_taggable_type'),
    )

    # Relationships
    tag = relationship("Tag", back_populates="taggables")
    tagged_by_user = relationship("User", foreign_keys=[tagged_by])


class RemindableType(str, Enum):
    """알림 대상 엔티티 타입"""
    ASSET = "asset"
    ACCOUNT = "account"
    TRANSACTION = "transaction"


class TargetType(str, Enum):
    """활동 대상 엔티티 타입 (댓글/로그 공통)"""
    ASSET = "asset"
    ACCOUNT = "account"
    TRANSACTION = "transaction"


class ActivityType(str, Enum):
    """활동 유형"""
    COMMENT = "comment"
    LOG = "log"


class Activity(Base):
    """활동 (댓글 + 로그)
    단일 Polymorphic 테이블.
    댓글은 content 사용, 로그는 payload(JSONB) 사용 권장.
    """
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Polymorphic 대상
    target_type = Column(String(20), nullable=False)  # 'asset','account','transaction'
    target_id = Column(String(36), nullable=False)

    # 유형/내용
    activity_type = Column(String(20), nullable=False)
    content = Column(Text)                # 댓글 본문
    payload = Column(JSONB)               # 로그 데이터

    # 스레드
    parent_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"))
    thread_root_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"))

    # 정책/플래그
    visibility = Column(String(20), nullable=False, server_default='private')  # private/shared/public
    is_immutable = Column(Boolean, nullable=False, server_default='false')
    is_deleted = Column(Boolean, nullable=False, server_default='false')
    deleted_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("target_type IN ('asset','account','transaction')", name='check_target_type'),
        CheckConstraint("activity_type IN ('comment','log')", name='check_activity_type'),
        CheckConstraint("visibility IN ('private','shared','public')", name='check_visibility'),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    parent = relationship("Activity", remote_side=[id], foreign_keys=[parent_id])
    thread_root = relationship("Activity", remote_side=[id], foreign_keys=[thread_root_id])

class ReminderType(str, Enum):
    """알림 유형"""
    REVIEW = "review"          # 검토
    DIVIDEND = "dividend"      # 배당
    REBALANCE = "rebalance"    # 리밸런싱
    DEADLINE = "deadline"      # 마감일
    CUSTOM = "custom"          # 커스텀


class RepeatInterval(str, Enum):
    """반복 주기"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Reminder(Base):
    """알림"""
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Polymorphic 연결
    remindable_type = Column(String(20), nullable=False)  # 'asset', 'account', 'transaction'
    remindable_id = Column(String(36), nullable=False)    # 해당 엔티티의 ID
    
    # 알림 유형 및 내용
    reminder_type = Column(String(20), nullable=False, server_default='review')
    title = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 시간 설정
    remind_at = Column(DateTime(timezone=True), nullable=False)
    repeat_interval = Column(String(20))  # 'daily', 'weekly', 'monthly', 'yearly', null
    
    # 우선순위
    priority = Column(Integer, nullable=False, server_default='0')
    
    # 상태 관리
    is_active = Column(Boolean, nullable=False, server_default='true')
    is_dismissed = Column(Boolean, nullable=False, server_default='false')
    dismissed_at = Column(DateTime(timezone=True))
    snoozed_until = Column(DateTime(timezone=True))
    last_notified_at = Column(DateTime(timezone=True))
    
    # 자동 완료 설정
    auto_complete_on_view = Column(Boolean, nullable=False, server_default='false')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("remindable_type IN ('asset', 'account', 'transaction')", name='check_remindable_type'),
        CheckConstraint("reminder_type IN ('review', 'dividend', 'rebalance', 'deadline', 'custom')", name='check_reminder_type'),
        CheckConstraint("repeat_interval IS NULL OR repeat_interval IN ('daily', 'weekly', 'monthly', 'yearly')", name='check_repeat_interval'),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

