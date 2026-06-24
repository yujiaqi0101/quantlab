"""
Gate Registry — Gate 注册表

按名称获取 Gate 类，用于动态创建 Pipeline。
"""

from __future__ import annotations

import logging
from typing import Dict, Type

from .gate import ValidationGate

logger = logging.getLogger("quantlab.ml.validation.pipeline.registry")


class GateRegistry:
    """Gate 注册表"""

    def __init__(self) -> None:
        self._gates: Dict[str, Type[ValidationGate]] = {}

    def register(self, name: str, gate_cls: Type[ValidationGate]) -> None:
        self._gates[name] = gate_cls
        logger.debug(f"Registered gate: {name}")

    def get(self, name: str) -> Type[ValidationGate] | None:
        return self._gates.get(name)

    def list_all(self) -> Dict[str, Type[ValidationGate]]:
        return dict(self._gates)

    def list_names(self) -> list[str]:
        return list(self._gates.keys())


# 全局单例
_gate_registry: GateRegistry | None = None


def get_gate_registry() -> GateRegistry:
    global _gate_registry
    if _gate_registry is None:
        _gate_registry = GateRegistry()
        _register_default_gates(_gate_registry)
    return _gate_registry


def _register_default_gates(registry: GateRegistry) -> None:
    """注册所有默认 Gate"""
    try:
        from .gates.data_gate import DataGate
        registry.register("data", DataGate)
    except ImportError:
        pass

    try:
        from .gates.training_gate import TrainingGate
        registry.register("training", TrainingGate)
    except ImportError:
        pass

    try:
        from .gates.leakage_gate import LeakageGate
        registry.register("leakage", LeakageGate)
    except ImportError:
        pass

    try:
        from .gates.timeseries_gate import WalkForwardGate
        registry.register("walk_forward", WalkForwardGate)
    except ImportError:
        pass

    try:
        from .gates.trading_gate import TradingGate
        registry.register("trading", TradingGate)
    except ImportError:
        pass

    try:
        from .gates.robustness_gate import RobustnessGate
        registry.register("robustness", RobustnessGate)
    except ImportError:
        pass

    try:
        from .gates.benchmark_gate import BenchmarkGate
        registry.register("benchmark", BenchmarkGate)
    except ImportError:
        pass
