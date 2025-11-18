"""
배당 거래 테스트
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Account


def test_create_dividend_transaction_with_cash_asset(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """배당 거래 생성 시 지정한 현금 자산으로 입금 거래 자동 생성 (현금배당)"""
    
    # 1. 주식 자산 생성
    stock_payload = {
        "account_id": test_account.id,
        "name": "삼성전자",
        "asset_type": "stock",
        "symbol": "005930",
        "currency": "KRW"
    }
    
    stock_response = client.post(
        "/api/v1/assets",
        json=stock_payload,
        headers=auth_header
    )
    assert stock_response.status_code == 201
    stock_asset_id = stock_response.json()["id"]
    
    # 2. 현금 자산 생성
    cash_payload = {
        "account_id": test_account.id,
        "name": "현금(KRW)",
        "asset_type": "cash",
        "currency": "KRW"
    }
    
    cash_response = client.post(
        "/api/v1/assets",
        json=cash_payload,
        headers=auth_header
    )
    assert cash_response.status_code == 201
    cash_asset_id = cash_response.json()["id"]
    
    # 3. 배당 거래 생성 (현금배당: 수량 0, 가격 = 총 배당금)
    dividend_payload = {
        "asset_id": stock_asset_id,
        "type": "dividend",
        "quantity": 0,   # 현금배당은 수량 0
        "price": 1000,   # 총 배당금 1000원
        "fee": 0,
        "tax": 150,      # 배당소득세 150원
        "transaction_date": "2024-11-18T10:00:00",
        "description": "2024년 4분기 배당",
        "is_confirmed": True,
        "cash_asset_id": cash_asset_id
    }
    
    dividend_response = client.post(
        "/api/v1/transactions",
        json=dividend_payload,
        headers=auth_header
    )
    
    assert dividend_response.status_code == 201
    dividend_data = dividend_response.json()
    assert dividend_data["type"] == "dividend"
    assert dividend_data["related_transaction_id"] is not None
    
    # 4. 연결된 현금 입금 거래 확인
    cash_tx_id = dividend_data["related_transaction_id"]
    cash_tx_response = client.get(
        f"/api/v1/transactions/{cash_tx_id}",
        headers=auth_header
    )
    
    assert cash_tx_response.status_code == 200
    cash_tx_data = cash_tx_response.json()
    assert cash_tx_data["type"] == "deposit"
    assert cash_tx_data["asset_id"] == cash_asset_id
    # 현금 거래 수량 = 배당 가격 - 세금 = 1000 - 150 = 850
    assert cash_tx_data["quantity"] == 850.0
    assert cash_tx_data["price"] == 1.0
    assert "배당금 입금" in cash_tx_data["description"]


def test_create_dividend_transaction_without_cash_asset(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """배당 거래 생성 시 현금 자산 미지정 시 자동 생성 (현금배당)"""
    
    # 1. 주식 자산 생성
    stock_payload = {
        "account_id": test_account.id,
        "name": "애플",
        "asset_type": "stock",
        "symbol": "AAPL",
        "currency": "USD"
    }
    
    stock_response = client.post(
        "/api/v1/assets",
        json=stock_payload,
        headers=auth_header
    )
    assert stock_response.status_code == 201
    stock_asset_id = stock_response.json()["id"]
    
    # 2. 배당 거래 생성 (cash_asset_id 없음, 현금배당)
    dividend_payload = {
        "asset_id": stock_asset_id,
        "type": "dividend",
        "quantity": 0,   # 현금배당은 수량 0
        "price": 2.5,    # 총 배당금 $2.5
        "fee": 0,
        "tax": 0.38,     # 세금 $0.38
        "transaction_date": "2024-11-18T10:00:00",
        "description": "AAPL Q4 배당",
        "is_confirmed": True
    }
    
    dividend_response = client.post(
        "/api/v1/transactions",
        json=dividend_payload,
        headers=auth_header
    )
    
    assert dividend_response.status_code == 201
    dividend_data = dividend_response.json()
    assert dividend_data["related_transaction_id"] is not None
    
    # 3. 연결된 현금 입금 거래 확인
    cash_tx_id = dividend_data["related_transaction_id"]
    cash_tx_response = client.get(
        f"/api/v1/transactions/{cash_tx_id}",
        headers=auth_header
    )
    
    assert cash_tx_response.status_code == 200
    cash_tx_data = cash_tx_response.json()
    assert cash_tx_data["type"] == "deposit"
    # 현금 거래 수량 = 배당 가격 - 세금 = 2.5 - 0.38 = 2.12
    expected_amount = 2.5 - 0.38
    assert abs(cash_tx_data["quantity"] - expected_amount) < 0.01
    assert cash_tx_data["price"] == 1.0


def test_dividend_transaction_zero_price(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """배당 거래에서 가격이 0인 경우 현금 거래 생성 안함 (현금배당, 수량 0)"""
    
    # 1. 주식 자산 생성
    stock_payload = {
        "account_id": test_account.id,
        "name": "테스트주식",
        "asset_type": "stock",
        "currency": "KRW"
    }
    
    stock_response = client.post(
        "/api/v1/assets",
        json=stock_payload,
        headers=auth_header
    )
    assert stock_response.status_code == 201
    stock_asset_id = stock_response.json()["id"]
    
    # 2. 가격이 0인 배당 거래 생성 (현금배당, 수량 0)
    dividend_payload = {
        "asset_id": stock_asset_id,
        "type": "dividend",
        "quantity": 0,   # 현금배당은 수량 0
        "price": 0,      # 가격 0
        "fee": 0,
        "tax": 0,
        "transaction_date": "2024-11-18T10:00:00",
        "description": "현금배당 마커",
        "is_confirmed": True
    }
    
    dividend_response = client.post(
        "/api/v1/transactions",
        json=dividend_payload,
        headers=auth_header
    )
    
    # 가격이 0이면 배당 거래만 생성되고 현금 거래는 생성되지 않음
    assert dividend_response.status_code == 201
    dividend_data = dividend_response.json()
    assert dividend_data["quantity"] == 0
    assert dividend_data["price"] == 0
    assert dividend_data["type"] == "dividend"
    # 연결된 거래가 없어야 함
    assert dividend_data["related_transaction_id"] is None
