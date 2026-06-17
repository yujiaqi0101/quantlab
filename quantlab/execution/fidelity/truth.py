"""
Execution Truth Layer — 执行真值层

定义：什么是真实收益？

不是：PnL
而是：PnL - execution cost - slippage - impact

统一输出：True PnL

True PnL = Gross PnL - Total Execution Cost
         = Gross PnL - (fee + slippage + impact + opportunity + funding)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .cost.model import ExecutionCostModel, CostBreakdown, TradeCostRecord

logger = logging.getLogger("quantlab.execution.fidelity.truth")


@dataclass
class TruePnLReport:
    """真实 PnL 报告"""
    timestamp: int
    gross_pnl: float = 0.0          # 毛收益
    fee_cost: float = 0.0           # 手续费
    slippage_cost: float = 0.0      # 滑点
    impact_cost: float = 0.0        # 冲击
    opportunity_cost: float = 0.0   # 机会成本
    funding_cost: float = 0.0       # 资金费率
    total_cost: float = 0.0         # 总成本
    true_pnl: float = 0.0           # 真实收益
    true_pnl_bps: float = 0.0       # 真实收益率（bps）
    cost_drag_bps: float = 0.0      # 成本拖累（bps）

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "gross_pnl": self.gross_pnl,
            "fee_cost": self.fee_cost,
            "slippage_cost": self.slippage_cost,
            "impact_cost": self.impact_cost,
            "opportunity_cost": self.opportunity_cost,
            "funding_cost": self.funding_cost,
            "total_cost": self.total_cost,
            "true_pnl": self.true_pnl,
            "true_pnl_bps": self.true_pnl_bps,
            "cost_drag_bps": self.cost_drag_bps,
        }


@dataclass
class PositionTruePnL:
    """单仓位真实 PnL"""
    symbol: str
    qty: float
    avg_entry: float
    current_price: float
    gross_pnl: float
    total_cost: float
    true_pnl: float
    cost_bps: float

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_entry": self.avg_entry,
            "current_price": self.current_price,
            "gross_pnl": self.gross_pnl,
            "total_cost": self.total_cost,
            "true_pnl": self.true_pnl,
            "cost_bps": self.cost_bps,
        }


class ExecutionTruthLayer:
    """
    执行真值层

    用法：
        truth = ExecutionTruthLayer()
        # 记录交易成本
        truth.record_trade_cost(cost_record)
        # 更新持仓
        truth.update_position("BTCUSDT", qty=0.5, avg_entry=50000)
        # 计算真实 PnL
        truth.update_price("BTCUSDT", 51000)
        report = truth.compute_true_pnl()
        print(f"True PnL: {report.true_pnl}")
    """

    def __init__(self, cost_model: Optional[ExecutionCostModel] = None) -> None:
        self.cost_model = cost_model or ExecutionCostModel()
        self._positions: Dict[str, Dict] = {}     # symbol → {qty, avg_entry, accumulated_cost}
        self._prices: Dict[str, float] = {}       # symbol → current_price
        self._trade_costs: List[TradeCostRecord] = []
        self._reports: List[TruePnLReport] = []

    def record_trade_cost(self, record: TradeCostRecord) -> None:
        """记录交易成本"""
        self._trade_costs.append(record)
        symbol = record.symbol

        # 更新持仓累计成本
        if symbol not in self._positions:
            self._positions[symbol] = {
                "qty": 0,
                "avg_entry": 0,
                "accumulated_cost": 0,
            }

        pos = self._positions[symbol]
        pos["accumulated_cost"] += record.costs.total_cost

        # 更新持仓
        old_qty = pos["qty"]
        old_entry = pos["avg_entry"]
        new_qty = record.qty if record.side == "BUY" else -record.qty
        total_qty = old_qty + new_qty

        if total_qty != 0:
            if (old_qty > 0 and new_qty > 0) or (old_qty < 0 and new_qty < 0):
                # 加仓
                pos["avg_entry"] = (
                    (old_qty * old_entry + new_qty * record.price) / total_qty
                )
            else:
                # 减仓或反转
                if abs(total_qty) < abs(old_qty):
                    pass  # 部分减仓，保持均价
                else:
                    pos["avg_entry"] = record.price

        pos["qty"] = total_qty

    def update_position(self, symbol: str, qty: float, avg_entry: float) -> None:
        """直接更新持仓"""
        if symbol not in self._positions:
            self._positions[symbol] = {
                "qty": 0,
                "avg_entry": 0,
                "accumulated_cost": 0,
            }
        self._positions[symbol]["qty"] = qty
        self._positions[symbol]["avg_entry"] = avg_entry

    def update_price(self, symbol: str, price: float) -> None:
        """更新价格"""
        self._prices[symbol] = price

    def compute_true_pnl(self) -> TruePnLReport:
        """计算真实 PnL"""
        gross_pnl = 0.0
        total_notional = 0.0

        position_reports: List[PositionTruePnL] = []

        for symbol, pos in self._positions.items():
            qty = pos["qty"]
            if qty == 0:
                continue

            avg_entry = pos["avg_entry"]
            current_price = self._prices.get(symbol, avg_entry)
            accumulated_cost = pos["accumulated_cost"]

            # 毛收益
            pos_gross = (current_price - avg_entry) * qty
            gross_pnl += pos_gross

            notional = abs(qty * current_price)
            total_notional += notional

            # 真实收益
            true_pnl = pos_gross - accumulated_cost
            cost_bps = accumulated_cost / notional * 10000 if notional > 0 else 0

            position_reports.append(PositionTruePnL(
                symbol=symbol,
                qty=qty,
                avg_entry=avg_entry,
                current_price=current_price,
                gross_pnl=pos_gross,
                total_cost=accumulated_cost,
                true_pnl=true_pnl,
                cost_bps=cost_bps,
            ))

        # 汇总成本
        total_costs = self.cost_model.get_total_costs()

        # 但 accumulated_cost 已经在 record_trade_cost 中累计
        # 这里用 position 累计的更准确
        total_cost = sum(p["accumulated_cost"] for p in self._positions.values())

        true_pnl = gross_pnl - total_cost
        true_pnl_bps = true_pnl / total_notional * 10000 if total_notional > 0 else 0
        cost_drag_bps = total_cost / total_notional * 10000 if total_notional > 0 else 0

        report = TruePnLReport(
            timestamp=int(time.time() * 1000),
            gross_pnl=gross_pnl,
            fee_cost=total_costs.fee_cost,
            slippage_cost=total_costs.slippage_cost,
            impact_cost=total_costs.impact_cost,
            opportunity_cost=total_costs.opportunity_cost,
            funding_cost=total_costs.funding_cost,
            total_cost=total_cost,
            true_pnl=true_pnl,
            true_pnl_bps=true_pnl_bps,
            cost_drag_bps=cost_drag_bps,
        )

        self._reports.append(report)
        return report

    def get_position_reports(self) -> List[PositionTruePnL]:
        """获取各仓位真实 PnL"""
        reports = []
        for symbol, pos in self._positions.items():
            qty = pos["qty"]
            if qty == 0:
                continue
            avg_entry = pos["avg_entry"]
            current_price = self._prices.get(symbol, avg_entry)
            accumulated_cost = pos["accumulated_cost"]
            gross = (current_price - avg_entry) * qty
            true_pnl = gross - accumulated_cost
            notional = abs(qty * current_price)
            reports.append(PositionTruePnL(
                symbol=symbol,
                qty=qty,
                avg_entry=avg_entry,
                current_price=current_price,
                gross_pnl=gross,
                total_cost=accumulated_cost,
                true_pnl=true_pnl,
                cost_bps=accumulated_cost / notional * 10000 if notional > 0 else 0,
            ))
        return reports

    def get_history(self, limit: int = 100) -> List[Dict]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def get_summary(self) -> Dict:
        """汇总"""
        if not self._reports:
            return {"count": 0}

        latest = self._reports[-1]
        return {
            "latest": latest.to_dict(),
            "positions": [p.to_dict() for p in self.get_position_reports()],
            "trade_count": len(self._trade_costs),
            "report_count": len(self._reports),
        }
