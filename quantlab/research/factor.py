"""
FactorRegistry — V4.5 因子注册中心

职责：
  - 注册因子函数（类似 StrategyRegistry）
  - 按名称查找因子
  - 列出所有可用因子 + 元信息
  - 与 FeatureStore 集成：注册的因子可直接 compute

用法：
    from quantlab.factors import ma, rsi, atr

    fr = FactorRegistry()
    fr.register("MA", ma, description="移动均线")
    fr.register("RSI", rsi, description="相对强弱指标")

    # 列出所有因子
    fr.list_factors()

    # 直接计算
    df_ma = fr.compute("MA", ctx, period=20)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.research.factor_registry")


# ------------------------------------------------------------------
# FactorInfo
# ------------------------------------------------------------------
@dataclass(slots=True)
class FactorInfo:
    """因子元信息"""
    name: str
    fn: Any = field(repr=False)           # 实际因子函数
    description: str = ""
    category: str = ""       # "trend" / "momentum" / "volatility" / "volume"
    parameters: str = ""     # "period, fast, slow"
    tags: str = ""           # "technical,lagging"
    version: str = "1"


# ------------------------------------------------------------------
# FactorRegistry
# ------------------------------------------------------------------
class FactorRegistry:
    """
    因子注册中心

    类似 StrategyRegistry，但注册的是因子函数而非策略类。
    因子函数签名：fn(ctx, **params) -> Series/DataFrame
    """

    def __init__(self) -> None:
        self._factors: Dict[str, FactorInfo] = {}

    # ------------------------------------------------------------------
    # 注册 / 注销
    # ------------------------------------------------------------------
    def register(
        self,
        name: str,
        fn: Callable,
        description: str = "",
        category: str = "",
        parameters: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1",
    ) -> FactorInfo:
        """注册因子"""
        if name in self._factors:
            logger.warning(f"factor already registered, overwriting: {name}")
        info = FactorInfo(
            name=name,
            fn=fn,
            description=description,
            category=category,
            parameters=parameters,
            tags=",".join(tags or []),
            version=version,
        )
        self._factors[name] = info
        logger.info(f"factor registered: {name} [{category}]")
        return info

    def unregister(self, name: str) -> bool:
        if name in self._factors:
            del self._factors[name]
            return True
        return False

    # ------------------------------------------------------------------
    # 查找
    # ------------------------------------------------------------------
    def get(self, name: str) -> Optional[FactorInfo]:
        return self._factors.get(name)

    def get_fn(self, name: str) -> Optional[Callable]:
        info = self._factors.get(name)
        return info.fn if info else None

    # ------------------------------------------------------------------
    # 计算
    # ------------------------------------------------------------------
    def compute(self, name: str, ctx: Any, **params) -> Any:
        """
        调用因子函数

        用法（单 symbol）：
            s = fr.compute("MA", ctx, symbol="AAPL", period=20)

        用法（全 symbol，不传 symbol）：
            df = fr.compute_all("MA", ctx, period=20)
        """
        info = self._factors.get(name)
        if info is None:
            raise KeyError(f"factor not registered: {name}")
        return info.fn(ctx, **params)

    def compute_all(self, name: str, ctx: Any, **params) -> pd.DataFrame:
        """
        对 ctx 中所有 symbol 计算因子，返回 DataFrame

        用法：
            df_ma = fr.compute_all("MA", ctx, period=20)
            → DataFrame(columns=symbols)
        """
        import pandas as pd
        info = self._factors.get(name)
        if info is None:
            raise KeyError(f"factor not registered: {name}")
        result = {}
        for sym in ctx.symbols:
            result[sym] = info.fn(ctx, symbol=sym, **params)
        return pd.DataFrame(result)

    # ------------------------------------------------------------------
    # 列表 / 搜索
    # ------------------------------------------------------------------
    def list_factors(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[FactorInfo]:
        results = list(self._factors.values())
        if category:
            results = [f for f in results if f.category == category]
        if tag:
            results = [f for f in results if tag in f.tags]
        return results

    def search(self, keyword: str) -> List[FactorInfo]:
        kw = keyword.lower()
        return [
            f for f in self._factors.values()
            if kw in f.name.lower()
            or kw in f.description.lower()
            or kw in f.category.lower()
            or kw in f.tags.lower()
        ]

    def categories(self) -> List[str]:
        cats = set(f.category for f in self._factors.values() if f.category)
        return sorted(cats)

    def stats(self) -> Dict[str, Any]:
        by_cat: Dict[str, int] = {}
        for f in self._factors.values():
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
        return {
            "total_factors": len(self._factors),
            "by_category": by_cat,
        }

    # ------------------------------------------------------------------
    # 批量注册（从 quantlab.factors 自动发现）
    # ------------------------------------------------------------------
    def register_defaults(self) -> int:
        """
        自动注册 quantlab.factors 下的所有因子

        返回注册数量
        """
        count = 0
        try:
            from quantlab.factors.ma import ma
            self.register("MA", ma, description="移动均线",
                          category="trend", parameters="period")
            count += 1
        except ImportError:
            pass
        try:
            from quantlab.factors.rsi import rsi
            self.register("RSI", rsi, description="相对强弱指标",
                          category="momentum", parameters="period")
            count += 1
        except ImportError:
            pass
        try:
            from quantlab.factors.atr import atr
            self.register("ATR", atr, description="平均真实波幅",
                          category="volatility", parameters="period")
            count += 1
        except ImportError:
            pass
        try:
            from quantlab.factors.boll import boll
            self.register("BOLL", boll, description="布林带",
                          category="volatility", parameters="period,k")
            count += 1
        except ImportError:
            pass
        try:
            from quantlab.factors.alpha101 import alpha009, alpha040, alpha049
            self.register("Alpha009", alpha009, description="WQ Alpha#9",
                          category="alpha101", parameters="period")
            self.register("Alpha040", alpha040, description="WQ Alpha#40",
                          category="alpha101", parameters="period")
            self.register("Alpha049", alpha049, description="WQ Alpha#49",
                          category="alpha101", parameters="period")
            count += 3
        except ImportError:
            pass
        return count
