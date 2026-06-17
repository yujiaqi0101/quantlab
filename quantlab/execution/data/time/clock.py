"""
统一时间引擎 — Exchange Time 为唯一时间源

核心原则：
  所有系统事件必须基于 exchange timestamp
  避免本地时钟漂移导致未来函数错误

用法：
  from quantlab.execution.data.time.clock import ExchangeClock

  clock = ExchangeClock()
  clock.sync(server_time_ms=1700000000000)
  now = clock.now()       # exchange time
  ts = clock.timestamp()  # unix ms
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("quantlab.execution.data.time")


@dataclass
class ExchangeClock:
    """
    统一时钟 — 以交易所时间为准

    offset = server_time - local_time
    now() = time.time() + offset
    """
    offset_seconds: float = 0.0
    last_sync: float = 0.0
    sync_interval: float = 30.0  # 每 30 秒重新同步
    _max_drift: float = 5.0      # 最大允许漂移 5 秒

    def sync(self, server_time_ms: int) -> None:
        """用交易所返回的时间戳同步本地时钟"""
        server_ts = server_time_ms / 1000.0
        local_ts = time.time()
        new_offset = server_ts - local_ts

        # 漂移过大告警
        drift = abs(new_offset - self.offset_seconds)
        if drift > self._max_drift:
            logger.warning(
                f"ExchangeClock drift detected: {drift:.3f}s "
                f"(old_offset={self.offset_seconds:.3f}, "
                f"new_offset={new_offset:.3f})"
            )

        self.offset_seconds = new_offset
        self.last_sync = local_ts
        logger.debug(
            f"ExchangeClock synced: offset={self.offset_seconds:.3f}s"
        )

    def now(self) -> float:
        """返回当前 exchange time (unix seconds)"""
        return time.time() + self.offset_seconds

    def timestamp(self) -> int:
        """返回当前 exchange time (unix milliseconds)"""
        return int(self.now() * 1000)

    def needs_sync(self) -> bool:
        """是否需要重新同步"""
        return (time.time() - self.last_sync) > self.sync_interval

    def to_iso(self) -> str:
        """返回 ISO 格式时间字符串"""
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(self.now(), tz=timezone.utc)
        return dt.isoformat()


# 全局单例
_global_clock: Optional[ExchangeClock] = None


def get_clock() -> ExchangeClock:
    global _global_clock
    if _global_clock is None:
        _global_clock = ExchangeClock()
    return _global_clock
