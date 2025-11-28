"""
Category flow_type compatibility tests
단건 생성 및 업로드 경로에서 사용하는 flow_type 검증 로직의 실패 케이스를 확인합니다.

이 테스트는 DB나 FastAPI 앱 기동 없이, transactions API 모듈에 정의된
도우미 함수(allowed_category_flow_types_for, validate_category_flow_type_compatibility)를 직접 검증합니다.
"""

import pytest
from types import SimpleNamespace

# 대상 함수 임포트 (API 모듈에 정의됨)
from app.api.transactions import (
    allowed_category_flow_types_for,
    validate_category_flow_type_compatibility,
)


def make_category(flow_type: str):
    """flow_type 속성만 가진 간단한 모형 Category 객체 생성"""
    return SimpleNamespace(flow_type=flow_type)


@pytest.mark.parametrize(
    "tx_type, expected",
    [
        ("buy", {"investment", "neutral"}),
        ("sell", {"investment", "neutral"}),
        ("deposit", {"income", "transfer", "neutral"}),
        ("interest", {"income", "transfer", "neutral"}),
        ("cash_dividend", {"income", "transfer", "neutral"}),
        ("stock_dividend", {"income", "transfer", "neutral"}),
        ("withdraw", {"expense", "transfer", "neutral"}),
        ("fee", {"expense", "transfer", "neutral"}),
        ("transfer_in", {"transfer", "neutral"}),
        ("transfer_out", {"transfer", "neutral"}),
        ("adjustment", {"neutral"}),
    ],
)
def test_allowed_category_flow_types_for(tx_type, expected):
    assert allowed_category_flow_types_for(tx_type) == expected


def test_create_transaction_invalid_category_raises_http_exception():
    """
    단건 생성 실패 케이스: 매수(buy) 거래에 지출(expense) 카테고리를 지정하면 에러
    """
    expense_category = make_category("expense")
    with pytest.raises(Exception) as excinfo:
        validate_category_flow_type_compatibility("buy", expense_category)
    # 메시지에 핵심 단어 포함 확인
    assert "허용" in str(excinfo.value)
    assert "buy" in str(excinfo.value)
    assert "expense" in str(excinfo.value)


def test_upload_invalid_category_name_mapping_raises_http_exception():
    """
    업로드 실패 케이스: 출금(withdraw) 거래에 수입(income) 카테고리 매핑 시 에러
    업로드 경로도 동일한 검증 함수를 사용하므로 같은 예외 발생을 확인한다.
    """
    income_category = make_category("income")
    with pytest.raises(Exception) as excinfo:
        validate_category_flow_type_compatibility("withdraw", income_category)
    assert "withdraw" in str(excinfo.value)
    assert "income" in str(excinfo.value)
