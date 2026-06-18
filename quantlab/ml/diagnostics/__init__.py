"""
ML Diagnostics — 诊断模块

ML Lab M1 必做：
  Feature Diagnostics — 发现坏特征（全空/全0/方差≈0/inf）
  Label Diagnostics   — 发现标签失衡（类别分布严重倾斜）
"""

from .feature_diagnostics import (
    FeatureDiagnostics,
    FeatureDiagnosticResult,
    FeatureDiagnosticsReport,
    run_feature_diagnostics,
)
from .label_diagnostics import (
    LabelDiagnostics,
    LabelDiagnosticResult,
    LabelDiagnosticsReport,
    run_label_diagnostics,
)

__all__ = [
    "FeatureDiagnostics",
    "FeatureDiagnosticResult",
    "FeatureDiagnosticsReport",
    "run_feature_diagnostics",
    "LabelDiagnostics",
    "LabelDiagnosticResult",
    "LabelDiagnosticsReport",
    "run_label_diagnostics",
]
