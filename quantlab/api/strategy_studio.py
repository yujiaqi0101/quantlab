"""
Strategy Studio API — 策略工作室 REST API

端点：
  POST /api/strategy-studio/compose       装配策略
  POST /api/strategy-studio/validate      验证策略
  POST /api/strategy-studio/run           运行回测
  GET  /api/strategy-studio/strategies    策略列表
  GET  /api/strategy-studio/strategies/{name}/{version}  策略详情
  GET  /api/strategy-studio/dependencies/{name}/{version}  依赖图
  GET  /api/strategy-studio/packages/{type}  列出某类型 Package
"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..asset_package.base import PackageType, PackageStatus
from ..asset_package.registry import get_package_registry, register_package_class
from ..asset_package.types import (
    TrainedModel, LinearModel, TreeModel, EnsembleModel,
    ModelFramework, ModelTask,
    ThresholdSignal, ProbabilitySignal, TrendSignal, RankingSignal,
    FixedSizing, ConfidenceSizing, VolatilitySizing, KellySizing,
    MaxPositionRisk, StopLossRisk, TakeProfitRisk, MaxDrawdownRisk,
    PaperExecution, BinanceExecution, ReplayExecution, BacktestExecution,
    StandardObserve, HFObserveProfile,
    StrategyPackage,
)
from ..strategy_studio.composer import StrategyComposer, ComposeRequest
from ..strategy_studio.resolver import DependencyResolver
from ..strategy_studio.runtime import StrategyRuntime, Bar
from ..strategy_studio.validator import StrategyValidator

logger = logging.getLogger("quantlab.api.strategy_studio")


# ==================================================================
# 注册所有 Package 类
# ==================================================================

def _register_all_package_classes() -> None:
    """注册所有 Package 类型对应的类（供 Registry 反序列化）"""
    register_package_class(PackageType.MODEL, TrainedModel)
    register_package_class(PackageType.SIGNAL, ThresholdSignal)
    register_package_class(PackageType.POSITION, FixedSizing)
    register_package_class(PackageType.RISK, MaxPositionRisk)
    register_package_class(PackageType.EXECUTION, PaperExecution)
    register_package_class(PackageType.OBSERVE, StandardObserve)
    register_package_class(PackageType.STRATEGY, StrategyPackage)


_register_all_package_classes()


# ==================================================================
# 预置默认 Package（首次启动时自动写入 storage，让下拉框有数据可选）
# ==================================================================

def _seed_default_packages() -> None:
    """首次启动时预置默认 Package 模板"""
    from ..asset_package.storage import get_package_storage
    storage = get_package_storage()
    registry = get_package_registry()
    need_seed_templates = False
    try:
        existing = storage.list(PackageType.MODEL)
        if not existing:
            need_seed_templates = True
    except Exception:
        need_seed_templates = True

    defaults = []
    if need_seed_templates:
        # ---- Model 模板 ----
        defaults.append(TrainedModel(
            name="LGBM_Momentum",
            version="1.0.0",
            description="LightGBM 动量因子模型（示例模板）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["lightgbm", "momentum", "example"],
            framework=ModelFramework.LIGHTGBM,
            task=ModelTask.REGRESSION,
            model_id="example-lgbm-momentum-v1",
            features=["rsi", "macd", "vol_ratio", "mom_5", "mom_20"],
            label="ret_5d",
            hyperparams={"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05},
        ))
        defaults.append(TrainedModel(
            name="XGB_Trend",
            version="1.0.0",
            description="XGBoost 趋势分类模型（示例模板）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["xgboost", "trend", "classification"],
            framework=ModelFramework.XGBOOST,
            task=ModelTask.CLASSIFICATION,
            model_id="example-xgb-trend-v1",
            features=["sma_cross", "adx", "bb_position", "vol_regime"],
            label="trend_label",
            hyperparams={"n_estimators": 300, "max_depth": 5, "learning_rate": 0.03},
        ))
        defaults.append(LinearModel(
            name="Linear_Baseline",
            version="1.0.0",
            description="Ridge 回归基线模型",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["sklearn", "linear", "baseline"],
            task=ModelTask.REGRESSION,
            model_id="example-linear-baseline-v1",
            features=["rsi", "macd", "vol_ratio"],
            label="ret_5d",
            linear_type="ridge",
            alpha=1.0,
        ))
        defaults.append(TreeModel(
            name="Tree_Volatility",
            version="1.0.0",
            description="LightGBM 波动率预测树模型模板",
            status=PackageStatus.DRAFT,
            created_by="system",
            tags=["lightgbm", "volatility"],
            framework=ModelFramework.LIGHTGBM,
            task=ModelTask.REGRESSION,
            features=["realized_vol", "iv", "hv_ratio"],
            label="vol_5d",
            tree_type="lightgbm",
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
        ))

        # ---- Signal 模板 ----
        defaults.append(ThresholdSignal(
            name="Threshold_Default",
            version="1.0.0",
            description="默认阈值信号（回归模型：pred > 2% 做多，< -2% 做空）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["threshold", "default"],
            long_threshold=0.02,
            short_threshold=-0.02,
            use_short=True,
        ))
        defaults.append(ProbabilitySignal(
            name="Probability_Default",
            version="1.0.0",
            description="概率信号（分类模型：prob > 0.72 做多，< 0.28 做空）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["probability", "classification"],
            buy_threshold=0.72,
            sell_threshold=0.28,
            use_short=True,
        ))
        defaults.append(TrendSignal(
            name="MA_Cross",
            version="1.0.0",
            description="均线交叉趋势信号（5/20 MA）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["trend", "ma"],
            fast_window=5,
            slow_window=20,
            use_short=True,
        ))
        defaults.append(RankingSignal(
            name="Rank_Top20",
            version="1.0.0",
            description="横截面排序信号（前20%做多，后20%做空）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["ranking", "cross-sectional"],
            top_pct=0.2,
            bottom_pct=0.2,
            use_short=True,
        ))

        # ---- Position 模板 ----
        defaults.append(FixedSizing(
            name="Fixed_EqualWeight",
            version="1.0.0",
            description="固定仓位（每信号20%，上限100%）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["fixed", "equal-weight"],
            base_size=0.2,
            max_size=1.0,
        ))
        defaults.append(KellySizing(
            name="Kelly_Half",
            version="1.0.0",
            description="半凯利仓位（0.5x Kelly，胜率55%，盈亏比1.5）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["kelly", "dynamic"],
            kelly_fraction=0.5,
            win_rate=0.55,
            win_loss_ratio=1.5,
            max_size=0.3,
        ))

        # ---- Risk 模板 ----
        defaults.append(MaxPositionRisk(
            name="Risk_Default",
            version="1.0.0",
            description="默认风控（单品种30%上限，总仓位100%）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["default"],
            max_position=0.3,
            max_portfolio=1.0,
        ))
        defaults.append(StopLossRisk(
            name="StopLoss_8pct",
            version="1.0.0",
            description="8% 固定止损",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["stop-loss"],
            stop_loss_pct=0.08,
            trailing=False,
        ))

        # ---- Execution 模板 ----
        defaults.append(PaperExecution(
            name="Paper_Default",
            version="1.0.0",
            description="默认模拟执行（纸面交易，初始资金10万）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["paper", "simulation"],
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage_rate=0.001,
        ))
        defaults.append(BacktestExecution(
            name="Backtest_Default",
            version="1.0.0",
            description="回测执行配置（初始资金10万）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["backtest"],
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
        ))

        # ---- Observe 模板 ----
        defaults.append(StandardObserve(
            name="Observe_Default",
            version="1.0.0",
            description="标准观察配置（收益/回撤/Sharpe/仓位等核心指标）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["default", "metrics"],
            metrics=[
                "daily_return", "cumulative_return", "drawdown",
                "sharpe_ratio", "win_rate", "position_summary",
            ],
        ))

        for pkg in defaults:
            try:
                registry.register(pkg)
            except Exception as e:
                logger.debug(f"Skip seeding {pkg.id}: {e}")

    # ---- 默认演示策略（独立检查，总是确保存在）----
    demo_strategies = [
        StrategyPackage(
            name="Demo_CrossSection",
            version="1.0.0",
            description="演示策略：横截面动量排序 + 凯利仓位（多标的回测）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["demo", "cross-sectional", "momentum"],
            family="Momentum",
            model_ref="ref://Linear_Baseline@1.0.0",
            signal_ref="ref://Rank_Top20@1.0.0",
            position_ref="ref://Kelly_Half@1.0.0",
            risk_ref="ref://Risk_Default@1.0.0",
            execution_ref="ref://Backtest_Default@1.0.0",
            observe_ref="ref://Observe_Default@1.0.0",
        ),
        StrategyPackage(
            name="Demo_TrendSingle",
            version="1.0.0",
            description="演示策略：均线趋势 + 固定等权（单标的合成数据回测）",
            status=PackageStatus.ACTIVE,
            created_by="system",
            tags=["demo", "trend", "single"],
            family="Trend",
            model_ref="ref://LGBM_Momentum@1.0.0",
            signal_ref="ref://Threshold_Default@1.0.0",
            position_ref="ref://Fixed_EqualWeight@1.0.0",
            risk_ref="ref://Risk_Default@1.0.0",
            execution_ref="ref://Backtest_Default@1.0.0",
            observe_ref="ref://Observe_Default@1.0.0",
        ),
    ]
    demo_count = 0
    for strat in demo_strategies:
        try:
            if not storage.exists(PackageType.STRATEGY, strat.name, strat.version):
                registry.register(strat)
                demo_count += 1
        except Exception as e:
            logger.debug(f"Skip seeding strategy {strat.id}: {e}")

    seeded = len(defaults) + demo_count
    if seeded > 0:
        logger.info(f"Seeded {seeded} default packages to storage")


_seed_default_packages()


# ==================================================================
# 请求/响应模型
# ==================================================================

class ComposeRequestBody(BaseModel):
    name: str
    family: str = ""
    version: str = "1.0"
    description: str = ""
    model_ref: str
    signal_ref: str
    position_ref: str
    risk_ref: str
    execution_ref: str
    observe_ref: str
    auto_validate: bool = True


class ValidateRequestBody(BaseModel):
    name: str
    version: str
    smoke_test_bars: int = 100


class RunRequestBody(BaseModel):
    name: str
    version: str
    dataset_id: str = ""           # 数据集ID，优先于symbol/synthetic
    symbol: str = "BTCUSDT"        # 合成数据时使用
    bars: int = 500                # 合成数据K线数量
    initial_capital: float = 100000.0
    seed: int = 42
    max_symbols: int = 30          # 多标的回测时最多包含的标的数（按数据集中顺序）
    start_date: str = ""           # 回测起始日期（可选）
    end_date: str = ""             # 回测结束日期（可选）


def _generate_synthetic_bars(symbol: str, n_bars: int, seed: int = 42,
                             start_price: float = 100.0) -> List[Bar]:
    """生成合成K线数据（几何布朗运动 + 均值回归 + 趋势切换）"""
    rng = random.Random(seed)
    bars: List[Bar] = []
    price = start_price
    base_date = datetime(2025, 1, 1)

    regime = 0
    regime_length = rng.randint(20, 60)
    drift = 0.0002

    for i in range(n_bars):
        regime_length -= 1
        if regime_length <= 0:
            regime = rng.choice([-1, 0, 1])
            regime_length = rng.randint(20, 80)
            drift = regime * rng.uniform(0.0001, 0.0008)

        volatility = 0.015
        daily_ret = drift + rng.gauss(0, volatility)
        price = price * math.exp(daily_ret)

        high_offset = abs(rng.gauss(0, volatility * 0.5))
        low_offset = abs(rng.gauss(0, volatility * 0.5))
        open_noise = rng.gauss(0, volatility * 0.3)

        close = price
        open_price = close * math.exp(-open_noise)
        high = max(open_price, close) * (1 + high_offset)
        low = min(open_price, close) * (1 - low_offset)
        volume = rng.uniform(1000, 50000) * (1 + abs(daily_ret) * 10)

        ts = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        bars.append(Bar(
            timestamp=ts,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=round(volume, 0),
            symbol=symbol,
        ))

    return bars


# ==================================================================
# Router
# ==================================================================

router = APIRouter(prefix="/api/v1/strategy-studio", tags=["Strategy Studio"])


@router.post("/compose")
async def compose_strategy(req: ComposeRequestBody):
    """装配策略"""
    composer = StrategyComposer()
    request = ComposeRequest(
        name=req.name,
        family=req.family,
        version=req.version,
        description=req.description,
        model_ref=req.model_ref,
        signal_ref=req.signal_ref,
        position_ref=req.position_ref,
        risk_ref=req.risk_ref,
        execution_ref=req.execution_ref,
        observe_ref=req.observe_ref,
        auto_validate=req.auto_validate,
    )
    result = composer.compose(request)
    return result.to_dict()


@router.post("/validate")
async def validate_strategy(req: ValidateRequestBody):
    """验证策略"""
    registry = get_package_registry()
    strategy = registry.get(PackageType.STRATEGY, req.name, req.version)
    if strategy is None:
        raise HTTPException(404, f"Strategy not found: {req.name}@{req.version}")

    validator = StrategyValidator(registry=registry)
    report = validator.validate(strategy, smoke_test_bars=req.smoke_test_bars)
    return report.to_dict()


@router.post("/run")
async def run_strategy(req: RunRequestBody):
    """运行策略回测

    数据源优先级：
    1. dataset_id 指定 → 从 Dataset 加载真实数据（支持多标的截面回测）
    2. 无 dataset_id → 生成合成K线（单标的）
    """
    registry = get_package_registry()
    strategy = registry.get(PackageType.STRATEGY, req.name, req.version)
    if strategy is None:
        raise HTTPException(404, f"Strategy not found: {req.name}@{req.version}")

    try:
        data_source = "synthetic"
        symbol_used = req.symbol
        symbols_traded = 0
        dataset_name = ""
        df = None
        bars = None

        if req.dataset_id:
            from ..ml.dataset import get_dataset_manager
            ds_mgr = get_dataset_manager()
            ds = ds_mgr.get_dataset(req.dataset_id)
            if ds is None:
                raise HTTPException(404, f"Dataset not found: {req.dataset_id}")

            dataset_name = ds.name
            data_source = f"dataset:{ds.name}"

            loaded_df = ds.get_data()
            if loaded_df is None:
                loaded = ds_mgr.load_dataset_data(req.dataset_id)
                if loaded:
                    loaded_df = ds.get_data()
            if loaded_df is None or len(loaded_df) == 0:
                raise HTTPException(400, f"Dataset {req.dataset_id} has no data loaded")

            df = loaded_df.copy()

            if req.start_date:
                df = df[df.index >= req.start_date]
            if req.end_date:
                df = df[df.index <= req.end_date]

            if "symbol" in df.columns and req.max_symbols > 0:
                all_syms = sorted(df["symbol"].unique().tolist())
                if len(all_syms) > req.max_symbols:
                    selected = all_syms[:req.max_symbols]
                    df = df[df["symbol"].isin(selected)]
                    symbol_used = f"{len(selected)} symbols"
                else:
                    symbol_used = f"{len(all_syms)} symbols"
                symbols_traded = len(all_syms[:req.max_symbols])
            elif "symbol" not in df.columns and len(df) > 0:
                df["symbol"] = req.symbol
                symbol_used = req.symbol
                symbols_traded = 1

            runtime = StrategyRuntime(strategy, registry=registry)
            result = runtime.run(df, initial_capital=req.initial_capital)
        else:
            bars = _generate_synthetic_bars(
                symbol=req.symbol,
                n_bars=req.bars,
                seed=req.seed,
            )
            runtime = StrategyRuntime(strategy, registry=registry)
            result = runtime.run(bars, initial_capital=req.initial_capital)
            symbols_traded = 1

        resp = {
            "ok": len(result.errors) == 0,
            "strategy_id": result.strategy_id,
            "symbol": symbol_used,
            "dataset_id": req.dataset_id,
            "dataset_name": dataset_name,
            "bars": result.bars_processed,
            "symbols_traded": result.symbols_traded,
            "initial_capital": req.initial_capital,
            "data_source": data_source,
            "metrics": result.metrics,
            "equity_curve": result.equity_curve,
            "orders": result.orders[-200:] if len(result.orders) > 200 else result.orders,
            "total_orders": result.metrics.get("total_orders", len(result.orders)),
            "positions_history": result.positions_history,
            "errors": result.errors,
        }
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Strategy run failed: {e}")
        raise HTTPException(500, f"Strategy run failed: {str(e)}")


@router.get("/strategies")
async def list_strategies():
    """策略列表"""
    registry = get_package_registry()
    strategies = registry.list(PackageType.STRATEGY)
    return {
        "strategies": [s.to_manifest() for s in strategies if s is not None],
        "count": len(strategies),
    }


@router.get("/strategies/{name}/{version}")
async def get_strategy(name: str, version: str):
    """策略详情"""
    registry = get_package_registry()
    strategy = registry.get(PackageType.STRATEGY, name, version)
    if strategy is None:
        raise HTTPException(404, f"Strategy not found: {name}@{version}")
    return strategy.to_manifest()


@router.get("/dependencies/{name}/{version}")
async def get_dependencies(name: str, version: str):
    """获取策略依赖图"""
    registry = get_package_registry()
    strategy = registry.get(PackageType.STRATEGY, name, version)
    if strategy is None:
        raise HTTPException(404, f"Strategy not found: {name}@{version}")

    resolver = DependencyResolver(registry=registry)
    graph = resolver.resolve(strategy)
    return graph.to_dict()


@router.get("/packages/{pkg_type}")
async def list_packages(pkg_type: str):
    """列出某类型的所有 Package"""
    try:
        pt = PackageType(pkg_type.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid package type: {pkg_type}")

    registry = get_package_registry()
    packages = registry.list(pt)
    return {
        "packages": [p.to_manifest() for p in packages if p is not None],
        "count": len(packages),
        "type": pt.value,
    }


@router.get("/datasets")
async def list_datasets_for_backtest():
    """获取可用于回测的数据集列表（仅返回有数据的）"""
    from ..ml.dataset import get_dataset_manager
    ds_mgr = get_dataset_manager()
    datasets = []
    for ds in ds_mgr.list_datasets():
        has_data = ds._has_data_flag or ds.get_data() is not None
        if has_data:
            stats = ds.get_stats()
            datasets.append({
                "dataset_id": ds.dataset_id,
                "name": ds.name,
                "symbols_count": len(ds.symbols) if ds.symbols else stats.n_symbols,
                "frequency": ds.frequency,
                "start_date": ds.start_date or (stats.date_range[0] if stats.date_range else ""),
                "end_date": ds.end_date or (stats.date_range[1] if stats.date_range else ""),
                "rows": stats.n_rows,
                "asset_type": ds.asset_type,
                "is_multi_symbol": len(ds.symbols) > 1 if ds.symbols else stats.n_symbols > 1,
            })
    return {"datasets": datasets, "count": len(datasets)}
