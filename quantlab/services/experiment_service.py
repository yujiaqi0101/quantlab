"""
ExperimentService — 实验业务入口

封装：实验创建、查询、比较、回测触发
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..research.database import Database, default_db_path
from ..research.experiment import Experiment, ExperimentResult
from ..research.sweeper import ParameterSweeper
from ..research.report import Report

logger = logging.getLogger("quantlab.services.experiment")


class ExperimentService:
    """
    实验服务（Facade）

    统一入口：
      - 创建/查询/删除实验
      - 运行回测
      - 参数扫描
      - 生成报告
    """

    def __init__(
        self,
        db: Optional[Database] = None,
    ) -> None:
        self._db = db or Database(default_db_path())
        self._sweeper = ParameterSweeper(db=self._db)

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

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验详情"""
        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            # 获取结果
            res_row = conn.execute(
                "SELECT * FROM results WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
            if res_row:
                result["metrics"] = dict(res_row)
            return result

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

    # ---- Heatmap ----

    def heatmap(self, sweep_id: str, x_param: str, y_param: str, metric: str = "sharpe"):
        """生成 Heatmap"""
        return self._sweeper.heatmap(sweep_id, x_param, y_param, metric)

    # ---- Robustness ----

    def robustness(self, sweep_id: str, params: List[str], metric: str = "sharpe"):
        """计算稳健性"""
        return self._sweeper.robustness_score(sweep_id, params, metric)

    # ---- Candidates ----

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
