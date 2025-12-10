"""
거래 전략 추상 클래스
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from broker.base import BrokerConnector
from api import transaction_api

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """전략 타입"""
    DCA = "dca"  # Dollar-Cost Averaging
    REBALANCE = "rebalance"  # 목표 비중 유지
    STOP_LOSS = "stop_loss"  # 손절
    TAKE_PROFIT = "take_profit"  # 익절
    TARGET_VALUE = "target_value"  # 목표 가치 유지


@dataclass
class StrategyConfig:
    """전략 설정"""
    strategy_type: StrategyType
    asset_id: str
    symbol: str
    config: Dict[str, Any]  # 전략별 설정값


class BaseStrategy(ABC):
    """거래 전략 추상 클래스"""
    
    def __init__(self, broker: BrokerConnector):
        self.broker = broker
    
    @abstractmethod
    def execute(self, config: StrategyConfig) -> bool:
        """전략 실행"""
        pass
    
    def _record_transaction(self, asset_id: str, transaction_type: str,
                           quantity: float, price: float,
                           broker_order_id: str, strategy: str) -> bool:
        """백엔드에 거래 기록"""
        try:
            transaction_data = {
                "asset_id": asset_id,
                "type": transaction_type,
                "quantity": quantity,
                "price": price,
                "confirmed": False,  # 나중에 체결 확인 후 업데이트
                "extras": {
                    "broker_order_id": broker_order_id,
                    "strategy": strategy
                }
            }
            
            response = transaction_api.create_transaction(transaction_data)
            logger.info(f"Transaction recorded: {response}")
            return True
        except Exception as e:
            logger.error(f"Failed to record transaction: {str(e)}")
            return False
