"""
환전 거래 테스트
"""
import pytest
from fastapi.testclient import TestClient
from app.models import Account


def test_create_exchange_transaction_with_metadata(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """환전 거래 생성 시 transaction_metadata에 환율 정보 저장"""
    
    # 1. KRW 현금 자산 생성
    krw_payload = {
        "account_id": test_account.id,
        "name": "원화",
        "asset_type": "cash",
        "currency": "KRW"
    }
    
    krw_response = client.post(
        "/api/v1/assets",
        json=krw_payload,
        headers=auth_header
    )
    assert krw_response.status_code == 201
    krw_asset_id = krw_response.json()["id"]
    
    # 2. USD 현금 자산 생성
    usd_payload = {
        "account_id": test_account.id,
        "name": "달러",
        "asset_type": "cash",
        "currency": "USD"
    }
    
    usd_response = client.post(
        "/api/v1/assets",
        json=usd_payload,
        headers=auth_header
    )
    assert usd_response.status_code == 201
    usd_asset_id = usd_response.json()["id"]
    
    # 3. 환전 거래 생성 (1,300,000원 → $1,000)
    exchange_payload = {
        "asset_id": krw_asset_id,
        "type": "exchange",
        "quantity": -1300000,  # 원화 출금
        "price": 1.0,
        "fee": 0,
        "tax": 0,
        "transaction_date": "2024-11-18T10:00:00",
        "description": "원화 → 달러 환전",
        "is_confirmed": True,
        "target_asset_id": usd_asset_id,
        "target_amount": 1000,  # 달러 입금
        "extras": {
            "exchange_rate": 0.000769230769  # 1000 / 1300000
        }
    }
    
    exchange_response = client.post(
        "/api/v1/transactions",
        json=exchange_payload,
        headers=auth_header
    )
    
    assert exchange_response.status_code == 201
    exchange_data = exchange_response.json()
    assert exchange_data["type"] == "exchange"
    assert exchange_data["extras"] is not None
    assert "exchange_rate" in exchange_data["extras"]
    assert exchange_data["extras"]["exchange_rate"] == pytest.approx(0.000769230769, rel=1e-6)
    
    # 4. 연결된 거래 확인
    assert exchange_data["related_transaction_id"] is not None
    related_tx_id = exchange_data["related_transaction_id"]
    
    related_response = client.get(
        f"/api/v1/transactions/{related_tx_id}",
        headers=auth_header
    )
    
    assert related_response.status_code == 200
    related_data = related_response.json()
    assert related_data["type"] == "exchange"
    assert related_data["asset_id"] == usd_asset_id
    assert related_data["quantity"] == 1000
    # 연결 거래도 같은 메타데이터를 공유해야 함
    if related_data["extras"]:
        assert "exchange_rate" in related_data["extras"]


def test_exchange_rate_calculation(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """환율 계산 검증: 대상금액 / 출발금액"""
    
    # 1. EUR 현금 자산 생성
    eur_payload = {
        "account_id": test_account.id,
        "name": "유로",
        "asset_type": "cash",
        "currency": "EUR"
    }
    
    eur_response = client.post(
        "/api/v1/assets",
        json=eur_payload,
        headers=auth_header
    )
    assert eur_response.status_code == 201
    eur_asset_id = eur_response.json()["id"]
    
    # 2. JPY 현금 자산 생성
    jpy_payload = {
        "account_id": test_account.id,
        "name": "엔화",
        "asset_type": "cash",
        "currency": "JPY"
    }
    
    jpy_response = client.post(
        "/api/v1/assets",
        json=jpy_payload,
        headers=auth_header
    )
    assert jpy_response.status_code == 201
    jpy_asset_id = jpy_response.json()["id"]
    
    # 3. 환전 거래 생성 (€100 → ¥16,000)
    # 환율: 16000 / 100 = 160
    exchange_payload = {
        "asset_id": eur_asset_id,
        "type": "exchange",
        "quantity": -100,
        "price": 1.0,
        "fee": 0,
        "tax": 0,
        "transaction_date": "2024-11-18T10:00:00",
        "description": "유로 → 엔화 환전",
        "is_confirmed": True,
        "target_asset_id": jpy_asset_id,
        "target_amount": 16000,
        "extras": {
            "exchange_rate": 160.0
        }
    }
    
    exchange_response = client.post(
        "/api/v1/transactions",
        json=exchange_payload,
        headers=auth_header
    )
    
    assert exchange_response.status_code == 201
    exchange_data = exchange_response.json()
    assert exchange_data["extras"]["exchange_rate"] == 160.0
