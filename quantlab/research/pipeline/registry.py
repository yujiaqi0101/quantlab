"""
Pipeline Registry — 统一注册 Factor / Signal / Strategy

所有 Pipeline 执行需要的组件都通过 Registry 查找，
不再让各 Service 各自跑自己的逻辑。

用法：
    registry = PipelineRegistry()
    registry.register_factor("RSI", RSIFactor, {"period": 14})
    registry.register_strategy("ma_cross", MACrossStrategy)

    # 查找
    factor_cls = registry.get_factor("RSI")
    strategy_cls = registry.get_strategy("ma_cross")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("quantlab.research.pipeline.registry")


@dataclass
class FactorEntry:
    """因子注册条目"""
    name: str
    factory: Any           # 因子类或工厂函数
    default_params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    category: str = ""


@dataclass
class StrategyEntry:
    """策略注册条目"""
    strategy_id: str
    factory: Any           # 策略类或工厂函数
    default_params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class SignalEntry:
    """信号注册条目"""
    signal_id: str
    strategy_id: str       # 关联的策略
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


class PipelineRegistry:
    """
    Pipeline 统一注册表

    集中管理 Factor / Signal / Strategy 的注册和查找
    """

    def __init__(self) -> None:
        self._factors: Dict[str, FactorEntry] = {}
        self._strategies: Dict[str, StrategyEntry] = {}
        self._signals: Dict[str, SignalEntry] = {}

    # ---- Factor ----

    def register_factor(
        self,
        name: str,
        factory: Any,
        default_params: Optional[Dict[str, Any]] = None,
        description: str = "",
        category: str = "",
    ) -> FactorEntry:
        """注册因子"""
        entry = FactorEntry(
            name=name,
            factory=factory,
            default_params=default_params or {},
            description=description,
            category=category,
        )
        self._factors[name] = entry
        logger.debug(f"pipeline registry: factor '{name}' registered")
        return entry

    def get_factor(self, name: str) -> Optional[FactorEntry]:
        return self._factors.get(name)

    def list_factors(self, category: Optional[str] = None) -> List[FactorEntry]:
        factors = list(self._factors.values())
        if category:
            factors = [f for f in factors if f.category == category]
        return factors

    def create_factor(self, name: str, **params) -> Any:
        """创建因子实例"""
        entry = self._factors.get(name)
        if entry is None:
            raise KeyError(f"Factor '{name}' not registered")
        merged = {**entry.default_params, **params}
        if callable(entry.factory):
            return entry.factory(**merged)
        # 如果是类
        return entry.factory(**merged)

    # ---- Strategy ----

    def register_strategy(
        self,
        strategy_id: str,
        factory: Any,
        default_params: Optional[Dict[str, Any]] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> StrategyEntry:
        """注册策略"""
        entry = StrategyEntry(
            strategy_id=strategy_id,
            factory=factory,
            default_params=default_params or {},
            description=description,
            tags=tags or [],
        )
        self._strategies[strategy_id] = entry
        logger.debug(f"pipeline registry: strategy '{strategy_id}' registered")
        return entry

    def get_strategy(self, strategy_id: str) -> Optional[StrategyEntry]:
        return self._strategies.get(strategy_id)

    def list_strategies(self, tag: Optional[str] = None) -> List[StrategyEntry]:
        strategies = list(self._strategies.values())
        if tag:
            strategies = [s for s in strategies if tag in s.tags]
        return strategies

    def create_strategy(self, strategy_id: str, **params) -> Any:
        """创建策略实例"""
        entry = self._strategies.get(strategy_id)
        if entry is None:
            raise KeyError(f"Strategy '{strategy_id}' not registered")
        merged = {**entry.default_params, **params}
        if callable(entry.factory):
            return entry.factory(**merged)
        return entry.factory(**merged)

    # ---- Signal ----

    def register_signal(
        self,
        signal_id: str,
        strategy_id: str,
        params: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> SignalEntry:
        """注册信号"""
        entry = SignalEntry(
            signal_id=signal_id,
            strategy_id=strategy_id,
            params=params or {},
            description=description,
        )
        self._signals[signal_id] = entry
        return entry

    def get_signal(self, signal_id: str) -> Optional[SignalEntry]:
        return self._signals.get(signal_id)

    def list_signals(self) -> List[SignalEntry]:
        return list(self._signals.values())

    # ---- 统计 ----

    def stats(self) -> Dict[str, Any]:
        return {
            "factors": len(self._factors),
            "strategies": len(self._strategies),
            "signals": len(self._signals),
        }

    # ---- 从 Service 自动注册 ----

    def register_from_services(
        self,
        factor_service=None,
        strategy_service=None,
    ) -> int:
        """
        从现有 Service 自动注册

        返回注册总数
        """
        count = 0

        if factor_service is not None:
            try:
                factors = factor_service.list_factors()
                for f in factors:
                    name = f.get("name", f.get("id", ""))
                    if name and name not in self._factors:
                        self.register_factor(
                            name=name,
                            factory=None,  # 通过 Service 间接调用
                            description=f.get("description", ""),
                            category=f.get("category", ""),
                        )
                        count += 1
            except Exception as e:
                logger.warning(f"Failed to register from factor_service: {e}")

        if strategy_service is not None:
            try:
                strategies = strategy_service.list_strategies()
                for s in strategies:
                    sid = s.get("id", s.get("strategy_id", ""))
                    if sid and sid not in self._strategies:
                        self.register_strategy(
                            strategy_id=sid,
                            factory=None,
                            description=s.get("description", ""),
                            tags=s.get("tags", []),
                        )
                        count += 1
            except Exception as e:
                logger.warning(f"Failed to register from strategy_service: {e}")

        return count
