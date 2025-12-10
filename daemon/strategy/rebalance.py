"""
Rebalance 전략: 목표 비중 유지
"""

import logging
from .base import BaseStrategy, StrategyConfig
from broker.base import OrderSide

logger = logging.getLogger(__name__)


class RebalanceStrategy(BaseStrategy):
    """리밸런스 전략: 포트폴리오 목표 비중 유지"""
    
    def execute(self, config: StrategyConfig, current_weight: float = None) -> bool:
        """
        리밸런스 전략 실행
        
        config.config 예시:
        {
            "target_weight": 0.3,        # 목표 비중 (30%)
            "rebalance_threshold": 0.05  # 리밸런싱 임계값 (±5%)
        }
        """
        try:
            if current_weight is None:
                logger.warning("current_weight is required for rebalance strategy")
                return False
            
            logger.info(f"Executing rebalance strategy for {config.symbol}")
            
            target_weight = config.config.get("target_weight")
            rebalance_threshold = config.config.get("rebalance_threshold", 0.05)
            
            if not target_weight or target_weight <= 0:
                logger.warning(f"Invalid target_weight: {target_weight}")
                return False
            
            # 목표 비중과의 차이 계산
            weight_diff = abs(current_weight - target_weight)
            
            if weight_diff <= rebalance_threshold:
                logger.info(f"Rebalance not needed for {config.symbol}: diff={weight_diff:.4f}")
                return False
            
            # 현재가 조회
            price_data = self.broker.get_current_price(config.symbol)
            current_price = price_data.current_price
            
            if current_price <= 0:
                logger.warning(f"Invalid price for {config.symbol}: {current_price}")
                return False
            
            # 리밸런싱 필요: 매수 또는 매도
            side = OrderSide.BUY if current_weight < target_weight else OrderSide.SELL
            
            # 수량 계산 (간단한 예시)
            adjust_quantity = weight_diff * 100  # 임의 계산
            
            order = self.broker.place_order(
                symbol=config.symbol,
                side=side,
                qty=adjust_quantity,
                price=current_price
            )
            
            logger.info(f"Rebalance order placed: {order.order_id} ({side.value}) {adjust_quantity} {config.symbol} @ {current_price}")
            
            # 백엔드에 거래 기록
            self._record_transaction(
                asset_id=config.asset_id,
                transaction_type=side.value,
                quantity=adjust_quantity,
                price=current_price,
                broker_order_id=order.order_id,
                strategy="rebalance"
            )
            
            return True
        except Exception as e:
            logger.error(f"Rebalance strategy execution failed: {str(e)}")
            return False
