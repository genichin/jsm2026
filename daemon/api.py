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
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or settings.api_base_url
        self.token = token or settings.api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })
    
    def get(self, endpoint: str, params: Dict = None, **kwargs) -> requests.Response:
        """GET 요청"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GET {endpoint} failed: {str(e)}")
            raise
    
    def post(self, endpoint: str, data: Dict = None, **kwargs) -> requests.Response:
        """POST 요청"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=data, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"POST {endpoint} failed: {str(e)}")
            raise
    
    def put(self, endpoint: str, data: Dict = None, params: Dict = None, **kwargs) -> requests.Response:
        """PUT 요청"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.put(url, json=data, params=params, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT {endpoint} failed: {str(e)}")
            raise
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE 요청"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.delete(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE {endpoint} failed: {str(e)}")
            raise


class AssetAPI:
    """자산 관련 API"""
    
    def __init__(self, client: APIClient = None):
        self.client = client or APIClient()
    
    def list_assets(self, account_id: str = None, asset_type: str = None, 
                    page: int = 1, size: int = 100) -> Dict:
        """자산 목록 조회"""
        params = {"page": page, "size": size, "is_active": True}
        if account_id:
            params["account_id"] = account_id
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
