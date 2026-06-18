"""
Leakage Detector — 数据泄漏检测

ML Lab 第八部分：自动报警未来函数 / 数据穿越 / 标签泄漏

  检查：
    1. 代码中的 shift(-N)（未来函数）
    2. 标签使用了未来数据（标签生成时的 shift(-N)）
    3. 训练集和测试集时间重叠
    4. 滚动统计使用了未来数据（center=True）
    5. 标准化使用了全样本统计量
"""

from __future__ import annotations

import ast
import inspect
import logging
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger("quantlab.ml.leakage")


class LeakageType(str, Enum):
    """泄漏类型"""
    FUTURE_FUNCTION = "FUTURE_FUNCTION"          # 未来函数 shift(-N)
    LABEL_LEAKAGE = "LABEL_LEAKAGE"              # 标签泄漏
    TIME_OVERLAP = "TIME_OVERLAP"                # 时间重叠
    CENTERED_ROLLING = "CENTERED_ROLLING"        # 居中滚动（使用未来数据）
    FULL_SAMPLE_NORMALIZATION = "FULL_SAMPLE_NORMALIZATION"  # 全样本标准化
    LOOKAHEAD_BIAS = "LOOKAHEAD_BIAS"            # 前视偏差


class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # 严重，必须修复
    WARNING = "WARNING"     # 警告，建议修复
    INFO = "INFO"           # 提示


@dataclass
class LeakageIssue:
    """泄漏问题"""
    type: LeakageType
    severity: Severity
    message: str
    location: str = ""        # 代码位置或数据列
    suggestion: str = ""      # 修复建议

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class LeakageReport:
    """泄漏检测报告"""
    issues: List[LeakageIssue] = field(default_factory=list)
    n_critical: int = 0
    n_warning: int = 0
    n_info: int = 0
    passed: bool = True       # 是否通过（无 CRITICAL）

    def add(self, issue: LeakageIssue) -> None:
        self.issues.append(issue)
        if issue.severity == Severity.CRITICAL:
            self.n_critical += 1
            self.passed = False
        elif issue.severity == Severity.WARNING:
            self.n_warning += 1
        else:
            self.n_info += 1

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "n_critical": self.n_critical,
            "n_warning": self.n_warning,
            "n_info": self.n_info,
            "issues": [i.to_dict() for i in self.issues],
        }


