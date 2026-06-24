"""
Position Package — 仓位包

把仓位计算逻辑从硬编码类升级为可注册、可复用的 Package。

4 种实现：
  - FixedSizing: 固定仓位
  - ConfidenceSizing: 置信度映射
  - VolatilitySizing: 波动率调整
  - KellySizing: 凯利公式
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..base import AssetPackage, PackageType
from .signal import Signal, SignalSide

logger = logging.getLogger("quantlab.asset_package.types.position")


# ==================================================================
# PositionPackage 基类
# ==================================================================

@dataclass
class PositionPackage(AssetPackage):
    """仓位包基类"""
    package_type: PackageType = PackageType.POSITION

    def size(self, signals: List[Signal], capital: float,
             market_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        根据信号计算仓位

        Args:
            signals: 信号列表
            capital: 总资金
            market_data: 市场数据（某些模式需要，如波动率）

        Returns:
            {symbol: position_size} 仓位字典（正=多, 负=空, 0=空仓）
        """
        raise NotImplementedError("Subclass must implement size()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })


# ==================================================================
# 1. FixedSizing — 固定仓位
# ==================================================================

@dataclass
class FixedSizing(PositionPackage):
    """固定仓位：每个活跃信号分配固定比例"""
    base_size: float = 0.2         # 20%
    max_size: float = 1.0          # 100%

    def to_config(self) -> Dict[str, Any]:
        return {"base_size": self.base_size, "max_size": self.max_size}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.base_size = config.get("base_size", 0.2)
        self.max_size = config.get("max_size", 1.0)

    def size(self, signals: List[Signal], capital: float,
             market_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        positions = {}
        active_count = sum(1 for s in signals if s.is_active)
        if active_count == 0:
            return {s.symbol: 0.0 for s in signals}
        per_size = min(self.base_size, self.max_size / active_count)
        for sig in signals:
            if sig.side == SignalSide.BUY:
                positions[sig.symbol] = per_size
            elif sig.side == SignalSide.SELL:
                positions[sig.symbol] = -per_size
            else:
                positions[sig.symbol] = 0.0
        return positions


# ==================================================================
# 2. ConfidenceSizing — 置信度映射
# ==================================================================

@dataclass
class ConfidenceSizing(PositionPackage):
    """置信度映射：仓位 = score * confidence_scale"""
    confidence_scale: float = 1.0
    max_size: float = 1.0
    min_size: float = 0.0

    def to_config(self) -> Dict[str, Any]:
        return {
            "confidence_scale": self.confidence_scale,
            "max_size": self.max_size,
            "min_size": self.min_size,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.confidence_scale = config.get("confidence_scale", 1.0)
        self.max_size = config.get("max_size", 1.0)
        self.min_size = config.get("min_size", 0.0)

    def size(self, signals: List[Signal], capital: float,
             market_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        positions = {}
        for sig in signals:
            if sig.side == SignalSide.HOLD:
                positions[sig.symbol] = 0.0
                continue
            raw = abs(sig.score) * self.confidence_scale
            size = max(self.min_size, min(self.max_size, raw))
            if sig.side == SignalSide.SELL:
                size = -size
            positions[sig.symbol] = size
        return positions


# ==================================================================
# 3. VolatilitySizing — 波动率调整
# ==================================================================

@dataclass
class VolatilitySizing(PositionPackage):
    """波动率调整：仓位 = target_volatility / asset_volatility"""
    target_volatility: float = 0.15   # 目标年化波动率 15%
    vol_lookback: int = 20
    max_size: float = 1.0

    def to_config(self) -> Dict[str, Any]:
        return {
            "target_volatility": self.target_volatility,
            "vol_lookback": self.vol_lookback,
            "max_size": self.max_size,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.target_volatility = config.get("target_volatility", 0.15)
        self.vol_lookback = config.get("vol_lookback", 20)
        self.max_size = config.get("max_size", 1.0)

    def size(self, signals: List[Signal], capital: float,
             market_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        positions = {}
        for sig in signals:
            if sig.side == SignalSide.HOLD:
                positions[sig.symbol] = 0.0
                continue
            # 估算波动率
            if market_data is not None and sig.symbol in market_data:
                prices = market_data[sig.symbol].dropna()
                if len(prices) >= self.vol_lookback:
                    returns = prices.pct_change().dropna().tail(self.vol_lookback)
                    vol = returns.std() * np.sqrt(252)  # 年化
                else:
                    vol = self.target_volatility
            else:
                vol = self.target_volatility
            raw = self.target_volatility / (vol + 1e-9)
            size = min(self.max_size, raw)
            if sig.side == SignalSide.SELL:
                size = -size
            positions[sig.symbol] = size
        return positions


# ==================================================================
# 4. KellySizing — 凯利公式
# ==================================================================

@dataclass
class KellySizing(PositionPackage):
    """凯利公式：f* = (p*b - q) / b"""
    kelly_fraction: float = 0.5      # 半凯利
    win_rate: float = 0.55          # 胜率
    win_loss_ratio: float = 1.5     # 盈亏比
    max_size: float = 1.0

    def to_config(self) -> Dict[str, Any]:
        return {
            "kelly_fraction": self.kelly_fraction,
            "win_rate": self.win_rate,
            "win_loss_ratio": self.win_loss_ratio,
            "max_size": self.max_size,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.kelly_fraction = config.get("kelly_fraction", 0.5)
        self.win_rate = config.get("win_rate", 0.55)
        self.win_loss_ratio = config.get("win_loss_ratio", 1.5)
        self.max_size = config.get("max_size", 1.0)

    def size(self, signals: List[Signal], capital: float,
             market_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        p = self.win_rate
        q = 1 - p
        b = self.win_loss_ratio
        kelly = (p * b - q) / b if b > 0 else 0
        kelly = max(0, kelly) * self.kelly_fraction
        kelly = min(self.max_size, kelly)
        positions = {}
        for sig in signals:
            if sig.side == SignalSide.HOLD:
                positions[sig.symbol] = 0.0
            elif sig.side == SignalSide.BUY:
                positions[sig.symbol] = kelly
            else:
                positions[sig.symbol] = -kelly
        return positions
