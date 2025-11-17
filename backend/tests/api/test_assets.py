"""
자산(Assets) API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Asset, Account


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
def test_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 자산 생성"""
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


class TestCreateAsset:
    """자산 생성 테스트"""
    
    def test_create_asset_success(self, client: TestClient, auth_header: dict, test_account: Account):
        """정상 자산 생성"""
        response = client.post(
            "/api/v1/assets",
            headers=auth_header,
            json={
                "account_id": test_account.id,
                "name": "Samsung Electronics",
                "asset_type": "stock",
                "symbol": "005930",
                "currency": "KRW"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Samsung Electronics"
        assert data["asset_type"] == "stock"
        assert data["symbol"] == "005930"
        assert data["currency"] == "KRW"
        assert data["account_id"] == test_account.id
        assert "id" in data
        assert "balance" in data
        assert "price" in data
    
    def test_create_asset_no_auth(self, client: TestClient, test_account: Account):
        """인증 없이 자산 생성 시도"""
        response = client.post(
            "/api/v1/assets",
            json={
                "account_id": test_account.id,
                "name": "Test Asset",
                "asset_type": "stock"
            }
        )
        
        assert response.status_code == 401
    
    def test_create_asset_invalid_account(self, client: TestClient, auth_header: dict):
        """존재하지 않는 계좌로 자산 생성 시도"""
        response = client.post(
            "/api/v1/assets",
            headers=auth_header,
            json={
                "account_id": "nonexistent-account-id",
                "name": "Test Asset",
                "asset_type": "stock"
            }
        )
        
        assert response.status_code == 404
        assert "계좌를 찾을 수 없습니다" in response.json()["detail"]


class TestListAssets:
    """자산 목록 조회 테스트"""
    
    def test_list_assets_success(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 목록 조회 성공"""
        response = client.get(
            "/api/v1/assets",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        
        # 생성한 자산이 목록에 있는지 확인
        asset_ids = [item["id"] for item in data["items"]]
        assert test_asset.id in asset_ids
    
    def test_list_assets_pagination(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """페이지네이션 테스트"""
        response = client.get(
            "/api/v1/assets?page=1&size=10",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
    
    def test_list_assets_filter_by_type(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 유형별 필터링"""
        response = client.get(
            "/api/v1/assets?asset_type=stock",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["asset_type"] == "stock"
    
    def test_list_assets_no_auth(self, client: TestClient):
        """인증 없이 목록 조회 시도"""
        response = client.get("/api/v1/assets")
        
        assert response.status_code == 401


class TestGetAsset:
    """자산 상세 조회 테스트"""
    
    def test_get_asset_success(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 상세 조회 성공"""
        response = client.get(
            f"/api/v1/assets/{test_asset.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_asset.id
        assert data["name"] == test_asset.name
        assert data["asset_type"] == test_asset.asset_type
        assert "balance" in data
        assert "price" in data
    
    def test_get_asset_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 자산 조회"""
        response = client.get(
            "/api/v1/assets/nonexistent-asset-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert "자산을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_get_asset_no_auth(self, client: TestClient, test_asset: Asset):
        """인증 없이 자산 조회 시도"""
        response = client.get(f"/api/v1/assets/{test_asset.id}")
        
        assert response.status_code == 401
    
    def test_get_other_users_asset(
        self, 
        client: TestClient, 
        db_session: Session,
        test_password: str,
        test_asset: Asset
    ):
        """다른 사용자의 자산 조회 시도"""
        # 다른 사용자 생성 및 로그인
        from app.core.security import get_password_hash
        from app.models import User
        
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
        
        # 첫 번째 사용자의 자산에 접근 시도
        response = client.get(
            f"/api/v1/assets/{test_asset.id}",
            headers=other_auth_header
        )
        
        assert response.status_code == 404  # 권한 없음 = 찾을 수 없음


class TestUpdateAsset:
    """자산 수정 테스트"""
    
    def test_update_asset_success(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 정보 수정 성공"""
        response = client.put(
            f"/api/v1/assets/{test_asset.id}",
            headers=auth_header,
            json={
                "name": "Updated Asset Name",
                "is_active": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Asset Name"
        assert data["is_active"] == False

    def test_update_asset_currency(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 통화(currency) 변경 성공"""
        response = client.put(
            f"/api/v1/assets/{test_asset.id}",
            headers=auth_header,
            json={
                "currency": "USD"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
    
    def test_update_asset_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 자산 수정 시도"""
        response = client.put(
            "/api/v1/assets/nonexistent-id",
            headers=auth_header,
            json={"name": "New Name"}
        )
        
        assert response.status_code == 404


class TestDeleteAsset:
    """자산 삭제 테스트"""
    
    def test_delete_asset_success(self, client: TestClient, auth_header: dict, test_asset: Asset):
        """자산 삭제 성공 (하드 삭제)"""
        response = client.delete(
            f"/api/v1/assets/{test_asset.id}",
            headers=auth_header
        )
        
        assert response.status_code == 204
        
        # 삭제 후 조회 시 404 반환
        get_response = client.get(
            f"/api/v1/assets/{test_asset.id}",
            headers=auth_header
        )
        assert get_response.status_code == 404
    
    def test_delete_asset_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 자산 삭제 시도"""
        response = client.delete(
            "/api/v1/assets/nonexistent-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
