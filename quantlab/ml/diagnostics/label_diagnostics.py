"""
Label Diagnostics — 标签诊断

ML Lab 第六部分：和 Feature Diagnostics 同样重要。

  统计：
    - label_distribution   标签分布
    - n_missing            缺失数
    - n_inf                无穷值数
    - variance             方差（回归标签）
    - class_distribution   类别分布（分类标签）

  报警：
    - 标签严重失衡（如 上涨 95% / 下跌 5%）
    - 标签全为空
    - 标签含 inf
    - 回归标签方差为 0
    - 分类标签类别数 ≤ 1

  用法：
      diag = LabelDiagnostics()
      report = diag.report(y)            # y: pd.Series
      # report.is_imbalanced: 是否失衡
      # report.class_distribution: 类别分布
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.diagnostics.label")


# 失衡判定阈值
DEFAULT_IMBALANCE_RATIO = 0.9     # 最大类别占比 > 90% 视为严重失衡
DEFAULT_MIN_CLASS_RATIO = 0.01    # 最小类别占比 < 1% 视为稀有类


@dataclass
class LabelDiagnosticResult:
    """标签诊断结果"""
    label_name: str = ""
    label_type: str = "regression"        # regression / classification
    n_samples: int = 0
    n_missing: int = 0
    missing_rate: float = 0.0
    n_inf: int = 0
    inf_count: int = 0
    variance: float = 0.0
    mean: float = 0.0
    std: float = 0.0
    n_unique: int = 0
    # 分类标签
    class_distribution: Dict[str, float] = field(default_factory=dict)
    n_classes: int = 0
    max_class_ratio: float = 0.0
    min_class_ratio: float = 0.0
    # 报警
    is_bad: bool = False
    is_imbalanced: bool = False
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_name": self.label_name,
            "label_type": self.label_type,
            "n_samples": self.n_samples,
            "n_missing": self.n_missing,
            "missing_rate": round(self.missing_rate, 4),
            "n_inf": self.n_inf,
            "inf_count": self.inf_count,
            "variance": float(self.variance) if np.isfinite(self.variance) else None,
            "mean": float(self.mean) if np.isfinite(self.mean) else None,
            "std": float(self.std) if np.isfinite(self.std) else None,
            "n_unique": self.n_unique,
            "class_distribution": self.class_distribution,
            "n_classes": self.n_classes,
            "max_class_ratio": round(self.max_class_ratio, 4),
            "min_class_ratio": round(self.min_class_ratio, 4),
            "is_bad": self.is_bad,
            "is_imbalanced": self.is_imbalanced,
            "issues": self.issues,
        }


@dataclass
class LabelDiagnosticsReport:
    """标签诊断完整报告"""
    label_name: str = ""
    label_type: str = "regression"
    n_samples: int = 0
    is_bad: bool = False
    is_imbalanced: bool = False
    issues: List[str] = field(default_factory=list)
    result: LabelDiagnosticResult = field(default_factory=LabelDiagnosticResult)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_name": self.label_name,
            "label_type": self.label_type,
            "n_samples": self.n_samples,
            "is_bad": self.is_bad,
            "is_imbalanced": self.is_imbalanced,
            "issues": self.issues,
            "result": self.result.to_dict(),
            "summary": self.summary,
        }


class LabelDiagnostics:
    """
    标签诊断器

    用法：
        diag = LabelDiagnostics()
        report = diag.report(y, label_type="classification")
        # report.is_imbalanced → True 表示标签严重失衡
    """

    def __init__(
        self,
        imbalance_ratio: float = DEFAULT_IMBALANCE_RATIO,
        min_class_ratio: float = DEFAULT_MIN_CLASS_RATIO,
    ) -> None:
        self.imbalance_ratio = imbalance_ratio
        self.min_class_ratio = min_class_ratio

    # ------------------------------------------------------------------
    # 自动判断标签类型
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_label_type(series: pd.Series) -> str:
        """推断标签类型：分类 or 回归"""
        # 显式分类：object / category / bool
        if pd.api.types.is_bool_dtype(series):
            return "classification"
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            return "classification"
        # 数值型：唯一值少且为整数 → 分类
        n_unique = series.nunique(dropna=True)
        if n_unique <= 10 and pd.api.types.is_integer_dtype(series):
            return "classification"
        # 默认回归
        return "regression"

    # ------------------------------------------------------------------
    # 诊断
    # ------------------------------------------------------------------

    def diagnose(
        self,
        y: pd.Series,
        label_type: Optional[str] = None,
    ) -> LabelDiagnosticResult:
        """
        诊断标签

        Args:
            y: 标签 Series
            label_type: 显式指定 "regression" / "classification"，None 则自动推断
        """
        name = str(y.name) if y.name is not None else "label"
        n_samples = len(y)
        if n_samples == 0:
            return LabelDiagnosticResult(
                label_name=name,
                n_samples=0,
                is_bad=True,
                issues=["empty_label"],
            )

        lt = label_type or self._infer_label_type(y)

        # 缺失
        n_missing = int(y.isna().sum())
        missing_rate = n_missing / n_samples

        # inf（数值型）
        n_inf = 0
        if pd.api.types.is_numeric_dtype(y):
            try:
                n_inf = int(np.isinf(y.dropna()).sum())
            except Exception:
                n_inf = 0

        # 数值统计（回归标签）
        variance = 0.0
        mean = 0.0
        std = 0.0
        n_unique = int(y.nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(y):
            try:
                clean = y.replace([np.inf, -np.inf], np.nan).dropna()
                if len(clean) > 0:
                    variance = float(clean.var())
                    mean = float(clean.mean())
                    std = float(clean.std())
            except Exception:
                pass

        # 类别分布（分类标签）
        class_distribution: Dict[str, float] = {}
        n_classes = 0
        max_class_ratio = 0.0
        min_class_ratio = 0.0
        if lt == "classification":
            try:
                counts = y.value_counts(dropna=True, normalize=True)
                n_classes = len(counts)
                if n_classes > 0:
                    # key 统一转 str，便于 JSON 序列化
                    class_distribution = {str(k): float(v) for k, v in counts.items()}
                    max_class_ratio = float(counts.iloc[0])
                    min_class_ratio = float(counts.iloc[-1])
            except Exception:
                pass

        # 判定问题
        issues: List[str] = []
        is_imbalanced = False

        if missing_rate >= 1.0:
            issues.append("all_missing")
        elif missing_rate > 0.5:
            issues.append("high_missing_rate")

        if n_inf > 0:
            issues.append("has_inf")

        if lt == "regression":
            if variance < 1e-10:
                issues.append("near_zero_variance")
            if n_unique <= 1:
                issues.append("constant_label")
        else:
            # 分类标签：判定失衡
            if n_classes <= 1:
                issues.append("single_class")
            else:
                if max_class_ratio > self.imbalance_ratio:
                    issues.append("severe_imbalance")
                    is_imbalanced = True
                if min_class_ratio < self.min_class_ratio:
                    issues.append("rare_class")

        is_bad = len(issues) > 0

        return LabelDiagnosticResult(
            label_name=name,
            label_type=lt,
            n_samples=n_samples,
            n_missing=n_missing,
            missing_rate=missing_rate,
            n_inf=n_inf,
            inf_count=n_inf,
            variance=variance,
            mean=mean,
            std=std,
            n_unique=n_unique,
            class_distribution=class_distribution,
            n_classes=n_classes,
            max_class_ratio=max_class_ratio,
            min_class_ratio=min_class_ratio,
            is_bad=is_bad,
            is_imbalanced=is_imbalanced,
            issues=issues,
        )

    def report(
        self,
        y: pd.Series,
        label_type: Optional[str] = None,
    ) -> LabelDiagnosticsReport:
        """生成完整诊断报告"""
        result = self.diagnose(y, label_type=label_type)

        summary = {
            "label_name": result.label_name,
            "label_type": result.label_type,
            "n_samples": result.n_samples,
            "is_bad": result.is_bad,
            "is_imbalanced": result.is_imbalanced,
            "n_issues": len(result.issues),
            "issues": result.issues,
            "n_classes": result.n_classes,
            "max_class_ratio": round(result.max_class_ratio, 4),
            "min_class_ratio": round(result.min_class_ratio, 4),
            "imbalance_threshold": self.imbalance_ratio,
            "min_class_threshold": self.min_class_ratio,
        }

        return LabelDiagnosticsReport(
            label_name=result.label_name,
            label_type=result.label_type,
            n_samples=result.n_samples,
            is_bad=result.is_bad,
            is_imbalanced=result.is_imbalanced,
            issues=result.issues,
            result=result,
            summary=summary,
        )


# ------------------------------------------------------------------
# 模块级便捷函数
# ------------------------------------------------------------------

def run_label_diagnostics(
    y: pd.Series,
    label_type: Optional[str] = None,
) -> LabelDiagnosticsReport:
    """便捷函数：一键诊断标签"""
    diag = LabelDiagnostics()
    return diag.report(y, label_type=label_type)
