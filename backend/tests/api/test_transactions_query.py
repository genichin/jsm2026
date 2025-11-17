"""
거래 조회, 필터링, 페이지네이션 테스트

GET /api/v1/transactions - 전체 거래 조회 (필터, 페이지네이션)
GET /api/v1/transactions/{id} - 단일 거래 조회
GET /api/v1/transactions/assets/{asset_id}/transactions - 자산별 거래 조회
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Account, Asset, AssetTransaction


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
def test_stock_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 주식 자산"""
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
def sample_transactions(
    db_session: Session,
    test_cash_asset: Asset,
    test_stock_asset: Asset
) -> list[AssetTransaction]:
    """테스트용 샘플 거래 데이터 (30건)"""
    transactions = []
    
    # 기준 날짜: 2025-11-01
    base_date = datetime(2025, 11, 1, 10, 0, 0)
    
    # 현금 자산 거래 (15건)
    for i in range(15):
        tx_date = base_date + timedelta(days=i)
        tx_type = "deposit" if i % 2 == 0 else "withdraw"
        quantity = 10000 * (i + 1) if i % 2 == 0 else -5000 * (i + 1)
        
        tx = AssetTransaction(
            asset_id=test_cash_asset.id,
            type=tx_type,
            quantity=quantity,
            price=1.0,
            fee=0,
            tax=0,
            realized_profit=0,
            transaction_date=tx_date,
            description=f"현금 거래 #{i+1}",
            is_confirmed=True if i < 10 else False  # 처음 10건만 확정
        )
        transactions.append(tx)
    
    # 주식 자산 거래 (15건)
    for i in range(15):
        tx_date = base_date + timedelta(days=i, hours=2)
        tx_type = "buy" if i % 3 == 0 else "sell"
        quantity = 10 * (i + 1) if tx_type == "buy" else -5 * (i + 1)
        
        tx = AssetTransaction(
            asset_id=test_stock_asset.id,
            type=tx_type,
            quantity=quantity,
            price=70000 + (i * 1000),
            fee=100,
            tax=50,
            realized_profit=500 if tx_type == "sell" else 0,
            transaction_date=tx_date,
            description=f"주식 거래 #{i+1}",
            is_confirmed=True
        )
        transactions.append(tx)
    
    db_session.add_all(transactions)
    db_session.commit()
    
    return transactions


