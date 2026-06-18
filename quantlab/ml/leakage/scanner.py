"""
Feature Leakage Scanner — 特征泄漏扫描器

ML Lab M3 第二部分：扫描 FeatureSet 发现未来数据

  自动检查：
    1. Feature 代码中的 shift(-N)（未来函数）
    2. Feature 与 Label 的 IC 过高（>0.5 CRITICAL）
    3. Feature 名包含未来暗示（future/forward/next/target）
    4. rolling(center=True)

  输出：
    CRITICAL / WARNING / INFO
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd

from .detector import (
    LeakageDetector, LeakageReport, LeakageIssue,
    LeakageType, Severity,
)

logger = logging.getLogger("quantlab.ml.leakage.scanner")


# 特征名中暗示未来的关键词
FUTURE_KEYWORDS = [
    "future", "forward", "next", "target",
    "label", "y_", "ret_future", "fwd",
]


class FeatureLeakageScanner:
    """
    特征泄漏扫描器

    用法：
        scanner = FeatureLeakageScanner()

        # 1. 扫描 FeatureSet 代码
        report = scanner.scan_feature_set(feature_set)

        # 2. 扫描特征数据
        report = scanner.scan_data(features_df, label_series)

        # 3. 扫描特征名
        report = scanner.scan_names(feature_names)
    """

    def __init__(self) -> None:
        self._detector = LeakageDetector()

    def scan_feature_set(self, feature_set: Any) -> LeakageReport:
        """
        扫描 FeatureSet 中的所有 Feature 代码

        Args:
            feature_set: FeatureSet 对象，包含 feature_ids

        Returns:
            LeakageReport
        """
        report = LeakageReport()

        try:
            from ..feature import get_feature_registry
            registry = get_feature_registry()
            feature_ids = getattr(feature_set, "feature_ids", []) or []
            for fid in feature_ids:
                feat = registry.get_feature(fid)
                if feat is None:
                    continue
                # 扫描 Feature 类的代码
                sub = self._detector.check_code(type(feat))
                for issue in sub.issues:
                    issue.location = f"feature: {fid} | {issue.location}"
                    report.add(issue)
        except Exception as e:
            logger.warning(f"scan_feature_set failed: {e}")

        return report

    def scan_data(
        self,
        features: pd.DataFrame,
        label: pd.Series,
        ic_threshold_critical: float = 0.5,
        ic_threshold_warning: float = 0.3,
    ) -> LeakageReport:
        """
        扫描特征数据，检测异常高的预测力

        Args:
            features: 特征 DataFrame
            label: 标签 Series
            ic_threshold_critical: CRITICAL 阈值（默认 0.5）
            ic_threshold_warning: WARNING 阈值（默认 0.3）
        """
        report = LeakageReport()

        common_idx = features.index.intersection(label.index)
        features = features.loc[common_idx]
        label = label.loc[common_idx]
        valid_mask = label.notna()
        label_valid = label[valid_mask]

        for col in features.columns:
            feat = features[col][valid_mask]
            mask = feat.notna() & label_valid.notna()
            if mask.sum() < 10:
                continue
            try:
                ic = float(feat[mask].corr(label_valid[mask]))
            except Exception:
                continue

            if abs(ic) > ic_threshold_critical:
                report.add(LeakageIssue(
                    type=LeakageType.LABEL_LEAKAGE,
                    severity=Severity.CRITICAL,
                    message=f"Feature '{col}' IC={ic:.4f} > {ic_threshold_critical} (likely leakage)",
                    location=f"column: {col}",
                    suggestion="Check if this feature uses future data.",
                ))
            elif abs(ic) > ic_threshold_warning:
                report.add(LeakageIssue(
                    type=LeakageType.LABEL_LEAKAGE,
                    severity=Severity.WARNING,
                    message=f"Feature '{col}' IC={ic:.4f} > {ic_threshold_warning}",
                    location=f"column: {col}",
                    suggestion="Verify this feature does not use future data.",
                ))

        return report

    def scan_names(self, feature_names: List[str]) -> LeakageReport:
        """
        扫描特征名，检测未来暗示关键词

        Args:
            feature_names: 特征名列表
        """
        report = LeakageReport()
        pattern = re.compile("|".join(FUTURE_KEYWORDS), re.IGNORECASE)

        for name in feature_names:
            if pattern.search(name):
                report.add(LeakageIssue(
                    type=LeakageType.LOOKAHEAD_BIAS,
                    severity=Severity.WARNING,
                    message=f"Feature name '{name}' contains future-related keyword",
                    location=f"name: {name}",
                    suggestion="Rename or verify this feature does not use future data.",
                ))

        return report

    def scan_all(
        self,
        feature_set: Optional[Any] = None,
        features_df: Optional[pd.DataFrame] = None,
        label_series: Optional[pd.Series] = None,
    ) -> LeakageReport:
        """综合扫描"""
        report = LeakageReport()

        if feature_set is not None:
            sub = self.scan_feature_set(feature_set)
            for issue in sub.issues:
                report.add(issue)

        if features_df is not None:
            # 扫描特征名
            sub = self.scan_names(list(features_df.columns))
            for issue in sub.issues:
                report.add(issue)

            # 扫描数据
            if label_series is not None:
                sub = self.scan_data(features_df, label_series)
                for issue in sub.issues:
                    report.add(issue)

        return report
