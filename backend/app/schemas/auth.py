"""
Pydantic schemas for authentication
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """토큰 페이로드"""
    user_id: str | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str  # 이메일 또는 사용자명
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "admin@jsmoney.com",
                    "password": "admin123"
                },
                {
                    "username": "admin",
                    "password": "admin123"
                }
            ]
        }
    }


class RegisterRequest(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "username": "username",
                    "password": "password123",
                    "full_name": "홍길동"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """사용자 응답"""
    id: str
    email: str
    username: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserUpdateRequest(BaseModel):
    """사용자 프로필 업데이트 요청"""
    username: str | None = None
    full_name: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "newusername",
                    "full_name": "홍길동"
                }
            ]
        }
    }


class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str
    new_password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_password": "oldpassword123",
                    "new_password": "newpassword123"
                }
            ]
        }
    }
