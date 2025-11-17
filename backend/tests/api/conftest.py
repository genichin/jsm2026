"""
API 테스트용 공통 픽스처
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Account, AccountShare, Asset
from app.core.security import get_password_hash


@pytest.fixture(scope="function")
def test_user(db_session: Session, test_password: str) -> User:
    """
    테스트용 사용자 생성
    """
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password=get_password_hash(test_password),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_header(client: TestClient, test_user: User, test_password: str) -> dict:
    """
    인증된 사용자의 Authorization 헤더 반환
    """
    # 로그인하여 토큰 획득
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user.email,
            "password": test_password
        }
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def superuser(db_session: Session, test_password: str) -> User:
    """
    테스트용 슈퍼유저 생성
    """
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash(test_password),
        full_name="Admin User",
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def superuser_auth_header(client: TestClient, superuser: User, test_password: str) -> dict:
    """
    슈퍼유저의 Authorization 헤더 반환
    """
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": superuser.email,
            "password": test_password
        }
    )
    assert response.status_code == 200, f"Superuser login failed: {response.text}"
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌"""
    account = Account(
        owner_id=test_user.id,
        name="테스트 은행계좌",
        account_type="bank_account",
        provider="테스트은행",
        account_number="1234567890",
        currency="KRW",
        is_active=True
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    
    # 소유자 공유 레코드 생성
    owner_share = AccountShare(
        account_id=account.id,
        user_id=test_user.id,
        role="owner",
        can_read=True,
        can_write=True,
        can_delete=True,
        can_share=True,
        shared_by=test_user.id
    )
    db_session.add(owner_share)
    db_session.commit()
    
    return account


@pytest.fixture(scope="function")
def test_asset(client: TestClient, auth_header: dict, test_account: Account) -> dict:
    """테스트용 자산"""
    payload = {
        "name": "테스트자산",
        "asset_type": "stock",
        "account_id": test_account.id
    }
    response = client.post("/api/v1/assets", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()
