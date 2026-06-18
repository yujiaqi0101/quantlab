"""
Strategy Registry — 本地策略目录

T1 第九模块：本地策略目录（RSI / Momentum / LGBM）

  StrategyInfo       — 策略元信息
  StrategyParameter  — 策略参数
  StrategyRegistry   — 注册表
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.strategy_registry")


@dataclass
class StrategyParameter:
    """策略参数定义"""
    name: str
    type: str = "float"        # int / float / bool / str / choice
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    choices: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "min": self.min,
            "max": self.max,
            "choices": self.choices,
            "description": self.description,
        }


@dataclass
class StrategyInfo:
    """策略信息"""
    strategy_id: str
    name: str
    description: str = ""
    category: str = "general"      # momentum / mean_reversion / ml / portfolio
    tags: List[str] = field(default_factory=list)
    parameters: List[StrategyParameter] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    timeframe: str = "1d"
    author: str = ""
    version: str = "1.0.0"
    enabled: bool = True

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "parameters": [p.to_dict() for p in self.parameters],
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "author": self.author,
            "version": self.version,
            "enabled": self.enabled,
        }

    def get_parameter(self, name: str) -> Optional[StrategyParameter]:
        for p in self.parameters:
            if p.name == name:
                return p
        return None


class StrategyRegistry:
    """
    策略注册表 — 本地策略目录

    用法：
        reg = StrategyRegistry()
        reg.register(StrategyInfo(strategy_id="rsi", name="RSI Strategy"))
        info = reg.get_strategy("rsi")
        strategies = reg.list_strategies()
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, StrategyInfo] = {}

    def register(self, info: StrategyInfo) -> None:
        """注册策略"""
        self._strategies[info.strategy_id] = info
        logger.info(f"Strategy registered: {info.strategy_id} ({info.name})")

    def unregister(self, strategy_id: str) -> bool:
        """注销策略"""
        if strategy_id in self._strategies:
            self._strategies.pop(strategy_id)
            return True
        return False

    def get_strategy(self, strategy_id: str) -> Optional[StrategyInfo]:
        """获取策略信息"""
        return self._strategies.get(strategy_id)

    def has(self, strategy_id: str) -> bool:
        return strategy_id in self._strategies

    def list_strategies(
        self,
        category: str = "",
        tag: str = "",
        enabled_only: bool = False,
    ) -> List[StrategyInfo]:
        """列出策略"""
        result = list(self._strategies.values())
        if category:
            result = [s for s in result if s.category == category]
        if tag:
            result = [s for s in result if tag in s.tags]
        if enabled_only:
            result = [s for s in result if s.enabled]
        return result

    def list_categories(self) -> List[str]:
        """列出所有类别"""
        return list(set(s.category for s in self._strategies.values()))

    def list_tags(self) -> List[str]:
        """列出所有标签"""
        tags = set()
        for s in self._strategies.values():
            tags.update(s.tags)
        return list(tags)

    def to_dict(self) -> Dict:
        return {
            "total": len(self._strategies),
            "strategies": [s.to_dict() for s in self._strategies.values()],
            "categories": self.list_categories(),
            "tags": self.list_tags(),
        }


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_registry: Optional[StrategyRegistry] = None


def get_registry() -> StrategyRegistry:
    """获取全局 StrategyRegistry 单例"""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
        # 自动注册内置策略
        try:
            from .builtin import register_all_builtin
            register_all_builtin(_registry)
        except Exception as e:
            logger.warning(f"Failed to register builtin strategies: {e}")
    return _registry


def register_builtin(reg: Optional[StrategyRegistry] = None) -> int:
    """注册内置策略（兼容旧接口）"""
    from .builtin import register_all_builtin
    target = reg or get_registry()
    return register_all_builtin(target)
