"""
Market Data Service — 统一行情服务

整个交易系统的地基。Backtest / Paper / Live 三模式全部调用同一套接口。

模块：
  - service     统一 Service + Provider 抽象
  - cache       行情缓存（后续可独立扩展）
  - websocket   WS 推送抽象
  - snapshot    快照
"""

from .service import (
    Bar,
    Snapshot,
    MarketDataProvider,
    BacktestProvider,
    MarketDataService,
    get_market_data_service,
    set_market_data_service,
)


__all__ = [
    "Bar",
    "Snapshot",
    "MarketDataProvider",
    "BacktestProvider",
    "MarketDataService",
    "get_market_data_service",
    "set_market_data_service",
]
