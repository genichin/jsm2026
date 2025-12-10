"""
브로커 팩토리 및 유틸리티
"""

from typing import Dict
from .base import BrokerConnector
from .demo import DemoBrokerConnector
from .upbit import UpbitConnector
import logging

logger = logging.getLogger(__name__)


class BrokerFactory:
    """브로커 커넥터 팩토리"""
    
    _connectors: Dict[str, type] = {
        "demo": DemoBrokerConnector,
        "upbit": UpbitConnector,
    }
    
    @classmethod
    def create(cls, broker_type: str, **kwargs) -> BrokerConnector:
        """
        브로커 커넥터 생성
        
        Args:
            broker_type: 브로커 타입 (demo, upbit 등)
            **kwargs: 브로커별 초기화 파라미터
        
        Returns:
            BrokerConnector: 해당 타입의 브로커 커넥터 인스턴스
        
        Raises:
            ValueError: 지원하지 않는 브로커 타입
        """
        if broker_type not in cls._connectors:
            raise ValueError(
                f"Unknown broker type: {broker_type}. "
                f"Supported types: {', '.join(cls._connectors.keys())}"
            )
        
        connector_class = cls._connectors[broker_type]
        logger.info(f"Creating {broker_type} broker connector")
        
        try:
            return connector_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create {broker_type} connector: {str(e)}")
            raise
    
    @classmethod
    def register(cls, broker_type: str, connector_class: type):
        """
        새로운 브로커 커넥터 등록
        
        Args:
            broker_type: 브로커 타입
            connector_class: BrokerConnector를 상속한 클래스
        """
        if not issubclass(connector_class, BrokerConnector):
            raise TypeError(f"{connector_class} must inherit from BrokerConnector")
        
        cls._connectors[broker_type] = connector_class
        logger.info(f"Registered broker type: {broker_type}")
    
    @classmethod
    def list_supported(cls) -> list:
        """지원하는 브로커 타입 목록"""
        return list(cls._connectors.keys())


def get_broker_connector(broker_type: str = "demo", **kwargs) -> BrokerConnector:
    """
    편의 함수: 브로커 커넥터 생성
    
    Args:
        broker_type: 브로커 타입 (기본값: demo)
        **kwargs: 브로커별 초기화 파라미터
    
    Returns:
        BrokerConnector: 해당 타입의 브로커 커넥터
    """
    return BrokerFactory.create(broker_type, **kwargs)
