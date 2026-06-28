"""
模块 5: Signal Ranker

截面排序，保留 TopK / BottomK / TopBottomK。
按 confidence 排序（此时 score 还未计算），排序后写入 signal.metadata["rank_position"]。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .signal import Signal, SignalDirection, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.ranker")


class Ranker(ABC):
    """排序器抽象基类"""

    name: str = "base"

    @abstractmethod
    def rank(self, signal_set: SignalSet) -> SignalSet:
        ...

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name}


class NoRanker(Ranker):
    """不排序 — 透传"""

    name = "none"

    def rank(self, signal_set: SignalSet) -> SignalSet:
        for i, s in enumerate(signal_set.signals):
            s.metadata["rank_position"] = i
        return signal_set


class TopKRanker(Ranker):
    """取 confidence 最高的 K 个 LONG（其余 NEUTRAL）"""

    name = "topk"

    def __init__(self, k: int = 50) -> None:
        self.k = int(k)

    def rank(self, signal_set: SignalSet) -> SignalSet:
        longs = [s for s in signal_set.signals if s.direction == SignalDirection.LONG]
        # 按 confidence 降序
        longs_sorted = sorted(longs, key=lambda s: s.confidence, reverse=True)
        keep_ids = set(id(s) for s in longs_sorted[: self.k])

        result: List[Signal] = []
        rank_pos = 0
        for s in signal_set.signals:
            if s.direction == SignalDirection.LONG and id(s) not in keep_ids:
                # 降级为 NEUTRAL
                s.direction = SignalDirection.NEUTRAL
                s.metadata["rank_position"] = -1
                s.metadata["rank_demoted"] = True
            elif s.direction == SignalDirection.LONG:
                s.metadata["rank_position"] = rank_pos
                rank_pos += 1
            else:
                s.metadata["rank_position"] = -1
            result.append(s)

        new_set = SignalSet(
            signals=result,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata["ranker_k"] = self.k
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "k": self.k}


class BottomKRanker(Ranker):
    """取 confidence 最低的 K 个 SHORT（其余 NEUTRAL）"""

    name = "bottomk"

    def __init__(self, k: int = 50) -> None:
        self.k = int(k)

    def rank(self, signal_set: SignalSet) -> SignalSet:
        shorts = [s for s in signal_set.signals if s.direction == SignalDirection.SHORT]
        shorts_sorted = sorted(shorts, key=lambda s: s.confidence)  # 升序
        keep_ids = set(id(s) for s in shorts_sorted[: self.k])

        result: List[Signal] = []
        rank_pos = 0
        for s in signal_set.signals:
            if s.direction == SignalDirection.SHORT and id(s) not in keep_ids:
                s.direction = SignalDirection.NEUTRAL
                s.metadata["rank_position"] = -1
                s.metadata["rank_demoted"] = True
            elif s.direction == SignalDirection.SHORT:
                s.metadata["rank_position"] = rank_pos
                rank_pos += 1
            else:
                s.metadata["rank_position"] = -1
            result.append(s)

        new_set = SignalSet(
            signals=result,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata["ranker_k"] = self.k
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "k": self.k}


class TopBottomKRanker(Ranker):
    """同时取 TopK 多 + BottomK 空"""

    name = "topbottomk"

    def __init__(self, k_long: int = 50, k_short: int = 50) -> None:
        self.k_long = int(k_long)
        self.k_short = int(k_short)

    def rank(self, signal_set: SignalSet) -> SignalSet:
        longs = [s for s in signal_set.signals if s.direction == SignalDirection.LONG]
        shorts = [s for s in signal_set.signals if s.direction == SignalDirection.SHORT]
        longs_keep = set(id(s) for s in sorted(longs, key=lambda x: x.confidence, reverse=True)[: self.k_long])
        shorts_keep = set(id(s) for s in sorted(shorts, key=lambda x: x.confidence)[: self.k_short])

        result: List[Signal] = []
        lpos = spos = 0
        for s in signal_set.signals:
            if s.direction == SignalDirection.LONG:
                if id(s) in longs_keep:
                    s.metadata["rank_position"] = lpos
                    lpos += 1
                else:
                    s.direction = SignalDirection.NEUTRAL
                    s.metadata["rank_position"] = -1
                    s.metadata["rank_demoted"] = True
            elif s.direction == SignalDirection.SHORT:
                if id(s) in shorts_keep:
                    s.metadata["rank_position"] = spos
                    spos += 1
                else:
                    s.direction = SignalDirection.NEUTRAL
                    s.metadata["rank_position"] = -1
                    s.metadata["rank_demoted"] = True
            else:
                s.metadata["rank_position"] = -1
            result.append(s)

        new_set = SignalSet(
            signals=result,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata["ranker_k_long"] = self.k_long
        new_set.metadata["ranker_k_short"] = self.k_short
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "k_long": self.k_long, "k_short": self.k_short}


# ---- 工厂 ----

_RANKERS = {
    "none": NoRanker,
    "topk": TopKRanker,
    "bottomk": BottomKRanker,
    "topbottomk": TopBottomKRanker,
}


def get_ranker(method: str = "none", **params) -> Ranker:
    cls = _RANKERS.get(method.lower(), NoRanker)
    import inspect
    sig = inspect.signature(cls.__init__)
    valid = {k: v for k, v in params.items() if k in sig.parameters}
    return cls(**valid)
