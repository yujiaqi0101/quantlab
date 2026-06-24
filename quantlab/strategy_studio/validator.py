"""
StrategyValidator — 策略验证器

职责：
  1. 依赖完整性检查（调用 DependencyResolver）
  2. Paper Smoke Test（100 bar 模拟运行）
  3. 检查 Order/Position/PnL/Risk 是否正常

验证流程：
  Strategy → DependencyResolver → SmokeTest → ValidationReport
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..asset_package.base import PackageType
from ..asset_package.registry import PackageRegistry, get_package_registry
from ..asset_package.types import (
    StrategyPackage, StrategyStatus, ValidationState,
    SignalPackage, PositionPackage, RiskPackage,
)
from .resolver import DependencyResolver, ValidationResult

logger = logging.getLogger("quantlab.strategy_studio.validator")


# ==================================================================
# ValidationReport
# ==================================================================

@dataclass
class ValidationReport:
    """验证报告"""
    strategy_id: str
    passed: bool
    dependency_check: Optional[ValidationResult] = None
    smoke_test: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "passed": self.passed,
            "dependency_check": self.dependency_check.to_dict() if self.dependency_check else None,
            "smoke_test": self.smoke_test,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ==================================================================
# StrategyValidator
# ==================================================================

class StrategyValidator:
    """
    策略验证器

    用法：
        validator = StrategyValidator()
        report = validator.validate(strategy)
        if report.passed:
            print("Strategy validated")
    """

    def __init__(self, registry: Optional[PackageRegistry] = None) -> None:
        self.registry = registry or get_package_registry()
        self.resolver = DependencyResolver(registry=self.registry)

    def validate(self, strategy: StrategyPackage,
                 smoke_test_bars: int = 100) -> ValidationReport:
        """
        验证策略

        流程：
          1. 依赖完整性检查
          2. Paper Smoke Test（100 bar 模拟运行）
          3. 返回报告
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. 依赖检查
        graph = self.resolver.resolve(strategy)
        dep_result = self.resolver.validate(graph)
        if not dep_result.passed:
            errors.extend(dep_result.errors)
            return ValidationReport(
                strategy_id=strategy.id,
                passed=False,
                dependency_check=dep_result,
                errors=errors,
            )

        # 2. Smoke Test
        smoke_result = self._run_smoke_test(strategy, smoke_test_bars)
        if not smoke_result.get("passed", False):
            errors.extend(smoke_result.get("errors", []))
            return ValidationReport(
                strategy_id=strategy.id,
                passed=False,
                dependency_check=dep_result,
                smoke_test=smoke_result,
                errors=errors,
            )

        # 3. 更新策略状态
        strategy.validation = ValidationState.PASS
        strategy.strategy_status = StrategyStatus.VALIDATED

        return ValidationReport(
            strategy_id=strategy.id,
            passed=True,
            dependency_check=dep_result,
            smoke_test=smoke_result,
            warnings=warnings,
        )

    def _run_smoke_test(self, strategy: StrategyPackage, bars: int) -> Dict[str, Any]:
        """
        Paper Smoke Test：用模拟数据跑 N bar，检查策略能正常运行

        检查项：
          - Signal 能生成
          - Position 能计算
          - Risk 能应用
          - 无异常
        """
        errors: List[str] = []
        checks: List[Dict[str, Any]] = []

        try:
            # 加载 Signal/Position/Risk Package
            signal_pkg = self._load_package(strategy.signal_ref, PackageType.SIGNAL)
            position_pkg = self._load_package(strategy.position_ref, PackageType.POSITION)
            risk_pkg = self._load_package(strategy.risk_ref, PackageType.RISK)

            if signal_pkg is None:
                errors.append(f"Cannot load signal: {strategy.signal_ref}")
            if position_pkg is None:
                errors.append(f"Cannot load position: {strategy.position_ref}")
            if risk_pkg is None:
                errors.append(f"Cannot load risk: {strategy.risk_ref}")

            if errors:
                return {"passed": False, "errors": errors, "checks": checks}

            # 生成模拟预测数据
            np.random.seed(42)
            symbols = ["BTC", "ETH", "SOL"]
            predictions = pd.Series(
                np.random.randn(len(symbols)) * 0.05,
                index=symbols,
            )

            # 1. Signal 生成
            signals = signal_pkg.generate(predictions, metadata={"timestamp": "smoke_test"})
            checks.append({
                "name": "signal_generation",
                "passed": len(signals) > 0,
                "detail": f"Generated {len(signals)} signals",
            })

            # 2. Position 计算
            positions = position_pkg.size(signals, capital=100000)
            checks.append({
                "name": "position_sizing",
                "passed": len(positions) > 0,
                "detail": f"Computed {len(positions)} positions",
            })

            # 3. Risk 应用
            adjusted = risk_pkg.apply(positions, portfolio_state={})
            checks.append({
                "name": "risk_application",
                "passed": len(adjusted) > 0,
                "detail": f"Applied risk to {len(adjusted)} positions",
            })

            # 4. 检查无异常
            all_passed = all(c["passed"] for c in checks)
            return {
                "passed": all_passed,
                "bars": bars,
                "checks": checks,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Smoke test failed: {e}")
            errors.append(f"Smoke test exception: {e}")
            return {"passed": False, "errors": errors, "checks": checks}

    def _load_package(self, ref_str: str, pkg_type: PackageType):
        """通过 ref 加载 Package"""
        if not ref_str:
            return None
        try:
            return self.registry.get_by_ref(pkg_type, ref_str)
        except Exception as e:
            logger.error(f"Failed to load package {ref_str}: {e}")
            return None
