"""
Account schemas for request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum


class AccountType(str, Enum):
    """계좌 유형 Enum"""
    BANK_ACCOUNT = "bank_account"      # 은행계좌
    SECURITIES = "securities"          # 증권계좌
    CASH = "cash"                      # 현금
    DEBIT_CARD = "debit_card"         # 체크카드
    CREDIT_CARD = "credit_card"       # 신용카드
    SAVINGS = "savings"                # 저축예금
    DEPOSIT = "deposit"                # 적금
    CRYPTO_WALLET = "crypto_wallet"   # 가상화폐 지갑


class ShareRole(str, Enum):
    """공유 역할"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class AccountBase(BaseModel):
    """계좌 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=100, description="계좌명")
    account_type: AccountType = Field(..., description="계좌 유형")
    provider: Optional[str] = Field(None, max_length=100, description="금융기관/거래소명")
    account_number: Optional[str] = Field(None, max_length=50, description="계좌번호")
    currency: str = Field(default="KRW", max_length=3, description="통화 코드 (ISO 4217)")
    is_active: bool = Field(default=True, description="활성화 상태")
    api_config: Optional[dict] = Field(None, description="API 연동 설정")
    daemon_config: Optional[dict] = Field(None, description="Daemon 설정")


class AccountCreate(AccountBase):
    """계좌 생성 요청"""
    pass


class AccountUpdate(BaseModel):
    """계좌 수정 요청 (모든 필드 선택적)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="계좌명")
    account_type: Optional[AccountType] = Field(None, description="계좌 유형")
    provider: Optional[str] = Field(None, max_length=100, description="금융기관/거래소명")
    account_number: Optional[str] = Field(None, max_length=50, description="계좌번호")
    currency: Optional[str] = Field(None, max_length=3, description="통화 코드")
    is_active: Optional[bool] = Field(None, description="활성화 상태")
    api_config: Optional[dict] = Field(None, description="API 연동 설정")
    daemon_config: Optional[dict] = Field(None, description="Daemon 설정")


class AccountInDB(AccountBase):
    """DB에 저장된 계좌 (내부용)"""
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountResponse(AccountInDB):
    """계좌 응답 (API 반환용)"""
    pass


class AccountListResponse(BaseModel):
    """계좌 목록 응답"""
    total: int
    accounts: list[AccountResponse]


# ==================== 계좌 공유 스키마 ====================

class AccountShareCreate(BaseModel):
    """계좌 공유 생성 요청"""
    user_email: str = Field(..., description="공유할 사용자의 이메일")
    role: ShareRole = Field(default=ShareRole.VIEWER, description="공유 역할")
    
    @field_validator('user_email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('유효한 이메일 주소를 입력하세요')
        return v.lower()


class AccountShareUpdate(BaseModel):
    """계좌 공유 수정 요청"""
    role: Optional[ShareRole] = Field(None, description="공유 역할")
    can_read: Optional[bool] = Field(None, description="읽기 권한")
    can_write: Optional[bool] = Field(None, description="쓰기 권한")
    can_delete: Optional[bool] = Field(None, description="삭제 권한")
    can_share: Optional[bool] = Field(None, description="공유 권한")


class AccountShareResponse(BaseModel):
    """계좌 공유 응답"""
    id: str
    account_id: str
    user_id: str
    role: str
    can_read: bool
    can_write: bool
    can_delete: bool
    can_share: bool
    shared_at: datetime
    shared_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AccountShareListResponse(BaseModel):
    """계좌 공유 목록 응답"""
    total: int
    shares: list[AccountShareResponse]
