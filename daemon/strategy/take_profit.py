"""
Take Profit 전략: 익절
"""

import logging
from .base import BaseStrategy, StrategyConfig
from broker.base import OrderSide

logger = logging.getLogger(__name__)


class TakeProfitStrategy(BaseStrategy):
    """익절 전략: 수익 한도 이상 익절 매도"""
    
    def execute(self, config: StrategyConfig, 
               current_price: float, avg_cost: float) -> bool:
        """
        익절 전략 실행
        
        config.config 예시:
        {
            "profit_threshold": 0.2  # 익절 임계값 (+20%)
        }
        """
        try:
            profit_threshold = config.config.get("profit_threshold")
            
            if profit_threshold is None or profit_threshold <= 0:
                logger.warning(f"Invalid profit_threshold: {profit_threshold}")
                return False
            
            logger.info(f"Checking take profit for {config.symbol}")
            
            if current_price <= 0 or avg_cost <= 0:
                logger.warning(f"Invalid price/cost: current={current_price}, avg={avg_cost}")
                return False
            
            # 수익율 계산
            profit_percent = (current_price - avg_cost) / avg_cost
            
            if profit_percent >= profit_threshold:
                logger.info(f"Take profit triggered for {config.symbol}: {profit_percent:.2%}")
                
                # 매도 주문
                balance = self.broker.get_balance().get(config.symbol)
                if balance and balance.quantity > 0:
                    order = self.broker.place_order(
                        symbol=config.symbol,
                        side=OrderSide.SELL,
                        qty=balance.quantity,
                        price=current_price,
                        asset_id=config.asset_id
                    )
                    
                    logger.info(f"Take profit order placed: {order.order_id} for {balance.quantity} {config.symbol}")
                    
                    self._record_transaction(
                        asset_id=config.asset_id,
                        transaction_type="sell",
                        quantity=balance.quantity,
                        price=current_price,
                        broker_order_id=order.order_id,
                        strategy="take_profit"
                    )
                    return True
                else:
                    logger.warning(f"No position to sell for {config.symbol}")
            
            return False
        except Exception as e:
            logger.error(f"Take profit strategy execution failed: {str(e)}")
            return False
