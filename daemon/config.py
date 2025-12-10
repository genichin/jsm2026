"""
daemon 설정 모듈
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """daemon 설정"""
    
    # 백엔드 API
    api_base_url: str = "http://localhost:8000/api/v1"
    api_token: str = ""
    
    # 스케줄러 (선택사항: None일 경우 해당 작업 실행 안함)
    schedule_balance_cron: Optional[str] = None
    schedule_strategy_cron: Optional[str] = None
    schedule_price_update_cron: Optional[str] = None
    
    # 브로커
    broker: str = "demo"
    broker_app_key: str = ""
    broker_app_secret: str = ""
    broker_account: str = ""
    account_id: Optional[str] = None  # 특정 계좌만 처리 (None이면 모든 계좌)
    
    # 리스크 한도
    max_order_value_krw: float = 1000000
    slippage_bps: float = 50  # 0.50%
    max_retry: int = 3
    
    # 로깅
    log_level: str = "INFO"
    
    model_config = ConfigDict(
        case_sensitive=False,
        env_file=None  # 나중에 동적으로 로드
    )


# 환경변수 ENV로 .env.{ENV} 파일 선택
# 예: ENV=upbit → .env.upbit, ENV=demo → .env.demo
env_name = os.getenv("ENV", "daemon")
env_file_path = Path(__file__).parent / f".env.{env_name}"

# .env 파일이 있으면 로드
if env_file_path.exists():
    settings = Settings(_env_file=env_file_path)
else:
    # 없으면 환경변수에서만 로드
    settings = Settings()
