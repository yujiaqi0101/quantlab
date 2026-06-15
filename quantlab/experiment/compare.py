"""
V4.4 Experiment Management — Compare

实验对比引擎。
这是整个系统最重要的功能之一。

支持：
  - 指标对比表（Return / Sharpe / MaxDD / Trades / WinRate）
  - 权益曲线叠加（多条资金曲线叠加，前端特别有价值）
  - 参数差异对比
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd

from .artifact import ExperimentArtifact


class ExperimentComparer:
    """
    实验对比引擎

    用法：
        comparer = ExperimentComparer(db=database)
        result = comparer.compare(["exp_001", "exp_002", "exp_003"])
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def compare(
        self,
        experiment_ids: List[str],
        *,
        include_equity: bool = True,
        include_trades: bool = False,
    ) -> Dict[str, Any]:
        """
        对比多个实验

        参数：
          experiment_ids  实验 ID 列表
          include_equity  是否包含权益曲线
          include_trades  是否包含交易明细

        返回：
          {
            "experiments": [...],
            "metrics_table": [...],
            "equity_curves": {...},
            "param_diff": {...}
          }
        """
        if self._db is None or not experiment_ids:
            return {
                "experiments": [],
                "metrics_table": [],
                "equity_curves": {},
                "param_diff": {},
            }

        # 1. 获取实验数据
        experiments = []
        for eid in experiment_ids:
            exp = self._get_experiment(eid)
            if exp is not None:
                experiments.append(exp)

        if not experiments:
            return {
                "experiments": [],
                "metrics_table": [],
                "equity_curves": {},
                "param_diff": {},
            }

        # 2. 指标对比表
        metrics_table = self._build_metrics_table(experiments)

        # 3. 权益曲线叠加
        equity_curves = {}
        if include_equity:
            for exp in experiments:
                eid = exp["id"]
                artifact = ExperimentArtifact(eid)
                eq = artifact.load_equity()
                if eq is not None and not eq.empty:
                    # 转为前端友好的格式
                    if isinstance(eq.index, pd.DatetimeIndex):
                        dates = [str(d) for d in eq.index]
                    else:
                        dates = [str(d) for d in eq.index]

                    # 取 equity 列或第一列
                    if "equity" in eq.columns:
                        values = eq["equity"].tolist()
                    else:
                        values = eq.iloc[:, 0].tolist()

                    equity_curves[eid] = {
                        "name": exp.get("name", eid),
                        "dates": dates,
                        "values": values,
                    }

        # 4. 参数差异
        param_diff = self._build_param_diff(experiments)

        return {
            "experiments": experiments,
            "metrics_table": metrics_table,
            "equity_curves": equity_curves,
            "param_diff": param_diff,
        }

    def _get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """从 DB 获取实验"""
        with self._db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    e.id, e.name, e.strategy,
                    e.params_json, e.created_at,
                    e.dataset_id, e.dataset_version,
                    e.tags_json, e.strategy_version,
                    r.sharpe, r.total_return,
                    r.max_drawdown, r.trade_count,
                    r.win_rate, r.final_equity
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
            d["tags"] = json.loads(d.pop("tags_json", "[]"))
        except Exception:
            d["tags"] = []
        return d

    @staticmethod
    def _build_metrics_table(
        experiments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """构建指标对比表"""
        metrics_keys = [
            "total_return", "sharpe", "max_drawdown",
            "trade_count", "win_rate", "final_equity",
        ]

        table = []
        for exp in experiments:
            row = {
                "id": exp["id"],
                "name": exp.get("name", ""),
                "strategy": exp.get("strategy", ""),
            }
            for key in metrics_keys:
                row[key] = exp.get(key, 0)
            table.append(row)

        return table

    @staticmethod
    def _build_param_diff(
        experiments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建参数差异对比"""
        if not experiments:
            return {}

        # 收集所有参数 key
        all_keys: set = set()
        for exp in experiments:
            params = exp.get("params", {})
            all_keys.update(params.keys())

        # 对比
        diff = {}
        for key in sorted(all_keys):
            values = {}
            for exp in experiments:
                values[exp["id"]] = exp.get("params", {}).get(key, None)

            # 检查是否所有值相同
            unique_vals = set(str(v) for v in values.values())
            diff[key] = {
                "values": values,
                "same": len(unique_vals) == 1,
            }

        return diff
