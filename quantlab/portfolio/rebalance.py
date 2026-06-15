"""
Rebalance Engine — V4.6 调仓引擎

职责：
  - 对比当前仓位 vs 目标仓位
  - 生成调仓指令（买入/卖出）
  - 连接 Portfolio → Execution 的桥梁

流程：
  Current Portfolio → Target Portfolio → Rebalance Orders

  例:
    当前: BTC 20%, ETH 30%, cash 50%
    目标: BTC 50%, ETH 25%, SOL 25%
    → SELL ETH 5%, BUY BTC 30%, BUY SOL 25%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import TargetPortfolio

logger = logging.getLogger("quantlab.portfolio.rebalance")


# ------------------------------------------------------------------
# RebalanceOrder
# ------------------------------------------------------------------
@dataclass(slots=True)
class RebalanceOrder:
    """调仓指令"""
    symbol: str
    action: str          # "BUY" / "SELL"
    delta_weight: float  # 权重变化量
    current_weight: float
    target_weight: float

    @property
    def is_buy(self) -> bool:
        return self.action == "BUY"

    @property
    def is_sell(self) -> bool:
        return self.action == "SELL"


# ------------------------------------------------------------------
# RebalanceResult
# ------------------------------------------------------------------
@dataclass
class RebalanceResult:
    """调仓结果"""
    orders: List[RebalanceOrder] = field(default_factory=list)
    total_turnover: float = 0.0     # 总换手率
    n_buys: int = 0
    n_sells: int = 0
    timestamp: Any = None

    def __repr__(self) -> str:
        return (
            f"RebalanceResult(buys={self.n_buys}, sells={self.n_sells}, "
            f"turnover={self.total_turnover:.1%})"
        )


# ------------------------------------------------------------------
# RebalanceEngine
# ------------------------------------------------------------------
class RebalanceEngine:
    """
    调仓引擎

    用法：
        engine = RebalanceEngine(min_weight_change=0.01)
        result = engine.generate(current_weights, target_portfolio)
    """

    def __init__(
        self,
        min_weight_change: float = 0.005,   # 最小调仓阈值（0.5%）
    ) -> None:
        self.min_weight_change = min_weight_change

    def generate(
        self,
        current_weights: Dict[str, float],
        target: TargetPortfolio,
    ) -> RebalanceResult:
        """
        生成调仓指令

        current_weights: {symbol: current_weight}
        target: TargetPortfolio
        """
        all_symbols = set(list(current_weights.keys()) + list(target.positions.keys()))
        orders: List[RebalanceOrder] = []
        total_turnover = 0.0
        n_buys = 0
        n_sells = 0

        for sym in all_symbols:
            cur = current_weights.get(sym, 0.0)
            tgt = target.positions.get(sym, 0.0)
            delta = tgt - cur

            # 忽略微小变化
            if abs(delta) < self.min_weight_change:
                continue

            action = "BUY" if delta > 0 else "SELL"
            orders.append(RebalanceOrder(
                symbol=sym,
                action=action,
                delta_weight=delta,
                current_weight=cur,
                target_weight=tgt,
            ))
            total_turnover += abs(delta)
            if action == "BUY":
                n_buys += 1
            else:
                n_sells += 1

        return RebalanceResult(
            orders=orders,
            total_turnover=total_turnover / 2,  # 单边换手率
            n_buys=n_buys,
            n_sells=n_sells,
            timestamp=target.timestamp,
        )

    def generate_from_series(
        self,
        current_weights: Dict[str, float],
        targets: "pd.Series",
    ) -> List[RebalanceResult]:
        """
        批量生成：对每根 bar 的 TargetPortfolio 生成调仓指令

        targets: Series(index=时间, values=TargetPortfolio)
        """
        results = []
        running_weights = dict(current_weights)

        for idx, target in targets.items():
            result = self.generate(running_weights, target)
            results.append(result)
            # 更新当前仓位为目标仓位
            running_weights = dict(target.positions)

        return results
