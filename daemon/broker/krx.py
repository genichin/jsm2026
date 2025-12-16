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


@dataclass
class ManualTrade:
    """수동 등록 거래 정보"""
    trade_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    trade_date: str  # YYYY-MM-DD
    memo: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


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
        self.trades: Dict[str, ManualTrade] = {}  # trade_id -> ManualTrade
        self.pending_orders: Dict[str, Order] = {}  # order_id -> Order
        
        logger.info(f"KRXConnector initialized for {firm_name or 'KRX'}")
        
    def register_trade(self, symbol: str, side: OrderSide, quantity: float, 
                      price: float, trade_date: str, memo: str = "") -> ManualTrade:
        """
        거래 수동 등록
        
        Args:
            symbol: 종목코드
            side: 매수/매도 (OrderSide.BUY or OrderSide.SELL)
            quantity: 거래수량
            price: 거래가격
            trade_date: 거래일 (YYYY-MM-DD 형식)
            memo: 거래 메모
        
        Returns:
            ManualTrade: 등록된 거래 정보
        """
        try:
            trade_id = f"TRD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            trade = ManualTrade(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                trade_date=trade_date,
                memo=memo
            )
            self.trades[trade_id] = trade
            
            # 잔고 업데이트
            self._update_balance_from_trade(trade)
            
            logger.info(f"Registered trade {trade_id}: {side.value} {quantity} {symbol}@{price}")
            return trade
        
        except Exception as e:
            logger.error(f"Failed to register trade: {e}")
            raise
    
    def _update_balance_from_trade(self, trade: ManualTrade) -> None:
        """거래에 따른 잔고 업데이트 (Backend API를 통해 처리됨)"""
        # 실제 잔고 업데이트는 Backend API의 transaction 생성 시 자동으로 처리됨
        logger.debug(f"Trade {trade.trade_id} will update balance via Backend API")
        pass
    
    def get_trade(self, trade_id: str) -> Optional[ManualTrade]:
        """
        거래 조회
        
        Args:
            trade_id: 거래 ID
        
        Returns:
            ManualTrade: 거래 정보
        """
        return self.trades.get(trade_id)
    
    def list_trades(self, symbol: str = None) -> List[ManualTrade]:
        """
        거래 목록 조회
        
        Args:
            symbol: 종목코드 (None이면 모든 거래)
        
        Returns:
            List[ManualTrade]: 거래 목록
        """
        trades = self.trades.values()
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        return sorted(trades, key=lambda t: t.trade_date, reverse=True)
    
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
            
            # Balance 객체로 변환
            balances = {}
            for asset in tradable_assets:
                symbol = asset.get("symbol") or asset.get("id")
                balance = asset.get("balance", 0.0)
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
        """
        주문 접수 (KRX는 수동 거래로 처리됨)
        
        Args:
            symbol: 종목코드
            side: 매수/매도
            qty: 주문수량
            price: 주문가격
        
        Returns:
            Order: 생성된 주문 객체
        """
        try:
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
            logger.info(f"Created pending order {order_id}: {side.value} {qty} {symbol}")
            return order
        
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소
        
        Args:
            order_id: 취소할 주문 ID
        
        Returns:
            bool: 취소 성공 여부
        """
        try:
            if order_id in self.pending_orders:
                self.pending_orders[order_id].status = OrderStatus.CANCELLED
                logger.info(f"Cancelled order {order_id}")
                return True
            logger.warning(f"Order {order_id} not found")
            return False
        
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """주문 상태 확인"""
        order = self.pending_orders.get(order_id)
        if order:
            return order.status
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

    def confirm_order(self, order_id: str, executed_quantity: float = None, 
                     execution_price: float = None) -> bool:
        """
        주문 체결 확인 (수동)
        
        Args:
            order_id: 주문 ID
            executed_quantity: 체결 수량 (None이면 주문 수량 전부)
            execution_price: 체결 가격 (None이면 주문 가격 사용)
        
        Returns:
            bool: 성공 여부
        """
        try:
            if order_id not in self.pending_orders:
                logger.warning(f"Order {order_id} not found")
                return False
            
            order = self.pending_orders[order_id]
            exec_qty = executed_quantity or order.quantity
            exec_price = execution_price or order.price
            
            # 주문 체결 처리
            order.executed_quantity = exec_qty
            order.status = OrderStatus.EXECUTED if exec_qty == order.quantity else OrderStatus.PARTIAL
            
            # 거래 등록
            self.register_trade(
                symbol=order.symbol,
                side=order.side,
                quantity=exec_qty,
                price=exec_price,
                trade_date=datetime.now().strftime("%Y-%m-%d"),
                memo=f"Order {order_id} confirmed"
            )
            
            logger.info(f"Confirmed order {order_id}: {exec_qty} @{exec_price}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to confirm order: {e}")
            return False
    
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

    def _normalize_symbol(self, symbol: str) -> Dict[str, str]:
        """
        심볼 정규화
        - 6자리 숫자면 KRX 티커로 판단
        - yfinance 티커 후보 생성: .KS 우선, 실패 시 .KQ
        """
        s = symbol.strip().upper()
        res = {"raw": s}
        if s.endswith(".KS") or s.endswith(".KQ"):
            res["yf_primary"] = s
            res["yf_fallback"] = s[:-3] + (".KQ" if s.endswith(".KS") else ".KS")
            res["krx"] = s.split(".")[0]
            return res
        if s.isdigit() and len(s) == 6:
            res["yf_primary"] = f"{s}.KS"
            res["yf_fallback"] = f"{s}.KQ"
            res["krx"] = s
            return res
        # 기타 포맷은 그대로 사용 (yfinance가 직접 처리할 수도 있음)
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
            m = self._normalize_symbol(symbol)
            for yf_sym in [m.get("yf_primary"), m.get("yf_fallback")]:
                if not yf_sym:
                    continue
                try:
                    t = yf.Ticker(yf_sym)
                    # history 호출이 비교적 안정적
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
        except Exception:
            return None, None

    def _fetch_price_pykrx(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        pykrx로 가격 조회
        Returns: (last_close, prev_close)
        """
        if stock is None:
            return None, None
        try:
            m = self._normalize_symbol(symbol)
            krx = m.get("krx")
            if not krx:
                return None, None
            end = datetime.now()
            start = end - timedelta(days=14)
            # '종가' 컬럼 사용
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
        except Exception:
            return None, None
    
    def get_orderbook(self, symbol: str, depth: int = 5) -> Optional[OrderBook]:
        """호가정보 조회 (수동 거래에서는 구현되지 않음)"""
        logger.debug(f"Orderbook data not available for {symbol} in manual trading")
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

