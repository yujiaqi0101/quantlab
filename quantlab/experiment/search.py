"""
V4.4 Experiment Management — Search

多维度搜索引擎。
这是后面会天天用的功能。

支持：
  - 按策略搜索
  - 按数据集搜索
  - 按指标范围搜索（sharpe_gt, return_gt, max_dd_lt）
  - 按标签搜索
  - 按日期范围搜索
  - 排名（rank_by metric）
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd


class ExperimentSearch:
    """
    实验搜索引擎

    用法：
        search = ExperimentSearch(db=database)
        results = search.search(strategy="ma_cross", sharpe_gt=1.5)
        top = search.rank_by("sharpe", top=10)
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def search(
        self,
        *,
        q: str = "",
        strategy: Optional[str] = None,
        dataset_id: Optional[str] = None,
        sharpe_gt: Optional[float] = None,
        sharpe_lt: Optional[float] = None,
        return_gt: Optional[float] = None,
        return_lt: Optional[float] = None,
        max_dd_lt: Optional[float] = None,
        trade_count_gt: Optional[int] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        多维度搜索

        参数：
          q              模糊搜索（name/strategy/note）
          strategy       策略 ID
          dataset_id     数据集 ID
          sharpe_gt      Sharpe 下限
          sharpe_lt      Sharpe 上限
          return_gt      总收益下限（%）
          return_lt      总收益上限（%）
          max_dd_lt      最大回撤上限（正数，如 20 表示 < 20%）
          trade_count_gt 最小交易次数
          tags           包含任意标签
          date_from      起始日期
          date_to        结束日期
          limit          返回数量
        """
        if self._db is None:
            return []

        where = []
        params: List = []

        # 模糊搜索
        if q:
            where.append(
                "(e.name LIKE ? OR e.strategy LIKE ? OR e.note LIKE ?)"
            )
            like = f"%{q}%"
            params.extend([like, like, like])

        if strategy:
            where.append("e.strategy = ?")
            params.append(strategy)

        if dataset_id:
            where.append("e.dataset_id = ?")
            params.append(dataset_id)

        if sharpe_gt is not None:
            where.append("r.sharpe >= ?")
            params.append(sharpe_gt)

        if sharpe_lt is not None:
            where.append("r.sharpe <= ?")
            params.append(sharpe_lt)

        if return_gt is not None:
            where.append("r.total_return >= ?")
            params.append(return_gt)

        if return_lt is not None:
            where.append("r.total_return <= ?")
            params.append(return_lt)

        if max_dd_lt is not None:
            # max_drawdown 是负数，用户传正数
            where.append("r.max_drawdown >= ?")
            params.append(-max_dd_lt)

        if trade_count_gt is not None:
            where.append("r.trade_count >= ?")
            params.append(trade_count_gt)

        if tags:
            or_clauses = []
            for t in tags:
                or_clauses.append("e.tags_json LIKE ?")
                params.append(f'%"{t}"%')
            where.append("(" + " OR ".join(or_clauses) + ")")

        if date_from:
            where.append("e.created_at >= ?")
            params.append(date_from)

        if date_to:
            where.append("e.created_at <= ?")
            params.append(date_to)

        sql = """
            SELECT
                e.id, e.name, e.strategy,
                e.params_json, e.created_at,
                e.tag, e.note,
                e.dataset_id, e.dataset_version,
                e.tags_json, e.strategy_version,
                r.sharpe, r.total_return,
                r.max_drawdown, r.trade_count,
                r.win_rate, r.final_equity
            FROM experiments e
            LEFT JOIN results r ON e.id = r.experiment_id
        """

        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY r.sharpe DESC LIMIT ?"
        params.append(limit)

        with self._db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return self._rows_to_list(rows)

    def rank_by(
        self,
        metric: str = "sharpe",
        *,
        strategy: Optional[str] = None,
        top: int = 20,
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        按指标排名

        参数：
          metric    排名指标（sharpe / total_return / max_drawdown / win_rate / trade_count）
          strategy  限定策略
          top       返回数量
          ascending 是否升序
        """
        if self._db is None:
            return []

        # 指标列映射
        metric_map = {
            "sharpe": "r.sharpe",
            "total_return": "r.total_return",
            "return": "r.total_return",
            "max_drawdown": "r.max_drawdown",
            "max_dd": "r.max_drawdown",
            "win_rate": "r.win_rate",
            "trade_count": "r.trade_count",
            "final_equity": "r.final_equity",
        }

        col = metric_map.get(metric, "r.sharpe")

        # max_drawdown 特殊处理：数值越大（越接近0）= 越好
        if metric in ("max_drawdown", "max_dd"):
            ascending = False  # 降序（-10% > -30%）

        where = []
        params: List = []

        if strategy:
            where.append("e.strategy = ?")
            params.append(strategy)

        sql = f"""
            SELECT
                e.id, e.name, e.strategy,
                e.params_json, e.created_at,
                e.dataset_id, e.dataset_version,
                e.tags_json, e.strategy_version,
                r.sharpe, r.total_return,
                r.max_drawdown, r.trade_count,
                r.win_rate, r.final_equity
            FROM experiments e
            JOIN results r ON e.id = r.experiment_id
        """

        if where:
            sql += " WHERE " + " AND ".join(where)

        order = "ASC" if ascending else "DESC"
        sql += f" ORDER BY {col} {order} LIMIT ?"
        params.append(top)

        with self._db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        results = self._rows_to_list(rows)

        # 添加排名
        for i, r in enumerate(results, 1):
            r["rank"] = i

        return results

    # ---------------------------------------------------------
    # 工具
    # ---------------------------------------------------------
    @staticmethod
    def _rows_to_list(rows: Any) -> List[Dict[str, Any]]:
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
