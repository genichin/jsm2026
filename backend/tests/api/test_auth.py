"""
인증 API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


class TestRegister:
    """회원가입 테스트"""
    
    def test_register_success(self, client: TestClient):
        """정상 회원가입"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "Test1234!@#$",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # 비밀번호는 반환하지 않음
    
    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """중복 이메일로 회원가입 시도"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # 이미 존재하는 이메일
                "username": "differentuser",
                "password": "Test1234!@#$",
            }
        )
        
        assert response.status_code == 400
        assert "이미 사용 중인 이메일" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """중복 사용자명으로 회원가입 시도"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,  # 이미 존재하는 사용자명
                "password": "Test1234!@#$",
            }
        )
        
        assert response.status_code == 400
        assert "이미 사용 중인 사용자명" in response.json()["detail"]
    
    def test_register_invalid_email(self, client: TestClient):
        """잘못된 이메일 형식"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "notanemail",
                "username": "testuser",
                "password": "Test1234!@#$",
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestLogin:
    """로그인 테스트"""
    
    def test_login_with_email_success(self, client: TestClient, test_user: User, test_password: str):
        """이메일로 로그인 성공"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.email,
                "password": test_password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_with_username_success(self, client: TestClient, test_user: User, test_password: str):
        """사용자명으로 로그인 성공"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": test_password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """잘못된 비밀번호로 로그인 시도"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.email,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "올바르지 않습니다" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """존재하지 않는 사용자로 로그인 시도"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent@example.com",
                "password": "Test1234!@#$"
            }
        )
        
        assert response.status_code == 401
        assert "올바르지 않습니다" in response.json()["detail"]


class TestGetCurrentUser:
    """현재 사용자 정보 조회 테스트"""
    
    def test_get_current_user_success(self, client: TestClient, auth_header: dict, test_user: User):
        """인증된 사용자 정보 조회"""
        response = client.get(
            "/api/v1/auth/users/me",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "hashed_password" not in data
    
    def test_get_current_user_no_token(self, client: TestClient):
        """토큰 없이 사용자 정보 조회 시도"""
        response = client.get("/api/v1/auth/users/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """잘못된 토큰으로 사용자 정보 조회 시도"""
        response = client.get(
            "/api/v1/auth/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
