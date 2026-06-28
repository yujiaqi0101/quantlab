"""
Signal Engine 各模块单元测试

覆盖：PredictionAdapter / Calibrator / Generator / Filter / Ranker / Scorer / PositionAllocator / Templates / Explainability
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from quantlab.ml.signal_engine import (
    Prediction, Signal, SignalDirection, SignalSet,
    PredictionAdapter, get_calibrator, NoCalibration, TemperatureScaling,
    get_generator, ThresholdGenerator, QuantileGenerator, ClassificationGenerator,
    get_filter, BlacklistFilter, LiquidityFilter, build_filters, CompositeFilter,
    get_ranker, TopKRanker, NoRanker,
    get_scorer, TanhScorer, RankScorer,
    get_allocator, EqualWeightAllocator, KellyAllocator,
    get_template, list_templates,
    ExplainabilityEngine,
)


# ---------- Prediction Adapter ----------

class TestPredictionAdapter:
    def test_adapt_regression(self):
        p = PredictionAdapter().adapt_regression("BTC", "2026-01-01", 0.05, "lightgbm")
        assert p.symbol == "BTC"
        assert p.value == 0.05
        assert 0 < p.probability < 1

    def test_adapt_classifier(self):
        p = PredictionAdapter().adapt_classifier("BTC", "2026-01-01", 2, [0.1, 0.2, 0.7], "lightgbm")
        assert p.value == 2.0
        assert p.probability == 0.7
        assert p.metadata["class_label"] == "up"

    def test_adapt_proba(self):
        p = PredictionAdapter().adapt_proba("BTC", "2026-01-01", 0.85, "lightgbm")
        assert p.value == 0.85
        assert p.probability == 0.85

    def test_adapt_action(self):
        p = PredictionAdapter().adapt_action("BTC", "2026-01-01", 2, "rl")
        assert p.value == 2.0
        assert p.metadata["class_label"] == "up"

    def test_adapt_auto_regression(self):
        p = PredictionAdapter().adapt_auto("BTC", "2026-01-01", 0.05, "lightgbm")
        assert p.value == 0.05

    def test_adapt_auto_classifier(self):
        p = PredictionAdapter().adapt_auto("BTC", "2026-01-01", 2, "classifier", y_proba=[0.1, 0.2, 0.7])
        assert p.value == 2.0
        assert p.probability == 0.7


# ---------- Calibrator ----------

class TestCalibrator:
    def test_no_calibration(self):
        cal = NoCalibration()
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.8)
        assert cal.calibrate(p) is p  # 透传

    def test_temperature_scaling(self):
        cal = TemperatureScaling(temperature=2.0)
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9)
        p2 = cal.calibrate(p)
        assert p2.probability != p.probability  # 应该变化
        assert 0 < p2.probability < 1
        assert p2.metadata["calibrator"] == "temperature"

    def test_get_calibrator_factory(self):
        assert isinstance(get_calibrator("none"), NoCalibration)
        assert isinstance(get_calibrator("temperature"), TemperatureScaling)
        assert isinstance(get_calibrator("unknown"), NoCalibration)  # 兜底


# ---------- Generator ----------

class TestGenerator:
    def test_threshold_generator_long(self):
        gen = ThresholdGenerator(long_threshold=0.02, short_threshold=-0.02)
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.8)
        sig = gen.generate(p)
        assert sig.direction == SignalDirection.LONG
        assert sig.expected_return == 0.05
        assert sig.generator == "threshold"

    def test_threshold_generator_neutral(self):
        gen = ThresholdGenerator(long_threshold=0.02)
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=0.01, probability=0.5)
        sig = gen.generate(p)
        assert sig.direction == SignalDirection.NEUTRAL

    def test_threshold_generator_short(self):
        gen = ThresholdGenerator(long_threshold=0.02, short_threshold=-0.02, use_short=True)
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=-0.05, probability=0.3)
        sig = gen.generate(p)
        assert sig.direction == SignalDirection.SHORT

    def test_classification_generator(self):
        gen = ClassificationGenerator(use_short=True)
        p = Prediction(symbol="BTC", datetime="2026-01-01", value=2, probability=0.9)  # class 2 = Up
        sig = gen.generate(p)
        assert sig.direction == SignalDirection.LONG

    def test_quantile_generator_batch(self):
        gen = QuantileGenerator(long_quantile=0.8, short_quantile=0.2, use_short=True)
        preds = [
            Prediction(symbol=f"S{i}", datetime="2026-01-01", value=i * 0.01, probability=0.5)
            for i in range(10)
        ]
        signals = gen.generate_batch(preds)
        assert len(signals) == 10
        # 最高的两个应该 LONG
        longs = [s for s in signals if s.direction == SignalDirection.LONG]
        assert len(longs) >= 1

    def test_get_generator_factory(self):
        assert isinstance(get_generator("threshold"), ThresholdGenerator)
        assert isinstance(get_generator("quantile"), QuantileGenerator)


# ---------- Filter ----------

class TestFilter:
    def test_blacklist_filter(self):
        f = BlacklistFilter({"BAD"})
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG),
            Signal(symbol="BAD", datetime="2026-01-01", direction=SignalDirection.LONG),
        ])
        result = f.filter(ss)
        assert len(result.signals) == 1
        assert result.signals[0].symbol == "BTC"
        assert len(result.metadata["filtered_out"]) == 1

    def test_liquidity_filter_no_provider(self):
        f = LiquidityFilter(min_volume=1000)
        ss = SignalSet(signals=[Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG)])
        result = f.filter(ss)
        assert len(result.signals) == 1  # 无 provider 透传

    def test_liquidity_filter_with_provider(self):
        def provider(symbol, datetime):
            return {"volume": 1500, "amount": 10000} if symbol == "BTC" else {"volume": 0, "amount": 0}
        f = LiquidityFilter(min_volume=1000, market_data_provider=provider)
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.LONG),
        ])
        result = f.filter(ss)
        assert len(result.signals) == 1
        assert result.signals[0].symbol == "BTC"

    def test_composite_filter(self):
        cf = CompositeFilter([BlacklistFilter({"BAD"})])
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG),
            Signal(symbol="BAD", datetime="2026-01-01", direction=SignalDirection.LONG),
        ])
        result = cf.filter(ss)
        assert len(result.signals) == 1

    def test_build_filters(self):
        cf = build_filters([{"method": "blacklist", "blacklist": ["X"]}])
        assert len(cf.filters) == 1


# ---------- Ranker ----------

class TestRanker:
    def test_no_ranker(self):
        r = NoRanker()
        ss = SignalSet(signals=[Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG)])
        result = r.rank(ss)
        assert len(result.signals) == 1

    def test_topk_ranker(self):
        r = TopKRanker(k=2)
        signals = [
            Signal(symbol=f"S{i}", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.1 * i)
            for i in range(5)
        ]
        ss = SignalSet(signals=signals)
        result = r.rank(ss)
        # 保留 confidence 最高的 2 个 LONG
        longs = result.longs()
        assert len(longs) == 2
        # 其余降级为 NEUTRAL
        neutrals = result.neutrals()
        assert len(neutrals) == 3


# ---------- Scorer ----------

class TestScorer:
    def test_tanh_scorer(self):
        s = TanhScorer()
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.9),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.SHORT, confidence=0.8),
        ])
        s.score(ss)
        assert ss.signals[0].score > 0  # LONG 为正
        assert ss.signals[1].score < 0  # SHORT 为负

    def test_rank_scorer(self):
        s = RankScorer()
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.9),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.5),
        ])
        s.score(ss)
        # confidence 高的 score 也高
        assert ss.signals[0].score > ss.signals[1].score


# ---------- Position Allocator ----------

class TestAllocator:
    def test_equal_weight(self):
        a = EqualWeightAllocator(holding_period=5)
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG),
            Signal(symbol="ETH", datetime="2026-01-01", direction=SignalDirection.LONG),
        ])
        a.allocate(ss)
        assert ss.signals[0].suggested_weight == 0.5
        assert ss.signals[0].holding_period == 5

    def test_kelly_allocator(self):
        a = KellyAllocator(holding_period=3, max_weight=0.25)
        ss = SignalSet(signals=[
            Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, confidence=0.9, expected_return=0.1),
        ])
        a.allocate(ss)
        assert 0 < ss.signals[0].suggested_weight <= 0.25
        assert ss.signals[0].holding_period == 3

    def test_weight_normalization(self):
        """权重总和不超过 1.0"""
        a = EqualWeightAllocator()
        ss = SignalSet(signals=[
            Signal(symbol=f"S{i}", datetime="2026-01-01", direction=SignalDirection.LONG)
            for i in range(3)
        ])
        a.allocate(ss)
        total = sum(s.suggested_weight for s in ss.longs())
        assert total <= 1.0 + 1e-6


# ---------- Templates ----------

class TestTemplates:
    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) >= 8  # 至少 8 个内置模板

    def test_get_template(self):
        t = get_template("topk")
        assert t is not None
        assert t.name == "topk"
        assert "generator" in t.pipeline_config

    def test_get_template_not_found(self):
        assert get_template("nonexistent") is None


# ---------- Explainability ----------

class TestExplainability:
    def test_explain(self):
        sig = Signal(symbol="BTC", datetime="2026-01-01", direction=SignalDirection.LONG, score=72.0)
        sig.add_trace("generator", {"direction": "LONG"})
        sig.add_trace("scorer", {"score": 72.0})
        sig.metadata["prediction_value"] = 0.05
        sig.metadata["raw_probability"] = 0.85

        trace = ExplainabilityEngine().explain(sig)
        assert trace.after_generator == {"direction": "LONG"}
        assert trace.after_scorer == {"score": 72.0}
        assert trace.prediction["prediction_value"] == 0.05
        assert trace.final_signal["symbol"] == "BTC"