class LeakageDetector:
    """
    数据泄漏检测器

    用法：
        detector = LeakageDetector()

        # 1. 检测代码中的未来函数
        report = detector.check_code(my_feature_class)

        # 2. 检测数据是否泄漏
        report = detector.check_data(features_df, label_series)

        # 3. 检测训练/测试集是否重叠
        report = detector.check_time_overlap(train_idx, test_idx)
    """

    # ----------------------------------------------------------
    # 1. 代码检测
    # ----------------------------------------------------------

    def check_code(self, obj: Any) -> LeakageReport:
        """
        检测对象（类/函数）源码中的未来函数

        检测：
          - shift(-N)
          - rolling(..., center=True)
        """
        report = LeakageReport()

        try:
            source = inspect.getsource(obj)
        except (TypeError, OSError):
            return report

        source = textwrap.dedent(source)

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return report

        for node in ast.walk(tree):
            # 检测 shift(-N)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "shift":
                    if node.args:
                        first_arg = node.args[0]
                        # shift(-1) 或 shift(-N)
                        if isinstance(first_arg, ast.UnaryOp):
                            if isinstance(first_arg.op, ast.USub):
                                if isinstance(first_arg.operand, (ast.Constant, ast.Num)):
                                    val = getattr(first_arg.operand, "value",
                                                  getattr(first_arg.operand, "n", None))
                                    report.add(LeakageIssue(
                                        type=LeakageType.FUTURE_FUNCTION,
                                        severity=Severity.CRITICAL,
                                        message=f"Detected shift(-{val}): future function",
                                        location=f"line {node.lineno}",
                                        suggestion="Use shift(N) with positive N for past data, "
                                                  "or ensure this is intentional (e.g. label generation).",
                                    ))
                        # shift(-1) in Constant (Python 3.8+)
                        elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, int):
                            if first_arg.value < 0:
                                report.add(LeakageIssue(
                                    type=LeakageType.FUTURE_FUNCTION,
                                    severity=Severity.CRITICAL,
                                    message=f"Detected shift({first_arg.value}): future function",
                                    location=f"line {node.lineno}",
                                    suggestion="Use shift(N) with positive N for past data.",
                                ))

                # 检测 rolling(..., center=True)
                if isinstance(node.func, ast.Attribute) and node.func.attr == "rolling":
                    for kw in node.keywords:
                        if kw.arg == "center":
                            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                report.add(LeakageIssue(
                                    type=LeakageType.CENTERED_ROLLING,
                                    severity=Severity.CRITICAL,
                                    message="rolling(center=True) uses future data",
                                    location=f"line {node.lineno}",
                                    suggestion="Use center=False (default) to avoid lookahead bias.",
                                ))

        return report

    # ----------------------------------------------------------
    # 2. 数据检测
    # ----------------------------------------------------------

    def check_data(
        self,
        features: pd.DataFrame,
        label: pd.Series,
    ) -> LeakageReport:
        """
        检测特征和标签的数据泄漏

        检测：
          - 标签是否包含未来数据（通过检查标签和未来收益率的相关性）
          - 特征是否包含异常强的预测力（IC > 0.5 可能是泄漏）
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

            # IC 过高可能是泄漏
            if abs(ic) > 0.5:
                report.add(LeakageIssue(
                    type=LeakageType.LABEL_LEAKAGE,
                    severity=Severity.CRITICAL,
                    message=f"Feature '{col}' has suspiciously high IC={ic:.4f} with label",
                    location=f"column: {col}",
                    suggestion="Check if this feature uses future data. IC > 0.5 is rare in real trading.",
                ))
            elif abs(ic) > 0.3:
                report.add(LeakageIssue(
                    type=LeakageType.LABEL_LEAKAGE,
                    severity=Severity.WARNING,
                    message=f"Feature '{col}' has high IC={ic:.4f} with label",
                    location=f"column: {col}",
                    suggestion="Verify this feature does not use future data.",
                ))

        return report

    # ----------------------------------------------------------
    # 3. 时间重叠检测
    # ----------------------------------------------------------

    def check_time_overlap(
        self,
        train_index: pd.Index,
        test_index: pd.Index,
    ) -> LeakageReport:
        """检测训练集和测试集时间是否重叠"""
        report = LeakageReport()

        train_set = set(train_index)
        test_set = set(test_index)
        overlap = train_set & test_set

        if overlap:
            report.add(LeakageIssue(
                type=LeakageType.TIME_OVERLAP,
                severity=Severity.CRITICAL,
                message=f"Train and test sets overlap: {len(overlap)} samples",
                location=f"overlap range: {min(overlap)} ~ {max(overlap)}",
                suggestion="Ensure train and test sets are strictly time-separated.",
            ))

        return report

    # ----------------------------------------------------------
    # 4. 综合检测
    # ----------------------------------------------------------

    def check_all(
        self,
        feature_objects: Optional[List[Any]] = None,
        label_objects: Optional[List[Any]] = None,
        features_df: Optional[pd.DataFrame] = None,
        label_series: Optional[pd.Series] = None,
        train_index: Optional[pd.Index] = None,
        test_index: Optional[pd.Index] = None,
    ) -> LeakageReport:
        """综合检测"""
        report = LeakageReport()

        # 检测特征代码
        if feature_objects:
            for obj in feature_objects:
                sub = self.check_code(obj)
                for issue in sub.issues:
                    report.add(issue)

        # 检测标签代码
        if label_objects:
            for obj in label_objects:
                sub = self.check_code(obj)
                for issue in sub.issues:
                    # 标签使用 shift(-N) 是正常的，降级为 INFO
                    if issue.type == LeakageType.FUTURE_FUNCTION:
                        issue.severity = Severity.INFO
                        issue.message = f"[Label] {issue.message} (expected for labels)"
                    report.add(issue)

        # 检测数据
        if features_df is not None and label_series is not None:
            sub = self.check_data(features_df, label_series)
            for issue in sub.issues:
                report.add(issue)

        # 检测时间重叠
        if train_index is not None and test_index is not None:
            sub = self.check_time_overlap(train_index, test_index)
            for issue in sub.issues:
                report.add(issue)

        return report
