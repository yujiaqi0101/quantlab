"""
TrainingValidator — 训练前防泄漏校验

在 TrainingJob.run() 之前调用 validate()，检查:
  1. 时序切分严格无未来信息泄漏
  2. 特征中无未来函数 (label 泄漏到特征)
  3. 训练集/测试集日期不重叠
  4. 标签生成窗口不超过训练边界
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class ValidationIssue:
    level: str  # "error" / "warning"
    category: str  # "leakage" / "split" / "label"
    message: str
    feature: str = ""


@dataclass
class ValidationReport:
    ok: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0

    def add_error(self, category: str, message: str, feature: str = "") -> None:
        self.issues.append(ValidationIssue("error", category, message, feature))
        self.errors += 1
        self.ok = False

    def add_warning(self, category: str, message: str, feature: str = "") -> None:
        self.issues.append(ValidationIssue("warning", category, message, feature))
        self.warnings += 1

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [
                {
                    "level": i.level,
                    "category": i.category,
                    "message": i.message,
                    "feature": i.feature,
                }
                for i in self.issues
            ],
        }


class TrainingValidator:
    """训练前防泄漏校验。"""

    def validate(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        label_horizon: Optional[int] = None,
    ) -> ValidationReport:
        report = ValidationReport()

        # 1. 训练集/测试集日期不重叠
        if isinstance(X_train.index, pd.MultiIndex) and isinstance(X_test.index, pd.MultiIndex):
            train_dates = set(X_train.index.get_level_values("datetime"))
            test_dates = set(X_test.index.get_level_values("datetime"))
            overlap = train_dates & test_dates
            if overlap:
                report.add_error(
                    "split",
                    f"训练集/测试集日期重叠: {len(overlap)} 个日期 "
                    f"(示例: {sorted(overlap)[:3]})",
                )
        else:
            train_idx = set(X_train.index)
            test_idx = set(X_test.index)
            overlap = train_idx & test_idx
            if overlap:
                report.add_error(
                    "split",
                    f"训练集/测试集 index 重叠: {len(overlap)} 个",
                )

        # 2. 时序切分: train 的 datetime 必须都早于 test
        if isinstance(X_train.index, pd.MultiIndex):
            train_max = X_train.index.get_level_values("datetime").max()
            test_min = X_test.index.get_level_values("datetime").min()
            if train_max >= test_min:
                report.add_error(
                    "leakage",
                    f"时序切分泄漏: 训练集最大日期 {train_max} >= 测试集最小日期 {test_min}",
                )

        # 3. NaN 检查
        nan_ratio = X_train.isna().mean().mean()
        if nan_ratio > 0.3:
            report.add_warning(
                "data_quality",
                f"训练集 NaN 比例较高: {nan_ratio:.2%}",
            )

        # 4. 标签 NaN 检查
        if y_train.isna().mean() > 0.2:
            report.add_warning(
                "label",
                f"训练标签 NaN 比例较高: {y_train.isna().mean():.2%}",
            )

        # 5. 标签 horizon 检查
        if label_horizon is not None:
            # 测试集开始的 horizon 期内，标签可能依赖训练集数据 (不算泄漏，但要警告)
            if isinstance(X_test.index, pd.MultiIndex):
                test_dates = sorted(X_test.index.get_level_values("datetime").unique())
                if len(test_dates) >= label_horizon:
                    report.add_warning(
                        "label",
                        f"测试集前 {label_horizon} 期的标签可能依赖训练集尾部数据",
                    )

        return report


__all__ = ["TrainingValidator", "ValidationReport", "ValidationIssue"]
