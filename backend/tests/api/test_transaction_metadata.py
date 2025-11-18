"""
거래 메타데이터(transaction_metadata) 테스트
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Asset, Account, AssetTransaction


@pytest.fixture
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌 생성"""
    account = Account(
        owner_id=test_user.id,
        name="Test Account",
        account_type="securities",
        provider="Test Bank"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_cash_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 현금 자산 생성"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Cash KRW",
        asset_type="cash",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_usd_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 USD 현금 자산 생성"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Cash USD",
        asset_type="cash",
        currency="USD",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


class TestTransactionMetadata:
    """거래 메타데이터 CRUD 테스트"""
    
    def test_create_transaction_with_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """메타데이터를 포함한 거래 생성"""
        metadata = {
            "exchange_rate": 1400.0,
            "external_system_id": "EXT-12345",
            "note": "환전 거래"
        }
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 100000,
                "price": 1.0,
                "fee": 0,
                "tax": 0,
                "transaction_date": "2025-11-18T10:00:00",
                "description": "환전 입금",
                "transaction_metadata": metadata
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "deposit"
        assert data["transaction_metadata"] == metadata
        assert data["transaction_metadata"]["exchange_rate"] == 1400.0
        assert data["transaction_metadata"]["external_system_id"] == "EXT-12345"
    
    def test_create_transaction_without_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """메타데이터 없이 거래 생성 (null 허용)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 50000,
                "price": 1.0,
                "transaction_date": "2025-11-18T11:00:00",
                "description": "일반 입금"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["transaction_metadata"] is None
    
    def test_exchange_transaction_with_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        test_usd_asset: Asset
    ):
        """환전 거래에 환율 정보 저장"""
        exchange_rate = 1350.5
        metadata = {
            "exchange_rate": exchange_rate,
            "original_amount_krw": 1350500,
            "converted_amount_usd": 1000
        }
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "exchange",
                "quantity": -1350500,
                "price": 1.0,
                "transaction_date": "2025-11-18T12:00:00",
                "description": "KRW → USD 환전",
                "target_asset_id": test_usd_asset.id,
                "target_amount": 1000,
                "transaction_metadata": metadata
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "exchange"
        assert data["transaction_metadata"]["exchange_rate"] == exchange_rate
    
    def test_update_transaction_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """거래 메타데이터 업데이트"""
        # 1. 거래 생성
        create_response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 200000,
                "price": 1.0,
                "transaction_date": "2025-11-18T13:00:00",
                "description": "초기 입금",
                "transaction_metadata": {"initial": "data"}
            }
        )
        
        assert create_response.status_code == 201
        transaction_id = create_response.json()["id"]
        
        # 2. 메타데이터 업데이트
        updated_metadata = {
            "initial": "data",
            "updated_field": "new_value",
            "timestamp": "2025-11-18T14:00:00"
        }
        
        update_response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            headers=auth_header,
            json={
                "transaction_metadata": updated_metadata
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["transaction_metadata"]["updated_field"] == "new_value"
        assert data["transaction_metadata"]["timestamp"] == "2025-11-18T14:00:00"
    
    def test_list_transactions_includes_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """거래 목록 조회 시 메타데이터 포함"""
        # 1. 메타데이터가 있는 거래 생성
        metadata = {"list_test": "value"}
        client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 100000,
                "price": 1.0,
                "transaction_date": "2025-11-18T15:00:00",
                "transaction_metadata": metadata
            }
        )
        
        # 2. 목록 조회
        list_response = client.get(
            "/api/v1/transactions/recent?page=1&size=10",
            headers=auth_header
        )
        
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert len(items) > 0
        
        # 메타데이터가 있는 거래 찾기
        transaction_with_metadata = next(
            (item for item in items if item.get("transaction_metadata") == metadata),
            None
        )
        assert transaction_with_metadata is not None
        assert transaction_with_metadata["transaction_metadata"]["list_test"] == "value"
    
    def test_metadata_with_nested_structure(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """복잡한 중첩 구조의 메타데이터"""
        complex_metadata = {
            "exchange": {
                "rate": 1400.5,
                "provider": "Test Bank",
                "fees": {
                    "commission": 1000,
                    "tax": 500
                }
            },
            "external_refs": ["REF-001", "REF-002"],
            "tags": ["important", "verified"]
        }
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 300000,
                "price": 1.0,
                "transaction_date": "2025-11-18T16:00:00",
                "description": "복잡한 메타데이터 테스트",
                "transaction_metadata": complex_metadata
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["transaction_metadata"]["exchange"]["rate"] == 1400.5
        assert data["transaction_metadata"]["exchange"]["fees"]["commission"] == 1000
        assert "important" in data["transaction_metadata"]["tags"]
        assert len(data["transaction_metadata"]["external_refs"]) == 2
    
    def test_clear_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """메타데이터를 null로 업데이트 (삭제)"""
        # 1. 메타데이터가 있는 거래 생성
        create_response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 100000,
                "price": 1.0,
                "transaction_date": "2025-11-18T17:00:00",
                "transaction_metadata": {"to_be_deleted": "yes"}
            }
        )
        
        transaction_id = create_response.json()["id"]
        
        # 2. 메타데이터를 null로 업데이트
        update_response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            headers=auth_header,
            json={
                "transaction_metadata": None
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["transaction_metadata"] is None
