"""
Target Value 전략: 목표 평가 금액 유지
"""

import logging
from .base import BaseStrategy, StrategyConfig
from broker.base import OrderSide

logger = logging.getLogger(__name__)


class TargetValueStrategy(BaseStrategy):
    """목표 가치 전략: 자산의 평가 금액을 목표값으로 유지"""
    
    def execute(self, config: StrategyConfig, 
               current_quantity: float,
               orderbook=None) -> bool:
        """
        목표 가치 전략 실행
        
        Args:
            config: 전략 설정
            current_quantity: 현재 보유 수량
            orderbook: 호가 정보
        
        config.config 예시:
        {
            "target_value": 50000000,      # 목표 평가 금액 (KRW 또는 해당 화폐)
            "tolerance_percent": 0.05      # 허용 오차 (±5%)
        }
        """
        #orderbook 이 있는지 확인 없으면 그냥 종료
        if orderbook is None:
            logger.warning("Orderbook is required for target value strategy")
            return False
        try:
            # 소수점 거래 가능 플래그
            allow_fractional = self.broker.supports_fractional_trading()

            target_value = config.config.get("target_price", 0) * config.config.get("target_ratio", 0)
            print(f"Target value: {target_value}")
            tolerance_percent = config.config.get("trade_ratio", 0)
            if tolerance_percent == 0:
                # 기본 값 계산
                # 1. 브로커로 부터 최소 주문 단위 조회
                min_order_price = self.broker.get_min_order_price()
                if min_order_price != 0:
                    tolerance_percent = min_order_price / target_value
                    print(f"Calculated tolerance_percent: {tolerance_percent}")
                else:
                    # orderbook 의 가격 이용 : 가격/목표금액
                    best_price = (orderbook.get_best_bid() + orderbook.get_best_ask()) / 2
                    tolerance_percent = best_price / target_value


            print(f"Using tolerance_percent: {tolerance_percent}")
            
            if not target_value or target_value <= 0:
                logger.warning(f"Invalid target_value: {target_value}")
                return False
            
            logger.info(f"Checking target value strategy for {config.symbol}")

            # 매수 체크 : 두번째 ask 값을 사용한 평가 금액 계산
            current_price = orderbook.asks[1].price if len(orderbook.asks) > 1 else orderbook.get_best_ask()
            current_value = current_price * current_quantity
            # 목표값과의 차이 계산
            value_diff_percent = (target_value - current_value) / target_value
            if value_diff_percent >= tolerance_percent:
                # 매수 필요
                side = OrderSide.BUY
                # 필요한 목표 수량 계산
                target_quantity = target_value / current_price
                # 매수 수량 계산
                quantity_diff = target_quantity - current_quantity
                # 가능한 주문 수량 확인
                available_quantity = orderbook.asks[0].quantity if orderbook.asks else 0
                if len(orderbook.asks) > 1:
                    available_quantity += orderbook.asks[1].quantity
            else:
                # 매도 체크 : 두번째 bid 값을 사용한 평가 금액 계산
                current_price = orderbook.bids[1].price if len(orderbook.bids) > 1 else orderbook.get_best_bid()
                current_value = current_price * current_quantity
                # 목표값과의 차이 계산
                value_diff_percent = (current_value - target_value) / target_value
                if value_diff_percent >= tolerance_percent:
                    # 매도 필요
                    side = OrderSide.SELL
                    # 필요한 목표 수량 계산
                    target_quantity = target_value / current_price
                    # 매도 수량 계산
                    quantity_diff = current_quantity - target_quantity
                    # 가능한 주문 수량 확인
                    available_quantity = orderbook.bids[0].quantity if orderbook.bids else 0
                    if len(orderbook.bids) > 1:
                        available_quantity += orderbook.bids[1].quantity
                else:
                    # 허용 오차 범위 내면 조정 불필요
                    logger.info(
                        f"Target value within tolerance for {config.symbol}: "
                        f"current={current_value:.0f}, target={target_value:.0f}, diff={value_diff_percent:.2%}"
                    )
                    return False

            if allow_fractional is False and quantity_diff < 0.75:
                logger.info(f"Fractional trading not supported and quantity diff too small for {config.symbol}: {quantity_diff:.6f}")
                return False
            
            order_price = current_price
            order_quantity = min(quantity_diff, available_quantity)

            print(f"Placing order: side={side}, quantity={order_quantity}, price={order_price}")
            
            # 주문 접수
            order = self.broker.place_order(
                symbol=config.symbol,
                side=side,
                qty=order_quantity,
                price=order_price
            )
            
            logger.info(
                f"Target value order placed for {config.symbol}: "
                f"{order.order_id} ({side.value}) {order_quantity:.6f} @ {order_price}\n"
                f"  Current: {current_value:.0f}, Target: {target_value:.0f}, Diff: {value_diff_percent:.2%}"
            )
            
            # 백엔드에 거래 기록
            self._record_transaction(
                asset_id=config.asset_id,
                transaction_type=side.value,
                quantity=order_quantity,
                price=order_price,
                broker_order_id=order.order_id,
                strategy="target_value"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Target value strategy execution failed: {str(e)}")
            return False
