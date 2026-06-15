"""
FactorRegistry — V4.6 因子注册中心

类式注册（区别于 research/factor.py 的函数式注册）
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from .base import Factor

logger = logging.getLogger("quantlab.factor.registry")


class FactorRegistry:
    """
    因子注册中心

    注册因子类（不是实例），按需实例化
    """

    def __init__(self) -> None:
        self._factors: Dict[str, Type[Factor]] = {}

    def register(self, factor_cls: Type[Factor]) -> Type[Factor]:
        """注册因子类"""
        instance = factor_cls()
        name = instance.name
        if name in self._factors:
            logger.warning(f"factor already registered, overwriting: {name}")
        self._factors[name] = factor_cls
        logger.info(f"factor registered: {name} [{instance.category}]")
        return factor_cls

    def get(self, name: str) -> Type[Factor]:
        """获取因子类"""
        if name not in self._factors:
            raise KeyError(f"factor not registered: {name}")
        return self._factors[name]

    def has(self, name: str) -> bool:
        return name in self._factors

    def list(self) -> List[str]:
        return list(self._factors.keys())

    def list_by_category(self, category: str) -> List[str]:
        return [
            name for name, cls in self._factors.items()
            if cls().category == category
        ]

    def categories(self) -> List[str]:
        cats = set(cls().category for cls in self._factors.values())
        return sorted(cats)

    def info(self) -> List[dict]:
        """返回所有因子的元信息"""
        result = []
        for name, cls in self._factors.items():
            inst = cls()
            result.append({
                "name": inst.name,
                "category": inst.category,
                "description": inst.description,
                "class": cls.__name__,
            })
        return result

    def stats(self) -> dict:
        by_cat: Dict[str, int] = {}
        for cls in self._factors.values():
            cat = cls().category
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {
            "total": len(self._factors),
            "by_category": by_cat,
        }
