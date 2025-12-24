"""
daemon 메인 스케줄러 및 태스크
"""

import logging
import sys
import threading
import os
from typing import Callable, Optional, Tuple, Dict
try:
    import fcntl  # POSIX file locking
except ImportError:  # pragma: no cover
    fcntl = None
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from config import settings
from api import asset_api
from broker import get_broker_connector
from strategy import StrategyRunner, StrategyFactory, StrategyType, StrategyConfig

# 로깅 설정
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('daemon.log')
    ]
)
logger = logging.getLogger(__name__)


class DaemonScheduler:
    """daemon 스케줄러"""
    
    def __init__(self):
        # APScheduler에 Asia/Seoul 타임존 설정 (KST 기준 cron 실행)
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Seoul'))
        logger.info(f"Broker config: type={settings.broker}, key_len={len(settings.broker_app_key or '')}, secret_len={len(settings.broker_app_secret or '')}, account_id={settings.account_id}")
        self.broker = get_broker_connector(
            broker_type=settings.broker,
            access_key=settings.broker_app_key,
            secret_key=settings.broker_app_secret,
            account_id=settings.account_id,
            account_config_ttl=settings.account_config_ttl_sec
        )
        self.strategy_runner = StrategyRunner(self.broker)
        # 중복 실행 방지 락
        self._strategy_lock = threading.Lock()
        self._strategy_file_lock_fh = None
        # 계좌 설정 캐시
        self._account_config: Optional[Dict] = None
        self._account_config_cache_time: Optional[object] = None
        # TTL은 설정에서 가져와 브로커와 일관되게 사용
        self._account_config_ttl: int = settings.account_config_ttl_sec
    
    def _get_account_config(self, force_refresh: bool = False) -> Dict:
        """
        계좌 설정 조회 (캐싱)
        
        Args:
            force_refresh: 강제 새로고침 여부
        
        Returns:
            Dict: accounts.daemon_config 내용
        """
        from datetime import datetime
        
        now = datetime.now()
        
        # 캐시 유효성 검사
        cache_valid = (
            not force_refresh
            and self._account_config is not None
            and self._account_config_cache_time is not None
            and (now - self._account_config_cache_time).total_seconds() < self._account_config_ttl
        )
        
        if cache_valid:
            logger.debug("Using cached account config")
            return self._account_config
        
        # Backend API에서 계좌 설정 조회
        try:
            logger.info(f"Fetching account config for {settings.account_id}")
            response = asset_api.client.get(f"/accounts/{settings.account_id}")
            account_data = response.json()
            daemon_config = account_data.get("daemon_config", {})
            
            # 캐시 업데이트
            self._account_config = daemon_config
            self._account_config_cache_time = now
            
            logger.info(f"Fetched account config with keys: {list(daemon_config.keys()) if daemon_config else 'empty'}")
            return daemon_config
            
        except Exception as e:
            logger.error(f"Failed to fetch account config: {str(e)}")
            # 에러 시 기존 캐시 반환
            return self._account_config if self._account_config else {}
    
    def _invalidate_account_config_cache(self):
        """
        계좌 설정 캐시 무효화 (전략 실행 후)
        """
        self._account_config = None
        self._account_config_cache_time = None
        logger.debug("Account config cache invalidated")
    
    def setup_jobs(self):
        """모든 스케줄 작업 설정"""
        logger.info("Setting up daemon scheduler jobs")
        
        # 잔고 동기화 (평일 08:00)
        if settings.schedule_balance_cron:
            self.scheduler.add_job(
                self.sync_balance,
                CronTrigger.from_crontab(settings.schedule_balance_cron),
                id="balance_sync",
                name="Balance Synchronization",
                max_instances=1,
                replace_existing=True,
                coalesce=settings.scheduler_coalesce,
                misfire_grace_time=settings.scheduler_misfire_grace_time
            )
            logger.info(f"Added job: balance_sync with cron '{settings.schedule_balance_cron}'")
        else:
            logger.info("Skipped job: balance_sync (SCHEDULE_BALANCE_CRON not configured)")
        
        # 전략 실행 (10분마다)
        if settings.schedule_strategy_cron:
            self.scheduler.add_job(
                self.execute_strategy,
                CronTrigger.from_crontab(settings.schedule_strategy_cron),
                id="strategy_runner",
                name="Strategy Execution",
                max_instances=1,
                replace_existing=True,
                coalesce=settings.scheduler_coalesce,
                misfire_grace_time=settings.scheduler_misfire_grace_time
            )
            logger.info(f"Added job: strategy_runner with cron '{settings.schedule_strategy_cron}'")
        else:
            logger.info("Skipped job: strategy_runner (SCHEDULE_STRATEGY_CRON not configured)")
        
        # 가격 업데이트 (거래시간 중 5분마다)
        if settings.schedule_price_update_cron:
            self.scheduler.add_job(
                self.update_asset_prices,
                CronTrigger.from_crontab(settings.schedule_price_update_cron),
                id="price_updater",
                name="Price Update",
                max_instances=1,
                replace_existing=True,
                coalesce=settings.scheduler_coalesce,
                misfire_grace_time=settings.scheduler_misfire_grace_time
            )
            logger.info(f"Added job: price_updater with cron '{settings.schedule_price_update_cron}'")
        else:
            logger.info("Skipped job: price_updater (SCHEDULE_PRICE_UPDATE_CRON not configured)")

    def _acquire_process_lock(self) -> Tuple[bool, Optional[Callable[[], None]], str]:
        """멀티 프로세스용 락 획득 시도 (파일락 사용).
        Returns: (acquired, release_fn, method)
        method in {"file","none"}
        """
        # 파일락 (POSIX 전용)
        if fcntl is not None:
            try:
                # 잠금 파일 오픈(생성 포함)
                fh = open(settings.strategy_lock_file, "a+")
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    try:
                        fh.close()
                    except Exception:
                        pass
                    return False, None, "file"
                # 잠금 성공 시 핸들 저장
                self._strategy_file_lock_fh = fh
                def _release_file():
                    try:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                    try:
                        fh.close()
                    except Exception:
                        pass
                    self._strategy_file_lock_fh = None
                return True, _release_file, "file"
            except Exception as e:
                logger.warning(f"File lock acquire failed: {e}")

        return False, None, "none"
    
    def start(self):
        """스케줄러 시작"""
        self.setup_jobs()
        self.scheduler.start()
        logger.info("Daemon scheduler started")
        
        # daemon 시작 시 현재 시간이 개장~마감 사이면 즉시 전략 실행
        from datetime import datetime, time as dt_time
        now = datetime.now()
        current_time = now.time()
        
        # 개장/마감 시간 파싱
        open_hour, open_min = map(int, settings.market_open_time.split(':'))
        close_hour, close_min = map(int, settings.market_close_time.split(':'))
        market_open = dt_time(open_hour, open_min)
        market_close = dt_time(close_hour, close_min)
        
        # 거래 시간 체크 (tradable_everyday=true면 주말 포함)
        is_trading_day = settings.tradable_everyday or (now.weekday() < 5)
        
        if is_trading_day and market_open <= current_time < market_close:
            logger.info(f"Daemon started during market hours ({current_time.strftime('%H:%M:%S')}), starting strategy execution immediately")
            # 별도 스레드에서 실행 (메인 루프 블로킹 방지)
            import threading
            strategy_thread = threading.Thread(target=self.execute_strategy, daemon=True)
            strategy_thread.start()
        else:
            logger.info(f"Daemon started outside market hours ({current_time.strftime('%H:%M:%S')}), waiting for scheduled cron")
        
        # 대기
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        logger.info("Daemon scheduler stopped")
    
    def sync_balance(self):
        """잔고 동기화 (백엔드 DB와 브로커 API 비교)"""
        try:
            logger.info("=== Starting balance synchronization ===")
            
            # 1. 브로커에서 잔고 조회
            broker_balance = self.broker.get_balance()
            #logger.info(f"Broker balance: {broker_balance}")
            
            # 2. 백엔드에서 자산 목록 조회 (특정 계좌의 거래가능 자산만)
            # ACCOUNT_ID가 설정된 경우 해당 계좌만, 현금 제외
            params = {"size": 100}
            if settings.account_id:
                params["account_id"] = settings.account_id
                logger.info(f"Filtering assets for account: {settings.account_id}")
            
            assets_response = asset_api.list_assets(**params)
            assets = assets_response.get("items", [])
            
            # 현금 자산 제외 (asset_type이 'cash'가 아닌 것만)
            tradable_assets = [
                asset for asset in assets 
                if asset.get("asset_type") != "cash"
            ]
            
            logger.info(f"Backend assets count: {len(tradable_assets)} (total: {len(assets)}, filtered out cash assets)")
            
            # 3. 비교 및 동기화 (여기서는 로그만)
            for asset in tradable_assets:
                symbol = asset.get("symbol")
                backend_balance = asset.get("balance")
                
                if symbol and symbol in broker_balance:
                    broker_qty = broker_balance[symbol].quantity
                    if abs(broker_qty - backend_balance) > 0.001:
                        logger.warning(
                            f"Balance mismatch for {symbol}: "
                            f"broker={broker_qty}, backend={backend_balance}"
                        )
                else:
                    logger.debug(f"Asset {symbol} not in broker balance")
            
            logger.info("=== Balance synchronization completed ===")
            
        except Exception as e:
            logger.error(f"Balance synchronization failed: {str(e)}")
    
    def execute_strategy(self):
        """전략 실행 (개장~마감 시간 동안 루프)"""
        acquired = False
        release_proc: Optional[Callable[[], None]] = None
        lock_method = "none"
        # 프로세스 간 중복 실행 방지
        proc_ok, release_fn, lock_method = self._acquire_process_lock()
        if not proc_ok:
            logger.info(f"Strategy already running in another process (method={lock_method}); skipping this invocation")
            return
        release_proc = release_fn
        # 중복 실행 방지: 프로세스 내 스레드 간 보호
        try:
            if not self._strategy_lock.acquire(blocking=False):
                logger.info("Strategy already running; skipping this invocation")
                return
            acquired = True

            from datetime import datetime, time as dt_time
            import time as time_module
            
            logger.info("=== Starting strategy execution loop ===")
            
            # 장 마감 시간 파싱
            close_hour, close_min = map(int, settings.market_close_time.split(':'))
            market_close = dt_time(close_hour, close_min)
            loop_interval = settings.strategy_loop_interval
            
            logger.info(f"Market hours: {settings.market_open_time}~{settings.market_close_time}, Loop interval: {loop_interval}s")
            
            while True:
                now = datetime.now()
                current_time = now.time()
                
                # 마감 시간 체크
                if current_time >= market_close:
                    logger.info(f"Market closed at {current_time.strftime('%H:%M:%S')}, stopping strategy loop")
                    break
                
                # 평일 체크 (월~금: 0~4, tradable_everyday=true면 체크 안함)
                if (not settings.tradable_everyday) and now.weekday() >= 5:
                    logger.info("Weekend detected, stopping strategy loop")
                    break
                
                logger.info(f"=== Strategy execution at {now.strftime('%H:%M:%S')} ===")
                
                # 1. 미체결 거래 취소
                pending_orders = self.broker.get_pending_orders()
                if pending_orders:
                    logger.info(f"Found {len(pending_orders)} pending orders, cancelling...")
                    for order in pending_orders:
                        self.broker.cancel_order(order.order_id)
                        logger.info(f"Cancelled order: {order.order_id}")
            
                # 2. 브로커에서 최신 잔고 조회
                broker_balance = self.broker.get_balance()

                # 3. 백엔드에서 계좌 정보 조회 (캐싱)
                account_config = self._get_account_config()
                logger.debug(f"Account config keys: {list(account_config.keys()) if account_config else 'empty'}")
                
                # 4. 백엔드에서 자산 설정 조회
                # ACCOUNT_ID가 설정된 경우 해당 계좌만, 현금 제외
                params = {"size": 100}
                if settings.account_id:
                    params["account_id"] = settings.account_id
                    logger.info(f"Filtering assets for account: {settings.account_id}")
                
                assets_response = asset_api.list_assets(**params)
                assets = assets_response.get("items", [])
                
                # 현금 자산 제외 (asset_type이 'cash'가 아닌 것만)
                tradable_assets = [
                    asset for asset in assets 
                    if asset.get("asset_type") != "cash"
                ]
                
                logger.info(f"Backend assets count: {len(tradable_assets)} (total: {len(assets)}, filtered out cash assets)")
                
                # 4. 각 자산별 전략 실행
                for asset in tradable_assets:
                    asset_id = asset.get("id")
                    symbol = asset.get("symbol")
                    metadata = asset.get("asset_metadata", {})
                   
                    if not symbol:
                        logger.debug(f"Skipping asset without symbol")
                        continue

                    # metadata가 없으면 스킵
                    if not metadata:
                        logger.debug(f"Skipping asset {symbol} due to missing metadata")
                        continue

                    # 
                    strategy = metadata.get("strategy")
                    if not strategy:
                        logger.debug(f"Skipping asset {symbol} due to missing strategy in metadata")
                        continue

                    # 전략 유형 확인 metadata에서 'strategy_type' 키 확인
                    strategy_type_str = strategy.get("type", "not_defined").lower()
                    
                    try:
                        # 문자열을 StrategyType enum으로 변환
                        strategy_type = StrategyType[strategy_type_str.upper()]
                    except KeyError:
                        logger.warning(f"Unknown strategy type for {symbol}: {strategy_type_str}")
                        continue
                    
                    # 전략 설정 생성 (계좌 공통 설정 포함)
                    strategy_config = StrategyConfig(
                        strategy_type=strategy_type,
                        asset_id=asset_id,
                        symbol=symbol,
                        config=strategy.get("config", {}),
                        account_config=account_config  # 계좌 공통 설정 전달
                    )
                    
                    # 전략 실행 (필요시 추가 인자 전달)
                    try:
                        logger.info(f"Executing {strategy_type.value} strategy for {symbol}")
                        
                        # 전략별 추가 인자 준비
                        kwargs = {}
                        
                        if strategy_type == StrategyType.REBALANCE:
                            # 현재 비중 계산 (예시)
                            current_weight = asset.get("balance", 0) / 100  # 간단한 예시
                            kwargs["current_weight"] = current_weight
                        
                        elif strategy_type in [StrategyType.STOP_LOSS, StrategyType.TAKE_PROFIT]:
                            # 현재가 조회
                            price_data = self.broker.get_current_price(symbol)
                            kwargs["current_price"] = price_data.current_price
                            kwargs["avg_cost"] = asset.get("avg_price", price_data.current_price)
                        
                        elif strategy_type == StrategyType.TARGET_VALUE:
                            # 보유 수량은 broker_balance에서 조회
                            kwargs["current_quantity"] = broker_balance.get(symbol, 0).quantity
                            # 호가 정보 조회
                            orderbook = self.broker.get_orderbook(symbol)
                            kwargs["orderbook"] = orderbook
                        
                        # 전략 실행
                        result = self.strategy_runner.execute_strategy(strategy_config, **kwargs)
                        
                        if result:
                            logger.info(f"Strategy executed successfully for {symbol}")
                            # 주문 발생 시 계좌 설정 캐시 무효화
                            self._invalidate_account_config_cache()
                        else:
                            logger.debug(f"Strategy did not trigger for {symbol}")
                    
                    except Exception as e:
                        logger.error(f"Strategy execution failed for {symbol}: {str(e)}")
                    
                # 다음 실행까지 대기
                logger.info(f"Waiting {loop_interval} seconds until next execution...")
                time_module.sleep(loop_interval)
                
                logger.info("=== Strategy execution loop completed ===")
                
        except Exception as e:
            logger.error(f"Strategy execution loop failed: {str(e)}")
        finally:
            if acquired:
                try:
                    self._strategy_lock.release()
                except Exception:
                    pass
            if release_proc:
                try:
                    release_proc()
                except Exception:
                    pass
    
    def update_asset_prices(self):
        """가격 업데이트"""
        try:
            logger.info("=== Starting asset price update ===")
            
            # 1. 활성 자산 목록 조회 (지정된 계좌만 또는 모든 계좌)
            if settings.account_id:
                logger.info(f"Fetching assets from account: {settings.account_id}")
                assets_response = asset_api.list_assets(account_id=settings.account_id, size=100)
            else:
                logger.info("Fetching assets from all accounts")
                assets_response = asset_api.list_assets(size=100)
            
            assets = assets_response.get("items", [])
            
            # 거래 가능한 자산만 필터링
            tradable_assets = [
                a for a in assets 
                if a.get("asset_type") not in ["cash", "savings", "deposit"] 
                and a.get("symbol")
            ]
            
            logger.info(f"Updating prices for {len(tradable_assets)} tradable assets")
            
            # 2. symbol별로 그룹화 및 심볼 리스트 생성
            symbol_to_assets = {}
            symbols = []
            for asset in tradable_assets:
                symbol = asset.get("symbol")
                if symbol not in symbol_to_assets:
                    symbol_to_assets[symbol] = []
                    symbols.append(symbol)
                symbol_to_assets[symbol].append(asset)
            
            # 3. 모든 심볼의 가격을 한 번에 조회
            try:
                logger.info(f"Fetching prices for {len(symbols)} symbols: {symbols}")
                price_data_dict = self.broker.get_current_price(symbols)
                
                # 각 심볼별로 업데이트
                for symbol, assets_group in symbol_to_assets.items():
                    try:
                        price_data = price_data_dict.get(symbol)
                        
                        if price_data and price_data.current_price > 0:
                            result = asset_api.update_asset_price(
                                asset_id=assets_group[0]["id"],
                                price=price_data.current_price,
                                change=price_data.change_percent,
                                use_symbol=True
                            )
                            logger.info(f"Updated price for {symbol}: {price_data.current_price}")
                        else:
                            logger.warning(f"Invalid price for {symbol}")
                    
                    except Exception as e:
                        logger.error(f"Failed to update price for {symbol}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Failed to fetch prices for symbols {symbols}: {str(e)}")
            
            logger.info("=== Asset price update completed ===")
            
        except Exception as e:
            logger.error(f"Asset price update failed: {str(e)}")


def main():
    """메인 함수"""
    logger.info("Starting daemon service")
    logger.info(f"Configuration:")
    logger.info(f"  API Base URL: {settings.api_base_url}")
    logger.info(f"  Broker: {settings.broker}")
    logger.info(f"  Schedule Balance Cron: {settings.schedule_balance_cron}")
    logger.info(f"  Schedule Strategy Cron: {settings.schedule_strategy_cron}")
    logger.info(f"  Schedule Price Update Cron: {settings.schedule_price_update_cron}")
    
    daemon = DaemonScheduler()
    daemon.start()


if __name__ == "__main__":
    main()
