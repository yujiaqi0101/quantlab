"""
模块 2: Prediction Calibrator

校准概率，使 confidence 更可靠。
支持 Temperature Scaling / Platt Scaling / Isotonic Regression / NoCalibration。

校准器可选，默认 NoCalibration（透传）。
校准器的 fit 需要历史数据，在 pipeline 运行前可调用 fit，否则用默认参数。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np

from .signal import Prediction

logger = logging.getLogger("quantlab.ml.signal_engine.calibrator")


class Calibrator(ABC):
    """校准器抽象基类"""

    @abstractmethod
    def calibrate(self, prediction: Prediction) -> Prediction:
        """校准单个 Prediction，返回新的 Prediction（不修改原对象）"""
        ...

    def calibrate_batch(self, predictions: list) -> list:
        return [self.calibrate(p) for p in predictions]

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> "Calibrator":
        """用历史数据拟合校准参数（默认无操作）"""
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.__class__.__name__}


class NoCalibration(Calibrator):
    """透传 — 不校准"""

    def calibrate(self, prediction: Prediction) -> Prediction:
        return prediction


class TemperatureScaling(Calibrator):
    """Temperature Scaling — 单参数 T 缩放 logits"""

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = float(temperature)

    def calibrate(self, prediction: Prediction) -> Prediction:
        if self.temperature == 1.0 or prediction.probability in (0.0, 1.0):
            return prediction
        # 把 probability 当作 sigmoid 输出，反推 logit，除以 T 再 sigmoid
        p = max(1e-7, min(1 - 1e-7, prediction.probability))
        logit = float(np.log(p / (1 - p)))
        new_prob = float(1.0 / (1.0 + np.exp(-logit / self.temperature)))
        meta = dict(prediction.metadata)
        meta["raw_probability"] = prediction.probability
        meta["calibrator"] = "temperature"
        meta["temperature"] = self.temperature
        return Prediction(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            value=prediction.value,
            probability=new_prob,
            model_type=prediction.model_type,
            metadata=meta,
        )

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> "TemperatureScaling":
        """简单网格搜索最优 T（基于 NLL）"""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        # 把 y_pred clip 到 (1e-7, 1-1e-7)
        y_pred = np.clip(y_pred, 1e-7, 1 - 1e-7)
        best_t, best_nll = 1.0, float("inf")
        for t in np.linspace(0.1, 5.0, 50):
            logits = np.log(y_pred / (1 - y_pred))
            probs = 1.0 / (1.0 + np.exp(-logits / t))
            probs = np.clip(probs, 1e-7, 1 - 1e-7)
            nll = -np.mean(y_true * np.log(probs) + (1 - y_true) * np.log(1 - probs))
            if nll < best_nll:
                best_nll, best_t = nll, float(t)
        self.temperature = best_t
        logger.info(f"TemperatureScaling fit: T={self.temperature:.3f}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"method": "temperature", "temperature": self.temperature}


class PlattScaling(Calibrator):
    """Platt Scaling — logistic 回归校准: P(y=1) = sigmoid(a*x + b)"""

    def __init__(self, a: float = 1.0, b: float = 0.0) -> None:
        self.a = float(a)
        self.b = float(b)

    def calibrate(self, prediction: Prediction) -> Prediction:
        new_prob = float(1.0 / (1.0 + np.exp(-(self.a * prediction.probability + self.b))))
        meta = dict(prediction.metadata)
        meta["raw_probability"] = prediction.probability
        meta["calibrator"] = "platt"
        return Prediction(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            value=prediction.value,
            probability=new_prob,
            model_type=prediction.model_type,
            metadata=meta,
        )

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> "PlattScaling":
        """简单线性回归拟合 Platt 参数"""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        y_pred = np.clip(y_pred, 1e-7, 1 - 1e-7)
        # 用 logit 变换后线性回归
        logits = np.log(y_pred / (1 - y_pred))
        if len(logits) > 1 and np.std(logits) > 1e-8:
            # 最小二乘: y_true = sigmoid(a*logit + b)
            # 简化: 用均值匹配
            target_logit = np.log(np.clip(y_true.mean(), 1e-7, 1 - 1e-7) / (1 - np.clip(y_true.mean(), 1e-7, 1 - 1e-7)))
            pred_logit_mean = logits.mean()
            if abs(pred_logit_mean) > 1e-8:
                self.a = target_logit / pred_logit_mean
            self.b = 0.0
        logger.info(f"PlattScaling fit: a={self.a:.3f}, b={self.b:.3f}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"method": "platt", "a": self.a, "b": self.b}


class IsotonicRegression(Calibrator):
    """Isotonic Regression — 非参数单调校准"""

    def __init__(self) -> None:
        self._fitted = False
        self._pairs: list = []  # [(input_prob, output_prob), ...]

    def calibrate(self, prediction: Prediction) -> Prediction:
        if not self._fitted or not self._pairs:
            return prediction
        # 线性插值
        p = max(1e-7, min(1 - 1e-7, prediction.probability))
        xs = [x for x, _ in self._pairs]
        ys = [y for _, y in self._pairs]
        new_prob = float(np.interp(p, xs, ys))
        meta = dict(prediction.metadata)
        meta["raw_probability"] = prediction.probability
        meta["calibrator"] = "isotonic"
        return Prediction(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            value=prediction.value,
            probability=new_prob,
            model_type=prediction.model_type,
            metadata=meta,
        )

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> "IsotonicRegression":
        """用 sklearn 的 IsotonicRegression（如果可用）"""
        try:
            from sklearn.isotonic import IsotonicRegression as SKIsotonic
            y_true = np.asarray(y_true, dtype=float)
            y_pred = np.asarray(y_pred, dtype=float)
            # 按 y_pred 排序
            order = np.argsort(y_pred)
            xs = y_pred[order]
            ys = y_true[order]
            model = SKIsotonic(out_of_bounds="clip")
            model.fit(xs, ys)
            # 保存插值点
            self._pairs = list(zip(model.X_thresholds_, model.y_thresholds_))
            self._fitted = True
            logger.info(f"IsotonicRegression fit: {len(self._pairs)} thresholds")
        except ImportError:
            logger.warning("sklearn not available, IsotonicRegression acts as NoCalibration")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"method": "isotonic", "fitted": self._fitted}


# ---- 工厂 ----

_CALIBRATORS = {
    "temperature": TemperatureScaling,
    "platt": PlattScaling,
    "isotonic": IsotonicRegression,
    "none": NoCalibration,
}


def get_calibrator(method: str = "none", **params) -> Calibrator:
    """获取校准器实例"""
    cls = _CALIBRATORS.get(method.lower(), NoCalibration)
    try:
        return cls(**params)
    except TypeError:
        return cls()
