"""
전략 팩토리 및 매니저
"""

import logging
from typing import Dict, Type
from .base import BaseStrategy, StrategyType, StrategyConfig
from .dca import DCAStrategy
from .rebalance import RebalanceStrategy
from .stop_loss import StopLossStrategy
from .take_profit import TakeProfitStrategy
from .target_value import TargetValueStrategy
from broker.base import BrokerConnector

logger = logging.getLogger(__name__)


# 전략 타입별 클래스 매핑
STRATEGY_REGISTRY: Dict[StrategyType, Type[BaseStrategy]] = {
    StrategyType.DCA: DCAStrategy,
    StrategyType.REBALANCE: RebalanceStrategy,
    StrategyType.STOP_LOSS: StopLossStrategy,
    StrategyType.TAKE_PROFIT: TakeProfitStrategy,
    StrategyType.TARGET_VALUE: TargetValueStrategy,
}


class StrategyFactory:
    """전략 팩토리: 전략 타입에 따라 적절한 전략 인스턴스 생성"""
    
    @staticmethod
    def create_strategy(strategy_type: StrategyType, 
                       broker: BrokerConnector) -> BaseStrategy:
        """
        전략 인스턴스 생성
        
        Args:
            strategy_type: 전략 타입 (StrategyType enum)
            broker: 브로커 커넥터
            
        Returns:
            해당 전략의 인스턴스
            
        Raises:
            ValueError: 미지원하는 전략 타입
        """
        if strategy_type not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        strategy_class = STRATEGY_REGISTRY[strategy_type]
        return strategy_class(broker)


class StrategyRunner:
    """전략 실행기: 여러 자산에 대한 전략 실행 관리"""
    
    def __init__(self, broker: BrokerConnector):
        self.broker = broker
    
    def execute_strategy(self, config: StrategyConfig, **kwargs) -> bool:
        """
        전략 실행
        
        Args:
            config: 전략 설정
            **kwargs: 전략별 추가 인자 (current_weight, current_price, avg_cost 등)
            
        Returns:
            전략 실행 성공 여부
        """
        try:
            strategy_type = config.strategy_type
            strategy = StrategyFactory.create_strategy(strategy_type, self.broker)
            
            # 전략별로 필요한 인자 전달
            if strategy_type == StrategyType.REBALANCE:
                current_weight = kwargs.get("current_weight")
                return strategy.execute(config, current_weight)
            elif strategy_type == StrategyType.STOP_LOSS:
                current_price = kwargs.get("current_price")
                avg_cost = kwargs.get("avg_cost")
                return strategy.execute(config, current_price, avg_cost)
            elif strategy_type == StrategyType.TAKE_PROFIT:
                current_price = kwargs.get("current_price")
                avg_cost = kwargs.get("avg_cost")
                return strategy.execute(config, current_price, avg_cost)
            elif strategy_type == StrategyType.TARGET_VALUE:
                current_quantity = kwargs.get("current_quantity")
                orderbook = kwargs.get("orderbook")
                return strategy.execute(config, current_quantity, orderbook)
            else:  # DCA 등
                return strategy.execute(config)
        
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            return False
