"""
데모 브로커 커넥터 (테스트용)
"""

from typing import Dict, List
import logging
from .base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData

logger = logging.getLogger(__name__)


class DemoBrokerConnector(BrokerConnector):
    """데모 브로커 커넥터 (테스트용)"""
    
    def __init__(self):
        self.balances = {
            "KRW": Balance(symbol="KRW", quantity=10000000.0, avg_price=1.0),
            "005930": Balance(symbol="005930", quantity=100.0, avg_price=65000.0),
        }
        self.pending_orders: Dict[str, Order] = {}
        self.price_data = {
            "005930": PriceData(symbol="005930", current_price=70000.0, change_percent=2.5),
            "BTC": PriceData(symbol="BTC", current_price=45000000.0, change_percent=-1.2),
        }
    
    def get_balance(self) -> Dict[str, Balance]:
        """현재 계좌 잔고 조회"""
        logger.info("DemoBroker: Getting balance")
        return self.balances.copy()
    
    def get_pending_orders(self) -> List[Order]:
        """미체결 주문 목록"""
        logger.info("DemoBroker: Getting pending orders")
        return list(self.pending_orders.values())
    
    def place_order(self, symbol: str, side: OrderSide, qty: float, 
                   price: float = None) -> Order:
        """주문 접수"""
        order_id = f"ORD{len(self.pending_orders) + 1}"
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price or self.price_data.get(symbol, PriceData(symbol, 0, 0)).current_price,
            status=OrderStatus.PENDING,
            executed_quantity=0.0
        )
        self.pending_orders[order_id] = order
        logger.info(f"DemoBroker: Placed order {order_id} for {qty} {symbol}")
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if order_id in self.pending_orders:
            self.pending_orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"DemoBroker: Cancelled order {order_id}")
            return True
        logger.warning(f"DemoBroker: Order {order_id} not found")
        return False
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """주문 상태 확인"""
        order = self.pending_orders.get(order_id)
        if order:
            # 50% 확률로 체결
            if order.status == OrderStatus.PENDING and len(self.pending_orders) % 2 == 0:
                order.status = OrderStatus.EXECUTED
                order.executed_quantity = order.quantity
            return order.status
        return OrderStatus.REJECTED
    
    def get_current_price(self, symbol: str | list) -> PriceData | Dict:
        """현재가 조회"""
        # 리스트 처리
        if isinstance(symbol, list):
            logger.info(f"DemoBroker: Getting prices for {len(symbol)} symbols")
            result = {}
            for sym in symbol:
                if sym in self.price_data:
                    result[sym] = self.price_data[sym]
                else:
                    result[sym] = PriceData(symbol=sym, current_price=0.0, change_percent=0.0)
            return result
        
        # 단일 심볼 처리
        if symbol in self.price_data:
            return self.price_data[symbol]
        # 기본값 반환
        logger.warning(f"DemoBroker: Price data not found for {symbol}")
        return PriceData(symbol=symbol, current_price=0.0, change_percent=0.0)
