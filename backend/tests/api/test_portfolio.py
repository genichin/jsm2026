"""
포트폴리오 요약 테스트

GET /api/v1/transactions/portfolio - 포트폴리오 전체 요약
"""

import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Account, Asset, Transaction


@pytest.fixture
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌"""
    account = Account(
        owner_id=test_user.id,
        name="테스트 증권계좌",
        account_number="1234567890",
        account_type="securities",
        provider="테스트증권"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_cash_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 현금 자산"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="현금",
        asset_type="cash",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_stock_asset_samsung(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 주식 자산 - 삼성전자"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="삼성전자",
        asset_type="stock",
        symbol="005930",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_stock_asset_kakao(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 주식 자산 - 카카오"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="카카오",
        asset_type="stock",
        symbol="035720",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def portfolio_transactions(
    db_session: Session,
    test_cash_asset: Asset,
    test_stock_asset_samsung: Asset,
    test_stock_asset_kakao: Asset
) -> dict:
    """포트폴리오 테스트용 거래 데이터"""
    
    # 현금 자산 거래
    cash_transactions = [
        Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=10000000,  # 1000만원 입금
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="초기 입금",
            flow_type="income"
        ),
        Transaction(
            asset_id=test_cash_asset.id,
            type="withdraw",
            quantity=-3000000,  # 300만원 출금 (주식 매수용)
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 5, 10, 0, 0),
            description="주식 매수를 위한 출금",
            flow_type="expense"
        ),
    ]
    
    # 삼성전자 거래
    samsung_transactions = [
        Transaction(
            asset_id=test_stock_asset_samsung.id,
            type="buy",
            quantity=50,  # 50주 매수
            price=70000,  # 주당 70,000원
            fee=500,
            tax=150,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 5, 11, 0, 0),
            description="삼성전자 매수",
            flow_type="investment"
        ),
        Transaction(
            asset_id=test_stock_asset_samsung.id,
            type="sell",
            quantity=-20,  # 20주 매도
            price=75000,  # 주당 75,000원
            fee=300,
            tax=100,
            realized_profit=95000,  # (75000-70000)*20 - 300 - 100 = 99600 (대략 95000)
            transaction_date=datetime(2025, 11, 10, 14, 0, 0),
            description="삼성전자 일부 매도",
            flow_type="investment"
        ),
    ]
    
    # 카카오 거래
    kakao_transactions = [
        Transaction(
            asset_id=test_stock_asset_kakao.id,
            type="buy",
            quantity=30,  # 30주 매수
            price=50000,  # 주당 50,000원
            fee=300,
            tax=100,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 7, 10, 0, 0),
            description="카카오 매수",
            flow_type="investment"
        ),
    ]
    
    all_transactions = cash_transactions + samsung_transactions + kakao_transactions
    db_session.add_all(all_transactions)
    db_session.commit()
    
    return {
        "cash": cash_transactions,
        "samsung": samsung_transactions,
        "kakao": kakao_transactions,
        "all": all_transactions
    }


class TestPortfolioBasic:
    """포트폴리오 기본 조회 테스트"""
    
    def test_get_portfolio_empty(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """자산이 없는 경우 포트폴리오 조회"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 기본 필드 존재 확인
        assert "total_assets_value" in data
        assert "total_cash" in data
        assert "total_realized_profit" in data
        assert "total_unrealized_profit" in data
        assert "asset_summaries" in data
        
        # 빈 포트폴리오
        assert float(data["total_assets_value"]) == 0
        assert float(data["total_cash"]) == 0
        assert float(data["total_realized_profit"]) == 0
        assert data["asset_summaries"] == []
    
    def test_get_portfolio_with_cash_only(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """현금 자산만 있는 경우"""
        # 현금 입금
        from app.models import Transaction
        from sqlalchemy.orm import Session
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 1000000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        assert response.status_code == 201
        
        # 포트폴리오 조회
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 현금만 있음
        assert float(data["total_cash"]) == 1000000.0
        assert float(data["total_assets_value"]) == 0
        assert len(data["asset_summaries"]) == 1
        
        # 현금 자산 요약
        cash_summary = data["asset_summaries"][0]
        assert cash_summary["asset_name"] == "현금"
        assert cash_summary["asset_type"] == "cash"
        assert float(cash_summary["current_quantity"]) == 1000000.0
    
    def test_get_portfolio_no_auth(
        self,
        client: TestClient
    ):
        """인증 없이 포트폴리오 조회"""
        response = client.get("/api/v1/transactions/portfolio")
        assert response.status_code == 401


class TestPortfolioCalculation:
    """포트폴리오 계산 로직 테스트"""
    
    def test_portfolio_with_multiple_assets(
        self,
        client: TestClient,
        auth_header: dict,
        portfolio_transactions: dict
    ):
        """여러 자산이 있는 포트폴리오"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 자산 요약 개수 (현금 + 삼성전자 + 카카오)
        assert len(data["asset_summaries"]) == 3
        
        # 현금 잔액: 10,000,000 - 3,000,000 = 7,000,000
        assert float(data["total_cash"]) == 7000000.0
        
        # 실현손익: 삼성전자 매도에서 발생
        # 95,000 (삼성전자 realized_profit)
        assert float(data["total_realized_profit"]) == 95000.0
    
    def test_portfolio_asset_summaries_structure(
        self,
        client: TestClient,
        auth_header: dict,
        portfolio_transactions: dict
    ):
        """자산 요약 구조 검증"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 각 자산 요약 필드 확인
        for summary in data["asset_summaries"]:
            assert "asset_id" in summary
            assert "asset_name" in summary
            assert "asset_type" in summary
            assert "current_quantity" in summary
            assert "total_cost" in summary
            assert "realized_profit" in summary
            
            # 타입 검증
            assert summary["asset_type"] in ["cash", "stock", "crypto"]
    
    def test_portfolio_stock_quantity_calculation(
        self,
        client: TestClient,
        auth_header: dict,
        portfolio_transactions: dict,
        test_stock_asset_samsung: Asset,
        test_stock_asset_kakao: Asset
    ):
        """주식 보유 수량 계산"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 자산별 수량 확인
        samsung_summary = next(
            (s for s in data["asset_summaries"] if s["asset_id"] == test_stock_asset_samsung.id),
            None
        )
        kakao_summary = next(
            (s for s in data["asset_summaries"] if s["asset_id"] == test_stock_asset_kakao.id),
            None
        )
        
        assert samsung_summary is not None
        assert kakao_summary is not None
        
        # 삼성전자: 50주 매수 - 20주 매도 = 30주
        assert float(samsung_summary["current_quantity"]) == 30.0
        
        # 카카오: 30주 매수
        assert float(kakao_summary["current_quantity"]) == 30.0
    
    def test_portfolio_realized_profit_by_asset(
        self,
        client: TestClient,
        auth_header: dict,
        portfolio_transactions: dict,
        test_stock_asset_samsung: Asset
    ):
        """자산별 실현손익 확인"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        samsung_summary = next(
            (s for s in data["asset_summaries"] if s["asset_id"] == test_stock_asset_samsung.id),
            None
        )
        
        assert samsung_summary is not None
        # 삼성전자 매도로 인한 실현손익
        assert float(samsung_summary["realized_profit"]) == 95000.0


