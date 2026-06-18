"""
Risk Overlay — 风控层

ML Lab M5 第四部分：ML 模型不能直接控制风险，需要独立风控层

  统一处理：
    - 最大仓位限制
    - 最大回撤保护
    - 单品种限制
    - 相关性限制
    - 每日亏损限制

  例如：
    模型想：BTC 100%
    风控允许：BTC 30%
    最终：30%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.strategy.risk_overlay")


# ------------------------------------------------------------------
# 风控配置
# ------------------------------------------------------------------

@dataclass
class RiskConfig:
    """风控配置"""
    # 仓位限制
    max_position: float = 0.3           # 单品种最大仓位 30%
    max_portfolio: float = 1.0          # 总仓位上限 100%
    max_leverage: float = 1.0           # 最大杠杆

    # 回撤保护
    max_drawdown: float = 0.20          # 最大回撤 20%，触发后降仓
    drawdown_cutoff: float = 0.5        # 回撤触发后的仓位系数

    # 每日亏损
    max_daily_loss: float = 0.05        # 单日最大亏损 5%，触发后平仓

    # 单品种限制
    max_symbols: int = 10               # 最大持仓品种数
    min_position: float = 0.0           # 最小持仓

    # 相关性限制（简化版）
    max_correlation: float = 0.7        # 单品种间最大相关性

    # 滑动平均平滑
    position_smoothing: float = 0.0     # 0=不平滑, 0.5=半平滑, 1=完全平滑

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_position": self.max_position,
            "max_portfolio": self.max_portfolio,
            "max_leverage": self.max_leverage,
            "max_drawdown": self.max_drawdown,
            "drawdown_cutoff": self.drawdown_cutoff,
            "max_daily_loss": self.max_daily_loss,
            "max_symbols": self.max_symbols,
            "min_position": self.min_position,
            "max_correlation": self.max_correlation,
            "position_smoothing": self.position_smoothing,
        }


# ------------------------------------------------------------------
# 风控状态
# ------------------------------------------------------------------

@dataclass
class RiskState:
    """风控运行时状态"""
    current_drawdown: float = 0.0       # 当前回撤
    peak_equity: float = 1.0            # 历史峰值权益
    daily_pnl: float = 0.0              # 当日盈亏
    daily_pnl_reset_day: str = ""       # 上次重置日期
    positions: Dict[str, float] = field(default_factory=dict)  # symbol → size
    is_drawdown_breach: bool = False    # 是否触发回撤限制
    is_daily_loss_breach: bool = False  # 是否触发日亏限制

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_drawdown": self.current_drawdown,
            "peak_equity": self.peak_equity,
            "daily_pnl": self.daily_pnl,
            "positions": self.positions,
            "is_drawdown_breach": self.is_drawdown_breach,
            "is_daily_loss_breach": self.is_daily_loss_breach,
        }


# ------------------------------------------------------------------
# RiskOverlay
# ------------------------------------------------------------------

class RiskOverlay:
    """
    风控层

    用法：
        risk = RiskOverlay(config=RiskConfig(max_position=0.3))
        risk.update_equity(new_equity=1.05)

        # 单品种风控
        approved = risk.apply(symbol="BTC", target_size=1.0)
        # → 0.3 (被限制)

        # 组合风控
        approved = risk.apply_portfolio({
            "BTC": 0.5, "ETH": 0.4, "SOL": 0.3
        })
    """

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self.config = config or RiskConfig()
        self.state = RiskState()

    def set_config(self, config: RiskConfig) -> None:
        self.config = config

    def reset(self) -> None:
        """重置状态"""
        self.state = RiskState()

    # ------------------------------------------------------------------
    # 权益更新
    # ------------------------------------------------------------------

    def update_equity(self, new_equity: float, current_date: str = "") -> None:
        """更新权益曲线，计算回撤"""
        # 更新峰值
        if new_equity > self.state.peak_equity:
            self.state.peak_equity = new_equity

        # 计算回撤
        if self.state.peak_equity > 0:
            self.state.current_drawdown = max(
                0.0,
                (self.state.peak_equity - new_equity) / self.state.peak_equity,
            )

        # 检查回撤限制
        self.state.is_drawdown_breach = (
            self.state.current_drawdown >= self.config.max_drawdown
        )

        # 日亏重置
        if current_date and current_date != self.state.daily_pnl_reset_day:
            self.state.daily_pnl = 0.0
            self.state.daily_pnl_reset_day = current_date
            self.state.is_daily_loss_breach = False

    def record_pnl(self, pnl: float) -> None:
        """记录盈亏"""
        self.state.daily_pnl += pnl
        if self.state.daily_pnl < -self.config.max_daily_loss:
            self.state.is_daily_loss_breach = True

    # ------------------------------------------------------------------
    # 单品种风控
    # ------------------------------------------------------------------

    def apply(
        self,
        symbol: str,
        target_size: float,
        current_date: str = "",
    ) -> float:
        """
        应用风控到目标仓位

        Args:
            symbol: 标的
            target_size: 目标仓位（带符号）
            current_date: 当前日期

        Returns:
            风控后的仓位
        """
        if target_size == 0:
            self.state.positions[symbol] = 0.0
            return 0.0

        # 1. 日亏限制触发 → 强制平仓
        if self.state.is_daily_loss_breach:
            logger.warning(
                f"RiskOverlay: daily loss breach, force flat for {symbol}"
            )
            self.state.positions[symbol] = 0.0
            return 0.0

        # 2. 回撤限制触发 → 降仓
        size = target_size
        if self.state.is_drawdown_breach:
            size = target_size * self.config.drawdown_cutoff
            logger.info(
                f"RiskOverlay: drawdown breach, reduce {symbol} "
                f"{target_size:.2f} → {size:.2f}"
            )

        # 3. 单品种仓位限制
        abs_size = abs(size)
        if abs_size > self.config.max_position:
            size = np.sign(size) * self.config.max_position

        # 4. 最小仓位过滤
        if abs(size) < self.config.min_position:
            size = 0.0

        # 5. 平滑
        if self.config.position_smoothing > 0:
            old_pos = self.state.positions.get(symbol, 0.0)
            alpha = self.config.position_smoothing
            size = old_pos * alpha + size * (1.0 - alpha)

        # 更新状态
        self.state.positions[symbol] = size
        return float(size)

    # ------------------------------------------------------------------
    # 组合风控
    # ------------------------------------------------------------------

    def apply_portfolio(
        self,
        target_positions: Dict[str, float],
        current_date: str = "",
    ) -> Dict[str, float]:
        """
        应用组合风控

        Args:
            target_positions: {symbol: target_size}

        Returns:
            风控后的 {symbol: approved_size}
        """
        # 单品种逐个应用
        approved: Dict[str, float] = {}
        for sym, size in target_positions.items():
            approved[sym] = self.apply(sym, size, current_date)

        # 组合总仓位限制
        total = sum(abs(v) for v in approved.values())
        if total > self.config.max_portfolio:
            scale = self.config.max_portfolio / total if total > 0 else 0.0
            approved = {k: v * scale for k, v in approved.items()}
            logger.info(
                f"RiskOverlay: portfolio cap, scale={scale:.2f}"
            )

        # 品种数限制
        active = {k: v for k, v in approved.items() if abs(v) > 0}
        if len(active) > self.config.max_symbols:
            # 按仓位绝对值排序，保留前 N
            sorted_items = sorted(
                active.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )
            keep = set(k for k, _ in sorted_items[:self.config.max_symbols])
            approved = {k: (v if k in keep else 0.0) for k, v in approved.items()}

        # 更新状态
        self.state.positions = approved.copy()
        return approved

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """获取风控状态"""
        return {
            "config": self.config.to_dict(),
            "state": self.state.to_dict(),
            "total_exposure": sum(abs(v) for v in self.state.positions.values()),
            "n_positions": sum(1 for v in self.state.positions.values() if abs(v) > 0),
        }

    def is_safe(self) -> bool:
        """是否处于安全状态（无任何 breach）"""
        return not (self.state.is_drawdown_breach or self.state.is_daily_loss_breach)
