"""
Stop Loss 전략: 손절
"""

import logging
from .base import BaseStrategy, StrategyConfig
from broker.base import OrderSide

logger = logging.getLogger(__name__)


class StopLossStrategy(BaseStrategy):
    """손절 전략: 손실 한도 이상 손절 매도"""
    
    def execute(self, config: StrategyConfig, 
               current_price: float, avg_cost: float) -> bool:
        """
        손절 전략 실행
        
        config.config 예시:
        {
            "loss_threshold": -0.1  # 손절 임계값 (-10%)
        }
        """
        try:
            loss_threshold = config.config.get("loss_threshold")
            
            if loss_threshold is None or loss_threshold >= 0:
                logger.warning(f"Invalid loss_threshold: {loss_threshold}")
                return False
            
            logger.info(f"Checking stop loss for {config.symbol}")
            
            if current_price <= 0 or avg_cost <= 0:
                logger.warning(f"Invalid price/cost: current={current_price}, avg={avg_cost}")
                return False
            
            # 손실율 계산
            loss_percent = (current_price - avg_cost) / avg_cost
            
            if loss_percent <= loss_threshold:
                logger.warning(f"Stop loss triggered for {config.symbol}: {loss_percent:.2%}")
                
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
                    
                    logger.info(f"Stop loss order placed: {order.order_id} for {balance.quantity} {config.symbol}")
                    
                    self._record_transaction(
                        asset_id=config.asset_id,
                        transaction_type="sell",
                        quantity=balance.quantity,
                        price=current_price,
                        broker_order_id=order.order_id,
                        strategy="stop_loss"
                    )
                    return True
                else:
                    logger.warning(f"No position to sell for {config.symbol}")
            
            return False
        except Exception as e:
            logger.error(f"Stop loss strategy execution failed: {str(e)}")
            return False
