"""
Feature Importance — 特征重要性

ML Lab 第八层：训练完立即生成

  支持三种方法：
    1. Gain         — 模型内置的 gain importance（树模型）
    2. Permutation  — 排列重要性（模型无关）
    3. SHAP         — SHAP 值（可选，需 shap 库）

  前端：Feature Importance 页面
    输出：Momentum20 35%, RSI14 25%, ATR14 10%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ..model import Model
    from ..pipeline import TrainingDataset

logger = logging.getLogger("quantlab.ml.feature_analysis.importance")


@dataclass
class ImportanceResult:
    """特征重要性结果"""
    method: str = ""                       # gain / permutation / shap
    feature_names: List[str] = field(default_factory=list)
    importances: List[float] = field(default_factory=list)
    normalized: List[float] = field(default_factory=list)   # 归一化到 0-1
    ranking: List[int] = field(default_factory=list)        # 排名 1=最重要

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "feature_names": self.feature_names,
            "importances": [round(float(v), 6) for v in self.importances],
            "normalized": [round(float(v), 6) for v in self.normalized],
            "ranking": self.ranking,
            "details": [
                {
                    "feature": self.feature_names[i],
                    "importance": round(float(self.importances[i]), 6),
                    "normalized": round(float(self.normalized[i]), 6),
                    "rank": self.ranking[i],
                }
                for i in range(len(self.feature_names))
            ],
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.importances,
            "normalized": self.normalized,
            "rank": self.ranking,
        }).sort_values("importance", ascending=False).reset_index(drop=True)


def compute_gain_importance(model: "Model") -> ImportanceResult:
    """
    计算 Gain importance（模型内置）

    适用于：树模型（RandomForest / XGBoost / LightGBM）
    """
    fi = model.feature_importance()
    if fi is None:
        return ImportanceResult(method="gain")

    # fi 是 pd.Series，index=feature_names, values=importances
    feature_names = list(fi.index)
    importances = [float(v) for v in fi.values]

    # 归一化
    total = sum(importances) if sum(importances) > 0 else 1.0
    normalized = [v / total for v in importances]

    # 排名
    ranking = list(pd.Series(importances).rank(ascending=False, method="min").astype(int))

    return ImportanceResult(
        method="gain",
        feature_names=feature_names,
        importances=importances,
        normalized=normalized,
        ranking=ranking,
    )


def compute_permutation_importance(
    model: "Model",
    X: pd.DataFrame,
    y: pd.Series,
    metric: str = "ic",
    n_repeats: int = 5,
    seed: int = 42,
) -> ImportanceResult:
    """
    计算排列重要性（模型无关）

    原理：打乱单个特征，看指标下降多少。下降越多，特征越重要。

    Args:
        model: 已训练的模型
        X: 特征
        y: 标签
        metric: 评估指标，如 "ic", "rmse"
        n_repeats: 每个特征重复次数
        seed: 随机种子
    """
    rng = np.random.RandomState(seed)
    feature_names = list(X.columns)

    # 基准指标
    base_metrics = model.evaluate(X, y)
    base_score = getattr(base_metrics, metric, 0.0)

    importances = []
    for col in feature_names:
        scores_diff = []
        for _ in range(n_repeats):
            X_perm = X.copy()
            X_perm[col] = rng.permutation(X_perm[col].values)
            perm_metrics = model.evaluate(X_perm, y)
            perm_score = getattr(perm_metrics, metric, 0.0)
            # 指标下降量 = 基准 - 打乱后（IC 越大越好，所以下降为正）
            scores_diff.append(base_score - perm_score)
        importances.append(float(np.mean(scores_diff)))

    # 归一化（取绝对值后归一化）
    abs_imps = [abs(v) for v in importances]
    total = sum(abs_imps) if sum(abs_imps) > 0 else 1.0
    normalized = [v / total for v in abs_imps]

    # 排名（按绝对值大小）
    ranking = list(pd.Series(abs_imps).rank(ascending=False, method="min").astype(int))

    return ImportanceResult(
        method="permutation",
        feature_names=feature_names,
        importances=importances,
        normalized=normalized,
        ranking=ranking,
    )


def compute_shap_importance(
    model: "Model",
    X: pd.DataFrame,
    max_samples: int = 100,
) -> ImportanceResult:
    """
    计算 SHAP 重要性（需 shap 库）

    Args:
        model: 已训练的模型
        X: 特征
        max_samples: 最大样本数（SHAP 计算较慢）
    """
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed, returning empty result")
        return ImportanceResult(method="shap")

    # 采样
    if len(X) > max_samples:
        X_sample = X.sample(n=max_samples, random_state=42)
    else:
        X_sample = X

    feature_names = list(X.columns)

    try:
        # 获取底层模型
        underlying = getattr(model, "_model", None) or getattr(model, "model", None)
        if underlying is None:
            logger.warning("Cannot access underlying model for SHAP")
            return ImportanceResult(method="shap", feature_names=feature_names)

        # 树模型用 TreeExplainer
        if hasattr(underlying, "feature_importances_"):
            explainer = shap.TreeExplainer(underlying)
        else:
            explainer = shap.LinearExplainer(underlying, X_sample)

        shap_values = explainer.shap_values(X_sample)

        # 分类问题可能返回 list
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        # 平均绝对 SHAP 值
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        importances = list(mean_abs_shap)

        # 归一化
        total = sum(importances) if sum(importances) > 0 else 1.0
        normalized = [v / total for v in importances]

        # 排名
        ranking = list(pd.Series(importances).rank(ascending=False, method="min").astype(int))

        return ImportanceResult(
            method="shap",
            feature_names=feature_names,
            importances=importances,
            normalized=normalized,
            ranking=ranking,
        )

    except Exception as e:
        logger.error(f"SHAP computation failed: {e}")
        return ImportanceResult(method="shap", feature_names=feature_names)


class FeatureImportanceAnalyzer:
    """
    特征重要性分析器

    用法：
        analyzer = FeatureImportanceAnalyzer()
        result = analyzer.analyze(model, X, y, methods=["gain", "permutation"])
    """

    def analyze(
        self,
        model: "Model",
        X: Optional[pd.DataFrame] = None,
        y: Optional[pd.Series] = None,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, ImportanceResult]:
        """
        分析特征重要性

        Args:
            model: 已训练的模型
            X: 特征（permutation/shap 需要）
            y: 标签（permutation 需要）
            methods: 方法列表，默认 ["gain"]
        """
        if methods is None:
            methods = ["gain"]

        results: Dict[str, ImportanceResult] = {}

        for method in methods:
            try:
                if method == "gain":
                    results["gain"] = compute_gain_importance(model)
                elif method == "permutation":
                    if X is None or y is None:
                        logger.warning("Permutation importance requires X and y")
                        continue
                    results["permutation"] = compute_permutation_importance(model, X, y)
                elif method == "shap":
                    if X is None:
                        logger.warning("SHAP importance requires X")
                        continue
                    results["shap"] = compute_shap_importance(model, X)
                else:
                    logger.warning(f"Unknown method: {method}")
            except Exception as e:
                logger.error(f"Method {method} failed: {e}")
                results[method] = ImportanceResult(method=method)

        return results

    def analyze_tds(
        self,
        model: "Model",
        tds: "TrainingDataset",
        methods: Optional[List[str]] = None,
    ) -> Dict[str, ImportanceResult]:
        """从 TrainingDataset 分析"""
        return self.analyze(model, X=tds.X, y=tds.y, methods=methods)
