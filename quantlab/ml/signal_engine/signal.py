"""
Signal Engine 核心数据对象

定义整个 QuantLab 统一使用的 Signal / SignalSet / Prediction 对象。
严格遵循 docs/signal engine.md 第 628-653 行的 Signal 定义。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalDirection(str, Enum):
    """信号方向"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class Prediction:
    """
    统一预测对象 — 所有模型输出经 PredictionAdapter 后转为此格式。

    不同模型输出差异很大（回归值/分类标签/概率/序列/动作），
    PredictionAdapter 负责把它们全部转成 Prediction。
    """
    symbol: str
    datetime: str              # ISO 格式
    value: float               # 原始预测值 (回归: 收益率; 分类: 类别标签)
    probability: float = 0.0   # 概率/置信度 [0, 1]
    model_type: str = ""       # lightgbm / xgboost / linear / transformer / rl
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "datetime": self.datetime,
            "value": self.value,
            "probability": self.probability,
            "model_type": self.model_type,
            "metadata": self.metadata,
        }


@dataclass
class Signal:
    """
    统一信号对象 — 整个 QuantLab 通用。

    字段严格遵循 docs/signal engine.md 第 628-653 行定义。
    metadata 含溯源信息: prediction_value, raw_probability, filter_passed,
    rank_position, scorer_method, allocator_method, explain_trace。
    """
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    datetime: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    score: float = 0.0               # 统一评分 [-100, 100]
    confidence: float = 0.0          # 校准后置信度 [0, 1]
    expected_return: float = 0.0     # 期望收益
    suggested_weight: float = 0.0    # 建议权重 [0, 1]
    holding_period: int = 0          # 建议持仓天数
    source_model: str = ""           # 来源模型版本
    generator: str = ""              # 生成器名称 (threshold/quantile/...)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "datetime": self.datetime,
            "direction": self.direction.value if isinstance(self.direction, SignalDirection) else str(self.direction),
            "score": self.score,
            "confidence": self.confidence,
            "expected_return": self.expected_return,
            "suggested_weight": self.suggested_weight,
            "holding_period": self.holding_period,
            "source_model": self.source_model,
            "generator": self.generator,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Signal":
        direction = d.get("direction", "NEUTRAL")
        if isinstance(direction, str):
            try:
                direction = SignalDirection(direction)
            except ValueError:
                direction = SignalDirection.NEUTRAL
        return cls(
            signal_id=d.get("signal_id", str(uuid.uuid4())),
            symbol=d.get("symbol", ""),
            datetime=d.get("datetime", ""),
            direction=direction,
            score=float(d.get("score", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            expected_return=float(d.get("expected_return", 0.0)),
            suggested_weight=float(d.get("suggested_weight", 0.0)),
            holding_period=int(d.get("holding_period", 0)),
            source_model=d.get("source_model", ""),
            generator=d.get("generator", ""),
            metadata=d.get("metadata", {}) or {},
        )

    def add_trace(self, step: str, state: Dict[str, Any]) -> None:
        """追加溯源信息到 metadata['explain_trace']"""
        trace = self.metadata.setdefault("explain_trace", [])
        trace.append({"step": step, "state": state})


@dataclass
class SignalSet:
    """
    Signal Engine 最终输出 — Strategy Builder 直接读取。

    一个 SignalSet 包含同一时刻多个 symbol 的信号集合。
    """
    set_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signals: List[Signal] = field(default_factory=list)
    pipeline_config: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def by_symbol(self, symbol: str) -> Optional[Signal]:
        for s in self.signals:
            if s.symbol == symbol:
                return s
        return None

    def longs(self) -> List[Signal]:
        return [s for s in self.signals if s.direction == SignalDirection.LONG]

    def shorts(self) -> List[Signal]:
        return [s for s in self.signals if s.direction == SignalDirection.SHORT]

    def neutrals(self) -> List[Signal]:
        return [s for s in self.signals if s.direction == SignalDirection.NEUTRAL]

    def compute_summary(self) -> Dict[str, Any]:
        """计算统计摘要"""
        longs = self.longs()
        shorts = self.shorts()
        scores = [s.score for s in self.signals if s.direction != SignalDirection.NEUTRAL]
        self.summary = {
            "total": len(self.signals),
            "n_long": len(longs),
            "n_short": len(shorts),
            "n_neutral": len(self.signals) - len(longs) - len(shorts),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "avg_confidence": sum(s.confidence for s in self.signals) / len(self.signals) if self.signals else 0.0,
            "total_weight": sum(s.suggested_weight for s in self.signals),
        }
        return self.summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "set_id": self.set_id,
            "generated_at": self.generated_at,
            "signals": [s.to_dict() for s in self.signals],
            "pipeline_config": self.pipeline_config,
            "summary": self.summary,
            "metadata": self.metadata,
        }
