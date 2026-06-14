"""
MetricsCollector：实时指标（V3.2）

V3.2 收集：
    PnL        当日盈亏（绝对）
    Drawdown   当前回撤（负数或 0）
    Exposure   持仓市场价值 / 净值
    WinRate    已平仓胜率 [0, 1]
    Latency    下单到成交的毫秒数
    Trades     累计成交数
    Rejects    累计拒单数

记录两个时序：
    latest (dict)        最新一个值
    history (DataFrame)  全时序（用于 dashboard 画图）
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class Trade:
    """内部用的最简 Trade 记录，用于算 WinRate"""
    symbol: str
    pnl: float
    timestamp: object


class MetricsCollector:
    """
    V3.2 实时指标收集器

    用法：
        m = MetricsCollector(initial_equity=100000)
        m.update(pnl=120)
        m.update(drawdown=-0.02)
        m.update(exposure=0.6)
        m.record_trade(pnl=120, symbol="AAPL")
        m.record_trade(pnl=-50, symbol="MSFT")
        print(m.snapshot())
        print(m.win_rate)        # 0.5
        print(m.max_drawdown)    # 0.02
    """

    def __init__(self, initial_equity: float = 0.0):
        self.initial_equity = initial_equity
        self.peak_equity = initial_equity

        # 最新值
        self.pnl: float = 0.0
        self.drawdown: float = 0.0
        self.exposure: float = 0.0
        self.equity: float = initial_equity
        self.trade_count: int = 0
        self.reject_count: int = 0
        self._latency_samples: List[float] = []

        # Trades
        self._trades: List[Trade] = []

        # History（用于 dashboard / time-series 分析）
        self._history: List[Dict] = []

    # ---- 通用 update ----
    def update(self, **kwargs) -> None:
        """
        V3.2 标准 update 接口

        支持字段：
            pnl, drawdown, exposure, equity
            latency (ms)
            trade / reject 计数 +1 用 update_trade() / update_reject()
        """
        for k, v in kwargs.items():
            if k in ("pnl", "drawdown", "exposure", "equity"):
                setattr(self, k, float(v))
            elif k == "latency":
                self._latency_samples.append(float(v))
        # 自动算 drawdown
        if "equity" in kwargs and self.equity > 0:
            if self.equity > self.peak_equity:
                self.peak_equity = self.equity
            self.drawdown = (
                (self.equity - self.peak_equity) / self.peak_equity
                if self.peak_equity > 0
                else 0.0
            )

    def update_trade(self, pnl: float = 0.0, **kw) -> None:
        self.trade_count += 1
        t = Trade(
            symbol=kw.get("symbol", ""),
            pnl=pnl,
            timestamp=kw.get("timestamp"),
        )
        self._trades.append(t)

    def update_reject(self) -> None:
        self.reject_count += 1

    def record_trade(
        self,
        pnl: float,
        symbol: str = "",
        timestamp: object = None,
    ) -> None:
        """V3.2 简洁：直接记 trade"""
        self.update_trade(pnl=pnl, symbol=symbol, timestamp=timestamp)

    def record_latency(self, ms: float) -> None:
        """V3.2：下单到成交耗时（毫秒）"""
        self._latency_samples.append(ms)
        # 保留最近 1000 个
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]

    # ---- 计算派生指标 ----
    @property
    def win_rate(self) -> float:
        if not self._trades:
            return 0.0
        wins = sum(1 for t in self._trades if t.pnl > 0)
        return wins / len(self._trades)

    @property
    def max_drawdown(self) -> float:
        return self.drawdown   # 实时法：当前 drawdown

    @property
    def avg_latency_ms(self) -> float:
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)

    # ---- 快照 / 时序 ----
    def snapshot(self) -> Dict:
        return {
            "pnl": self.pnl,
            "equity": self.equity,
            "drawdown": self.drawdown,
            "exposure": self.exposure,
            "trade_count": self.trade_count,
            "reject_count": self.reject_count,
            "win_rate": self.win_rate,
            "avg_latency_ms": self.avg_latency_ms,
        }

    def record(
        self,
        timestamp: object = None,
        **kwargs,
    ) -> None:
        """记一帧到 history"""
        snap = self.snapshot()
        snap.update(kwargs)
        snap["ts"] = timestamp
        self._history.append(snap)

    def history_df(self) -> pd.DataFrame:
        if not self._history:
            return pd.DataFrame()
        return pd.DataFrame(self._history).set_index("ts")
