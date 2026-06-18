"""
Metrics Engine — 量化指标引擎

ML Lab M2 第四部分：量化里只看 Accuracy 是错误的。

  优先级：
    IC          ★★★★★   Information Coefficient
    RankIC      ★★★★★   Spearman Rank IC
    Sharpe      ★★★★★   年化夏普比率
    Precision   ★★★★☆   精确率（分类）
    Recall      ★★★★☆   召回率（分类）
    AUC         ★★★★☆   ROC AUC（分类）
    Accuracy    ★★      准确率（参考用）

  原因：预测正确 ≠ 赚钱

  用法：
      from quantlab.ml.metrics import compute_all_metrics
      metrics = compute_all_metrics(y_true, y_pred, is_classifier=False)
"""

from .metrics import (
    compute_ic,
    compute_rank_ic,
    compute_sharpe,
    compute_precision,
    compute_recall,
    compute_accuracy,
    compute_auc,
    compute_regression_metrics,
    compute_classification_metrics,
    compute_all_metrics,
    MetricsResult,
)

__all__ = [
    "compute_ic",
    "compute_rank_ic",
    "compute_sharpe",
    "compute_precision",
    "compute_recall",
    "compute_accuracy",
    "compute_auc",
    "compute_regression_metrics",
    "compute_classification_metrics",
    "compute_all_metrics",
    "MetricsResult",
]
