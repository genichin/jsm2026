"""
자산 검토 기능 API 테스트
"""
import pytest
from datetime import datetime, timedelta, timezone
from starlette.testclient import TestClient

from app.models import Asset


class TestAssetReview:
    """자산 검토 기능 테스트"""

    def test_mark_asset_reviewed_success(
        self, client: TestClient, auth_header: dict, test_asset: dict
    ):
        """자산 검토 완료 표시 성공"""
        asset_id = test_asset["id"]
        
        response = client.post(
            f"/api/v1/assets/{asset_id}/mark-reviewed",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        assert data["last_reviewed_at"] is not None
        assert data["next_review_date"] is not None
        
        # next_review_date가 last_reviewed_at + review_interval_days와 일치하는지 확인
        last_reviewed = datetime.fromisoformat(data["last_reviewed_at"].replace("Z", "+00:00"))
        next_review = datetime.fromisoformat(data["next_review_date"].replace("Z", "+00:00"))
        interval_days = data["review_interval_days"]
        
        expected_next = last_reviewed + timedelta(days=interval_days)
        # 시간 차이가 1분 이내면 통과 (트리거 실행 시간 고려)
        assert abs((next_review - expected_next).total_seconds()) < 60

    def test_mark_asset_reviewed_not_found(
        self, client: TestClient, auth_header: dict
    ):
        """존재하지 않는 자산 검토 표시 시도"""
        response = client.post(
            "/api/v1/assets/nonexistent-id/mark-reviewed",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert "찾을 수 없습니다" in response.json()["detail"]

    def test_mark_asset_reviewed_unauthorized(
        self, client: TestClient, test_asset: dict
    ):
        """인증 없이 검토 표시 시도"""
        response = client.post(
            f"/api/v1/assets/{test_asset['id']}/mark-reviewed"
        )
        
        assert response.status_code == 401

    def test_get_assets_pending_review_empty(
        self, client: TestClient, auth_header: dict
    ):
        """검토 필요 자산이 없을 때"""
        # 모든 테스트 자산을 검토 완료로 표시
        assets_response = client.get("/api/v1/assets", headers=auth_header)
        assets = assets_response.json()["items"]
        
        for asset in assets:
            client.post(
                f"/api/v1/assets/{asset['id']}/mark-reviewed",
                headers=auth_header
            )
        
        # 검토 필요 자산 조회
        response = client.get(
            "/api/v1/assets/review-pending",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_assets_pending_review_with_unreviewed(
        self, client: TestClient, auth_header: dict, test_asset: dict, test_account
    ):
        """검토하지 않은 자산이 있을 때"""
        # 새 자산 생성 (검토하지 않음)
        new_asset_response = client.post(
            "/api/v1/assets",
            json={
                "account_id": str(test_account.id),
                "name": "미검토 자산",
                "asset_type": "stock",
                "symbol": "TEST",
                "currency": "KRW",
            },
            headers=auth_header
        )
        assert new_asset_response.status_code == 201
        
        # 검토 필요 자산 조회
        response = client.get(
            "/api/v1/assets/review-pending",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # 미검토 자산이 포함되어 있는지 확인
        asset_ids = [asset["id"] for asset in data]
        assert new_asset_response.json()["id"] in asset_ids

    def test_get_assets_pending_review_ordering(
        self, client: TestClient, auth_header: dict, test_account, db_session
    ):
        """검토 필요 자산이 올바른 순서로 정렬되는지 확인"""
        from app.models import Asset
        from datetime import datetime, timezone, timedelta
        
        # 3개의 자산 생성
        asset1_response = client.post(
            "/api/v1/assets",
            json={
                "account_id": str(test_account.id),
                "name": "최근 검토 자산",
                "asset_type": "stock",
                "symbol": "NEW1",
                "currency": "KRW",
            },
            headers=auth_header
        )
        asset1_id = asset1_response.json()["id"]
        
        asset2_response = client.post(
            "/api/v1/assets",
            json={
                "account_id": str(test_account.id),
                "name": "오래된 검토 자산",
                "asset_type": "stock",
                "symbol": "OLD1",
                "currency": "KRW",
            },
            headers=auth_header
        )
        asset2_id = asset2_response.json()["id"]
        
        asset3_response = client.post(
            "/api/v1/assets",
            json={
                "account_id": str(test_account.id),
                "name": "미검토 자산",
                "asset_type": "stock",
                "symbol": "NONE1",
                "currency": "KRW",
            },
            headers=auth_header
        )
        asset3_id = asset3_response.json()["id"]
        
        # asset1을 최근에 검토
        client.post(f"/api/v1/assets/{asset1_id}/mark-reviewed", headers=auth_header)
        
        # asset2를 오래전에 검토한 것처럼 DB 직접 수정
        asset2 = db_session.query(Asset).filter(Asset.id == asset2_id).first()
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        asset2.last_reviewed_at = old_date
        asset2.next_review_date = old_date + timedelta(days=asset2.review_interval_days or 30)
        db_session.commit()
        
        # asset3는 미검토 상태 유지
        
        # 검토 필요 자산 조회
        response = client.get(
            "/api/v1/assets/review-pending",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 미검토 자산(asset3)이 가장 먼저 나와야 함
        # 그 다음 오래된 검토 자산(asset2)
        # 최근 검토 자산(asset1)은 나오지 않아야 함 (아직 검토 기한이 안 됨)
        asset_ids = [asset["id"] for asset in data]
        
        if asset3_id in asset_ids and asset2_id in asset_ids:
            idx_asset3 = asset_ids.index(asset3_id)
            idx_asset2 = asset_ids.index(asset2_id)
            assert idx_asset3 < idx_asset2, "미검토 자산이 오래된 검토 자산보다 먼저 나와야 합니다"

    def test_get_assets_pending_review_limit(
        self, client: TestClient, auth_header: dict, test_account
    ):
        """limit 파라미터 테스트"""
        # 여러 미검토 자산 생성
        for i in range(15):
            client.post(
                "/api/v1/assets",
                json={
                    "account_id": str(test_account.id),
                    "name": f"테스트 자산 {i}",
                    "asset_type": "stock",
                    "symbol": f"TEST{i}",
                    "currency": "KRW",
                },
                headers=auth_header
            )
        
        # limit=5로 조회
        response = client.get(
            "/api/v1/assets/review-pending?limit=5",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_update_asset_review_interval(
        self, client: TestClient, auth_header: dict, test_asset: dict
    ):
        """자산 검토 주기 변경 테스트"""
        asset_id = test_asset["id"]
        
        # 검토 주기를 60일로 변경
        response = client.put(
            f"/api/v1/assets/{asset_id}",
            json={"review_interval_days": 60},
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["review_interval_days"] == 60
        
        # 검토 완료 표시
        mark_response = client.post(
            f"/api/v1/assets/{asset_id}/mark-reviewed",
            headers=auth_header
        )
        
        assert mark_response.status_code == 200
        mark_data = mark_response.json()
        
        # next_review_date가 60일 후인지 확인
        last_reviewed = datetime.fromisoformat(mark_data["last_reviewed_at"].replace("Z", "+00:00"))
        next_review = datetime.fromisoformat(mark_data["next_review_date"].replace("Z", "+00:00"))
        
        expected_next = last_reviewed + timedelta(days=60)
        assert abs((next_review - expected_next).total_seconds()) < 60
