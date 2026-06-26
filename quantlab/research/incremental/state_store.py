"""
StateStore — 节点状态持久化 (checkpoint)

支持节点 save_state / load_state，用于增量计算的检查点。
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class NodeState:
    """单个节点的状态 (checkpoint)。"""
    node_id: str
    node_version: str = "1.0.0"
    data: Any = None  # 序列化数据 (ResearchFrame)
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    inputs_hash: str = ""  # 输入数据的 hash

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_version": self.node_version,
            "meta": self.meta,
            "timestamp": self.timestamp,
            "inputs_hash": self.inputs_hash,
        }


class StateStore:
    """节点状态存储 (Parquet + JSON)。"""

    def __init__(self, base_dir: str = ".quantlab_state") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, state: NodeState) -> None:
        """保存节点状态。"""
        # JSON: meta
        meta_path = self._meta_path(state.node_id, state.node_version)
        meta_path.write_text(json.dumps(state.to_dict(), default=str))
        # Parquet: data (如果是 DataFrame)
        if isinstance(state.data, pd.DataFrame):
            data_path = self._data_path(state.node_id, state.node_version)
            state.data.reset_index().to_parquet(data_path, index=False)
        elif state.data is not None:
            # pickle 兜底
            pickle_path = self._pickle_path(state.node_id, state.node_version)
            pickle_path.write_bytes(pickle.dumps(state.data))

    def load(
        self, node_id: str, version: str = "1.0.0"
    ) -> Optional[NodeState]:
        """加载节点状态。"""
        meta_path = self._meta_path(node_id, version)
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            return None
        # 加载 data
        data = None
        data_path = self._data_path(node_id, version)
        pickle_path = self._pickle_path(node_id, version)
        if data_path.exists():
            try:
                df = pd.read_parquet(data_path)
                if "datetime" in df.columns and "symbol" in df.columns:
                    df = df.set_index(["datetime", "symbol"])
                data = df
            except Exception:
                pass
        elif pickle_path.exists():
            try:
                data = pickle.loads(pickle_path.read_bytes())
            except Exception:
                pass
        return NodeState(
            node_id=meta["node_id"],
            node_version=meta["node_version"],
            data=data,
            meta=meta.get("meta", {}),
            timestamp=meta.get("timestamp", 0.0),
            inputs_hash=meta.get("inputs_hash", ""),
        )

    def exists(self, node_id: str, version: str = "1.0.0") -> bool:
        return self._meta_path(node_id, version).exists()

    def clear(self, node_id: str, version: str = "1.0.0") -> None:
        for p in [
            self._meta_path(node_id, version),
            self._data_path(node_id, version),
            self._pickle_path(node_id, version),
        ]:
            if p.exists():
                p.unlink()

    def _meta_path(self, node_id: str, version: str) -> Path:
        return self._base / f"{node_id}_{version}.meta.json"

    def _data_path(self, node_id: str, version: str) -> Path:
        return self._base / f"{node_id}_{version}.parquet"

    def _pickle_path(self, node_id: str, version: str) -> Path:
        return self._base / f"{node_id}_{version}.pkl"


__all__ = ["NodeState", "StateStore"]
