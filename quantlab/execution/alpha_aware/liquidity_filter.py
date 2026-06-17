"""
Liquidity-Aware Alpha Filter — 流动性过滤

核心逻辑：alpha 只有在"能成交"的市场才成立

指标：
  - volume（成交量）
  - spread（价差）
  - depth（深度）
  - impact_cost（冲击成本）

过滤规则：
  if (volume < threshold) reject alpha
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.alpha_aware.liquidity_filter")


class FilterVerdict(str, Enum):
    """过滤结论"""
    PASS = "PASS"                   # 通过
    WARN = "WARN"                   # 警告
    REJECT = "REJECT"               # 拒绝
    REJECT_CRITICAL = "REJECT_CRITICAL"  # 严重拒绝


@dataclass
class LiquidityMetrics:
    """流动性指标"""
    symbol: str
    avg_volume_24h: float = 0.0       # 24h 平均成交量（USD）
    avg_spread_bps: float = 0.0       # 平均价差（bps）
    avg_depth_usd: float = 0.0        # 平均深度（USD）
    volatility: float = 0.0           # 波动率
    impact_cost_bps: float = 0.0      # 冲击成本（bps）

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "avg_volume_24h": self.avg_volume_24h,
            "avg_spread_bps": self.avg_spread_bps,
            "avg_depth_usd": self.avg_depth_usd,
            "volatility": self.volatility,
            "impact_cost_bps": self.impact_cost_bps,
        }


@dataclass
class FilterResult:
    """过滤结果"""
    symbol: str
    verdict: FilterVerdict = FilterVerdict.PASS
    scores: Dict[str, float] = field(default_factory=dict)  # 各维度评分
    overall_score: float = 0.0       # 综合评分（0~1）
    reasons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "verdict": self.verdict.value,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "reasons": self.reasons,
            "recommendations": self.recommendations,
        }


class LiquidityAlphaFilter:
    """
    流动性过滤

    用法：
        filt = LiquidityAlphaFilter(
            min_volume_24h=10_000_000,
            max_spread_bps=10.0,
            min_depth_usd=100_000,
            max_impact_bps=5.0,
        )
        result = filt.check(LiquidityMetrics(
            symbol="BTCUSDT",
            avg_volume_24h=5_000_000_000,
            avg_spread_bps=2.0,
            avg_depth_usd=5_000_000,
            volatility=0.02,
            impact_cost_bps=1.0,
        ))
        print(result.verdict)  # PASS
    """

    def __init__(
        self,
        min_volume_24h: float = 10_000_000,     # 1000万 USD
        max_spread_bps: float = 10.0,
        min_depth_usd: float = 100_000,
        max_impact_bps: float = 5.0,
        max_volatility: float = 0.10,
    ) -> None:
        self.min_volume = min_volume_24h
        self.max_spread = max_spread_bps
        self.min_depth = min_depth_usd
        self.max_impact = max_impact_bps
        self.max_volatility = max_volatility

    def check(self, metrics: LiquidityMetrics) -> FilterResult:
        """检查流动性"""
        result = FilterResult(symbol=metrics.symbol)

        # 1. 成交量评分
        vol_score = self._volume_score(metrics.avg_volume_24h)
        result.scores["volume"] = vol_score

        # 2. 价差评分
        spread_score = self._spread_score(metrics.avg_spread_bps)
        result.scores["spread"] = spread_score

        # 3. 深度评分
        depth_score = self._depth_score(metrics.avg_depth_usd)
        result.scores["depth"] = depth_score

        # 4. 冲击成本评分
        impact_score = self._impact_score(metrics.impact_cost_bps)
        result.scores["impact"] = impact_score

        # 5. 波动率评分
        vol_score_2 = self._volatility_score(metrics.volatility)
        result.scores["volatility"] = vol_score_2

        # 综合评分
        result.overall_score = (
            vol_score * 0.3
            + spread_score * 0.2
            + depth_score * 0.2
            + impact_score * 0.2
            + vol_score_2 * 0.1
        )

        # 判定
        result.verdict = self._judge(metrics, result.scores)
        result.reasons = self._reasons(metrics, result.scores)
        result.recommendations = self._recommendations(metrics, result)

        return result

    def _volume_score(self, volume: float) -> float:
        """成交量评分"""
        if volume <= 0:
            return 0.0
        # 对数缩放：1000万=0, 1亿=0.5, 10亿=1.0
        return min(1.0, max(0.0, (math.log10(volume) - 7) / 3))

    def _spread_score(self, spread_bps: float) -> float:
        """价差评分"""
        if spread_bps <= 0:
            return 1.0
        # 0bps=1, 5bps=0.5, 10bps=0, >10bps=0
        return max(0.0, 1.0 - spread_bps / 10.0)

    def _depth_score(self, depth_usd: float) -> float:
        """深度评分"""
        if depth_usd <= 0:
            return 0.0
        return min(1.0, math.log10(max(1, depth_usd)) / 7)  # 1000万=1.0

    def _impact_score(self, impact_bps: float) -> float:
        """冲击成本评分"""
        if impact_bps <= 0:
            return 1.0
        return max(0.0, 1.0 - impact_bps / 10.0)

    def _volatility_score(self, vol: float) -> float:
        """波动率评分"""
        if vol <= 0:
            return 1.0
        return max(0.0, 1.0 - vol / 0.2)

    def _judge(self, m: LiquidityMetrics, scores: Dict) -> FilterVerdict:
        """判定"""
        # 严重拒绝条件
        if m.avg_volume_24h < self.min_volume * 0.1:
            return FilterVerdict.REJECT_CRITICAL
        if m.avg_spread_bps > self.max_spread * 3:
            return FilterVerdict.REJECT_CRITICAL
        if m.impact_cost_bps > self.max_impact * 5:
            return FilterVerdict.REJECT_CRITICAL

        # 普通拒绝
        if m.avg_volume_24h < self.min_volume:
            return FilterVerdict.REJECT
        if m.avg_spread_bps > self.max_spread:
            return FilterVerdict.REJECT
        if m.avg_depth_usd < self.min_depth:
            return FilterVerdict.REJECT
        if m.impact_cost_bps > self.max_impact:
            return FilterVerdict.REJECT
        if m.volatility > self.max_volatility:
            return FilterVerdict.REJECT

        # 警告
        if m.avg_volume_24h < self.min_volume * 3:
            return FilterVerdict.WARN
        if m.avg_spread_bps > self.max_spread * 0.5:
            return FilterVerdict.WARN

        return FilterVerdict.PASS

    def _reasons(self, m: LiquidityMetrics, scores: Dict) -> List[str]:
        reasons = []
        if m.avg_volume_24h < self.min_volume:
            reasons.append(f"成交量不足: {m.avg_volume_24h:.0f} < {self.min_volume:.0f}")
        if m.avg_spread_bps > self.max_spread:
            reasons.append(f"价差过大: {m.avg_spread_bps:.1f}bps > {self.max_spread:.1f}bps")
        if m.avg_depth_usd < self.min_depth:
            reasons.append(f"深度不足: {m.avg_depth_usd:.0f} < {self.min_depth:.0f}")
        if m.impact_cost_bps > self.max_impact:
            reasons.append(f"冲击成本高: {m.impact_cost_bps:.1f}bps > {self.max_impact:.1f}bps")
        if m.volatility > self.max_volatility:
            reasons.append(f"波动率过高: {m.volatility:.4f} > {self.max_volatility:.4f}")
        return reasons

    def _recommendations(self, m: LiquidityMetrics, result: FilterResult) -> List[str]:
        recs = []
        if result.verdict == FilterVerdict.REJECT_CRITICAL:
            recs.append("强烈建议放弃该标的，流动性严重不足")
        elif result.verdict == FilterVerdict.REJECT:
            recs.append("建议寻找流动性更好的替代标的")
        elif result.verdict == FilterVerdict.WARN:
            recs.append("可交易但需谨慎，建议减少仓位")
        else:
            recs.append("流动性良好，可正常交易")

        if m.avg_spread_bps > 5:
            recs.append("使用限价单减少价差损失")
        if m.impact_cost_bps > 3:
            recs.append("拆单减少冲击成本")
        return recs

    def batch_check(self, metrics_list: List[LiquidityMetrics]) -> List[FilterResult]:
        """批量检查"""
        return [self.check(m) for m in metrics_list]
