"""
Signal Registry — 信号仓库 + 版本管理

负责 Signal 的持久化和版本管理。
遵循文档第 528-572 行：Signal 不要即时生成然后丢掉，而是全部保存。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .signal import Signal
from .storage import get_signal_store

logger = logging.getLogger("quantlab.ml.signal_engine.registry")


@dataclass
class SignalVersion:
    """信号版本记录"""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str = ""
    version: int = 1
    generator_config: Dict[str, Any] = field(default_factory=dict)
    model_version: str = ""
    dataset_id: str = ""
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    pipeline_config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "signal_id": self.signal_id,
            "version": self.version,
            "generator_config": self.generator_config,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "validation_summary": self.validation_summary,
            "pipeline_config": self.pipeline_config,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SignalVersion":
        return cls(
            version_id=d.get("version_id", str(uuid.uuid4())),
            signal_id=d.get("signal_id", ""),
            version=int(d.get("version", 1)),
            generator_config=d.get("generator_config", {}) or {},
            model_version=d.get("model_version", ""),
            dataset_id=d.get("dataset_id", ""),
            validation_summary=d.get("validation_summary", {}) or {},
            pipeline_config=d.get("pipeline_config", {}) or {},
            created_at=d.get("created_at", ""),
        )


class SignalRegistry:
    """
    信号仓库 — SQLite 持久化 + 版本管理

    用法：
        reg = get_signal_registry()
        reg.register_signal(signal, version_info)
        signals = reg.list_signals(symbol="BTC", direction="LONG")
    """

    def __init__(self) -> None:
        self._store = get_signal_store()

    def register_signal(
        self,
        signal: Signal,
        version_info: Optional[SignalVersion] = None,
        pipeline_config: Optional[Dict[str, Any]] = None,
        model_version: str = "",
        dataset_id: str = "",
    ) -> SignalVersion:
        """
        注册信号到仓库。

        如果未提供 version_info，则自动创建一个新版本。
        """
        # 处理版本
        if version_info is None:
            latest = self._store.latest_version_number(signal.signal_id)
            version_info = SignalVersion(
                signal_id=signal.signal_id,
                version=latest + 1,
                model_version=model_version or signal.source_model,
                dataset_id=dataset_id,
                pipeline_config=pipeline_config or {},
            )

        # 先保存信号（version_id 暂为空，避免 FK 约束）
        self._store.save_signal(signal.to_dict(), version_id="")
        # 再保存版本
        self._store.save_version(version_info.to_dict())
        # 最后回填 version_id 到 signal
        self._store.update_signal_version_id(signal.signal_id, version_info.version_id)

        logger.info(
            f"Signal registered: {signal.signal_id} v{version_info.version} "
            f"({signal.symbol} {signal.direction.value})"
        )
        return version_info

    def register_signal_set(
        self,
        signal_set,
        model_version: str = "",
        dataset_id: str = "",
    ) -> List[SignalVersion]:
        """批量注册 SignalSet 中的所有信号"""
        versions: List[SignalVersion] = []
        for signal in signal_set.signals:
            v = self.register_signal(
                signal,
                pipeline_config=signal_set.pipeline_config,
                model_version=model_version,
                dataset_id=dataset_id,
            )
            versions.append(v)
        return versions

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        d = self._store.get_signal(signal_id)
        return Signal.from_dict(d) if d else None

    def list_signals(
        self,
        symbol: str = "",
        direction: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> List[Signal]:
        rows = self._store.list_signals(symbol, direction, limit, offset)
        return [Signal.from_dict(r) for r in rows]

    def count_signals(self, symbol: str = "", direction: str = "") -> int:
        return self._store.count_signals(symbol, direction)

    def list_versions(self, signal_id: str = "") -> List[SignalVersion]:
        rows = self._store.list_versions(signal_id)
        return [SignalVersion.from_dict(r) for r in rows]

    def get_version(self, version_id: str) -> Optional[SignalVersion]:
        row = self._store.get_version(version_id)
        return SignalVersion.from_dict(row) if row else None


# ---- 模块级单例 ----

_registry: Optional[SignalRegistry] = None


def get_signal_registry() -> SignalRegistry:
    global _registry
    if _registry is None:
        _registry = SignalRegistry()
    return _registry
