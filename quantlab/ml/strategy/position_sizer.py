"""
Position Sizer — 仓位管理器

ML Lab M5 第三部分：根据信号置信度决定仓位大小

  同样预测 0.03 和 0.30，置信度不同，仓位也应不同：
    score = 0.90  →  仓位 100%
    score = 0.55  →  仓位 20%

  size = f(score)

  支持模式：
    - Fixed       固定仓位
    - Volatility  波动率调整
    - Kelly       凯利公式（后期）
    - Confidence  置信度线性映射
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .signal_generator import Signal, SignalSide

logger = logging.getLogger("quantlab.ml.strategy.position_sizer")


# ------------------------------------------------------------------
# 仓位模式
# ------------------------------------------------------------------

class SizingMode(str, Enum):
    """仓位计算模式"""
    FIXED = "fixed"               # 固定仓位
    CONFIDENCE = "confidence"     # 置信度映射
    VOLATILITY = "volatility"     # 波动率调整
    KELLY = "kelly"               # 凯利公式


@dataclass
class PositionSizeConfig:
    """仓位配置"""
    mode: SizingMode = SizingMode.CONFIDENCE
    # 基础仓位（FIXED 模式或上限）
    base_size: float = 0.2         # 20%
    max_size: float = 1.0          # 100%
    min_size: float = 0.0          # 0%
    # CONFIDENCE 模式
    confidence_scale: float = 1.0  # score * scale → size
    # VOLATILITY 模式
    target_volatility: float = 0.15  # 目标年化波动率 15%
    vol_lookback: int = 20           # 波动率回看窗口
    # KELLY 模式
    kelly_fraction: float = 0.5      # 凯利分数（半凯利 = 0.5）
    win_rate: float = 0.55           # 胜率
    win_loss_ratio: float = 1.5      # 盈亏比

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "base_size": self.base_size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "confidence_scale": self.confidence_scale,
            "target_volatility": self.target_volatility,
            "vol_lookback": self.vol_lookback,
            "kelly_fraction": self.kelly_fraction,
            "win_rate": self.win_rate,
            "win_loss_ratio": self.win_loss_ratio,
        }


# ------------------------------------------------------------------
# PositionSizer
# ------------------------------------------------------------------

class PositionSizer:
    """
    仓位管理器

    用法：
        sizer = PositionSizer(config=PositionSizeConfig(mode=SizingMode.CONFIDENCE))
        size = sizer.size(signal=signal)
        # → 0.85

        # 批量
        sizes = sizer.size_batch(signals)
    """

    def __init__(self, config: Optional[PositionSizeConfig] = None) -> None:
        self.config = config or PositionSizeConfig()
        # 波动率历史（用于 VOLATILITY 模式）
        self._returns_history: List[float] = []

    def set_config(self, config: PositionSizeConfig) -> None:
        self.config = config

    def update_returns(self, ret: float) -> None:
        """更新收益率历史（VOLATILITY 模式用）"""
        self._returns_history.append(float(ret))
        lookback = self.config.vol_lookback
        if len(self._returns_history) > lookback * 2:
            self._returns_history = self._returns_history[-lookback * 2:]

    # ------------------------------------------------------------------
    # 单笔仓位
    # ------------------------------------------------------------------

    def size(
        self,
        signal: Signal,
        current_position: float = 0.0,
        current_volatility: Optional[float] = None,
    ) -> float:
        """
        计算目标仓位

        Args:
            signal: 交易信号
            current_position: 当前持仓（用于平滑）
            current_volatility: 当前波动率（VOLATILITY 模式）

        Returns:
            目标仓位（带符号：正=多, 负=空, 0=空仓）
        """
        if signal.side == SignalSide.HOLD:
            return 0.0

        # 计算原始仓位大小
        raw_size = self._compute_raw_size(signal, current_volatility)

        # 应用方向
        signed_size = raw_size if signal.side == SignalSide.BUY else -raw_size

        # 限制范围
        signed_size = max(-self.config.max_size, min(self.config.max_size, signed_size))
        if abs(signed_size) < self.config.min_size:
            return 0.0

        return float(signed_size)

    # ------------------------------------------------------------------
    # 批量仓位
    # ------------------------------------------------------------------

    def size_batch(
        self,
        signals: List[Signal],
        current_positions: Optional[List[float]] = None,
    ) -> List[float]:
        """批量计算仓位"""
        sizes: List[float] = []
        for i, sig in enumerate(signals):
            cur_pos = current_positions[i] if current_positions else 0.0
            sizes.append(self.size(sig, cur_pos))
        return sizes

    def size_series(
        self,
        signals: List[Signal],
        returns: Optional[pd.Series] = None,
    ) -> pd.Series:
        """
        生成仓位序列

        Args:
            signals: 信号列表
            returns: 收益率序列（VOLATILITY 模式用）

        Returns:
            仓位序列（带符号）
        """
        sizes: List[float] = []
        for i, sig in enumerate(signals):
            cur_vol = None
            if returns is not None and self.config.mode == SizingMode.VOLATILITY:
                cur_vol = self._compute_volatility(returns.iloc[:i+1])
            sizes.append(self.size(sig, current_volatility=cur_vol))
        return pd.Series(sizes, dtype=float)

    # ------------------------------------------------------------------
    # 内部：原始仓位计算
    # ------------------------------------------------------------------

    def _compute_raw_size(
        self,
        signal: Signal,
        current_volatility: Optional[float] = None,
    ) -> float:
        """根据模式计算原始仓位"""
        mode = self.config.mode

        if mode == SizingMode.FIXED:
            return self.config.base_size

        if mode == SizingMode.CONFIDENCE:
            # score * scale，限制在 [min, max]
            size = signal.score * self.config.confidence_scale
            return max(self.config.min_size, min(self.config.max_size, size))

        if mode == SizingMode.VOLATILITY:
            # 目标波动率 / 实际波动率 × base_size
            vol = current_volatility or self._estimate_volatility()
            if vol <= 0:
                return self.config.base_size
            size = (self.config.target_volatility / vol) * self.config.base_size
            return max(self.config.min_size, min(self.config.max_size, size))

        if mode == SizingMode.KELLY:
            # 凯利公式：f = (p*b - q) / b
            # p = 胜率, q = 1-p, b = 盈亏比
            p = self.config.win_rate
            b = self.config.win_loss_ratio
            q = 1.0 - p
            kelly = (p * b - q) / b if b > 0 else 0.0
            # 半凯利 + 置信度调整
            size = kelly * self.config.kelly_fraction * (0.5 + 0.5 * signal.score)
            return max(self.config.min_size, min(self.config.max_size, size))

        # 默认：置信度
        size = signal.score * self.config.confidence_scale
        return max(self.config.min_size, min(self.config.max_size, size))

    def _compute_volatility(self, returns: pd.Series) -> float:
        """计算波动率"""
        if len(returns) < 2:
            return self.config.target_volatility
        window = returns.tail(self.config.vol_lookback)
        if len(window) < 2:
            return self.config.target_volatility
        # 年化波动率（假设日频）
        return float(window.std() * np.sqrt(252))

    def _estimate_volatility(self) -> float:
        """从历史估算波动率"""
        if len(self._returns_history) < 2:
            return self.config.target_volatility
        arr = np.array(self._returns_history[-self.config.vol_lookback:])
        return float(arr.std() * np.sqrt(252))


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def compute_position_stats(positions: pd.Series) -> Dict[str, Any]:
    """仓位统计"""
    if positions.empty:
        return {"total": 0, "long": 0, "short": 0, "flat": 0, "avg_size": 0.0}
    longs = int((positions > 0).sum())
    shorts = int((positions < 0).sum())
    flats = int((positions == 0).sum())
    return {
        "total": len(positions),
        "long": longs,
        "short": shorts,
        "flat": flats,
        "avg_size": float(positions.abs().mean()),
        "max_size": float(positions.abs().max()),
    }
