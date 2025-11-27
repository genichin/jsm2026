"""
경계 조건 및 에러 처리 테스트

다양한 엣지 케이스와 에러 상황을 테스트합니다.
"""

import pytest
import io
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Account, Asset, Transaction


@pytest.fixture
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌"""
    account = Account(
        owner_id=test_user.id,
        name="테스트 계좌",
        account_type="securities",
        provider="테스트증권"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 자산"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="테스트자산",
        asset_type="stock",
        symbol="TEST",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


class TestInvalidDataFormats:
    """잘못된 데이터 형식 테스트"""
    
    def test_invalid_date_format(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """잘못된 날짜 형식"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "invalid-date-format"
            }
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    def test_invalid_quantity_format(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """잘못된 수량 형식 (문자열)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": "not-a-number",
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_price_format(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """잘못된 가격 형식"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "buy",
                "quantity": 10,
                "price": "invalid-price",
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_transaction_type(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """존재하지 않는 거래 유형"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "invalid_type",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_asset_type(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """잘못된 자산 유형으로 생성"""
        response = client.post(
            "/api/v1/assets",
            headers=auth_header,
            json={
                "account_id": test_account.id,
                "name": "Invalid Asset",
                "asset_type": "invalid_type",
                "currency": "KRW"
            }
        )
        
        assert response.status_code == 422


class TestBoundaryValues:
    """경계값 테스트"""
    
    def test_zero_quantity(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """수량이 0인 거래 (스키마 검증)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "dividend",
                "quantity": 0,
                "price": 70000,
                "transaction_date": "2025-11-13T10:00:00",
                "description": "배당 마커"
            }
        )
        
        # 0 수량 불가 (스키마 검증)
        assert response.status_code == 422
    
    def test_zero_price(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """가격이 0인 거래"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "adjustment",
                "quantity": 100,
                "price": 0,
                "transaction_date": "2025-11-13T10:00:00",
                "description": "무상증자"
            }
        )
        
        # 0 가격 허용 (무상증자 등)
        assert response.status_code == 201
    
    def test_negative_fee(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """음수 수수료 (불가)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "buy",
                "quantity": 10,
                "price": 70000,
                "fee": -100,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        # 음수 수수료 불가
        assert response.status_code == 422 or response.status_code == 400
    
    def test_negative_tax(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """음수 세금 (불가)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "sell",
                "quantity": -10,
                "price": 75000,
                "tax": -50,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        # 음수 세금 불가
        assert response.status_code == 422 or response.status_code == 400
    
    def test_very_large_quantity(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """매우 큰 수량 (현실적 범위)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 99999999.99999999,  # NUMERIC(20,8) 범위 내
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert abs(float(data["quantity"]) - 99999999.99999999) < 0.00000001
    
    def test_very_large_price(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """매우 큰 가격 (현실적 범위)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "buy",
                "quantity": 1,
                "price": 9999999999.99,  # NUMERIC(15,2) 범위 내
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert abs(float(data["price"]) - 9999999999.99) < 0.01
    
    def test_very_small_decimal(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """매우 작은 소수점 (가상화폐 등)"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 0.00000001,  # 최소 단위
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert abs(float(data["quantity"]) - 0.00000001) < 0.000000001


class TestMissingRequiredFields:
    """필수 필드 누락 테스트"""
    
    def test_missing_asset_id(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """asset_id 누락"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_type(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """type 누락"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_quantity(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """quantity 누락"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_price(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """price 누락"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_transaction_date(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """transaction_date 누락"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0
            }
        )
        
        assert response.status_code == 422


class TestResourceNotFound:
    """리소스 없음 테스트"""
    
    def test_nonexistent_asset(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 자산으로 거래 생성"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": fake_uuid,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00"
            }
        )
        
        assert response.status_code == 404
        assert "자산" in response.json()["detail"]
    
    def test_nonexistent_transaction(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 거래 조회"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = client.get(
            f"/api/v1/transactions/{fake_uuid}",
            headers=auth_header
        )
        
        assert response.status_code == 404
    
    def test_nonexistent_account(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 계좌로 자산 생성"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = client.post(
            "/api/v1/assets",
            headers=auth_header,
            json={
                "account_id": fake_uuid,
                "name": "Test Asset",
                "asset_type": "stock",
                "currency": "KRW"
            }
        )
        
        assert response.status_code == 404


class TestFileUploadErrors:
    """파일 업로드 에러 테스트"""
    
    def test_empty_file_upload(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """빈 파일 업로드"""
        empty_file = io.BytesIO(b"")
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("empty.csv", empty_file, "text/csv")},
            data={
                "asset_id": test_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 400
    
    def test_invalid_file_type(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """지원하지 않는 파일 형식"""
        invalid_file = io.BytesIO(b"This is a text file")
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("file.txt", invalid_file, "text/plain")},
            data={
                "asset_id": test_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 400
    
    def test_corrupted_csv_file(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """손상된 CSV 파일"""
        corrupted_csv = io.BytesIO(b"invalid,csv,data\n\x00\x01\x02corrupt")
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("corrupted.csv", corrupted_csv, "text/csv")},
            data={
                "asset_id": test_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 400
    
    def test_upload_without_file(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """파일 없이 업로드 요청"""
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            data={
                "asset_id": test_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 422


class TestPaginationEdgeCases:
    """페이지네이션 경계 테스트"""
    
    def test_page_zero(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """페이지 번호 0 (최소값 위반)"""
        response = client.get(
            "/api/v1/transactions?page=0&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 422
    
    def test_negative_page(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """음수 페이지 번호"""
        response = client.get(
            "/api/v1/transactions?page=-1&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 422
    
    def test_zero_size(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """사이즈 0"""
        response = client.get(
            "/api/v1/transactions?page=1&size=0",
            headers=auth_header
        )
        
        assert response.status_code == 422
    
    def test_excessive_size(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """과도한 사이즈 (최대값 초과)"""
        response = client.get(
            "/api/v1/transactions?page=1&size=1000",
            headers=auth_header
        )
        
        # 최대값 제한 (100)
        assert response.status_code == 422
    
    def test_non_numeric_page(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """숫자가 아닌 페이지 번호"""
        response = client.get(
            "/api/v1/transactions?page=abc&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 422


class TestConcurrencyAndRaceConditions:
    """동시성 및 경합 조건 테스트"""
    
    def test_update_deleted_transaction(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset,
        db_session: Session
    ):
        """삭제된 거래 수정 시도"""
        # 거래 생성
        tx = Transaction(
            asset_id=test_asset.id,
            type="deposit",
            quantity=1000,
            price=1.0,
            transaction_date=datetime(2025, 11, 13, 10, 0, 0),
            description="Test"
        )
        db_session.add(tx)
        db_session.commit()
        tx_id = tx.id
        
        # 거래 삭제
        db_session.delete(tx)
        db_session.commit()
        
        # 삭제된 거래 수정 시도
        response = client.put(
            f"/api/v1/transactions/{tx_id}",
            headers=auth_header,
            json={
                "quantity": 2000
            }
        )
        
        assert response.status_code == 404
    
    def test_delete_already_deleted_transaction(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset,
        db_session: Session
    ):
        """이미 삭제된 거래 재삭제"""
        # 거래 생성
        tx = Transaction(
            asset_id=test_asset.id,
            type="deposit",
            quantity=1000,
            price=1.0,
            transaction_date=datetime(2025, 11, 13, 10, 0, 0),
            description="Test"
        )
        db_session.add(tx)
        db_session.commit()
        tx_id = tx.id
        
        # 첫 번째 삭제
        response1 = client.delete(
            f"/api/v1/transactions/{tx_id}",
            headers=auth_header
        )
        assert response1.status_code == 204
        
        # 두 번째 삭제 시도
        response2 = client.delete(
            f"/api/v1/transactions/{tx_id}",
            headers=auth_header
        )
        assert response2.status_code == 404


class TestSpecialCharacters:
    """특수 문자 처리 테스트"""
    
    def test_unicode_in_description(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """설명에 유니코드 문자"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00",
                "description": "한글 설명 🎉 émojis ñ ü"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "한글 설명" in data["description"]
        assert "🎉" in data["description"]
    
    def test_very_long_description(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """매우 긴 설명"""
        long_description = "A" * 10000  # 10KB
        
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00",
                "description": long_description
            }
        )
        
        # TEXT 타입이므로 허용되어야 함
        assert response.status_code == 201
    
    def test_sql_injection_attempt(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: Asset
    ):
        """SQL 인젝션 시도"""
        response = client.post(
            "/api/v1/transactions",
            headers=auth_header,
            json={
                "asset_id": test_asset.id,
                "type": "deposit",
                "quantity": 1000,
                "price": 1.0,
                "transaction_date": "2025-11-13T10:00:00",
                "description": "'; DROP TABLE transactions; --"
            }
        )
        
        # 정상 처리 (SQLAlchemy가 자동으로 이스케이프)
        assert response.status_code == 201
        
        # 거래 목록이 여전히 조회되는지 확인
        response2 = client.get("/api/v1/transactions", headers=auth_header)
        assert response2.status_code == 200
