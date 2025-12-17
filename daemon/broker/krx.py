"""
KRX(한국거래소) 수동 거래 브로커 커넥터
API를 지원하지 않는 금융사의 한국 거래소 종목을 처리하는 모듈
수동으로 거래를 등록하고 관리합니다.
"""

from typing import Dict, List, Optional
import logging
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from datetime import timedelta

# Optional providers
try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None  # type: ignore

try:
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore

# 직접 실행 시 절대 import, 모듈로 import 시 상대 import
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from broker.base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData, OrderBook, OrderBookLevel
    from api import asset_api
else:
    from .base import BrokerConnector, OrderSide, OrderStatus, Order, Balance, PriceData, OrderBook, OrderBookLevel
    from api import asset_api

logger = logging.getLogger(__name__)

class KRXConnector(BrokerConnector):
    """KRX 수동 거래 커넥터
    
    API를 지원하지 않는 금융사의 한국 거래소 종목을 처리합니다.
    거래는 수동으로 등록되며 로컬 메모리에서 관리됩니다.
    """
    
    def __init__(self, firm_name: str = "", **kwargs):
        """
        KRX 수동 거래 커넥터 초기화
        
        Args:
            firm_name: 금융사명 (예: '키움증권', '한국투자')
        """
        self.account_id = kwargs.get("account_id", "")
        self.firm_name = firm_name
        self.symbol_market_map: Dict[str, str] = {}  # symbol -> market (KOSPI/KOSDAQ)
        
        logger.info(f"KRXConnector initialized for {firm_name or 'KRX'}")
    
    def get_balance(self) -> Dict[str, Balance]:
        """현재 계좌 잔고 조회 (Backend API 연동)"""
        try:
            # Backend API로부터 자산 정보 가져오기
            params = {"size": 100, "is_active": True}
            if self.account_id:
                params["account_id"] = self.account_id
                logger.info(f"Filtering assets for account: {self.account_id}")
            
            assets_response = asset_api.list_assets(**params)
            assets = assets_response.get("items", [])
            
            # 현금 자산 제외 (asset_type이 'cash'가 아닌 것만)
            tradable_assets = [
                asset for asset in assets 
                if asset.get("asset_type") != "cash"
            ]
            
            logger.info(f"Backend assets: {len(tradable_assets)} tradable (total: {len(assets)})")
            
            # Balance 객체로 변환 및 market 정보 캐싱
            balances = {}
            for asset in tradable_assets:
                symbol = asset.get("symbol") or asset.get("id")
                balance = asset.get("balance", 0.0)
                market = asset.get("market")  # KOSPI, KOSDAQ, KRW 등
                
                # market 정보 캐싱
                if market and symbol:
                    self.symbol_market_map[symbol] = market
                
                # avg_price는 백엔드에서 제공하지 않으므로 0으로 설정
                balances[symbol] = Balance(
                    symbol=symbol,
                    quantity=balance,
                    avg_price=0.0
                )
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get balance from backend API: {e}")
            return {}
    
    def get_pending_orders(self) -> List[Order]:
        """미체결 주문 목록 없음"""
        return []
    
    def place_order(self, symbol: str, side: OrderSide, qty: float, 
                   price: float = None) -> Order:
        logger.debug(f"Placing manual order: {side.value} {qty} {symbol}@{price or 'MKT'}")

        '''
        수동 거래의 경우 백엔드 API를 통해 해당 자산의 redis에 주문이 필요함을 알려줌 asset:{asset_id}:need_trade:price, asset:{asset_id}:need_trade:quantity
        (실제 주문은 사용자가 증권사 HTS/MTS에서 직접 수행)
        '''
        try:
            # 1) 자산 조회 (account_id와 symbol 동시 필터링)
            params = {"size": 1, "symbol": symbol, "account_id": self.account_id}
            assets_response = asset_api.list_assets(**params)
            items = assets_response.get("items", []) if assets_response else []

            # symbol 필터 미지원 백엔드일 경우를 대비해 후처리
            asset = None
            if items:
                asset = items[0]

            if not asset:
                logger.debug(f"place_order lookup: asset not found for {symbol}")
                return None
            
            asset_id = asset.get("id")
            if not asset_id:
                logger.debug(f"place_order lookup: asset_id not found for {symbol}")
                return None
            # 2) 자산 수동 거래 정보 업데이트
            asset_api.update_asset_need_trade(
                asset_id=asset_id,
                price=price,
                quantity=qty if side == OrderSide.BUY else -qty
            )

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
        # """
        # 주문 접수 (KRX는 수동 거래로 처리됨)
        
        # Args:
        #     symbol: 종목코드
        #     side: 매수/매도
        #     qty: 주문수량
        #     price: 주문가격
        
        # Returns:
        #     Order: 생성된 주문 객체
        # """
        # try:
        #     order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        #     order = Order(
        #         order_id=order_id,
        #         symbol=symbol,
        #         side=side,
        #         quantity=qty,
        #         price=price or 0.0,
        #         status=OrderStatus.PENDING,
        #         executed_quantity=0.0
        #     )
        #     self.pending_orders[order_id] = order
        #     logger.info(f"Created pending order {order_id}: {side.value} {qty} {symbol}")
        #     return order
        
        # except Exception as e:
        #     logger.error(f"Failed to place order: {e}")
        #     raise
    
    def cancel_order(self, order_id: str) -> bool:
        return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        return None
    
    def get_current_price(self, symbol: str | list) -> PriceData | Dict:
        """
        현재가 조회: yfinance 1차, pykrx 2차 폴백 사용
        """
        if isinstance(symbol, list):
            result: Dict[str, PriceData] = {}
            for s in symbol:
                pd = self.get_price(s)
                if pd is None:
                    pd = PriceData(symbol=s, current_price=0.0, change_percent=0.0, change_amount=0.0)
                result[s] = pd
            return result
        else:
            pd = self.get_price(symbol)
            return pd if pd is not None else PriceData(symbol=symbol, current_price=0.0, change_percent=0.0, change_amount=0.0)

    def get_price(self, symbol: str) -> Optional[PriceData]:
        """
        현재가 조회: yfinance → pykrx 폴백
        """
        try:
            # 1) yfinance 시도
            price, prev_close = self._fetch_price_yf(symbol)
            # 2) pykrx 폴백
            if price is None:
                price, prev_close = self._fetch_price_pykrx(symbol)

            if price is None:
                logger.warning(f"Failed to fetch price for {symbol} via yfinance/pykrx")
                return None

            change_amount = 0.0
            change_percent = 0.0
            if prev_close and prev_close > 0:
                change_amount = float(price - prev_close)
                change_percent = float((change_amount / prev_close) * 100.0)

            return PriceData(
                symbol=symbol,
                current_price=float(price),
                change_percent=change_percent,
                change_amount=change_amount,
            )
        except Exception as e:
            logger.error(f"get_price error for {symbol}: {e}")
            return None

    def _normalize_symbol(self, symbol: str, market: str = None) -> Dict[str, str]:
        """
        심볼 정규화
        - market 정보가 있으면 KOSPI→.KS, KOSDAQ→.KQ 직접 매핑
        - market 정보 없으면 기존 fallback 방식 사용
        """
        s = symbol.strip().upper()
        res = {"raw": s}
        
        # 이미 .KS/.KQ suffix가 있는 경우
        if s.endswith(".KS") or s.endswith(".KQ"):
            res["yf_primary"] = s
            res["yf_fallback"] = s[:-3] + (".KQ" if s.endswith(".KS") else ".KS")
            res["krx"] = s.split(".")[0]
            return res
        
        # 6자리 숫자 + market 정보가 있는 경우 (최적 경로)
        if s.isdigit() and len(s) == 6 and market:
            suffix = ".KS" if market == "KOSPI" else ".KQ" if market == "KOSDAQ" else ""
            if suffix:
                res["yf_primary"] = f"{s}{suffix}"
                res["yf_fallback"] = ""  # market 정보가 정확하므로 fallback 불필요
                res["krx"] = s
                return res
        
        # 6자리 숫자이지만 market 정보 없음 (fallback 방식)
        if s.isdigit() and len(s) == 6:
            res["yf_primary"] = f"{s}.KS"
            res["yf_fallback"] = f"{s}.KQ"
            res["krx"] = s
            return res
        
        # 기타 포맷은 그대로 사용
        res["yf_primary"] = s
        res["yf_fallback"] = ""
        res["krx"] = s if s.isdigit() else ""
        return res

    def _fetch_price_yf(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        yfinance로 가격 조회
        Returns: (last_close, prev_close)
        """
        if yf is None:
            return None, None
        try:
            # 캐시된 market 정보 활용
            market = self.symbol_market_map.get(symbol)
            m = self._normalize_symbol(symbol, market=market)
            
            for yf_sym in [m.get("yf_primary"), m.get("yf_fallback")]:
                if not yf_sym:
                    continue
                try:
                    t = yf.Ticker(yf_sym)
                    hist = t.history(period="10d", auto_adjust=False)
                    if hist is None or hist.empty:
                        continue
                    closes = hist["Close"].dropna()
                    if closes.empty:
                        continue
                    last_close = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else None
                    return last_close, prev_close
                except Exception:
                    continue
            return None, None
        except Exception as e:
            logger.error(f"yfinance unexpected error for {symbol}: {e}")
            return None, None

    def _fetch_price_pykrx(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        pykrx로 가격 조회
        Returns: (last_close, prev_close)
        """
        if stock is None:
            return None, None
        try:
            # 캐시된 market 정보 활용 (pykrx는 6자리 KRX 코드만 필요)
            market = self.symbol_market_map.get(symbol)
            m = self._normalize_symbol(symbol, market=market)
            krx = m.get("krx")
            if not krx:
                return None, None
            
            end = datetime.now()
            start = end - timedelta(days=14)
            
            df = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), krx)
            if df is None or df.empty:
                return None, None
            
            # pykrx는 종종 멀티인덱스/컬럼명을 한글로 반환
            col_close_candidates = ["종가", "Close", "close"]
            close_series = None
            for col in col_close_candidates:
                if col in df.columns:
                    close_series = df[col].dropna()
                    break
            
            if close_series is None or close_series.empty:
                return None, None
            
            last_close = float(close_series.iloc[-1])
            prev_close = float(close_series.iloc[-2]) if len(close_series) >= 2 else None
            return last_close, prev_close
        except Exception as e:
            logger.error(f"pykrx error for {symbol}: {e}")
            return None, None
    
    def get_orderbook(self, symbol: str, depth: int = 5) -> Optional[OrderBook]:
        """호가정보 조회 (백엔드 자산 엔드포인트로 현재가만 사용)"""
        try:
            # 1) 자산 조회 (account_id와 symbol 동시 필터링)
            params = {"size": 1, "symbol": symbol, "account_id": self.account_id}
            assets_response = asset_api.list_assets(**params)
            items = assets_response.get("items", []) if assets_response else []

            # symbol 필터 미지원 백엔드일 경우를 대비해 후처리
            asset = None
            if items:
                asset = items[0]

            if not asset:
                logger.debug(f"Orderbook lookup: asset not found for {symbol}")
                return None

            price = (
                asset.get("current_price")
                or asset.get("price")
                or asset.get("last_price")
            )
            if price is None:
                logger.debug(f"Orderbook lookup: price not available for {symbol}")
                return None

            price = float(price)
            bids = [OrderBookLevel(price=price, quantity=10000)]
            asks = [OrderBookLevel(price=price, quantity=10000)]

            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now().timestamp(),
            )
        except Exception as e:
            logger.error(f"Failed to get orderbook for {symbol}: {e}")
            return None

    def get_min_order_price(self) -> float:
        """ 최소 주문 금액 없음. """
        return 0.0
    
    def supports_fractional_trading(self) -> bool:
        """
        소수점 거래 지원 여부
        KRX 주식은 1주 단위로만 거래 가능
        """
        return False

