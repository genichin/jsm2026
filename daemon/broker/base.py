"""
브로커 커넥터 추상 클래스 및 데이터 모델
"""

from abc import ABC, abstractmethod
from typing import Dict, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """주문 방향"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


@dataclass
class Order:
    """주문 정보"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    status: OrderStatus
    executed_quantity: float = 0.0


@dataclass
class Balance:
    """계좌 잔고"""
    symbol: str
    quantity: float
    avg_price: float = 0.0


@dataclass
class PriceData:
    """가격 정보"""
    symbol: str
    current_price: float
    change_percent: float
    change_amount: float = 0.0


class BrokerConnector(ABC):
    """브로커 커넥터 추상 클래스"""
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Balance]:
        """현재 계좌 잔고 조회"""
        pass
    
    @abstractmethod
    def get_pending_orders(self) -> list:
        """미체결 주문 목록"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: OrderSide, qty: float, 
                   price: float = None) -> Order:
        """주문 접수"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """주문 상태 확인"""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: Union[str, list]) -> Union[PriceData, Dict]:
        """
        현재가 조회
        
        Args:
            symbol: 단일 심볼 문자열 또는 심볼 리스트
        
        Returns:
            단일 심볼이면 PriceData, 리스트면 Dict[symbol, PriceData]
        """
        pass
