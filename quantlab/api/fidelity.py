"""
Execution Fidelity Layer API

提供 Execution Fidelity Layer 的所有 API 端点
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..execution.fidelity import (
    OrderBookSimulator,
    SquareRootImpactModel,
    MarketImpactEngine,
    LatencySimulator,
    LatencyProfile,
    ExecutionCostModel,
    FillEngineV2,
    FillReconciliationV2,
    DeterministicReplayEngine,
    ReplayEvent,
    ReplayConfig,
    ShadowModeEngine,
    AdaptiveExecutionEngine,
    MarketState,
    ExecutionTruthLayer,
)

logger = logging.getLogger("quantlab.api.fidelity")

router = APIRouter(prefix="/api/v1/fidelity", tags=["fidelity"])


# ============================================================
# Registry — 单例管理
# ============================================================

class FidelityRegistry:
    """Execution Fidelity 组件注册表"""

    def __init__(self) -> None:
        self.fill_engines: Dict[str, FillEngineV2] = {}
        self.impact_engine = MarketImpactEngine()
        self.latency_sim = LatencySimulator()
        self.cost_model = ExecutionCostModel()
        self.reconciliation = FillReconciliationV2()
        self.replay_engine = DeterministicReplayEngine()
        self.shadow_engine = ShadowModeEngine()
        self.adaptive_engine = AdaptiveExecutionEngine()
        self.truth_layer = ExecutionTruthLayer()

    def get_fill_engine(self, symbol: str) -> FillEngineV2:
        if symbol not in self.fill_engines:
            self.fill_engines[symbol] = FillEngineV2(symbol=symbol)
        return self.fill_engines[symbol]

    def summary(self) -> Dict:
        return {
            "fill_engines": list(self.fill_engines.keys()),
            "cost_stats": self.cost_model.get_avg_cost_bps(),
            "latency_stats": self.latency_sim.get_stats(),
            "shadow_summary": self.shadow_engine.get_summary(),
            "adaptive_stats": self.adaptive_engine.get_policy_stats(),
            "truth_summary": self.truth_layer.get_summary(),
            "replay_status": self.replay_engine.get_status(),
        }


_registry = FidelityRegistry()


def get_registry() -> FidelityRegistry:
    return _registry


# ============================================================
# Models
# ============================================================

class OrderBookRequest(BaseModel):
    symbol: str = "BTCUSDT"
    mid_price: float = 50000
    volatility: float = 0.02
    volume: float = 1000000


class ImpactRequest(BaseModel):
    order_qty: float
    mid_price: float
    volume: float
    volatility: float
    side: str = "BUY"
    model: str = "sqrt"   # sqrt / linear / power


class LatencySimulateRequest(BaseModel):
    signal_ts: int = 0
    apply_jitter: bool = True


class CostCalculateRequest(BaseModel):
    symbol: str
    side: str
    qty: float
    price: float
    slippage_bps: float = 0.0
    volume: float = 0
    volatility: float = 0.0
    is_maker: bool = False
    opportunity_cost: float = 0.0
    funding_cost: float = 0.0


class FillOrderRequest(BaseModel):
    order_id: str
    symbol: str
    side: str
    qty: float
    order_type: str = "MARKET"
    mid_price: float = 0
    price: Optional[float] = None
    volatility: float = 0.01
    volume: float = 1000000
    signal_ts: int = 0


class ReconcileFillsRequest(BaseModel):
    paper_fills: List[Dict]
    live_fills: List[Dict]


class ReconcilePositionsRequest(BaseModel):
    local_positions: Dict[str, float]
    exchange_positions: Dict[str, float]


class ReplayLoadRequest(BaseModel):
    events: List[Dict]
    deterministic: bool = True
    random_seed: int = 42


class ShadowFillRequest(BaseModel):
    order_id: str
    symbol: str
    qty: float
    price: float
    timestamp: int = 0


class AdaptivePlanRequest(BaseModel):
    order_id: str
    symbol: str
    side: str
    total_qty: float
    volatility: float = 0.01
    volume: float = 1000000
    spread_bps: float = 2.0
    trend_strength: float = 0.0
    liquidity_score: float = 1.0
    urgency: float = 0.5


class TruthUpdatePriceRequest(BaseModel):
    symbol: str
    price: float


class TruthUpdatePositionRequest(BaseModel):
    symbol: str
    qty: float
    avg_entry: float


# ============================================================
# Endpoints
# ============================================================

@router.get("/status")
async def fidelity_status():
    """Execution Fidelity 系统总览"""
    return _registry.summary()


# --- Order Book ---

@router.post("/orderbook/generate")
async def generate_orderbook(req: OrderBookRequest):
    """生成订单簿快照"""
    sim = OrderBookSimulator(symbol=req.symbol)
    book = sim.generate(
        mid_price=req.mid_price,
        volatility=req.volatility,
        volume=req.volume,
    )
    return book.to_dict()


@router.post("/orderbook/sweep")
async def sweep_orderbook(req: OrderBookRequest, side: str = "BUY", qty: float = 1.0):
    """模拟市价单吃深度"""
    sim = OrderBookSimulator(symbol=req.symbol)
    book = sim.generate(
        mid_price=req.mid_price,
        volatility=req.volatility,
        volume=req.volume,
    )
    impact = sim.estimate_market_impact(book, side, qty)
    return {
        "book": book.to_dict(),
        "sweep_result": impact,
    }


# --- Impact ---

@router.post("/impact/calculate")
async def calculate_impact(req: ImpactRequest):
    """计算市场冲击"""
    models = {
        "sqrt": SquareRootImpactModel(),
        "linear": __import__(
            "quantlab.execution.fidelity.impact.model",
            fromlist=["LinearImpactModel"],
        ).LinearImpactModel(),
        "power": __import__(
            "quantlab.execution.fidelity.impact.model",
            fromlist=["PowerImpactModel"],
        ).PowerImpactModel(),
    }
    model = models.get(req.model, SquareRootImpactModel())
    result = model.calculate(
        order_qty=req.order_qty,
        mid_price=req.mid_price,
        volume=req.volume,
        volatility=req.volatility,
        side=req.side,
    )
    return result.to_dict()


@router.post("/impact/suggest-split")
async def suggest_split(req: ImpactRequest):
    """建议拆单方案"""
    total_qty = req.order_qty
    splits = _registry.impact_engine.suggest_split(
        total_qty=total_qty,
        mid_price=req.mid_price,
        volume=req.volume,
        volatility=req.volatility,
        max_impact_bps=5.0,
    )
    return {
        "total_qty": total_qty,
        "splits": splits,
        "num_slices": len(splits),
    }


# --- Latency ---

@router.post("/latency/simulate")
async def simulate_latency(req: LatencySimulateRequest):
    """模拟延迟"""
    m = _registry.latency_sim.simulate(
        signal_ts=req.signal_ts,
        apply_jitter=req.apply_jitter,
    )
    return m.to_dict()


@router.get("/latency/stats")
async def latency_stats():
    """延迟统计"""
    return _registry.latency_sim.get_stats()


# --- Cost ---

@router.post("/cost/calculate")
async def calculate_cost(req: CostCalculateRequest):
    """计算交易成本"""
    record = _registry.cost_model.calculate(
        symbol=req.symbol,
        side=req.side,
        qty=req.qty,
        price=req.price,
        slippage_bps=req.slippage_bps,
        volume=req.volume,
        volatility=req.volatility,
        is_maker=req.is_maker,
        opportunity_cost=req.opportunity_cost,
        funding_cost=req.funding_cost,
    )
    return record.to_dict()


@router.get("/cost/summary")
async def cost_summary():
    """成本汇总"""
    return {
        "avg_cost_bps": _registry.cost_model.get_avg_cost_bps(),
        "total_costs": _registry.cost_model.get_total_costs().to_dict(),
        "history": _registry.cost_model.get_history(limit=50),
    }


# --- Fill Engine V2 ---

@router.post("/fill/process")
async def process_fill(req: FillOrderRequest):
    """处理订单（Fill Engine V2）"""
    engine = _registry.get_fill_engine(req.symbol)
    result = engine.process_order(
        order_id=req.order_id,
        side=req.side,
        qty=req.qty,
        order_type=req.order_type,
        mid_price=req.mid_price,
        price=req.price,
        volatility=req.volatility,
        volume=req.volume,
        signal_ts=req.signal_ts,
    )
    return result.to_dict()


@router.get("/fill/stats")
async def fill_stats():
    """成交引擎统计"""
    stats = {}
    for symbol, engine in _registry.fill_engines.items():
        stats[symbol] = engine.get_stats()
    return stats


# --- Reconciliation ---

@router.post("/reconciliation/fills")
async def reconcile_fills(req: ReconcileFillsRequest):
    """对账 Paper vs Live fills"""
    report = _registry.reconciliation.reconcile_fills(
        paper_fills=req.paper_fills,
        live_fills=req.live_fills,
    )
    return report.to_dict()


@router.post("/reconciliation/positions")
async def reconcile_positions(req: ReconcilePositionsRequest):
    """对账本地 vs 交易所持仓"""
    report = _registry.reconciliation.reconcile_positions(
        local_positions=req.local_positions,
        exchange_positions=req.exchange_positions,
    )
    return report.to_dict()


@router.get("/reconciliation/history")
async def reconciliation_history():
    """对账历史"""
    return _registry.reconciliation.get_history()


# --- Replay ---

@router.post("/replay/load")
async def replay_load(req: ReplayLoadRequest):
    """加载回放事件"""
    events = [
        ReplayEvent(
            timestamp=e.get("timestamp", 0),
            type=e.get("type", ""),
            data=e.get("data", {}),
            sequence=e.get("sequence", i),
        )
        for i, e in enumerate(req.events)
    ]
    _registry.replay_engine = DeterministicReplayEngine(
        ReplayConfig(deterministic=req.deterministic, random_seed=req.random_seed)
    )
    _registry.replay_engine.load_events(events)
    return {"status": "loaded", "events": len(events)}


@router.post("/replay/play")
async def replay_play():
    """执行回放"""
    result = _registry.replay_engine.play()
    return result


@router.get("/replay/status")
async def replay_status():
    """回放状态"""
    return _registry.replay_engine.get_status()


# --- Shadow Mode ---

@router.post("/shadow/paper-fill")
async def shadow_paper_fill(req: ShadowFillRequest):
    """记录纸面成交"""
    _registry.shadow_engine.record_paper_fill(
        order_id=req.order_id,
        symbol=req.symbol,
        qty=req.qty,
        price=req.price,
        timestamp=req.timestamp,
    )
    return {"status": "recorded"}


@router.post("/shadow/live-fill")
async def shadow_live_fill(req: ShadowFillRequest):
    """记录实盘成交"""
    _registry.shadow_engine.record_live_fill(
        order_id=req.order_id,
        symbol=req.symbol,
        qty=req.qty,
        price=req.price,
        timestamp=req.timestamp,
    )
    return {"status": "recorded"}


@router.post("/shadow/compare/{order_id}")
async def shadow_compare(order_id: str):
    """对比单个订单"""
    comp = _registry.shadow_engine.compare(order_id)
    return comp.to_dict()


@router.get("/shadow/compare-all")
async def shadow_compare_all():
    """对比所有订单"""
    comparisons = _registry.shadow_engine.compare_all()
    return {
        "comparisons": [c.to_dict() for c in comparisons],
        "summary": _registry.shadow_engine.get_summary(),
    }


@router.get("/shadow/alerts")
async def shadow_alerts():
    """影子模式告警"""
    return {"alerts": _registry.shadow_engine.get_alerts()}


# --- Adaptive ---

@router.post("/adaptive/plan")
async def adaptive_plan(req: AdaptivePlanRequest):
    """生成自适应执行计划"""
    market = MarketState(
        volatility=req.volatility,
        volume=req.volume,
        spread_bps=req.spread_bps,
        trend_strength=req.trend_strength,
        liquidity_score=req.liquidity_score,
    )
    plan = _registry.adaptive_engine.plan(
        order_id=req.order_id,
        symbol=req.symbol,
        side=req.side,
        total_qty=req.total_qty,
        market=market,
        urgency=req.urgency,
    )
    return plan.to_dict()


@router.get("/adaptive/plans")
async def adaptive_plans():
    """获取执行计划历史"""
    return {"plans": _registry.adaptive_engine.get_plans()}


@router.get("/adaptive/stats")
async def adaptive_stats():
    """自适应策略统计"""
    return _registry.adaptive_engine.get_policy_stats()


# --- Truth Layer ---

@router.post("/truth/position")
async def truth_update_position(req: TruthUpdatePositionRequest):
    """更新持仓"""
    _registry.truth_layer.update_position(
        symbol=req.symbol,
        qty=req.qty,
        avg_entry=req.avg_entry,
    )
    return {"status": "updated"}


@router.post("/truth/price")
async def truth_update_price(req: TruthUpdatePriceRequest):
    """更新价格"""
    _registry.truth_layer.update_price(req.symbol, req.price)
    return {"status": "updated"}


@router.get("/truth/pnl")
async def truth_pnl():
    """获取 True PnL"""
    report = _registry.truth_layer.compute_true_pnl()
    return {
        "report": report.to_dict(),
        "positions": [p.to_dict() for p in _registry.truth_layer.get_position_reports()],
        "summary": _registry.truth_layer.get_summary(),
    }


@router.get("/truth/history")
async def truth_history():
    """True PnL 历史"""
    return {"history": _registry.truth_layer.get_history()}
