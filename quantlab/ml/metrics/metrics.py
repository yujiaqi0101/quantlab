"""
Metrics Engine — 量化指标计算

ML Lab M2 第四部分：Metrics Engine

  量化指标优先级：
    IC          ★★★★★   预测值与真实值的 Pearson 相关系数
    RankIC      ★★★★★   预测值与真实值的 Spearman 相关系数
    Sharpe      ★★★★★   年化夏普比率（基于预测收益）
    Precision   ★★★★☆   精确率（分类）
    Recall      ★★★★☆   召回率（分类）
    AUC         ★★★★☆   ROC AUC（分类）
    Accuracy    ★★      准确率（参考用）

  原因：预测正确 ≠ 赚钱
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.metrics")


# 默认年化因子（按交易日 252）
DEFAULT_ANNUALIZATION = 252


@dataclass
class MetricsResult:
    """指标计算结果"""
    # 回归指标
    ic: float = 0.0
    rank_ic: float = 0.0
    sharpe: float = 0.0
    mae: float = 0.0
    mse: float = 0.0
    rmse: float = 0.0
    r2: float = 0.0
    # 分类指标
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    auc: float = 0.0
    # 元信息
    n_samples: int = 0
    is_classifier: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ic": round(self.ic, 6),
            "rank_ic": round(self.rank_ic, 6),
            "sharpe": round(self.sharpe, 6),
            "mae": round(self.mae, 6),
            "mse": round(self.mse, 6),
            "rmse": round(self.rmse, 6),
            "r2": round(self.r2, 6),
            "accuracy": round(self.accuracy, 6),
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "auc": round(self.auc, 6),
            "n_samples": self.n_samples,
            "is_classifier": self.is_classifier,
            "extra": self.extra,
        }


# ------------------------------------------------------------------
# 单指标计算函数
# ------------------------------------------------------------------

def compute_ic(y_true: pd.Series, y_pred: pd.Series) -> float:
    """
    Information Coefficient — Pearson 相关系数

    IC > 0.05 即认为有预测能力
    IC > 0.1  为强预测
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() < 2:
        return 0.0
    try:
        return float(y_true[mask].corr(y_pred[mask]))
    except Exception:
        return 0.0


def compute_rank_ic(y_true: pd.Series, y_pred: pd.Series) -> float:
    """
    Rank IC — Spearman 相关系数

    对异常值更鲁棒，量化里常用
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() < 2:
        return 0.0
    try:
        return float(y_true[mask].corr(y_pred[mask], method="spearman"))
    except Exception:
        return 0.0


def compute_sharpe(
    y_true: pd.Series,
    y_pred: pd.Series,
    annualization: int = DEFAULT_ANNUALIZATION,
) -> float:
    """
    Sharpe Ratio — 年化夏普比率

    量化核心指标：预测值作为信号，计算信号加权的收益夏普

    简化计算：
      returns = y_true（真实收益）
      signal = y_pred（预测信号）
      strategy_returns = signal * returns（信号加权收益）
      sharpe = mean(strategy_returns) / std(strategy_returns) * sqrt(annualization)
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() < 2:
        return 0.0
    try:
        returns = y_true[mask].astype(float)
        signal = y_pred[mask].astype(float)
        # 信号加权收益
        strategy_returns = signal * returns
        if strategy_returns.std() == 0:
            return 0.0
        sharpe = (
            strategy_returns.mean() / strategy_returns.std()
            * np.sqrt(annualization)
        )
        return float(sharpe)
    except Exception:
        return 0.0


def compute_accuracy(y_true: pd.Series, y_pred: pd.Series) -> float:
    """分类准确率"""
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() == 0:
        return 0.0
    try:
        return float((y_true[mask] == y_pred[mask]).mean())
    except Exception:
        return 0.0


def compute_precision(
    y_true: pd.Series,
    y_pred: pd.Series,
    positive_label: Any = 1,
) -> float:
    """
    精确率：预测为正的样本中，实际为正的比例

    Precision = TP / (TP + FP)
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() == 0:
        return 0.0
    try:
        from sklearn.metrics import precision_score
        yt = y_true[mask].astype(int)
        yp = y_pred[mask].astype(int)
        return float(precision_score(yt, yp, pos_label=positive_label, zero_division=0))
    except Exception:
        # 手动计算
        yt = y_true[mask]
        yp = y_pred[mask]
        predicted_pos = (yp == positive_label).sum()
        if predicted_pos == 0:
            return 0.0
        true_pos = ((yp == positive_label) & (yt == positive_label)).sum()
        return float(true_pos / predicted_pos)


def compute_recall(
    y_true: pd.Series,
    y_pred: pd.Series,
    positive_label: Any = 1,
) -> float:
    """
    召回率：实际为正的样本中，被预测为正的比例

    Recall = TP / (TP + FN)
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() == 0:
        return 0.0
    try:
        from sklearn.metrics import recall_score
        yt = y_true[mask].astype(int)
        yp = y_pred[mask].astype(int)
        return float(recall_score(yt, yp, pos_label=positive_label, zero_division=0))
    except Exception:
        yt = y_true[mask]
        yp = y_pred[mask]
        actual_pos = (yt == positive_label).sum()
        if actual_pos == 0:
            return 0.0
        true_pos = ((yp == positive_label) & (yt == positive_label)).sum()
        return float(true_pos / actual_pos)


