"""
Experiment Tracker — 实验追踪

ML Lab 第五层：训练不能只保存模型，必须保存完整实验

  Experiment
    - experiment_id: EXP-001
    - dataset_id
    - feature_set_id
    - label_set_id
    - model_type
    - model_params
    - metrics
    - feature_importance
    - created_at
    - tags
    - notes

  以后能追溯：为什么这个模型好
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd

from ..storage import get_ml_store

logger = logging.getLogger("quantlab.ml.experiment")


@dataclass
class Experiment:
    """
    实验记录

    用法：
        exp = Experiment(
            name="LGBM_momentum_v1",
            dataset_id="crypto_1h",
            feature_set_id="momentum_v1",
            label_set_id="return_10d",
            model_type="LIGHTGBM",
            model_params={"n_estimators": 200},
            metrics={"ic": 0.12, "sharpe": 1.47},
        )
        tracker = get_experiment_tracker()
        tracker.save(exp)
    """
    experiment_id: str = field(default_factory=lambda: f"EXP-{uuid.uuid4().hex[:8]}")
    name: str = ""
    dataset_id: str = ""
    feature_set_id: str = ""
    label_set_id: str = ""
    # 模式1（传统）：feature_ids + label_id
    feature_ids: List[str] = field(default_factory=list)
    label_id: str = ""
    model_type: str = ""
    model_params: Dict[str, Any] = field(default_factory=dict)
    is_classifier: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    feature_importance_by_method: Dict[str, Dict[str, float]] = field(default_factory=dict)
    train_samples: int = 0
    test_samples: int = 0
    train_time: float = 0.0
    status: str = "COMPLETED"        # COMPLETED / FAILED
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""

    # 关联的 job_id（可选）
    job_id: str = ""
    # 关联的 model_version_id（可选）
    model_version_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.name:
            self.name = f"{self.model_type}_{self.experiment_id[-4:]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "dataset_id": self.dataset_id,
            "feature_set_id": self.feature_set_id,
            "label_set_id": self.label_set_id,
            "feature_ids": self.feature_ids,
            "label_id": self.label_id,
            "model_type": self.model_type,
            "model_params": self.model_params,
            "is_classifier": self.is_classifier,
            "metrics": self.metrics,
            "feature_importance": self.feature_importance,
            "feature_importance_by_method": self.feature_importance_by_method,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "train_time": round(self.train_time, 4),
            "status": self.status,
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at,
            "job_id": self.job_id,
            "model_version_id": self.model_version_id,
        }


# Experiment 表的 SQL（在 MLStore 中动态创建，这里定义 schema）
EXPERIMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id      TEXT PRIMARY KEY,
    name               TEXT,
    dataset_id         TEXT DEFAULT '',
    feature_set_id     TEXT DEFAULT '',
    label_set_id       TEXT DEFAULT '',
    feature_ids        TEXT DEFAULT '[]',
    label_id           TEXT DEFAULT '',
    model_type         TEXT DEFAULT '',
    model_params       TEXT DEFAULT '{}',
    is_classifier      INTEGER DEFAULT 0,
    metrics            TEXT DEFAULT '{}',
    feature_importance TEXT DEFAULT '{}',
    feature_importance_by_method TEXT DEFAULT '{}',
    train_samples      INTEGER DEFAULT 0,
    test_samples       INTEGER DEFAULT 0,
    train_time         REAL DEFAULT 0.0,
    status             TEXT DEFAULT 'COMPLETED',
    notes              TEXT DEFAULT '',
    tags               TEXT DEFAULT '[]',
    created_at         TEXT DEFAULT '',
    job_id             TEXT DEFAULT '',
    model_version_id   TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_exp_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_exp_model ON experiments(model_type);
CREATE INDEX IF NOT EXISTS idx_exp_created ON experiments(created_at);
"""


