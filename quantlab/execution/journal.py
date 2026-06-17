"""
Trading Journal — 交易日志

记录：
  - 今天为什么开仓
  - 为什么停策略
  - 参数为什么修改
  - 市场观察
  - 复盘思考

几年后价值巨大。

用法：
    from quantlab.execution.journal import TradingJournal, JournalEntry

    journal = TradingJournal(store_dir="./journal")

    # 开仓记录
    journal.log_open(
        symbol="BTCUSDT",
        qty=0.5,
        price=50000,
        reason="RSI<30 + 趋势线支撑",
        strategy="rsi_reversal",
    )

    # 平仓记录
    journal.log_close(
        symbol="BTCUSDT",
        qty=0.5,
        price=51000,
        pnl=500,
        reason="止盈",
        strategy="rsi_reversal",
    )

    # 复盘
    journal.log_reflection(
        title="2024-01-15 复盘",
        content="今天 RSI 策略表现良好，但止损太紧...",
    )

    # 查询
    entries = journal.list_entries(category="open")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.journal")


# ------------------------------------------------------------------
# JournalCategory
# ------------------------------------------------------------------

class JournalCategory(str, Enum):
    OPEN = "open"              # 开仓
    CLOSE = "close"            # 平仓
    RISK = "risk"              # 风险事件
    STRATEGY = "strategy"      # 策略变更
    PARAM = "param"            # 参数修改
    REFLECTION = "reflection"  # 复盘
    OBSERVATION = "observation"  # 市场观察
    ERROR = "error"            # 错误
    OTHER = "other"


# ------------------------------------------------------------------
# JournalEntry
# ------------------------------------------------------------------

@dataclass
class JournalEntry:
    """日志条目"""
    entry_id: str
    timestamp: str
    category: str              # JournalCategory.value
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# TradingJournal
# ------------------------------------------------------------------

class TradingJournal:
    """
    交易日志

    存储为 JSONL 文件（每行一条），方便追加和检索。
    """

    def __init__(
        self,
        store_dir: str = "./journal",
        filename: str = "journal.jsonl",
    ) -> None:
        self.store_dir = store_dir
        self.filename = filename
        self.filepath = os.path.join(store_dir, filename)

        # 内存缓存（最近 N 条）
        self._entries: List[JournalEntry] = []
        self._max_cache = 1000

        # 确保目录存在
        os.makedirs(store_dir, exist_ok=True)

        # 加载历史
        self._load_history()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def log(
        self,
        category: JournalCategory,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JournalEntry:
        """
        记录一条日志

        参数：
          category   分类
          title      标题
          content    内容
          metadata   额外数据（symbol/qty/price/pnl 等）
        """
        import uuid

        entry = JournalEntry(
            entry_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now().isoformat(),
            category=category.value,
            title=title,
            content=content,
            metadata=metadata or {},
        )

        # 写入文件
        self._append(entry)

        # 加入缓存
        self._entries.append(entry)
        if len(self._entries) > self._max_cache:
            self._entries = self._entries[-self._max_cache:]

        logger.info(
            f"Journal: [{category.value}] {title}"
        )
        return entry

    # 便捷方法
    def log_open(
        self,
        symbol: str,
        qty: float,
        price: float,
        reason: str,
        strategy: str = "",
        **extra,
    ) -> JournalEntry:
        """记录开仓"""
        return self.log(
            category=JournalCategory.OPEN,
            title=f"OPEN {symbol} {qty}@{price}",
            content=reason,
            metadata={
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "strategy": strategy,
                **extra,
            },
        )

    def log_close(
        self,
        symbol: str,
        qty: float,
        price: float,
        pnl: float,
        reason: str,
        strategy: str = "",
        **extra,
    ) -> JournalEntry:
        """记录平仓"""
        return self.log(
            category=JournalCategory.CLOSE,
            title=f"CLOSE {symbol} {qty}@{price} pnl={pnl:.2f}",
            content=reason,
            metadata={
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "pnl": pnl,
                "strategy": strategy,
                **extra,
            },
        )

    def log_risk(
        self,
        event: str,
        details: str,
        **extra,
    ) -> JournalEntry:
        """记录风险事件"""
        return self.log(
            category=JournalCategory.RISK,
            title=f"RISK: {event}",
            content=details,
            metadata=extra,
        )

    def log_strategy(
        self,
        action: str,
        strategy: str,
        reason: str,
        **extra,
    ) -> JournalEntry:
        """记录策略变更（启动/停止/重启）"""
        return self.log(
            category=JournalCategory.STRATEGY,
            title=f"STRATEGY {action}: {strategy}",
            content=reason,
            metadata={"strategy": strategy, "action": action, **extra},
        )

    def log_param(
        self,
        strategy: str,
        param_name: str,
        old_value: Any,
        new_value: Any,
        reason: str,
    ) -> JournalEntry:
        """记录参数修改"""
        return self.log(
            category=JournalCategory.PARAM,
            title=f"PARAM {strategy}.{param_name}: {old_value} → {new_value}",
            content=reason,
            metadata={
                "strategy": strategy,
                "param": param_name,
                "old": old_value,
                "new": new_value,
            },
        )

    def log_reflection(
        self,
        title: str,
        content: str,
        **extra,
    ) -> JournalEntry:
        """记录复盘"""
        return self.log(
            category=JournalCategory.REFLECTION,
            title=title,
            content=content,
            metadata=extra,
        )

    def log_observation(
        self,
        title: str,
        content: str,
        **extra,
    ) -> JournalEntry:
        """记录市场观察"""
        return self.log(
            category=JournalCategory.OBSERVATION,
            title=title,
            content=content,
            metadata=extra,
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_entries(
        self,
        category: Optional[str] = None,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[JournalEntry]:
        """
        查询日志

        参数：
          category    分类
          strategy    策略名
          symbol      标的
          start_date  起始日期（YYYY-MM-DD）
          end_date    结束日期
          limit       返回条数
        """
        result = self._entries

        if category:
            result = [e for e in result if e.category == category]
        if strategy:
            result = [
                e for e in result
                if e.metadata.get("strategy") == strategy
            ]
        if symbol:
            result = [
                e for e in result
                if e.metadata.get("symbol") == symbol
            ]
        if start_date:
            result = [
                e for e in result
                if e.timestamp >= start_date
            ]
        if end_date:
            result = [
                e for e in result
                if e.timestamp <= end_date + "T23:59:59"
            ]

        return result[-limit:]

    def get(self, entry_id: str) -> Optional[JournalEntry]:
        """按 ID 查询"""
        for e in self._entries:
            if e.entry_id == entry_id:
                return e
        return None

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """统计"""
        from collections import Counter

        by_category = Counter(e.category for e in self._entries)
        by_strategy = Counter(
            e.metadata.get("strategy", "")
            for e in self._entries
        )

        return {
            "total": len(self._entries),
            "by_category": dict(by_category),
            "by_strategy": dict(by_strategy),
            "filepath": self.filepath,
        }

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _append(self, entry: JournalEntry) -> None:
        """追加到文件"""
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Journal write failed: {e}")

    def _load_history(self) -> None:
        """加载历史日志"""
        if not os.path.exists(self.filepath):
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        entry = JournalEntry(**d)
                        self._entries.append(entry)
                    except Exception:
                        continue

            # 只保留最近 N 条在内存
            if len(self._entries) > self._max_cache:
                self._entries = self._entries[-self._max_cache:]

            logger.info(
                f"Journal: loaded {len(self._entries)} entries from {self.filepath}"
            )
        except Exception as e:
            logger.error(f"Journal load failed: {e}")


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_journal: Optional[TradingJournal] = None


def get_journal() -> TradingJournal:
    """获取全局 TradingJournal"""
    global _global_journal
    if _global_journal is None:
        _global_journal = TradingJournal()
    return _global_journal


def set_journal(journal: TradingJournal) -> None:
    global _global_journal
    _global_journal = journal
