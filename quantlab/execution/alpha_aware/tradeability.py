"""
Tradeability Score System — 可交易评分系统

统一输出：
  Alpha Score = Predictive Power × Executability × Stability × Cost Efficiency

最终你不再选：Sharpe 最高的策略
而是：最能活下来的策略
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .realizability import AlphaMetrics, ExecutionConstraints
from .survival import SurvivalInput

logger = logging.getLogger("quantlab.execution.alpha_aware.tradeability")


@dataclass
class TradeabilityScores:
    """可交易性各维度评分"""
    predictive_power: float = 0.0       # 预测能力（0~1）
    executability: float = 0.0          # 可执行性（0~1）
    stability: float = 0.0              # 稳定性（0~1）
    cost_efficiency: float = 0.0        # 成本效率（0~1）

    def to_dict(self) -> Dict:
        return {
            "predictive_power": self.predictive_power,
            "executability": self.executability,
            "stability": self.stability,
            "cost_efficiency": self.cost_efficiency,
        }


@dataclass
class TradeabilityReport:
    """可交易性报告"""
    scores: TradeabilityScores = field(default_factory=TradeabilityScores)

    # 综合
    alpha_score: float = 0.0            # 综合评分（0~1）
    rank: str = ""                      # S / A / B / C / D
    is_recommended: bool = False        # 是否推荐

    # 拆解
    components: Dict = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "scores": self.scores.to_dict(),
            "alpha_score": self.alpha_score,
            "rank": self.rank,
            "is_recommended": self.is_recommended,
            "components": self.components,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
        }


class TradeabilityScoreSystem:
    """
    可交易评分系统

    用法：
        system = TradeabilityScoreSystem()
        report = system.evaluate(
            metrics=AlphaMetrics(ic=0.05, sharpe=1.5, turnover=3.0),
            constraints=ExecutionConstraints(avg_volume=1_000_000, slippage_bps=2.0),
            survival=SurvivalInput(
                ic_mean=0.05,
                ic_ir=1.5,
                slippage_sensitivity=0.3,
                breakpoint_multiplier=2.5,
                liquidity_score=0.8,
                real_sharpe=1.2,
                paper_sharpe=1.5,
            ),
        )
        print(report.rank)  # A
    """

    def __init__(
        self,
        recommend_threshold: float = 0.6,
    ) -> None:
        self.recommend_threshold = recommend_threshold

    def evaluate(
        self,
        metrics: AlphaMetrics,
        constraints: ExecutionConstraints,
        survival: SurvivalInput,
    ) -> TradeabilityReport:
        """评估可交易性"""
        report = TradeabilityReport()

        # 1. 预测能力
        report.scores.predictive_power = self._predictive_power(metrics, survival)
        report.components["predictive_power"] = report.scores.predictive_power

        # 2. 可执行性
        report.scores.executability = self._executability(metrics, constraints, survival)
        report.components["executability"] = report.scores.executability

        # 3. 稳定性
        report.scores.stability = self._stability(metrics, survival)
        report.components["stability"] = report.scores.stability

        # 4. 成本效率
        report.scores.cost_efficiency = self._cost_efficiency(metrics, constraints)
        report.components["cost_efficiency"] = report.scores.cost_efficiency

        # 综合评分（乘法：任一维度低都会拉低总分）
        report.alpha_score = (
            report.scores.predictive_power
            * report.scores.executability
            * report.scores.stability
            * report.scores.cost_efficiency
        )

        # 开四次方根（几何平均的变体，避免分数过低）
        if report.alpha_score > 0:
            report.alpha_score = math.pow(report.alpha_score, 0.5)

        # 评级
        report.rank = self._rank(report.alpha_score)
        report.is_recommended = report.alpha_score >= self.recommend_threshold

        # 拆解
        report.strengths = self._strengths(report.scores)
        report.weaknesses = self._weaknesses(report.scores)
        report.recommendations = self._recommendations(report)

        return report

    def _predictive_power(self, m: AlphaMetrics, s: SurvivalInput) -> float:
        """预测能力"""
        # IC
        ic_score = min(1.0, abs(m.ic) / 0.1)

        # IC IR
        ir_score = min(1.0, abs(m.ic_ir) / 2.0)

        # IC 命中率
        hit_score = s.ic_hit_rate

        # 夏普
        sharpe_score = min(1.0, m.sharpe / 3.0)

        return (ic_score * 0.3 + ir_score * 0.25 + hit_score * 0.15 + sharpe_score * 0.3)

    def _executability(
        self,
        m: AlphaMetrics,
        c: ExecutionConstraints,
        s: SurvivalInput,
    ) -> float:
        """可执行性"""
        # 流动性
        liquidity = s.liquidity_score

        # 换手合理性
        turnover_score = max(0.0, 1.0 - m.turnover / 10.0)

        # 滑点韧性
        slippage_resilience = min(1.0, s.breakpoint_multiplier / 3.0)

        # 延迟可扩展性
        if s.latency_critical_ms >= 1000:
            latency_score = 1.0
        elif s.latency_critical_ms >= 100:
            latency_score = 0.6
        else:
            latency_score = 0.3

        return (liquidity * 0.3 + turnover_score * 0.25 + slippage_resilience * 0.25 + latency_score * 0.2)

    def _stability(self, m: AlphaMetrics, s: SurvivalInput) -> float:
        """稳定性"""
        # IC 稳定性
        ic_stability = min(1.0, abs(s.ic_ir) / 2.0)

        # 回撤
        drawdown_score = max(0.0, 1.0 - m.max_drawdown / 0.3)

        # 换手波动
        turnover_stability = max(0.0, 1.0 - s.turnover_volatility / 5.0)

        # 夏普衰减
        if m.sharpe > 0:
            decay = 1 - s.real_sharpe / m.sharpe if m.sharpe > 0 else 1
            decay_score = 1 - decay
        else:
            decay_score = 0

        return (ic_stability * 0.3 + drawdown_score * 0.25 + turnover_stability * 0.2 + decay_score * 0.25)

    def _cost_efficiency(self, m: AlphaMetrics, c: ExecutionConstraints) -> float:
        """成本效率"""
        # 年化成本
        annual_cost = m.turnover * (c.fee_rate + c.slippage_bps / 10000) * 252

        # 成本占收益比例
        if m.avg_return > 0:
            cost_ratio = annual_cost / m.avg_return
            cost_score = max(0.0, 1.0 - cost_ratio)
        else:
            cost_score = 0.0

        # 真实夏普 vs 纸面夏普
        if m.sharpe > 0:
            real_sharpe_ratio = max(0.0, min(1.0, (m.sharpe - annual_cost / max(0.01, m.avg_return) * m.sharpe) / m.sharpe))
        else:
            real_sharpe_ratio = 0

        return (cost_score * 0.6 + real_sharpe_ratio * 0.4)

    def _rank(self, score: float) -> str:
        if score >= 0.8:
            return "S"
        elif score >= 0.65:
            return "A"
        elif score >= 0.5:
            return "B"
        elif score >= 0.35:
            return "C"
        elif score >= 0.2:
            return "D"
        else:
            return "F"

    def _strengths(self, scores: TradeabilityScores) -> List[str]:
        strengths = []
        if scores.predictive_power >= 0.7:
            strengths.append(f"预测能力强: {scores.predictive_power:.2f}")
        if scores.executability >= 0.7:
            strengths.append(f"可执行性好: {scores.executability:.2f}")
        if scores.stability >= 0.7:
            strengths.append(f"稳定性高: {scores.stability:.2f}")
        if scores.cost_efficiency >= 0.7:
            strengths.append(f"成本效率高: {scores.cost_efficiency:.2f}")
        return strengths

    def _weaknesses(self, scores: TradeabilityScores) -> List[str]:
        weaknesses = []
        if scores.predictive_power < 0.4:
            weaknesses.append(f"预测能力弱: {scores.predictive_power:.2f}")
        if scores.executability < 0.4:
            weaknesses.append(f"可执行性差: {scores.executability:.2f}")
        if scores.stability < 0.4:
            weaknesses.append(f"稳定性低: {scores.stability:.2f}")
        if scores.cost_efficiency < 0.4:
            weaknesses.append(f"成本效率低: {scores.cost_efficiency:.2f}")
        return weaknesses

    def _recommendations(self, report: TradeabilityReport) -> List[str]:
        recs = []
        if report.is_recommended:
            recs.append("推荐投入实盘")
        else:
            recs.append("暂不推荐实盘，需优化")

        # 针对最弱维度
        scores = report.scores
        weakest = min(
            [("predictive_power", scores.predictive_power),
             ("executability", scores.executability),
             ("stability", scores.stability),
             ("cost_efficiency", scores.cost_efficiency)],
            key=lambda x: x[1],
        )

        if weakest[1] < 0.5:
            if weakest[0] == "predictive_power":
                recs.append("提升预测能力：优化因子或增加特征")
            elif weakest[0] == "executability":
                recs.append("提升可执行性：选择流动性更好的标的或降低换手")
            elif weakest[0] == "stability":
                recs.append("提升稳定性：增加信号过滤或平滑持仓")
            elif weakest[0] == "cost_efficiency":
                recs.append("提升成本效率：使用 maker 单或拆单")

        return recs
