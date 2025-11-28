"""
현금배당(cash_dividend) 거래 테스트 (단일 현금 자산 거래)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Account


def test_cash_dividend_on_cash_asset_with_source_asset(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """현금배당은 현금 자산에 단일 거래로 기록되고, extras.asset에 배당 자산 ID를 담는다"""

    # 1. 배당 원자산(주식) 생성
    stock_payload = {
        "account_id": test_account.id,
        "name": "삼성전자",
        "asset_type": "stock",
        "symbol": "005930",
        "currency": "KRW"
    }
    stock_response = client.post("/api/v1/assets", json=stock_payload, headers=auth_header)
    assert stock_response.status_code == 201
    stock_asset_id = stock_response.json()["id"]

    # 2. 현금 자산 생성
    cash_payload = {
        "account_id": test_account.id,
        "name": "현금(KRW)",
        "asset_type": "cash",
        "currency": "KRW"
    }
    cash_response = client.post("/api/v1/assets", json=cash_payload, headers=auth_header)
    assert cash_response.status_code == 201
    cash_asset_id = cash_response.json()["id"]

    # 3. 현금배당 거래 생성 (현금 자산에 양수 수량, extras.asset에 주식 자산 ID)
    payload = {
        "asset_id": cash_asset_id,
        "type": "cash_dividend",
        "quantity": 850.0,
        "extras": {
            "asset": stock_asset_id,
            "tax": 150.0
        },
        "transaction_date": "2024-11-18T10:00:00",
        "description": "삼성전자 현금배당"
    }
    res = client.post("/api/v1/transactions", json=payload, headers=auth_header)
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "cash_dividend"
    assert data["asset_id"] == cash_asset_id
    assert data["quantity"] == 850.0
    assert (data.get("extras") or {}).get("asset") == stock_asset_id
    # 연결 거래 없음
    assert data["related_transaction_id"] is None


def test_cash_dividend_requires_positive_quantity(
    client: TestClient,
    auth_header: dict,
    test_account: Account
):
    """현금배당은 수량(금액)이 양수여야 한다"""

    # 현금 자산 생성
    cash_payload = {
        "account_id": test_account.id,
        "name": "현금(KRW)",
        "asset_type": "cash",
        "currency": "KRW"
    }
    cash_response = client.post("/api/v1/assets", json=cash_payload, headers=auth_header)
    assert cash_response.status_code == 201
    cash_asset_id = cash_response.json()["id"]

    # 수량 0은 거부
    payload0 = {
        "asset_id": cash_asset_id,
        "type": "cash_dividend",
        "quantity": 0,
        "transaction_date": "2024-11-18T10:00:00"
    }
    res0 = client.post("/api/v1/transactions", json=payload0, headers=auth_header)
    assert res0.status_code == 422 or res0.status_code == 400

    # 수량 음수는 거부
    payload_neg = {
        "asset_id": cash_asset_id,
        "type": "cash_dividend",
        "quantity": -10,
        "transaction_date": "2024-11-18T10:00:00"
    }
    res_neg = client.post("/api/v1/transactions", json=payload_neg, headers=auth_header)
    assert res_neg.status_code == 422 or res_neg.status_code == 400
