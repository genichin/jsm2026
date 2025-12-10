#!/usr/bin/env python3
"""
Upbit API 인증 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
import uuid
import hashlib
import json

try:
    import jwt
except ImportError:
    jwt = None

try:
    import requests
except ImportError:
    requests = None

from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_upbit_auth():
    """Upbit API 인증 테스트"""
    
    logger.info(f"=== Upbit API 인증 테스트 ===")
    logger.info(f"Access Key: {settings.broker_app_key[:10]}...")
    logger.info(f"Secret Key Length: {len(settings.broker_app_secret)}")
    
    if not jwt or not requests:
        logger.error("jwt 또는 requests 모듈이 없습니다")
        return
    
    # JWT 토큰 생성
    base_url = "https://api.upbit.com/v1"
    query_hash = hashlib.sha512(b"").hexdigest()
    
    payload = {
        "access_key": settings.broker_app_key,
        "nonce": str(uuid.uuid4()),
        "query_hash": query_hash,
        "query_hash_alg": "SHA512",
    }
    
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    token = jwt.encode(payload, settings.broker_app_secret, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    
    logger.info(f"Generated Token: {token[:100]}...")
    
    # API 호출
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    logger.info(f"Headers: {headers}")
    
    try:
        logger.info(f"Calling: GET {base_url}/accounts")
        response = requests.get(f"{base_url}/accounts", headers=headers, timeout=10)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Headers: {response.headers}")
        logger.info(f"Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ SUCCESS! Retrieved {len(data)} accounts")
            for account in data:
                logger.info(f"  - {account.get('currency')}: {account.get('balance')}")
        else:
            logger.error(f"❌ API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Request failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_upbit_auth()
