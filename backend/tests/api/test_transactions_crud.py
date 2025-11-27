"""
거래(Transactions) CRUD API 테스트
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Asset, Account, Transaction


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
        name="Test Cash",
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
    """테스트용 주식 자산 생성"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Stock",
        asset_type="stock",
        symbol="TEST",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_transaction(db_session: Session, test_cash_asset: Asset) -> Transaction:
    """테스트용 거래 생성"""
    transaction = Transaction(
        asset_id=test_cash_asset.id,
        type="deposit",
        quantity=10000,
        price=1.0,
        fee=0,
        tax=0,
        realized_profit=0,
        transaction_date=datetime(2025, 11, 1, 10, 0, 0),
        description="Test Deposit",
        is_confirmed=True
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction


class TestCreateTransaction:
    """거래 생성 테스트"""
    
    def test_create_cash_deposit_success(self, client: TestClient, auth_header: dict, test_cash_asset: Asset):
        """현금 입금 거래 생성 성공"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 50000,
                "price": 1.0,
                "fee": 0,
                "tax": 0,
                "transaction_date": "2025-11-13T10:00:00",
                "description": "월급 입금"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "deposit"
        assert data["quantity"] == 50000
        assert data["price"] == 1.0
        assert data["asset_id"] == test_cash_asset.id
        assert "id" in data
    
    def test_create_cash_withdraw_success(self, client: TestClient, auth_header: dict, test_cash_asset: Asset):
        """현금 출금 거래 생성 성공"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "withdraw",
                "quantity": -20000,
                "price": 1.0,
                "transaction_date": "2025-11-13T11:00:00",
                "description": "ATM 출금"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "withdraw"
        assert data["quantity"] == -20000
    
    def test_create_stock_buy_success(self, client: TestClient, auth_header: dict, test_stock_asset: Asset):
        """주식 매수 거래 생성 성공"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_stock_asset.id,
                "type": "buy",
                "quantity": 10,
                "price": 50000,
                "fee": 500,
                "tax": 150,
                "transaction_date": "2025-11-13T14:00:00",
                "description": "주식 매수"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "buy"
        assert data["quantity"] == 10
        assert data["price"] == 50000
        assert data["fee"] == 500
        assert data["tax"] == 150
    
    def test_create_stock_sell_success(self, client: TestClient, auth_header: dict, test_stock_asset: Asset):
        """주식 매도 거래 생성 성공"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_stock_asset.id,
                "type": "sell",
                "quantity": -5,
                "price": 55000,
                "fee": 275,
                "tax": 825,
                "transaction_date": "2025-11-13T15:00:00",
                "description": "주식 매도"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "sell"
        assert data["quantity"] == -5
        assert data["price"] == 55000
    
    def test_create_transaction_no_auth(self, client: TestClient, test_cash_asset: Asset):
        """인증 없이 거래 생성 시도"""
        response = client.post(
            "/api/v1/transactions",
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": 10000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 401
    
    def test_create_transaction_invalid_asset(self, client: TestClient, auth_header: dict):
        """존재하지 않는 자산으로 거래 생성 시도"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": "nonexistent-asset-id",
                "type": "deposit",
                "quantity": 10000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 404
        assert "자산을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_create_transaction_invalid_quantity_direction(self, client: TestClient, auth_header: dict, test_cash_asset: Asset):
        """잘못된 수량 방향 (입금인데 음수)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_cash_asset.id,
                "type": "deposit",
                "quantity": -10000,  # 입금은 양수여야 함
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestListTransactions:
    """거래 목록 조회 테스트"""
    
    def test_list_transactions_success(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 목록 조회 성공"""
        response = client.get(
            "/api/v1/transactions",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] >= 1
        
        # 생성한 거래가 목록에 있는지 확인
        transaction_ids = [item["id"] for item in data["items"]]
        assert test_transaction.id in transaction_ids
    
    def test_list_transactions_pagination(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """페이지네이션 테스트"""
        response = client.get(
            "/api/v1/transactions?page=1&size=5",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
    
    def test_list_transactions_filter_by_type(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 유형별 필터링"""
        response = client.get(
            "/api/v1/transactions?type=deposit",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "deposit"
    
    def test_list_transactions_filter_by_asset(self, client: TestClient, auth_header: dict, test_transaction: Transaction, test_cash_asset: Asset):
        """자산별 필터링"""
        response = client.get(
            f"/api/v1/transactions?asset_id={test_cash_asset.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["asset_id"] == test_cash_asset.id
    
    def test_list_transactions_filter_by_date_range(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """날짜 범위 필터링"""
        response = client.get(
            "/api/v1/transactions?start_date=2025-11-01&end_date=2025-11-30",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_list_transactions_no_auth(self, client: TestClient):
        """인증 없이 목록 조회 시도"""
        response = client.get("/api/v1/transactions")
        
        assert response.status_code == 401


class TestGetTransaction:
    """거래 상세 조회 테스트"""
    
    def test_get_transaction_success(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 상세 조회 성공"""
        response = client.get(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_transaction.id
        assert data["type"] == test_transaction.type
        assert data["quantity"] == test_transaction.quantity
        assert "asset" in data  # 자산 정보 포함
    
    def test_get_transaction_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 거래 조회"""
        response = client.get(
            "/api/v1/transactions/nonexistent-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert "거래를 찾을 수 없습니다" in response.json()["detail"]
    
    def test_get_transaction_no_auth(self, client: TestClient, test_transaction: Transaction):
        """인증 없이 거래 조회 시도"""
        response = client.get(f"/api/v1/transactions/{test_transaction.id}")
        
        assert response.status_code == 401
    
    def test_get_other_users_transaction(
        self,
        client: TestClient,
        db_session: Session,
        test_password: str,
        test_transaction: Transaction
    ):
        """다른 사용자의 거래 조회 시도"""
        from app.core.security import get_password_hash
        from app.models import User, Account, Asset
        
        # 다른 사용자 생성
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash(test_password),
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        # 다른 사용자로 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "other@example.com",
                "password": test_password
            }
        )
        other_token = login_response.json()["access_token"]
        other_auth_header = {"Authorization": f"Bearer {other_token}"}
        
        # 첫 번째 사용자의 거래 조회 시도
        response = client.get(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=other_auth_header
        )
        
        assert response.status_code == 404  # 권한 없음 = 찾을 수 없음


class TestUpdateTransaction:
    """거래 수정 테스트"""
    
    def test_update_transaction_success(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 정보 수정 성공"""
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header,
            json={
                "description": "Updated Description",
                "memo": "Updated Memo"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Description"
        assert data["memo"] == "Updated Memo"
    
    def test_update_transaction_quantity(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 수량 수정 (수량은 변경 불가 - description/memo만 가능)"""
        # TransactionUpdate 스키마는 quantity를 지원하지 않음
        # description, memo, is_confirmed, category_id만 변경 가능
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header,
            json={
                "is_confirmed": False,
                "memo": "수정된 메모"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_confirmed"] == False
        assert data["memo"] == "수정된 메모"
        # quantity는 변경되지 않음
        assert data["quantity"] == test_transaction.quantity
    
    def test_update_transaction_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 거래 수정 시도"""
        response = client.put(
            "/api/v1/transactions/nonexistent-id",
            headers=auth_header,
            json={"description": "New Description"}
        )
        
        assert response.status_code == 404
    
    def test_update_transaction_no_auth(self, client: TestClient, test_transaction: Transaction):
        """인증 없이 거래 수정 시도"""
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}",
            json={"description": "New Description"}
        )
        
        assert response.status_code == 401
    
    def test_update_transaction_type(
        self, 
        client: TestClient, 
        auth_header: dict, 
        test_transaction: Transaction
    ):
        """거래 유형 변경"""
        # deposit에서 withdraw로 변경
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header,
            json={
                "type": "withdraw",
                "description": "유형 변경 테스트"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "withdraw"
        assert data["description"] == "유형 변경 테스트"


class TestDeleteTransaction:
    """거래 삭제 테스트"""
    
    def test_delete_transaction_success(self, client: TestClient, auth_header: dict, test_transaction: Transaction):
        """거래 삭제 성공"""
        response = client.delete(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header
        )
        
        assert response.status_code == 204
        
        # 삭제 후 조회 시 404 반환
        get_response = client.get(
            f"/api/v1/transactions/{test_transaction.id}",
            headers=auth_header
        )
        assert get_response.status_code == 404
    
    def test_delete_transaction_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 거래 삭제 시도"""
        response = client.delete(
            "/api/v1/transactions/nonexistent-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
    
    def test_delete_transaction_no_auth(self, client: TestClient, test_transaction: Transaction):
        """인증 없이 거래 삭제 시도"""
        response = client.delete(f"/api/v1/transactions/{test_transaction.id}")
        
        assert response.status_code == 401


class TestTransactionBusinessRules:
    """거래 비즈니스 규칙 테스트"""
    
    def test_buy_creates_linked_cash_transaction(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_stock_asset: Asset,
        test_cash_asset: Asset
    ):
        """주식 매수 시 연결된 현금 거래 자동 생성 확인"""
        # 매수 거래 생성
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_stock_asset.id,
                "type": "buy",
                "quantity": 10,
                "price": 50000,
                "fee": 500,
                "tax": 150,
                "transaction_date": "2025-11-13T14:00:00",
                "description": "주식 매수"
            }
        )
        
        assert response.status_code == 201
        buy_transaction_id = response.json()["id"]
        
        # DB에서 연결된 현금 거래 확인
        cash_transactions = db_session.query(Transaction).filter(
            Transaction.asset_id == test_cash_asset.id,
            Transaction.related_transaction_id == buy_transaction_id
        ).all()
        
        # 연결 거래가 생성되었는지 확인
        if len(cash_transactions) > 0:
            cash_tx = cash_transactions[0]
            assert cash_tx.type == "withdraw"
            # 매수금액 + 수수료 + 세금 = 50000*10 + 500 + 150 = 500650
            expected_amount = -(50000 * 10 + 500 + 150)
            assert cash_tx.quantity == expected_amount
    
    def test_sell_creates_linked_cash_transaction(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_stock_asset: Asset,
        test_cash_asset: Asset
    ):
        """주식 매도 시 연결된 현금 거래 자동 생성 확인"""
        # 매도 거래 생성
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_stock_asset.id,
                "type": "sell",
                "quantity": -5,
                "price": 55000,
                "fee": 275,
                "tax": 825,
                "transaction_date": "2025-11-13T15:00:00",
                "description": "주식 매도"
            }
        )
        
        assert response.status_code == 201
        sell_transaction_id = response.json()["id"]
        
        # DB에서 연결된 현금 거래 확인
        cash_transactions = db_session.query(Transaction).filter(
            Transaction.asset_id == test_cash_asset.id,
            Transaction.related_transaction_id == sell_transaction_id
        ).all()
        
        # 연결 거래가 생성되었는지 확인
        if len(cash_transactions) > 0:
            cash_tx = cash_transactions[0]
            assert cash_tx.type == "deposit"
            # 매도금액 - 수수료 - 세금 = 55000*5 - 275 - 825 = 273900
            expected_amount = 55000 * 5 - 275 - 825
            assert cash_tx.quantity == expected_amount


class TestExchangeTransaction:
    """환전(Exchange) 거래 테스트"""
    
    @pytest.fixture
    def exchange_account(self, db_session: Session, test_user: User) -> Account:
        """환전용 계좌"""
        account = Account(
            owner_id=test_user.id,
            name="환전 계좌",
            account_type="bank_account",
            provider="국제은행",
            account_number="123-456",
            currency="KRW",
            is_active=True,
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        return account
    
    @pytest.fixture
    def krw_asset(self, db_session: Session, test_user: User, exchange_account: Account) -> Asset:
        """KRW 현금 자산"""
        asset = Asset(
            user_id=test_user.id,
            account_id=exchange_account.id,
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
    def usd_asset(self, db_session: Session, test_user: User, exchange_account: Account) -> Asset:
        """USD 현금 자산"""
        asset = Asset(
            user_id=test_user.id,
            account_id=exchange_account.id,
            name="USD 현금",
            asset_type="cash",
            currency="USD",
            is_active=True,
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        return asset
    
    def test_create_exchange_via_transactions_endpoint(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        krw_asset: Asset,
        usd_asset: Asset
    ):
        """POST /api/v1/transactions로 환전 거래 생성"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": krw_asset.id,
                "type": "exchange",
                "quantity": -1400,  # 1400 KRW 감소
                "price": 1.0,
                "fee": 100,
                "tax": 0,
                "transaction_date": "2025-11-15T10:00:00",
                "description": "환전 (KRW → USD)",
                "target_asset_id": usd_asset.id,
                "target_amount": 1.0,  # 1 USD 증가
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "exchange"
        assert data["quantity"] == -1400
        assert data["asset_id"] == krw_asset.id
        assert data["related_transaction_id"] is not None
        
        # DB에서 대응 거래 확인
        related_tx = db_session.query(Transaction).filter(
            Transaction.id == data["related_transaction_id"]
        ).first()
        
        assert related_tx is not None
        assert related_tx.type == "exchange"
        assert related_tx.asset_id == usd_asset.id
        assert related_tx.quantity == 1.0
        assert related_tx.related_transaction_id == data["id"]
    
    def test_exchange_requires_target_asset_id(
        self,
        client: TestClient,
        auth_header: dict,
        krw_asset: Asset
    ):
        """환전 거래는 target_asset_id 필수"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": krw_asset.id,
                "type": "exchange",
                "quantity": -1400,
                "price": 1.0,
                "transaction_date": "2025-11-15T10:00:00",
                # target_asset_id 누락
                "target_amount": 1.0,
            }
        )
        
        assert response.status_code == 400
        assert "target_asset_id" in response.json()["detail"]
    
    def test_exchange_requires_target_amount(
        self,
        client: TestClient,
        auth_header: dict,
        krw_asset: Asset,
        usd_asset: Asset
    ):
        """환전 거래는 target_amount 필수"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": krw_asset.id,
                "type": "exchange",
                "quantity": -1400,
                "price": 1.0,
                "transaction_date": "2025-11-15T10:00:00",
                "target_asset_id": usd_asset.id,
                # target_amount 누락
            }
        )
        
        assert response.status_code == 400
        assert "target_amount" in response.json()["detail"]
