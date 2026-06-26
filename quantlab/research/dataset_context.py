"""
DatasetContext — 提供原始数据访问给 Node

封装 Dataset + Universe + Calendar，提供节点访问原始数据的统一入口。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd

from .frame import ResearchFrame


@dataclass
class DatasetContext:
    """数据集上下文。"""

    panel: pd.DataFrame  # (datetime, symbol) MultiIndex
    universe_id: str = "default"
    calendar_id: str = "crypto"
    adjustment: str = "none"  # none / forward / backward
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_frame(self, name: str = "panel") -> ResearchFrame:
        return ResearchFrame.from_panel(self.panel, name=name)

    def filter_universe(self, symbols: list) -> "DatasetContext":
        """按标的池过滤。"""
        mask = self.panel.index.get_level_values("symbol").isin(symbols)
        return DatasetContext(
            panel=self.panel[mask],
            universe_id=self.universe_id,
            calendar_id=self.calendar_id,
            adjustment=self.adjustment,
            meta=dict(self.meta),
        )

    def filter_date_range(self, start: str, end: str) -> "DatasetContext":
        """按日期范围过滤。"""
        dts = self.panel.index.get_level_values("datetime")
        mask = (dts >= pd.Timestamp(start)) & (dts <= pd.Timestamp(end))
        return DatasetContext(
            panel=self.panel[mask],
            universe_id=self.universe_id,
            calendar_id=self.calendar_id,
            adjustment=self.adjustment,
            meta=dict(self.meta),
        )

    @property
    def symbols(self) -> list:
        return list(self.panel.index.get_level_values("symbol").unique())

    @property
    def datetimes(self):
        return self.panel.index.get_level_values("datetime").unique()

    def fingerprint(self) -> str:
        import hashlib
        h = hashlib.sha256()
        h.update(str(self.panel.shape).encode())
        h.update(str(self.panel.columns.tolist()).encode())
        h.update(self.universe_id.encode())
        h.update(self.calendar_id.encode())
        h.update(self.adjustment.encode())
        return h.hexdigest()[:16]


__all__ = ["DatasetContext"]
