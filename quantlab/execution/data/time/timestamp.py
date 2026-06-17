"""
时间戳工具 — 统一时间戳格式

所有系统组件使用统一的 Timestamp 类型
避免 datetime / float / int 混用
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Union


@dataclass(frozen=True)
class Timestamp:
    """
    不可变时间戳 — 统一使用 unix milliseconds

    用法：
        ts = Timestamp.now()
        ts = Timestamp.from_ms(1700000000000)
        ts.to_iso()  # "2023-11-14T22:13:20.000Z"
    """
    ms: int

    @classmethod
    def now(cls) -> "Timestamp":
        import time
        return cls(ms=int(time.time() * 1000))

    @classmethod
    def from_ms(cls, ms: int) -> "Timestamp":
        return cls(ms=int(ms))

    @classmethod
    def from_seconds(cls, seconds: float) -> "Timestamp":
        return cls(ms=int(seconds * 1000))

    @classmethod
    def from_iso(cls, iso_str: str) -> "Timestamp":
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return cls(ms=int(dt.timestamp() * 1000))

    def to_ms(self) -> int:
        return self.ms

    def to_seconds(self) -> float:
        return self.ms / 1000.0

    def to_iso(self) -> str:
        dt = datetime.fromtimestamp(self.ms / 1000.0, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.ms / 1000.0, tz=timezone.utc)

    def __lt__(self, other: "Timestamp") -> bool:
        return self.ms < other.ms

    def __le__(self, other: "Timestamp") -> bool:
        return self.ms <= other.ms

    def __sub__(self, other: "Timestamp") -> float:
        """返回差值（秒）"""
        return (self.ms - other.ms) / 1000.0
