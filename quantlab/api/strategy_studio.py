"""
Strategy Studio API — 策略工作室 REST API

端点：
  POST /api/strategy-studio/compose       装配策略
  POST /api/strategy-studio/validate      验证策略
  GET  /api/strategy-studio/strategies    策略列表
  GET  /api/strategy-studio/strategies/{name}/{version}  策略详情
  GET  /api/strategy-studio/dependencies/{name}/{version}  依赖图
  GET  /api/strategy-studio/packages/{type}  列出某类型 Package
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..asset_package.base import PackageType
from ..asset_package.registry import get_package_registry, register_package_class
from ..asset_package.types import (
    ThresholdSignal, ProbabilitySignal, TrendSignal, RankingSignal,
    FixedSizing, ConfidenceSizing, VolatilitySizing, KellySizing,
    MaxPositionRisk, StopLossRisk, TakeProfitRisk, MaxDrawdownRisk,
    PaperExecution, BinanceExecution, ReplayExecution, BacktestExecution,
    StandardObserve, HFObserveProfile,
    StrategyPackage,
)
from ..strategy_studio.composer import StrategyComposer, ComposeRequest
from ..strategy_studio.resolver import DependencyResolver
from ..strategy_studio.validator import StrategyValidator

logger = logging.getLogger("quantlab.api.strategy_studio")


# ==================================================================
# 注册所有 Package 类
# ==================================================================

def _register_all_package_classes() -> None:
    """注册所有 Package 类型对应的类（供 Registry 反序列化）"""
    register_package_class(PackageType.SIGNAL, ThresholdSignal)
    register_package_class(PackageType.POSITION, FixedSizing)
    register_package_class(PackageType.RISK, MaxPositionRisk)
    register_package_class(PackageType.EXECUTION, PaperExecution)
    register_package_class(PackageType.OBSERVE, StandardObserve)
    register_package_class(PackageType.STRATEGY, StrategyPackage)


_register_all_package_classes()


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
