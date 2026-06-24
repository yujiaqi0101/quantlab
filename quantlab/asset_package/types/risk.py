"""
Risk Package — 风控包

把风控逻辑从硬编码类升级为可注册、可复用的 Package。

4 种实现：
  - MaxPositionRisk: 单品种仓位上限
  - StopLossRisk: 止损
  - TakeProfitRisk: 止盈
  - MaxDrawdownRisk: 最大回撤保护
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import AssetPackage, PackageType

logger = logging.getLogger("quantlab.asset_package.types.risk")


# ==================================================================
# RiskPackage 基类
# ==================================================================

@dataclass
class RiskPackage(AssetPackage):
    """风控包基类"""
    package_type: PackageType = PackageType.RISK

    def apply(self, positions: Dict[str, float],
              portfolio_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        应用风控规则，返回调整后的仓位

        Args:
            positions: 原始仓位 {symbol: size}
            portfolio_state: 组合状态（如当前回撤、已实现 PnL 等）

        Returns:
            调整后的仓位 {symbol: size}
        """
        raise NotImplementedError("Subclass must implement apply()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })


# ==================================================================
# 1. MaxPositionRisk — 单品种仓位上限
# ==================================================================

@dataclass
class MaxPositionRisk(RiskPackage):
    """单品种仓位上限 + 总仓位上限"""
    max_position: float = 0.3           # 单品种最大仓位 30%
    max_portfolio: float = 1.0          # 总仓位上限 100%

    def to_config(self) -> Dict[str, Any]:
        return {"max_position": self.max_position, "max_portfolio": self.max_portfolio}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.max_position = config.get("max_position", 0.3)
        self.max_portfolio = config.get("max_portfolio", 1.0)

    def apply(self, positions: Dict[str, float],
              portfolio_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        # 1. 单品种上限
        adjusted = {s: max(-self.max_position, min(self.max_position, p))
                    for s, p in positions.items()}
        # 2. 总仓位上限（按比例缩放）
        gross = sum(abs(p) for p in adjusted.values())
        if gross > self.max_portfolio and gross > 0:
            scale = self.max_portfolio / gross
            adjusted = {s: p * scale for s, p in adjusted.items()}
        return adjusted


# ==================================================================
# 2. StopLossRisk — 止损
# ==================================================================

@dataclass
class StopLossRisk(RiskPackage):
    """止损：当某品种亏损超过阈值时清仓"""
    stop_loss_pct: float = 0.08         # 8% 止损
    trailing: bool = False              # 是否追踪止损

    def to_config(self) -> Dict[str, Any]:
        return {"stop_loss_pct": self.stop_loss_pct, "trailing": self.trailing}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.stop_loss_pct = config.get("stop_loss_pct", 0.08)
        self.trailing = config.get("trailing", False)

    def apply(self, positions: Dict[str, float],
              portfolio_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        state = portfolio_state or {}
        unrealized_pnl = state.get("unrealized_pnl", {})
        adjusted = {}
        for symbol, pos in positions.items():
            pnl_pct = unrealized_pnl.get(symbol, 0.0)
            if pnl_pct < -self.stop_loss_pct:
                logger.info(f"StopLoss triggered: {symbol} pnl={pnl_pct:.2%}")
                adjusted[symbol] = 0.0
            else:
                adjusted[symbol] = pos
        return adjusted


# ==================================================================
# 3. TakeProfitRisk — 止盈
# ==================================================================

@dataclass
class TakeProfitRisk(RiskPackage):
    """止盈：当某品种盈利超过阈值时清仓"""
    take_profit_pct: float = 0.20       # 20% 止盈

    def to_config(self) -> Dict[str, Any]:
        return {"take_profit_pct": self.take_profit_pct}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.take_profit_pct = config.get("take_profit_pct", 0.20)

    def apply(self, positions: Dict[str, float],
              portfolio_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        state = portfolio_state or {}
        unrealized_pnl = state.get("unrealized_pnl", {})
        adjusted = {}
        for symbol, pos in positions.items():
            pnl_pct = unrealized_pnl.get(symbol, 0.0)
            if pnl_pct > self.take_profit_pct:
                logger.info(f"TakeProfit triggered: {symbol} pnl={pnl_pct:.2%}")
                adjusted[symbol] = 0.0
            else:
                adjusted[symbol] = pos
        return adjusted


# ==================================================================
# 4. MaxDrawdownRisk — 最大回撤保护
# ==================================================================

@dataclass
class MaxDrawdownRisk(RiskPackage):
    """最大回撤保护：回撤超阈值时降仓"""
    max_drawdown: float = 0.20          # 最大回撤 20%
    drawdown_cutoff: float = 0.5        # 回撤触发后的仓位系数

    def to_config(self) -> Dict[str, Any]:
        return {
            "max_drawdown": self.max_drawdown,
            "drawdown_cutoff": self.drawdown_cutoff,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.max_drawdown = config.get("max_drawdown", 0.20)
        self.drawdown_cutoff = config.get("drawdown_cutoff", 0.5)

    def apply(self, positions: Dict[str, float],
              portfolio_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        state = portfolio_state or {}
        current_drawdown = state.get("current_drawdown", 0.0)
        if current_drawdown > self.max_drawdown:
            logger.warning(f"MaxDrawdown triggered: dd={current_drawdown:.2%}")
            return {s: p * self.drawdown_cutoff for s, p in positions.items()}
        return positions
