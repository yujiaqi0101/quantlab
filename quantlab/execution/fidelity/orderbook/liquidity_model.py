"""
Liquidity Model — 流动性模型

量化市场流动性：
  1. 流动性评分（0~1）
  2. 深度估算
  3. 流动性调整滑点

流动性低 → 滑点高
流动性高 → 滑点低
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger("quantlab.execution.fidelity.liquidity")


@dataclass
class LiquidityProfile:
    """流动性画像"""
    symbol: str
    score: float              # 0~1, 1=极高流动性
    depth_usd: float          # 前 10 档深度（USD）
    avg_spread_bps: float     # 平均价差
    volume_24h: float = 0.0   # 24h 成交量
    volatility: float = 0.0   # 当前波动率

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "depth_usd": self.depth_usd,
            "avg_spread_bps": self.avg_spread_bps,
            "volume_24h": self.volume_24h,
            "volatility": self.volatility,
        }


class LiquidityModel:
    """
    流动性模型

    用法：
        model = LiquidityModel()
        profile = model.assess(symbol="BTCUSDT", volume_24h=5000000000, volatility=0.02)
        slippage_mult = model.slippage_multiplier(profile)
    """

    def __init__(
        self,
        high_volume_threshold: float = 1_000_000_000,   # 10亿 USD
        low_volume_threshold: float = 10_000_000,        # 1000万 USD
    ) -> None:
        self.high_vol_threshold = high_volume_threshold
        self.low_vol_threshold = low_volume_threshold

    def assess(
        self,
        symbol: str,
        volume_24h: float,
        volatility: float,
        depth_usd: float = 0,
        avg_spread_bps: float = 0,
    ) -> LiquidityProfile:
        """评估流动性"""
        # 基于成交量评分
        if volume_24h >= self.high_vol_threshold:
            vol_score = 1.0
        elif volume_24h <= self.low_vol_threshold:
            vol_score = 0.1
        else:
            vol_score = (
                (volume_24h - self.low_vol_threshold)
                / (self.high_vol_threshold - self.low_vol_threshold)
            )

        # 波动率惩罚
        vol_penalty = min(0.5, volatility * 10)
        score = max(0.05, vol_score - vol_penalty)

        return LiquidityProfile(
            symbol=symbol,
            score=score,
            depth_usd=depth_usd,
            avg_spread_bps=avg_spread_bps,
            volume_24h=volume_24h,
            volatility=volatility,
        )

    def slippage_multiplier(self, profile: LiquidityProfile) -> float:
        """
        滑点乘数

        流动性高 → 乘数接近 1
        流动性低 → 乘数放大
        """
        # score=1 → 1x, score=0.1 → 10x
        if profile.score <= 0:
            return 100.0
        return 1.0 / profile.score

    def max_order_size_pct(self, profile: LiquidityProfile) -> float:
        """
        建议最大下单量占深度的百分比

        流动性高 → 可下更大单
        """
        if profile.depth_usd <= 0:
            return 0.01
        return min(0.1, profile.score * 0.1)

    def is_tradable(self, profile: LiquidityProfile) -> bool:
        """是否可交易"""
        return profile.score >= 0.1 and profile.depth_usd > 0
