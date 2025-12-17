"""
daemon 메인 스케줄러 및 태스크
"""

import logging
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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
        self.scheduler = BackgroundScheduler()
        logger.info(f"Broker config: type={settings.broker}, key_len={len(settings.broker_app_key or '')}, secret_len={len(settings.broker_app_secret or '')}, account_id={settings.account_id}")
        self.broker = get_broker_connector(
            broker_type=settings.broker,
            access_key=settings.broker_app_key,
            secret_key=settings.broker_app_secret,
            account_id=settings.account_id
        )
        self.strategy_runner = StrategyRunner(self.broker)
    
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
                replace_existing=True
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
                replace_existing=True
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
                replace_existing=True
            )
            logger.info(f"Added job: price_updater with cron '{settings.schedule_price_update_cron}'")
        else:
            logger.info("Skipped job: price_updater (SCHEDULE_PRICE_UPDATE_CRON not configured)")
    
    def start(self):
        """스케줄러 시작"""
        self.setup_jobs()
        self.scheduler.start()
        logger.info("Daemon scheduler started")
        
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
        """전략 실행"""
        try:
            logger.info("=== Starting strategy execution ===")
            
            # 1. 미체결 거래 취소
            pending_orders = self.broker.get_pending_orders()
            if pending_orders:
                logger.info(f"Found {len(pending_orders)} pending orders, cancelling...")
                for order in pending_orders:
                    self.broker.cancel_order(order.order_id)
                    logger.info(f"Cancelled order: {order.order_id}")
            
            # 2. 브로커에서 최신 잔고 조회
            broker_balance = self.broker.get_balance()
            
            # 3. 백엔드에서 자산 설정 조회
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
                
                # 전략 설정 생성
                strategy_config = StrategyConfig(
                    strategy_type=strategy_type,
                    asset_id=asset_id,
                    symbol=symbol,
                    config=strategy.get("config", {})
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

                        #print(kwargs)
                    
                    # 전략 실행
                    result = self.strategy_runner.execute_strategy(strategy_config, **kwargs)
                    
                    if result:
                        logger.info(f"Strategy executed successfully for {symbol}")
                    else:
                        logger.debug(f"Strategy did not trigger for {symbol}")
                
                except Exception as e:
                    logger.error(f"Strategy execution failed for {symbol}: {str(e)}")
            
            logger.info("=== Strategy execution completed ===")
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
    
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
