"""
ML Storage — SQLite + Parquet 持久化

ML Lab M2 第十四层：所有 ML 产物必须有持久化

  MLStore       — SQLite 统一存储（datasets / features / labels / experiments / models）
  ParquetStore  — Parquet 文件存储（大规模特征/标签数据）
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.ml.storage")

# 默认数据库路径
DEFAULT_DB_PATH = "storage/ml_lab.db"
DEFAULT_PARQUET_DIR = "storage/parquet"


class MLStore:
    """
    ML Lab 统一 SQLite 存储

    用法：
        store = get_ml_store()
        with store._cursor() as cur:
            cur.execute("SELECT * FROM datasets")
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器"""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_tables(self) -> None:
        """初始化所有表"""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id     TEXT PRIMARY KEY,
                    name           TEXT DEFAULT '',
                    symbols        TEXT DEFAULT '',
                    frequency      TEXT DEFAULT '1h',
                    start_date     TEXT DEFAULT '',
                    end_date       TEXT DEFAULT '',
                    description    TEXT DEFAULT '',
                    row_count      INTEGER DEFAULT 0,
                    created_at     TEXT DEFAULT '',
                    asset_type     TEXT DEFAULT 'crypto',
                    storage_path   TEXT DEFAULT '',
                    storage_format TEXT DEFAULT 'parquet',
                    schema_json    TEXT DEFAULT '{}',
                    tags_json      TEXT DEFAULT '[]',
                    is_ohlcv       INTEGER DEFAULT 1,
                    coverage       TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS feature_sets (
                    feature_set_id TEXT PRIMARY KEY,
                    name           TEXT,
                    features       TEXT DEFAULT '[]',
                    description    TEXT DEFAULT '',
                    created_at     TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS label_sets (
                    label_set_id TEXT PRIMARY KEY,
                    name         TEXT,
                    labels       TEXT DEFAULT '[]',
                    description  TEXT DEFAULT '',
                    created_at   TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS training_jobs (
                    job_id       TEXT PRIMARY KEY,
                    dataset_id   TEXT DEFAULT '',
                    feature_set_id TEXT DEFAULT '',
                    label_set_id TEXT DEFAULT '',
                    model_type   TEXT DEFAULT '',
                    status       TEXT DEFAULT 'PENDING',
                    metrics      TEXT DEFAULT '{}',
                    created_at   TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS models (
                    model_id     TEXT PRIMARY KEY,
                    name         TEXT,
                    model_type   TEXT DEFAULT '',
                    version      TEXT DEFAULT '1',
                    metrics      TEXT DEFAULT '{}',
                    status       TEXT DEFAULT 'ACTIVE',
                    created_at   TEXT DEFAULT ''
                );
            """)
            # 迁移：为旧表添加新列（如果不存在）
            self._migrate_datasets_table(cur)
        logger.info(f"MLStore initialized: {self.db_path}")

    def _migrate_datasets_table(self, cur) -> None:
        """迁移 datasets 表，添加统一存储后的新列"""
        new_columns = [
            ("asset_type", "TEXT DEFAULT 'crypto'"),
            ("storage_path", "TEXT DEFAULT ''"),
            ("storage_format", "TEXT DEFAULT 'parquet'"),
            ("schema_json", "TEXT DEFAULT '{}'"),
            ("tags_json", "TEXT DEFAULT '[]'"),
            ("is_ohlcv", "INTEGER DEFAULT 1"),
            ("coverage", "TEXT DEFAULT ''"),
        ]
        for col_name, col_def in new_columns:
            try:
                cur.execute(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass  # 列已存在，跳过

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ---- Label Set 持久化 ----

    def list_label_sets(self) -> list:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM label_sets")
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["labels"] = json.loads(d.get("labels", "[]"))
            except (json.JSONDecodeError, TypeError):
                d["labels"] = []
            # 映射字段名以匹配 LabelSetRegistry 期望的格式
            mapped = {
                "ls_id": d.get("label_set_id", ""),
                "name": d.get("name", ""),
                "label_id": d.get("label_set_id", ""),
                "description": d.get("description", ""),
                "version": "1",
                "label_type": "regression",
                "classes": [],
                "tags": [],
                "created_at": d.get("created_at", ""),
            }
            result.append(mapped)
        return result

    def save_label_set(self, data: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO label_sets (label_set_id, name, labels, description, created_at) VALUES (?,?,?,?,?)",
                [
                    data.get("ls_id", data.get("label_set_id", "")),
                    data.get("name", ""),
                    json.dumps(data.get("labels", [])),
                    data.get("description", ""),
                    data.get("created_at", ""),
                ],
            )

    def delete_label_set_by_name(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM label_sets WHERE name = ?", [name])

    # ---- Feature Set 持久化 ----

    def list_feature_sets(self) -> list:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM feature_sets")
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["features"] = json.loads(d.get("features", "[]"))
            except (json.JSONDecodeError, TypeError):
                d["features"] = []
            mapped = {
                "fs_id": d.get("feature_set_id", ""),
                "name": d.get("name", ""),
                "feature_ids": d.get("features", []) if isinstance(d.get("features"), list) else [],
                "description": d.get("description", ""),
                "version": "1",
                "tags": [],
                "created_at": d.get("created_at", ""),
            }
            result.append(mapped)
        return result

    def save_feature_set(self, data: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO feature_sets (feature_set_id, name, features, description, created_at) VALUES (?,?,?,?,?)",
                [
                    data.get("fs_id", data.get("feature_set_id", "")),
                    data.get("name", ""),
                    json.dumps(data.get("feature_ids", data.get("features", []))),
                    data.get("description", ""),
                    data.get("created_at", ""),
                ],
            )

    def delete_feature_set_by_name(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM feature_sets WHERE name = ?", [name])

    # ---- Dataset 持久化 ----

    def list_datasets(self) -> list:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM datasets")
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # 解析 JSON 字段
            try:
                tags = json.loads(d.get("tags_json", "[]"))
            except (json.JSONDecodeError, TypeError):
                tags = []
            try:
                schema = json.loads(d.get("schema_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                schema = {"columns": [], "column_names": [], "has_ohlcv": True}
            mapped = {
                "dataset_id": d.get("dataset_id", ""),
                "name": d.get("name", ""),
                "symbols": d.get("symbols", ""),
                "start_date": d.get("start_date", ""),
                "end_date": d.get("end_date", ""),
                "frequency": d.get("frequency", "1h"),
                "description": d.get("description", ""),
                "tags": tags,
                "created_at": d.get("created_at", ""),
                "has_data": d.get("row_count", 0) > 0,
                # 统一存储扩展字段
                "asset_type": d.get("asset_type", "crypto"),
                "storage_path": d.get("storage_path", ""),
                "storage_format": d.get("storage_format", "parquet"),
                "schema": schema,
                "is_ohlcv": bool(d.get("is_ohlcv", 1)),
                "coverage": d.get("coverage", ""),
            }
            result.append(mapped)
        return result

    def save_dataset(self, data: dict, has_data: bool = False) -> None:
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO datasets
                (dataset_id, name, symbols, frequency, start_date, end_date,
                 description, row_count, created_at,
                 asset_type, storage_path, storage_format, schema_json, tags_json, is_ohlcv, coverage)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    data.get("dataset_id", ""),
                    data.get("name", ""),
                    data.get("symbols", "") if isinstance(data.get("symbols"), str) else json.dumps(data.get("symbols", [])),
                    data.get("frequency", "1h"),
                    data.get("start_date", ""),
                    data.get("end_date", ""),
                    data.get("description", ""),
                    data.get("row_count", 0),
                    data.get("created_at", ""),
                    data.get("asset_type", "crypto"),
                    data.get("storage_path", ""),
                    data.get("storage_format", "parquet"),
                    json.dumps(data.get("schema", {"columns": [], "column_names": [], "has_ohlcv": True})),
                    json.dumps(data.get("tags", [])),
                    1 if data.get("is_ohlcv", True) else 0,
                    data.get("coverage", ""),
                ],
            )

    def delete_dataset(self, dataset_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM datasets WHERE dataset_id = ?", [dataset_id])

    def update_dataset_has_data(self, dataset_id: str, has_data: bool) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE datasets SET row_count = ? WHERE dataset_id = ?", [1 if has_data else 0, dataset_id])


class ParquetStore:
    """
    Parquet 文件存储（大规模特征/标签数据）

    用法：
        store = get_parquet_store()
        store.save("features", "fs_001", df)
        df = store.load("features", "fs_001")
    """

    def __init__(self, root_dir: str = DEFAULT_PARQUET_DIR) -> None:
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def _path(self, category: str, key: str) -> str:
        dir_path = os.path.join(self.root_dir, category)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{key}.parquet")

    def save(self, category: str, key: str, df: pd.DataFrame) -> str:
        path = self._path(category, key)
        df.to_parquet(path, index=False)
        logger.info(f"Parquet saved: {path} ({len(df)} rows)")
        return path

    def load(self, category: str, key: str) -> Optional[pd.DataFrame]:
        path = self._path(category, key)
        if not os.path.exists(path):
            return None
        return pd.read_parquet(path)

    def exists(self, category: str, key: str) -> bool:
        return os.path.exists(self._path(category, key))

    def delete(self, category: str, key: str) -> bool:
        path = self._path(category, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_keys(self, category: str) -> List[str]:
        dir_path = os.path.join(self.root_dir, category)
        if not os.path.isdir(dir_path):
            return []
        return [
            f[:-8]  # strip .parquet
            for f in os.listdir(dir_path)
            if f.endswith(".parquet")
        ]

    # ---- Dataset 专用别名 ----

    def save_dataset_data(self, dataset_id: str, df: pd.DataFrame) -> str:
        return self.save("datasets", dataset_id, df)

    def load_dataset_data(self, dataset_id: str) -> Optional[pd.DataFrame]:
        return self.load("datasets", dataset_id)


# ------------------------------------------------------------------
# 单例
# ------------------------------------------------------------------

_ml_store: Optional[MLStore] = None
_parquet_store: Optional[ParquetStore] = None


def get_ml_store(db_path: str = DEFAULT_DB_PATH) -> MLStore:
    """获取 MLStore 单例"""
    global _ml_store
    if _ml_store is None:
        _ml_store = MLStore(db_path)
    return _ml_store


def get_parquet_store(root_dir: str = DEFAULT_PARQUET_DIR) -> ParquetStore:
    """获取 ParquetStore 单例"""
    global _parquet_store
    if _parquet_store is None:
        _parquet_store = ParquetStore(root_dir)
    return _parquet_store
