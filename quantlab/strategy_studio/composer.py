"""
StrategyComposer — 策略装配器

职责：
  1. 接收 ComposeRequest（用户选择的各组件 ref）
  2. 创建 StrategyPackage
  3. 调用 DependencyResolver 验证依赖
  4. 保存到 PackageRegistry
  5. 返回 ComposeResult

装配流程：
  ComposeRequest → StrategyPackage → DependencyResolver → Registry → ComposeResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..asset_package.base import PackageType
from ..asset_package.registry import PackageRegistry, get_package_registry
from ..asset_package.types import StrategyPackage, StrategyStatus, ValidationState
from .resolver import DependencyResolver, ValidationResult

logger = logging.getLogger("quantlab.strategy_studio.composer")


# ==================================================================
# ComposeRequest
# ==================================================================

@dataclass
class ComposeRequest:
    """装配请求"""
    name: str                           # 策略名
    family: str = ""                    # 策略族
    version: str = "1.0"                # 版本
    description: str = ""

    # ref 引用
    model_ref: str = ""                # ref://Momentum_LGBM@1.2.0
    signal_ref: str = ""               # ref://ProbabilitySignal@1.0
    position_ref: str = ""             # ref://VolatilitySizing@2.0
    risk_ref: str = ""                 # ref://CryptoBasicRisk@1.1
    execution_ref: str = ""             # ref://PaperExecution@1.0
    observe_ref: str = ""               # ref://StandardObserve@1.0

    # 是否自动验证
    auto_validate: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "version": self.version,
            "description": self.description,
            "model_ref": self.model_ref,
            "signal_ref": self.signal_ref,
            "position_ref": self.position_ref,
            "risk_ref": self.risk_ref,
            "execution_ref": self.execution_ref,
            "observe_ref": self.observe_ref,
            "auto_validate": self.auto_validate,
        }


# ==================================================================
# ComposeResult
# ==================================================================

@dataclass
class ComposeResult:
    """装配结果"""
    success: bool
    strategy_id: str = ""              # name@version
    strategy: Optional[StrategyPackage] = None
    validation: Optional[ValidationResult] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy_id": self.strategy_id,
            "strategy": self.strategy.to_manifest() if self.strategy else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "errors": self.errors,
        }


# ==================================================================
# StrategyComposer
# ==================================================================

class StrategyComposer:
    """
    策略装配器

    用法：
        composer = StrategyComposer()
        result = composer.compose(ComposeRequest(
            name="Momentum_LGBM_v2",
            family="Momentum",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ProbabilitySignal@1.0",
            ...
        ))
        if result.success:
            print(f"Strategy built: {result.strategy_id}")
    """

    def __init__(self, registry: Optional[PackageRegistry] = None) -> None:
        self.registry = registry or get_package_registry()
        self.resolver = DependencyResolver(registry=self.registry)

    def compose(self, request: ComposeRequest) -> ComposeResult:
        """
        装配策略

        流程：
          1. 创建 StrategyPackage
          2. 解析依赖
          3. 验证依赖完整性
          4. 保存到 Registry
          5. 返回结果
        """
        errors: List[str] = []

        # 1. 验证必填字段
        if not request.name:
            errors.append("Strategy name is required")
        if not request.model_ref:
            errors.append("model_ref is required")
        if not request.signal_ref:
            errors.append("signal_ref is required")
        if not request.position_ref:
            errors.append("position_ref is required")
        if not request.risk_ref:
            errors.append("risk_ref is required")
        if not request.execution_ref:
            errors.append("execution_ref is required")
        if not request.observe_ref:
            errors.append("observe_ref is required")

        if errors:
            return ComposeResult(success=False, errors=errors)

        # 2. 创建 StrategyPackage
        strategy = StrategyPackage(
            name=request.name,
            version=request.version,
            description=request.description,
            family=request.family or request.name,
            strategy_status=StrategyStatus.CANDIDATE,
            validation=ValidationState.PENDING,
            model_ref=request.model_ref,
            signal_ref=request.signal_ref,
            position_ref=request.position_ref,
            risk_ref=request.risk_ref,
            execution_ref=request.execution_ref,
            observe_ref=request.observe_ref,
        )

        # 3. 解析依赖
        graph = self.resolver.resolve(strategy)

        # 4. 验证依赖
        validation = self.resolver.validate(graph)
        if not validation.passed:
            return ComposeResult(
                success=False,
                strategy=strategy,
                validation=validation,
                errors=validation.errors,
            )

        # 5. 保存到 Registry
        try:
            self.registry.register(strategy)
            strategy.strategy_status = StrategyStatus.CANDIDATE
            if request.auto_validate:
                strategy.validation = ValidationState.PENDING
            logger.info(f"Strategy composed: {strategy.id}")
        except Exception as e:
            return ComposeResult(
                success=False,
                strategy=strategy,
                errors=[f"Failed to register strategy: {e}"],
            )

        return ComposeResult(
            success=True,
            strategy_id=strategy.id,
            strategy=strategy,
            validation=validation,
        )
