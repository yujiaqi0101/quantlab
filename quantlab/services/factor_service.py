"""
FactorService — 因子业务入口

封装：因子注册、计算、IC分析、可视化
API 层只调本 Service，不直接碰 FactorRegistry / FactorEngine
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..factor.registry import FactorRegistry
from ..factor.factor_engine import FactorEngine
from ..factor.ic_analysis import compute_ic, compute_ic_stats

logger = logging.getLogger("quantlab.services.factor")


class FactorService:
    """
    因子服务（Facade）

    统一入口：
      - 列出因子 / 分类
      - 计算因子值
      - IC 分析
      - 因子可视化数据
    """

    def __init__(
        self,
        registry: Optional[FactorRegistry] = None,
        engine: Optional[FactorEngine] = None,
    ) -> None:
        self._registry = registry or FactorRegistry()
        self._engine = engine or FactorEngine()

    # ---- 查询 ----

    def list_factors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有因子"""
        if category:
            names = self._registry.list_by_category(category)
        else:
            names = self._registry.list()
        return [self._registry.info_for(name) if hasattr(self._registry, 'info_for') else {"name": name} for name in names]

    def get_factor(self, name: str) -> Dict[str, Any]:
        """获取因子详情"""
        if hasattr(self._registry, 'info_for'):
            return self._registry.info_for(name)
        return {"name": name}

    def categories(self) -> List[str]:
        """列出因子分类"""
        return self._registry.categories()

    # ---- 计算 ----

    def compute(self, factor_name: str, data: Any, **kwargs) -> Any:
        """计算因子值"""
        factor_cls = self._registry.get(factor_name)
        factor = factor_cls()
        return factor.compute(data, **kwargs)

    # ---- IC 分析 ----

    def ic_analysis(
        self,
        factor_name: str,
        data: Any,
        forward_period: int = 1,
    ) -> Dict[str, Any]:
        """IC 分析"""
        factor_values = self.compute(factor_name, data)
        ic_series = compute_ic(factor_values, data, forward_period)
        return compute_ic_stats(ic_series)

    # ---- 注册 ----

    def register(self, factor_cls: type) -> type:
        """注册因子类"""
        return self._registry.register(factor_cls)

    def register_decorator(self):
        """返回 @register_factor 装饰器"""
        return self._registry.register
