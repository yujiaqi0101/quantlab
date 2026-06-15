"""
DTO — Runtime

**从 domain 重新导出**，保留旧类型名（兼容）。
"""

from ..domain.runtime import (
    StartStrategySpec as StartStrategyRequest,
    RuntimeInstance as RuntimeStatus,
)


__all__ = [
    "StartStrategyRequest",
    "RuntimeStatus",
]
