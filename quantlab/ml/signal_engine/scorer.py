"""
模块 6: Signal Scorer

统一评分到 [-100, 100]。
评分基于 confidence 和 expected_return 组合，方向决定正负号。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import numpy as np

from .signal import Signal, SignalDirection, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.scorer")


class Scorer(ABC):
    """评分器抽象基类"""

    name: str = "base"

    @abstractmethod
    def score(self, signal_set: SignalSet) -> SignalSet:
        ...

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name}


class TanhScorer(Scorer):
    """tanh 映射到 [-100, 100]
    基于 expected_return，LONG 为正，SHORT 为负
    """

    name = "tanh"

    def __init__(self, scale: float = 50.0) -> None:
        self.scale = float(scale)

    def score(self, signal_set: SignalSet) -> SignalSet:
        for s in signal_set.signals:
            if s.direction == SignalDirection.NEUTRAL:
                s.score = 0.0
                continue
            # 用 confidence 和 expected_return 组合
            raw = s.confidence * (1 if s.direction == SignalDirection.LONG else -1)
            s.score = float(100.0 * np.tanh(raw * self.scale / 100.0))
            s.metadata["scorer_method"] = self.name
            s.metadata["scorer_raw"] = raw
        return signal_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "scale": self.scale}


class RankScorer(Scorer):
    """排名映射 — rank/(n-1)*200-100"""

    name = "rank"

    def score(self, signal_set: SignalSet) -> SignalSet:
        active = [s for s in signal_set.signals if s.direction != SignalDirection.NEUTRAL]
        if len(active) <= 1:
            for s in active:
                s.score = 0.0 if s.direction == SignalDirection.NEUTRAL else (
                    100.0 if s.direction == SignalDirection.LONG else -100.0
                )
            return signal_set
        # 按 confidence 排序
        order = sorted(range(len(active)), key=lambda i: active[i].confidence, reverse=True)
        n = len(active)
        for rank, idx in enumerate(order):
            s = active[idx]
            if s.direction == SignalDirection.NEUTRAL:
                s.score = 0.0
            else:
                # rank=0 (最高) → 100, rank=n-1 (最低) → -100
                base = 100.0 - (rank / max(1, n - 1)) * 200.0
                s.score = float(base) if s.direction == SignalDirection.LONG else float(-base)
            s.metadata["scorer_method"] = self.name
            s.metadata["scorer_rank"] = rank
        return signal_set


class ZScoreScorer(Scorer):
    """Z-Score 标准化后映射"""

    name = "zscore"

    def score(self, signal_set: SignalSet) -> SignalSet:
        active = [s for s in signal_set.signals if s.direction != SignalDirection.NEUTRAL]
        if not active:
            return signal_set
        confs = np.array([s.confidence for s in active])
        mean, std = float(confs.mean()), float(confs.std())
        if std < 1e-8:
            std = 1.0
        for s in active:
            z = (s.confidence - mean) / std
            # clip 到 [-3, 3] 再映射到 [-100, 100]
            z = max(-3.0, min(3.0, z))
            s.score = float(z / 3.0 * 100.0) * (1 if s.direction == SignalDirection.LONG else -1)
            s.metadata["scorer_method"] = self.name
            s.metadata["scorer_z"] = z
        return signal_set


class QuantileScorer(Scorer):
    """截面分位映射"""

    name = "quantile"

    def score(self, signal_set: SignalSet) -> SignalSet:
        active = [s for s in signal_set.signals if s.direction != SignalDirection.NEUTRAL]
        if not active:
            return signal_set
        confs = np.array([s.confidence for s in active])
        for s in active:
            # 该 signal 的 confidence 在所有 active 中的分位
            q = float((confs <= s.confidence).sum() / len(confs))
            s.score = float((q * 2 - 1) * 100) * (1 if s.direction == SignalDirection.LONG else -1)
            s.metadata["scorer_method"] = self.name
            s.metadata["scorer_quantile"] = q
        return signal_set


# ---- 工厂 ----

_SCORERS = {
    "tanh": TanhScorer,
    "rank": RankScorer,
    "zscore": ZScoreScorer,
    "quantile": QuantileScorer,
}


def get_scorer(method: str = "tanh", **params) -> Scorer:
    cls = _SCORERS.get(method.lower(), TanhScorer)
    import inspect
    sig = inspect.signature(cls.__init__)
    valid = {k: v for k, v in params.items() if k in sig.parameters}
    return cls(**valid)
