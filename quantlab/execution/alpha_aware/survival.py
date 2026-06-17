"""
Alpha Survival Filter — Alpha 生存过滤器

规则：
  - IC 稳定性
  - 换手
  - 滑点敏感性
  - 流动性

输出：Survives / Dies
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.alpha_aware.survival")


@dataclass
class SurvivalInput:
    """生存评估输入"""
    # IC 指标
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ic_ir: float = 0.0
    ic_hit_rate: float = 0.0          # IC 正向命中率

    # 换手
    turnover: float = 0.0
    turnover_volatility: float = 0.0

    # 滑点敏感性
    slippage_sensitivity: float = 0.0  # 0~1，1=极敏感
    breakpoint_multiplier: float = 0.0  # 收益归零的滑点倍数

    # 流动性
    liquidity_score: float = 0.0       # 0~1
    volume_score: float = 0.0

    # 延迟
    latency_critical_ms: float = 0.0
    latency_class: str = "MEDIUM"

    # 真实夏普
    real_sharpe: float = 0.0
    paper_sharpe: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "ic_ir": self.ic_ir,
            "ic_hit_rate": self.ic_hit_rate,
            "turnover": self.turnover,
            "turnover_volatility": self.turnover_volatility,
            "slippage_sensitivity": self.slippage_sensitivity,
            "breakpoint_multiplier": self.breakpoint_multiplier,
            "liquidity_score": self.liquidity_score,
            "volume_score": self.volume_score,
            "latency_critical_ms": self.latency_critical_ms,
            "latency_class": self.latency_class,
            "real_sharpe": self.real_sharpe,
            "paper_sharpe": self.paper_sharpe,
        }


@dataclass
class SurvivalScores:
    """各维度生存评分"""
    ic_stability: float = 0.0          # IC 稳定性（0~1）
    turnover_score: float = 0.0        # 换手评分
    slippage_resilience: float = 0.0   # 滑点韧性
    liquidity_fit: float = 0.0         # 流动性匹配
    latency_scalability: float = 0.0   # 延迟可扩展性
    sharpe_quality: float = 0.0        # 夏普质量

    def to_dict(self) -> Dict:
        return {
            "ic_stability": self.ic_stability,
            "turnover_score": self.turnover_score,
            "slippage_resilience": self.slippage_resilience,
            "liquidity_fit": self.liquidity_fit,
            "latency_scalability": self.latency_scalability,
            "sharpe_quality": self.sharpe_quality,
        }


@dataclass
class SurvivalReport:
    """生存报告"""
    input_data: SurvivalInput = field(default_factory=SurvivalInput)
    scores: SurvivalScores = field(default_factory=SurvivalScores)

    # 综合
    survival_score: float = 0.0        # 0~1，1=极可能生存
    survives: bool = False
    verdict: str = ""                  # SURVIVES / DIES / MARGINAL

    # 拆解
    failure_reasons: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "input": self.input_data.to_dict(),
            "scores": self.scores.to_dict(),
            "survival_score": self.survival_score,
            "survives": self.survives,
            "verdict": self.verdict,
            "failure_reasons": self.failure_reasons,
            "strengths": self.strengths,
            "recommendations": self.recommendations,
        }


class AlphaSurvivalFilter:
    """
    Alpha 生存过滤器

    用法：
        filt = AlphaSurvivalFilter()
        report = filt.evaluate(SurvivalInput(
            ic_mean=0.05,
            ic_ir=1.5,
            turnover=3.0,
            slippage_sensitivity=0.3,
            breakpoint_multiplier=2.5,
            liquidity_score=0.8,
            real_sharpe=1.2,
            paper_sharpe=2.0,
        ))
        print(report.verdict)  # SURVIVES
    """

    def __init__(
        self,
        survival_threshold: float = 0.6,
        min_ic: float = 0.02,
        min_real_sharpe: float = 0.5,
        max_turnover: float = 10.0,
        min_breakpoint: float = 1.5,
    ) -> None:
        self.survival_threshold = survival_threshold
        self.min_ic = min_ic
        self.min_real_sharpe = min_real_sharpe
        self.max_turnover = max_turnover
        self.min_breakpoint = min_breakpoint

    def evaluate(self, data: SurvivalInput) -> SurvivalReport:
        """评估 Alpha 生存能力"""
        report = SurvivalReport(input_data=data)

        # 1. IC 稳定性
        report.scores.ic_stability = self._ic_stability(data)
        report.scores.turnover_score = self._turnover_score(data)
        report.scores.slippage_resilience = self._slippage_resilience(data)
        report.scores.liquidity_fit = self._liquidity_fit(data)
        report.scores.latency_scalability = self._latency_scalability(data)
        report.scores.sharpe_quality = self._sharpe_quality(data)

        # 综合评分
        report.survival_score = (
            report.scores.ic_stability * 0.25
            + report.scores.turnover_score * 0.15
            + report.scores.slippage_resilience * 0.20
            + report.scores.liquidity_fit * 0.15
            + report.scores.latency_scalability * 0.10
            + report.scores.sharpe_quality * 0.15
        )

        # 判定
        report.survives = (
            report.survival_score >= self.survival_threshold
            and data.ic_mean >= self.min_ic
            and data.real_sharpe >= self.min_real_sharpe
            and data.turnover <= self.max_turnover
            and data.breakpoint_multiplier >= self.min_breakpoint
        )

        report.verdict = self._verdict(report)
        report.failure_reasons = self._failure_reasons(data, report)
        report.strengths = self._strengths(data, report)
        report.recommendations = self._recommendations(data, report)

        return report

    def _ic_stability(self, data: SurvivalInput) -> float:
        """IC 稳定性"""
        # IC 均值
        ic_mean_score = min(1.0, abs(data.ic_mean) / 0.1)

        # IC 信息比
        ic_ir_score = min(1.0, abs(data.ic_ir) / 2.0)

        # IC 命中率
        ic_hit_score = data.ic_hit_rate

        return (ic_mean_score * 0.4 + ic_ir_score * 0.4 + ic_hit_score * 0.2)

    def _turnover_score(self, data: SurvivalInput) -> float:
        """换手评分"""
        # 换手水平
        level_score = max(0.0, 1.0 - data.turnover / 10.0)

        # 换手稳定性
        stability_score = max(0.0, 1.0 - data.turnover_volatility / 5.0)

        return level_score * 0.7 + stability_score * 0.3

    def _slippage_resilience(self, data: SurvivalInput) -> float:
        """滑点韧性"""
        # 敏感性越低越好
        sensitivity_score = 1.0 - data.slippage_sensitivity

        # breakpoint 越高越好
        breakpoint_score = min(1.0, data.breakpoint_multiplier / 3.0)

        return sensitivity_score * 0.4 + breakpoint_score * 0.6

    def _liquidity_fit(self, data: SurvivalInput) -> float:
        """流动性匹配"""
        return (data.liquidity_score * 0.6 + data.volume_score * 0.4)

    def _latency_scalability(self, data: SurvivalInput) -> float:
        """延迟可扩展性"""
        if data.latency_critical_ms >= 1000:
            return 1.0
        elif data.latency_critical_ms >= 100:
            return 0.6
        elif data.latency_critical_ms >= 10:
            return 0.3
        else:
            return 0.1

    def _sharpe_quality(self, data: SurvivalInput) -> float:
        """夏普质量"""
        # 真实夏普
        real_score = min(1.0, data.real_sharpe / 2.0)

        # 衰减率
        if data.paper_sharpe > 0:
            decay = 1 - data.real_sharpe / data.paper_sharpe
            decay_score = 1 - decay
        else:
            decay_score = 0

        return real_score * 0.6 + decay_score * 0.4

    def _verdict(self, report: SurvivalReport) -> str:
        if report.survives and report.survival_score >= 0.8:
            return "SURVIVES_STRONG"
        elif report.survives:
            return "SURVIVES"
        elif report.survival_score >= 0.4:
            return "MARGINAL"
        else:
            return "DIES"

    def _failure_reasons(self, data: SurvivalInput, report: SurvivalReport) -> List[str]:
        reasons = []
        if data.ic_mean < self.min_ic:
            reasons.append(f"IC 过低: {data.ic_mean:.4f} < {self.min_ic}")
        if data.real_sharpe < self.min_real_sharpe:
            reasons.append(f"真实夏普过低: {data.real_sharpe:.2f} < {self.min_real_sharpe}")
        if data.turnover > self.max_turnover:
            reasons.append(f"换手过高: {data.turnover:.1f} > {self.max_turnover}")
        if data.breakpoint_multiplier < self.min_breakpoint:
            reasons.append(f"滑点脆弱: breakpoint={data.breakpoint_multiplier:.1f}x < {self.min_breakpoint}x")
        if data.slippage_sensitivity > 0.7:
            reasons.append(f"滑点敏感性过高: {data.slippage_sensitivity:.2f}")
        if data.liquidity_score < 0.3:
            reasons.append(f"流动性不足: {data.liquidity_score:.2f}")
        if data.latency_critical_ms < 100:
            reasons.append(f"延迟脆弱: {data.latency_critical_ms:.0f}ms")
        return reasons

    def _strengths(self, data: SurvivalInput, report: SurvivalReport) -> List[str]:
        strengths = []
        if data.ic_mean >= 0.05:
            strengths.append(f"IC 强: {data.ic_mean:.4f}")
        if data.ic_ir >= 1.5:
            strengths.append(f"IC 稳定: IR={data.ic_ir:.2f}")
        if data.real_sharpe >= 1.5:
            strengths.append(f"真实夏普高: {data.real_sharpe:.2f}")
        if data.breakpoint_multiplier >= 3.0:
            strengths.append(f"滑点韧性强: breakpoint={data.breakpoint_multiplier:.1f}x")
        if data.liquidity_score >= 0.7:
            strengths.append(f"流动性好: {data.liquidity_score:.2f}")
        if data.latency_critical_ms >= 1000:
            strengths.append(f"延迟可扩展: {data.latency_critical_ms:.0f}ms")
        return strengths

    def _recommendations(self, data: SurvivalInput, report: SurvivalReport) -> List[str]:
        recs = []
        if report.verdict == "DIES":
            recs.append("建议放弃该策略")
        elif report.verdict == "MARGINAL":
            recs.append("策略边缘，需要优化")
        elif report.verdict == "SURVIVES":
            recs.append("策略可生存，可投入实盘")
        else:
            recs.append("策略强健，推荐实盘")

        if data.turnover > 5.0:
            recs.append("降低换手：增加信号阈值或平滑持仓")
        if data.slippage_sensitivity > 0.5:
            recs.append("减少滑点敏感性：使用限价单或拆单")
        if data.liquidity_score < 0.5:
            recs.append("选择流动性更好的标的")
        return recs