def compute_auc(
    y_true: pd.Series,
    y_pred: pd.Series,
) -> float:
    """
    ROC AUC — 需要概率预测或连续分数

    适用于二分类，y_pred 为正类的概率或分数
    """
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() < 2:
        return 0.0
    try:
        from sklearn.metrics import roc_auc_score
        yt = y_true[mask].astype(int)
        yp = y_pred[mask].astype(float)
        # 检查是否为二分类
        if yt.nunique() < 2:
            return 0.0
        return float(roc_auc_score(yt, yp))
    except Exception:
        return 0.0


# ------------------------------------------------------------------
# 批量指标计算
# ------------------------------------------------------------------

def compute_regression_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    annualization: int = DEFAULT_ANNUALIZATION,
) -> MetricsResult:
    """计算回归指标：IC / RankIC / Sharpe / MAE / MSE / RMSE / R2"""
    mask = y_true.notna() & y_pred.notna()
    n = int(mask.sum())
    if n == 0:
        return MetricsResult(n_samples=0, is_classifier=False)

    yt = y_true[mask].astype(float)
    yp = y_pred[mask].astype(float)

    result = MetricsResult(
        n_samples=n,
        is_classifier=False,
        ic=compute_ic(yt, yp),
        rank_ic=compute_rank_ic(yt, yp),
        sharpe=compute_sharpe(yt, yp, annualization),
    )

    try:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        result.mae = float(mean_absolute_error(yt, yp))
        result.mse = float(mean_squared_error(yt, yp))
        result.rmse = float(np.sqrt(result.mse))
        result.r2 = float(r2_score(yt, yp))
    except Exception as e:
        logger.warning(f"sklearn metrics failed: {e}")

    return result


def compute_classification_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_proba: Optional[pd.Series] = None,
    positive_label: Any = 1,
) -> MetricsResult:
    """
    计算分类指标：Accuracy / Precision / Recall / AUC / IC

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_proba: 正类概率（可选，用于 AUC）
        positive_label: 正类标签
    """
    mask = y_true.notna() & y_pred.notna()
    n = int(mask.sum())
    if n == 0:
        return MetricsResult(n_samples=0, is_classifier=True)

    yt = y_true[mask]
    yp = y_pred[mask]

    result = MetricsResult(
        n_samples=n,
        is_classifier=True,
        accuracy=compute_accuracy(yt, yp),
        precision=compute_precision(yt, yp, positive_label),
        recall=compute_recall(yt, yp, positive_label),
        # IC 对分类也有意义（预测分数与真实标签的相关性）
        ic=compute_ic(yt.astype(float), yp.astype(float)),
    )

    # AUC：优先用概率，否则用预测标签
    if y_proba is not None:
        proba_masked = y_proba[mask] if hasattr(y_proba, "__getitem__") else y_proba
        result.auc = compute_auc(yt, pd.Series(proba_masked, index=yt.index))
    else:
        result.auc = compute_auc(yt, yp.astype(float))

    return result


def compute_all_metrics(
    y_true: Union[pd.Series, np.ndarray, list],
    y_pred: Union[pd.Series, np.ndarray, list],
    is_classifier: bool = False,
    y_proba: Optional[Union[pd.Series, np.ndarray, list]] = None,
    annualization: int = DEFAULT_ANNUALIZATION,
    positive_label: Any = 1,
) -> MetricsResult:
    """
    一键计算所有指标

    Args:
        y_true: 真实值
        y_pred: 预测值
        is_classifier: 是否分类问题
        y_proba: 正类概率（分类用，可选）
        annualization: 年化因子（回归用）
        positive_label: 正类标签（分类用）

    Returns:
        MetricsResult

    用法：
        # 回归
        metrics = compute_all_metrics(y_true, y_pred, is_classifier=False)
        print(f"IC={metrics.ic:.4f}, Sharpe={metrics.sharpe:.4f}")

        # 分类
        metrics = compute_all_metrics(y_true, y_pred, is_classifier=True, y_proba=proba)
        print(f"AUC={metrics.auc:.4f}, Precision={metrics.precision:.4f}")
    """
    # 统一转为 pd.Series
    if not isinstance(y_true, pd.Series):
        y_true = pd.Series(y_true, name="y_true")
    if not isinstance(y_pred, pd.Series):
        y_pred = pd.Series(y_pred, index=y_true.index, name="y_pred")
    if y_proba is not None and not isinstance(y_proba, pd.Series):
        y_proba = pd.Series(y_proba, index=y_true.index, name="y_proba")

    if is_classifier:
        return compute_classification_metrics(
            y_true, y_pred, y_proba=y_proba, positive_label=positive_label,
        )
    else:
        return compute_regression_metrics(y_true, y_pred, annualization=annualization)
