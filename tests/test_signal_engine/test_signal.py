"""
Signal Engine 核心对象测试

覆盖：Prediction / Signal / SignalSet 的创建、序列化、方法。
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from quantlab.ml.signal_engine import (
    Prediction, Signal, SignalDirection, SignalSet,
)


class TestPrediction:
    def test_create_prediction(self):
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.8)
        assert p.symbol == "BTC"
        assert p.value == 0.05
        assert p.probability == 0.8

    def test_to_dict(self):
        p = Prediction(symbol="ETH", datetime="2026-01-01", value=0.03, probability=0.7, model_type="lightgbm")
        d = p.to_dict()
        assert d["symbol"] == "ETH"
        assert d["value"] == 0.03
        assert d["model_type"] == "lightgbm"


class TestSignal:
    def test_create_signal(self):
        s = Signal(
            symbol="BTC",
            datetime="2026-01-01",
            direction=SignalDirection.LONG,
            score=72.0,
            confidence=0.85,
            expected_return=0.05,
        )
        assert s.symbol == "BTC"
        assert s.direction == SignalDirection.LONG
        assert s.score == 72.0
        assert s.signal_id  # 自动生成 UUID

    def test_to_dict_and_from_dict(self):
        s = Signal(
            symbol="ETH",
            datetime="2026-01-01",
            direction=SignalDirection.SHORT,
            score=-50.0,
            confidence=0.6,
            expected_return=-0.02,
            suggested_weight=0.1,
            holding_period=5,
            source_model="lightgbm_v1",
            generator="threshold",
        )
        d = s.to_dict()
        assert d["direction"] == "SHORT"
        assert d["score"] == -50.0

        s2 = Signal.from_dict(d)
        assert s2.symbol == "ETH"
        assert s2.direction == SignalDirection.SHORT
        assert s2.score == -50.0

    def test_add_trace(self):
        s = Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG)
        s.add_trace("generator", {"direction": "LONG"})
        s.add_trace("scorer", {"score": 72.0})
        trace = s.metadata["explain_trace"]
        assert len(trace) == 2
        assert trace[0]["step"] == "generator"
        assert trace[1]["state"]["score"] == 72.0


class TestSignalSet:
    def test_create_and_query(self):
        signals = [
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.9),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.SHORT, confidence=0.7),
            Signal(symbol="SOL", datetime="2026-01-01", direction=SignalDirection.NEUTRAL, confidence=0.5),
        ]
        ss = SignalSet(signals=signals)
        assert len(ss.signals) == 3
        assert len(ss.longs()) == 1
        assert len(ss.shorts()) == 1
        assert len(ss.neutrals()) == 1
        assert ss.by_symbol("BTC").direction == SignalDirection.LONG
        assert ss.by_symbol("XXX") is None

    def test_compute_summary(self):
        signals = [
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, score=80, confidence=0.9, suggested_weight=0.5),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.SHORT, score=-60, confidence=0.7, suggested_weight=0.3),
        ]
        ss = SignalSet(signals=signals)
        summary = ss.compute_summary()
        assert summary["total"] == 2
        assert summary["n_long"] == 1
        assert summary["n_short"] == 1
        assert summary["avg_score"] == 10.0  # (80 + -60) / 2
        assert summary["total_weight"] == 0.8

    def test_to_dict(self):
        ss = SignalSet(signals=[Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG)])
        d = ss.to_dict()
        assert "signals" in d
        assert "set_id" in d
        assert len(d["signals"]) == 1
