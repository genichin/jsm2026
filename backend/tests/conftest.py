"""
pytest 공통 픽스처 설정
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings


# 테스트 DB URL (환경 변수 또는 기본값)
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL_TEST",
    "postgresql://postgres:jsmdb123!@localhost:5432/jsmdb_test"
)


@pytest.fixture(scope="session")
def test_engine():
    """
    테스트용 DB 엔진 생성 (세션당 1회)
    - Alembic 마이그레이션 적용
    - 테스트 종료 시 모든 테이블 드롭
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False  # SQL 로그 출력 (디버깅 시 True)
    )
    
    # 모든 테이블 생성 (Alembic 대신 SQLAlchemy로 생성)
    # 실제 환경에서는 alembic upgrade head 사용 권장
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 테스트 종료 시 모든 테이블 드롭
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    각 테스트마다 독립적인 DB 세션 제공
    - 트랜잭션 시작
    - 테스트 종료 시 자동 롤백 (상태 격리)
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # 세션 생성
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = TestSessionLocal()
    
    # 중첩 트랜잭션 지원 (savepoint)
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    session.begin_nested()
    
    yield session
    
    # 테스트 종료: 롤백 및 정리
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient 제공
    - DB dependency override로 테스트 세션 주입
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # 세션은 db_session fixture에서 관리
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 정리
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def test_password() -> str:
    """테스트용 비밀번호"""
    return "Test1234!@#$"


@pytest.fixture(scope="function")
def test_user_data(test_password: str) -> dict:
    """테스트 유저 생성용 데이터"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": test_password,
        "full_name": "Test User"
    }
