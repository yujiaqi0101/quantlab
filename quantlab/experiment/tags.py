"""
V4.4 Experiment Management — Tags

实验标签系统。
从第一天就做标签，以后筛选极其方便。

预定义标签：
  production   生产环境策略
  candidate    候选策略
  failed       失败实验
  favorite     收藏
  archive      归档
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set


# 预定义标签
BUILTIN_TAGS = {
    "production": "生产环境策略",
    "candidate": "候选策略",
    "failed": "失败实验",
    "favorite": "收藏",
    "archive": "归档",
    "baseline": "基准",
    "optimized": "已优化",
    "walkforward": "Walk-Forward 验证",
    "overfitting": "疑似过拟合",
    "experimental": "实验性",
}


class TagManager:
    """
    标签管理器

    用法：
        tm = TagManager(db=database)
        tm.add_tag("exp_001", "candidate")
        tm.remove_tag("exp_001", "failed")
        tm.get_tags("exp_001")
        tm.list_by_tag("candidate")
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db
        self._custom_tags: Dict[str, str] = {}

    def register_tag(self, name: str, description: str = "") -> None:
        """注册自定义标签"""
        self._custom_tags[name] = description

    def list_available_tags(self) -> Dict[str, str]:
        """列出所有可用标签（内置 + 自定义）"""
        tags = dict(BUILTIN_TAGS)
        tags.update(self._custom_tags)
        return tags

    # ---------------------------------------------------------
    # 标签操作（基于 DB）
    # ---------------------------------------------------------
    def add_tag(self, experiment_id: str, tag: str) -> None:
        """给实验添加标签"""
        if self._db is None:
            return

        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM experiments WHERE id = ?",
                (experiment_id,),
            ).fetchone()

            if row is None:
                return

            tags = json.loads(row["tags_json"] or "[]")
            if tag not in tags:
                tags.append(tag)
                conn.execute(
                    "UPDATE experiments SET tags_json = ? WHERE id = ?",
                    (json.dumps(tags, ensure_ascii=False), experiment_id),
                )

    def remove_tag(self, experiment_id: str, tag: str) -> None:
        """移除实验标签"""
        if self._db is None:
            return

        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM experiments WHERE id = ?",
                (experiment_id,),
            ).fetchone()

            if row is None:
                return

            tags = json.loads(row["tags_json"] or "[]")
            if tag in tags:
                tags.remove(tag)
                conn.execute(
                    "UPDATE experiments SET tags_json = ? WHERE id = ?",
                    (json.dumps(tags, ensure_ascii=False), experiment_id),
                )

    def get_tags(self, experiment_id: str) -> List[str]:
        """获取实验的所有标签"""
        if self._db is None:
            return []

        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT tags_json FROM experiments WHERE id = ?",
                (experiment_id,),
            ).fetchone()

            if row is None:
                return []

            return json.loads(row["tags_json"] or "[]")

    def set_tags(self, experiment_id: str, tags: List[str]) -> None:
        """设置实验标签（覆盖）"""
        if self._db is None:
            return

        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET tags_json = ? WHERE id = ?",
                (json.dumps(tags, ensure_ascii=False), experiment_id),
            )

    def list_by_tag(self, tag: str, limit: int = 100) -> List[Dict[str, Any]]:
        """按标签列出实验"""
        if self._db is None:
            return []

        with self._db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.id, e.name, e.strategy,
                    e.params_json, e.created_at,
                    e.tag, e.note,
                    e.dataset_id, e.dataset_version,
                    e.tags_json,
                    r.sharpe, r.total_return,
                    r.max_drawdown, r.trade_count
                FROM experiments e
                LEFT JOIN results r ON e.id = r.experiment_id
                WHERE e.tags_json LIKE ?
                ORDER BY e.created_at DESC
                LIMIT ?
                """,
                (f'%"{tag}"%', limit),
            ).fetchall()

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