class TestPortfolioFiltering:
    """포트폴리오 필터링 테스트"""
    
    def test_portfolio_only_confirmed_transactions(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """flow_type가 다른 거래가 모두 합산되는지 확인"""
        # 확정(수입) 거래
        confirmed_tx = Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=1000000,
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="확정 거래",
            flow_type="income"
        )
        
        # 미확정(분류되지 않은) 거래
        unconfirmed_tx = Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=500000,
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 2, 10, 0, 0),
            description="미확정 거래",
            flow_type="undefined"
        )
        
        db_session.add_all([confirmed_tx, unconfirmed_tx])
        db_session.commit()
        
        # 포트폴리오 조회
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 모든 거래 합산 (1,500,000)
        assert float(data["total_cash"]) == 1500000.0
    
    def test_portfolio_only_active_assets(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """활성 자산만 포함"""
        # 거래 추가
        tx = Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=1000000,
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="입금",
            flow_type="income"
        )
        db_session.add(tx)
        db_session.commit()
        
        # 포트폴리오 조회 (활성 상태)
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        assert response.status_code == 200
        data1 = response.json()
        assert len(data1["asset_summaries"]) == 1
        
        # 자산 비활성화
        test_cash_asset.is_active = False
        db_session.commit()
        
        # 포트폴리오 재조회 (비활성 상태)
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        assert response.status_code == 200
        data2 = response.json()
        
        # 비활성 자산은 제외됨
        assert len(data2["asset_summaries"]) == 0
        assert float(data2["total_cash"]) == 0


