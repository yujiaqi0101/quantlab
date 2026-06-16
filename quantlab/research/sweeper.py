"""
Parameter Sweeper — V4.7 参数扫描引擎

职责：
  - 参数网格生成（Grid Search）
  - 批量运行实验
  - Heatmap 数据生成
  - Robustness Score 计算
  - Candidate 自动筛选

基于已有的 Optimizer / generate_param_grid，
但更轻量：不需要多进程，直接串行跑，结果存 DB。

用法：
    sweeper = ParameterSweeper(db)

    result = sweeper.run(
        strategy_id="ma_cross",
        param_space={"fast": [5,10,20], "slow": [60,120]},
        dataset_id="crypto_btcusdt",
    )

    # Heatmap
    heatmap = sweeper.heatmap(result["sweep_id"], x="fast", y="slow", metric="sharpe")

    # Robustness
    robust = sweeper.robustness_score(result["sweep_id"], params=["fast", "slow"])
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("quantlab.research.sweeper")


@dataclass(slots=True)
class SweepResult:
    """单次参数扫描的结果"""
    sweep_id: str
    strategy_id: str
    dataset_id: str
    param_space: Dict[str, List]
    total_combos: int
    completed: int = 0
    errors: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    status: str = "running"  # running / completed / error


@dataclass(slots=True)
class HeatmapData:
    """Heatmap 可视化数据"""
    x_label: str
    y_label: str
    x_values: List
    y_values: List
    matrix: List[List[Optional[float]]]  # 2D matrix [y][x]
    metric: str


class ParameterSweeper:
    """
    参数扫描引擎

    1. 生成参数组合
    2. 逐个运行回测（串行，简单可靠）
    3. 收集结果
    4. 生成 Heatmap / Robustness / Candidate
    """

    def __init__(self, db=None) -> None:
        self.db = db
        # 内存中的 sweep 结果缓存
        self._sweeps: Dict[str, SweepResult] = {}

    def _make_sweep_id(self, strategy_id: str, param_space: Dict, dataset_id: str) -> str:
        raw = f"{strategy_id}:{json.dumps(param_space, sort_keys=True)}:{dataset_id}"
        return f"sweep_{hashlib.md5(raw.encode()).hexdigest()[:12]}"

    def generate_combinations(self, param_space: Dict[str, List]) -> List[Dict]:
        """生成所有参数组合"""
        keys = list(param_space.keys())
        values = list(param_space.values())
        combos = []
        for combo in product(*values):
            combos.append(dict(zip(keys, combo)))
        return combos

    def run(
        self,
        strategy_id: str,
        param_space: Dict[str, List],
        dataset_id: str,
        runner=None,
    ) -> SweepResult:
        """
        运行参数扫描

        参数:
            strategy_id   策略 ID
            param_space   参数空间 {"fast": [5,10,20], "slow": [60,120]}
            dataset_id    数据集 ID
            runner        可选的回测运行函数 runner(params, strategy_id, dataset_id) -> Dict
                          如果不提供，使用 mock 模式（生成随机指标）
        """
        sweep_id = self._make_sweep_id(strategy_id, param_space, dataset_id)
        combos = self.generate_combinations(param_space)

        result = SweepResult(
            sweep_id=sweep_id,
            strategy_id=strategy_id,
            dataset_id=dataset_id,
            param_space=param_space,
            total_combos=len(combos),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        for i, params in enumerate(combos):
            try:
                if runner:
                    metrics = runner(params, strategy_id, dataset_id)
                else:
                    # Mock 模式：生成随机指标（开发/测试用）
                    metrics = self._mock_run(params, strategy_id)

                entry = {
                    "params": params,
                    "sharpe": metrics.get("sharpe", 0),
                    "total_return": metrics.get("total_return", 0),
                    "max_drawdown": metrics.get("max_drawdown", 0),
                    "trade_count": metrics.get("trade_count", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "final_equity": metrics.get("final_equity", 0),
                }
                result.results.append(entry)
                result.completed += 1

                # 保存到 DB（如果可用）
                if self.db:
                    self._save_to_db(sweep_id, params, metrics, strategy_id, dataset_id)

            except Exception as e:
                logger.warning(f"Sweep error for {params}: {e}")
                result.errors += 1

        result.status = "completed" if result.errors == 0 else "completed_with_errors"
        self._sweeps[sweep_id] = result
        return result

    def heatmap(
        self,
        sweep_id: str,
        x_param: str,
        y_param: str,
        metric: str = "sharpe",
    ) -> HeatmapData:
        """
        生成 Heatmap 数据

        参数:
            sweep_id  扫描 ID
            x_param   X 轴参数名
            y_param   Y 轴参数名
            metric    指标名（sharpe / total_return / max_drawdown）
        """
        sweep = self._sweeps.get(sweep_id)
        if not sweep:
            raise KeyError(f"Sweep '{sweep_id}' not found")

        # 收集唯一的 x/y 值
        x_values = sorted(set(
            r["params"].get(x_param) for r in sweep.results
            if x_param in r["params"]
        ))
        y_values = sorted(set(
            r["params"].get(y_param) for r in sweep.results
            if y_param in r["params"]
        ))

        # 构建 2D matrix
        matrix: List[List[Optional[float]]] = []
        for yv in y_values:
            row: List[Optional[float]] = []
            for xv in x_values:
                # 找到匹配的结果
                found = None
                for r in sweep.results:
                    if r["params"].get(x_param) == xv and r["params"].get(y_param) == yv:
                        found = r.get(metric)
                        break
                row.append(round(found, 4) if found is not None else None)
            matrix.append(row)

        return HeatmapData(
            x_label=x_param,
            y_label=y_param,
            x_values=x_values,
            y_values=y_values,
            matrix=matrix,
            metric=metric,
        )

    def robustness_score(
        self,
        sweep_id: str,
        params: List[str],
        metric: str = "sharpe",
    ) -> Dict[str, Any]:
        """
        计算参数稳健性分数

        核心思想：
          最佳参数周围的指标变化越小 → 越稳健

        方法：
          1. 找到 metric 最高的参数组合
          2. 计算所有"邻居"（只差一个参数值）的 metric 方差
          3. robustness = 1 / (1 + std_of_neighbors)

        返回:
            best_params     最佳参数组合
            best_metric     最佳指标值
            neighbor_count  邻居数量
            neighbor_std    邻居标准差
            robustness      稳健性分数 (0~1, 越高越好)
        """
        sweep = self._sweeps.get(sweep_id)
        if not sweep or not sweep.results:
            return {"robustness": 0, "best_params": {}, "best_metric": 0}

        # 找最佳
        best = max(sweep.results, key=lambda r: r.get(metric, -999))
        best_params = best["params"]
        best_metric = best.get(metric, 0)

        # 找邻居（只有一个参数不同的组合）
        neighbor_metrics = []
        for r in sweep.results:
            diff_count = sum(
                1 for p in params
                if r["params"].get(p) != best_params.get(p)
            )
            if diff_count == 1:
                neighbor_metrics.append(r.get(metric, 0))

        if not neighbor_metrics:
            # 没有邻居，无法评估稳健性
            return {
                "best_params": best_params,
                "best_metric": round(best_metric, 4),
                "neighbor_count": 0,
                "neighbor_std": 0,
                "robustness": 0.5,  # 中性
            }

        neighbor_std = float(np.std(neighbor_metrics))
        robustness = 1.0 / (1.0 + neighbor_std)

        return {
            "best_params": best_params,
            "best_metric": round(best_metric, 4),
            "neighbor_count": len(neighbor_metrics),
            "neighbor_metrics": [round(m, 4) for m in neighbor_metrics],
            "neighbor_std": round(neighbor_std, 4),
            "robustness": round(robustness, 4),
        }

    def find_candidates(
        self,
        sweep_id: str,
        min_sharpe: float = 1.5,
        max_drawdown: float = 0.20,
        min_trades: int = 50,
        min_robustness: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        自动筛选候选策略

        规则：
          - Sharpe > min_sharpe
          - MaxDD < max_drawdown
          - TradeCount > min_trades
        """
        sweep = self._sweeps.get(sweep_id)
        if not sweep:
            return []

        candidates = []
        for r in sweep.results:
            sharpe = r.get("sharpe", 0)
            mdd = abs(r.get("max_drawdown", 1))
            trades = r.get("trade_count", 0)

            if sharpe >= min_sharpe and mdd <= max_drawdown and trades >= min_trades:
                candidates.append({
                    "params": r["params"],
                    "sharpe": sharpe,
                    "max_drawdown": mdd,
                    "trade_count": trades,
                    "total_return": r.get("total_return", 0),
                    "win_rate": r.get("win_rate", 0),
                })

        # 按 Sharpe 排序
        candidates.sort(key=lambda c: c["sharpe"], reverse=True)
        return candidates

    def get_sweep(self, sweep_id: str) -> Optional[SweepResult]:
        return self._sweeps.get(sweep_id)

    def list_sweeps(self) -> List[Dict[str, Any]]:
        return [
            {
                "sweep_id": s.sweep_id,
                "strategy_id": s.strategy_id,
                "dataset_id": s.dataset_id,
                "total_combos": s.total_combos,
                "completed": s.completed,
                "errors": s.errors,
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in self._sweeps.values()
        ]

    # ---- 内部 ----

    def _mock_run(self, params: Dict, strategy_id: str) -> Dict[str, Any]:
        """Mock 回测（开发/测试用，生成合理随机指标）"""
        # 用参数的 hash 作为种子，保证可复现
        seed = int(hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)

        sharpe = round(rng.uniform(0.5, 2.5), 4)
        total_return = round(rng.uniform(-0.2, 1.5), 4)
        max_drawdown = round(rng.uniform(0.05, 0.4), 4)
        trade_count = int(rng.uniform(50, 500))
        win_rate = round(rng.uniform(0.4, 0.7), 4)
        final_equity = round(100000 * (1 + total_return), 2)

        return {
            "sharpe": sharpe,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "trade_count": trade_count,
            "win_rate": win_rate,
            "final_equity": final_equity,
        }

    def _save_to_db(self, sweep_id: str, params: Dict, metrics: Dict,
                    strategy_id: str, dataset_id: str) -> None:
        """保存扫描结果到数据库"""
        if not self.db:
            return
        try:
            import datetime
            exp_id = f"{sweep_id}_{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}"
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO experiments
                       (id, name, strategy, params_json, created_at, dataset_id, tag, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        exp_id,
                        f"Sweep: {strategy_id}",
                        strategy_id,
                        json.dumps(params),
                        datetime.datetime.now().isoformat(timespec="seconds"),
                        dataset_id,
                        sweep_id,
                        "normal",
                    ),
                )
                conn.execute(
                    """INSERT OR REPLACE INTO results
                       (experiment_id, final_equity, total_return, sharpe,
                        max_drawdown, trade_count, win_rate, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        exp_id,
                        metrics.get("final_equity", 0),
                        metrics.get("total_return", 0),
                        metrics.get("sharpe", 0),
                        metrics.get("max_drawdown", 0),
                        metrics.get("trade_count", 0),
                        metrics.get("win_rate", 0),
                        "sweep",
                    ),
                )
        except Exception as e:
            logger.warning(f"DB save failed: {e}")
