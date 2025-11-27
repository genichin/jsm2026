"""
환전(Exchange) CRUD 테스트
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Account, Asset, Transaction


@pytest.fixture
def test_bank_account(db_session: Session, test_user: User) -> Account:
    """은행 계좌 생성 (KRW)
    동일 계좌 내 두 통화의 현금 자산을 만들기 위해 사용
    """
    account = Account(
        owner_id=test_user.id,
        name="은행계좌",
        account_type="bank_account",
        provider="테스트은행",
        account_number="111-222",
        currency="KRW",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def krw_cash_asset(db_session: Session, test_user: User, test_bank_account: Account) -> Asset:
    asset = Asset(
        user_id=test_user.id,
        account_id=test_bank_account.id,
        name="KRW 현금",
        asset_type="cash",
        currency="KRW",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def usd_cash_asset(db_session: Session, test_user: User, test_bank_account: Account) -> Asset:
    asset = Asset(
        user_id=test_user.id,
        account_id=test_bank_account.id,
        name="USD 현금",
        asset_type="cash",
        currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


class TestCreateExchange:
    def test_create_exchange_success(
        self,
        client: TestClient,
        auth_header: dict,
        krw_cash_asset: Asset,
        usd_cash_asset: Asset,
    ):
        """KRW → USD 환전 쌍 레코드 생성 성공"""
        payload = {
            "source_asset_id": krw_cash_asset.id,
            "target_asset_id": usd_cash_asset.id,
            "source_amount": 1500000,
            "target_amount": 1100,
            "fee": 5000,
            "transaction_date": "2025-11-10T10:00:00",
            "description": "KRW to USD exchange"
        }
        response = client.post("/api/v1/transactions/exchange", headers=auth_header, json=payload)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["created_count"] == 2
        assert len(data["transactions"]) == 2

        # KRW 출발 트랜잭션
        src = next(t for t in data["transactions"] if t["asset_id"] == krw_cash_asset.id)
        dst = next(t for t in data["transactions"] if t["asset_id"] == usd_cash_asset.id)

        assert src["type"] == "exchange"
        assert dst["type"] == "exchange"
        assert src["quantity"] == -1500000
        assert dst["quantity"] == 1100
        assert src["fee"] == 5000
        assert dst["fee"] == 0
        assert src["related_transaction_id"] == dst["id"]
        assert dst["related_transaction_id"] == src["id"]

    def test_create_exchange_requires_cash_assets(
        self,
        client: TestClient,
        auth_header: dict,
        krw_cash_asset: Asset,
        stock_asset: Asset,
    ):
        """현금 자산이 아닌 경우 400 반환"""
        payload = {
            "source_asset_id": krw_cash_asset.id,
            "target_asset_id": stock_asset.id,
            "source_amount": 100000,
            "target_amount": 70,
            "transaction_date": "2025-11-10T10:00:00"
        }
        response = client.post("/api/v1/transactions/exchange", headers=auth_header, json=payload)
        assert response.status_code == 400
        assert "현금 자산" in response.json()["detail"]

    def test_create_exchange_requires_same_account(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_user: User,
        krw_cash_asset: Asset,
    ):
        """서로 다른 계좌의 현금 자산 간 환전은 400 반환"""
        # 다른 계좌와 그 계좌의 USD 현금 자산 생성
        another_account = Account(
            owner_id=test_user.id,
            name="다른 계좌",
            account_type="bank_account",
            provider="테스트은행",
            account_number="333-444",
            currency="USD",
            is_active=True,
        )
        db_session.add(another_account)
        db_session.commit()
        db_session.refresh(another_account)

        usd_other_account = Asset(
            user_id=test_user.id,
            account_id=another_account.id,
            name="USD 현금(다른계좌)",
            asset_type="cash",
            currency="USD",
            is_active=True,
        )
        db_session.add(usd_other_account)
        db_session.commit()
        db_session.refresh(usd_other_account)

        payload = {
            "source_asset_id": krw_cash_asset.id,
            "target_asset_id": usd_other_account.id,
            "source_amount": 100000,
            "target_amount": 80,
            "transaction_date": "2025-11-10T10:00:00",
        }
        response = client.post("/api/v1/transactions/exchange", headers=auth_header, json=payload)
        assert response.status_code == 400
        assert "같은 계좌" in response.json()["detail"]

    @pytest.fixture
    def stock_asset(self, db_session: Session, test_user: User, test_bank_account: Account) -> Asset:
        asset = Asset(
            user_id=test_user.id,
            account_id=test_bank_account.id,
            name="TEST 주식",
            asset_type="stock",
            symbol="TEST",
            currency="KRW",
            is_active=True,
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        return asset