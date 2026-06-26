"""
FactorInfo 元数据定义
=====================
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import pandas as pd

from ..factors.context import FactorContext


# 因子函数签名: (ctx: FactorContext, **kwargs) -> pd.DataFrame
FactorFn = Callable[..., pd.DataFrame]


@dataclass
class FactorInfo:
    """单个因子的元数据与可调用句柄。

    Attributes:
        name:        因子唯一名称 (如 "alpha_001", "ma_5")
        category:    分类 (trend/momentum/volatility/volume/cross_sectional/composite/fundamental)
        description: 中文描述
        fn:          因子计算函数
        direction:   信号方向: 1=正向(值越大越看好), -1=反向(值越小越看好), 0=方向中性
        source:      来源标识 (alpha191/alpha101/technical/custom)
        params:      默认参数 (如 {"window": 5})
        metadata:    附加元数据
    """
    name: str
    category: str
    description: str
    fn: FactorFn
    direction: int = 0
    source: str = "custom"
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute(self, ctx: FactorContext, **kwargs: Any) -> pd.DataFrame:
        """执行因子计算，返回 date × symbol 面板。"""
        merged = {**self.params, **kwargs}
        return self.fn(ctx, **merged)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为前端 FactorInfo 结构。"""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "direction": self.direction,
            "source": self.source,
            "params": self.params,
        }
