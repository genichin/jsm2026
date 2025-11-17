#!/usr/bin/env python3
"""
환경 설정 확인 스크립트
현재 어떤 환경으로 실행되는지, 어떤 데이터베이스를 사용하는지 확인합니다.
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def main():
    print("=" * 60)
    print("J's Money Backend - Environment Configuration")
    print("=" * 60)
    print()
    
    # 환경 정보
    env = os.getenv("ENV", "not set")
    print(f"🌍 Environment Variable (ENV): {env}")
    print(f"📁 Config File Used: {settings.model_config.get('env_file', 'unknown')}")
    print()
    
    # 앱 설정
    print("📱 Application Settings:")
    print(f"   Name: {settings.APP_NAME}")
    print(f"   Version: {settings.APP_VERSION}")
    print(f"   Debug Mode: {settings.DEBUG}")
    print()
    
    # 데이터베이스
    print("🗄️  Database Configuration:")
    print(f"   URL: {settings.DATABASE_URL}")
    
    # URL에서 데이터베이스 이름 추출
    if "/" in settings.DATABASE_URL:
        db_name = settings.DATABASE_URL.split("/")[-1]
        print(f"   Database Name: {db_name}")
        
        if db_name == "jsmdb_dev":
            print("   ✅ Using DEVELOPMENT database")
        elif db_name == "jsmdb":
            print("   ✅ Using PRODUCTION database")
        else:
            print(f"   ⚠️  Unknown database: {db_name}")
    print()
    
    # Redis
    print("📦 Redis Configuration:")
    print(f"   Host: {settings.REDIS_HOST}")
    print(f"   Port: {settings.REDIS_PORT}")
    print(f"   DB: {settings.REDIS_DB}")
    print()
    
    # 보안
    print("🔒 Security Settings:")
    print(f"   Secret Key: {settings.SECRET_KEY[:20]}... (truncated)")
    print(f"   Algorithm: {settings.ALGORITHM}")
    print(f"   Token Expire: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print()
    
    # CORS
    print("🌐 CORS Settings:")
    origins = settings.cors_origins_list
    if origins == ["*"]:
        print("   ⚠️  WARNING: All origins allowed (development only!)")
    else:
        print(f"   Allowed Origins: {', '.join(origins)}")
    print()
    
    # 경고 메시지
    if settings.DEBUG and env == "production":
        print("⚠️  WARNING: DEBUG mode is ON in production environment!")
        print()
    
    if settings.SECRET_KEY == "your-secret-key-here-change-this-in-production":
        print("⚠️  WARNING: Using default SECRET_KEY! Change it in production!")
        print()
    
    print("=" * 60)
    
    # 환경별 권장사항
    if env == "development" or settings.DEBUG:
        print("\n💡 Development Environment Detected")
        print("   - Using development database (jsmdb_dev)")
        print("   - Debug mode enabled")
        print("   - All CORS origins allowed")
        print("   - This is OK for development!")
    elif env == "production" or not settings.DEBUG:
        print("\n🚀 Production Environment Detected")
        print("   - Using production database (jsmdb)")
        print("   - Debug mode should be OFF")
        print("   - Specific CORS origins only")
        print("   - Make sure to use secure settings!")
    
    print()

if __name__ == "__main__":
    main()
