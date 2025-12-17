"""
백엔드 API 클라이언트
"""

import requests
from typing import Dict, List, Optional, Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """백엔드 API 호출용 클라이언트"""
    
    def __init__(self, base_url: str = None, token: str = None, username: str = None, password: str = None):
        self.base_url = base_url or settings.api_base_url
        self.token = token or settings.api_token
        self.username = username or settings.api_username
        self.password = password or settings.api_password
        self.session = requests.Session()
        self._update_auth_header()
    
    def _update_auth_header(self):
        """인증 헤더 업데이트"""
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })
    
    def _refresh_token(self):
        """토큰 갱신"""
        if not self.username or not self.password:
            logger.error("Cannot refresh token: username or password not configured")
            return False
        
        try:
            logger.info("Refreshing API token...")
            # 토큰 갱신 시에는 인증 헤더 제거
            temp_session = requests.Session()
            response = temp_session.post(
                f"{self.base_url.replace('/api/v1', '')}/api/v1/auth/token",
                data={
                    "username": self.username,
                    "password": self.password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.token = data.get("access_token")
            
            if self.token:
                self._update_auth_header()
                logger.info("API token refreshed successfully")
                return True
            else:
                logger.error("Token refresh failed: no access_token in response")
                return False
                
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return False
    
    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """재시도 로직이 포함된 요청"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = getattr(self.session, method)(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            # 401 에러 시 토큰 갱신 후 재시도
            if e.response.status_code == 401:
                logger.warning(f"{method.upper()} {endpoint} returned 401, attempting token refresh...")
                if self._refresh_token():
                    # 토큰 갱신 성공 시 재시도
                    response = getattr(self.session, method)(url, **kwargs)
                    response.raise_for_status()
                    return response
            raise
    
    def get(self, endpoint: str, params: Dict = None, **kwargs) -> requests.Response:
        """GET 요청"""
        try:
            return self._request_with_retry("get", endpoint, params=params, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"GET {endpoint} failed: {str(e)}")
            raise
    
    def post(self, endpoint: str, data: Dict = None, **kwargs) -> requests.Response:
        """POST 요청"""
        try:
            return self._request_with_retry("post", endpoint, json=data, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"POST {endpoint} failed: {str(e)}")
            raise
    
    def put(self, endpoint: str, data: Dict = None, params: Dict = None, **kwargs) -> requests.Response:
        """PUT 요청"""
        try:
            return self._request_with_retry("put", endpoint, json=data, params=params, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT {endpoint} failed: {str(e)}")
            raise
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE 요청"""
        try:
            return self._request_with_retry("delete", endpoint, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE {endpoint} failed: {str(e)}")
            raise


class AssetAPI:
    """자산 관련 API"""
    
    def __init__(self, client: APIClient = None):
        self.client = client or APIClient()
    
    def list_assets(
        self,
        account_id: str = None,
        asset_type: str = None,
        symbol: str = None,
        page: int = 1,
        size: int = 100,
        is_active: bool = None,
    ) -> Dict:
        """자산 목록 조회"""
        params = {"page": page, "size": size}

        # account_id와 symbol 모두 전달 가능 (동시 필터로 단일 자산 선택)
        if account_id:
            params["account_id"] = account_id
        if symbol:
            params["symbol"] = symbol

        if is_active is not None:
            params["is_active"] = is_active
        if asset_type:
            params["asset_type"] = asset_type
        
        response = self.client.get("/assets", params=params)
        return response.json()
    
    def get_asset(self, asset_id: str) -> Dict:
        """자산 상세 조회"""
        response = self.client.get(f"/assets/{asset_id}")
        return response.json()
    
    def update_asset_price(self, asset_id: str, price: float, 
                          change: float = None, use_symbol: bool = False) -> Dict:
        """자산 가격 업데이트"""
        params = {"price": price}
        if change is not None:
            params["change"] = change
        if use_symbol:
            params["use_symbol"] = True
        
        response = self.client.put(f"/assets/{asset_id}/price", params=params)
        return response.json()
    
    def update_asset_need_trade(self, asset_id: str, price: float, quantity: float) -> Dict:
        """자산의 거래 필요 정보 업데이트 (수동 거래용)"""
        data = {
            "price": price,
            "quantity": quantity
        }
        response = self.client.put(f"/assets/{asset_id}/need_trade", data=data)
        return response.json()


class TransactionAPI:
    """거래 관련 API"""
    
    def __init__(self, client: APIClient = None):
        self.client = client or APIClient()
    
    def create_transaction(self, transaction_data: Dict) -> Dict:
        """거래 기록 추가"""
        response = self.client.post("/transactions", data=transaction_data)
        return response.json()
    
    def list_transactions(self, asset_id: str = None, page: int = 1, 
                         size: int = 50) -> Dict:
        """거래 목록 조회"""
        params = {"page": page, "size": size}
        if asset_id:
            params["asset_id"] = asset_id
        
        response = self.client.get("/transactions", params=params)
        return response.json()


# 전역 클라이언트 인스턴스
api_client = APIClient()
asset_api = AssetAPI(api_client)
transaction_api = TransactionAPI(api_client)
