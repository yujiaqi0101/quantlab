"""
Execution-Aware Alpha Layer API

提供 Execution-Aware Alpha Layer 的所有 API 端点

10 个模块：
  1. Alpha Realizability Engine
  2. Turnover Pressure Model
  3. Liquidity-Aware Alpha Filter
  4. Execution Sensitivity Test
  5. Latency Fragility Test
  6. Market Impact Backtest
  7. Execution-Adjusted Sharpe
  8. Alpha Survival Filter
  9. Execution-Aware Feature Engineering
  10. Tradeability Score System
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..execution.alpha_aware import (
    # 模块 1
    AlphaMetrics,
    ExecutionConstraints,
    AlphaRealizabilityEngine,
    # 模块 2
    TurnoverPressureModel,
    # 模块 3
    LiquidityMetrics,
    LiquidityAlphaFilter,
    # 模块 4
    SensitivityScenario,
    ExecutionSensitivityTest,
    # 模块 5
    LatencyScenario,
    LatencyFragilityTest,
    # 模块 6
    BacktestTrade,
    MarketImpactBacktest,
    # 模块 7
    ExecutionAdjustedSharpe,
    # 模块 8
    SurvivalInput,
    AlphaSurvivalFilter,
    # 模块 9
    FeatureContext,
    ExecutionAwareFeatureEngine,
    # 模块 10
    TradeabilityScoreSystem,
)

logger = logging.getLogger("quantlab.api.alpha_aware")

router = APIRouter(prefix="/api/v1/alpha-aware", tags=["alpha-aware"])


# ============================================================
# 请求模型
# ============================================================

class RealizabilityRequest(BaseModel):
    ic: float = 0.05
    ic_ir: float = 1.0
    sharpe: float = 1.5
    sortino: float = 2.0
    max_drawdown: float = 0.15
    win_rate: float = 0.55
    avg_return: float = 0.2
    turnover: float = 3.0
    holding_period: float = 5.0
    # 约束
    avg_volume: float = 1_000_000
    avg_spread_bps: float = 2.0
    avg_depth: float = 100.0
    volatility: float = 0.02
    fee_rate: float = 0.0004
    slippage_bps: float = 2.0
    max_participation: float = 0.1


class TurnoverRequest(BaseModel):
    positions: List[float] = Field(default_factory=list)
    capital: float = 1_000_000
    fee_rate: float = 0.0004
    slippage_bps: float = 2.0
    max_sustainable_turnover: float = 5.0


class LiquidityFilterRequest(BaseModel):
    symbol: str = "BTCUSDT"
    avg_volume_24h: float = 1_000_000_000
    avg_spread_bps: float = 2.0
    avg_depth_usd: float = 1_000_000
    volatility: float = 0.02
    impact_cost_bps: float = 1.0
    # 阈值
    min_volume_24h: float = 10_000_000
    max_spread_bps: float = 10.0
    min_depth_usd: float = 100_000
    max_impact_bps: float = 5.0
    max_volatility: float = 0.10


class SensitivityRequest(BaseModel):
    base_sharpe: float = 2.0
    base_return: float = 0.3
    slippage_sensitivity: float = 0.3  # 0~1，每倍滑点衰减比例


class LatencyFragilityRequest(BaseModel):
    base_sharpe: float = 2.0
    alpha_decay_rate: float = 0.001  # 每 ms 衰减率


class ImpactBacktestRequest(BaseModel):
    paper_sharpe: float = 2.0
    paper_return: float = 0.3
    paper_drawdown: float = 0.15
    trades: List[Dict] = Field(default_factory=list)
    impact_coefficient: float = 0.1
    volume: float = 1_000_000
    volatility: float = 0.02
    fee_rate: float = 0.0004


class AdjustedSharpeRequest(BaseModel):
    paper_sharpe: float = 2.0
    annual_return: float = 0.3
    turnover: float = 5.0
    fee_rate: float = 0.0004
    slippage_bps: float = 2.0
    volume: float = 1_000_000
    volatility: float = 0.02
    avg_order_qty: float = 10.0
    opportunity_cost_bps: float = 0.0
    funding_rate_bps: float = 0.0
    holding_days: float = 5.0


class SurvivalRequest(BaseModel):
    ic_mean: float = 0.05
    ic_std: float = 0.03
    ic_ir: float = 1.5
    ic_hit_rate: float = 0.6
    turnover: float = 3.0
    turnover_volatility: float = 1.0
    slippage_sensitivity: float = 0.3
    breakpoint_multiplier: float = 2.5
    liquidity_score: float = 0.8
    volume_score: float = 0.7
    latency_critical_ms: float = 500
    latency_class: str = "MEDIUM"
    real_sharpe: float = 1.2
    paper_sharpe: float = 2.0


class FeatureAdjustmentRequest(BaseModel):
    features: Dict[str, float] = Field(default_factory=dict)
    volume: float = 1_000_000
    spread_bps: float = 2.0
    depth: float = 100.0
    volatility: float = 0.02
    turnover: float = 1.0
    impact_bps: float = 1.0


class TradeabilityRequest(BaseModel):
    # AlphaMetrics
    ic: float = 0.05
    ic_ir: float = 1.5
    sharpe: float = 1.5
    sortino: float = 2.0
    max_drawdown: float = 0.15
    win_rate: float = 0.55
    avg_return: float = 0.2
    turnover: float = 3.0
    holding_period: float = 5.0
    # ExecutionConstraints
    avg_volume: float = 1_000_000
    avg_spread_bps: float = 2.0
    avg_depth: float = 100.0
    volatility: float = 0.02
    fee_rate: float = 0.0004
    slippage_bps: float = 2.0
    max_participation: float = 0.1
    # SurvivalInput
    ic_mean: float = 0.05
    ic_std: float = 0.03
    ic_hit_rate: float = 0.6
    turnover_volatility: float = 1.0
    slippage_sensitivity: float = 0.3
    breakpoint_multiplier: float = 2.5
    liquidity_score: float = 0.8
    volume_score: float = 0.7
    latency_critical_ms: float = 500
    latency_class: str = "MEDIUM"
    real_sharpe: float = 1.2
    paper_sharpe: float = 1.5


# ============================================================
# 模块 1：Alpha Realizability Engine
# ============================================================

@router.post("/realizability/evaluate")
async def evaluate_realizability(req: RealizabilityRequest):
    """评估 Alpha 可实现性"""
    engine = AlphaRealizabilityEngine()
    metrics = AlphaMetrics(
        ic=req.ic, ic_ir=req.ic_ir, sharpe=req.sharpe, sortino=req.sortino,
        max_drawdown=req.max_drawdown, win_rate=req.win_rate,
        avg_return=req.avg_return, turnover=req.turnover,
        holding_period=req.holding_period,
    )
    constraints = ExecutionConstraints(
        avg_volume=req.avg_volume, avg_spread_bps=req.avg_spread_bps,
        avg_depth=req.avg_depth, volatility=req.volatility,
        fee_rate=req.fee_rate, slippage_bps=req.slippage_bps,
        max_participation=req.max_participation,
    )
    report = engine.evaluate(metrics, constraints)
    return report.to_dict()


# ============================================================
# 模块 2：Turnover Pressure Model
# ============================================================

@router.post("/turnover/analyze")
async def analyze_turnover(req: TurnoverRequest):
    """分析换手压力"""
    model = TurnoverPressureModel(
        fee_rate=req.fee_rate,
        slippage_bps=req.slippage_bps,
        max_sustainable_turnover=req.max_sustainable_turnover,
    )
    analysis = model.analyze(req.positions, capital=req.capital)
    suggestions = model.suggest_optimization(analysis)
    return {**analysis.to_dict(), "optimization": suggestions}


# ============================================================
# 模块 3：Liquidity-Aware Alpha Filter
# ============================================================

@router.post("/liquidity/filter")
async def filter_by_liquidity(req: LiquidityFilterRequest):
    """流动性过滤"""
    filt = LiquidityAlphaFilter(
        min_volume_24h=req.min_volume_24h,
        max_spread_bps=req.max_spread_bps,
        min_depth_usd=req.min_depth_usd,
        max_impact_bps=req.max_impact_bps,
        max_volatility=req.max_volatility,
    )
    metrics = LiquidityMetrics(
        symbol=req.symbol,
        avg_volume_24h=req.avg_volume_24h,
        avg_spread_bps=req.avg_spread_bps,
        avg_depth_usd=req.avg_depth_usd,
        volatility=req.volatility,
        impact_cost_bps=req.impact_cost_bps,
    )
    result = filt.check(metrics)
    return result.to_dict()


# ============================================================
# 模块 4：Execution Sensitivity Test
# ============================================================

@router.post("/sensitivity/test")
async def test_sensitivity(req: SensitivityRequest):
    """执行敏感性测试"""
    test = ExecutionSensitivityTest()

    def backtest_fn(mult: float) -> Dict:
        # 模拟：收益随滑点倍数衰减
        sharpe = req.base_sharpe * (1 - req.slippage_sensitivity * (mult - 1))
        total_return = req.base_return * (1 - req.slippage_sensitivity * 0.5 * (mult - 1))
        return {
            "sharpe": max(0, sharpe),
            "total_return": total_return,
            "max_drawdown": 0.15 + 0.05 * mult,
            "win_rate": 0.55 - 0.05 * mult,
            "cost_ratio": 0.1 * mult,
        }

    report = test.run(backtest_fn)
    return report.to_dict()


# ============================================================
# 模块 5：Latency Fragility Test
# ============================================================

@router.post("/latency/fragility")
async def test_latency_fragility(req: LatencyFragilityRequest):
    """延迟脆弱性测试"""
    test = LatencyFragilityTest()

    def backtest_fn(delay_ms: float) -> Dict:
        # 指数衰减
        decay = math.exp(-req.alpha_decay_rate * delay_ms)
        sharpe = req.base_sharpe * decay
        return {
            "sharpe": sharpe,
            "total_return": 0.3 * decay,
            "alpha_decay": 1 - decay,
            "fill_rate": max(0.5, 1 - delay_ms / 10000),
            "slippage_increase_bps": delay_ms * 0.01,
        }

    report = test.run(backtest_fn)
    return report.to_dict()


# ============================================================
# 模块 6：Market Impact Backtest
# ============================================================

@router.post("/impact/backtest")
async def impact_backtest(req: ImpactBacktestRequest):
    """冲击回测"""
    bt = MarketImpactBacktest(
        impact_coefficient=req.impact_coefficient,
        volume=req.volume,
        volatility=req.volatility,
        fee_rate=req.fee_rate,
    )

    trades = [
        BacktestTrade(
            timestamp=t.get("timestamp", 0),
            symbol=t.get("symbol", "BTC"),
            side=t.get("side", "BUY"),
            qty=t.get("qty", 1.0),
            intended_price=t.get("intended_price", 50000),
        )
        for t in req.trades
    ]

    # 如果没有交易，生成示例
    if not trades:
        for i in range(20):
            trades.append(BacktestTrade(
                timestamp=i * 86400,
                symbol="BTC",
                side="BUY" if i % 2 == 0 else "SELL",
                qty=5.0,
                intended_price=50000 + i * 100,
            ))

    result = bt.run(
        trades=trades,
        paper_sharpe=req.paper_sharpe,
        paper_return=req.paper_return,
        paper_drawdown=req.paper_drawdown,
    )
    return result.to_dict()


# ============================================================
# 模块 7：Execution-Adjusted Sharpe
# ============================================================

@router.post("/sharpe/adjusted")
async def adjusted_sharpe(req: AdjustedSharpeRequest):
    """计算执行调整夏普"""
    calc = ExecutionAdjustedSharpe()
    report = calc.calculate(
        paper_sharpe=req.paper_sharpe,
        annual_return=req.annual_return,
        turnover=req.turnover,
        fee_rate=req.fee_rate,
        slippage_bps=req.slippage_bps,
        volume=req.volume,
        volatility=req.volatility,
        avg_order_qty=req.avg_order_qty,
        opportunity_cost_bps=req.opportunity_cost_bps,
        funding_rate_bps=req.funding_rate_bps,
        holding_days=req.holding_days,
    )
    return report.to_dict()


# ============================================================
# 模块 8：Alpha Survival Filter
# ============================================================

@router.post("/survival/evaluate")
async def evaluate_survival(req: SurvivalRequest):
    """评估 Alpha 生存能力"""
    filt = AlphaSurvivalFilter()
    data = SurvivalInput(
        ic_mean=req.ic_mean, ic_std=req.ic_std, ic_ir=req.ic_ir,
        ic_hit_rate=req.ic_hit_rate,
        turnover=req.turnover, turnover_volatility=req.turnover_volatility,
        slippage_sensitivity=req.slippage_sensitivity,
        breakpoint_multiplier=req.breakpoint_multiplier,
        liquidity_score=req.liquidity_score, volume_score=req.volume_score,
        latency_critical_ms=req.latency_critical_ms, latency_class=req.latency_class,
        real_sharpe=req.real_sharpe, paper_sharpe=req.paper_sharpe,
    )
    report = filt.evaluate(data)
    return report.to_dict()


# ============================================================
# 模块 9：Execution-Aware Feature Engineering
# ============================================================

@router.post("/features/adjust")
async def adjust_features(req: FeatureAdjustmentRequest):
    """调整特征（执行感知）"""
    engine = ExecutionAwareFeatureEngine()
    ctx = FeatureContext(
        volume=req.volume, spread_bps=req.spread_bps, depth=req.depth,
        volatility=req.volatility, turnover=req.turnover, impact_bps=req.impact_bps,
    )
    adjusted = engine.adjust_batch(req.features, ctx)
    return {
        "context": ctx.to_dict(),
        "features": {k: v.to_dict() for k, v in adjusted.items()},
    }


# ============================================================
# 模块 10：Tradeability Score System
# ============================================================

@router.post("/tradeability/score")
async def tradeability_score(req: TradeabilityRequest):
    """计算可交易评分"""
    system = TradeabilityScoreSystem()

    metrics = AlphaMetrics(
        ic=req.ic, ic_ir=req.ic_ir, sharpe=req.sharpe, sortino=req.sortino,
        max_drawdown=req.max_drawdown, win_rate=req.win_rate,
        avg_return=req.avg_return, turnover=req.turnover,
        holding_period=req.holding_period,
    )
    constraints = ExecutionConstraints(
        avg_volume=req.avg_volume, avg_spread_bps=req.avg_spread_bps,
        avg_depth=req.avg_depth, volatility=req.volatility,
        fee_rate=req.fee_rate, slippage_bps=req.slippage_bps,
        max_participation=req.max_participation,
    )
    survival = SurvivalInput(
        ic_mean=req.ic_mean, ic_std=req.ic_std, ic_ir=req.ic_ir,
        ic_hit_rate=req.ic_hit_rate,
        turnover=req.turnover, turnover_volatility=req.turnover_volatility,
        slippage_sensitivity=req.slippage_sensitivity,
        breakpoint_multiplier=req.breakpoint_multiplier,
        liquidity_score=req.liquidity_score, volume_score=req.volume_score,
        latency_critical_ms=req.latency_critical_ms, latency_class=req.latency_class,
        real_sharpe=req.real_sharpe, paper_sharpe=req.paper_sharpe,
    )

    report = system.evaluate(metrics, constraints, survival)
    return report.to_dict()


# ============================================================
# 综合评估：一键全流程
# ============================================================

@router.post("/evaluate/all")
async def evaluate_all(req: TradeabilityRequest):
    """一键全流程评估：10 个模块全部运行"""
    result: Dict[str, Any] = {}

    # 模块 1：Realizability
    engine = AlphaRealizabilityEngine()
    metrics = AlphaMetrics(
        ic=req.ic, ic_ir=req.ic_ir, sharpe=req.sharpe, sortino=req.sortino,
        max_drawdown=req.max_drawdown, win_rate=req.win_rate,
        avg_return=req.avg_return, turnover=req.turnover,
        holding_period=req.holding_period,
    )
    constraints = ExecutionConstraints(
        avg_volume=req.avg_volume, avg_spread_bps=req.avg_spread_bps,
        avg_depth=req.avg_depth, volatility=req.volatility,
        fee_rate=req.fee_rate, slippage_bps=req.slippage_bps,
        max_participation=req.max_participation,
    )
    result["realizability"] = engine.evaluate(metrics, constraints).to_dict()

    # 模块 2：Turnover
    turnover_model = TurnoverPressureModel(
        fee_rate=req.fee_rate, slippage_bps=req.slippage_bps,
    )
    # 生成示例持仓序列
    positions = [0.1 * (1 + 0.02 * i) for i in range(20)]
    result["turnover"] = turnover_model.analyze(positions).to_dict()

    # 模块 3：Liquidity Filter
    filt = LiquidityAlphaFilter()
    liq_metrics = LiquidityMetrics(
        symbol="ALPHA",
        avg_volume_24h=req.avg_volume * 252,
        avg_spread_bps=req.avg_spread_bps,
        avg_depth_usd=req.avg_depth * 1000,
        volatility=req.volatility,
        impact_cost_bps=req.slippage_bps,
    )
    result["liquidity_filter"] = filt.check(liq_metrics).to_dict()

    # 模块 4：Sensitivity
    sens_test = ExecutionSensitivityTest()
    def sens_fn(mult: float) -> Dict:
        sharpe = req.sharpe * (1 - 0.3 * (mult - 1))
        return {
            "sharpe": max(0, sharpe),
            "total_return": req.avg_return * (1 - 0.15 * (mult - 1)),
            "max_drawdown": req.max_drawdown + 0.05 * mult,
            "win_rate": req.win_rate - 0.05 * mult,
            "cost_ratio": 0.1 * mult,
        }
    result["sensitivity"] = sens_test.run(sens_fn).to_dict()

    # 模块 5：Latency Fragility
    lat_test = LatencyFragilityTest()
    def lat_fn(delay_ms: float) -> Dict:
        decay = math.exp(-0.001 * delay_ms)
        return {
            "sharpe": req.sharpe * decay,
            "total_return": req.avg_return * decay,
            "alpha_decay": 1 - decay,
            "fill_rate": max(0.5, 1 - delay_ms / 10000),
            "slippage_increase_bps": delay_ms * 0.01,
        }
    result["latency_fragility"] = lat_test.run(lat_fn).to_dict()

    # 模块 6：Impact Backtest
    bt = MarketImpactBacktest(
        volume=req.avg_volume, volatility=req.volatility, fee_rate=req.fee_rate,
    )
    trades = [
        BacktestTrade(timestamp=i * 86400, symbol="ALPHA",
                      side="BUY" if i % 2 == 0 else "SELL",
                      qty=10, intended_price=100)
        for i in range(20)
    ]
    result["impact_backtest"] = bt.run(
        trades, req.sharpe, req.avg_return, req.max_drawdown,
    ).to_dict()

    # 模块 7：Adjusted Sharpe
    adj_calc = ExecutionAdjustedSharpe()
    result["adjusted_sharpe"] = adj_calc.calculate(
        paper_sharpe=req.sharpe, annual_return=req.avg_return,
        turnover=req.turnover, fee_rate=req.fee_rate,
        slippage_bps=req.slippage_bps, volume=req.avg_volume,
        volatility=req.volatility, avg_order_qty=10,
    ).to_dict()

    # 模块 8：Survival
    surv_filt = AlphaSurvivalFilter()
    surv_data = SurvivalInput(
        ic_mean=req.ic_mean, ic_std=req.ic_std, ic_ir=req.ic_ir,
        ic_hit_rate=req.ic_hit_rate,
        turnover=req.turnover, turnover_volatility=req.turnover_volatility,
        slippage_sensitivity=req.slippage_sensitivity,
        breakpoint_multiplier=req.breakpoint_multiplier,
        liquidity_score=req.liquidity_score, volume_score=req.volume_score,
        latency_critical_ms=req.latency_critical_ms, latency_class=req.latency_class,
        real_sharpe=req.real_sharpe, paper_sharpe=req.paper_sharpe,
    )
    result["survival"] = surv_filt.evaluate(surv_data).to_dict()

    # 模块 9：Features
    feat_engine = ExecutionAwareFeatureEngine()
    feat_ctx = FeatureContext(
        volume=req.avg_volume, spread_bps=req.avg_spread_bps,
        depth=req.avg_depth, volatility=req.volatility,
        turnover=req.turnover, impact_bps=req.slippage_bps,
    )
    features = {"rsi": 65, "momentum": 0.05, "mean_reversion": -0.03}
    adjusted = feat_engine.adjust_batch(features, feat_ctx)
    result["features"] = {k: v.to_dict() for k, v in adjusted.items()}

    # 模块 10：Tradeability
    trade_system = TradeabilityScoreSystem()
    result["tradeability"] = trade_system.evaluate(
        metrics, constraints, surv_data,
    ).to_dict()

    # 总结
    result["summary"] = {
        "realizability_verdict": result["realizability"]["verdict"],
        "survival_verdict": result["survival"]["verdict"],
        "tradeability_rank": result["tradeability"]["rank"],
        "tradeability_score": result["tradeability"]["alpha_score"],
        "adjusted_sharpe": result["adjusted_sharpe"]["decomposition"]["real_sharpe"],
        "is_recommended": result["tradeability"]["is_recommended"],
    }

    return result


# ============================================================
# Health
# ============================================================

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "execution-aware-alpha",
        "modules": [
            "alpha_realizability_engine",
            "turnover_pressure_model",
            "liquidity_alpha_filter",
            "execution_sensitivity_test",
            "latency_fragility_test",
            "market_impact_backtest",
            "execution_adjusted_sharpe",
            "alpha_survival_filter",
            "execution_aware_features",
            "tradeability_score_system",
        ],
    }
