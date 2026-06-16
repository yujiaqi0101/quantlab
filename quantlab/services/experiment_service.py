"""
ExperimentService — 实验业务入口

V2.0 重构：统一封装实验创建、查询、比较、搜索、标签、血缘、报告
API 层只调本 Service，不直接碰 core
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..research.database import Database, default_db_path
from ..research.experiment import Experiment, ExperimentResult
from ..research.sweeper import ParameterSweeper
from ..research.report import Report
from ..research.repository import ExperimentRepository
from ..experiment.registry import ExperimentRegistry
from ..experiment.search import ExperimentSearch
from ..experiment.compare import ExperimentComparer
from ..experiment.report import ReportGenerator
from ..experiment.tags import TagManager
from ..experiment.artifact import ExperimentArtifact

logger = logging.getLogger("quantlab.services.experiment")


class ExperimentService:
    """
    实验服务（Facade）

    统一入口：
      - 创建/查询/删除实验
      - 运行回测
      - 参数扫描
      - 搜索/排名/对比
      - 标签/文件夹/收藏
      - 血缘关系
      - 生成报告
    """

    def __init__(
        self,
        db: Optional[Database] = None,
    ) -> None:
        self._db = db or Database(default_db_path())
        self._sweeper = ParameterSweeper(db=self._db)
        self._repo: Optional[ExperimentRepository] = None
        self._registry: Optional[ExperimentRegistry] = None
        self._search: Optional[ExperimentSearch] = None
        self._comparer: Optional[ExperimentComparer] = None
        self._report_gen: Optional[ReportGenerator] = None
        self._tag_mgr: Optional[TagManager] = None

    # ---- 懒加载组件 ----

    def _get_repo(self) -> ExperimentRepository:
        if self._repo is None:
            self._repo = ExperimentRepository(db=self._db)
        return self._repo

    def _get_registry(self) -> ExperimentRegistry:
        if self._registry is None:
            self._registry = ExperimentRegistry(db=self._db)
            self._registry.rebuild_index()
        return self._registry

    def _get_search(self) -> ExperimentSearch:
        if self._search is None:
            self._search = ExperimentSearch(db=self._db)
        return self._search

    def _get_comparer(self) -> ExperimentComparer:
        if self._comparer is None:
            self._comparer = ExperimentComparer(db=self._db)
        return self._comparer

    def _get_report_gen(self) -> ReportGenerator:
        if self._report_gen is None:
            self._report_gen = ReportGenerator(db=self._db)
        return self._report_gen

    def _get_tag_mgr(self) -> TagManager:
        if self._tag_mgr is None:
            self._tag_mgr = TagManager(db=self._db)
        return self._tag_mgr

    # ---- 查询 ----

    def list_experiments(
        self,
        strategy: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出实验"""
        with self._db.get_connection() as conn:
            query = "SELECT * FROM experiments WHERE 1=1"
            params = []
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)
            if tag:
                query += " AND tag = ?"
                params.append(tag)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def search_experiments(
        self,
        strategy: Optional[str] = None,
        tag: Optional[str] = None,
        sharpe_min: Optional[float] = None,
        max_dd_max: Optional[float] = None,
        return_min: Optional[float] = None,
        dataset_id: Optional[str] = None,
        limit: int = 100,
    ) -> Any:
        """搜索实验（返回 DataFrame）"""
        return self._get_repo().search(
            strategy=strategy,
            tag=tag,
            sharpe_min=sharpe_min,
            max_dd_max=max_dd_max,
            return_min=return_min,
            dataset_id=dataset_id,
            limit=limit,
        )

    def multi_search(self, **kwargs) -> List[Dict[str, Any]]:
        """多维度搜索"""
        return self._get_search().search(**kwargs)

    def rank_by(
        self,
        metric: str = "sharpe",
        strategy: Optional[str] = None,
        top: int = 20,
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """按指标排名"""
        return self._get_search().rank_by(
            metric=metric,
            strategy=strategy,
            top=top,
            ascending=ascending,
        )

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验详情"""
        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            res_row = conn.execute(
                "SELECT * FROM results WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
            if res_row:
                result["metrics"] = dict(res_row)
            return result

    def get_experiment_full(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验完整信息（含 Registry）"""
        return self._get_registry().get(experiment_id)

    def delete_experiment(self, experiment_id: str) -> bool:
        """删除实验"""
        return self._get_registry().delete(experiment_id)

    # ---- 对比 ----

    def compare(
        self,
        experiment_ids: List[str],
        include_equity: bool = True,
        include_trades: bool = False,
    ) -> Dict[str, Any]:
        """实验对比"""
        return self._get_comparer().compare(
            experiment_ids,
            include_equity=include_equity,
            include_trades=include_trades,
        )

    # ---- 标签 / 文件夹 / 收藏 ----

    def list_available_tags(self) -> Dict[str, str]:
        """列出所有可用标签"""
        return self._get_tag_mgr().list_available_tags()

    def list_folders(self) -> List[str]:
        """列出所有文件夹"""
        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT folder FROM experiments WHERE folder != '' ORDER BY folder"
            ).fetchall()
        return [row["folder"] for row in rows]

    def set_status(self, experiment_id: str, status: str) -> None:
        """设置实验状态"""
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET status = ? WHERE id = ?",
                (status, experiment_id),
            )

    def set_favorite(self, experiment_id: str, favorite: bool) -> None:
        """设置收藏"""
        fav = 1 if favorite else 0
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET favorite = ? WHERE id = ?",
                (fav, experiment_id),
            )

    def set_folder(self, experiment_id: str, folder: str) -> None:
        """设置文件夹"""
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET folder = ? WHERE id = ?",
                (folder, experiment_id),
            )

    def set_note(self, experiment_id: str, note: str) -> None:
        """更新研究备注"""
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET note = ? WHERE id = ?",
                (note, experiment_id),
            )
        self.log_activity(experiment_id, "note_updated", note[:100])

    def set_parent(self, experiment_id: str, parent_id: str) -> None:
        """设置父实验"""
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE experiments SET parent_id = ? WHERE id = ?",
                (parent_id, experiment_id),
            )
        self.log_activity(experiment_id, "parent_set", f"parent={parent_id}")

    # ---- 血缘关系 ----

    def get_lineage(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验血缘关系"""
        def _get_exp(conn: Any, eid: str) -> Optional[Dict]:
            row = conn.execute(
                "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE id = ?",
                (eid,),
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            try:
                d["params"] = json.loads(d.pop("params_json", "{}"))
            except Exception:
                d["params"] = {}
            return d

        with self._db.get_connection() as conn:
            current = _get_exp(conn, experiment_id)
            if current is None:
                return {"error": f"Experiment '{experiment_id}' not found"}

            ancestors = []
            pid = current.get("parent_id", "")
            visited = {experiment_id}
            while pid and pid not in visited:
                visited.add(pid)
                parent = _get_exp(conn, pid)
                if parent is None:
                    break
                ancestors.append(parent)
                pid = parent.get("parent_id", "")

            children_rows = conn.execute(
                "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE parent_id = ?",
                (experiment_id,),
            ).fetchall()
            children = []
            for row in children_rows:
                d = dict(row)
                try:
                    d["params"] = json.loads(d.pop("params_json", "{}"))
                except Exception:
                    d["params"] = {}
                children.append(d)

            siblings = []
            parent_id = current.get("parent_id", "")
            if parent_id:
                sib_rows = conn.execute(
                    "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE parent_id = ? AND id != ?",
                    (parent_id, experiment_id),
                ).fetchall()
                for row in sib_rows:
                    d = dict(row)
                    try:
                        d["params"] = json.loads(d.pop("params_json", "{}"))
                    except Exception:
                        d["params"] = {}
                    siblings.append(d)

            root_id = ancestors[-1]["id"] if ancestors else experiment_id

            def _build_tree(conn: Any, eid: str, visited_set: set) -> Dict:
                node = _get_exp(conn, eid)
                if node is None:
                    return {}
                node["children"] = []
                child_rows = conn.execute(
                    "SELECT id FROM experiments WHERE parent_id = ?",
                    (eid,),
                ).fetchall()
                for cr in child_rows:
                    cid = cr["id"]
                    if cid not in visited_set:
                        visited_set.add(cid)
                        child_tree = _build_tree(conn, cid, visited_set)
                        if child_tree:
                            node["children"].append(child_tree)
                return node

            family = _build_tree(conn, root_id, {root_id})

        return {
            "experiment_id": experiment_id,
            "ancestors": list(reversed(ancestors)),
            "children": children,
            "siblings": siblings,
            "family": family,
        }

    # ---- 活动日志 ----

    def log_activity(self, experiment_id: str, action: str, detail: str = "") -> None:
        """记录实验活动日志"""
        now = datetime.now(timezone.utc).isoformat()
        with self._db.get_connection() as conn:
            conn.execute(
                "INSERT INTO activity_log (experiment_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (experiment_id, action, detail, now),
            )

    def get_activity(self, experiment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取实验活动日志"""
        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, experiment_id, action, detail, created_at FROM activity_log WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        """全局研究时间线"""
        with self._db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.id, a.experiment_id, a.action, a.detail, a.created_at,
                       e.name, e.strategy, e.status
                FROM activity_log a
                LEFT JOIN experiments e ON a.experiment_id = e.id
                ORDER BY a.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- Artifact ----

    def get_artifact(self, experiment_id: str) -> ExperimentArtifact:
        """获取实验 Artifact"""
        return ExperimentArtifact(experiment_id)

    # ---- Sweep ----

    def run_sweep(
        self,
        strategy_id: str,
        param_space: Dict[str, List],
        dataset_id: str = "default",
        runner=None,
    ):
        """运行参数扫描"""
        return self._sweeper.run(
            strategy_id=strategy_id,
            param_space=param_space,
            dataset_id=dataset_id,
            runner=runner,
        )

    def get_sweep(self, sweep_id: str):
        """获取扫描结果"""
        return self._sweeper.get_sweep(sweep_id)

    def list_sweeps(self) -> List[Dict[str, Any]]:
        """列出所有扫描"""
        return self._sweeper.list_sweeps()

    def heatmap(self, sweep_id: str, x_param: str, y_param: str, metric: str = "sharpe"):
        """生成 Heatmap"""
        return self._sweeper.heatmap(sweep_id, x_param, y_param, metric)

    def robustness(self, sweep_id: str, params: List[str], metric: str = "sharpe"):
        """计算稳健性"""
        return self._sweeper.robustness_score(sweep_id, params, metric)

    def find_candidates(
        self,
        sweep_id: str,
        min_sharpe: float = 1.5,
        max_drawdown: float = 0.20,
        min_trades: int = 50,
    ):
        """筛选候选策略"""
        return self._sweeper.find_candidates(
            sweep_id, min_sharpe, max_drawdown, min_trades
        )

    # ---- Report ----

    def generate_report(self, result: ExperimentResult) -> str:
        """生成文本报告"""
        report = Report(result)
        return report.generate()
