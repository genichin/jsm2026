"""
거래 전략 실행 엔진
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from broker.base import OrderSide
from broker import BrokerConnector
from api import asset_api, transaction_api

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """전략 타입"""
    DCA = "dca"  # Dollar-Cost Averaging
    REBALANCE = "rebalance"  # 목표 비중 유지
    STOP_LOSS = "stop_loss"  # 손절
    TAKE_PROFIT = "take_profit"  # 익절


@dataclass
class StrategyConfig:
    """전략 설정"""
    strategy_type: StrategyType
    asset_id: str
    symbol: str
    # DCA 설정
    monthly_amount: Optional[float] = None
    # Rebalance 설정
    target_weight: Optional[float] = None
    rebalance_threshold: Optional[float] = 0.05  # ±5%
    # Stop Loss / Take Profit 설정
    loss_threshold: Optional[float] = None  # -10% 등
    profit_threshold: Optional[float] = None  # +20% 등


class StrategyRunner:
    """거래 전략 실행기"""
    
    def __init__(self, broker: BrokerConnector):
        self.broker = broker
    
    def execute_dca(self, config: StrategyConfig) -> bool:
        """DCA 전략 실행"""
        try:
            logger.info(f"Executing DCA strategy for {config.symbol}")
            
            # 현재가 조회
            price_data = self.broker.get_current_price(config.symbol)
            current_price = price_data.current_price
            
            if current_price <= 0:
                logger.warning(f"Invalid price for {config.symbol}: {current_price}")
                return False
            
            # 매수 수량 계산
            buy_quantity = config.monthly_amount / current_price
            
            # 주문 접수
            order = self.broker.place_order(
                symbol=config.symbol,
                side=OrderSide.BUY,
                qty=buy_quantity,
                price=current_price
            )
            
            logger.info(f"DCA order placed: {order.order_id} for {buy_quantity} {config.symbol}")
            
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
    
    def execute_rebalance(self, config: StrategyConfig, 
                         current_weight: float) -> bool:
        """목표 비중 유지 전략 실행"""
        try:
            logger.info(f"Executing rebalance strategy for {config.symbol}")
            
            # 목표 비중과의 차이 계산
            weight_diff = abs(current_weight - config.target_weight)
            
            if weight_diff <= config.rebalance_threshold:
                logger.info(f"Rebalance not needed for {config.symbol}: diff={weight_diff}")
                return False
            
            # 현재가 조회
            price_data = self.broker.get_current_price(config.symbol)
            current_price = price_data.current_price
            
            # 리밸런싱 필요: 매수 또는 매도
            side = OrderSide.BUY if current_weight < config.target_weight else OrderSide.SELL
            
            # 수량 계산 (간단한 예시)
            adjust_quantity = weight_diff * 100  # 임의 계산
            
            order = self.broker.place_order(
                symbol=config.symbol,
                side=side,
                qty=adjust_quantity,
                price=current_price
            )
            
            logger.info(f"Rebalance order placed: {order.order_id} ({side.value}) {adjust_quantity} {config.symbol}")
            
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
    
    def execute_stop_loss(self, config: StrategyConfig, 
                         current_price: float, avg_cost: float) -> bool:
        """손절 전략 실행"""
        try:
            if config.loss_threshold is None:
                return False
            
            loss_percent = (current_price - avg_cost) / avg_cost * 100
            
            if loss_percent <= config.loss_threshold:
                logger.info(f"Stop loss triggered for {config.symbol}: {loss_percent}%")
                
                # 매도 주문
                balance = self.broker.get_balance().get(config.symbol)
                if balance and balance.quantity > 0:
                    order = self.broker.place_order(
                        symbol=config.symbol,
                        side=OrderSide.SELL,
                        qty=balance.quantity,
                        price=current_price
                    )
                    
                    self._record_transaction(
                        asset_id=config.asset_id,
                        transaction_type="sell",
                        quantity=balance.quantity,
                        price=current_price,
                        broker_order_id=order.order_id,
                        strategy="stop_loss"
                    )
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Stop loss strategy execution failed: {str(e)}")
            return False
    
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
