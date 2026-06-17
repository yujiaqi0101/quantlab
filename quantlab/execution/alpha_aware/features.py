"""
Execution-Aware Feature Engineering — 执行感知特征

更高级的特征工程：
  RSI → RSI_adjusted

加入：
  - liquidity weighting
  - turnover penalty
  - impact scaling

变成：Execution-aware feature space
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger("quantlab.execution.alpha_aware.features")


@dataclass
class FeatureContext:
    """特征上下文"""
    volume: float = 1_000_000
    spread_bps: float = 2.0
    depth: float = 100.0
    volatility: float = 0.02
    turnover: float = 1.0
    impact_bps: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "volume": self.volume,
            "spread_bps": self.spread_bps,
            "depth": self.depth,
            "volatility": self.volatility,
            "turnover": self.turnover,
            "impact_bps": self.impact_bps,
        }


@dataclass
class AdjustedFeature:
    """调整后特征"""
    name: str
    original: float
    adjusted: float
    weight: float
    adjustment_factor: float

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "original": self.original,
            "adjusted": self.adjusted,
            "weight": self.weight,
            "adjustment_factor": self.adjustment_factor,
        }


class ExecutionAwareFeatureEngine:
    """
    执行感知特征引擎

    用法：
        engine = ExecutionAwareFeatureEngine()
        ctx = FeatureContext(volume=500_000, spread_bps=5.0, volatility=0.03)

        # 调整 RSI
        rsi_adj = engine.adjust_rsi(rsi_value=65, ctx=ctx)

        # 调整动量
        mom_adj = engine.adjust_momentum(momentum=0.05, ctx=ctx)

        # 批量调整
        features = {"rsi": 65, "momentum": 0.05, "mean_reversion": -0.03}
        adjusted = engine.adjust_batch(features, ctx)
    """

    def __init__(
        self,
        volume_ref: float = 1_000_000,    # 参考成交量
        spread_ref_bps: float = 2.0,      # 参考价差
        volatility_ref: float = 0.02,     # 参考波动率
    ) -> None:
        self.volume_ref = volume_ref
        self.spread_ref = spread_ref_bps
        self.volatility_ref = volatility_ref

    def compute_liquidity_weight(self, ctx: FeatureContext) -> float:
        """计算流动性权重（0~1，1=流动性极好）"""
        # 成交量权重
        vol_weight = min(1.0, math.log10(max(1, ctx.volume)) / math.log10(max(1, self.volume_ref)))

        # 价差权重
        spread_weight = max(0.0, 1.0 - (ctx.spread_bps - self.spread_ref) / 20)

        # 深度权重
        depth_weight = min(1.0, ctx.depth / 1000)

        return vol_weight * 0.4 + spread_weight * 0.3 + depth_weight * 0.3

    def compute_turnover_penalty(self, ctx: FeatureContext) -> float:
        """计算换手惩罚（0~1，1=无惩罚）"""
        return max(0.0, 1.0 - ctx.turnover / 10.0)

    def compute_impact_scaling(self, ctx: FeatureContext) -> float:
        """计算冲击缩放（>1=放大，<1=缩小）"""
        # 冲击越大，特征信号越被稀释
        if ctx.impact_bps <= 0:
            return 1.0
        return max(0.1, 1.0 - ctx.impact_bps / 20)

    def compute_volatility_scaling(self, ctx: FeatureContext) -> float:
        """计算波动率缩放"""
        # 高波动时，短期信号衰减更快
        if ctx.volatility <= 0:
            return 1.0
        ratio = ctx.volatility / self.volatility_ref
        return max(0.3, 1.0 / ratio)

    def adjust_rsi(self, rsi_value: float, ctx: FeatureContext) -> AdjustedFeature:
        """调整 RSI"""
        # RSI 在流动性差时信号衰减
        liquidity_weight = self.compute_liquidity_weight(ctx)
        turnover_penalty = self.compute_turnover_penalty(ctx)
        impact_scaling = self.compute_impact_scaling(ctx)

        # 综合调整因子
        adjustment = liquidity_weight * turnover_penalty * impact_scaling

        # RSI 调整：向 50（中性）回归
        adjusted = 50 + (rsi_value - 50) * adjustment

        return AdjustedFeature(
            name="rsi_adjusted",
            original=rsi_value,
            adjusted=adjusted,
            weight=liquidity_weight,
            adjustment_factor=adjustment,
        )

    def adjust_momentum(self, momentum: float, ctx: FeatureContext) -> AdjustedFeature:
        """调整动量"""
        liquidity_weight = self.compute_liquidity_weight(ctx)
        turnover_penalty = self.compute_turnover_penalty(ctx)
        vol_scaling = self.compute_volatility_scaling(ctx)

        # 动量在高波动时衰减
        adjustment = liquidity_weight * turnover_penalty * vol_scaling

        adjusted = momentum * adjustment

        return AdjustedFeature(
            name="momentum_adjusted",
            original=momentum,
            adjusted=adjusted,
            weight=liquidity_weight,
            adjustment_factor=adjustment,
        )

    def adjust_mean_reversion(
        self,
        mean_rev_signal: float,
        ctx: FeatureContext,
    ) -> AdjustedFeature:
        """调整均值回归"""
        liquidity_weight = self.compute_liquidity_weight(ctx)
        impact_scaling = self.compute_impact_scaling(ctx)

        # 均值回归在流动性差时更难执行
        adjustment = liquidity_weight * impact_scaling

        adjusted = mean_rev_signal * adjustment

        return AdjustedFeature(
            name="mean_reversion_adjusted",
            original=mean_rev_signal,
            adjusted=adjusted,
            weight=liquidity_weight,
            adjustment_factor=adjustment,
        )

    def adjust_volume_signal(
        self,
        volume_signal: float,
        ctx: FeatureContext,
    ) -> AdjustedFeature:
        """调整成交量信号"""
        # 成交量信号在低流动性时反而可能更显著，但执行困难
        liquidity_weight = self.compute_liquidity_weight(ctx)
        turnover_penalty = self.compute_turnover_penalty(ctx)

        adjustment = liquidity_weight * turnover_penalty
        adjusted = volume_signal * adjustment

        return AdjustedFeature(
            name="volume_signal_adjusted",
            original=volume_signal,
            adjusted=adjusted,
            weight=liquidity_weight,
            adjustment_factor=adjustment,
        )

    def adjust_batch(
        self,
        features: Dict[str, float],
        ctx: FeatureContext,
    ) -> Dict[str, AdjustedFeature]:
        """批量调整特征"""
        result = {}

        for name, value in features.items():
            name_lower = name.lower()
            # 精确匹配特征类型（避免子串误匹配，如 "rsi" 误匹配 "mean_reversion"）
            if name_lower == "rsi" or name_lower.startswith("rsi_") or name_lower.endswith("_rsi"):
                result[name] = self.adjust_rsi(value, ctx)
            elif "momentum" in name_lower or name_lower.startswith("mom_") or name_lower == "mom":
                result[name] = self.adjust_momentum(value, ctx)
            elif "reversion" in name_lower or name_lower in ("mr", "mean_reversion"):
                result[name] = self.adjust_mean_reversion(value, ctx)
            elif "volume" in name_lower or name_lower == "vol":
                result[name] = self.adjust_volume_signal(value, ctx)
            else:
                # 默认：通用调整
                liquidity_weight = self.compute_liquidity_weight(ctx)
                turnover_penalty = self.compute_turnover_penalty(ctx)
                adjustment = liquidity_weight * turnover_penalty
                result[name] = AdjustedFeature(
                    name=f"{name}_adjusted",
                    original=value,
                    adjusted=value * adjustment,
                    weight=liquidity_weight,
                    adjustment_factor=adjustment,
                )

        return result

    def compute_execution_aware_alpha(
        self,
        alpha_signal: float,
        ctx: FeatureContext,
    ) -> AdjustedFeature:
        """计算执行感知 Alpha 信号"""
        liquidity_weight = self.compute_liquidity_weight(ctx)
        turnover_penalty = self.compute_turnover_penalty(ctx)
        impact_scaling = self.compute_impact_scaling(ctx)
        vol_scaling = self.compute_volatility_scaling(ctx)

        # 综合调整
        adjustment = liquidity_weight * turnover_penalty * impact_scaling * vol_scaling
        adjusted = alpha_signal * adjustment

        return AdjustedFeature(
            name="execution_aware_alpha",
            original=alpha_signal,
            adjusted=adjusted,
            weight=liquidity_weight,
            adjustment_factor=adjustment,
        )
