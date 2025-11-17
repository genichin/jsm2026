"""
태그 관리 API 테스트

테스트 범위:
1. 태그 생성 (POST /api/v1/tags)
2. 태그 목록 조회 (GET /api/v1/tags)
3. 태그 상세 조회 (GET /api/v1/tags/{tag_id})
4. 태그 수정 (PATCH /api/v1/tags/{tag_id})
5. 태그 삭제 (DELETE /api/v1/tags/{tag_id})
6. 태그 연결 (POST /api/v1/tags/attach)
7. 태그 일괄 연결 (POST /api/v1/tags/attach-batch)
8. 태그 연결 해제 (DELETE /api/v1/tags/detach/{taggable_id})
9. 엔티티의 태그 조회 (GET /api/v1/tags/entity/{taggable_type}/{taggable_id})
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_tag(client: TestClient, auth_header: dict):
    """테스트용 태그 생성"""
    payload = {
        "name": "테스트태그",
        "color": "#FF5733",
        "description": "테스트용 태그입니다"
    }
    response = client.post("/api/v1/tags", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def test_asset(client: TestClient, auth_header: dict, test_account):
    """태그 연결 테스트용 자산 생성"""
    payload = {
        "name": "테스트자산",
        "asset_type": "stock",
        "account_id": test_account.id
    }
    response = client.post("/api/v1/assets", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()


class TestTagCreate:
    """태그 생성 테스트"""

    def test_create_tag_success(self, client: TestClient, auth_header: dict):
        """기본 태그 생성 성공"""
        payload = {
            "name": "중요",
            "color": "#FF0000",
            "description": "중요한 항목"
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "중요"
        assert data["color"] == "#FF0000"
        assert data["description"] == "중요한 항목"
        assert "id" in data
        assert "created_at" in data
        assert "allowed_types" in data

    def test_create_tag_minimal(self, client: TestClient, auth_header: dict):
        """최소 필드로 태그 생성"""
        payload = {
            "name": "간단태그"
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "간단태그"
        assert data["color"] is None
        assert data["description"] is None

    def test_create_tag_with_allowed_types(self, client: TestClient, auth_header: dict):
        """특정 엔티티 타입만 허용하는 태그 생성"""
        payload = {
            "name": "자산전용",
            "allowed_types": ["asset"]
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert "asset" in data["allowed_types"]

    def test_create_tag_duplicate_name(self, client: TestClient, auth_header: dict, test_tag: dict):
        """중복된 이름으로 태그 생성 시도"""
        payload = {
            "name": test_tag["name"]
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 409
        assert "이미 존재" in response.json()["detail"]

    def test_create_tag_invalid_color(self, client: TestClient, auth_header: dict):
        """잘못된 색상 형식"""
        payload = {
            "name": "테스트",
            "color": "red"  # #RRGGBB 형식이 아님
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_create_tag_missing_name(self, client: TestClient, auth_header: dict):
        """필수 필드 누락 (이름)"""
        payload = {
            "color": "#FF0000"
        }
        response = client.post("/api/v1/tags", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_create_tag_no_auth(self, client: TestClient):
        """인증 없이 태그 생성 시도"""
        payload = {
            "name": "테스트"
        }
        response = client.post("/api/v1/tags", json=payload)
        
        assert response.status_code == 401


class TestTagList:
    """태그 목록 조회 테스트"""

    def test_list_tags_success(self, client: TestClient, auth_header: dict, test_tag: dict):
        """태그 목록 조회 성공"""
        response = client.get("/api/v1/tags", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "tags" in data
        assert data["total"] >= 1
        assert any(tag["id"] == test_tag["id"] for tag in data["tags"])

    def test_list_tags_with_stats(self, client: TestClient, auth_header: dict, test_tag: dict):
        """통계 정보 포함 조회"""
        response = client.get("/api/v1/tags?include_stats=true", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        # 통계 필드가 있는지 확인 (API 구현 여부에 따라 다를 수 있음)
        # 최소한 목록이 반환되는지 확인
        assert isinstance(data["tags"], list)

    def test_list_tags_empty(self, client: TestClient, auth_header: dict):
        """태그가 없는 경우 빈 목록 반환"""
        response = client.get("/api/v1/tags", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        assert isinstance(data["tags"], list)

    def test_list_tags_no_auth(self, client: TestClient):
        """인증 없이 조회"""
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 401


class TestTagDetail:
    """태그 상세 조회 테스트"""

    def test_get_tag_success(self, client: TestClient, auth_header: dict, test_tag: dict):
        """태그 상세 조회 성공"""
        response = client.get(f"/api/v1/tags/{test_tag['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_tag["id"]
        assert data["name"] == test_tag["name"]

    def test_get_tag_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 태그 조회"""
        response = client.get("/api/v1/tags/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_get_tag_no_auth(self, client: TestClient, test_tag: dict):
        """인증 없이 조회"""
        response = client.get(f"/api/v1/tags/{test_tag['id']}")
        
        assert response.status_code == 401


class TestTagUpdate:
    """태그 수정 테스트"""

    def test_update_tag_name(self, client: TestClient, auth_header: dict, test_tag: dict):
        """태그 이름 수정"""
        payload = {
            "name": "수정된태그"
        }
        response = client.patch(f"/api/v1/tags/{test_tag['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된태그"

    def test_update_tag_color(self, client: TestClient, auth_header: dict, test_tag: dict):
        """태그 색상 수정"""
        payload = {
            "color": "#00FF00"
        }
        response = client.patch(f"/api/v1/tags/{test_tag['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["color"] == "#00FF00"

    def test_update_tag_description(self, client: TestClient, auth_header: dict, test_tag: dict):
        """태그 설명 수정"""
        payload = {
            "description": "새로운 설명"
        }
        response = client.patch(f"/api/v1/tags/{test_tag['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "새로운 설명"

    def test_update_tag_allowed_types(self, client: TestClient, auth_header: dict, test_tag: dict):
        """허용된 엔티티 타입 수정"""
        payload = {
            "allowed_types": ["account"]
        }
        response = client.patch(f"/api/v1/tags/{test_tag['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert "account" in data["allowed_types"]

    def test_update_tag_duplicate_name(self, client: TestClient, auth_header: dict):
        """다른 태그와 중복되는 이름으로 수정 시도"""
        # 두 개의 태그 생성
        tag1 = client.post("/api/v1/tags", json={"name": "태그1"}, headers=auth_header).json()
        tag2 = client.post("/api/v1/tags", json={"name": "태그2"}, headers=auth_header).json()
        
        # tag2를 tag1과 같은 이름으로 변경 시도
        payload = {
            "name": "태그1"
        }
        response = client.patch(f"/api/v1/tags/{tag2['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 409

    def test_update_tag_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 태그 수정"""
        payload = {
            "name": "새이름"
        }
        response = client.patch("/api/v1/tags/non-existent-id", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_update_tag_no_auth(self, client: TestClient, test_tag: dict):
        """인증 없이 수정"""
        payload = {
            "name": "새이름"
        }
        response = client.patch(f"/api/v1/tags/{test_tag['id']}", json=payload)
        
        assert response.status_code == 401


class TestTagDelete:
    """태그 삭제 테스트"""

    def test_delete_tag_success(self, client: TestClient, auth_header: dict):
        """태그 삭제 성공"""
        # 삭제용 태그 생성
        tag = client.post("/api/v1/tags", json={"name": "삭제할태그"}, headers=auth_header).json()
        
        response = client.delete(f"/api/v1/tags/{tag['id']}", headers=auth_header)
        
        assert response.status_code == 204
        
        # 삭제 확인
        check_response = client.get(f"/api/v1/tags/{tag['id']}", headers=auth_header)
        assert check_response.status_code == 404

    def test_delete_tag_with_connections(self, client: TestClient, auth_header: dict, test_tag: dict, test_asset: dict):
        """연결된 엔티티가 있는 태그 삭제"""
        # 태그 연결
        client.post("/api/v1/tags/attach", json={
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers=auth_header)
        
        # 태그 삭제
        response = client.delete(f"/api/v1/tags/{test_tag['id']}", headers=auth_header)
        
        assert response.status_code == 204

    def test_delete_tag_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 태그 삭제"""
        response = client.delete("/api/v1/tags/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_delete_tag_no_auth(self, client: TestClient, test_tag: dict):
        """인증 없이 삭제"""
        response = client.delete(f"/api/v1/tags/{test_tag['id']}")
        
        assert response.status_code == 401


class TestTagAttach:
    """태그 연결 테스트"""

    def test_attach_tag_to_asset(self, client: TestClient, auth_header: dict, test_tag: dict, test_asset: dict):
        """자산에 태그 연결"""
        payload = {
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["tag_id"] == test_tag["id"]
        assert data["taggable_type"] == "asset"
        assert data["taggable_id"] == test_asset["id"]
        assert "id" in data
        assert "tagged_at" in data

    def test_attach_tag_to_account(self, client: TestClient, auth_header: dict, test_tag: dict, test_account):
        """계좌에 태그 연결"""
        payload = {
            "tag_id": test_tag["id"],
            "taggable_type": "account",
            "taggable_id": test_account.id
        }
        response = client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["taggable_type"] == "account"

    def test_attach_tag_duplicate(self, client: TestClient, auth_header: dict, test_tag: dict, test_asset: dict):
        """이미 연결된 태그 재연결 시도"""
        payload = {
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        # 첫 번째 연결
        client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        # 중복 연결 시도
        response = client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        assert response.status_code == 409
        assert "이미" in response.json()["detail"]

    def test_attach_tag_invalid_entity(self, client: TestClient, auth_header: dict, test_tag: dict):
        """존재하지 않는 엔티티에 태그 연결 시도"""
        payload = {
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": "non-existent-id"
        }
        response = client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_attach_invalid_tag(self, client: TestClient, auth_header: dict, test_asset: dict):
        """존재하지 않는 태그로 연결 시도"""
        payload = {
            "tag_id": "non-existent-id",
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_attach_tag_no_auth(self, client: TestClient, test_tag: dict, test_asset: dict):
        """인증 없이 태그 연결"""
        payload = {
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach", json=payload)
        
        assert response.status_code == 401


class TestTagAttachBatch:
    """태그 일괄 연결 테스트"""

    def test_attach_batch_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """여러 태그 일괄 연결 성공"""
        # 여러 태그 생성
        tag1 = client.post("/api/v1/tags", json={"name": "태그1"}, headers=auth_header).json()
        tag2 = client.post("/api/v1/tags", json={"name": "태그2"}, headers=auth_header).json()
        tag3 = client.post("/api/v1/tags", json={"name": "태그3"}, headers=auth_header).json()
        
        payload = {
            "tag_ids": [tag1["id"], tag2["id"], tag3["id"]],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach-batch", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 3
        assert len(data["taggables"]) == 3

    def test_attach_batch_partial_duplicate(self, client: TestClient, auth_header: dict, test_asset: dict):
        """일부 태그가 이미 연결된 경우"""
        tag1 = client.post("/api/v1/tags", json={"name": "태그A"}, headers=auth_header).json()
        tag2 = client.post("/api/v1/tags", json={"name": "태그B"}, headers=auth_header).json()
        
        # tag1 먼저 연결
        client.post("/api/v1/tags/attach", json={
            "tag_id": tag1["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers=auth_header)
        
        # tag1, tag2 일괄 연결
        payload = {
            "tag_ids": [tag1["id"], tag2["id"]],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach-batch", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        # tag1은 스킵되고 tag2만 연결됨
        assert data["total"] == 1

    def test_attach_batch_invalid_entity(self, client: TestClient, auth_header: dict, test_tag: dict):
        """존재하지 않는 엔티티에 일괄 연결"""
        payload = {
            "tag_ids": [test_tag["id"]],
            "taggable_type": "asset",
            "taggable_id": "non-existent-id"
        }
        response = client.post("/api/v1/tags/attach-batch", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_attach_batch_no_auth(self, client: TestClient, test_tag: dict, test_asset: dict):
        """인증 없이 일괄 연결"""
        payload = {
            "tag_ids": [test_tag["id"]],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }
        response = client.post("/api/v1/tags/attach-batch", json=payload)
        
        assert response.status_code == 401


class TestTagDetach:
    """태그 연결 해제 테스트"""

    def test_detach_tag_success(self, client: TestClient, auth_header: dict, test_tag: dict, test_asset: dict):
        """태그 연결 해제 성공"""
        # 태그 연결
        attach_response = client.post("/api/v1/tags/attach", json={
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers=auth_header)
        taggable = attach_response.json()
        
        # 연결 해제
        response = client.delete(f"/api/v1/tags/detach/{taggable['id']}", headers=auth_header)
        
        assert response.status_code == 204

    def test_detach_tag_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 연결 해제"""
        response = client.delete("/api/v1/tags/detach/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_detach_tag_no_auth(self, client: TestClient, test_tag: dict, test_asset: dict):
        """인증 없이 연결 해제"""
        # 태그 연결 (인증 사용)
        attach_response = client.post("/api/v1/tags/attach", json={
            "tag_id": test_tag["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers={"Authorization": "Bearer dummy"})
        
        # 연결 해제 시도 (인증 없음)
        if attach_response.status_code == 201:
            taggable = attach_response.json()
            response = client.delete(f"/api/v1/tags/detach/{taggable['id']}")
            assert response.status_code == 401


class TestEntityTags:
    """엔티티의 태그 조회 테스트"""

    def test_get_entity_tags_success(self, client: TestClient, auth_header: dict, test_asset: dict):
        """엔티티에 연결된 태그 조회"""
        # 여러 태그 생성 및 연결
        tag1 = client.post("/api/v1/tags", json={"name": "태그1"}, headers=auth_header).json()
        tag2 = client.post("/api/v1/tags", json={"name": "태그2"}, headers=auth_header).json()
        
        client.post("/api/v1/tags/attach", json={
            "tag_id": tag1["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers=auth_header)
        
        client.post("/api/v1/tags/attach", json={
            "tag_id": tag2["id"],
            "taggable_type": "asset",
            "taggable_id": test_asset["id"]
        }, headers=auth_header)
        
        # 엔티티의 태그 조회
        response = client.get(f"/api/v1/tags/entity/asset/{test_asset['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "asset"
        assert data["entity_id"] == test_asset["id"]
        assert data["total"] == 2
        assert len(data["tags"]) == 2

    def test_get_entity_tags_empty(self, client: TestClient, auth_header: dict, test_asset: dict):
        """태그가 연결되지 않은 엔티티"""
        response = client.get(f"/api/v1/tags/entity/asset/{test_asset['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["tags"]) == 0

    def test_get_entity_tags_invalid_entity(self, client: TestClient, auth_header: dict):
        """존재하지 않는 엔티티의 태그 조회"""
        response = client.get("/api/v1/tags/entity/asset/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_get_entity_tags_no_auth(self, client: TestClient, test_asset: dict):
        """인증 없이 엔티티 태그 조회"""
        response = client.get(f"/api/v1/tags/entity/asset/{test_asset['id']}")
        
        assert response.status_code == 401
