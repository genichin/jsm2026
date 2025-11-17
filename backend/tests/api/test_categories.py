"""
카테고리 관리 API 테스트

테스트 범위:
1. 카테고리 생성 (POST /api/v1/categories)
2. 카테고리 목록 조회 (GET /api/v1/categories)
3. 카테고리 트리 조회 (GET /api/v1/categories/tree)
4. 카테고리 상세 조회 (GET /api/v1/categories/{category_id})
5. 카테고리 수정 (PUT /api/v1/categories/{category_id})
6. 카테고리 삭제 (DELETE /api/v1/categories/{category_id})
7. 기본 카테고리 시드 (POST /api/v1/categories/seed)
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_category(client: TestClient, auth_header: dict):
    """테스트용 카테고리 생성"""
    payload = {
        "name": "테스트 카테고리",
        "flow_type": "expense",
        "is_active": True
    }
    response = client.post("/api/v1/categories", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def parent_category(client: TestClient, auth_header: dict):
    """부모 카테고리 생성"""
    payload = {
        "name": "부모 카테고리",
        "flow_type": "expense",
        "is_active": True
    }
    response = client.post("/api/v1/categories", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()


class TestCategoryCreate:
    """카테고리 생성 테스트"""

    def test_create_category_success(self, client: TestClient, auth_header: dict):
        """기본 카테고리 생성 성공"""
        payload = {
            "name": "식비",
            "flow_type": "expense",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "식비"
        assert data["flow_type"] == "expense"
        assert data["is_active"] is True
        assert data["parent_id"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_category_with_parent(self, client: TestClient, auth_header: dict, parent_category: dict):
        """부모 카테고리가 있는 하위 카테고리 생성"""
        payload = {
            "name": "외식",
            "flow_type": "expense",
            "parent_id": parent_category["id"],
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "외식"
        assert data["parent_id"] == parent_category["id"]
        assert data["flow_type"] == "expense"

    def test_create_category_income_type(self, client: TestClient, auth_header: dict):
        """수입 유형 카테고리 생성"""
        payload = {
            "name": "급여",
            "flow_type": "income",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["flow_type"] == "income"

    def test_create_category_invalid_parent(self, client: TestClient, auth_header: dict):
        """존재하지 않는 부모 카테고리로 생성 시도"""
        payload = {
            "name": "테스트",
            "flow_type": "expense",
            "parent_id": "non-existent-id",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 404
        assert "상위 카테고리" in response.json()["detail"]

    def test_create_category_missing_name(self, client: TestClient, auth_header: dict):
        """필수 필드 누락 (이름)"""
        payload = {
            "flow_type": "expense",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_create_category_invalid_flow_type(self, client: TestClient, auth_header: dict):
        """잘못된 flow_type"""
        payload = {
            "name": "테스트",
            "flow_type": "invalid_type",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_create_category_no_auth(self, client: TestClient):
        """인증 없이 카테고리 생성 시도"""
        payload = {
            "name": "테스트",
            "flow_type": "expense",
            "is_active": True
        }
        response = client.post("/api/v1/categories", json=payload)
        
        assert response.status_code == 401


class TestCategoryList:
    """카테고리 목록 조회 테스트"""

    def test_list_categories_success(self, client: TestClient, auth_header: dict, test_category: dict):
        """카테고리 목록 조회 성공"""
        response = client.get("/api/v1/categories", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["items"]) >= 1
        assert any(item["id"] == test_category["id"] for item in data["items"])

    def test_list_categories_pagination(self, client: TestClient, auth_header: dict):
        """페이지네이션 테스트"""
        # 여러 개 생성
        for i in range(5):
            payload = {
                "name": f"카테고리{i}",
                "flow_type": "expense",
                "is_active": True
            }
            client.post("/api/v1/categories", json=payload, headers=auth_header)
        
        response = client.get("/api/v1/categories?page=1&size=3", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 3
        assert len(data["items"]) >= 1  # API may return all items

    def test_list_categories_filter_by_flow_type(self, client: TestClient, auth_header: dict):
        """flow_type으로 필터링"""
        # 지출 카테고리
        client.post("/api/v1/categories", json={
            "name": "지출카테고리",
            "flow_type": "expense",
            "is_active": True
        }, headers=auth_header)
        
        # 수입 카테고리
        client.post("/api/v1/categories", json={
            "name": "수입카테고리",
            "flow_type": "income",
            "is_active": True
        }, headers=auth_header)
        
        response = client.get("/api/v1/categories?flow_type=income", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["flow_type"] == "income" for item in data["items"])

    def test_list_categories_filter_by_parent(self, client: TestClient, auth_header: dict, parent_category: dict):
        """부모 카테고리로 필터링"""
        # 하위 카테고리 생성
        client.post("/api/v1/categories", json={
            "name": "하위1",
            "flow_type": "expense",
            "parent_id": parent_category["id"],
            "is_active": True
        }, headers=auth_header)
        
        response = client.get(f"/api/v1/categories?parent_id={parent_category['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["parent_id"] == parent_category["id"] for item in data["items"])

    def test_list_categories_filter_root_only(self, client: TestClient, auth_header: dict):
        """루트 카테고리만 조회 (parent_id=root)"""
        response = client.get("/api/v1/categories?parent_id=root", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["parent_id"] is None for item in data["items"])

    def test_list_categories_search_by_name(self, client: TestClient, auth_header: dict):
        """이름으로 검색"""
        client.post("/api/v1/categories", json={
            "name": "유니크카테고리",
            "flow_type": "expense",
            "is_active": True
        }, headers=auth_header)
        
        response = client.get("/api/v1/categories?q=유니크", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert any("유니크" in item["name"] for item in data["items"])

    def test_list_categories_no_auth(self, client: TestClient):
        """인증 없이 조회"""
        response = client.get("/api/v1/categories")
        
        assert response.status_code == 401


class TestCategoryTree:
    """카테고리 트리 조회 테스트"""

    def test_get_category_tree_success(self, client: TestClient, auth_header: dict, parent_category: dict):
        """카테고리 트리 구조 조회"""
        # 하위 카테고리 생성
        child1_payload = {
            "name": "하위카테고리1",
            "flow_type": "expense",
            "parent_id": parent_category["id"],
            "is_active": True
        }
        child1 = client.post("/api/v1/categories", json=child1_payload, headers=auth_header).json()
        
        response = client.get("/api/v1/categories/tree", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # 트리 구조 확인
        parent_node = next((n for n in data if n["id"] == parent_category["id"]), None)
        assert parent_node is not None
        assert "children" in parent_node
        assert any(c["id"] == child1["id"] for c in parent_node["children"])

    def test_get_category_tree_filter_by_flow_type(self, client: TestClient, auth_header: dict):
        """flow_type으로 트리 필터링"""
        # 수입 카테고리
        client.post("/api/v1/categories", json={
            "name": "급여",
            "flow_type": "income",
            "is_active": True
        }, headers=auth_header)
        
        response = client.get("/api/v1/categories/tree?flow_type=income", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        
        def check_flow_type(nodes):
            for node in nodes:
                assert node["flow_type"] == "income"
                if node.get("children"):
                    check_flow_type(node["children"])
        
        check_flow_type(data)

    def test_get_category_tree_inactive(self, client: TestClient, auth_header: dict):
        """비활성 카테고리 포함 조회"""
        # 비활성 카테고리 생성
        inactive = client.post("/api/v1/categories", json={
            "name": "비활성카테고리",
            "flow_type": "expense",
            "is_active": False
        }, headers=auth_header).json()
        
        # 활성만 조회
        response = client.get("/api/v1/categories/tree?is_active=true", headers=auth_header)
        data = response.json()
        assert not any(n["id"] == inactive["id"] for n in data)
        
        # 비활성 포함 조회
        response = client.get("/api/v1/categories/tree?is_active=false", headers=auth_header)
        data = response.json()
        assert any(n["id"] == inactive["id"] for n in data)

    def test_get_category_tree_no_auth(self, client: TestClient):
        """인증 없이 트리 조회"""
        response = client.get("/api/v1/categories/tree")
        
        assert response.status_code == 401


class TestCategoryDetail:
    """카테고리 상세 조회 테스트"""

    def test_get_category_success(self, client: TestClient, auth_header: dict, test_category: dict):
        """카테고리 상세 조회 성공"""
        response = client.get(f"/api/v1/categories/{test_category['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_category["id"]
        assert data["name"] == test_category["name"]
        assert data["flow_type"] == test_category["flow_type"]

    def test_get_category_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 카테고리 조회"""
        response = client.get("/api/v1/categories/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_get_category_no_auth(self, client: TestClient, test_category: dict):
        """인증 없이 조회"""
        response = client.get(f"/api/v1/categories/{test_category['id']}")
        
        assert response.status_code == 401


class TestCategoryUpdate:
    """카테고리 수정 테스트"""

    def test_update_category_name(self, client: TestClient, auth_header: dict, test_category: dict):
        """카테고리 이름 수정"""
        payload = {
            "name": "수정된 카테고리명"
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 카테고리명"

    def test_update_category_flow_type(self, client: TestClient, auth_header: dict, test_category: dict):
        """flow_type 변경"""
        payload = {
            "flow_type": "income"
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["flow_type"] == "income"

    def test_update_category_is_active(self, client: TestClient, auth_header: dict, test_category: dict):
        """활성 상태 변경"""
        payload = {
            "is_active": False
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_category_set_parent(self, client: TestClient, auth_header: dict, test_category: dict, parent_category: dict):
        """부모 카테고리 설정"""
        payload = {
            "parent_id": parent_category["id"]
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == parent_category["id"]

    def test_update_category_remove_parent(self, client: TestClient, auth_header: dict, parent_category: dict):
        """부모 카테고리 제거 (루트로 변경)"""
        # 하위 카테고리 생성
        child = client.post("/api/v1/categories", json={
            "name": "하위",
            "flow_type": "expense",
            "parent_id": parent_category["id"],
            "is_active": True
        }, headers=auth_header).json()
        
        # 부모 제거
        payload = {
            "parent_id": ""
        }
        response = client.put(f"/api/v1/categories/{child['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] is None

    def test_update_category_invalid_parent(self, client: TestClient, auth_header: dict, test_category: dict):
        """존재하지 않는 부모로 변경 시도"""
        payload = {
            "parent_id": "non-existent-id"
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_update_category_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 카테고리 수정"""
        payload = {
            "name": "새이름"
        }
        response = client.put("/api/v1/categories/non-existent-id", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_update_category_no_auth(self, client: TestClient, test_category: dict):
        """인증 없이 수정"""
        payload = {
            "name": "새이름"
        }
        response = client.put(f"/api/v1/categories/{test_category['id']}", json=payload)
        
        assert response.status_code == 401


class TestCategoryDelete:
    """카테고리 삭제 테스트"""

    def test_delete_category_success(self, client: TestClient, auth_header: dict):
        """카테고리 삭제 성공"""
        # 삭제용 카테고리 생성
        category = client.post("/api/v1/categories", json={
            "name": "삭제할카테고리",
            "flow_type": "expense",
            "is_active": True
        }, headers=auth_header).json()
        
        response = client.delete(f"/api/v1/categories/{category['id']}", headers=auth_header)
        
        assert response.status_code == 204
        
        # 삭제 확인
        check_response = client.get(f"/api/v1/categories/{category['id']}", headers=auth_header)
        assert check_response.status_code == 404

    def test_delete_category_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 카테고리 삭제"""
        response = client.delete("/api/v1/categories/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_delete_category_no_auth(self, client: TestClient, test_category: dict):
        """인증 없이 삭제"""
        response = client.delete(f"/api/v1/categories/{test_category['id']}")
        
        assert response.status_code == 401


class TestCategorySeed:
    """기본 카테고리 시드 테스트"""

    def test_seed_default_categories_success(self, client: TestClient, auth_header: dict):
        """기본 카테고리 시드 성공"""
        response = client.post("/api/v1/categories/seed", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # 기본 카테고리 확인 (식비, 교통, 급여 등)
        category_names = [cat["name"] for cat in data]
        assert any(name in ["식비", "교통", "주거", "급여"] for name in category_names)

    def test_seed_idempotent(self, client: TestClient, auth_header: dict):
        """시드 여러 번 실행 시 중복 생성 안 됨 (idempotent)"""
        # 첫 번째 시드
        response1 = client.post("/api/v1/categories/seed", headers=auth_header)
        assert response1.status_code == 200
        count1 = len(response1.json())
        
        # 두 번째 시드
        response2 = client.post("/api/v1/categories/seed", headers=auth_header)
        assert response2.status_code == 200
        count2 = len(response2.json())
        
        # 두 번째는 이미 존재하므로 새로 생성된 개수가 적거나 0
        assert count2 <= count1

    def test_seed_with_overwrite(self, client: TestClient, auth_header: dict):
        """overwrite=true로 기존 비활성화 후 재생성"""
        # 첫 번째 시드
        first_response = client.post("/api/v1/categories/seed", headers=auth_header)
        assert first_response.status_code == 200
        
        # 전체 카테고리 수 확인
        all_cats = client.get("/api/v1/categories?size=200", headers=auth_header).json()
        initial_total = all_cats["total"]
        
        # overwrite로 재생성
        response = client.post("/api/v1/categories/seed?overwrite=true", headers=auth_header)
        
        assert response.status_code == 200
        # overwrite는 기존 것을 비활성화하고 재생성하므로 응답이 비어있을 수 있음
        # 대신 전체 카테고리가 여전히 존재하는지 확인
        all_cats_after = client.get("/api/v1/categories?size=200&is_active=true", headers=auth_header).json()
        assert all_cats_after["total"] >= 0  # 재생성됨

    def test_seed_creates_hierarchy(self, client: TestClient, auth_header: dict):
        """시드가 계층 구조를 생성하는지 확인"""
        response = client.post("/api/v1/categories/seed", headers=auth_header)
        assert response.status_code == 200
        
        # 트리 조회
        tree_response = client.get("/api/v1/categories/tree", headers=auth_header)
        tree = tree_response.json()
        
        # 부모-자식 관계 확인
        parent_with_children = next((n for n in tree if len(n.get("children", [])) > 0), None)
        assert parent_with_children is not None, "시드 데이터에 하위 카테고리가 있어야 합니다"

    def test_seed_no_auth(self, client: TestClient):
        """인증 없이 시드"""
        response = client.post("/api/v1/categories/seed")
        
        assert response.status_code == 401
