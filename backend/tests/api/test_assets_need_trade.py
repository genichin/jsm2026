"""
Assets need_trade API tests
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import get_password_hash


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def new_user(db_session: Session, test_password: str) -> User:
    user = User(
        email="needtrade_other@example.com",
        username="needtrade_other",
        hashed_password=get_password_hash(test_password),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestNeedTrade:
    def test_put_need_trade_and_get_asset_returns_it(
        self,
        client: TestClient,
        auth_header: dict,
        test_asset: dict,
    ):
        asset_id = test_asset["id"]

        # set need_trade
        resp = client.put(
            f"/api/v1/assets/{asset_id}/need_trade",
            headers=auth_header,
            json={"price": 12345.67, "quantity": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == asset_id
        assert data["need_trade"]["price"] == pytest.approx(12345.67)
        assert data["need_trade"]["quantity"] == pytest.approx(10)
        assert 1 <= data["need_trade"]["ttl"] <= 600

        # small sleep to reduce ttl slightly (non-zero)
        time.sleep(1)

        # get asset and verify need_trade present
        resp2 = client.get(f"/api/v1/assets/{asset_id}", headers=auth_header)
        assert resp2.status_code == 200
        asset = resp2.json()
        assert "need_trade" in asset
        nt = asset["need_trade"]
        assert nt is not None
        assert nt["price"] == pytest.approx(12345.67)
        assert nt["quantity"] == pytest.approx(10)
        assert 1 <= nt["ttl"] <= 600

    def test_put_need_trade_requires_auth(self, client: TestClient, test_asset: dict):
        asset_id = test_asset["id"]
        resp = client.put(
            f"/api/v1/assets/{asset_id}/need_trade",
            json={"price": 1000.0, "quantity": 1},
        )
        assert resp.status_code == 401

    def test_put_need_trade_other_user_forbidden(
        self,
        client: TestClient,
        new_user: User,
        test_password: str,
        test_asset: dict,
    ):
        # login as other user
        token = _login(client, new_user.email, test_password)
        headers = {"Authorization": f"Bearer {token}"}

        # attempt to set need_trade on someone else's asset -> 404 (not found)
        resp = client.put(
            f"/api/v1/assets/{test_asset['id']}/need_trade",
            headers=headers,
            json={"price": 111.0, "quantity": 2},
        )
        assert resp.status_code == 404
