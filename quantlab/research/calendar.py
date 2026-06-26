"""
CalendarRegistry — 交易日历注册表

内置日历:
  - crypto: 7x24 全天候
  - a_share: A股 (周一至周五 09:30-11:30, 13:00-15:00)
  - nyse: 纽约证券交易所
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class CalendarDefinition:
    id: str
    sessions: List = field(default_factory=list)  # [(start_time, end_time), ...]
    tz: str = "UTC"
    holidays: List[str] = field(default_factory=list)  # ["2024-01-01", ...]

    def generate_dates(self, start: str, end: str, freq: str = "D") -> pd.DatetimeIndex:
        """生成日期范围。"""
        dates = pd.date_range(start, end, freq=freq, tz=self.tz)
        # 过滤节假日 (对齐 tz)
        if self.holidays:
            holidays = pd.to_datetime(self.holidays)
            if dates.tz is not None:
                holidays = holidays.tz_localize(dates.tz)
            mask = dates.normalize().isin(holidays.normalize())
            dates = dates[~mask]
        return dates


class CalendarRegistry:
    """交易日历注册表。"""

    def __init__(self) -> None:
        self._store: dict = {}
        self._lock = threading.RLock()

    def register(self, cal: CalendarDefinition) -> "CalendarRegistry":
        with self._lock:
            self._store[cal.id] = cal
        return self

    def get(self, cal_id: str) -> Optional[CalendarDefinition]:
        with self._lock:
            return self._store.get(cal_id)

    def list(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())


_calendar_registry: Optional[CalendarRegistry] = None


def get_calendar_registry() -> CalendarRegistry:
    """全局 CalendarRegistry。"""
    global _calendar_registry
    if _calendar_registry is None:
        _calendar_registry = CalendarRegistry()
        # 内置日历
        _calendar_registry.register(
            CalendarDefinition(
                id="crypto",
                sessions=[("00:00", "23:59")],
                tz="UTC",
            )
        )
        _calendar_registry.register(
            CalendarDefinition(
                id="a_share",
                sessions=[("09:30", "11:30"), ("13:00", "15:00")],
                tz="Asia/Shanghai",
            )
        )
        _calendar_registry.register(
            CalendarDefinition(
                id="nyse",
                sessions=[("09:30", "16:00")],
                tz="America/New_York",
            )
        )
    return _calendar_registry


__all__ = [
    "CalendarDefinition",
    "CalendarRegistry",
    "get_calendar_registry",
]
