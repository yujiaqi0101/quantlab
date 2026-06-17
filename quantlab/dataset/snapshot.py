"""
Dataset Snapshot — 数据快照（可复现性保证）

研究必须可复现。Snapshot 在某个时间点冻结数据状态，
实验永远绑定 snapshot_id，哪怕两年后结果还能复现。

例如：
  2026-06-17 当天数据 → Snapshot_001
  实验记录: experiment.snapshot_id = "snap_20260617_001"
  两年后：load_snapshot("snap_20260617_001") → 完全相同的数据

用法：
    manager = SnapshotManager()
    snap = manager.create("btcusdt_1m", data, note="修复前快照")
    restored = manager.load(snap.snapshot_id)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.dataset.snapshot")


# ------------------------------------------------------------------
# Snapshot
# ------------------------------------------------------------------

@dataclass(slots=True)
class Snapshot:
    """数据快照"""
    snapshot_id: str             # snap_20260617_001
    dataset_id: str              # btcusdt_1m
    created_at: str              # 2026-06-17T10:00:00
    version: str = "1.0.0"       # 数据集版本
    rows: int = 0
    columns: int = 0
    symbols: str = ""            # "BTCUSDT,ETHUSDT"
    data_hash: str = ""          # 数据指纹
    storage_path: str = ""       # 快照存储路径
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# SnapshotManager
# ------------------------------------------------------------------

class SnapshotManager:
    """
    快照管理器

    - create(): 创建快照（冻结当前数据）
    - load(): 加载快照（恢复数据）
    - list(): 列出所有快照
    - verify(): 验证快照完整性
    """

    def __init__(self, store_dir: str = "storage/snapshots") -> None:
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self._index: Dict[str, Snapshot] = {}
        self._load_index()

    # ---- 创建 ----

    def create(
        self,
        dataset_id: str,
        data: Dict[str, pd.DataFrame],
        note: str = "",
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """
        创建快照

        参数：
          dataset_id  数据集 ID
          data        {symbol: DataFrame}
          note        备注
          version     数据集版本
          metadata    额外元数据
        """
        import datetime

        # 生成 snapshot_id
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{dataset_id}_{ts}"

        # 存储路径
        snap_dir = os.path.join(self.store_dir, snapshot_id)
        os.makedirs(snap_dir, exist_ok=True)

        # 计算数据指纹和统计
        total_rows = 0
        total_cols = 0
        symbols = []
        hash_parts = []

        for sym, df in data.items():
            symbols.append(sym)
            total_rows += len(df)
            total_cols = max(total_cols, len(df.columns))

            # 保存为 parquet
            df.to_parquet(os.path.join(snap_dir, f"{sym}.parquet"))

            # 数据指纹
            hash_parts.append(f"{sym}:{len(df)}:{_df_hash(df)}")

        data_hash = hashlib.md5("|".join(hash_parts).encode()).hexdigest()[:16]

        snap = Snapshot(
            snapshot_id=snapshot_id,
            dataset_id=dataset_id,
            created_at=datetime.datetime.now().isoformat(timespec="seconds"),
            version=version,
            rows=total_rows,
            columns=total_cols,
            symbols=",".join(symbols),
            data_hash=data_hash,
            storage_path=snap_dir,
            note=note,
            metadata=metadata or {},
        )

        self._index[snapshot_id] = snap
        self._save_index()
        logger.info(f"snapshot created: {snapshot_id} ({total_rows} rows, hash={data_hash})")
        return snap

    # ---- 加载 ----

    def load(self, snapshot_id: str) -> Dict[str, pd.DataFrame]:
        """加载快照数据"""
        snap = self._index.get(snapshot_id)
        if not snap:
            raise KeyError(f"snapshot not found: {snapshot_id}")

        snap_dir = snap.storage_path
        if not os.path.isdir(snap_dir):
            raise FileNotFoundError(f"snapshot directory missing: {snap_dir}")

        data = {}
        for sym in snap.symbols.split(","):
            fpath = os.path.join(snap_dir, f"{sym}.parquet")
            if os.path.exists(fpath):
                data[sym] = pd.read_parquet(fpath)
        return data

    # ---- 查询 ----

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        return self._index.get(snapshot_id)

    def list(
        self,
        dataset_id: Optional[str] = None,
    ) -> List[Snapshot]:
        if dataset_id:
            return [s for s in self._index.values() if s.dataset_id == dataset_id]
        return list(self._index.values())

    def delete(self, snapshot_id: str) -> bool:
        snap = self._index.pop(snapshot_id, None)
        if not snap:
            return False
        if os.path.isdir(snap.storage_path):
            shutil.rmtree(snap.storage_path, ignore_errors=True)
        self._save_index()
        logger.info(f"snapshot deleted: {snapshot_id}")
        return True

    # ---- 验证 ----

    def verify(self, snapshot_id: str) -> Dict[str, Any]:
        """验证快照完整性"""
        snap = self._index.get(snapshot_id)
        if not snap:
            return {"valid": False, "error": "snapshot not found"}

        snap_dir = snap.storage_path
        if not os.path.isdir(snap_dir):
            return {"valid": False, "error": "snapshot directory missing"}

        # 检查文件
        symbols = snap.symbols.split(",") if snap.symbols else []
        missing_files = []
        for sym in symbols:
            fpath = os.path.join(snap_dir, f"{sym}.parquet")
            if not os.path.exists(fpath):
                missing_files.append(sym)

        if missing_files:
            return {
                "valid": False,
                "error": f"missing files: {missing_files}",
            }

        # 验证数据指纹
        try:
            data = self.load(snapshot_id)
            hash_parts = []
            for sym in symbols:
                df = data.get(sym)
                if df is not None:
                    hash_parts.append(f"{sym}:{len(df)}:{_df_hash(df)}")

            current_hash = hashlib.md5("|".join(hash_parts).encode()).hexdigest()[:16]
            hash_match = current_hash == snap.data_hash

            return {
                "valid": True,
                "hash_match": hash_match,
                "expected_hash": snap.data_hash,
                "actual_hash": current_hash,
                "rows": sum(len(df) for df in data.values()),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ---- 持久化 ----

    def _index_path(self) -> str:
        return os.path.join(self.store_dir, "_index.json")

    def _save_index(self) -> None:
        data = {k: asdict(v) for k, v in self._index.items()}
        try:
            with open(self._index_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"snapshot index save fail: {e}")

    def _load_index(self) -> None:
        path = self._index_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, d in data.items():
                self._index[k] = Snapshot(**d)
        except Exception as e:
            logger.warning(f"snapshot index load fail: {e}")


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _df_hash(df: pd.DataFrame) -> str:
    """计算 DataFrame 指纹"""
    try:
        # 用 values 的哈希
        return hashlib.md5(
            pd.util.hash_pandas_object(df, index=True).values.tobytes()
        ).hexdigest()[:12]
    except Exception:
        # fallback: 行数+列名
        return hashlib.md5(
            f"{len(df)}:{','.join(str(c) for c in df.columns)}".encode()
        ).hexdigest()[:12]


# ---- 全局单例 ----

_manager: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    global _manager
    if _manager is None:
        _manager = SnapshotManager()
    return _manager
