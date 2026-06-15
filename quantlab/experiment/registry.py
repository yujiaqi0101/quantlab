"""
V4.4 Experiment Management — Registry

实验注册中心。
统一管理所有实验的注册、索引、查找。

内部索引：
  strategy → [experiment_ids]
  dataset  → [experiment_ids]
  tag      → [experiment_ids]
  date     → [experiment_ids]
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

from .artifact import ExperimentArtifact
from .tags import TagManager

logger = logging.getLogger("quantlab.experiment.registry")


class ExperimentRegistry:
    """
    实验注册中心

    统一访问入口，封装 DB + Artifact + Tags。

    用法：
        registry = ExperimentRegistry(db=database)
        registry.register(experiment_dict)
        exp = registry.get("exp_001")
        experiments = registry.list(strategy="ma_cross")
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db
        self._tag_manager = TagManager(db=db)
        # 内存索引（加速查询）
        self._by_strategy: Dict[str, Set[str]] = {}
        self._by_dataset: Dict[str, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}

    @property
    def tag_manager(self) -> TagManager:
        return self._tag_manager

    # ---------------------------------------------------------
    # 注册
    # ---------------------------------------------------------
    def register(self, experiment: Dict[str, Any]) -> None:
        """
        注册实验到索引

        参数：
          experiment  实验字典（必须含 id, strategy, dataset_id, tags）
        """
        exp_id = experiment.get("id", "")
        strategy = experiment.get("strategy", "")
        dataset_id = experiment.get("dataset_id", "")
        tags = experiment.get("tags", [])

        if not exp_id:
            return

        # 索引
        if strategy:
            self._by_strategy.setdefault(strategy, set()).add(exp_id)
        if dataset_id:
            self._by_dataset.setdefault(dataset_id, set()).add(exp_id)
        for tag in tags:
            self._by_tag.setdefault(tag, set()).add(exp_id)

    def rebuild_index(self) -> int:
        """从 DB 重建内存索引"""
        if self._db is None:
            return 0

        self._by_strategy.clear()
        self._by_dataset.clear()
        self._by_tag.clear()

        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, strategy, dataset_id, tags_json FROM experiments"
            ).fetchall()

        for row in rows:
            exp_id = row["id"]
            strategy = row["strategy"]
            dataset_id = row["dataset_id"] or ""
            try:
                tags = json.loads(row["tags_json"] or "[]")
            except Exception:
                tags = []

            if strategy:
                self._by_strategy.setdefault(strategy, set()).add(exp_id)
            if dataset_id:
                self._by_dataset.setdefault(dataset_id, set()).add(exp_id)
            for tag in tags:
                self._by_tag.setdefault(tag, set()).add(exp_id)

        return len(rows)

    # ---------------------------------------------------------
    # 查询
    # ---------------------------------------------------------
    def get(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验详情"""
        if self._db is None:
            return None

        with self._db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    e.id, e.name, e.strategy,
                    e.params_json, e.created_at,
                    e.tag, e.note,
                    e.dataset_id, e.dataset_version,
                    e.tags_json, e.strategy_version,
                    r.final_equity, r.total_return,
                    r.sharpe, r.max_drawdown,
                    r.trade_count, r.win_rate,
                    r.source, r.extras_json
                FROM experiments e
                LEFT JOIN results r ON e.id = r.experiment_id
                WHERE e.id = ?
                """,
                (experiment_id,),
            ).fetchone()

        if row is None:
            return None

        d = dict(row)
        try:
            d["params"] = json.loads(d.pop("params_json", "{}"))
        except Exception:
            d["params"] = {}
        try:
            d["extras"] = json.loads(d.pop("extras_json", "{}"))
        except Exception:
            d["extras"] = {}
        try:
            d["tags"] = json.loads(d.pop("tags_json", "[]"))
        except Exception:
            d["tags"] = []

        # 加载 artifact 信息
        artifact = ExperimentArtifact(experiment_id)
        d["artifact"] = artifact.to_dict()

        return d

    def list(
        self,
        *,
        strategy: Optional[str] = None,
        dataset_id: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出实验（可按策略/数据集/标签过滤）"""
        if self._db is None:
            return []

        where = []
        params: List = []

        if strategy:
            where.append("e.strategy = ?")
            params.append(strategy)
        if dataset_id:
            where.append("e.dataset_id = ?")
            params.append(dataset_id)
        if tag:
            where.append("e.tags_json LIKE ?")
            params.append(f'%"{tag}"%')

        sql = """
            SELECT
                e.id, e.name, e.strategy,
                e.params_json, e.created_at,
                e.tag, e.note,
                e.dataset_id, e.dataset_version,
                e.tags_json, e.strategy_version,
                r.sharpe, r.total_return,
                r.max_drawdown, r.trade_count,
                r.win_rate
            FROM experiments e
            LEFT JOIN results r ON e.id = r.experiment_id
        """

        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)

        with self._db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        result = []
        for row in rows:
            d = dict(row)
            try:
                d["params"] = json.loads(d.pop("params_json", "{}"))
            except Exception:
                d["params"] = {}
            try:
                d["tags"] = json.loads(d.pop("tags_json", "[]"))
            except Exception:
                d["tags"] = []
            result.append(d)

        return result

    def delete(self, experiment_id: str) -> bool:
        """删除实验"""
        if self._db is None:
            return False

        with self._db.get_connection() as conn:
            conn.execute(
                "DELETE FROM experiments WHERE id = ?",
                (experiment_id,),
            )

        # 清理索引
        for s in self._by_strategy.values():
            s.discard(experiment_id)
        for s in self._by_dataset.values():
            s.discard(experiment_id)
        for s in self._by_tag.values():
            s.discard(experiment_id)

        return True

    # ---------------------------------------------------------
    # 索引查询
    # ---------------------------------------------------------
    def list_by_strategy(self, strategy: str) -> List[str]:
        """按策略查实验 ID"""
        return list(self._by_strategy.get(strategy, set()))

    def list_by_dataset(self, dataset_id: str) -> List[str]:
        """按数据集查实验 ID"""
        return list(self._by_dataset.get(dataset_id, set()))

    def list_by_tag(self, tag: str) -> List[str]:
        """按标签查实验 ID"""
        return list(self._by_tag.get(tag, set()))

    def list_strategies(self) -> List[str]:
        """列出所有策略"""
        return list(self._by_strategy.keys())

    def list_datasets(self) -> List[str]:
        """列出所有数据集"""
        return list(self._by_dataset.keys())

    def count(self) -> int:
        """实验总数"""
        all_ids: Set[str] = set()
        for s in self._by_strategy.values():
            all_ids.update(s)
        return len(all_ids)
