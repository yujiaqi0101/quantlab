"""
Feature Diagnostics — 特征诊断

ML Lab 第五部分：M1 就要做，不要等后面。

  自动统计：
    - missing_rate   缺失率
    - inf_count      无穷值数量
    - zero_rate      零值率
    - variance       方差
    - n_unique       唯一值数量

  发现坏特征并自动标红：
    - 全为空（missing_rate == 1.0）
    - 全为 0（zero_rate == 1.0）
    - 方差接近 0（variance < 1e-10）
    - 含 inf
    - 唯一值数量 ≤ 1（常量特征）

  用法：
      diag = FeatureDiagnostics()
      results = diag.diagnose(X)            # X: DataFrame，每列一个特征
      bad = diag.find_bad_features(X)       # 仅返回坏特征
      report = diag.report(X)               # 完整报告（含 summary）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.diagnostics.feature")


# 坏特征判定阈值（保守值，避免误报）
DEFAULT_VAR_THRESHOLD = 1e-10
DEFAULT_MISSING_THRESHOLD = 0.95       # 缺失率高于 95% 标红
DEFAULT_ZERO_THRESHOLD = 0.95          # 零值率高于 95% 标红


@dataclass
class FeatureDiagnosticResult:
    """单个特征的诊断结果"""
    feature_name: str = ""
    n_samples: int = 0
    n_missing: int = 0
    missing_rate: float = 0.0
    n_inf: int = 0
    inf_count: int = 0                  # 别名，与文档一致
    n_zero: int = 0
    zero_rate: float = 0.0
    variance: float = 0.0
    n_unique: int = 0
    dtype: str = ""
    is_bad: bool = False
    issues: List[str] = field(default_factory=list)   # 具体问题列表

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "n_samples": self.n_samples,
            "n_missing": self.n_missing,
            "missing_rate": round(self.missing_rate, 4),
            "n_inf": self.n_inf,
            "inf_count": self.inf_count,
            "n_zero": self.n_zero,
            "zero_rate": round(self.zero_rate, 4),
            "variance": float(self.variance) if np.isfinite(self.variance) else None,
            "n_unique": self.n_unique,
            "dtype": self.dtype,
            "is_bad": self.is_bad,
            "issues": self.issues,
        }


@dataclass
class FeatureDiagnosticsReport:
    """特征诊断完整报告"""
    n_features: int = 0
    n_samples: int = 0
    n_bad: int = 0
    bad_features: List[str] = field(default_factory=list)
    results: List[FeatureDiagnosticResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "n_bad": self.n_bad,
            "bad_features": self.bad_features,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }


class FeatureDiagnostics:
    """
    特征诊断器

    用法：
        diag = FeatureDiagnostics()
        report = diag.report(X)
        # report.results: 每个特征一行
        # report.bad_features: 被标红的坏特征列表
    """

    def __init__(
        self,
        var_threshold: float = DEFAULT_VAR_THRESHOLD,
        missing_threshold: float = DEFAULT_MISSING_THRESHOLD,
        zero_threshold: float = DEFAULT_ZERO_THRESHOLD,
    ) -> None:
        self.var_threshold = var_threshold
        self.missing_threshold = missing_threshold
        self.zero_threshold = zero_threshold

    # ------------------------------------------------------------------
    # 单特征诊断
    # ------------------------------------------------------------------

    def diagnose_column(self, series: pd.Series) -> FeatureDiagnosticResult:
        """诊断单个特征列"""
        n_samples = len(series)
        if n_samples == 0:
            return FeatureDiagnosticResult(
                feature_name=str(series.name),
                n_samples=0,
                is_bad=True,
                issues=["empty_column"],
            )

        # 缺失
        n_missing = int(series.isna().sum())
        missing_rate = n_missing / n_samples

        # inf（仅数值型有意义）
        n_inf = 0
        variance = 0.0
        n_unique = int(series.nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(series):
            # inf 计数（不含 NaN）
            try:
                n_inf = int(np.isinf(series.dropna()).sum())
            except Exception:
                n_inf = 0
            # 方差（剔除 inf 和 NaN，避免污染）
            try:
                clean = series.replace([np.inf, -np.inf], np.nan).dropna()
                if len(clean) > 0:
                    variance = float(clean.var())
                else:
                    variance = 0.0
            except Exception:
                variance = 0.0

        # 零值（仅数值型）
        n_zero = 0
        zero_rate = 0.0
        if pd.api.types.is_numeric_dtype(series):
            try:
                n_zero = int((series == 0).sum())
                zero_rate = n_zero / n_samples
            except Exception:
                pass

        # 判定坏特征
        issues: List[str] = []
        name = str(series.name)

        if missing_rate >= 1.0:
            issues.append("all_missing")              # 全为空
        elif missing_rate > self.missing_threshold:
            issues.append("high_missing_rate")        # 缺失率过高

        if n_inf > 0:
            issues.append("has_inf")                  # 含无穷值

        if zero_rate >= 1.0:
            issues.append("all_zero")                 # 全为 0
        elif zero_rate > self.zero_threshold:
            issues.append("high_zero_rate")           # 零值率过高

        if pd.api.types.is_numeric_dtype(series):
            if variance < self.var_threshold:
                issues.append("near_zero_variance")   # 方差接近 0

        if n_unique <= 1:
            issues.append("constant_feature")         # 常量特征

        is_bad = len(issues) > 0

        return FeatureDiagnosticResult(
            feature_name=name,
            n_samples=n_samples,
            n_missing=n_missing,
            missing_rate=missing_rate,
            n_inf=n_inf,
            inf_count=n_inf,
            n_zero=n_zero,
            zero_rate=zero_rate,
            variance=variance,
            n_unique=n_unique,
            dtype=str(series.dtype),
            is_bad=is_bad,
            issues=issues,
        )

    # ------------------------------------------------------------------
    # 批量诊断
    # ------------------------------------------------------------------

    def diagnose(self, X: pd.DataFrame) -> List[FeatureDiagnosticResult]:
        """诊断整个特征矩阵，每列一个结果"""
        results: List[FeatureDiagnosticResult] = []
        for col in X.columns:
            try:
                results.append(self.diagnose_column(X[col]))
            except Exception as e:
                logger.error(f"Feature diagnose failed: {col} — {e}")
                results.append(FeatureDiagnosticResult(
                    feature_name=str(col),
                    is_bad=True,
                    issues=[f"diagnose_error: {e}"],
                ))
        return results

    def find_bad_features(self, X: pd.DataFrame) -> List[str]:
        """仅返回坏特征名列表"""
        return [r.feature_name for r in self.diagnose(X) if r.is_bad]

    def report(self, X: pd.DataFrame) -> FeatureDiagnosticsReport:
        """生成完整诊断报告"""
        results = self.diagnose(X)
        bad = [r.feature_name for r in results if r.is_bad]

        # 汇总统计
        n_features = len(results)
        n_bad = len(bad)
        n_samples = len(X)
        issue_counts: Dict[str, int] = {}
        for r in results:
            for issue in r.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        summary = {
            "n_features": n_features,
            "n_samples": n_samples,
            "n_bad": n_bad,
            "bad_ratio": round(n_bad / n_features, 4) if n_features > 0 else 0.0,
            "issue_counts": issue_counts,
            "var_threshold": self.var_threshold,
            "missing_threshold": self.missing_threshold,
            "zero_threshold": self.zero_threshold,
        }

        return FeatureDiagnosticsReport(
            n_features=n_features,
            n_samples=n_samples,
            n_bad=n_bad,
            bad_features=bad,
            results=results,
            summary=summary,
        )


# ------------------------------------------------------------------
# 模块级便捷函数
# ------------------------------------------------------------------

def run_feature_diagnostics(X: pd.DataFrame) -> FeatureDiagnosticsReport:
    """便捷函数：一键诊断特征矩阵"""
    diag = FeatureDiagnostics()
    return diag.report(X)
