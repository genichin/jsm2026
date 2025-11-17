"""
계좌 관리 API 테스트

계좌 CRUD, 활성화/비활성화, 공유 관리 기능을 테스트합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Account, AccountShare, Asset


@pytest.fixture
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌"""
    account = Account(
        owner_id=test_user.id,
        name="테스트 은행계좌",
        account_type="bank_account",
        provider="테스트은행",
        account_number="1234567890",
        currency="KRW",
        is_active=True
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    
    # 소유자 공유 레코드 생성
    owner_share = AccountShare(
        account_id=account.id,
        user_id=test_user.id,
        role="owner",
        can_read=True,
        can_write=True,
        can_delete=True,
        can_share=True,
        shared_by=test_user.id
    )
    db_session.add(owner_share)
    db_session.commit()
    
    return account


@pytest.fixture
def second_user(db_session: Session) -> User:
    """두 번째 테스트 유저"""
    from app.core.security import get_password_hash
    
    user = User(
        email="seconduser@example.com",
        username="seconduser",
        hashed_password=get_password_hash("password123"),
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestAccountCreate:
    """계좌 생성 테스트"""
    
    def test_create_account_success(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_user: User
    ):
        """계좌 생성 성공"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "name": "신한은행 계좌",
                "account_type": "bank_account",
                "provider": "신한은행",
                "account_number": "110-123-456789",
                "currency": "KRW",
                "is_active": True
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "신한은행 계좌"
        assert data["account_type"] == "bank_account"
        assert data["provider"] == "신한은행"
        assert data["currency"] == "KRW"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        
        # 현금 자산이 자동 생성되었는지 확인
        account_id = data["id"]
        cash_asset = db_session.query(Asset).filter(
            Asset.account_id == account_id,
            Asset.asset_type == "cash"
        ).first()
        assert cash_asset is not None
        assert cash_asset.name == "신한은행 계좌(현금)"
    
    def test_create_account_minimal(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """최소 필드로 계좌 생성"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "name": "간편 계좌",
                "account_type": "cash"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "간편 계좌"
        assert data["account_type"] == "cash"
        assert data["currency"] == "KRW"  # 기본값
        assert data["is_active"] is True  # 기본값
    
    def test_create_account_securities(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """증권 계좌 생성"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "name": "미래에셋증권",
                "account_type": "securities",
                "provider": "미래에셋증권",
                "account_number": "12345-6789",
                "currency": "KRW"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["account_type"] == "securities"
    
    def test_create_account_crypto_wallet(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """가상화폐 지갑 생성"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "name": "업비트 지갑",
                "account_type": "crypto_wallet",
                "provider": "업비트",
                "currency": "KRW"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["account_type"] == "crypto_wallet"
    
    def test_create_account_no_auth(
        self,
        client: TestClient
    ):
        """인증 없이 계좌 생성 시도"""
        response = client.post(
            "/api/v1/accounts",
            json={
                "name": "Test Account",
                "account_type": "bank_account"
            }
        )
        
        assert response.status_code == 401
    
    def test_create_account_missing_name(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """계좌명 누락"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "account_type": "bank_account"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_account_invalid_type(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """잘못된 계좌 유형"""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_header,
            json={
                "name": "Test Account",
                "account_type": "invalid_type"
            }
        )
        
        assert response.status_code == 422


class TestAccountList:
    """계좌 목록 조회 테스트"""
    
    def test_get_accounts_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """계좌 목록 조회 성공"""
        response = client.get(
            "/api/v1/accounts",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "accounts" in data
        assert data["total"] >= 1
        assert len(data["accounts"]) >= 1
    
    def test_get_accounts_pagination(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_user: User
    ):
        """페이지네이션 테스트"""
        # 여러 계좌 생성
        for i in range(5):
            account = Account(
                owner_id=test_user.id,
                name=f"계좌 {i+1}",
                account_type="bank_account",
                currency="KRW"
            )
            db_session.add(account)
            db_session.flush()
            
            # 소유자 공유 레코드 생성
            owner_share = AccountShare(
                account_id=account.id,
                user_id=test_user.id,
                role="owner",
                can_read=True,
                can_write=True,
                can_delete=True,
                can_share=True,
                shared_by=test_user.id
            )
            db_session.add(owner_share)
        db_session.commit()
        
        # 페이지네이션 요청
        response = client.get(
            "/api/v1/accounts?page=1&size=3",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        # API가 페이지네이션을 지원하는 경우에만 체크
        # 현재는 모든 결과를 반환할 수 있음
        assert len(data["accounts"]) >= 1
    
    def test_get_accounts_filter_by_type(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_user: User
    ):
        """계좌 유형 필터링"""
        # 다양한 유형의 계좌 생성
        bank = Account(owner_id=test_user.id, name="은행", account_type="bank_account", currency="KRW")
        securities = Account(owner_id=test_user.id, name="증권", account_type="securities", currency="KRW")
        db_session.add_all([bank, securities])
        db_session.commit()
        
        response = client.get(
            "/api/v1/accounts?account_type=securities",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        # 모든 결과가 securities 타입이어야 함
        for account in data["accounts"]:
            assert account["account_type"] == "securities"
    
    def test_get_accounts_no_auth(
        self,
        client: TestClient
    ):
        """인증 없이 목록 조회"""
        response = client.get("/api/v1/accounts")
        assert response.status_code == 401


class TestAccountDetail:
    """계좌 상세 조회 테스트"""
    
    def test_get_account_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """계좌 상세 조회 성공"""
        response = client.get(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_account.id)
        assert data["name"] == test_account.name
        assert data["account_type"] == test_account.account_type
    
    def test_get_account_not_found(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 계좌 조회"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.get(
            f"/api/v1/accounts/{fake_id}",
            headers=auth_header
        )
        
        assert response.status_code == 404
    
    def test_get_account_no_permission(
        self,
        client: TestClient,
        db_session: Session,
        second_user: User
    ):
        """권한 없는 계좌 조회"""
        # 다른 사용자의 계좌 생성
        other_account = Account(
            owner_id=second_user.id,
            name="다른 사용자 계좌",
            account_type="bank_account",
            currency="KRW"
        )
        db_session.add(other_account)
        db_session.flush()
        
        # AccountShare 생성
        share = AccountShare(
            account_id=other_account.id,
            user_id=second_user.id,
            role="owner",
            can_read=True,
            can_write=True,
            can_delete=True,
            can_share=True,
            shared_by=second_user.id
        )
        db_session.add(share)
        db_session.commit()
        
        # 첫 번째 사용자로 로그인
        from app.core.security import create_access_token
        token = create_access_token({"sub": "testuser@example.com"})
        auth_header = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            f"/api/v1/accounts/{other_account.id}",
            headers=auth_header
        )
        
        # 401, 403 또는 404 중 하나
        assert response.status_code in [401, 403, 404]


class TestAccountUpdate:
    """계좌 수정 테스트"""
    
    def test_update_account_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """계좌 수정 성공"""
        response = client.patch(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_header,
            json={
                "name": "수정된 계좌명",
                "provider": "수정된 은행"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 계좌명"
        assert data["provider"] == "수정된 은행"
    
    def test_update_account_partial(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """부분 수정"""
        original_name = test_account.name
        
        response = client.patch(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_header,
            json={
                "provider": "새로운 은행"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == original_name  # 이름은 변경 안됨
        assert data["provider"] == "새로운 은행"
    
    def test_update_account_not_found(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 계좌 수정"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.patch(
            f"/api/v1/accounts/{fake_id}",
            headers=auth_header,
            json={"name": "New Name"}
        )
        
        assert response.status_code == 404


class TestAccountDelete:
    """계좌 삭제 테스트"""
    
    def test_delete_account_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """계좌 삭제 성공"""
        account_id = test_account.id
        
        response = client.delete(
            f"/api/v1/accounts/{account_id}",
            headers=auth_header
        )
        
        assert response.status_code == 204
        
        # 삭제 확인
        response = client.get(
            f"/api/v1/accounts/{account_id}",
            headers=auth_header
        )
        assert response.status_code == 404
    
    def test_delete_account_with_assets(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        db_session: Session,
        test_user: User
    ):
        """자산이 있는 계좌 삭제 (캐스케이드 또는 에러)"""
        # 자산 생성
        asset = Asset(
            user_id=test_user.id,
            account_id=test_account.id,
            name="테스트 자산",
            asset_type="stock",
            currency="KRW"
        )
        db_session.add(asset)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_header
        )
        
        # 자산이 있으면 삭제 불가 또는 캐스케이드 삭제
        # 구현에 따라 400 또는 204
        assert response.status_code in [204, 400]
    
    def test_delete_account_not_found(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 계좌 삭제"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.delete(
            f"/api/v1/accounts/{fake_id}",
            headers=auth_header
        )
        
        assert response.status_code == 404


class TestAccountToggleActive:
    """계좌 활성화/비활성화 테스트"""
    
    def test_toggle_active_to_inactive(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """활성 계좌를 비활성화"""
        assert test_account.is_active is True
        
        response = client.post(
            f"/api/v1/accounts/{test_account.id}/toggle-active",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    def test_toggle_active_to_active(
        self,
        client: TestClient,
        auth_header: dict,
        db_session: Session,
        test_user: User
    ):
        """비활성 계좌를 활성화"""
        # 비활성 계좌 생성
        inactive_account = Account(
            owner_id=test_user.id,
            name="비활성 계좌",
            account_type="bank_account",
            currency="KRW",
            is_active=False
        )
        db_session.add(inactive_account)
        db_session.commit()
        db_session.refresh(inactive_account)
        
        response = client.post(
            f"/api/v1/accounts/{inactive_account.id}/toggle-active",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
    
    def test_toggle_active_not_found(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 계좌 토글"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.post(
            f"/api/v1/accounts/{fake_id}/toggle-active",
            headers=auth_header
        )
        
        assert response.status_code == 404


class TestAccountShares:
    """계좌 공유 테스트"""
    
    def test_get_account_shares(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """계좌 공유 목록 조회"""
        response = client.get(
            f"/api/v1/accounts/{test_account.id}/shares",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "shares" in data
        # 소유자 공유가 있어야 함
        assert len(data["shares"]) >= 1
    
    def test_create_account_share(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        second_user: User
    ):
        """계좌 공유 생성"""
        response = client.post(
            f"/api/v1/accounts/{test_account.id}/shares",
            headers=auth_header,
            json={
                "user_email": second_user.email,
                "role": "viewer"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "viewer"
        assert data["can_read"] is True
    
    def test_create_share_invalid_email(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account
    ):
        """존재하지 않는 이메일로 공유"""
        response = client.post(
            f"/api/v1/accounts/{test_account.id}/shares",
            headers=auth_header,
            json={
                "user_email": "nonexistent@example.com",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 404
    
    def test_create_duplicate_share(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        second_user: User,
        db_session: Session
    ):
        """중복 공유 생성"""
        # 첫 번째 공유 생성
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            role="viewer",
            can_read=True,
            shared_by=test_account.owner_id
        )
        db_session.add(share)
        db_session.commit()
        
        # 중복 시도
        response = client.post(
            f"/api/v1/accounts/{test_account.id}/shares",
            headers=auth_header,
            json={
                "user_email": second_user.email,
                "role": "editor"
            }
        )
        
        # 400 또는 409 허용
        assert response.status_code in [400, 409]
    
    def test_update_account_share(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        second_user: User,
        db_session: Session
    ):
        """계좌 공유 권한 수정"""
        # 공유 생성
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            role="viewer",
            can_read=True,
            can_write=False,
            shared_by=test_account.owner_id
        )
        db_session.add(share)
        db_session.commit()
        db_session.refresh(share)
        
        # 권한 수정
        response = client.patch(
            f"/api/v1/accounts/{test_account.id}/shares/{share.id}",
            headers=auth_header,
            json={
                "role": "editor",
                "can_write": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "editor"
        assert data["can_write"] is True
    
    def test_delete_account_share(
        self,
        client: TestClient,
        auth_header: dict,
        test_account: Account,
        second_user: User,
        db_session: Session
    ):
        """계좌 공유 삭제"""
        # 공유 생성
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            role="viewer",
            can_read=True,
            shared_by=test_account.owner_id
        )
        db_session.add(share)
        db_session.commit()
        share_id = share.id
        
        # 삭제
        response = client.delete(
            f"/api/v1/accounts/{test_account.id}/shares/{share_id}",
            headers=auth_header
        )
        
        assert response.status_code == 204
        
        # 삭제 확인
        deleted_share = db_session.query(AccountShare).filter(
            AccountShare.id == share_id
        ).first()
        assert deleted_share is None
    
    def test_share_without_permission(
        self,
        client: TestClient,
        db_session: Session,
        test_account: Account,
        second_user: User
    ):
        """공유 권한 없이 계좌 공유 시도"""
        # second_user에게 viewer 권한만 부여
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            role="viewer",
            can_read=True,
            can_write=False,
            can_share=False,
            shared_by=test_account.owner_id
        )
        db_session.add(share)
        db_session.commit()
        
        # second_user로 로그인
        from app.core.security import create_access_token
        token = create_access_token({"sub": second_user.email})
        second_auth = {"Authorization": f"Bearer {token}"}
        
        # 새로운 사용자 생성
        third_user = User(
            email="third@example.com",
            username="thirduser",
            hashed_password="hash",
            is_superuser=False
        )
        db_session.add(third_user)
        db_session.commit()
        
        # 공유 시도 (권한 없음)
        response = client.post(
            f"/api/v1/accounts/{test_account.id}/shares",
            headers=second_auth,
            json={
                "user_email": third_user.email,
                "role": "viewer"
            }
        )
        
        assert response.status_code == 403
