"""
Risk Validator — 风控验证器

在订单进入 OMS 之前做预检查
与 RiskEngine 配合，但更轻量
"""

from __future__ import annotations

from typing import Dict, Tuple

from .risk_engine import RiskEngine


class RiskValidator:
    """
    风控验证器 — 包装 RiskEngine

    用法：
        validator = RiskValidator(risk_engine)
        ok, reason = validator.validate_order(
            symbol="BTCUSDT",
            qty=100,
            positions=portfolio.positions,
            equity=portfolio.equity(),
            price=50000,
        )
    """

    def __init__(self, engine: RiskEngine) -> None:
        self._engine = engine

    def validate_order(
        self,
        symbol: str,
        qty: int,
        positions: Dict[str, float],
        equity: float,
        price: float = 0.0,
        daily_pnl: float = 0.0,
    ) -> Tuple[bool, str]:
        return self._engine.check(
            order_qty=qty,
            symbol=symbol,
            current_positions=positions,
            current_equity=equity,
            price=price,
            daily_pnl=daily_pnl,
        )

    def validate_batch(
        self,
        orders: list,
        positions: Dict[str, float],
        equity: float,
        prices: Dict[str, float],
        daily_pnl: float = 0.0,
    ) -> list:
        """批量验证，返回 [(order, ok, reason), ...]"""
        results = []
        for order in orders:
            price = prices.get(order.get("symbol", ""), 0.0)
            ok, reason = self.validate_order(
                symbol=order.get("symbol", ""),
                qty=order.get("quantity", 0),
                positions=positions,
                equity=equity,
                price=price,
                daily_pnl=daily_pnl,
            )
            results.append((order, ok, reason))
        return results
