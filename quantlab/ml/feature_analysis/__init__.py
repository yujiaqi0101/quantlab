"""
Feature Analysis — 特征分析

ML Lab 第四部分 + 第八部分：Alpha Factory 的基础 + Feature Importance

  统计指标（第四部分）：
    - IC (Information Coefficient)
    - Rank IC
    - Mutual Information
    - Correlation

  特征重要性（第八部分）：
    - Gain         — 模型内置 gain importance
    - Permutation  — 排列重要性（模型无关）
    - SHAP         — SHAP 值（可选）

  用法：
      analyzer = FeatureAnalyzer()
      result = analyzer.analyze(features_df, label_series)

      fi_analyzer = FeatureImportanceAnalyzer()
      fi_result = fi_analyzer.analyze(model, X, y, methods=["gain", "permutation"])
"""

from .analyzer import FeatureAnalyzer, FeatureAnalysisResult
from .importance import (
    ImportanceResult,
    FeatureImportanceAnalyzer,
    compute_gain_importance,
    compute_permutation_importance,
    compute_shap_importance,
)

__all__ = [
    "FeatureAnalyzer",
    "FeatureAnalysisResult",
    "ImportanceResult",
    "FeatureImportanceAnalyzer",
    "compute_gain_importance",
    "compute_permutation_importance",
    "compute_shap_importance",
]
