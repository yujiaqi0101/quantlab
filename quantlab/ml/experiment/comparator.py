"""
Experiment Comparator — 实验对比

ML Lab M2 第六部分：ExperimentComparator

  比较：
    EXP_001 VS EXP_002

  输出：
    指标       Exp1     Exp2     Diff
    IC         0.08     0.11     +0.03
    Sharpe     1.4      1.6      +0.20
    MaxDD      -8%      -6%      +2%

  用法：
      comparator = ExperimentComparator()
      comparator.add(exp1)
      comparator.add(exp2)
      report = comparator.compare()
      table = comparator.to_table()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

# 避免循环导入：使用 TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from . import Experiment

logger = logging.getLogger("quantlab.ml.experiment.comparator")


# 对比时关注的指标（按重要性排序）
DEFAULT_METRICS_TO_COMPARE = [
    "ic",
    "rank_ic",
    "sharpe",
    "rmse",
    "r2",
    "accuracy",
    "precision",
    "recall",
    "auc",
    "mae",
]


def _is_numeric(val: Any) -> bool:
    """判断值是否为数值（int/float，排除 bool）"""
    if isinstance(val, bool):
        return False
    return isinstance(val, (int, float)) or (
        isinstance(val, str)
        and val.replace(".", "", 1).replace("-", "", 1).isdigit()
    )


@dataclass
class ComparisonRow:
    """单行对比结果"""
    metric: str = ""
    values: Dict[str, float] = field(default_factory=dict)    # {exp_name: value}
    diff: Dict[str, float] = field(default_factory=dict)      # {exp_name: diff_vs_baseline}
    is_better: Dict[str, bool] = field(default_factory=dict)  # {exp_name: 是否优于baseline}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "values": self.values,
            "diff": self.diff,
            "is_better": self.is_better,
        }


@dataclass
class ComparisonReport:
    """实验对比报告"""
    baseline_name: str = ""
    experiment_names: List[str] = field(default_factory=list)
    rows: List[ComparisonRow] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_name": self.baseline_name,
            "experiment_names": self.experiment_names,
            "rows": [r.to_dict() for r in self.rows],
            "summary": self.summary,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame 便于展示"""
        data = []
        for row in self.rows:
            d = {"metric": row.metric}
            for name, val in row.values.items():
                d[name] = val
                if name in row.diff:
                    d[f"{name}_diff"] = row.diff[name]
            data.append(d)
        return pd.DataFrame(data)


class ExperimentComparator:
    """
    实验对比器

    用法：
        comparator = ExperimentComparator()
        comparator.add(exp1)       # 第一个为 baseline
        comparator.add(exp2)
        report = comparator.compare()
        print(comparator.to_table())
    """

    def __init__(self, metrics_to_compare: Optional[List[str]] = None) -> None:
        self._experiments: List[Any] = []
        self._names: List[str] = []
        self._metrics = metrics_to_compare or DEFAULT_METRICS_TO_COMPARE

    def add(self, exp: Any) -> "ExperimentComparator":
        """添加实验（第一个为 baseline）"""
        self._experiments.append(exp)
        name = exp.name or exp.experiment_id
        self._names.append(name)
        return self

    def reset(self) -> "ExperimentComparator":
        """清空"""
        self._experiments = []
        self._names = []
        return self

    def compare(self) -> ComparisonReport:
        """
        生成对比报告

        Returns:
            ComparisonReport
        """
        if len(self._experiments) < 2:
            logger.warning("Need at least 2 experiments to compare")
            return ComparisonReport()

        baseline = self._experiments[0]
        baseline_name = self._names[0]

        # 收集所有实验中出现过的指标
        all_metrics = set()
        for exp in self._experiments:
            all_metrics.update(exp.metrics.keys())
        # 按优先级排序
        metrics_ordered = [m for m in self._metrics if m in all_metrics]
        for m in sorted(all_metrics):
            if m not in metrics_ordered:
                metrics_ordered.append(m)

        rows: List[ComparisonRow] = []
        for metric in metrics_ordered:
            row = ComparisonRow(metric=metric)
            baseline_val = baseline.metrics.get(metric)

            # 跳过非数值指标（如 extra dict）
            if not _is_numeric(baseline_val):
                continue

            for i, exp in enumerate(self._experiments):
                name = self._names[i]
                val = exp.metrics.get(metric)
                if not _is_numeric(val):
                    continue
                val = float(val)
                row.values[name] = val
                if baseline_val is not None and i > 0:
                    diff = val - float(baseline_val)
                    row.diff[name] = diff
                    # 判断是否更好
                    # 对于 rmse/mae/mse 越小越好，其他越大越好
                    is_lower_better = metric in ("rmse", "mae", "mse")
                    row.is_better[name] = (
                        diff < 0 if is_lower_better else diff > 0
                        )
            rows.append(row)

        # 汇总
        summary = {
            "n_experiments": len(self._experiments),
            "baseline": baseline_name,
            "experiments": self._names,
            "metrics_compared": [r.metric for r in rows],
            "n_metrics": len(rows),
        }

        return ComparisonReport(
            baseline_name=baseline_name,
            experiment_names=list(self._names),
            rows=rows,
            summary=summary,
        )

    def to_table(self) -> str:
        """生成文本对比表"""
        report = self.compare()
        if not report.rows:
            return "No data to compare"

        # 构建表头
        headers = ["Metric"] + report.experiment_names
        # 添加 diff 列（对比 baseline）
        diff_headers = []
        for name in report.experiment_names[1:]:
            diff_headers.append(f"{name}_diff")

        all_headers = headers + diff_headers
        # 构建行
        lines = []
        # 表头
        col_width = 14
        header_line = " | ".join(h.ljust(col_width) for h in all_headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # 数据行
        for row in report.rows:
            cells = [row.metric.ljust(col_width)]
            for name in report.experiment_names:
                val = row.values.get(name)
                cells.append(f"{val:.4f}".ljust(col_width) if val is not None else "-".ljust(col_width))
            # diff
            for name in report.experiment_names[1:]:
                diff = row.diff.get(name)
                if diff is not None:
                    sign = "+" if diff >= 0 else ""
                    cells.append(f"{sign}{diff:.4f}".ljust(col_width))
                else:
                    cells.append("-".ljust(col_width))
            lines.append(" | ".join(cells))

        return "\n".join(lines)

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame"""
        return self.compare().to_dataframe()


# ------------------------------------------------------------------
# 便捷函数
# ------------------------------------------------------------------

def compare_experiments(
    experiments: List[Any],
    metrics_to_compare: Optional[List[str]] = None,
) -> ComparisonReport:
    """
    便捷函数：对比多个实验

    用法：
        report = compare_experiments([exp1, exp2, exp3])
        print(report.to_dataframe())
    """
    comparator = ExperimentComparator(metrics_to_compare=metrics_to_compare)
    for exp in experiments:
        comparator.add(exp)
    return comparator.compare()
