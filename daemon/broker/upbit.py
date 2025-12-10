"""
업비트(암호화폐) 브로커 커넥터
"""

from typing import Dict, List, Union
import logging
import sys
from pathlib import Path
import uuid
import hashlib

try:
    import requests
except ImportError:
    requests = None

try:
    import jwt
except ImportError:
    jwt = None

# 직접 실행 시 절대 import, 모듈로 import 시 상대 import
if __name__ == "__main__":
    # 프로젝트 루트를 sys.path에 추가
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from broker.base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData, OrderBook, OrderBookLevel
else:
    from .base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData, OrderBook, OrderBookLevel

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

            # 필수 모듈 확인
            if not requests or not jwt:
                logger.warning("requests or jwt not available, returning dummy balance")
                return {
                    "KRW": Balance(symbol="KRW", quantity=5000000.0, avg_price=1.0),
                    "BTC": Balance(symbol="BTC", quantity=0.5, avg_price=40000000.0),
                    "ETH": Balance(symbol="ETH", quantity=5.0, avg_price=2000000.0),
                }

            # Upbit API 인증 토큰 생성 (JWT)
            query_hash = hashlib.sha512(b"").hexdigest()
            payload = {
                "access_key": self.access_key,
                "nonce": str(uuid.uuid4()),
                "query_hash": query_hash,
                "query_hash_alg": "SHA512",
            }

            token = jwt.encode(payload, self.secret_key, algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(f"{self.base_url}/accounts", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            balances: Dict[str, Balance] = {}
            for item in data:
                currency = item.get("currency")
                balance = float(item.get("balance", 0) or 0)
                avg_price = float(item.get("avg_buy_price", 0) or 0)
                if currency:
                    balances[currency] = Balance(symbol=currency, quantity=balance, avg_price=avg_price)

            logger.info(f"Upbit: Retrieved {len(balances)} balances")
            return balances

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
            # symbol 정규화 (예: BTC -> KRW-BTC)
            if "-" not in symbol:
                symbol = f"KRW-{symbol}"
            
            logger.info(f"Upbit: Placing {side.value} order for {price} {qty} {symbol}")
            
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
                    # Upbit 형식: KRW-BTC (화폐-코인)
                    normalized = f"KRW-{sym}" if "-" not in sym else sym
                    normalized_map[normalized] = sym
                    normalized_symbols.append(normalized)
                
                # 실제 Upbit API 호출 (여러 심볼 한 번에)
                if requests:
                    try:
                        response = requests.get(
                            f"{self.base_url}/ticker",
                            params={"markets": ','.join(normalized_symbols)},
                            timeout=10
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        # 에러 응답 처리
                        if isinstance(data, dict) and 'error' in data:
                            logger.error(f"Upbit API error: {data['error']}")
                            # 폴백: 빈 데이터 반환
                            return {sym: PriceData(symbol=sym, current_price=0.0, change_percent=0.0) 
                                    for sym in symbol}
                        
                        result = {}
                        for item in data:
                            market = item['market']
                            original_sym = normalized_map.get(market, market)
                            result[original_sym] = PriceData(
                                symbol=original_sym,
                                current_price=item['trade_price'],
                                change_percent=item['signed_change_rate'] * 100
                            )
                        
                        # 응답에 없는 심볼은 0으로 처리
                        for sym in symbol:
                            if sym not in result:
                                result[sym] = PriceData(symbol=sym, current_price=0.0, change_percent=0.0)
                        
                        return result
                    except Exception as e:
                        logger.error(f"Failed to fetch prices from Upbit API: {str(e)}")
                        # 폴백: 빈 데이터 반환
                        return {sym: PriceData(symbol=sym, current_price=0.0, change_percent=0.0) 
                                for sym in symbol}
                else:
                    logger.warning("requests module not available, returning dummy data")
                    # requests 모듈이 없는 경우 더미 데이터
                    price_map = {
                        "KRW-BTC": PriceData(symbol="KRW-BTC", current_price=45000000.0, change_percent=2.5),
                        "KRW-ETH": PriceData(symbol="KRW-ETH", current_price=2500000.0, change_percent=-1.2),
                        "KRW-XRP": PriceData(symbol="KRW-XRP", current_price=3000.0, change_percent=0.5),
                    }
                    
                    result = {}
                    for normalized_sym in normalized_symbols:
                        original_sym = normalized_map[normalized_sym]
                        if normalized_sym in price_map:
                            price_data = price_map[normalized_sym]
                            result[original_sym] = PriceData(
                                symbol=original_sym,
                                current_price=price_data.current_price,
                                change_percent=price_data.change_percent
                            )
                        else:
                            result[original_sym] = PriceData(symbol=original_sym, current_price=0.0, change_percent=0.0)
                    
                    return result
            
            # 단일 심볼 처리
            original_symbol = symbol
            # symbol 정규화 - Upbit 형식: KRW-BTC (화폐-코인)
            if "-" not in symbol:
                symbol = f"KRW-{symbol}"
            
            logger.info(f"Upbit: Getting price for {symbol}")
            
            # 실제 Upbit API 호출 (인증 불필요)
            if requests:
                try:
                    response = requests.get(
                        f"{self.base_url}/ticker",
                        params={"markets": symbol},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # 에러 응답 처리
                    if isinstance(data, dict) and 'error' in data:
                        logger.error(f"Upbit API error: {data['error']}")
                        return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
                    
                    if data and len(data) > 0:
                        item = data[0]
                        return PriceData(
                            symbol=original_symbol,
                            current_price=item['trade_price'],
                            change_percent=item['signed_change_rate'] * 100
                        )
                    else:
                        logger.warning(f"Upbit: No price data returned for {symbol}")
                        return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch price from Upbit API: {str(e)}")
                    return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
            else:
                logger.warning("requests module not available, returning dummy data")
                # requests 모듈이 없는 경우 더미 데이터
                price_map = {
                    "KRW-BTC": PriceData(symbol="KRW-BTC", current_price=45000000.0, change_percent=2.5),
                    "KRW-ETH": PriceData(symbol="KRW-ETH", current_price=2500000.0, change_percent=-1.2),
                    "KRW-XRP": PriceData(symbol="KRW-XRP", current_price=3000.0, change_percent=0.5),
                }
                
                if symbol in price_map:
                    price_data = price_map[symbol]
                    return PriceData(
                        symbol=original_symbol,
                        current_price=price_data.current_price,
                        change_percent=price_data.change_percent
                    )
                
                logger.warning(f"Upbit: Price data not found for {symbol}")
                return PriceData(symbol=original_symbol, current_price=0.0, change_percent=0.0)
            
        except Exception as e:
            logger.error(f"Upbit: Failed to get current price: {str(e)}")
            return PriceData(symbol=symbol, current_price=0.0, change_percent=0.0)
    
    def get_orderbook(self, symbol: Union[str, list]) -> Union[OrderBook, Dict]:
        """
        호가 조회 (5단계)
        
        실제 구현 시:
        - GET /orderbook?markets={market} 엔드포인트 호출
        """
        try:
            if isinstance(symbol, list):
                logger.info(f"Upbit: Getting orderbook for {len(symbol)} symbols")
                result = {}
                
                for sym in symbol:
                    normalized = f"KRW-{sym}" if "-" not in sym else sym
                    
                    if requests:
                        try:
                            response = requests.get(
                                f"{self.base_url}/orderbook",
                                params={"markets": normalized},
                                timeout=10
                            )
                            response.raise_for_status()
                            data = response.json()
                            
                            if isinstance(data, dict) and 'error' in data:
                                logger.error(f"Upbit API error: {data['error']}")
                                result[sym] = OrderBook(symbol=sym)
                                continue
                            
                            if data and len(data) > 0:
                                item = data[0]
                                orderbook_units = item.get('orderbook_units', [])
                                
                                if orderbook_units:
                                    # 최대 5개씩 추출
                                    bids = [OrderBookLevel(price=unit['bid_price'], quantity=unit['bid_size']) 
                                           for unit in orderbook_units[:5] if 'bid_price' in unit]
                                    asks = [OrderBookLevel(price=unit['ask_price'], quantity=unit['ask_size']) 
                                           for unit in orderbook_units[:5] if 'ask_price' in unit]
                                    
                                    result[sym] = OrderBook(
                                        symbol=sym,
                                        bids=bids,
                                        asks=asks
                                    )
                                else:
                                    result[sym] = OrderBook(symbol=sym)
                            else:
                                result[sym] = OrderBook(symbol=sym)
                        
                        except Exception as e:
                            logger.error(f"Failed to fetch orderbook for {sym}: {str(e)}")
                            result[sym] = OrderBook(symbol=sym)
                    else:
                        # 더미 데이터 (5단계)
                        price = 45000000.0 if sym == "BTC" else 2500000.0
                        result[sym] = OrderBook(
                            symbol=sym,
                            bids=[OrderBookLevel(price=price * (0.999 - i * 0.002), quantity=0.1) for i in range(5)],
                            asks=[OrderBookLevel(price=price * (1.001 + i * 0.002), quantity=0.1) for i in range(5)]
                        )
                
                return result
            
            # 단일 심볼 처리
            original_symbol = symbol
            normalized = f"KRW-{symbol}" if "-" not in symbol else symbol
            
            logger.info(f"Upbit: Getting orderbook for {normalized}")
            
            if requests:
                try:
                    response = requests.get(
                        f"{self.base_url}/orderbook",
                        params={"markets": normalized},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if isinstance(data, dict) and 'error' in data:
                        logger.error(f"Upbit API error: {data['error']}")
                        return OrderBook(symbol=original_symbol)
                    
                    if data and len(data) > 0:
                        item = data[0]
                        orderbook_units = item.get('orderbook_units', [])
                        
                        if orderbook_units:
                            # 최대 5개씩 추출
                            bids = [OrderBookLevel(price=unit['bid_price'], quantity=unit['bid_size']) 
                                   for unit in orderbook_units[:5] if 'bid_price' in unit]
                            asks = [OrderBookLevel(price=unit['ask_price'], quantity=unit['ask_size']) 
                                   for unit in orderbook_units[:5] if 'ask_price' in unit]
                            
                            return OrderBook(
                                symbol=original_symbol,
                                bids=bids,
                                asks=asks
                            )
                    
                    return OrderBook(symbol=original_symbol)
                
                except Exception as e:
                    logger.error(f"Failed to fetch orderbook: {str(e)}")
                    return OrderBook(symbol=original_symbol)
            else:
                # 더미 데이터 (5단계)
                price = 45000000.0 if symbol == "BTC" else 2500000.0
                return OrderBook(
                    symbol=original_symbol,
                    bids=[OrderBookLevel(price=price * (0.999 - i * 0.002), quantity=0.1) for i in range(5)],
                    asks=[OrderBookLevel(price=price * (1.001 + i * 0.002), quantity=0.1) for i in range(5)]
                )
        
        except Exception as e:
            logger.error(f"Upbit: Failed to get orderbook: {str(e)}")
            return OrderBook(symbol=symbol)

    def get_min_order_price(self) -> float:
        return 5000.0

    def supports_fractional_trading(self) -> bool:
        return True

if __name__ == "__main__":
    # 간단한 테스트
    logging.basicConfig(level=logging.INFO)
    
    print("=== Upbit Connector Test ===")
    connector = UpbitConnector(access_key="test-key", secret_key="test-secret")
    
    # 단일 심볼 테스트
    print("\n1. Single symbol test (BTC):")
    price = connector.get_current_price('BTC')
    print(f"   Symbol: {price.symbol}")
    print(f"   Price: {price.current_price:,.0f} KRW")
    print(f"   Change: {price.change_percent:+.2f}%")
    
    # 여러 심볼 테스트
    print("\n2. Multiple symbols test (BTC, ETH, XRP):")
    prices = connector.get_current_price(['BTC', 'ETH', 'XRP'])
    for symbol, price_data in prices.items():
        print(f"   {symbol}: {price_data.current_price:,.0f} KRW ({price_data.change_percent:+.2f}%)")