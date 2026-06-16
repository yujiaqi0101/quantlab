"""
Alpha Store — SQLite 持久化

保存 Alpha 记录，支持：
  - CRUD
  - 按指标筛选
  - 按标签/状态查询
  - 排名查询
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd

from .alpha import Alpha, AlphaMetrics, AlphaRecord, AlphaStatus

logger = logging.getLogger("quantlab.alpha.store")


class AlphaStore:
    """
    Alpha 持久化存储

    使用 SQLite 存储 Alpha 记录
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_dir = os.path.join(os.path.expanduser("~"), ".quantlab")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "alpha.db")

        self._db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alphas (
                    alpha_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    alpha_type TEXT NOT NULL DEFAULT 'threshold',
                    status TEXT NOT NULL DEFAULT 'draft',
                    factor_name TEXT NOT NULL DEFAULT '',
                    signal_expr TEXT NOT NULL DEFAULT '',
                    lower REAL,
                    upper REAL,
                    factor_name_2 TEXT,
                    components_json TEXT DEFAULT '[]',
                    combine_method TEXT,
                    -- 指标
                    ic REAL DEFAULT 0,
                    rank_ic REAL DEFAULT 0,
                    ir REAL DEFAULT 0,
                    coverage REAL DEFAULT 0,
                    turnover REAL DEFAULT 0,
                    forward_ret_1d REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    sharpe REAL DEFAULT 0,
                    score REAL DEFAULT 0,
                    -- 元数据
                    tags_json TEXT DEFAULT '[]',
                    note TEXT DEFAULT '',
                    dataset_id TEXT DEFAULT '',
                    created_at TEXT DEFAULT '',
                    evaluated_at TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alpha_factor ON alphas(factor_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alpha_status ON alphas(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alpha_score ON alphas(score DESC)
            """)

    # ---- CRUD ----

    def save(self, alpha: Alpha) -> None:
        """保存 Alpha（upsert）"""
        record = AlphaRecord.from_alpha(alpha)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alphas (
                    alpha_id, name, alpha_type, status,
                    factor_name, signal_expr, lower, upper, factor_name_2,
                    components_json, combine_method,
                    ic, rank_ic, ir, coverage, turnover, forward_ret_1d,
                    win_rate, sharpe, score,
                    tags_json, note, dataset_id, created_at, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.alpha_id, record.name, record.alpha_type, record.status,
                record.factor_name, record.signal_expr, record.lower, record.upper,
                record.factor_name_2, record.components_json, record.combine_method,
                record.ic, record.rank_ic, record.ir, record.coverage,
                record.turnover, record.forward_ret_1d,
                record.win_rate, record.sharpe, record.score,
                record.tags_json, record.note, record.dataset_id,
                record.created_at, record.evaluated_at,
            ))

    def save_batch(self, alphas: List[Alpha]) -> int:
        """批量保存"""
        count = 0
        for alpha in alphas:
            self.save(alpha)
            count += 1
        logger.info(f"saved {count} alphas")
        return count

    def get(self, alpha_id: str) -> Optional[Alpha]:
        """获取单个 Alpha"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM alphas WHERE alpha_id = ?", (alpha_id,)
            ).fetchone()
            if row is None:
                return None
            return AlphaRecord(**dict(row)).to_alpha()

    def delete(self, alpha_id: str) -> bool:
        """删除 Alpha"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM alphas WHERE alpha_id = ?", (alpha_id,)
            )
            return cursor.rowcount > 0

    # ---- 查询 ----

    def list_alphas(
        self,
        status: Optional[str] = None,
        factor_name: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[Alpha]:
        """列出 Alpha"""
        with self._get_conn() as conn:
            query = "SELECT * FROM alphas WHERE 1=1"
            params: List[Any] = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if factor_name:
                query += " AND factor_name = ?"
                params.append(factor_name)
            if tag:
                query += " AND tags_json LIKE ?"
                params.append(f'%"{tag}"%')

            query += " ORDER BY score DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [AlphaRecord(**dict(r)).to_alpha() for r in rows]

    def search(
        self,
        q: str = "",
        ic_min: Optional[float] = None,
        ir_min: Optional[float] = None,
        coverage_min: Optional[float] = None,
        score_min: Optional[float] = None,
        limit: int = 100,
    ) -> List[Alpha]:
        """多条件搜索"""
        with self._get_conn() as conn:
            query = "SELECT * FROM alphas WHERE 1=1"
            params: List[Any] = []

            if q:
                query += " AND (name LIKE ? OR factor_name LIKE ? OR signal_expr LIKE ?)"
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
            if ic_min is not None:
                query += " AND ic >= ?"
                params.append(ic_min)
            if ir_min is not None:
                query += " AND ir >= ?"
                params.append(ir_min)
            if coverage_min is not None:
                query += " AND coverage >= ?"
                params.append(coverage_min)
            if score_min is not None:
                query += " AND score >= ?"
                params.append(score_min)

            query += " ORDER BY score DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [AlphaRecord(**dict(r)).to_alpha() for r in rows]

    def get_leaderboard(
        self,
        metric: str = "score",
        limit: int = 20,
        ascending: bool = False,
    ) -> List[Alpha]:
        """获取排行榜"""
        valid_metrics = {"score", "ic", "rank_ic", "ir", "coverage", "sharpe", "win_rate"}
        if metric not in valid_metrics:
            metric = "score"

        order = "ASC" if ascending else "DESC"
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM alphas WHERE status != 'archived' ORDER BY {metric} {order} LIMIT ?",
                (limit,),
            ).fetchall()
            return [AlphaRecord(**dict(r)).to_alpha() for r in rows]

    def update_status(self, alpha_id: str, status: str) -> bool:
        """更新状态"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE alphas SET status = ? WHERE alpha_id = ?",
                (status, alpha_id),
            )
            return cursor.rowcount > 0

    def update_tags(self, alpha_id: str, tags: List[str]) -> bool:
        """更新标签"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE alphas SET tags_json = ? WHERE alpha_id = ?",
                (json.dumps(tags), alpha_id),
            )
            return cursor.rowcount > 0

    def update_note(self, alpha_id: str, note: str) -> bool:
        """更新备注"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE alphas SET note = ? WHERE alpha_id = ?",
                (note, alpha_id),
            )
            return cursor.rowcount > 0

    def count_by_status(self) -> Dict[str, int]:
        """按状态统计"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM alphas GROUP BY status"
            ).fetchall()
            return {r["status"]: r["cnt"] for r in rows}

    def get_stats(self) -> Dict[str, Any]:
        """全局统计"""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM alphas").fetchone()["cnt"]
            candidates = conn.execute(
                "SELECT COUNT(*) as cnt FROM alphas WHERE status = 'candidate'"
            ).fetchone()["cnt"]

            top_ic = conn.execute(
                "SELECT name, ic FROM alphas ORDER BY ic DESC LIMIT 1"
            ).fetchone()
            top_ir = conn.execute(
                "SELECT name, ir FROM alphas ORDER BY ir DESC LIMIT 1"
            ).fetchone()

            return {
                "total": total,
                "candidates": candidates,
                "top_ic": dict(top_ic) if top_ic else None,
                "top_ir": dict(top_ir) if top_ir else None,
            }

    def get_factor_names(self) -> List[str]:
        """获取所有因子名"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT factor_name FROM alphas ORDER BY factor_name"
            ).fetchall()
            return [r["factor_name"] for r in rows]