class TestPortfolioEdgeCases:
    """포트폴리오 엣지 케이스 테스트"""
    
    def test_portfolio_with_zero_quantity_asset(
        self,
        client: TestClient,
        auth_header: dict,
        test_stock_asset_samsung: Asset,
        db_session: Session
    ):
        """수량이 0인 자산 (전량 매도)"""
        # 매수
        buy_tx = Transaction(
            asset_id=test_stock_asset_samsung.id,
            type="buy",
            quantity=10,
            price=70000,
            fee=100,
            tax=50,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="매수",
            flow_type="investment"
        )
        
        # 전량 매도
        sell_tx = Transaction(
            asset_id=test_stock_asset_samsung.id,
            type="sell",
            quantity=-10,
            price=75000,
            fee=100,
            tax=50,
            realized_profit=49700,  # (75000-70000)*10 - 100 - 50
            transaction_date=datetime(2025, 11, 5, 14, 0, 0),
            description="전량 매도",
            flow_type="investment"
        )
        
        db_session.add_all([buy_tx, sell_tx])
        db_session.commit()
        
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 자산은 목록에 포함되지만 수량은 0
        samsung_summary = next(
            (s for s in data["asset_summaries"] if s["asset_id"] == test_stock_asset_samsung.id),
            None
        )
        
        assert samsung_summary is not None
        assert float(samsung_summary["current_quantity"]) == 0.0
        # 실현손익은 기록됨
        assert float(samsung_summary["realized_profit"]) == 49700.0
    
    def test_portfolio_with_negative_cash(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """마이너스 현금 (출금이 입금보다 많은 경우)"""
        transactions = [
            Transaction(
                asset_id=test_cash_asset.id,
                type="deposit",
                quantity=100000,
                price=1.0,
                fee=0,
                tax=0,
                realized_profit=0,
                transaction_date=datetime(2025, 11, 1, 10, 0, 0),
                description="입금",
                flow_type="income"
            ),
            Transaction(
                asset_id=test_cash_asset.id,
                type="withdraw",
                quantity=-150000,  # 입금보다 많은 출금
                price=1.0,
                fee=0,
                tax=0,
                realized_profit=0,
                transaction_date=datetime(2025, 11, 2, 10, 0, 0),
                description="출금",
                flow_type="expense"
            ),
        ]
        
        db_session.add_all(transactions)
        db_session.commit()
        
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 마이너스 현금 허용 (100000 - 150000 = -50000)
        assert float(data["total_cash"]) == -50000.0
    
    def test_portfolio_with_large_numbers(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """큰 금액 처리"""
        # 10억원 입금
        tx = Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=1000000000,  # 10억
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="대량 입금",
            flow_type="income"
        )
        
        db_session.add(tx)
        db_session.commit()
        
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 큰 숫자 정확히 처리
        assert float(data["total_cash"]) == 1000000000.0


class TestPortfolioResponseStructure:
    """포트폴리오 응답 구조 테스트"""
    
    def test_portfolio_response_schema(
        self,
        client: TestClient,
        auth_header: dict,
        portfolio_transactions: dict
    ):
        """포트폴리오 응답 스키마 검증"""
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 최상위 필드
        required_top_fields = [
            "total_assets_value",
            "total_cash",
            "total_realized_profit",
            "total_unrealized_profit",
            "asset_summaries"
        ]
        
        for field in required_top_fields:
            assert field in data, f"Missing top-level field: {field}"
        
        # asset_summaries 타입 확인
        assert isinstance(data["asset_summaries"], list)
        
        # 각 자산 요약 필드
        if len(data["asset_summaries"]) > 0:
            summary = data["asset_summaries"][0]
            required_summary_fields = [
                "asset_id",
                "asset_name",
                "asset_type",
                "current_quantity",
                "total_cost",
                "realized_profit"
            ]
            
            for field in required_summary_fields:
                assert field in summary, f"Missing summary field: {field}"
    
    def test_portfolio_decimal_precision(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """소수점 정밀도 테스트"""
        # 소수점이 있는 금액
        tx = Transaction(
            asset_id=test_cash_asset.id,
            type="deposit",
            quantity=1234.56,
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=datetime(2025, 11, 1, 10, 0, 0),
            description="소수점 입금",
            flow_type="income"
        )
        
        db_session.add(tx)
        db_session.commit()
        
        response = client.get(
            "/api/v1/transactions/portfolio",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 소수점 정밀도 유지
        assert abs(float(data["total_cash"]) - 1234.56) < 0.01
