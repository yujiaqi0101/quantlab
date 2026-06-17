"""
Alpha Realizability Engine — Alpha 可实现性评估

核心问题变了：
  从：预测收益
  变成：这个收益在真实交易约束下是否成立？

评估一个 alpha，不再只是 IC / Sharpe
而是：是否可交易（Tradability）

核心评分：
  real_score = signal_strength × liquidity_score × turnover_penalty × cost_adjusted_return

举例：
  纸面很好：IC=0.08, Sharpe=2.0
  但真实环境：成交太慢、滑点太大、换手太高
  最终：real_score < 0
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.alpha_aware.realizability")


@dataclass
class AlphaMetrics:
    """Alpha 基础指标（纸面）"""
    ic: float = 0.0                # Information Coefficient
    ic_ir: float = 0.0             # IC 信息比
    sharpe: float = 0.0            # 夏普
    sortino: float = 0.0           # 索提诺
    max_drawdown: float = 0.0      # 最大回撤
    win_rate: float = 0.0          # 胜率
    avg_return: float = 0.0        # 平均收益
    turnover: float = 0.0          # 换手率
    holding_period: float = 0.0    # 持仓周期（天）

    def to_dict(self) -> Dict:
        return {
            "ic": self.ic,
            "ic_ir": self.ic_ir,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "avg_return": self.avg_return,
            "turnover": self.turnover,
            "holding_period": self.holding_period,
        }


@dataclass
class ExecutionConstraints:
    """执行约束"""
    avg_volume: float = 1_000_000      # 平均成交量
    avg_spread_bps: float = 2.0        # 平均价差
    avg_depth: float = 100.0           # 平均深度
    volatility: float = 0.02           # 波动率
    fee_rate: float = 0.0004           # 手续费率
    slippage_bps: float = 2.0          # 滑点
    max_participation: float = 0.1     # 最大参与率

    def to_dict(self) -> Dict:
        return {
            "avg_volume": self.avg_volume,
            "avg_spread_bps": self.avg_spread_bps,
            "avg_depth": self.avg_depth,
            "volatility": self.volatility,
            "fee_rate": self.fee_rate,
            "slippage_bps": self.slippage_bps,
            "max_participation": self.max_participation,
        }


@dataclass
class RealizabilityReport:
    """可实现性报告"""
    # 各维度评分（0~1）
    signal_strength: float = 0.0       # 信号强度
    liquidity_score: float = 0.0       # 流动性评分
    turnover_penalty: float = 0.0      # 换手惩罚（1=无惩罚，0=完全惩罚）
    cost_adjusted_return: float = 0.0  # 成本调整后收益

    # 综合
    real_score: float = 0.0            # 可实现性综合评分
    real_sharpe: float = 0.0           # 真实夏普
    is_tradable: bool = False          # 是否可交易

    # 拆解
    components: Dict = field(default_factory=dict)
    verdict: str = ""                  # 结论
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "signal_strength": self.signal_strength,
            "liquidity_score": self.liquidity_score,
            "turnover_penalty": self.turnover_penalty,
            "cost_adjusted_return": self.cost_adjusted_return,
            "real_score": self.real_score,
            "real_sharpe": self.real_sharpe,
            "is_tradable": self.is_tradable,
            "components": self.components,
            "verdict": self.verdict,
            "warnings": self.warnings,
        }


class AlphaRealizabilityEngine:
    """
    Alpha 可实现性评估引擎

    用法：
        engine = AlphaRealizabilityEngine()
        report = engine.evaluate(
            metrics=AlphaMetrics(ic=0.08, sharpe=2.0, turnover=5.0),
            constraints=ExecutionConstraints(avg_volume=500000, slippage_bps=5.0),
        )
        print(report.verdict)  # TRADABLE / MARGINAL / UNTRADABLE
    """

    def __init__(
        self,
        min_real_score: float = 0.3,
        min_ic: float = 0.02,
        max_turnover: float = 10.0,
    ) -> None:
        self.min_real_score = min_real_score
        self.min_ic = min_ic
        self.max_turnover = max_turnover

    def evaluate(
        self,
        metrics: AlphaMetrics,
        constraints: ExecutionConstraints,
    ) -> RealizabilityReport:
        """评估 Alpha 可实现性"""
        report = RealizabilityReport()

        # 1. 信号强度（基于 IC 和 IC_IR）
        report.signal_strength = self._signal_strength(metrics)
        report.components["signal_strength"] = report.signal_strength

        # 2. 流动性评分
        report.liquidity_score = self._liquidity_score(constraints)
        report.components["liquidity_score"] = report.liquidity_score

        # 3. 换手惩罚
        report.turnover_penalty = self._turnover_penalty(metrics.turnover)
        report.components["turnover_penalty"] = report.turnover_penalty

        # 4. 成本调整后收益
        report.cost_adjusted_return = self._cost_adjusted_return(metrics, constraints)
        report.components["cost_adjusted_return"] = report.cost_adjusted_return

        # 5. 综合评分
        report.real_score = (
            report.signal_strength
            * report.liquidity_score
            * report.turnover_penalty
            * max(0, report.cost_adjusted_return)
        )

        # 6. 真实夏普
        report.real_sharpe = self._real_sharpe(metrics, constraints)

        # 7. 可交易性
        report.is_tradable = (
            report.real_score >= self.min_real_score
            and metrics.ic >= self.min_ic
            and metrics.turnover <= self.max_turnover
        )

        # 8. 结论
        report.verdict = self._verdict(report)
        report.warnings = self._warnings(metrics, constraints, report)

        return report

    def _signal_strength(self, m: AlphaMetrics) -> float:
        """信号强度评分（0~1）"""
        # IC 映射：IC=0 → 0, IC=0.1 → 1
        ic_score = min(1.0, abs(m.ic) / 0.1)

        # IC_IR 映射
        ir_score = min(1.0, abs(m.ic_ir) / 2.0)

        # 综合
        return (ic_score * 0.6 + ir_score * 0.4)

    def _liquidity_score(self, c: ExecutionConstraints) -> float:
        """流动性评分（0~1）"""
        # 成交量评分
        vol_score = min(1.0, math.log10(max(1, c.avg_volume)) / 8)  # 1亿=1.0

        # 价差评分：spread 越小越好
        spread_score = max(0, 1 - c.avg_spread_bps / 20)

        # 深度评分
        depth_score = min(1.0, c.avg_depth / 1000)

        return (vol_score * 0.4 + spread_score * 0.3 + depth_score * 0.3)

    def _turnover_penalty(self, turnover: float) -> float:
        """换手惩罚（1=无惩罚，0=完全惩罚）"""
        # turnover=0 → 1, turnover=10 → 0.5, turnover=20 → 0
        if turnover <= 0:
            return 1.0
        return max(0.0, 1.0 - turnover / 20.0)

    def _cost_adjusted_return(self, m: AlphaMetrics, c: ExecutionConstraints) -> float:
        """成本调整后收益"""
        # 年化成本（简化）
        annual_cost = (
            m.turnover * (c.fee_rate + c.slippage_bps / 10000) * 252  # 252 交易日
        )

        # 调整后收益
        adjusted = m.avg_return - annual_cost

        # 归一化到 0~1（假设 avg_return 0.2 为满分）
        if m.avg_return <= 0:
            return 0.0
        return max(0, min(1.0, adjusted / 0.2))

    def _real_sharpe(self, m: AlphaMetrics, c: ExecutionConstraints) -> float:
        """真实夏普"""
        # 成本惩罚
        annual_cost_return = m.turnover * (c.fee_rate + c.slippage_bps / 10000) * 252
        cost_penalty = annual_cost_return / max(0.01, m.avg_return) * m.sharpe

        return m.sharpe - cost_penalty

    def _verdict(self, report: RealizabilityReport) -> str:
        if report.real_score >= 0.6 and report.real_sharpe >= 1.0:
            return "TRADABLE"
        elif report.real_score >= 0.3 and report.real_sharpe >= 0.5:
            return "MARGINAL"
        else:
            return "UNTRADABLE"

    def _warnings(
        self,
        m: AlphaMetrics,
        c: ExecutionConstraints,
        report: RealizabilityReport,
    ) -> List[str]:
        warnings = []
        if m.turnover > self.max_turnover:
            warnings.append(f"换手过高: {m.turnover:.1f} > {self.max_turnover}")
        if report.liquidity_score < 0.3:
            warnings.append(f"流动性不足: score={report.liquidity_score:.2f}")
        if report.cost_adjusted_return < 0:
            warnings.append("成本超过收益：策略在真实环境下亏损")
        if report.real_sharpe < 0:
            warnings.append(f"真实夏普为负: {report.real_sharpe:.2f}")
        if m.ic < self.min_ic:
            warnings.append(f"IC 过低: {m.ic:.4f} < {self.min_ic}")
        return warnings
