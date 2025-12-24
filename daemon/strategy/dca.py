"""
DCA (Dollar-Cost Averaging) 전략
"""

import logging
from .base import BaseStrategy, StrategyConfig
from broker.base import OrderSide

logger = logging.getLogger(__name__)


class DCAStrategy(BaseStrategy):
    """DCA 전략: 정기적으로 일정 금액 매수"""
    
    def execute(self, config: StrategyConfig) -> bool:
        """
        DCA 전략 실행
        
        config.config 예시:
        {
            "monthly_amount": 1000000  # 월간 매수 금액 (KRW)
        }
        """
        try:
            logger.info(f"Executing DCA strategy for {config.symbol}")
            
            monthly_amount = config.config.get("monthly_amount")
            if not monthly_amount or monthly_amount <= 0:
                logger.warning(f"Invalid monthly_amount for DCA: {monthly_amount}")
                return False
            
            # 현재가 조회
            price_data = self.broker.get_current_price(config.symbol)
            current_price = price_data.current_price
            
            if current_price <= 0:
                logger.warning(f"Invalid price for {config.symbol}: {current_price}")
                return False
            
            # 매수 수량 계산
            buy_quantity = monthly_amount / current_price
            
            # 주문 접수
            order = self.broker.place_order(
                symbol=config.symbol,
                side=OrderSide.BUY,
                qty=buy_quantity,
                price=current_price,
                asset_id=config.asset_id
            )
            
            logger.info(f"DCA order placed: {order.order_id} for {buy_quantity} {config.symbol} @ {current_price}")
            
            # 백엔드에 거래 기록
            self._record_transaction(
                asset_id=config.asset_id,
                transaction_type="buy",
                quantity=buy_quantity,
                price=current_price,
                broker_order_id=order.order_id,
                strategy="dca"
            )
            
            return True
        except Exception as e:
            logger.error(f"DCA strategy execution failed: {str(e)}")
            return False
