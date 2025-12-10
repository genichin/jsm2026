"""
업비트(암호화폐) 브로커 커넥터
"""

from typing import Dict, List
import logging
import requests
from .base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData

logger = logging.getLogger(__name__)


class UpbitConnector(BrokerConnector):
    """업비트(암호화폐) 커넥터"""
    
    def __init__(self, access_key: str = None, secret_key: str = None):
        """
        업비트 API 초기화
        
        Args:
            access_key: Upbit API Access Key
            secret_key: Upbit API Secret Key
        """
        self.access_key = access_key or ""
        self.secret_key = secret_key or ""
        self.base_url = "https://api.upbit.com/v1"
        self.pending_orders: Dict[str, Order] = {}
        logger.info(f"UpbitConnector initialized")
    
    def get_balance(self) -> Dict[str, Balance]:
        """
        현재 계좌 잔고 조회
        
        실제 구현 시:
        - GET /accounts 엔드포인트 호출
        - Authorization: Bearer {access_key} 헤더 필요
        """
        try:
            logger.info("Upbit: Getting balance")
            # TODO: 실제 Upbit API 호출
            # import requests
            # response = requests.get(f"{self.base_url}/accounts", 
            #     headers={"Authorization": f"Bearer {self.access_key}"})
            
            # 임시 반환 (테스트용)
            return {
                "KRW": Balance(symbol="KRW", quantity=5000000.0, avg_price=1.0),
                "BTC": Balance(symbol="BTC", quantity=0.5, avg_price=40000000.0),
                "ETH": Balance(symbol="ETH", quantity=5.0, avg_price=2000000.0),
            }
        except Exception as e:
            logger.error(f"Upbit: Failed to get balance: {str(e)}")
            return {}
    
    def get_pending_orders(self) -> List[Order]:
        """
        미체결 주문 목록
        
        실제 구현 시:
        - GET /orders?state=wait 엔드포인트 호출
        """
        try:
            logger.info("Upbit: Getting pending orders")
            # TODO: 실제 Upbit API 호출
            # response = requests.get(f"{self.base_url}/orders?state=wait",
            #     headers={"Authorization": f"Bearer {self.access_key}"})
            
            return list(self.pending_orders.values())
        except Exception as e:
            logger.error(f"Upbit: Failed to get pending orders: {str(e)}")
            return []
    
    def place_order(self, symbol: str, side: OrderSide, qty: float, 
                   price: float = None) -> Order:
        """
        주문 접수
        
        실제 구현 시:
        - POST /orders 엔드포인트 호출
        - symbol 형식: BTC-KRW, ETH-KRW 등
        """
        try:
            # symbol 정규화 (예: BTC -> BTC-KRW)
            if "-" not in symbol:
                symbol = f"{symbol}-KRW"
            
            logger.info(f"Upbit: Placing {side.value} order for {qty} {symbol}")
            
            # TODO: 실제 Upbit API 호출
            # order_data = {
            #     "market": symbol,
            #     "side": side.value,  # buy or sell
            #     "volume": qty,
            #     "price": price,  # 지정가 주문 시
            #     "ord_type": "limit" if price else "market"
            # }
            # response = requests.post(f"{self.base_url}/orders", json=order_data,
            #     headers={"Authorization": f"Bearer {self.access_key}"})
            
            # 임시 주문 객체 생성
            order_id = f"UPBIT_{symbol}_{len(self.pending_orders) + 1}"
            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=qty,
                price=price or 0.0,
                status=OrderStatus.PENDING,
                executed_quantity=0.0
            )
            self.pending_orders[order_id] = order
            
            logger.info(f"Upbit: Order placed {order_id}")
            return order
            
        except Exception as e:
            logger.error(f"Upbit: Failed to place order: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소
        
        실제 구현 시:
        - DELETE /orders/{uuid} 엔드포인트 호출
        """
        try:
            logger.info(f"Upbit: Cancelling order {order_id}")
            
            # TODO: 실제 Upbit API 호출
            # response = requests.delete(f"{self.base_url}/orders/{order_id}",
            #     headers={"Authorization": f"Bearer {self.access_key}"})
            
            if order_id in self.pending_orders:
                self.pending_orders[order_id].status = OrderStatus.CANCELLED
                logger.info(f"Upbit: Order {order_id} cancelled")
                return True
            
            logger.warning(f"Upbit: Order {order_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Upbit: Failed to cancel order: {str(e)}")
            return False
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """
        주문 상태 확인
        
        실제 구현 시:
        - GET /orders/{uuid} 엔드포인트 호출
        """
        try:
            logger.info(f"Upbit: Getting order status for {order_id}")
            
            # TODO: 실제 Upbit API 호출
            # response = requests.get(f"{self.base_url}/orders/{order_id}",
            #     headers={"Authorization": f"Bearer {self.access_key}"})
            # state = response.json()["state"]  # wait, done, cancel
            
            if order_id in self.pending_orders:
                return self.pending_orders[order_id].status
            
            return OrderStatus.REJECTED
            
        except Exception as e:
            logger.error(f"Upbit: Failed to get order status: {str(e)}")
            return OrderStatus.REJECTED
    
    def get_current_price(self, symbol: str | list) -> PriceData | Dict:
        """
        현재가 조회
        
        실제 구현 시:
        - GET /ticker?markets={market} 엔드포인트 호출 (인증 불필요)
        - symbol 형식: BTC-KRW, ETH-KRW 등
        """
        try:
            # 리스트 처리
            if isinstance(symbol, list):
                logger.info(f"Upbit: Getting prices for {len(symbol)} symbols")
                
                # symbol 정규화 (원본 -> 정규화 매핑)
                normalized_map = {}
                normalized_symbols = []
                for sym in symbol:
                    normalized = f"{sym}-KRW" if "-" not in sym else sym
                    normalized_map[normalized] = sym
                    normalized_symbols.append(normalized)
                
                # 실제 Upbit API 호출 (여러 심볼 한 번에)
                try:
                    markets_param = ','.join(normalized_symbols)
                    response = requests.get(
                        f"{self.base_url}/ticker",
                        params={"markets": markets_param},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # API 응답을 normalized symbol을 키로 하는 딕셔너리로 변환
                    price_map = {}
                    for item in data:
                        market = item.get("market")
                        if market:
                            price_map[market] = PriceData(
                                symbol=market,
                                current_price=item.get("trade_price", 0.0),
                                change_percent=item.get("signed_change_rate", 0.0) * 100
                            )
                    
                    # 원본 심볼로 매핑하여 결과 생성
                    result = {}
                    for normalized_sym in normalized_symbols:
                        original_sym = normalized_map[normalized_sym]
                        if normalized_sym in price_map:
                            # PriceData의 symbol은 원본 심볼로 유지
                            price_data = price_map[normalized_sym]
                            result[original_sym] = PriceData(
                                symbol=original_sym,
                                current_price=price_data.current_price,
                                change_percent=price_data.change_percent
                            )
                        else:
                            logger.warning(f"Upbit: Price data not found for {normalized_sym}")
                            result[original_sym] = PriceData(symbol=original_sym, current_price=0.0, change_percent=0.0)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Upbit: API request failed: {str(e)}")
                    # API 호출 실패 시 빈 데이터로 결과 생성
                    result = {}
                    for normalized_sym in normalized_symbols:
                        original_sym = normalized_map[normalized_sym]
                        result[original_sym] = PriceData(symbol=original_sym, current_price=0.0, change_percent=0.0)
                except Exception as e:
                    logger.error(f"Upbit: Unexpected error while getting prices: {str(e)}")
                    result = {}
                    for normalized_sym in normalized_symbols:
                        original_sym = normalized_map[normalized_sym]
                        result[original_sym] = PriceData(symbol=original_sym, current_price=0.0, change_percent=0.0)
                
                return result
            
            # 단일 심볼 처리
            # 원본 심볼 저장
            original_symbol = symbol
            
            # symbol 정규화
            if "-" not in symbol:
                symbol = f"{symbol}-KRW"
            
            logger.info(f"Upbit: Getting price for {symbol}")
            
            # 실제 Upbit API 호출 (인증 불필요)
            try:
                response = requests.get(
                    f"{self.base_url}/ticker",
                    params={"markets": symbol},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    item = data[0]
                    return PriceData(
                        symbol=original_symbol,
                        current_price=item.get("trade_price", 0.0),
                        change_percent=item.get("signed_change_rate", 0.0) * 100
                    )
                else:
                    logger.warning(f"Upbit: Empty response for {symbol}")
                    return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Upbit: API request failed for {symbol}: {str(e)}")
                return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
            except Exception as e:
                logger.error(f"Upbit: Unexpected error while getting price for {symbol}: {str(e)}")
                return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
            
        except Exception as e:
            logger.error(f"Upbit: Failed to get current price: {str(e)}")
            return PriceData(symbol=symbol, current_price=0.0, change_percent=0.0)