class TestTransactionsList:
    """거래 목록 조회 테스트 (GET /api/v1/transactions)"""
    
    def test_list_all_transactions_default_pagination(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """기본 페이지네이션으로 전체 거래 조회"""
        response = client.get(
            "/api/v1/transactions",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 기본값: page=1, size=20
        assert data["page"] == 1
        assert data["size"] == 20
        assert data["total"] == 30  # 전체 30건
        assert data["pages"] == 2  # 총 2페이지
        assert len(data["items"]) == 20  # 첫 페이지 20건
        
        # 최신 거래가 먼저 (transaction_date 내림차순)
        dates = [item["transaction_date"] for item in data["items"]]
        assert dates == sorted(dates, reverse=True)
    
    def test_list_transactions_with_pagination(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """페이지네이션 파라미터 테스트"""
        # 페이지 2, 사이즈 10
        response = client.get(
            "/api/v1/transactions?page=2&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["size"] == 10
        assert data["total"] == 30
        assert data["pages"] == 3  # 총 3페이지 (30 / 10)
        assert len(data["items"]) == 10
    
    def test_list_transactions_last_page(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """마지막 페이지 조회 (부분 결과)"""
        response = client.get(
            "/api/v1/transactions?page=3&size=15",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 3
        assert data["size"] == 15
        assert data["total"] == 30
        assert len(data["items"]) == 0  # 마지막 페이지 넘어감
    
    def test_list_transactions_invalid_page(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """잘못된 페이지 파라미터"""
        response = client.get(
            "/api/v1/transactions?page=0",
            headers=auth_header
        )
        
        # Query validation error
        assert response.status_code == 422


class TestTransactionsFilter:
    """거래 필터링 테스트"""
    
    def test_filter_by_asset_id(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        sample_transactions: list
    ):
        """자산 ID로 필터링"""
        response = client.get(
            f"/api/v1/transactions?asset_id={test_cash_asset.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 15  # 현금 자산 거래만 15건
        for item in data["items"]:
            assert item["asset"]["id"] == test_cash_asset.id
    
    def test_filter_by_transaction_type(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """거래 유형으로 필터링 (deposit)"""
        response = client.get(
            "/api/v1/transactions?type=deposit",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 8  # deposit 타입만 (현금 거래 중 짝수 인덱스)
        for item in data["items"]:
            assert item["type"] == "deposit"
    
    def test_filter_by_date_range(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """날짜 범위로 필터링"""
        start_date = "2025-11-05T00:00:00"
        end_date = "2025-11-10T23:59:59"
        
        response = client.get(
            f"/api/v1/transactions?start_date={start_date}&end_date={end_date}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 11/5 ~ 11/10 사이 거래 (6일 * 2건/일 = 12건)
        assert data["total"] == 12
        
        # 날짜 비교 (timezone-aware 처리)
        from datetime import timezone
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        
        for item in data["items"]:
            tx_date = datetime.fromisoformat(item["transaction_date"].replace('Z', '+00:00'))
            assert tx_date >= start_dt
            assert tx_date <= end_dt
    
    def test_filter_by_start_date_only(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """시작 날짜만으로 필터링"""
        start_date = "2025-11-10T00:00:00"
        
        response = client.get(
            f"/api/v1/transactions?start_date={start_date}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 11/10 이후 거래 (11/10 ~ 11/15, 6일 * 2건 = 12건)
        assert data["total"] == 12
    
    def test_filter_by_end_date_only(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """종료 날짜만으로 필터링"""
        end_date = "2025-11-05T23:59:59"
        
        response = client.get(
            f"/api/v1/transactions?end_date={end_date}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 11/5 이전 거래 (11/1 ~ 11/5, 5일 * 2건 = 10건)
        assert data["total"] == 10
    
    def test_filter_by_is_confirmed(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """확정 상태로 필터링"""
        response = client.get(
            "/api/v1/transactions?is_confirmed=false",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 미확정 거래만 (현금 거래 중 마지막 5건)
        assert data["total"] == 5
        for item in data["items"]:
            assert item["is_confirmed"] is False
    
    def test_filter_by_account_id(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        sample_transactions: list
    ):
        """계좌 ID로 필터링"""
        response = client.get(
            f"/api/v1/transactions?account_id={test_account.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 모든 거래가 같은 계좌에 속함
        assert data["total"] == 30
    
    def test_filter_multiple_conditions(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        sample_transactions: list
    ):
        """복합 필터 조건"""
        response = client.get(
            f"/api/v1/transactions?asset_id={test_cash_asset.id}&type=deposit&is_confirmed=true",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 현금 자산 + deposit + 확정 거래
        assert data["total"] == 5  # 짝수 인덱스 중 처음 10건(0,2,4,6,8)
        for item in data["items"]:
            assert item["asset"]["id"] == test_cash_asset.id
            assert item["type"] == "deposit"
            assert item["is_confirmed"] is True


class TestSingleTransaction:
    """단일 거래 조회 테스트 (GET /api/v1/transactions/{id})"""
    
    def test_get_transaction_success(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """단일 거래 조회 성공"""
        transaction = sample_transactions[0]
        
        response = client.get(
            f"/api/v1/transactions/{transaction.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == transaction.id
        assert data["type"] == transaction.type
        assert data["quantity"] == transaction.quantity
        assert "asset" in data
        assert data["asset"]["id"] == transaction.asset_id
    
    def test_get_transaction_not_found(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 거래 조회"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.get(
            f"/api/v1/transactions/{fake_id}",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert "찾을 수 없습니다" in response.json()["detail"]
    
    def test_get_transaction_no_auth(
        self,
        client: TestClient,
        sample_transactions: list
    ):
        """인증 없이 거래 조회"""
        transaction = sample_transactions[0]
        
        response = client.get(
            f"/api/v1/transactions/{transaction.id}"
        )
        
        assert response.status_code == 401


class TestAssetTransactionsList:
    """자산별 거래 조회 테스트 (GET /api/v1/transactions/assets/{asset_id}/transactions)"""
    
    def test_get_asset_transactions_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_stock_asset: Asset,
        sample_transactions: list
    ):
        """자산별 거래 조회 성공"""
        response = client.get(
            f"/api/v1/transactions/assets/{test_stock_asset.id}/transactions",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 15  # 주식 거래 15건
        assert len(data["items"]) == 15
        
        for item in data["items"]:
            assert item["asset_id"] == test_stock_asset.id
    
    def test_get_asset_transactions_with_type_filter(
        self,
        client: TestClient,
        auth_header: dict,
        test_stock_asset: Asset,
        sample_transactions: list
    ):
        """자산별 거래 조회 + 타입 필터"""
        response = client.get(
            f"/api/v1/transactions/assets/{test_stock_asset.id}/transactions?type=buy",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # buy 타입만 (인덱스 0, 3, 6, 9, 12 = 5건)
        assert data["total"] == 5
        for item in data["items"]:
            assert item["type"] == "buy"
    
    def test_get_asset_transactions_with_date_filter(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        sample_transactions: list
    ):
        """자산별 거래 조회 + 날짜 필터"""
        start_date = "2025-11-08T00:00:00"
        
        response = client.get(
            f"/api/v1/transactions/assets/{test_cash_asset.id}/transactions?start_date={start_date}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 11/8 이후 거래 (11/8 ~ 11/15, 8일 = 8건)
        assert data["total"] == 8
    
    def test_get_asset_transactions_pagination(
        self,
        client: TestClient,
        auth_header: dict,
        test_stock_asset: Asset,
        sample_transactions: list
    ):
        """자산별 거래 조회 + 페이지네이션"""
        response = client.get(
            f"/api/v1/transactions/assets/{test_stock_asset.id}/transactions?page=1&size=5",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["size"] == 5
        assert data["total"] == 15
        assert data["pages"] == 3
        assert len(data["items"]) == 5
    
    def test_get_asset_transactions_invalid_asset(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 자산의 거래 조회"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.get(
            f"/api/v1/transactions/assets/{fake_id}/transactions",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert "자산을 찾을 수 없습니다" in response.json()["detail"]


class TestTransactionsSorting:
    """거래 정렬 테스트"""
    
    def test_default_sorting_latest_first(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """기본 정렬: 최신 거래 먼저"""
        response = client.get(
            "/api/v1/transactions?size=30",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # transaction_date 내림차순
        dates = [datetime.fromisoformat(item["transaction_date"].replace('Z', '+00:00')) 
                 for item in data["items"]]
        
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1]
    
    def test_sorting_consistency(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """페이지 간 정렬 일관성"""
        # 첫 페이지
        response1 = client.get(
            "/api/v1/transactions?page=1&size=10",
            headers=auth_header
        )
        # 두 번째 페이지
        response2 = client.get(
            "/api/v1/transactions?page=2&size=10",
            headers=auth_header
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        items1 = response1.json()["items"]
        items2 = response2.json()["items"]
        
        # 첫 페이지 마지막 날짜 >= 두 번째 페이지 첫 날짜
        last_date_page1 = datetime.fromisoformat(items1[-1]["transaction_date"].replace('Z', '+00:00'))
        first_date_page2 = datetime.fromisoformat(items2[0]["transaction_date"].replace('Z', '+00:00'))
        
        assert last_date_page1 >= first_date_page2


class TestTransactionsResponseStructure:
    """거래 응답 구조 검증"""
    
    def test_transaction_response_fields(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """거래 응답 필드 검증"""
        response = client.get(
            "/api/v1/transactions?size=1",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        item = data["items"][0]
        
        # 필수 필드 존재 확인
        required_fields = [
            "id", "asset_id", "type", "quantity", "price",
            "fee", "tax", "realized_profit", "transaction_date",
            "description", "is_confirmed", "created_at", "updated_at", "asset"
        ]
        
        for field in required_fields:
            assert field in item, f"Missing field: {field}"
        
        # asset 하위 필드 확인
        asset_fields = ["id", "name", "asset_type", "currency", "is_active"]
        for field in asset_fields:
            assert field in item["asset"], f"Missing asset field: {field}"
    
    def test_pagination_metadata(
        self,
        client: TestClient,
        auth_header: dict,
        sample_transactions: list
    ):
        """페이지네이션 메타데이터 검증"""
        response = client.get(
            "/api/v1/transactions?page=2&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 메타데이터 필드 확인
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        
        # 값 검증
        assert isinstance(data["items"], list)
        assert data["total"] == 30
        assert data["page"] == 2
        assert data["size"] == 10
        assert data["pages"] == 3
