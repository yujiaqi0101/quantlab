"""
Fill Engine V2 — 升级版成交引擎

集成：
  1. Order Book Simulation
  2. Matching Engine
  3. Liquidity Model
  4. Slippage Model
  5. Market Impact Model
  6. Latency Model

完整流程：
  order
    ↓
  order book simulation
    ↓
  liquidity matching
    ↓
  partial fill
    ↓
  execution price (with slippage + impact)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.fills.fill_engine import Fill
from ..core.fills.slippage_model import SlippageModel, PercentageSlippage
from .matcher import MatchingEngine, MatchResult
from .orderbook.simulator import OrderBookSimulator
from .orderbook.liquidity_model import LiquidityModel
from .impact.model import MarketImpactEngine, ImpactResult
from .latency.model import LatencySimulator, LatencyProfile
from .cost.model import ExecutionCostModel, TradeCostRecord

logger = logging.getLogger("quantlab.execution.fidelity.fill_engine")


@dataclass
class FillResult:
    """完整成交结果"""
    fill: Fill
    impact: Optional[ImpactResult] = None
    cost: Optional[TradeCostRecord] = None
    match_result: Optional[MatchResult] = None

    def to_dict(self) -> Dict:
        return {
            "fill": self.fill.to_dict(),
            "impact": self.impact.to_dict() if self.impact else None,
            "cost": self.cost.to_dict() if self.cost else None,
            "match": self.match_result.to_dict() if self.match_result else None,
        }


class FillEngineV2:
    """
    升级版成交引擎

    用法：
        engine = FillEngineV2(
            symbol="BTCUSDT",
            slippage_model=PercentageSlippage(rate=0.0005),
        )
        result = engine.process_order(
            order_id="o1",
            side="BUY",
            qty=10,
            order_type="MARKET",
            mid_price=50000,
            volatility=0.02,
            volume=1000000,
        )
    """

    def __init__(
        self,
        symbol: str = "",
        slippage_model: SlippageModel = None,
        book_sim: OrderBookSimulator = None,
        liquidity_model: LiquidityModel = None,
        impact_engine: MarketImpactEngine = None,
        latency_sim: LatencySimulator = None,
        cost_model: ExecutionCostModel = None,
        commission_rate: float = 0.0004,
    ) -> None:
        self.symbol = symbol
        self.slippage_model = slippage_model or PercentageSlippage(rate=0.0005)
        self.book_sim = book_sim or OrderBookSimulator(symbol=symbol or "GENERIC")
        self.liquidity_model = liquidity_model or LiquidityModel()
        self.impact_engine = impact_engine or MarketImpactEngine()
        self.latency_sim = latency_sim or LatencySimulator()
        self.cost_model = cost_model or ExecutionCostModel()
        self.commission_rate = commission_rate

        self.matcher = MatchingEngine(
            book_sim=self.book_sim,
            liquidity=self.liquidity_model,
        )
        self._fills: List[FillResult] = []

    def process_order(
        self,
        order_id: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        mid_price: float = 0,
        price: Optional[float] = None,
        volatility: float = 0.01,
        volume: float = 1000000,
        signal_ts: int = 0,
    ) -> FillResult:
        """处理订单 — 完整成交流程"""
        # 1. 撮合
        match = self.matcher.match(
            order_id=order_id,
            symbol=self.symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            price=price,
            mid_price=mid_price,
            volatility=volatility,
            volume=volume,
        )

        if match.total_filled <= 0:
            logger.info(f"FillEngineV2: order {order_id} no fill (queue={match.queue_position})")
            return FillResult(
                fill=Fill(
                    order_id=order_id,
                    symbol=self.symbol,
                    side=side,
                    fill_qty=0,
                    fill_price=0,
                    timestamp=int(time.time() * 1000),
                ),
                match_result=match,
            )

        # 2. 冲击计算
        impact = self.impact_engine.evaluate(
            order_qty=match.total_filled,
            mid_price=mid_price,
            volume=volume,
            volatility=volatility,
            side=side,
        )

        # 3. 延迟模拟
        latency = self.latency_sim.simulate(signal_ts=signal_ts)

        # 4. 创建 Fill
        fill = Fill(
            id=f"FILL-{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            symbol=self.symbol,
            side=side,
            fill_qty=match.total_filled,
            fill_price=match.avg_fill_price,
            commission=match.total_filled * match.avg_fill_price * self.commission_rate,
            slippage=match.avg_fill_price - mid_price if side == "BUY" else mid_price - match.avg_fill_price,
            timestamp=latency.fill_ts if signal_ts else int(time.time() * 1000),
            local_timestamp=latency.local_recv_ts if signal_ts else int(time.time() * 1000),
            is_partial=not match.is_complete,
            source="paper_v2",
        )

        # 5. 成本计算
        cost = self.cost_model.calculate(
            symbol=self.symbol,
            side=side,
            qty=match.total_filled,
            price=match.avg_fill_price,
            slippage_bps=match.slippage_bps,
            volume=volume,
            volatility=volatility,
        )

        result = FillResult(
            fill=fill,
            impact=impact,
            cost=cost,
            match_result=match,
        )
        self._fills.append(result)

        logger.info(
            f"FillEngineV2: {order_id} filled {match.total_filled}/{qty} "
            f"@ {match.avg_fill_price:.2f} "
            f"(slippage={match.slippage_bps:.1f}bps, "
            f"impact={impact.impact_bps:.1f}bps, "
            f"cost={cost.costs.total_cost:.2f})"
        )

        return result

    def get_all_fills(self) -> List[Fill]:
        return [r.fill for r in self._fills]

    def get_fill_results(self) -> List[FillResult]:
        return list(self._fills)

    def restore(self, fills: List[Fill]) -> None:
        """恢复"""
        for fill in fills:
            self._fills.append(FillResult(fill=fill))
        logger.info(f"FillEngineV2 restored {len(fills)} fills")

    def get_stats(self) -> Dict:
        if not self._fills:
            return {"count": 0}
        total_cost = sum(r.cost.costs.total_cost for r in self._fills if r.cost)
        total_notional = sum(r.fill.fill_qty * r.fill.fill_price for r in self._fills)
        return {
            "count": len(self._fills),
            "total_cost": total_cost,
            "total_notional": total_notional,
            "avg_cost_bps": total_cost / total_notional * 10000 if total_notional > 0 else 0,
            "latency_stats": self.latency_sim.get_stats(),
        }
