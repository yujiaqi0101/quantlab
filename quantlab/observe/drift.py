"""
Drift Detection — 数据漂移检测

监控训练数据 vs 当前数据的差异。

例如：
  RSI 分布发生变化 → Data Drift → 报警

未来可扩展：
  - Model Drift（模型预测分布变化）
  - Concept Drift（特征-标签关系变化）

检测方法：
  1) PSI (Population Stability Index)  — 适合分桶特征
  2) KS 检验                           — 适合连续分布
  3) 均值/标准差差异                    — 简单快速

用法：
    from quantlab.observe.drift import DriftDetector, DriftConfig

    detector = DriftDetector()

    # 注册基线（训练数据）
    detector.set_baseline("rsi_14", training_rsi_values)

    # 检测当前数据
    result = detector.detect("rsi_14", current_rsi_values)
    print(result.to_dict())

    # 批量检测
    results = detector.detect_all({
        "rsi_14": current_rsi,
        "momentum": current_momentum,
    })
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("quantlab.observe.drift")


# ------------------------------------------------------------------
# DriftResult
# ------------------------------------------------------------------

@dataclass
class DriftResult:
    """漂移检测结果"""
    feature_name: str
    method: str                       # "psi" / "ks" / "mean_std"
    score: float = 0.0                # 漂移分数
    threshold: float = 0.0
    drifted: bool = False             # 是否漂移
    baseline_mean: float = 0.0
    current_mean: float = 0.0
    baseline_std: float = 0.0
    current_std: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "method": self.method,
            "score": self.score,
            "threshold": self.threshold,
            "drifted": self.drifted,
            "baseline_mean": self.baseline_mean,
            "current_mean": self.current_mean,
            "baseline_std": self.baseline_std,
            "current_std": self.current_std,
            "details": self.details,
        }


# ------------------------------------------------------------------
# DriftConfig
# ------------------------------------------------------------------

@dataclass
class DriftConfig:
    """漂移检测配置"""
    method: str = "psi"               # psi / ks / mean_std
    psi_threshold: float = 0.2        # PSI > 0.2 视为漂移
    ks_pvalue_threshold: float = 0.05  # p < 0.05 视为漂移
    mean_std_threshold: float = 0.5    # 标准化均值差 > 0.5 视为漂移
    n_bins: int = 10                  # PSI 分桶数


# ------------------------------------------------------------------
# DriftDetector
# ------------------------------------------------------------------

class DriftDetector:
    """
    数据漂移检测器

    用法：
        detector = DriftDetector()
        detector.set_baseline("rsi", training_values)
        result = detector.detect("rsi", current_values)
    """

    def __init__(self, config: Optional[DriftConfig] = None) -> None:
        self.config = config or DriftConfig()
        # 基线数据：feature_name → np.ndarray
        self._baselines: Dict[str, np.ndarray] = {}

    def set_baseline(
        self,
        feature_name: str,
        values: Any,
    ) -> None:
        """设置基线数据（训练数据）"""
        arr = np.asarray(values, dtype=float)
        # 去除 NaN
        arr = arr[~np.isnan(arr)]
        self._baselines[feature_name] = arr
        logger.info(
            f"DriftDetector: baseline '{feature_name}' set "
            f"(n={len(arr)}, mean={np.mean(arr):.4f})"
        )

    def detect(
        self,
        feature_name: str,
        current_values: Any,
        method: Optional[str] = None,
    ) -> DriftResult:
        """
        检测漂移

        参数：
          feature_name     特征名
          current_values   当前数据
          method           检测方法（默认用 config.method）
        """
        if feature_name not in self._baselines:
            return DriftResult(
                feature_name=feature_name,
                method="none",
                details={"error": "baseline not set"},
            )

        baseline = self._baselines[feature_name]
        current = np.asarray(current_values, dtype=float)
        current = current[~np.isnan(current)]

        if len(current) == 0:
            return DriftResult(
                feature_name=feature_name,
                method="none",
                details={"error": "current values empty"},
            )

        m = method or self.config.method

        if m == "psi":
            return self._detect_psi(feature_name, baseline, current)
        elif m == "ks":
            return self._detect_ks(feature_name, baseline, current)
        elif m == "mean_std":
            return self._detect_mean_std(feature_name, baseline, current)
        else:
            return DriftResult(
                feature_name=feature_name,
                method=m,
                details={"error": f"unknown method: {m}"},
            )

    def detect_all(
        self,
        current_data: Dict[str, Any],
        method: Optional[str] = None,
    ) -> List[DriftResult]:
        """批量检测所有特征"""
        results: List[DriftResult] = []
        for name, values in current_data.items():
            if name in self._baselines:
                results.append(self.detect(name, values, method=method))
        return results

    # ------------------------------------------------------------------
    # PSI (Population Stability Index)
    # ------------------------------------------------------------------

    def _detect_psi(
        self,
        feature_name: str,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> DriftResult:
        """
        PSI 检测

        PSI < 0.1   无漂移
        PSI 0.1-0.2 轻微漂移
        PSI > 0.2   显著漂移
        """
        n_bins = self.config.n_bins

        # 用 baseline 的分位数作为分桶边界
        bins = np.linspace(
            np.min(baseline),
            np.max(baseline),
            n_bins + 1,
        )
        # 防止边界相等
        bins = np.unique(bins)
        if len(bins) < 3:
            return DriftResult(
                feature_name=feature_name,
                method="psi",
                details={"error": "insufficient unique values"},
            )

        # 分桶
        baseline_counts, _ = np.histogram(baseline, bins=bins)
        current_counts, _ = np.histogram(current, bins=bins)

        # 比例（加 1 平滑避免除 0）
        baseline_pct = (baseline_counts + 1) / (len(baseline) + n_bins)
        current_pct = (current_counts + 1) / (len(current) + n_bins)

        # PSI = Σ (current% - baseline%) * ln(current% / baseline%)
        psi = float(np.sum(
            (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
        ))

        threshold = self.config.psi_threshold
        drifted = psi > threshold

        return DriftResult(
            feature_name=feature_name,
            method="psi",
            score=psi,
            threshold=threshold,
            drifted=drifted,
            baseline_mean=float(np.mean(baseline)),
            current_mean=float(np.mean(current)),
            baseline_std=float(np.std(baseline)),
            current_std=float(np.std(current)),
            details={
                "n_bins": len(bins) - 1,
                "baseline_n": len(baseline),
                "current_n": len(current),
            },
        )

    # ------------------------------------------------------------------
    # KS 检验
    # ------------------------------------------------------------------

    def _detect_ks(
        self,
        feature_name: str,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> DriftResult:
        """KS 检验（Kolmogorov-Smirnov）"""
        try:
            from scipy import stats
        except ImportError:
            return DriftResult(
                feature_name=feature_name,
                method="ks",
                details={"error": "scipy not installed"},
            )

        stat, pvalue = stats.ks_2samp(baseline, current)
        threshold = self.config.ks_pvalue_threshold
        drifted = pvalue < threshold

        return DriftResult(
            feature_name=feature_name,
            method="ks",
            score=float(stat),
            threshold=threshold,
            drifted=drifted,
            baseline_mean=float(np.mean(baseline)),
            current_mean=float(np.mean(current)),
            baseline_std=float(np.std(baseline)),
            current_std=float(np.std(current)),
            details={
                "statistic": float(stat),
                "pvalue": float(pvalue),
            },
        )

    # ------------------------------------------------------------------
    # 均值/标准差差异
    # ------------------------------------------------------------------

    def _detect_mean_std(
        self,
        feature_name: str,
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> DriftResult:
        """均值/标准差差异检测"""
        b_mean = float(np.mean(baseline))
        c_mean = float(np.mean(current))
        b_std = float(np.std(baseline))
        c_std = float(np.std(baseline))

        # 标准化均值差
        pooled_std = (b_std + c_std) / 2 if (b_std + c_std) > 0 else 1.0
        score = abs(c_mean - b_mean) / pooled_std

        threshold = self.config.mean_std_threshold
        drifted = score > threshold

        return DriftResult(
            feature_name=feature_name,
            method="mean_std",
            score=score,
            threshold=threshold,
            drifted=drifted,
            baseline_mean=b_mean,
            current_mean=c_mean,
            baseline_std=b_std,
            current_std=c_std,
            details={
                "mean_diff": c_mean - b_mean,
                "std_diff": c_std - b_std,
            },
        )

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def list_baselines(self) -> List[str]:
        """列出所有基线"""
        return list(self._baselines.keys())

    def remove_baseline(self, feature_name: str) -> bool:
        if feature_name in self._baselines:
            del self._baselines[feature_name]
            return True
        return False

    def clear_baselines(self) -> None:
        self._baselines.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "n_baselines": len(self._baselines),
            "baselines": list(self._baselines.keys()),
            "method": self.config.method,
        }
