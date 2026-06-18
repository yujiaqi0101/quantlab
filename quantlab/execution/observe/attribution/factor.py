"""
Factor Attribution — 因子归因（接口预留）

当 Alpha Factory 成熟后再做。

预留接口：
  - Momentum / Volatility / Volume / RSI 等因子贡献

当前版本：仅提供接口骨架，不实现具体逻辑。

用法：
    attr = FactorAttribution(store)
    report = attr.analyze(session_id="s1")
    # 当前返回空结果，待 Alpha Factory 成熟后实现
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..event_store import EventStore, StoredEvent

logger = logging.getLogger("quantlab.execution.observe.attribution.factor")


@dataclass
class FactorContribution:
    """单因子贡献"""
    factor: str = ""  # momentum / volatility / volume / rsi
    label: str = ""   # 动量 / 波动率 / 成交量 / RSI
    pnl: float = 0.0
    pnl_pct: float = 0.0
    n_trades: int = 0
    # 因子值范围
    avg_factor_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor": self.factor,
            "label": self.label,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "n_trades": self.n_trades,
            "avg_factor_value": round(self.avg_factor_value, 4),
        }


@dataclass
class FactorAttributionReport:
    """因子归因报告"""
    start_ts: int = 0
    end_ts: int = 0
    total_pnl: float = 0.0
    total_trades: int = 0
    factors: List[FactorContribution] = field(default_factory=list)
    # 是否已实现
    implemented: bool = False
    note: str = "因子归因待 Alpha Factory 成熟后实现"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "factors": [f.to_dict() for f in self.factors],
            "implemented": self.implemented,
            "note": self.note,
        }


class FactorAttribution:
    """
    因子归因（接口预留）

    当 Alpha Factory 成熟后，实现以下因子：
      - Momentum（动量）
      - Volatility（波动率）
      - Volume（成交量）
      - RSI
      - 自定义因子
    """

    # 预定义因子
    PREDEFINED_FACTORS = {
        "momentum": "动量",
        "volatility": "波动率",
        "volume": "成交量",
        "rsi": "RSI",
    }

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def analyze(self, session_id: str) -> FactorAttributionReport:
        """分析（当前返回空报告）"""
        report = FactorAttributionReport()
        # TODO: 待 Alpha Factory 成熟后实现
        # 1. 从事件中提取因子值
        # 2. 按因子分组统计 PnL
        # 3. 计算因子贡献
        return report

    def analyze_range(
        self,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str] = None,
    ) -> FactorAttributionReport:
        """分析时间范围（当前返回空报告）"""
        return FactorAttributionReport()
