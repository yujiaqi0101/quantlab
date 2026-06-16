"""
Alpha Lineage — Alpha 演化血缘

记录 Alpha 的演化过程，形成 Family Tree：

  Momentum20
       │
       ▼
  Momentum20 > 0
       │
       ▼
  Momentum20 > 0 AND VolumeRank > 0.8
       │
       ▼
  Composite Alpha

支持：
  - 记录父子关系
  - 查询祖先链
  - 查询后代树
  - 生成可视化数据
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from ..alpha.alpha import Alpha
from ..alpha.store import AlphaStore

logger = logging.getLogger("quantlab.alpha_graph.lineage")


class AlphaLineage:
    """
    Alpha 血缘管理

    用法：
        lineage = AlphaLineage(store)
        lineage.add_relation(parent_id, child_id, "mutation")
        tree = lineage.get_family_tree(alpha_id)
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        db_dir = os.path.join(os.path.expanduser("~"), ".quantlab")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "alpha_lineage.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alpha_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL DEFAULT 'mutation',
                    metadata_json TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parent ON alpha_relations(parent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_child ON alpha_relations(child_id)
            """)

    # ---- 关系管理 ----

    def add_relation(
        self,
        parent_id: str,
        child_id: str,
        relation_type: str = "mutation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加父子关系

        relation_type:
          - "mutation"    变异（阈值/窗口变化）
          - "combination" 组合（多个 Alpha 合并）
          - "evolution"   进化（自动进化引擎）
          - "manual"      手动创建
        """
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO alpha_relations (parent_id, child_id, relation_type, metadata_json)
                VALUES (?, ?, ?, ?)
            """, (
                parent_id, child_id, relation_type,
                json.dumps(metadata or {}),
            ))

    def add_parents(
        self,
        child_id: str,
        parent_ids: List[str],
        relation_type: str = "mutation",
    ) -> None:
        """添加多个父 Alpha"""
        for pid in parent_ids:
            self.add_relation(pid, child_id, relation_type)

    # ---- 查询 ----

    def get_ancestors(self, alpha_id: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        获取祖先链

        返回从根到当前 Alpha 的祖先列表
        """
        ancestors = []
        visited = {alpha_id}
        current_ids = [alpha_id]

        for _ in range(max_depth):
            next_ids = []
            with self._get_conn() as conn:
                for cid in current_ids:
                    rows = conn.execute(
                        "SELECT parent_id, relation_type, metadata_json FROM alpha_relations WHERE child_id = ?",
                        (cid,),
                    ).fetchall()
                    for row in rows:
                        pid = row["parent_id"]
                        if pid not in visited:
                            visited.add(pid)
                            alpha = self._store.get(pid)
                            ancestors.append({
                                "alpha_id": pid,
                                "name": alpha.name if alpha else pid,
                                "relation_type": row["relation_type"],
                                "metadata": json.loads(row["metadata_json"]),
                            })
                            next_ids.append(pid)
            if not next_ids:
                break
            current_ids = next_ids

        return ancestors

    def get_children(self, alpha_id: str) -> List[Dict[str, Any]]:
        """获取直接子 Alpha"""
        children = []
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT child_id, relation_type, metadata_json FROM alpha_relations WHERE parent_id = ?",
                (alpha_id,),
            ).fetchall()
            for row in rows:
                alpha = self._store.get(row["child_id"])
                children.append({
                    "alpha_id": row["child_id"],
                    "name": alpha.name if alpha else row["child_id"],
                    "relation_type": row["relation_type"],
                    "metadata": json.loads(row["metadata_json"]),
                })
        return children

    def get_family_tree(self, alpha_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        获取 Family Tree

        返回可视化用的树结构
        """
        alpha = self._store.get(alpha_id)
        root_name = alpha.name if alpha else alpha_id

        tree = self._build_tree(alpha_id, max_depth, set())

        return {
            "root_id": alpha_id,
            "root_name": root_name,
            "tree": tree,
        }

    def _build_tree(
        self,
        alpha_id: str,
        max_depth: int,
        visited: set,
    ) -> Dict[str, Any]:
        """递归构建树"""
        if alpha_id in visited or max_depth <= 0:
            return {"id": alpha_id, "children": []}

        visited.add(alpha_id)
        alpha = self._store.get(alpha_id)

        node = {
            "id": alpha_id,
            "name": alpha.name if alpha else alpha_id,
            "status": alpha.status.value if alpha else "unknown",
            "score": alpha.metrics.score if alpha else 0,
            "children": [],
        }

        # 获取子节点
        children = self.get_children(alpha_id)
        for child in children:
            child_tree = self._build_tree(child["alpha_id"], max_depth - 1, visited)
            child_tree["relation"] = child["relation_type"]
            node["children"].append(child_tree)

        return node

    # ---- 可视化数据 ----

    def get_graph_data(self, alpha_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        生成图可视化数据（节点 + 边）

        用于前端渲染类似 Git Graph 的体验
        """
        nodes = []
        edges = []

        # 收集所有相关 Alpha
        if alpha_ids is None:
            # 从关系表获取所有 Alpha
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT parent_id FROM alpha_relations UNION SELECT DISTINCT child_id FROM alpha_relations"
                ).fetchall()
                alpha_ids = [r[0] for r in rows]

        # 节点
        for aid in alpha_ids:
            alpha = self._store.get(aid)
            nodes.append({
                "id": aid,
                "name": alpha.name if alpha else aid,
                "status": alpha.status.value if alpha else "unknown",
                "score": alpha.metrics.score if alpha else 0,
                "factor": alpha.factor_name if alpha else "",
            })

        # 边
        with self._get_conn() as conn:
            if alpha_ids:
                placeholders = ",".join(["?"] * len(alpha_ids))
                rows = conn.execute(
                    f"SELECT parent_id, child_id, relation_type FROM alpha_relations WHERE parent_id IN ({placeholders}) OR child_id IN ({placeholders})",
                    alpha_ids + alpha_ids,
                ).fetchall()
                for row in rows:
                    edges.append({
                        "source": row["parent_id"],
                        "target": row["child_id"],
                        "type": row["relation_type"],
                    })

        return {"nodes": nodes, "edges": edges}

    # ---- 统计 ----

    def get_lineage_stats(self) -> Dict[str, Any]:
        """血缘统计"""
        with self._get_conn() as conn:
            total_relations = conn.execute("SELECT COUNT(*) as cnt FROM alpha_relations").fetchone()["cnt"]

            # 根节点（没有父节点的 Alpha）
            roots = conn.execute("""
                SELECT DISTINCT parent_id FROM alpha_relations
                WHERE parent_id NOT IN (SELECT child_id FROM alpha_relations)
            """).fetchall()

            # 叶节点（没有子节点的 Alpha）
            leaves = conn.execute("""
                SELECT DISTINCT child_id FROM alpha_relations
                WHERE child_id NOT IN (SELECT parent_id FROM alpha_relations)
            """).fetchall()

        return {
            "total_relations": total_relations,
            "root_count": len(roots),
            "leaf_count": len(leaves),
        }
