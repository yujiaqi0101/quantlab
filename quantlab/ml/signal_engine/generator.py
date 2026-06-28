"""
模块 3: Signal Generator（核心）

把 Prediction 转成有 direction 的 Signal。
支持 Threshold / Quantile / Ranking / Probability / Classification / Regression 六种生成器。
全部插件化（策略模式 + 工厂）。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np

from .signal import Prediction, Signal, SignalDirection

logger = logging.getLogger("quantlab.ml.signal_engine.generator")


class Generator(ABC):
    """信号生成器抽象基类"""

    name: str = "base"

    @abstractmethod
    def generate(self, prediction: Prediction) -> Signal:
        """把单个 Prediction 转成 Signal"""
        ...

    def generate_batch(self, predictions: List[Prediction]) -> List[Signal]:
        """批量生成"""
        return [self.generate(p) for p in predictions]

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name}


class ThresholdGenerator(Generator):
    """阈值生成器 — 回归模型"""

    name = "threshold"

    def __init__(
        self,
        long_threshold: float = 0.02,
        short_threshold: float = -0.02,
        use_short: bool = False,
    ) -> None:
        self.long_threshold = float(long_threshold)
        self.short_threshold = float(short_threshold)
        self.use_short = bool(use_short)

    def generate(self, prediction: Prediction) -> Signal:
        value = prediction.value
        if value > self.long_threshold:
            direction = SignalDirection.LONG
        elif self.use_short and value < self.short_threshold:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,  # 由 Scorer 填充
            confidence=prediction.probability,
            expected_return=value,
            suggested_weight=0.0,  # 由 Allocator 填充
            holding_period=0,  # 由 Allocator 填充
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": value,
                "raw_probability": prediction.probability,
                "long_threshold": self.long_threshold,
                "short_threshold": self.short_threshold,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
        }


class QuantileGenerator(Generator):
    """分位数生成器 — 截面分位（需要批量计算）"""

    name = "quantile"

    def __init__(
        self,
        long_quantile: float = 0.8,
        short_quantile: float = 0.2,
        use_short: bool = False,
    ) -> None:
        self.long_quantile = float(long_quantile)
        self.short_quantile = float(short_quantile)
        self.use_short = bool(use_short)

    def generate(self, prediction: Prediction) -> Signal:
        """单条生成时退化为阈值模式（用 0 作阈值）"""
        direction = SignalDirection.LONG if prediction.value > 0 else (
            SignalDirection.SHORT if self.use_short and prediction.value < 0 else SignalDirection.NEUTRAL
        )
        return self._build_signal(prediction, direction)

    def generate_batch(self, predictions: List[Prediction]) -> List[Signal]:
        """批量生成：按截面分位数决定方向"""
        if len(predictions) == 0:
            return []
        values = np.array([p.value for p in predictions])
        long_cut = float(np.quantile(values, self.long_quantile)) if len(values) > 1 else 0.0
        short_cut = float(np.quantile(values, self.short_quantile)) if len(values) > 1 else 0.0

        signals: List[Signal] = []
        for p in predictions:
            if p.value >= long_cut:
                direction = SignalDirection.LONG
            elif self.use_short and p.value <= short_cut:
                direction = SignalDirection.SHORT
            else:
                direction = SignalDirection.NEUTRAL
            sig = self._build_signal(p, direction)
            sig.metadata["long_quantile_cut"] = long_cut
            sig.metadata["short_quantile_cut"] = short_cut
            signals.append(sig)
        return signals

    def _build_signal(self, prediction: Prediction, direction: SignalDirection) -> Signal:
        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,
            confidence=prediction.probability,
            expected_return=prediction.value,
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": prediction.value,
                "raw_probability": prediction.probability,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "long_quantile": self.long_quantile,
            "short_quantile": self.short_quantile,
            "use_short": self.use_short,
        }


class RankingGenerator(Generator):
    """排序生成器 — 截面排名（需要批量计算）"""

    name = "ranking"

    def __init__(self, top_pct: float = 0.2, bottom_pct: float = 0.2, use_short: bool = False) -> None:
        self.top_pct = float(top_pct)
        self.bottom_pct = float(bottom_pct)
        self.use_short = bool(use_short)

    def generate(self, prediction: Prediction) -> Signal:
        direction = SignalDirection.LONG if prediction.value > 0 else SignalDirection.NEUTRAL
        return self._build_signal(prediction, direction)

    def generate_batch(self, predictions: List[Prediction]) -> List[Signal]:
        if len(predictions) == 0:
            return []
        n = len(predictions)
        order = np.argsort([p.value for p in predictions])[::-1]  # 降序
        top_n = max(1, int(n * self.top_pct))
        bottom_n = max(1, int(n * self.bottom_pct))
        top_idx = set(order[:top_n].tolist())
        bottom_idx = set(order[-bottom_n:].tolist()) if self.use_short else set()

        signals: List[Signal] = []
        for i, p in enumerate(predictions):
            if i in top_idx:
                direction = SignalDirection.LONG
            elif i in bottom_idx:
                direction = SignalDirection.SHORT
            else:
                direction = SignalDirection.NEUTRAL
            sig = self._build_signal(p, direction)
            sig.metadata["rank"] = int(np.where(order == i)[0][0]) if i in order else -1
            signals.append(sig)
        return signals

    def _build_signal(self, prediction: Prediction, direction: SignalDirection) -> Signal:
        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,
            confidence=prediction.probability,
            expected_return=prediction.value,
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": prediction.value,
                "raw_probability": prediction.probability,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "top_pct": self.top_pct,
            "bottom_pct": self.bottom_pct,
            "use_short": self.use_short,
        }


class ProbabilityGenerator(Generator):
    """概率生成器 — 分类模型，按概率阈值"""

    name = "probability"

    def __init__(self, long_threshold: float = 0.6, short_threshold: float = 0.4) -> None:
        self.long_threshold = float(long_threshold)
        self.short_threshold = float(short_threshold)

    def generate(self, prediction: Prediction) -> Signal:
        prob = prediction.probability
        if prob >= self.long_threshold:
            direction = SignalDirection.LONG
        elif prob <= self.short_threshold:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,
            confidence=prob,
            expected_return=prediction.value,
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": prediction.value,
                "raw_probability": prediction.probability,
                "long_threshold": self.long_threshold,
                "short_threshold": self.short_threshold,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
        }


class ClassificationGenerator(Generator):
    """分类生成器 — 类别直转 (0=Down→SHORT, 1=Neutral→NEUTRAL, 2=Up→LONG)"""

    name = "classification"

    CLASS_TO_DIRECTION = {
        0: SignalDirection.SHORT,
        1: SignalDirection.NEUTRAL,
        2: SignalDirection.LONG,
    }

    def __init__(self, use_short: bool = True) -> None:
        self.use_short = bool(use_short)

    def generate(self, prediction: Prediction) -> Signal:
        cls = int(prediction.value) if prediction.value is not None else 1
        direction = self.CLASS_TO_DIRECTION.get(cls, SignalDirection.NEUTRAL)
        if direction == SignalDirection.SHORT and not self.use_short:
            direction = SignalDirection.NEUTRAL

        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,
            confidence=prediction.probability,
            expected_return=prediction.value,
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": prediction.value,
                "raw_probability": prediction.probability,
                "class": cls,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "use_short": self.use_short}


class RegressionGenerator(Generator):
    """回归生成器 — 连续值符号化"""

    name = "regression"

    def __init__(self, use_short: bool = False) -> None:
        self.use_short = bool(use_short)

    def generate(self, prediction: Prediction) -> Signal:
        if prediction.value > 0:
            direction = SignalDirection.LONG
        elif prediction.value < 0 and self.use_short:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        return Signal(
            symbol=prediction.symbol,
            datetime=prediction.datetime,
            direction=direction,
            score=0.0,
            confidence=prediction.probability,
            expected_return=prediction.value,
            source_model=prediction.model_type,
            generator=self.name,
            metadata={
                "prediction_value": prediction.value,
                "raw_probability": prediction.probability,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "use_short": self.use_short}


# ---- 工厂 ----

_GENERATORS = {
    "threshold": ThresholdGenerator,
    "quantile": QuantileGenerator,
    "ranking": RankingGenerator,
    "probability": ProbabilityGenerator,
    "classification": ClassificationGenerator,
    "regression": RegressionGenerator,
}


def get_generator(method: str = "threshold", **params) -> Generator:
    """获取生成器实例"""
    cls = _GENERATORS.get(method.lower(), ThresholdGenerator)
    # 过滤不匹配的参数
    import inspect
    sig = inspect.signature(cls.__init__)
    valid = {k: v for k, v in params.items() if k in sig.parameters}
    return cls(**valid)
