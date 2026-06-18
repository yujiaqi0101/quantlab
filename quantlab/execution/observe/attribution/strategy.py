"""
Strategy Attribution — 策略归因

回答：这 12% 是谁赚出来的？

统计每个策略的：
  - 收益贡献（PnL Contribution）
  - 成交贡献（Trade Count）
  - 风险贡献（Risk Contribution，基于波动率）
  - 胜率贡献

输出示例：
    Strategy           PnL       PnL%    Trades  WinRate  RiskContrib
    BTC_Momentum      +4500      62%      120     58%      55%
    LGBM_Trend        +2000      28%       80     52%      25%
    Portfolio          +500       7%       30     60%      10%
    Others             +200       3%       15     55%      10%

用法：
    attr = StrategyAttribution(store)
    report = attr.analyze(session_id="s1")
    report = attr.analyze_range(start_ts=..., end_ts=...)
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..event_store import EventStore, StoredEvent

logger = logging.getLogger("quantlab.execution.observe.attribution.strategy")


@dataclass
class StrategyMetric:
    """单策略指标"""
    strategy: str = ""
    # PnL
    pnl: float = 0.0
    pnl_pct: float = 0.0  # 占总 PnL 的百分比
    # 交易
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    win_rate: float = 0.0
    # 金额
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    # 风险（基于 PnL 序列的标准差）
    pnl_std: float = 0.0
    risk_pct: float = 0.0  # 风险贡献百分比
    # 平均
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    # 最大单笔
    max_win: float = 0.0
    max_loss: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "win_rate": round(self.win_rate, 4),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "profit_factor": round(self.profit_factor, 4),
            "pnl_std": round(self.pnl_std, 2),
            "risk_pct": round(self.risk_pct, 2),
            "avg_pnl": round(self.avg_pnl, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "max_win": round(self.max_win, 2),
            "max_loss": round(self.max_loss, 2),
        }


@dataclass
class StrategyAttributionReport:
    """策略归因报告"""
    # 时间范围
    start_ts: int = 0
    end_ts: int = 0
    # 总体
    total_pnl: float = 0.0
    total_trades: int = 0
    overall_win_rate: float = 0.0
    # 各策略
    strategies: List[StrategyMetric] = field(default_factory=list)
    # 摘要
    best_strategy: str = ""
    worst_strategy: str = ""
    # 集中度（赫芬达尔指数，越高越集中）
    concentration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "overall_win_rate": round(self.overall_win_rate, 4),
            "strategies": [s.to_dict() for s in self.strategies],
            "best_strategy": self.best_strategy,
            "worst_strategy": self.worst_strategy,
            "concentration": round(self.concentration, 4),
        }


class StrategyAttribution:
    """
    策略归因分析

    用法：
        attr = StrategyAttribution(store)
        report = attr.analyze(session_id="s1")
        report = attr.analyze_range(start_ts=..., end_ts=...)
    """

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def analyze(self, session_id: str) -> StrategyAttributionReport:
        """分析整个会话的策略归因"""
        events = self.store.query(session_id=session_id, limit=100000)
        return self._build(events)

    def analyze_range(
        self,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str] = None,
    ) -> StrategyAttributionReport:
        """分析时间范围内的策略归因"""
        events = self.store.query(
            session_id=session_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=100000,
        )
        return self._build(events)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _build(self, events: List[StoredEvent]) -> StrategyAttributionReport:
        """构建报告"""
        report = StrategyAttributionReport()

        if not events:
            return report

        report.start_ts = events[0].timestamp
        report.end_ts = events[-1].timestamp

        # 按 trace_id 分组（每个 trace 是一笔交易）
        traces: Dict[str, List[StoredEvent]] = defaultdict(list)
        for e in events:
            tid = e.trace_id or e.event_id
            traces[tid].append(e)

        # 提取每笔交易的 PnL 和策略
        # trade_records: List[(strategy, pnl)]
        trade_records: List[Tuple[str, float]] = []
        for tid, evs in traces.items():
            pnl, strategy = self._extract_trade_pnl(evs)
            if pnl is not None:
                trade_records.append((strategy, pnl))

        if not trade_records:
            return report

        # 按策略聚合
        strategy_pnls: Dict[str, List[float]] = defaultdict(list)
        for strategy, pnl in trade_records:
            strategy_pnls[strategy].append(pnl)

        # 计算每个策略的指标
        total_pnl = sum(p for _, p in trade_records)
        report.total_pnl = total_pnl
        report.total_trades = len(trade_records)

        # 总体胜率
        wins = sum(1 for _, p in trade_records if p > 0)
        report.overall_win_rate = wins / len(trade_records) if trade_records else 0

        # 计算风险（PnL 标准差）总和
        total_std = 0.0
        strategy_stds: Dict[str, float] = {}
        for strategy, pnls in strategy_pnls.items():
            std = self._std(pnls)
            strategy_stds[strategy] = std
            total_std += std

        # 构建策略指标
        for strategy, pnls in strategy_pnls.items():
            m = StrategyMetric(strategy=strategy)
            m.pnl = sum(pnls)
            m.pnl_pct = (m.pnl / total_pnl * 100) if total_pnl != 0 else 0
            m.n_trades = len(pnls)
            m.n_wins = sum(1 for p in pnls if p > 0)
            m.n_losses = sum(1 for p in pnls if p < 0)
            m.win_rate = m.n_wins / m.n_trades if m.n_trades else 0
            m.gross_profit = sum(p for p in pnls if p > 0)
            m.gross_loss = abs(sum(p for p in pnls if p < 0))
            m.profit_factor = m.gross_profit / m.gross_loss if m.gross_loss > 0 else float('inf')
            m.pnl_std = strategy_stds[strategy]
            m.risk_pct = (strategy_stds[strategy] / total_std * 100) if total_std > 0 else 0
            m.avg_pnl = m.pnl / m.n_trades if m.n_trades else 0
            wins_list = [p for p in pnls if p > 0]
            losses_list = [p for p in pnls if p < 0]
            m.avg_win = sum(wins_list) / len(wins_list) if wins_list else 0
            m.avg_loss = sum(losses_list) / len(losses_list) if losses_list else 0
            m.max_win = max(pnls) if pnls else 0
            m.max_loss = min(pnls) if pnls else 0
            report.strategies.append(m)

        # 按 PnL 降序
        report.strategies.sort(key=lambda s: s.pnl, reverse=True)

        # 最佳/最差策略
        if report.strategies:
            report.best_strategy = report.strategies[0].strategy
            report.worst_strategy = report.strategies[-1].strategy

        # 集中度（赫芬达尔指数）
        if total_pnl > 0:
            shares = [(s.pnl / total_pnl) ** 2 for s in report.strategies if s.pnl > 0]
            report.concentration = sum(shares)

        return report

    def _extract_trade_pnl(
        self,
        events: List[StoredEvent],
    ) -> Tuple[Optional[float], str]:
        """
        从事件列表提取一笔交易的 PnL 和策略

        策略来源优先级：
          1. SIGNAL 事件的 payload.strategy
          2. SIGNAL 事件的 source
          3. 会话的 strategy
        """
        events = sorted(events, key=lambda e: e.timestamp)

        # 找 PnL（FILL 事件中）
        pnl = None
        for e in events:
            if e.event_type.upper() == "FILL":
                p = e.payload.get("pnl")
                if p is not None:
                    pnl = float(p)
                    break

        # 如果没有显式 pnl，尝试从入场/出场计算
        if pnl is None:
            fills = [e for e in events if e.event_type.upper() == "FILL"]
            if len(fills) >= 2:
                entry = fills[0]
                exit = fills[-1]
                entry_price = float(entry.payload.get("price", 0))
                exit_price = float(exit.payload.get("price", 0))
                qty = float(entry.payload.get("qty", 0))
                entry_side = entry.payload.get("side", "").upper()
                if entry_price and exit_price and qty:
                    if entry_side == "BUY":
                        pnl = (exit_price - entry_price) * qty
                    else:
                        pnl = (entry_price - exit_price) * qty

        # 找策略
        strategy = "unknown"
        for e in events:
            if e.event_type.upper() == "SIGNAL":
                strategy = e.payload.get("strategy", e.source or "unknown")
                break
        if strategy == "unknown":
            # 从 session 获取
            for e in events:
                if e.session_id:
                    session = self.store.get_session(e.session_id)
                    if session and session.strategy:
                        strategy = session.strategy
                    break

        return pnl, strategy

    def _std(self, values: List[float]) -> float:
        """标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(var)
