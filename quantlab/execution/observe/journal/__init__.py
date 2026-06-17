"""
Trade Journal — 交易日志

人为解释层：记录每笔交易的"为什么"
不仅是数据，更是决策记录
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.observe.journal")


class JournalEntryType(str, Enum):
    SIGNAL = "SIGNAL"               # 策略信号
    ORDER = "ORDER"                  # 下单
    FILL = "FILL"                    # 成交
    RISK_ALERT = "RISK_ALERT"        # 风险告警
    KILL_SWITCH = "KILL_SWITCH"      # 熔断
    RECOVERY = "RECOVERY"            # 恢复
    MANUAL = "MANUAL"                # 人工干预
    SYSTEM = "SYSTEM"                # 系统事件


@dataclass
class JournalEntry:
    """日志条目"""
    type: JournalEntryType
    message: str
    timestamp: int = 0
    strategy_id: str = ""
    symbol: str = ""
    order_id: str = ""
    signal_id: str = ""
    data: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> Dict:
        return asdict(self)


class TradeJournal:
    """
    交易日志

    用法：
        journal = TradeJournal(persist_path="storage/journal.jsonl")
        journal.log_signal("s1", "BTCUSDT", "BUY signal: RSI < 30", data={...})
        journal.log_order("s1", "BTCUSDT", "order_123", "Order submitted")
        journal.log_fill("s1", "BTCUSDT", "order_123", "Filled 0.5 @ 50000")
        journal.query(symbol="BTCUSDT", limit=100)
    """

    def __init__(self, persist_path: str = "storage/journal.jsonl") -> None:
        self._path = persist_path
        self._entries: List[JournalEntry] = []
        self._max_memory: int = 50000
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def log(self, entry: JournalEntry) -> None:
        """记录日志条目"""
        self._entries.append(entry)
        if len(self._entries) > self._max_memory:
            self._entries = self._entries[-self._max_memory:]

        # 持久化
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Journal persist error: {e}")

    def log_signal(
        self,
        strategy_id: str,
        symbol: str,
        message: str,
        signal_id: str = "",
        data: Dict = None,
        tags: List[str] = None,
    ) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.SIGNAL,
            message=message,
            strategy_id=strategy_id,
            symbol=symbol,
            signal_id=signal_id,
            data=data or {},
            tags=tags or [],
        ))

    def log_order(
        self,
        strategy_id: str,
        symbol: str,
        order_id: str,
        message: str,
        data: Dict = None,
    ) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.ORDER,
            message=message,
            strategy_id=strategy_id,
            symbol=symbol,
            order_id=order_id,
            data=data or {},
        ))

    def log_fill(
        self,
        strategy_id: str,
        symbol: str,
        order_id: str,
        message: str,
        data: Dict = None,
    ) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.FILL,
            message=message,
            strategy_id=strategy_id,
            symbol=symbol,
            order_id=order_id,
            data=data or {},
        ))

    def log_risk_alert(self, message: str, data: Dict = None) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.RISK_ALERT,
            message=message,
            data=data or {},
        ))

    def log_kill_switch(self, message: str, data: Dict = None) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.KILL_SWITCH,
            message=message,
            data=data or {},
        ))

    def log_recovery(self, message: str, data: Dict = None) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.RECOVERY,
            message=message,
            data=data or {},
        ))

    def log_system(self, message: str, data: Dict = None) -> None:
        self.log(JournalEntry(
            type=JournalEntryType.SYSTEM,
            message=message,
            data=data or {},
        ))

    def query(
        self,
        type: Optional[JournalEntryType] = None,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        limit: int = 100,
    ) -> List[JournalEntry]:
        """查询日志"""
        results = []
        for entry in reversed(self._entries):
            if type and entry.type != type:
                continue
            if strategy_id and entry.strategy_id != strategy_id:
                continue
            if symbol and entry.symbol != symbol:
                continue
            if order_id and entry.order_id != order_id:
                continue
            if start_ts and entry.timestamp < start_ts:
                continue
            if end_ts and entry.timestamp > end_ts:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def to_dict_list(self, entries: List[JournalEntry]) -> List[Dict]:
        return [e.to_dict() for e in entries]
