"""
Data Quality Report — 增强数据质量报告

自动检查：
  - missing_bar:      缺失K线（时间序列断点）
  - duplicate_bar:    重复K线
  - timestamp_error:  时间逆序
  - outlier_price:    异常价格（Z-score > 3）

生成 Data Quality Report，包含：
  - 总体评分
  - 各项检查结果
  - 详细问题列表
  - 修复建议

用法：
    reporter = DataQualityReporter()
    report = reporter.report(df, frequency="1m")
    print(report.summary())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.dataset.quality")


# ------------------------------------------------------------------
# Issue
# ------------------------------------------------------------------

@dataclass(slots=True)
class DataIssue:
    """数据问题"""
    issue_type: str        # missing_bar / duplicate_bar / timestamp_error / outlier_price
    severity: str = "warning"  # error / warning / info
    count: int = 0
    description: str = ""
    locations: List[str] = field(default_factory=list)  # 问题位置（时间戳）
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# DataQualityReport
# ------------------------------------------------------------------

@dataclass(slots=True)
class DataQualityReport:
    """数据质量报告"""
    dataset_id: str = ""
    symbol: str = ""
    frequency: str = ""
    total_rows: int = 0
    score: float = 100.0       # 0-100, 100=完美
    issues: List[DataIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    passed: bool = True

    def summary(self) -> str:
        lines = [
            f"=== Data Quality Report ===",
            f"Dataset: {self.dataset_id}",
            f"Symbol:  {self.symbol}",
            f"Rows:    {self.total_rows}",
            f"Score:   {self.score:.1f}/100",
            f"Passed:  {'YES' if self.passed else 'NO'}",
            f"",
            f"Issues ({len(self.issues)}):",
        ]
        for issue in self.issues:
            lines.append(
                f"  [{issue.severity.upper()}] {issue.issue_type}: "
                f"{issue.count} occurrences - {issue.description}"
            )
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "symbol": self.symbol,
            "frequency": self.frequency,
            "total_rows": self.total_rows,
            "score": round(self.score, 1),
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "stats": dict(self.stats),
        }


# ------------------------------------------------------------------
# DataQualityReporter
# ------------------------------------------------------------------

class DataQualityReporter:
    """
    数据质量报告生成器

    检查项：
      1. missing_bar:      时间序列断点（根据频率推导预期间隔）
      2. duplicate_bar:    重复时间戳
      3. timestamp_error:  时间逆序
      4. outlier_price:    异常价格（Z-score）
      5. missing_values:   缺失值
      6. ohlcv_check:      OHLC 合法性
    """

    # 频率到 timedelta 的映射
    FREQ_DELTA = {
        "1m": pd.Timedelta(minutes=1),
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "30m": pd.Timedelta(minutes=30),
        "1h": pd.Timedelta(hours=1),
        "4h": pd.Timedelta(hours=4),
        "1d": pd.Timedelta(days=1),
        "1w": pd.Timedelta(weeks=1),
    }

    def report(
        self,
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        frequency: str = "",
        check_outliers: bool = True,
        outlier_threshold: float = 3.0,
    ) -> DataQualityReport:
        """
        生成数据质量报告

        参数：
          df                DataFrame
          dataset_id        数据集 ID
          symbol            标的符号
          frequency         频率（1m/5m/1d...）
          check_outliers    是否检查异常价格
          outlier_threshold Z-score 阈值
        """
        report = DataQualityReport(
            dataset_id=dataset_id,
            symbol=symbol,
            frequency=frequency,
            total_rows=len(df),
        )

        if df is None or df.empty:
            report.passed = False
            report.score = 0
            report.issues.append(DataIssue(
                issue_type="empty_data",
                severity="error",
                count=1,
                description="DataFrame is empty",
                suggestion="Check data source",
            ))
            return report

        # 基础统计
        report.stats["columns"] = list(df.columns)
        report.stats["start_time"] = str(df.index.min()) if len(df) > 0 else ""
        report.stats["end_time"] = str(df.index.max()) if len(df) > 0 else ""

        # 1. 检查时间逆序
        self._check_timestamp_order(df, report)

        # 2. 检查重复
        self._check_duplicates(df, report)

        # 3. 检查缺失K线
        if frequency:
            self._check_missing_bars(df, frequency, report)

        # 4. 检查缺失值
        self._check_missing_values(df, report)

        # 5. 检查 OHLC 合法性
        self._check_ohlcv(df, report)

        # 6. 检查异常价格
        if check_outliers:
            self._check_outliers(df, report, outlier_threshold)

        # 计算评分
        self._calculate_score(report)
        return report

    # ---- 检查项 ----

    def _check_timestamp_order(self, df: pd.DataFrame, report: DataQualityReport) -> None:
        """检查时间逆序"""
        if not isinstance(df.index, pd.DatetimeIndex):
            return

        if not df.index.is_monotonic_increasing:
            # 找逆序位置
            diffs = np.diff(df.index.values)
            descents = np.where(diffs < np.timedelta64(0))[0]
            locations = [str(df.index[i]) for i in descents[:10]]

            report.issues.append(DataIssue(
                issue_type="timestamp_error",
                severity="error",
                count=len(descents),
                description=f"{len(descents)} timestamps out of order",
                locations=locations,
                suggestion="Sort data by timestamp",
            ))

    def _check_duplicates(self, df: pd.DataFrame, report: DataQualityReport) -> None:
        """检查重复时间戳"""
        if not isinstance(df.index, pd.DatetimeIndex):
            return

        n_dup = int(df.index.duplicated().sum())
        if n_dup > 0:
            dup_mask = df.index.duplicated(keep=False)
            dup_times = df.index[dup_mask].unique()[:10]
            locations = [str(t) for t in dup_times]

            report.issues.append(DataIssue(
                issue_type="duplicate_bar",
                severity="error",
                count=n_dup,
                description=f"{n_dup} duplicate timestamps",
                locations=locations,
                suggestion="Remove duplicates (keep first or last)",
            ))

    def _check_missing_bars(
        self, df: pd.DataFrame, frequency: str, report: DataQualityReport
    ) -> None:
        """检查缺失K线（时间序列断点）"""
        if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 2:
            return

        expected_delta = self.FREQ_DELTA.get(frequency)
        if expected_delta is None:
            return

        # 计算时间差
        diffs = df.index.to_series().diff().dropna()

        # 找到大于预期间隔的位置（缺失）
        gaps = diffs[diffs > expected_delta]
        missing_count = 0
        locations = []

        for ts, gap in gaps.items():
            n_missing = int(gap / expected_delta) - 1
            if n_missing > 0:
                missing_count += n_missing
                if len(locations) < 10:
                    locations.append(f"{ts} (gap={gap}, missing~{n_missing})")

        if missing_count > 0:
            severity = "error" if missing_count > len(df) * 0.01 else "warning"
            report.issues.append(DataIssue(
                issue_type="missing_bar",
                severity=severity,
                count=missing_count,
                description=f"{missing_count} bars missing (frequency={frequency})",
                locations=locations,
                suggestion="Forward fill or interpolate missing bars",
            ))

    def _check_missing_values(self, df: pd.DataFrame, report: DataQualityReport) -> None:
        """检查缺失值"""
        total_missing = int(df.isnull().sum().sum())
        if total_missing > 0:
            missing_by_col = df.isnull().sum()
            missing_cols = missing_by_col[missing_by_col > 0]
            detail = ", ".join(f"{col}={cnt}" for col, cnt in missing_cols.items())

            report.issues.append(DataIssue(
                issue_type="missing_values",
                severity="warning",
                count=total_missing,
                description=f"{total_missing} missing values ({detail})",
                suggestion="Forward fill, back fill, or interpolate",
            ))

    def _check_ohlcv(self, df: pd.DataFrame, report: DataQualityReport) -> None:
        """检查 OHLC 合法性"""
        cols_lower = {c.lower(): c for c in df.columns}
        high_col = cols_lower.get("high")
        low_col = cols_lower.get("low")

        if not high_col or not low_col:
            return

        high = df[high_col]
        low = df[low_col]

        # high < low
        n_bad = int((high < low).sum())
        if n_bad > 0:
            report.issues.append(DataIssue(
                issue_type="ohlcv_error",
                severity="error",
                count=n_bad,
                description=f"high < low in {n_bad} rows",
                suggestion="Check data source for price errors",
            ))

    def _check_outliers(
        self, df: pd.DataFrame, report: DataQualityReport, threshold: float
    ) -> None:
        """检查异常价格（Z-score）"""
        cols_lower = {c.lower(): c for c in df.columns}
        close_col = cols_lower.get("close")

        if not close_col:
            return

        returns = df[close_col].pct_change().dropna()
        if len(returns) < 10:
            return

        z_scores = (returns - returns.mean()) / returns.std()
        outliers = z_scores[np.abs(z_scores) > threshold]

        if len(outliers) > 0:
            locations = [str(ts) for ts in outliers.index[:10]]
            report.issues.append(DataIssue(
                issue_type="outlier_price",
                severity="warning",
                count=len(outliers),
                description=f"{len(outliers)} outlier returns (|z|>{threshold})",
                locations=locations,
                suggestion="Review outliers — may be data errors or extreme events",
            ))

    # ---- 评分 ----

    def _calculate_score(self, report: DataQualityReport) -> None:
        """计算质量评分"""
        score = 100.0
        total_rows = max(report.total_rows, 1)

        for issue in report.issues:
            # 根据严重程度扣分
            if issue.severity == "error":
                penalty = min(30, (issue.count / total_rows) * 100 * 10)
            elif issue.severity == "warning":
                penalty = min(15, (issue.count / total_rows) * 100 * 5)
            else:
                penalty = min(5, (issue.count / total_rows) * 100 * 2)

            score -= penalty

            if issue.severity == "error" and issue.count > 0:
                report.passed = False

        report.score = max(0, score)
