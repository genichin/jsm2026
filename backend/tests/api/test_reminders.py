"""
리마인더 관리 API 테스트

테스트 범위:
1. 리마인더 생성 (POST /api/v1/reminders)
2. 리마인더 목록 조회 (GET /api/v1/reminders)
3. 대기 중인 리마인더 (GET /api/v1/reminders/pending)
4. 리마인더 통계 (GET /api/v1/reminders/stats)
5. 리마인더 상세 조회 (GET /api/v1/reminders/{reminder_id})
6. 리마인더 수정 (PATCH /api/v1/reminders/{reminder_id})
7. 리마인더 삭제 (DELETE /api/v1/reminders/{reminder_id})
8. 리마인더 완료 처리 (PATCH /api/v1/reminders/{reminder_id}/dismiss)
9. 리마인더 스누즈 (PATCH /api/v1/reminders/{reminder_id}/snooze)
10. 엔티티의 리마인더 조회 (GET /api/v1/reminders/entity/{remindable_type}/{remindable_id})
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


@pytest.fixture
def future_time():
    """미래 시각 (1시간 후)"""
    return datetime.utcnow() + timedelta(hours=1)


@pytest.fixture
def past_time():
    """과거 시각 (1시간 전)"""
    return datetime.utcnow() - timedelta(hours=1)


@pytest.fixture
def test_reminder(client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
    """테스트용 리마인더 생성"""
    payload = {
        "remindable_type": "asset",
        "remindable_id": test_asset["id"],
        "reminder_type": "review",
        "title": "테스트 리마인더",
        "description": "테스트용 리마인더입니다",
        "remind_at": future_time.isoformat(),
        "priority": 1
    }
    response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
    assert response.status_code == 201
    return response.json()


class TestReminderCreate:
    """리마인더 생성 테스트"""

    def test_create_reminder_success(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """기본 리마인더 생성 성공"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "자산 검토",
            "description": "분기별 자산 검토",
            "remind_at": future_time.isoformat(),
            "priority": 1,
            "auto_complete_on_view": False
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "자산 검토"
        assert data["reminder_type"] == "review"
        assert data["priority"] == 1
        assert data["is_dismissed"] is False
        assert "id" in data
        assert "created_at" in data

    def test_create_reminder_minimal(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """최소 필드로 리마인더 생성"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "간단 리마인더",
            "remind_at": future_time.isoformat()
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == 0
        assert data["auto_complete_on_view"] is False

    def test_create_reminder_for_account(self, client: TestClient, auth_header: dict, test_account, future_time: datetime):
        """계좌에 대한 리마인더 생성"""
        payload = {
            "remindable_type": "account",
            "remindable_id": test_account.id,
            "reminder_type": "deadline",
            "title": "카드 대금 납부",
            "remind_at": future_time.isoformat(),
            "priority": 2
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["remindable_type"] == "account"
        assert data["reminder_type"] == "deadline"

    def test_create_reminder_with_repeat(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """반복 리마인더 생성"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "월간 검토",
            "remind_at": future_time.isoformat(),
            "repeat_interval": "monthly"
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 201
        data = response.json()
        assert data["repeat_interval"] == "monthly"

    def test_create_reminder_invalid_entity(self, client: TestClient, auth_header: dict, future_time: datetime):
        """존재하지 않는 엔티티에 리마인더 생성"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": "non-existent-id",
            "reminder_type": "review",
            "title": "테스트",
            "remind_at": future_time.isoformat()
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_create_reminder_missing_title(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """필수 필드 누락 (제목)"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "remind_at": future_time.isoformat()
        }
        response = client.post("/api/v1/reminders", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_create_reminder_no_auth(self, client: TestClient, test_asset: dict, future_time: datetime):
        """인증 없이 리마인더 생성"""
        payload = {
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "테스트",
            "remind_at": future_time.isoformat()
        }
        response = client.post("/api/v1/reminders", json=payload)
        
        assert response.status_code == 401


class TestReminderList:
    """리마인더 목록 조회 테스트"""

    def test_list_reminders_success(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """리마인더 목록 조회 성공"""
        response = client.get("/api/v1/reminders", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(r["id"] == test_reminder["id"] for r in data)

    def test_list_reminders_filter_by_type(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """리마인더 유형으로 필터링"""
        # 다른 유형의 리마인더 생성
        client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "payment",
            "title": "납부 알림",
            "remind_at": future_time.isoformat()
        }, headers=auth_header)
        
        response = client.get("/api/v1/reminders?reminder_type=payment", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert all(r["reminder_type"] == "payment" for r in data)

    def test_list_reminders_filter_by_entity_type(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """엔티티 타입으로 필터링"""
        response = client.get("/api/v1/reminders?remindable_type=asset", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert all(r["remindable_type"] == "asset" for r in data)

    def test_list_reminders_pagination(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """페이지네이션 테스트"""
        # 여러 개 생성
        for i in range(5):
            client.post("/api/v1/reminders", json={
                "remindable_type": "asset",
                "remindable_id": test_asset["id"],
                "reminder_type": "review",
                "title": f"리마인더{i}",
                "remind_at": future_time.isoformat()
            }, headers=auth_header)
        
        response = client.get("/api/v1/reminders?limit=3", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_reminders_no_auth(self, client: TestClient):
        """인증 없이 조회"""
        response = client.get("/api/v1/reminders")
        
        assert response.status_code == 401


class TestReminderPending:
    """대기 중인 리마인더 조회 테스트"""

    def test_get_pending_reminders(self, client: TestClient, auth_header: dict, test_asset: dict, past_time: datetime):
        """대기 중인 리마인더 조회"""
        # 과거 시각으로 리마인더 생성 (발송 대기)
        client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "대기 리마인더",
            "remind_at": past_time.isoformat()
        }, headers=auth_header)
        
        response = client.get("/api/v1/reminders/pending", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 대기 중인 리마인더가 있어야 함
        assert any(r["title"] == "대기 리마인더" for r in data)

    def test_get_pending_reminders_excludes_dismissed(self, client: TestClient, auth_header: dict, test_asset: dict, past_time: datetime):
        """무시된 리마인더는 제외"""
        # 리마인더 생성
        reminder = client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "무시될 리마인더",
            "remind_at": past_time.isoformat()
        }, headers=auth_header).json()
        
        # 무시 처리
        client.patch(f"/api/v1/reminders/{reminder['id']}/dismiss", headers=auth_header)
        
        # 대기 중 조회
        response = client.get("/api/v1/reminders/pending", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        # 무시된 리마인더는 나타나지 않아야 함
        assert not any(r["id"] == reminder["id"] for r in data)

    def test_get_pending_reminders_no_auth(self, client: TestClient):
        """인증 없이 조회"""
        response = client.get("/api/v1/reminders/pending")
        
        assert response.status_code == 401


class TestReminderStats:
    """리마인더 통계 조회 테스트"""

    def test_get_reminder_stats(self, client: TestClient, auth_header: dict, test_asset: dict, past_time: datetime, future_time: datetime):
        """리마인더 통계 조회"""
        # 다양한 리마인더 생성
        client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "대기 리마인더",
            "remind_at": past_time.isoformat(),
            "priority": 2
        }, headers=auth_header)
        
        client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "미래 리마인더",
            "remind_at": future_time.isoformat()
        }, headers=auth_header)
        
        response = client.get("/api/v1/reminders/stats", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_reminders" in data
        assert "pending_reminders" in data
        assert "urgent_reminders" in data
        assert "snoozed_reminders" in data
        assert data["total_reminders"] >= 2

    def test_get_reminder_stats_no_auth(self, client: TestClient):
        """인증 없이 통계 조회"""
        response = client.get("/api/v1/reminders/stats")
        
        assert response.status_code == 401


class TestReminderDetail:
    """리마인더 상세 조회 테스트"""

    def test_get_reminder_success(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """리마인더 상세 조회 성공"""
        response = client.get(f"/api/v1/reminders/{test_reminder['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_reminder["id"]
        assert data["title"] == test_reminder["title"]

    def test_get_reminder_auto_complete(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """auto_complete_on_view 리마인더 조회 시 자동 완료"""
        # auto_complete_on_view=True로 생성
        reminder = client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "자동완료 리마인더",
            "remind_at": future_time.isoformat(),
            "auto_complete_on_view": True
        }, headers=auth_header).json()
        
        # 조회
        response = client.get(f"/api/v1/reminders/{reminder['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_dismissed"] is True
        assert data["dismissed_at"] is not None

    def test_get_reminder_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 리마인더 조회"""
        response = client.get("/api/v1/reminders/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_get_reminder_no_auth(self, client: TestClient, test_reminder: dict):
        """인증 없이 조회"""
        response = client.get(f"/api/v1/reminders/{test_reminder['id']}")
        
        assert response.status_code == 401


class TestReminderUpdate:
    """리마인더 수정 테스트"""

    def test_update_reminder_title(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """리마인더 제목 수정"""
        payload = {
            "title": "수정된 제목"
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "수정된 제목"

    def test_update_reminder_priority(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """우선순위 수정"""
        payload = {
            "priority": 2
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 2

    def test_update_reminder_time(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """알림 시각 수정"""
        new_time = datetime.utcnow() + timedelta(days=1)
        payload = {
            "remind_at": new_time.isoformat()
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}", json=payload, headers=auth_header)
        
        assert response.status_code == 200

    def test_update_reminder_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 리마인더 수정"""
        payload = {
            "title": "새제목"
        }
        response = client.patch("/api/v1/reminders/non-existent-id", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_update_reminder_no_auth(self, client: TestClient, test_reminder: dict):
        """인증 없이 수정"""
        payload = {
            "title": "새제목"
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}", json=payload)
        
        assert response.status_code == 401


class TestReminderDelete:
    """리마인더 삭제 테스트"""

    def test_delete_reminder_success(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """리마인더 삭제 성공"""
        # 삭제용 리마인더 생성
        reminder = client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "삭제될 리마인더",
            "remind_at": future_time.isoformat()
        }, headers=auth_header).json()
        
        response = client.delete(f"/api/v1/reminders/{reminder['id']}", headers=auth_header)
        
        assert response.status_code == 204
        
        # 삭제 확인
        check_response = client.get(f"/api/v1/reminders/{reminder['id']}", headers=auth_header)
        assert check_response.status_code == 404

    def test_delete_reminder_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 리마인더 삭제"""
        response = client.delete("/api/v1/reminders/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_delete_reminder_no_auth(self, client: TestClient, test_reminder: dict):
        """인증 없이 삭제"""
        response = client.delete(f"/api/v1/reminders/{test_reminder['id']}")
        
        assert response.status_code == 401


class TestReminderDismiss:
    """리마인더 완료 처리 테스트"""

    def test_dismiss_reminder_success(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """리마인더 무시 처리 성공"""
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/dismiss", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_dismissed"] is True
        assert data["dismissed_at"] is not None

    def test_dismiss_reminder_already_dismissed(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """이미 무시된 리마인더 재무시 시도"""
        # 첫 번째 무시
        client.patch(f"/api/v1/reminders/{test_reminder['id']}/dismiss", headers=auth_header)
        
        # 두 번째 무시 시도
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/dismiss", headers=auth_header)
        
        assert response.status_code == 400
        assert "이미 무시" in response.json()["detail"]

    def test_dismiss_reminder_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 리마인더 무시"""
        response = client.patch("/api/v1/reminders/non-existent-id/dismiss", headers=auth_header)
        
        assert response.status_code == 404

    def test_dismiss_reminder_no_auth(self, client: TestClient, test_reminder: dict):
        """인증 없이 무시 처리"""
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/dismiss")
        
        assert response.status_code == 401


class TestReminderSnooze:
    """리마인더 스누즈 테스트"""

    def test_snooze_reminder_success(self, client: TestClient, auth_header: dict, test_reminder: dict):
        """리마인더 스누즈 성공"""
        snooze_time = datetime.utcnow() + timedelta(hours=2)
        payload = {
            "snooze_until": snooze_time.isoformat()
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/snooze", json=payload, headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["snoozed_until"] is not None

    def test_snooze_reminder_invalid_time(self, client: TestClient, auth_header: dict, test_reminder: dict, past_time: datetime):
        """과거 시각으로 스누즈 시도"""
        payload = {
            "snooze_until": past_time.isoformat()
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/snooze", json=payload, headers=auth_header)
        
        assert response.status_code == 422

    def test_snooze_reminder_not_found(self, client: TestClient, auth_header: dict):
        """존재하지 않는 리마인더 스누즈"""
        snooze_time = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "snooze_until": snooze_time.isoformat()
        }
        response = client.patch("/api/v1/reminders/non-existent-id/snooze", json=payload, headers=auth_header)
        
        assert response.status_code == 404

    def test_snooze_reminder_no_auth(self, client: TestClient, test_reminder: dict):
        """인증 없이 스누즈"""
        snooze_time = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "snooze_until": snooze_time.isoformat()
        }
        response = client.patch(f"/api/v1/reminders/{test_reminder['id']}/snooze", json=payload)
        
        assert response.status_code == 401


class TestEntityReminders:
    """엔티티의 리마인더 조회 테스트"""

    def test_get_entity_reminders_success(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """엔티티의 리마인더 조회"""
        # 여러 리마인더 생성
        for i in range(3):
            client.post("/api/v1/reminders", json={
                "remindable_type": "asset",
                "remindable_id": test_asset["id"],
                "reminder_type": "review",
                "title": f"리마인더{i}",
                "remind_at": future_time.isoformat()
            }, headers=auth_header)
        
        response = client.get(f"/api/v1/reminders/entity/asset/{test_asset['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_entity_reminders_exclude_dismissed(self, client: TestClient, auth_header: dict, test_asset: dict, future_time: datetime):
        """무시된 리마인더 제외"""
        # 리마인더 생성
        reminder = client.post("/api/v1/reminders", json={
            "remindable_type": "asset",
            "remindable_id": test_asset["id"],
            "reminder_type": "review",
            "title": "무시될 리마인더",
            "remind_at": future_time.isoformat()
        }, headers=auth_header).json()
        
        # 무시 처리
        client.patch(f"/api/v1/reminders/{reminder['id']}/dismiss", headers=auth_header)
        
        # 무시 제외하고 조회
        response = client.get(f"/api/v1/reminders/entity/asset/{test_asset['id']}", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert not any(r["id"] == reminder["id"] for r in data)

    def test_get_entity_reminders_invalid_entity(self, client: TestClient, auth_header: dict):
        """존재하지 않는 엔티티의 리마인더 조회"""
        response = client.get("/api/v1/reminders/entity/asset/non-existent-id", headers=auth_header)
        
        assert response.status_code == 404

    def test_get_entity_reminders_no_auth(self, client: TestClient, test_asset: dict):
        """인증 없이 엔티티 리마인더 조회"""
        response = client.get(f"/api/v1/reminders/entity/asset/{test_asset['id']}")
        
        assert response.status_code == 401
