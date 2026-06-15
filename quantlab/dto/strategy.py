"""
DTO — StrategyInfo

**从 domain.strategy 重新导出**。
保留别名 StrategyInfo（兼容旧 import），对应 domain.StrategyDefinition。
"""

from ..domain.strategy import (
    StrategyDefinition as StrategyInfo,
    ParamSchema as StrategyParam,
)


__all__ = [
    "StrategyInfo",
    "StrategyParam",
]