class ExperimentTracker:
    """
    实验追踪器（M2 升级：SQLite 持久化）

    用法：
        tracker = get_experiment_tracker()
        tracker.save(exp)
        exp = tracker.get("EXP-xxx")
        all_exps = tracker.list_all()
        best = tracker.get_best(metric="ic")
    """

    def __init__(self, persist: bool = True) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._persist = persist
        self._store = None
        self._lock = threading.RLock()
        if persist:
            self._store = get_ml_store()
            self._ensure_table()
            self.load_from_store()

    def _ensure_table(self) -> None:
        """确保 experiments 表存在"""
        if not self._store:
            return
        with self._store._cursor() as cur:
            cur.executescript(EXPERIMENT_SCHEMA)
            # 迁移：为旧表添加 feature_importance_by_method 列
            try:
                cur.execute("ALTER TABLE experiments ADD COLUMN feature_importance_by_method TEXT DEFAULT '{}'")
            except Exception:
                pass  # 列已存在，跳过
            # 迁移：为旧表添加 feature_ids / label_id 列（模式1支持）
            try:
                cur.execute("ALTER TABLE experiments ADD COLUMN feature_ids TEXT DEFAULT '[]'")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE experiments ADD COLUMN label_id TEXT DEFAULT ''")
            except Exception:
                pass

    def save(self, exp: Experiment) -> str:
        """保存实验（内存 + SQLite）"""
        with self._lock:
            self._experiments[exp.experiment_id] = exp
            if self._persist and self._store:
                self._save_to_db(exp)
            logger.info(
                f"Experiment saved: {exp.experiment_id} ({exp.name}) "
                f"IC={exp.metrics.get('ic', 0):.4f}"
            )
            return exp.experiment_id

    def _save_to_db(self, exp: Experiment) -> None:
        """写入 SQLite"""
        with self._store._cursor() as cur:
            cur.execute(
                """INSERT INTO experiments
                   (experiment_id, name, dataset_id, feature_set_id, label_set_id,
                    feature_ids, label_id,
                    model_type, model_params, is_classifier, metrics, feature_importance,
                    feature_importance_by_method,
                    train_samples, test_samples, train_time, status, notes, tags,
                    created_at, job_id, model_version_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(experiment_id) DO UPDATE SET
                     name=excluded.name,
                     metrics=excluded.metrics,
                     feature_importance=excluded.feature_importance,
                     feature_importance_by_method=excluded.feature_importance_by_method,
                     status=excluded.status,
                     train_time=excluded.train_time,
                     feature_ids=excluded.feature_ids,
                     label_id=excluded.label_id,
                     model_version_id=excluded.model_version_id""",
                (
                    exp.experiment_id,
                    exp.name,
                    exp.dataset_id,
                    exp.feature_set_id,
                    exp.label_set_id,
                    json.dumps(exp.feature_ids, ensure_ascii=False),
                    exp.label_id,
                    exp.model_type,
                    json.dumps(exp.model_params, ensure_ascii=False, default=str),
                    1 if exp.is_classifier else 0,
                    json.dumps(exp.metrics, ensure_ascii=False, default=str),
                    json.dumps(exp.feature_importance, ensure_ascii=False, default=str),
                    json.dumps(exp.feature_importance_by_method, ensure_ascii=False, default=str),
                    exp.train_samples,
                    exp.test_samples,
                    exp.train_time,
                    exp.status,
                    exp.notes,
                    json.dumps(exp.tags, ensure_ascii=False),
                    exp.created_at,
                    exp.job_id,
                    exp.model_version_id,
                ),
            )

    def get(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def list_all(
        self,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[Experiment]:
        """列出所有实验"""
        result = list(self._experiments.values())
        if tag:
            result = [e for e in result if tag in e.tags]
        if status:
            result = [e for e in result if e.status == status]
        if model_type:
            result = [e for e in result if e.model_type == model_type]
        # 按创建时间降序
        result.sort(key=lambda e: e.created_at, reverse=True)
        return result

    def get_best(
        self,
        metric: str = "ic",
        ascending: bool = False,
        tag: Optional[str] = None,
    ) -> Optional[Experiment]:
        """
        获取指定指标最优的实验

        Args:
            metric: 指标名，如 "ic", "sharpe", "rmse"
            ascending: True 表示越小越好（如 rmse）
            tag: 过滤标签
        """
        exps = self.list_all(tag=tag, status="COMPLETED")
        if not exps:
            return None
        # 过滤掉没有该指标的
        valid = [e for e in exps if metric in e.metrics]
        if not valid:
            return None
        valid.sort(key=lambda e: e.metrics[metric], reverse=not ascending)
        return valid[0]

    def get_leaderboard(
        self,
        metric: str = "ic",
        ascending: bool = False,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取排行榜"""
        exps = self.list_all(status="COMPLETED")
        valid = [e for e in exps if metric in e.metrics]
        valid.sort(key=lambda e: e.metrics[metric], reverse=not ascending)
        return [e.to_dict() for e in valid[:limit]]

    def delete(self, experiment_id: str) -> bool:
        with self._lock:
            ok = self._experiments.pop(experiment_id, None) is not None
            if ok and self._persist and self._store:
                with self._store._cursor() as cur:
                    cur.execute("DELETE FROM experiments WHERE experiment_id = ?", (experiment_id,))
            return ok

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame 便于分析"""
        data = []
        for e in self.list_all():
            d = e.to_dict()
            # 展平 metrics
            for k, v in d.pop("metrics", {}).items():
                d[f"metric_{k}"] = v
            data.append(d)
        return pd.DataFrame(data)

    def get_summary(self) -> Dict[str, Any]:
        all_exps = list(self._experiments.values())
        completed = [e for e in all_exps if e.status == "COMPLETED"]
        return {
            "total": len(all_exps),
            "completed": len(completed),
            "failed": sum(1 for e in all_exps if e.status == "FAILED"),
            "best_ic": max((e.metrics.get("ic", 0) for e in completed), default=0),
            "best_sharpe": max((e.metrics.get("sharpe", 0) for e in completed), default=0),
            "model_types": list({e.model_type for e in all_exps}),
        }

    # ------------------------------------------------------------------
    # 持久化：从 DB 恢复
    # ------------------------------------------------------------------

    def load_from_store(self) -> int:
        """从 SQLite 恢复所有实验"""
        if not self._store:
            return 0
        with self._store._cursor() as cur:
            cur.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            rows = cur.fetchall()
        count = 0
        for row in rows:
            eid = row["experiment_id"]
            if eid in self._experiments:
                continue
            exp = Experiment(
                experiment_id=eid,
                name=row["name"],
                dataset_id=row["dataset_id"],
                feature_set_id=row["feature_set_id"],
                label_set_id=row["label_set_id"],
                feature_ids=json.loads(row["feature_ids"] or "[]"),
                label_id=row["label_id"] if "label_id" in row.keys() else "",
                model_type=row["model_type"],
                model_params=json.loads(row["model_params"] or "{}"),
                is_classifier=bool(row["is_classifier"]),
                metrics=json.loads(row["metrics"] or "{}"),
                feature_importance=json.loads(row["feature_importance"] or "{}"),
                feature_importance_by_method=json.loads(row["feature_importance_by_method"] or "{}"),
                train_samples=row["train_samples"],
                test_samples=row["test_samples"],
                train_time=row["train_time"],
                status=row["status"],
                notes=row["notes"],
                tags=json.loads(row["tags"] or "[]"),
                created_at=row["created_at"],
                job_id=row["job_id"],
                model_version_id=row["model_version_id"],
            )
            self._experiments[eid] = exp
            count += 1
        logger.info(f"Loaded {count} experiments from store")
        return count


_tracker: Optional[ExperimentTracker] = None


def get_experiment_tracker(persist: bool = True) -> ExperimentTracker:
    """
    获取 ExperimentTracker 单例。

    Args:
        persist: 是否开启 SQLite 持久化（默认 True）
                 首次创建时会自动从 DB 恢复已有实验
    """
    global _tracker
    if _tracker is None:
        _tracker = ExperimentTracker(persist=persist)
    return _tracker


# ------------------------------------------------------------------
# Experiment Comparator（M2 第六部分）
# ------------------------------------------------------------------

from .comparator import (
    ExperimentComparator,
    ComparisonRow,
    ComparisonReport,
    compare_experiments,
)
