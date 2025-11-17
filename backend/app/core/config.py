from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


def get_env_file() -> str:
    """
    ENV 환경 변수에 따라 적절한 .env 파일 경로 반환
    
    ENV=development → .env.development
    ENV=production → .env.production
    ENV 미설정 → .env
    """
    environment = os.getenv("ENV", "").lower()
    
    if environment == "development":
        return ".env.development"
    elif environment == "production":
        return ".env.production"
    else:
        # 기본값: .env 파일 사용
        return ".env"


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=get_env_file(), 
        case_sensitive=True,
        extra="allow"  # 추가 환경 변수 허용
    )
    
    # Application
    APP_NAME: str = "J's Money Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:jsmdb123!@jsmdb:5432/jsmdb"
    
    # Redis
    REDIS_HOST: str = "redis-stack"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - 문자열로 받아서 파싱
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 변환. '*'이면 모든 origin 허용"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Allowed Hosts - HTTPS 전용
    ALLOWED_HOSTS: str = "*"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Allowed hosts를 리스트로 변환"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    # Timezone
    TIMEZONE: str = "Asia/Seoul"


settings = Settings()
