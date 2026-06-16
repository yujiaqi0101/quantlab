"""
StrategyService — 策略业务入口

封装：策略注册、构建、编译、回测
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..strategy.registry import StrategyRegistry, get_strategy_registry
from ..strategy.api import list_strategies, get_strategy, validate_strategy_params
from ..strategy_builder import StrategyBuilder, StrategySpec, StrategyCompiler

logger = logging.getLogger("quantlab.services.strategy")


class StrategyService:
    """
    策略服务（Facade）

    统一入口：
      - 列出策略 / 搜索
      - 获取策略详情 / 参数 schema
      - 构建策略（可视化 Builder）
      - 编译策略规格
      - 验证参数
    """

    def __init__(
        self,
        registry: Optional[StrategyRegistry] = None,
    ) -> None:
        self._registry = registry or get_strategy_registry()
        self._builder = StrategyBuilder()

    # ---- 查询 ----

    def list_strategies(
        self,
        q: str = "",
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """列出策略"""
        return list_strategies(q=q, tags=tags)

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略详情"""
        return get_strategy(strategy_id)

    def validate_params(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        return validate_strategy_params(strategy_id, params)

    # ---- Builder ----

    def create_spec(
        self,
        name: str,
        signals: List[Dict[str, Any]],
        signal_logic: str = "AND",
        position: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> StrategySpec:
        """创建策略规格"""
        return self._builder.create_spec(
            name=name,
            signals=signals,
            signal_logic=signal_logic,
            position=position,
            risk=risk,
            description=description,
            tags=tags,
        )

    def compile_spec(self, spec: StrategySpec):
        """编译策略规格"""
        return self._builder.compile(spec)

    def list_specs(self) -> List[Dict[str, Any]]:
        """列出已保存的策略规格"""
        return self._builder.list_specs()

    def get_spec(self, spec_id: str) -> Optional[StrategySpec]:
        """获取策略规格"""
        return self._builder.get_spec(spec_id)

    def delete_spec(self, spec_id: str) -> bool:
        """删除策略规格"""
        return self._builder.delete_spec(spec_id)

    # ---- 注册装饰器 ----

    def register_decorator(self):
        """返回 @register_strategy 装饰器"""
        def decorator(cls):
            self._registry.register(cls)
            return cls
        return decorator
