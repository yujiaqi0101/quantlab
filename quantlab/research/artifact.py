"""
ArtifactStore — V4.5 研究产物存储

职责：
  - 保存研究结果：chart / table / factor / notebook output
  - 每个产物关联到 experiment_id
  - 磁盘持久化 + 元数据索引
  - 支持 parquet / csv / png / json 格式

用法：
    store = ArtifactStore(store_dir="storage/artifacts")
    store.save("scatter.png", data=png_bytes, kind="chart",
               experiment_id="exp_abc123")
    store.save("correlation.csv", data=df_corr, kind="table")

    artifacts = store.list_artifacts(experiment_id="exp_abc123")
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.research.artifact")


# ------------------------------------------------------------------
# Artifact
# ------------------------------------------------------------------
@dataclass(slots=True)
class Artifact:
    """研究产物元数据"""
    artifact_id: str
    name: str
    kind: str              # "chart" / "table" / "factor" / "notebook_output" / "custom"
    format: str            # "parquet" / "csv" / "png" / "json" / "pkl"
    path: str              # 磁盘路径
    experiment_id: str = ""
    session_id: str = ""
    created_at: str = ""
    description: str = ""
    tags: str = ""
    size_bytes: int = 0


# ------------------------------------------------------------------
# ArtifactStore
# ------------------------------------------------------------------
class ArtifactStore:
    """
    研究产物存储

    目录结构：
      store_dir/
        _index.json          # 全局索引
        {artifact_id}/
          data.parquet       # 或 .csv / .png / .json
          meta.json          # 单条元数据
    """

    def __init__(self, store_dir: str = "storage/artifacts") -> None:
        self.store_dir = store_dir
        self._index: Dict[str, Artifact] = {}
        os.makedirs(store_dir, exist_ok=True)
        self._load_index()

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------
    def save(
        self,
        name: str,
        data: Any,
        kind: str = "custom",
        format: str = "",
        experiment_id: str = "",
        session_id: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Artifact:
        """
        保存研究产物

        自动推断 format：
          - DataFrame → parquet
          - bytes → png（如果 name 以 .png 结尾）
          - dict → json
          - 其它 → pkl
        """
        artifact_id = _new_id()
        fmt = format or _infer_format(name, data)
        art_dir = os.path.join(self.store_dir, artifact_id)
        os.makedirs(art_dir, exist_ok=True)

        # 写数据
        data_path = os.path.join(art_dir, f"data.{fmt}")
        _write_data(data_path, data, fmt)

        # 元数据
        size = os.path.getsize(data_path) if os.path.exists(data_path) else 0
        art = Artifact(
            artifact_id=artifact_id,
            name=name,
            kind=kind,
            format=fmt,
            path=data_path,
            experiment_id=experiment_id,
            session_id=session_id,
            created_at=_now_iso(),
            description=description,
            tags=",".join(tags or []),
            size_bytes=size,
        )
        # 写单条 meta
        meta_path = os.path.join(art_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(asdict(art), f, indent=2, ensure_ascii=False)

        self._index[artifact_id] = art
        self._save_index()
        logger.info(f"artifact saved: {name} [{kind}/{fmt}] id={artifact_id}")
        return art

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def load(self, artifact_id: str) -> Optional[Any]:
        """加载产物数据"""
        art = self._index.get(artifact_id)
        if art is None:
            return None
        return _read_data(art.path, art.format)

    def load_by_name(self, name: str) -> Optional[Any]:
        """按 name 加载（返回第一个匹配）"""
        for art in self._index.values():
            if art.name == name:
                return self.load(art.artifact_id)
        return None

    def get_metadata(self, artifact_id: str) -> Optional[Artifact]:
        return self._index.get(artifact_id)

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------
    def delete(self, artifact_id: str) -> bool:
        art = self._index.pop(artifact_id, None)
        if art is None:
            return False
        art_dir = os.path.join(self.store_dir, artifact_id)
        if os.path.isdir(art_dir):
            shutil.rmtree(art_dir)
        self._save_index()
        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def list_artifacts(
        self,
        kind: Optional[str] = None,
        experiment_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Artifact]:
        results = list(self._index.values())
        if kind:
            results = [a for a in results if a.kind == kind]
        if experiment_id:
            results = [a for a in results if a.experiment_id == experiment_id]
        if session_id:
            results = [a for a in results if a.session_id == session_id]
        if tag:
            results = [a for a in results if tag in a.tags]
        return results

    def search(self, keyword: str) -> List[Artifact]:
        kw = keyword.lower()
        return [
            a for a in self._index.values()
            if kw in a.name.lower()
            or kw in a.description.lower()
            or kw in a.kind.lower()
            or kw in a.tags.lower()
        ]

    def stats(self) -> Dict[str, Any]:
        by_kind: Dict[str, int] = {}
        total_size = 0
        for a in self._index.values():
            by_kind[a.kind] = by_kind.get(a.kind, 0) + 1
            total_size += a.size_bytes
        return {
            "total_artifacts": len(self._index),
            "by_kind": by_kind,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
        }

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _index_path(self) -> str:
        return os.path.join(self.store_dir, "_index.json")

    def _load_index(self):
        ip = self._index_path()
        if not os.path.exists(ip):
            return
        try:
            with open(ip, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, d in raw.items():
                self._index[k] = Artifact(**d)
        except Exception:
            self._index = {}

    def _save_index(self):
        ip = self._index_path()
        try:
            raw = {k: asdict(v) for k, v in self._index.items()}
            with open(ip, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"artifact index save fail: {e}")


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    import uuid
    return "art_" + uuid.uuid4().hex[:8]


def _infer_format(name: str, data: Any) -> str:
    if isinstance(data, pd.DataFrame):
        return "parquet"
    if isinstance(data, bytes):
        if name.lower().endswith(".png"):
            return "png"
        if name.lower().endswith(".jpg"):
            return "jpg"
        return "bin"
    if isinstance(data, dict):
        return "json"
    return "pkl"


def _write_data(path: str, data: Any, fmt: str):
    if fmt == "parquet" and isinstance(data, pd.DataFrame):
        data.to_parquet(path)
    elif fmt == "csv" and isinstance(data, pd.DataFrame):
        data.to_csv(path)
    elif fmt in ("png", "jpg", "bin") and isinstance(data, bytes):
        with open(path, "wb") as f:
            f.write(data)
    elif fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    else:
        import pickle
        with open(path, "wb") as f:
            pickle.dump(data, f)


def _read_data(path: str, fmt: str) -> Any:
    if not os.path.exists(path):
        return None
    if fmt == "parquet":
        return pd.read_parquet(path)
    elif fmt == "csv":
        return pd.read_csv(path, index_col=0)
    elif fmt in ("png", "jpg", "bin"):
        with open(path, "rb") as f:
            return f.read()
    elif fmt == "json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)
