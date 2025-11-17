"""
카테고리 자동 규칙 API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Category


@pytest.fixture(scope="function")
def test_category(db_session: Session, test_user) -> Category:
    """테스트용 카테고리 생성"""
    category = Category(
        user_id=test_user.id,
        name="식비",
        flow_type="expense"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


class TestAutoRuleCreate:
    """자동 규칙 생성 테스트"""
    
    def test_create_rule_exact(self, client: TestClient, auth_header: dict, test_category: Category):
        """정확히 일치하는 규칙 생성"""
        payload = {
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "스타벅스",
            "priority": 10,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert data["pattern_type"] == "exact"
        assert data["pattern_text"] == "스타벅스"
        assert data["category_id"] == test_category.id
        assert data["priority"] == 10
    
    def test_create_rule_contains(self, client: TestClient, auth_header: dict, test_category: Category):
        """포함하는 규칙 생성"""
        payload = {
            "category_id": test_category.id,
            "pattern_type": "contains",
            "pattern_text": "카페",
            "priority": 20,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert data["pattern_type"] == "contains"
        assert data["pattern_text"] == "카페"
    
    def test_create_rule_regex(self, client: TestClient, auth_header: dict, test_category: Category):
        """정규식 규칙 생성"""
        payload = {
            "category_id": test_category.id,
            "pattern_type": "regex",
            "pattern_text": "^(GS25|CU|세븐일레븐)",
            "priority": 30,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload, headers=auth_header)
        assert response.status_code == 201
        data = response.json()
        assert data["pattern_type"] == "regex"
        assert data["pattern_text"] == "^(GS25|CU|세븐일레븐)"
    
    def test_create_rule_invalid_category(self, client: TestClient, auth_header: dict):
        """존재하지 않는 카테고리로 규칙 생성"""
        payload = {
            "category_id": "invalid-id",
            "pattern_type": "exact",
            "pattern_text": "테스트",
            "priority": 10,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload, headers=auth_header)
        assert response.status_code == 404
    
    def test_create_rule_invalid_pattern_type(self, client: TestClient, auth_header: dict, test_category: Category):
        """잘못된 pattern_type"""
        payload = {
            "category_id": test_category.id,
            "pattern_type": "invalid",
            "pattern_text": "테스트",
            "priority": 10,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload, headers=auth_header)
        assert response.status_code == 422
    
    def test_create_rule_no_auth(self, client: TestClient, test_category: Category):
        """인증 없이 규칙 생성"""
        payload = {
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "테스트",
            "priority": 10,
            "is_active": True
        }
        response = client.post("/api/v1/category-auto-rules", json=payload)
        assert response.status_code == 401


class TestAutoRuleList:
    """자동 규칙 목록 테스트"""
    
    def test_list_rules_success(self, client: TestClient, auth_header: dict, test_category: Category):
        """규칙 목록 조회"""
        # 규칙 2개 생성
        for i in range(2):
            client.post("/api/v1/category-auto-rules", json={
                "category_id": test_category.id,
                "pattern_type": "contains",
                "pattern_text": f"테스트{i+1}",
                "priority": (i+1) * 10,
                "is_active": True
            }, headers=auth_header)
        
        response = client.get("/api/v1/category-auto-rules", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        # priority 순으로 정렬되어야 함
        priorities = [rule["priority"] for rule in data]
        assert priorities == sorted(priorities)
    
    def test_list_rules_empty(self, client: TestClient, auth_header: dict):
        """규칙이 없는 경우"""
        response = client.get("/api/v1/category-auto-rules", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_rules_no_auth(self, client: TestClient):
        """인증 없이 목록 조회"""
        response = client.get("/api/v1/category-auto-rules")
        assert response.status_code == 401


class TestAutoRuleUpdate:
    """자동 규칙 수정 테스트"""
    
    def test_update_rule_pattern(self, client: TestClient, auth_header: dict, test_category: Category):
        """규칙 패턴 수정"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "contains",
            "pattern_text": "원래 패턴",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 수정
        response = client.put(
            f"/api/v1/category-auto-rules/{rule_id}",
            json={"pattern_text": "수정된 패턴"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pattern_text"] == "수정된 패턴"
    
    def test_update_rule_priority(self, client: TestClient, auth_header: dict, test_category: Category):
        """규칙 우선순위 수정"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "테스트",
            "priority": 50,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 수정
        response = client.put(
            f"/api/v1/category-auto-rules/{rule_id}",
            json={"priority": 5},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 5
    
    def test_update_rule_is_active(self, client: TestClient, auth_header: dict, test_category: Category):
        """규칙 활성화 상태 수정"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "contains",
            "pattern_text": "테스트",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 비활성화
        response = client.put(
            f"/api/v1/category-auto-rules/{rule_id}",
            json={"is_active": False},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    def test_update_rule_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 규칙 수정"""
        response = client.put(
            "/api/v1/category-auto-rules/invalid-id",
            json={"pattern_text": "수정"},
            headers=auth_header
        )
        assert response.status_code == 404
    
    def test_update_rule_no_auth(self, client: TestClient):
        """인증 없이 규칙 수정"""
        response = client.put(
            "/api/v1/category-auto-rules/some-id",
            json={"pattern_text": "수정"}
        )
        assert response.status_code == 401


class TestAutoRuleDelete:
    """자동 규칙 삭제 테스트"""
    
    def test_delete_rule_success(self, client: TestClient, auth_header: dict, test_category: Category):
        """규칙 삭제 성공"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "삭제할 규칙",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 삭제
        response = client.delete(f"/api/v1/category-auto-rules/{rule_id}", headers=auth_header)
        assert response.status_code == 204
        
        # 삭제 확인
        list_resp = client.get("/api/v1/category-auto-rules", headers=auth_header)
        rules = list_resp.json()
        rule_ids = [r["id"] for r in rules]
        assert rule_id not in rule_ids
    
    def test_delete_rule_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 규칙 삭제"""
        response = client.delete("/api/v1/category-auto-rules/invalid-id", headers=auth_header)
        assert response.status_code == 404
    
    def test_delete_rule_no_auth(self, client: TestClient):
        """인증 없이 규칙 삭제"""
        response = client.delete("/api/v1/category-auto-rules/some-id")
        assert response.status_code == 401


class TestAutoRuleSimulation:
    """자동 규칙 시뮬레이션 테스트"""
    
    def test_simulate_exact_match(self, client: TestClient, auth_header: dict, test_category: Category):
        """정확히 일치하는 경우 시뮬레이션"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "스타벅스 아메리카노",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 시뮬레이션
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "스타벅스 아메리카노"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["category_id"] == test_category.id
        assert data["rule_id"] == rule_id
    
    def test_simulate_contains_match(self, client: TestClient, auth_header: dict, test_category: Category):
        """포함하는 경우 시뮬레이션"""
        # 규칙 생성
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "contains",
            "pattern_text": "카페",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 시뮬레이션
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "투썸플레이스 카페라떼"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["category_id"] == test_category.id
    
    def test_simulate_regex_match(self, client: TestClient, auth_header: dict, test_category: Category):
        """정규식 매칭 시뮬레이션"""
        # 규칙 생성
        client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "regex",
            "pattern_text": "^(GS25|CU|세븐일레븐)",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        
        # 시뮬레이션
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "GS25 강남점"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
    
    def test_simulate_no_match(self, client: TestClient, auth_header: dict, test_category: Category):
        """매칭되지 않는 경우"""
        # 규칙 생성
        client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "exact",
            "pattern_text": "스타벅스",
            "priority": 10,
            "is_active": True
        }, headers=auth_header)
        
        # 시뮬레이션
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "투썸플레이스"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert data["category_id"] is None
    
    def test_simulate_priority_order(self, client: TestClient, auth_header: dict, test_category: Category, db_session: Session, test_user):
        """우선순위에 따른 매칭"""
        # 두 번째 카테고리 생성
        category2 = Category(
            user_id=test_user.id,
            name="교통비",
            flow_type="expense"
        )
        db_session.add(category2)
        db_session.commit()
        db_session.refresh(category2)
        
        # 낮은 우선순위 규칙 (숫자가 클수록 낮은 우선순위)
        client.post("/api/v1/category-auto-rules", json={
            "category_id": category2.id,
            "pattern_type": "contains",
            "pattern_text": "카카오택시",
            "priority": 20,
            "is_active": True
        }, headers=auth_header)
        
        # 높은 우선순위 규칙 (숫자가 작을수록 우선)
        create_resp = client.post("/api/v1/category-auto-rules", json={
            "category_id": test_category.id,
            "pattern_type": "contains",
            "pattern_text": "택시",
            "priority": 5,
            "is_active": True
        }, headers=auth_header)
        rule_id = create_resp.json()["id"]
        
        # 시뮬레이션 - 우선순위가 높은 규칙이 적용되어야 함
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "카카오택시 이용"},
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        # '택시'와 '카카오택시' 모두 매칭되지만, priority 5가 먼저 적용
        assert data["category_id"] == test_category.id
        assert data["rule_id"] == rule_id
    
    def test_simulate_no_auth(self, client: TestClient):
        """인증 없이 시뮬레이션"""
        response = client.post(
            "/api/v1/category-auto-rules/simulate",
            json={"description": "테스트"}
        )
        assert response.status_code == 401
