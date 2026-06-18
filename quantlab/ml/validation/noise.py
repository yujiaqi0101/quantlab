"""
Noise Tester — 噪音注入测试

ML Lab M3 第六部分：人为增加噪音/缺失值/随机误差

  验证：模型是否还能工作

  测试：
    1. 噪音注入：给测试特征加高斯噪音
    2. 缺失值注入：随机置 NaN
    3. 异常值注入：随机替换为极端值

  输出：Noise Sensitivity
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..model import Model

logger = logging.getLogger("quantlab.ml.validation.noise")


@dataclass
class NoiseTestItem:
    """单次噪音测试"""
    name: str = ""
    noise_level: float = 0.0
    ic: float = 0.0
    sharpe: float = 0.0
    rmse: float = 0.0
    delta_ic: float = 0.0
    delta_sharpe: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "noise_level": self.noise_level,
            "ic": round(self.ic, 6),
            "sharpe": round(self.sharpe, 6),
            "rmse": round(self.rmse, 6),
            "delta_ic": round(self.delta_ic, 6),
            "delta_sharpe": round(self.delta_sharpe, 6),
        }


@dataclass
class NoiseTestResult:
    """噪音测试结果"""
    baseline_ic: float = 0.0
    baseline_sharpe: float = 0.0
    tests: List[NoiseTestItem] = field(default_factory=list)
    # 噪音敏感度
    noise_sensitivity: float = 0.0     # IC 下降比例 / 噪音水平
    # 评分
    noise_score: float = 0.0
    grade: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_ic": round(self.baseline_ic, 6),
            "baseline_sharpe": round(self.baseline_sharpe, 6),
            "tests": [t.to_dict() for t in self.tests],
            "noise_sensitivity": round(self.noise_sensitivity, 6),
            "noise_score": round(self.noise_score, 2),
            "grade": self.grade,
        }


class NoiseTester:
    """
    噪音注入测试器

    用法：
        tester = NoiseTester()
        result = tester.test(model, X_test, y_test)
        print(f"Noise Sensitivity: {result.noise_sensitivity}")
    """

    def __init__(
        self,
        noise_levels: Optional[List[float]] = None,
        missing_ratios: Optional[List[float]] = None,
        outlier_ratios: Optional[List[float]] = None,
        seed: int = 42,
    ) -> None:
        self.noise_levels = noise_levels or [0.01, 0.05, 0.10]
        self.missing_ratios = missing_ratios or [0.05, 0.10, 0.20]
        self.outlier_ratios = outlier_ratios or [0.05, 0.10]
        self.seed = seed

    def test(
        self,
        model: Model,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> NoiseTestResult:
        """
        执行噪音测试

        Args:
            model: 已训练的模型
            X: 测试特征
            y: 测试标签
        """
        result = NoiseTestResult()
        rng = np.random.RandomState(self.seed)

        # 基准
        base_metrics = model.evaluate(X, y)
        result.baseline_ic = base_metrics.ic
        result.baseline_sharpe = base_metrics.sharpe

        tests: List[NoiseTestItem] = []

        # 1. 噪音注入
        for level in self.noise_levels:
            try:
                X_noisy = X.copy()
                # 按每列 std 缩放噪音
                for col in X.columns:
                    std = X[col].std()
                    if std > 0 and not np.isnan(std):
                        noise = rng.normal(0, level * std, len(X))
                        X_noisy[col] = X[col] + noise
                metrics = model.evaluate(X_noisy, y)
                tests.append(NoiseTestItem(
                    name="gaussian_noise",
                    noise_level=level,
                    ic=metrics.ic,
                    sharpe=metrics.sharpe,
                    rmse=metrics.rmse,
                    delta_ic=metrics.ic - result.baseline_ic,
                    delta_sharpe=metrics.sharpe - result.baseline_sharpe,
                ))
            except Exception as e:
                logger.warning(f"Noise test level={level} failed: {e}")

        # 2. 缺失值注入
        for ratio in self.missing_ratios:
            try:
                X_missing = X.copy()
                mask = rng.random(X.shape) < ratio
                X_missing.values[mask] = np.nan
                # 模型需支持 NaN，否则用 0 填充
                if not _model_supports_nan(model):
                    X_missing = X_missing.fillna(0)
                metrics = model.evaluate(X_missing, y)
                tests.append(NoiseTestItem(
                    name="missing_values",
                    noise_level=ratio,
                    ic=metrics.ic,
                    sharpe=metrics.sharpe,
                    rmse=metrics.rmse,
                    delta_ic=metrics.ic - result.baseline_ic,
                    delta_sharpe=metrics.sharpe - result.baseline_sharpe,
                ))
            except Exception as e:
                logger.warning(f"Missing test ratio={ratio} failed: {e}")

        # 3. 异常值注入
        for ratio in self.outlier_ratios:
            try:
                X_outlier = X.copy()
                mask = rng.random(X.shape) < ratio
                # 替换为 10 倍 std 的极端值
                for col in X.columns:
                    std = X[col].std()
                    if std > 0:
                        extreme = rng.choice([-10, 10], size=len(X)) * std
                        col_mask = mask[:, X.columns.get_loc(col)]
                        X_outlier.loc[col_mask, col] = extreme[col_mask]
                metrics = model.evaluate(X_outlier, y)
                tests.append(NoiseTestItem(
                    name="outliers",
                    noise_level=ratio,
                    ic=metrics.ic,
                    sharpe=metrics.sharpe,
                    rmse=metrics.rmse,
                    delta_ic=metrics.ic - result.baseline_ic,
                    delta_sharpe=metrics.sharpe - result.baseline_sharpe,
                ))
            except Exception as e:
                logger.warning(f"Outlier test ratio={ratio} failed: {e}")

        result.tests = tests

        # 噪音敏感度：平均 IC 下降比例 / 平均噪音水平
        if tests and abs(result.baseline_ic) > 1e-8:
            avg_drop = np.mean([
                (result.baseline_ic - t.ic) / abs(result.baseline_ic)
                for t in tests
            ])
            avg_level = np.mean([t.noise_level for t in tests])
            if avg_level > 0:
                result.noise_sensitivity = float(avg_drop / avg_level)

        # 评分
        result.noise_score = self._compute_score(result)
        result.grade = self._score_to_grade(result.noise_score)
        return result

    def _compute_score(self, result: NoiseTestResult) -> float:
        """评分：噪音敏感度越低越好"""
        # sensitivity < 1 为良好，> 5 为差
        if result.noise_sensitivity <= 0:
            return 100.0
        score = max(0, 100 - result.noise_sensitivity * 15)
        return float(score)

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"


def _model_supports_nan(model: Model) -> bool:
    """判断模型是否原生支持 NaN（如 LightGBM/XGBoost）"""
    model_type = getattr(model, "model_type", None)
    if model_type is None:
        return False
    return model_type.name in ("LIGHTGBM", "XGBOOST")
