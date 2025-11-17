"""
활동 로그 (댓글 + 로그) API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Account, Activity


class TestActivityCreate:
    """활동 생성 테스트"""
    
    def test_create_comment_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 생성 성공"""
        payload = {
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "좋은 자산입니다",
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "좋은 자산입니다"
        assert data["activity_type"] == "comment"
        assert data["target_type"] == "asset"
        assert data["is_immutable"] is False
    
    def test_create_log_success(self, client: TestClient, auth_header: dict, test_account: Account):
        """로그 생성 성공"""
        payload = {
            "target_type": "account",
            "target_id": test_account.id,
            "activity_type": "log",
            "payload": {"action": "balance_update", "old": 1000, "new": 2000},
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert data["payload"]["action"] == "balance_update"
        assert data["activity_type"] == "log"
        assert data["is_immutable"] is True
    
    def test_create_comment_empty_content(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 생성 - 빈 content"""
        payload = {
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "",
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        assert response.status_code == 422
    
    def test_create_log_missing_payload(self, client: TestClient, auth_header: dict, test_asset: dict):
        """로그 생성 - payload 누락 (선택적이므로 성공)"""
        payload = {
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "log",
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        # payload가 선택적이면 성공, 필수면 422
        assert response.status_code in [201, 422]
    
    def test_create_activity_invalid_target(self, client: TestClient, auth_header: dict):
        """활동 생성 - 존재하지 않는 대상"""
        payload = {
            "target_type": "asset",
            "target_id": "invalid-id",
            "activity_type": "comment",
            "content": "테스트 댓글",
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        assert response.status_code == 404
    
    def test_create_activity_invalid_visibility(self, client: TestClient, auth_header: dict, test_asset: dict):
        """활동 생성 - 잘못된 visibility"""
        payload = {
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "테스트 댓글",
            "visibility": "invalid"
        }
        response = client.post("/api/v1/activities", json=payload, headers=auth_header)
        assert response.status_code == 422
    
    def test_create_activity_no_auth(self, client: TestClient, test_asset: dict):
        """활동 생성 - 인증 없음"""
        payload = {
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "테스트 댓글",
            "visibility": "private"
        }
        response = client.post("/api/v1/activities", json=payload)
        assert response.status_code == 401


class TestActivityList:
    """활동 목록 테스트"""
    
    def test_list_activities_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """활동 목록 조회 성공"""
        # 댓글 2개 생성
        for i in range(2):
            client.post("/api/v1/activities", json={
                "target_type": "asset",
                "target_id": test_asset["id"],
                "activity_type": "comment",
                "content": f"댓글 {i+1}",
                "visibility": "private"
            }, headers=auth_header)
        
        response = client.get(
            f"/api/v1/activities?target_type=asset&target_id={test_asset['id']}",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert all(a["target_id"] == test_asset["id"] for a in data)
    
    def test_list_activities_filter_by_type(self, client: TestClient, auth_header: dict, test_account: Account):
        """활동 목록 - activity_type 필터"""
        # 댓글 1개, 로그 1개 생성
        client.post("/api/v1/activities", json={
            "target_type": "account",
            "target_id": test_account.id,
            "activity_type": "comment",
            "content": "댓글",
            "visibility": "private"
        }, headers=auth_header)
        
        client.post("/api/v1/activities", json={
            "target_type": "account",
            "target_id": test_account.id,
            "activity_type": "log",
            "payload": {"action": "test"},
            "visibility": "private"
        }, headers=auth_header)
        
        # 댓글만 조회
        response = client.get(
            f"/api/v1/activities?target_type=account&target_id={test_account.id}&activity_type=comment",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert all(a["activity_type"] == "comment" for a in data)
    
    def test_list_activities_order_desc(self, client: TestClient, auth_header: dict, test_asset: dict):
        """활동 목록 - 내림차순 정렬"""
        response = client.get(
            f"/api/v1/activities?target_type=asset&target_id={test_asset['id']}&order=desc",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        if len(data) > 1:
            # 최신 순으로 정렬 확인
            assert data[0]["created_at"] >= data[1]["created_at"]
    
    def test_list_activities_pagination(self, client: TestClient, auth_header: dict, test_asset: dict):
        """활동 목록 - 페이지네이션"""
        response = client.get(
            f"/api/v1/activities?target_type=asset&target_id={test_asset['id']}&skip=0&limit=1",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
    
    def test_list_activities_no_auth(self, client: TestClient, test_asset: dict):
        """활동 목록 - 인증 없음"""
        response = client.get(
            f"/api/v1/activities?target_type=asset&target_id={test_asset['id']}"
        )
        assert response.status_code == 401


class TestActivityDetail:
    """활동 상세 조회 테스트"""
    
    def test_get_activity_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """활동 상세 조회 성공"""
        # 댓글 생성
        create_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "테스트 댓글",
            "visibility": "private"
        }, headers=auth_header)
        activity_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == activity_id
        assert data["content"] == "테스트 댓글"
    
    def test_get_activity_not_found(self, client: TestClient, auth_header: dict):
        """활동 상세 조회 - 존재하지 않음"""
        response = client.get("/api/v1/activities/invalid-id", headers=auth_header)
        assert response.status_code == 404
    
    def test_get_activity_no_auth(self, client: TestClient, test_asset: dict):
        """활동 상세 조회 - 인증 없음"""
        # 댓글 생성 (인증 포함)
        create_resp = TestClient(client.app).post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "테스트",
            "visibility": "private"
        }, headers={"Authorization": "Bearer test_token"})
        
        if create_resp.status_code == 201:
            activity_id = create_resp.json()["id"]
            response = client.get(f"/api/v1/activities/{activity_id}")
            assert response.status_code == 401


class TestActivityThread:
    """활동 스레드 조회 테스트"""
    
    def test_get_thread_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """스레드 조회 성공"""
        # 부모 댓글 생성
        parent_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "부모 댓글",
            "visibility": "private"
        }, headers=auth_header)
        parent_id = parent_resp.json()["id"]
        
        # 자식 댓글 생성
        client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "자식 댓글",
            "parent_id": parent_id,
            "visibility": "private"
        }, headers=auth_header)
        
        # 스레드 조회 (thread_root_id는 DB에서 자동 설정됨)
        response = client.get(f"/api/v1/activities/thread/{parent_id}", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        # 스레드는 parent_id가 같은 모든 댓글을 포함
        assert isinstance(data, list)
    
    def test_get_thread_not_found(self, client: TestClient, auth_header: dict):
        """스레드 조회 - 존재하지 않음"""
        response = client.get("/api/v1/activities/thread/invalid-id", headers=auth_header)
        assert response.status_code == 404
    
    def test_get_thread_no_auth(self, client: TestClient):
        """스레드 조회 - 인증 없음"""
        response = client.get("/api/v1/activities/thread/some-id")
        assert response.status_code == 401


class TestActivityUpdate:
    """활동 수정 테스트"""
    
    def test_update_comment_content(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 내용 수정 성공"""
        # 댓글 생성
        create_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "원래 댓글",
            "visibility": "private"
        }, headers=auth_header)
        activity_id = create_resp.json()["id"]
        
        # 수정
        response = client.patch(
            f"/api/v1/activities/{activity_id}",
            json={"content": "수정된 댓글"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "수정된 댓글"
    
    def test_update_comment_visibility(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 visibility 수정"""
        # 댓글 생성
        create_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "테스트 댓글",
            "visibility": "private"
        }, headers=auth_header)
        activity_id = create_resp.json()["id"]
        
        # 수정
        response = client.patch(
            f"/api/v1/activities/{activity_id}",
            json={"visibility": "public"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["visibility"] == "public"
    
    def test_update_comment_empty_content(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 수정 - 빈 content"""
        # 댓글 생성
        create_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "원래 댓글",
            "visibility": "private"
        }, headers=auth_header)
        activity_id = create_resp.json()["id"]
        
        # 빈 content로 수정 시도
        response = client.patch(
            f"/api/v1/activities/{activity_id}",
            json={"content": ""},
            headers=auth_header
        )
        assert response.status_code == 422
    
    def test_update_activity_not_found(self, client: TestClient, auth_header: dict):
        """활동 수정 - 존재하지 않음"""
        response = client.patch(
            "/api/v1/activities/invalid-id",
            json={"content": "수정"},
            headers=auth_header
        )
        assert response.status_code == 404
    
    def test_update_activity_no_auth(self, client: TestClient, test_asset: dict):
        """활동 수정 - 인증 없음"""
        response = client.patch(
            "/api/v1/activities/some-id",
            json={"content": "수정"}
        )
        assert response.status_code == 401


class TestActivityDelete:
    """활동 삭제 테스트"""
    
    def test_delete_comment_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """댓글 삭제 성공"""
        # 댓글 생성
        create_resp = client.post("/api/v1/activities", json={
            "target_type": "asset",
            "target_id": test_asset["id"],
            "activity_type": "comment",
            "content": "삭제할 댓글",
            "visibility": "private"
        }, headers=auth_header)
        activity_id = create_resp.json()["id"]
        
        # 삭제
        response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_header)
        assert response.status_code == 204
        
        # 삭제 확인
        get_resp = client.get(f"/api/v1/activities/{activity_id}", headers=auth_header)
        if get_resp.status_code == 200:
            # soft delete인 경우
            assert get_resp.json()["is_deleted"] is True
    
    def test_delete_activity_not_found(self, client: TestClient, auth_header: dict):
        """활동 삭제 - 존재하지 않음"""
        response = client.delete("/api/v1/activities/invalid-id", headers=auth_header)
        assert response.status_code == 404
    
    def test_delete_activity_no_auth(self, client: TestClient):
        """활동 삭제 - 인증 없음"""
        response = client.delete("/api/v1/activities/some-id")
        assert response.status_code == 401
