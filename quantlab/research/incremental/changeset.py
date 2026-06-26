"""
ChangeSet — 数据变更集

描述一次数据更新包含哪些变更 (新增/修改/删除)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

import pandas as pd


class ChangeOp(str, Enum):
    INSERT = "insert"  # 新增数据
    UPDATE = "update"  # 修改数据
    DELETE = "delete"  # 删除数据


@dataclass
class Change:
    """单条变更。"""
    op: ChangeOp
    symbol: str
    timestamp: pd.Timestamp
    fields: dict = field(default_factory=dict)  # 更新的字段 {col: new_value}

    def __repr__(self) -> str:
        return f"Change({self.op.value} {self.symbol}@{self.timestamp})"


@dataclass
class ChangeSet:
    """一次数据变更集合。"""
    changes: List[Change] = field(default_factory=list)
    source: str = ""  # "live" / "backfill" / "correction"
    meta: dict = field(default_factory=dict)

    def add(self, change: Change) -> "ChangeSet":
        self.changes.append(change)
        return self

    def add_insert(self, symbol: str, timestamp: pd.Timestamp, fields: dict) -> "ChangeSet":
        return self.add(Change(ChangeOp.INSERT, symbol, timestamp, fields))

    def add_update(self, symbol: str, timestamp: pd.Timestamp, fields: dict) -> "ChangeSet":
        return self.add(Change(ChangeOp.UPDATE, symbol, timestamp, fields))

    def add_delete(self, symbol: str, timestamp: pd.Timestamp) -> "ChangeSet":
        return self.add(Change(ChangeOp.DELETE, symbol, timestamp))

    def symbols(self) -> set:
        return {c.symbol for c in self.changes}

    def timestamps(self) -> set:
        return {c.timestamp for c in self.changes}

    def is_empty(self) -> bool:
        return len(self.changes) == 0

    def size(self) -> int:
        return len(self.changes)

    @classmethod
    def from_panel_diff(cls, old: pd.DataFrame, new: pd.DataFrame) -> "ChangeSet":
        """从新旧 panel 对比生成 ChangeSet。"""
        cs = cls()
        # 简化：按 index 对比
        old_idx = set(old.index)
        new_idx = set(new.index)
        # 新增的行
        for idx in new_idx - old_idx:
            dt, sym = idx
            row = new.loc[idx].to_dict()
            cs.add_insert(sym, dt, row)
        # 删除的行
        for idx in old_idx - new_idx:
            dt, sym = idx
            cs.add_delete(sym, dt)
        # 修改的行
        for idx in old_idx & new_idx:
            dt, sym = idx
            old_row = old.loc[idx]
            new_row = new.loc[idx]
            diff = {}
            for col in new.columns:
                if col in old.columns:
                    if old_row[col] != new_row[col]:
                        diff[col] = new_row[col]
            if diff:
                cs.add_update(sym, dt, diff)
        return cs


__all__ = ["Change", "ChangeSet", "ChangeOp"]
