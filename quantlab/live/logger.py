"""
V3.2：re-export 兼容 V2.5 LiveLogger

实际定义已迁移到 monitoring/logger.py:TradeLogger
V2.5 接口（order/trade/reject/error）保持完全一致
"""
from ..monitoring.logger import (
    TradeLogger,
    LogRecord,
    new_trace_id,
)


# LiveLogger 是 V2.5 名字；V3.2 改名 TradeLogger
# 这里起一个别名让旧 import 不断
LiveLogger = TradeLogger


__all__ = [
    "TradeLogger",
    "LiveLogger",   # V2.5 兼容名
    "LogRecord",
    "new_trace_id",
]
