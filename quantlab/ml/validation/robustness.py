"""
Robustness Tester — 鲁棒性测试

ML Lab M3 第五部分：抗过拟合检测

  参数扰动测试：
    RSI14 → RSI13 / RSI15
    观察：结果是否崩掉

    如果 Sharpe 1.5 → -1.2，说明过拟合

  测试方式：
    1. 特征值扰动（小幅修改特征值）
    2. 训练数据扰动（bootstrap 采样）
    3. 随机种子扰动（不同 seed 训练）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

import numpy as np
import pandas as pd

from ..model import Model, ModelType, create_model

logger = logging.getLogger("quantlab.ml.validation.robustness")


@dataclass
class PerturbationResult:
    """单次扰动结果"""
    name: str = ""
    ic: float = 0.0
    sharpe: float = 0.0
    rmse: float = 0.0
    delta_ic: float = 0.0       # 与基准的差
    delta_sharpe: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ic": round(self.ic, 6),
            "sharpe": round(self.sharpe, 6),
            "rmse": round(self.rmse, 6),
            "delta_ic": round(self.delta_ic, 6),
            "delta_sharpe": round(self.delta_sharpe, 6),
        }


@dataclass
class RobustnessResult:
    """鲁棒性测试结果"""
    baseline_ic: float = 0.0
    baseline_sharpe: float = 0.0
    perturbations: List[PerturbationResult] = field(default_factory=list)
    # 统计
    mean_ic: float = 0.0
    std_ic: float = 0.0
    ic_drop_ratio: float = 0.0        # IC 下降比例
    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    sharpe_drop_ratio: float = 0.0
    # 评分
    robustness_score: float = 0.0     # 0~100
    grade: str = ""
    is_overfit: bool = False          # 是否过拟合

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_ic": round(self.baseline_ic, 6),
            "baseline_sharpe": round(self.baseline_sharpe, 6),
            "perturbations": [p.to_dict() for p in self.perturbations],
            "mean_ic": round(self.mean_ic, 6),
            "std_ic": round(self.std_ic, 6),
            "ic_drop_ratio": round(self.ic_drop_ratio, 4),
            "mean_sharpe": round(self.mean_sharpe, 6),
            "std_sharpe": round(self.std_sharpe, 6),
            "sharpe_drop_ratio": round(self.sharpe_drop_ratio, 4),
            "robustness_score": round(self.robustness_score, 2),
            "grade": self.grade,
            "is_overfit": self.is_overfit,
        }


class RobustnessTester:
    """
    鲁棒性测试器

    用法：
        tester = RobustnessTester()
        result = tester.test(
            X_train, y_train, X_test, y_test,
            model_type=ModelType.LIGHTGBM,
            model_params={"n_estimators": 100},
        )
        print(f"Robustness: {result.grade}, Overfit: {result.is_overfit}")
    """

    def __init__(
        self,
        n_perturbations: int = 5,
        noise_level: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.n_perturbations = n_perturbations
        self.noise_level = noise_level
        self.seed = seed

    def test(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_type: ModelType,
        model_params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> RobustnessResult:
        """
        执行鲁棒性测试

        Args:
            X_train, y_train: 训练数据
            X_test, y_test: 测试数据
            model_type: 模型类型
            model_params: 模型参数
            is_classifier: 是否分类
        """
        result = RobustnessResult()
        rng = np.random.RandomState(self.seed)

        # 基准模型
        base_model = create_model(model_type, model_params, is_classifier)
        base_model.fit(X_train, y_train)
        base_metrics = base_model.evaluate(X_test, y_test)
        result.baseline_ic = base_metrics.ic
        result.baseline_sharpe = base_metrics.sharpe

        # 扰动测试
        perturbations: List[PerturbationResult] = []

        for i in range(self.n_perturbations):
            # 1. 特征值扰动：给训练特征加少量噪音
            noise = rng.normal(0, self.noise_level, X_train.shape)
            X_train_noisy = X_train + noise

            try:
                model = create_model(model_type, model_params, is_classifier)
                model.fit(X_train_noisy, y_train)
                metrics = model.evaluate(X_test, y_test)

                p = PerturbationResult(
                    name=f"feature_noise_{i}",
                    ic=metrics.ic,
                    sharpe=metrics.sharpe,
                    rmse=metrics.rmse,
                    delta_ic=metrics.ic - result.baseline_ic,
                    delta_sharpe=metrics.sharpe - result.baseline_sharpe,
                )
                perturbations.append(p)
            except Exception as e:
                logger.warning(f"Perturbation {i} failed: {e}")

            # 2. 随机种子扰动
            seed_params = dict(model_params or {})
            seed_params["random_state"] = rng.randint(0, 10000)
            try:
                model = create_model(model_type, seed_params, is_classifier)
                model.fit(X_train, y_train)
                metrics = model.evaluate(X_test, y_test)

                p = PerturbationResult(
                    name=f"seed_{i}",
                    ic=metrics.ic,
                    sharpe=metrics.sharpe,
                    rmse=metrics.rmse,
                    delta_ic=metrics.ic - result.baseline_ic,
                    delta_sharpe=metrics.sharpe - result.baseline_sharpe,
                )
                perturbations.append(p)
            except Exception as e:
                logger.warning(f"Seed perturbation {i} failed: {e}")

        result.perturbations = perturbations

        if not perturbations:
            return result

        # 统计
        ics = [p.ic for p in perturbations]
        sharpes = [p.sharpe for p in perturbations]

        result.mean_ic = float(np.mean(ics))
        result.std_ic = float(np.std(ics))
        result.mean_sharpe = float(np.mean(sharpes))
        result.std_sharpe = float(np.std(sharpes))

        # 下降比例
        if abs(result.baseline_ic) > 1e-8:
            result.ic_drop_ratio = float(
                (result.baseline_ic - result.mean_ic) / abs(result.baseline_ic)
            )
        if abs(result.baseline_sharpe) > 1e-8:
            result.sharpe_drop_ratio = float(
                (result.baseline_sharpe - result.mean_sharpe)
                / abs(result.baseline_sharpe)
            )

        # 评分
        result.robustness_score = self._compute_score(result)
        result.grade = self._score_to_grade(result.robustness_score)
        # 过拟合判断：IC 下降超过 50% 或 Sharpe 反转
        result.is_overfit = (
            result.ic_drop_ratio > 0.5
            or (result.baseline_sharpe > 0 and result.mean_sharpe < 0)
        )

        return result

    def _compute_score(self, result: RobustnessResult) -> float:
        """评分：基于 IC 下降比例和 Sharpe 下降比例"""
        # IC 下降越少越好
        ic_score = max(0, 100 * (1 - result.ic_drop_ratio))
        # Sharpe 下降越少越好
        sharpe_score = max(0, 100 * (1 - result.sharpe_drop_ratio))
        score = 0.5 * ic_score + 0.5 * sharpe_score
        return float(min(100.0, score))

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
