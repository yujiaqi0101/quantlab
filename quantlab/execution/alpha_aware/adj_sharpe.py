"""
Execution-Adjusted Sharpe — 执行调整夏普

核心指标升级：
  Sharpe_real = Sharpe_paper - cost_penalty - slippage_penalty

输出：Paper Sharpe → Real Sharpe

这是机构内部真正看的指标。
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.alpha_aware.adj_sharpe")


@dataclass
class SharpeDecomposition:
    """夏普拆解"""
    paper_sharpe: float = 0.0
    fee_penalty: float = 0.0          # 手续费惩罚
    slippage_penalty: float = 0.0     # 滑点惩罚
    impact_penalty: float = 0.0       # 冲击惩罚
    opportunity_penalty: float = 0.0  # 机会成本惩罚
    funding_penalty: float = 0.0      # 资金费率惩罚

    @property
    def total_penalty(self) -> float:
        return (
            self.fee_penalty
            + self.slippage_penalty
            + self.impact_penalty
            + self.opportunity_penalty
            + self.funding_penalty
        )

    @property
    def real_sharpe(self) -> float:
        return self.paper_sharpe - self.total_penalty

    @property
    def decay_rate(self) -> float:
        """夏普衰减率"""
        if self.paper_sharpe <= 0:
            return 0.0
        return self.total_penalty / self.paper_sharpe

    def to_dict(self) -> Dict:
        return {
            "paper_sharpe": self.paper_sharpe,
            "fee_penalty": self.fee_penalty,
            "slippage_penalty": self.slippage_penalty,
            "impact_penalty": self.impact_penalty,
            "opportunity_penalty": self.opportunity_penalty,
            "funding_penalty": self.funding_penalty,
            "total_penalty": self.total_penalty,
            "real_sharpe": self.real_sharpe,
            "decay_rate": self.decay_rate,
        }


@dataclass
class AdjustedSharpeReport:
    """执行调整夏普报告"""
    decomposition: SharpeDecomposition = field(default_factory=SharpeDecomposition)

    # 评级
    grade: str = ""              # A / B / C / D / F
    is_institutional: bool = False  # 是否达到机构标准
    verdict: str = ""

    # 详细
    assumptions: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "decomposition": self.decomposition.to_dict(),
            "grade": self.grade,
            "is_institutional": self.is_institutional,
            "verdict": self.verdict,
            "assumptions": self.assumptions,
        }


class ExecutionAdjustedSharpe:
    """
    执行调整夏普

    用法：
        calc = ExecutionAdjustedSharpe()
        report = calc.calculate(
            paper_sharpe=2.0,
            annual_return=0.3,
            turnover=5.0,
            fee_rate=0.0004,
            slippage_bps=2.0,
            volume=1_000_000,
            volatility=0.02,
            avg_order_qty=10,
        )
        print(report.decomposition.real_sharpe)
    """

    def __init__(
        self,
        trading_days: int = 252,
        institutional_sharpe_threshold: float = 1.5,
    ) -> None:
        self.trading_days = trading_days
        self.institutional_threshold = institutional_sharpe_threshold

    def calculate(
        self,
        paper_sharpe: float,
        annual_return: float,
        turnover: float,             # 日均换手
        fee_rate: float = 0.0004,
        slippage_bps: float = 2.0,
        volume: float = 1_000_000,
        volatility: float = 0.02,
        avg_order_qty: float = 1.0,
        opportunity_cost_bps: float = 0.0,
        funding_rate_bps: float = 0.0,
        holding_days: float = 5.0,
    ) -> AdjustedSharpeReport:
        """计算执行调整夏普"""
        decomp = SharpeDecomposition(paper_sharpe=paper_sharpe)
        report = AdjustedSharpeReport(decomposition=decomp)

        # 记录假设
        report.assumptions = {
            "trading_days": self.trading_days,
            "annual_return": annual_return,
            "turnover": turnover,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "volume": volume,
            "volatility": volatility,
            "avg_order_qty": avg_order_qty,
        }

        # 年化收益率（用于惩罚转换）
        annual_vol = annual_return / paper_sharpe if paper_sharpe > 0 else 0.2

        # 1. 手续费惩罚
        annual_fee_cost = turnover * fee_rate * self.trading_days
        decomp.fee_penalty = annual_fee_cost / annual_vol if annual_vol > 0 else 0

        # 2. 滑点惩罚
        annual_slippage_cost = turnover * slippage_bps / 10000 * self.trading_days
        decomp.slippage_penalty = annual_slippage_cost / annual_vol if annual_vol > 0 else 0

        # 3. 冲击惩罚（sqrt 模型）
        if volume > 0 and avg_order_qty > 0:
            participation = avg_order_qty / volume
            impact_bps = volatility * 0.1 * math.sqrt(participation) * 10000
            annual_impact_cost = turnover * impact_bps / 10000 * self.trading_days
            decomp.impact_penalty = annual_impact_cost / annual_vol if annual_vol > 0 else 0

        # 4. 机会成本惩罚
        annual_opportunity_cost = opportunity_cost_bps / 10000 * self.trading_days
        decomp.opportunity_penalty = annual_opportunity_cost / annual_vol if annual_vol > 0 else 0

        # 5. 资金费率惩罚
        if holding_days > 0:
            annual_funding = funding_rate_bps / 10000 * (self.trading_days / holding_days)
            decomp.funding_penalty = annual_funding / annual_vol if annual_vol > 0 else 0

        # 评级
        report.grade = self._grade(decomp.real_sharpe)
        report.is_institutional = decomp.real_sharpe >= self.institutional_threshold
        report.verdict = self._verdict(decomp)

        return report

    def _grade(self, real_sharpe: float) -> str:
        if real_sharpe >= 2.0:
            return "A"
        elif real_sharpe >= 1.5:
            return "B"
        elif real_sharpe >= 1.0:
            return "C"
        elif real_sharpe >= 0.5:
            return "D"
        else:
            return "F"

    def _verdict(self, decomp: SharpeDecomposition) -> str:
        if decomp.real_sharpe >= 2.0:
            return "EXCELLENT"
        elif decomp.real_sharpe >= 1.5:
            return "INSTITUTIONAL"
        elif decomp.real_sharpe >= 1.0:
            return "TRADABLE"
        elif decomp.real_sharpe >= 0.5:
            return "MARGINAL"
        else:
            return "UNPROFITABLE"
