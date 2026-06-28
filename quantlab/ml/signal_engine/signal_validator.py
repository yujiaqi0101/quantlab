"""
模块 8: Signal Validator

验证 Signal（不是验证模型）。
指标：Hit Rate / Precision / Recall / Average Return / Turnover /
      Holding Days / IC / Rank IC / Win Rate。

输入是历史 Signal 列表 + 收益矩阵（symbol × datetime）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .signal import Signal, SignalDirection, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.validator")


@dataclass
class ValidationReport:
    """信号验证报告"""

    hit_rate: float = 0.0          # 方向命中率
    precision: float = 0.0         # 多头 Precision
    recall: float = 0.0
    avg_return: float = 0.0        # 平均收益
    turnover: float = 0.0          # 换手率
    avg_holding_days: float = 0.0
    ic: float = 0.0                # IC
    rank_ic: float = 0.0           # Rank IC
    win_rate: float = 0.0          # 胜率
    n_signals: int = 0
    period: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hit_rate": self.hit_rate,
            "precision": self.precision,
            "recall": self.recall,
            "avg_return": self.avg_return,
            "turnover": self.turnover,
            "avg_holding_days": self.avg_holding_days,
            "ic": self.ic,
            "rank_ic": self.rank_ic,
            "win_rate": self.win_rate,
            "n_signals": self.n_signals,
            "period": self.period,
            "details": self.details,
        }


class SignalValidator:
    """信号验证器"""

    def __init__(self, forward_periods: Optional[List[int]] = None) -> None:
        self.forward_periods = forward_periods or [1, 5, 10, 20]

    def validate(
        self,
        signals: List[Signal],
        returns: pd.DataFrame,
        benchmark: Optional[pd.Series] = None,
    ) -> ValidationReport:
        """
        验证信号列表。

        Args:
            signals: 历史 Signal 列表
            returns: symbol × datetime 收益矩阵 (columns=symbols, index=datetime)
            benchmark: 基准收益序列
        """
        if not signals:
            return ValidationReport()

        n = len(signals)
        hits = 0
        wins = 0
        returns_list: List[float] = []
        ic_values: List[float] = []
        rank_ic_values: List[float] = []

        for sig in signals:
            if sig.symbol not in returns.columns:
                continue
            series = returns[sig.symbol]
            # 找到信号 datetime 对应的下一期收益
            try:
                idx = series.index.get_loc(sig.datetime) if sig.datetime in series.index else None
            except (KeyError, TypeError):
                idx = None
            if idx is None or idx + 1 >= len(series):
                continue
            forward_ret = float(series.iloc[idx + 1])
            returns_list.append(forward_ret)

            # Hit Rate: 方向正确
            if sig.direction == SignalDirection.LONG and forward_ret > 0:
                hits += 1
            elif sig.direction == SignalDirection.SHORT and forward_ret < 0:
                hits += 1

            # Win Rate: 收益为正
            if forward_ret > 0:
                wins += 1

            # IC: 信号 score 与 forward_ret 的相关性
            ic_values.append((sig.score, forward_ret))
            rank_ic_values.append((sig.score, forward_ret))

        total_valid = len(returns_list) or 1

        # 计算 IC
        ic = self._compute_ic(ic_values)
        rank_ic = self._compute_rank_ic(rank_ic_values)

        # Turnover: 方向变化频率
        turnover = self._compute_turnover(signals)

        # 平均持仓
        avg_hold = float(np.mean([s.holding_period for s in signals])) if signals else 0.0

        return ValidationReport(
            hit_rate=hits / total_valid,
            precision=sum(1 for s, r in zip(signals, returns_list) if s.direction == SignalDirection.LONG and r > 0) / total_valid,
            recall=hits / total_valid,
            avg_return=float(np.mean(returns_list)) if returns_list else 0.0,
            turnover=turnover,
            avg_holding_days=avg_hold,
            ic=ic,
            rank_ic=rank_ic,
            win_rate=wins / total_valid,
            n_signals=n,
            period=f"forward_1",
            details={
                "forward_periods": self.forward_periods,
                "n_valid": len(returns_list),
                "benchmark": benchmark is not None,
            },
        )

    def validate_signal_set(
        self,
        signal_set: SignalSet,
        returns: pd.DataFrame,
        benchmark: Optional[pd.Series] = None,
    ) -> ValidationReport:
        return self.validate(signal_set.signals, returns, benchmark)

    @staticmethod
    def _compute_ic(pairs: List[tuple]) -> float:
        if len(pairs) < 2:
            return 0.0
        scores = np.array([p[0] for p in pairs])
        rets = np.array([p[1] for p in pairs])
        if np.std(scores) < 1e-8 or np.std(rets) < 1e-8:
            return 0.0
        return float(np.corrcoef(scores, rets)[0, 1])

    @staticmethod
    def _compute_rank_ic(pairs: List[tuple]) -> float:
        if len(pairs) < 2:
            return 0.0
        scores = np.array([p[0] for p in pairs])
        rets = np.array([p[1] for p in pairs])
        if np.std(scores) < 1e-8 or np.std(rets) < 1e-8:
            return 0.0
        # Spearman rank correlation
        from scipy.stats import spearmanr
        try:
            r, _ = spearmanr(scores, rets)
            return float(r) if not np.isnan(r) else 0.0
        except Exception:
            # 退化: 手动 rank
            rank_s = np.argsort(np.argsort(scores)).astype(float)
            rank_r = np.argsort(np.argsort(rets)).astype(float)
            if np.std(rank_s) < 1e-8 or np.std(rank_r) < 1e-8:
                return 0.0
            return float(np.corrcoef(rank_s, rank_r)[0, 1])

    @staticmethod
    def _compute_turnover(signals: List[Signal]) -> float:
        """方向变化频率"""
        if len(signals) < 2:
            return 0.0
        changes = 0
        for i in range(1, len(signals)):
            if signals[i].direction != signals[i - 1].direction:
                changes += 1
        return changes / (len(signals) - 1)
