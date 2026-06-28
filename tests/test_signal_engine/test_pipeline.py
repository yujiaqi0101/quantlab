"""
Signal Engine Pipeline 端到端集成测试

验证完整流水线：Prediction → Calibrator → Generator → Filter → Ranker → Scorer → Allocator → SignalSet
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from quantlab.ml.signal_engine import (
    Prediction, Signal, SignalDirection,
    PipelineConfig, SignalPipeline, run_pipeline,
    PredictionAdapter,
)


class TestPipelineBasics:
    """基础 pipeline 测试"""

    def test_minimal_pipeline(self):
        """最小 pipeline：默认配置，3 个 predictions"""
        preds = [
            Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.85, model_type="lightgbm"),
            Prediction(symbol="ETH", datetime="2026-01-01", value=0.03, probability=0.72, model_type="lightgbm"),
            Prediction(symbol="SOL", datetime="2026-01-01", value=-0.01, probability=0.45, model_type="lightgbm"),
        ]
        result = run_pipeline(preds)
        assert len(result.signals) == 3
        assert result.summary["total"] == 3
        # BTC value=0.05 > threshold=0.02 → LONG
        btc = result.by_symbol("BTC")
        assert btc.direction == SignalDirection.LONG
        # SOL value=-0.01, use_short=False → NEUTRAL
        sol = result.by_symbol("SOL")
        assert sol.direction == SignalDirection.NEUTRAL

    def test_pipeline_with_score_and_weight(self):
        """验证 score 和 weight 被填充"""
        preds = [
            Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9),
            Prediction(symbol="ETH", datetime="2026-01-01", value=0.04, probability=0.8),
        ]
        result = run_pipeline(preds)
        for s in result.signals:
            if s.direction == SignalDirection.LONG:
                assert s.score > 0  # LONG 正分
                assert s.suggested_weight > 0  # 有权重
                assert s.holding_period > 0  # 有持仓期

    def test_pipeline_with_trace(self):
        """验证 explain_trace 被写入"""
        preds = [Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9)]
        result = run_pipeline(preds)
        sig = result.signals[0]
        trace = sig.metadata.get("explain_trace", [])
        assert len(trace) >= 3  # 至少 generator/scorer/allocator 三步


class TestPipelineConfigurations:
    """不同配置组合测试"""

    def test_pipeline_with_short(self):
        """开启做空"""
        config = PipelineConfig(
            generator={"method": "threshold", "long_threshold": 0.02, "short_threshold": -0.02, "use_short": True},
        )
        preds = [
            Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9),
            Prediction(symbol="SOL", datetime="2026-01-01", value=-0.05, probability=0.3),
        ]
        result = run_pipeline(preds, config)
        assert result.by_symbol("BTC").direction == SignalDirection.LONG
        assert result.by_symbol("SOL").direction == SignalDirection.SHORT

    def test_pipeline_with_topk_ranker(self):
        """TopK 排序器"""
        config = PipelineConfig(
            generator={"method": "regression", "use_short": False},
            ranker={"method": "topk", "k": 2},
        )
        preds = [
            Prediction(symbol=f"S{i}", datetime="2026-01-01", value=0.01 * i, probability=0.1 * i)
            for i in range(1, 6)
        ]
        result = run_pipeline(preds, config)
        longs = result.longs()
        assert len(longs) == 2  # 只保留 2 个

    def test_pipeline_with_blacklist_filter(self):
        """黑名单过滤"""
        config = PipelineConfig(
            generator={"method": "regression", "use_short": False},
            filters=[{"method": "blacklist", "blacklist": ["S3"]}],
        )
        preds = [
            Prediction(symbol=f"S{i}", datetime="2026-01-01", value=0.05, probability=0.8)
            for i in range(1, 6)
        ]
        result = run_pipeline(preds, config)
        assert result.by_symbol("S3") is None  # 被过滤
        assert result.by_symbol("S1") is not None

    def test_pipeline_with_kelly_allocator(self):
        """Kelly 分配器"""
        config = PipelineConfig(
            generator={"method": "regression", "use_short": False},
            allocator={"method": "kelly", "max_weight": 0.2},
        )
        preds = [
            Prediction(symbol="BTC", datetime="2026-01-01", value=0.1, probability=0.9),
            Prediction(symbol="ETH", datetime="2026-01-01", value=0.08, probability=0.8),
        ]
        result = run_pipeline(preds, config)
        for s in result.longs():
            assert s.suggested_weight <= 0.2 + 1e-6  # 不超过 max_weight

    def test_pipeline_with_classification_generator(self):
        """分类生成器"""
        config = PipelineConfig(
            generator={"method": "classification", "use_short": True},
        )
        preds = [
            Prediction(symbol="BTC", datetime="2026-01-01", value=2, probability=0.9),  # Up → LONG
            Prediction(symbol="ETH", datetime="2026-01-01", value=0, probability=0.1),  # Down → SHORT
            Prediction(symbol="SOL", datetime="2026-01-01", value=1, probability=0.5),  # Neutral
        ]
        result = run_pipeline(preds, config)
        assert result.by_symbol("BTC").direction == SignalDirection.LONG
        assert result.by_symbol("ETH").direction == SignalDirection.SHORT
        assert result.by_symbol("SOL").direction == SignalDirection.NEUTRAL


class TestPipelineIntegration:
    """完整集成场景"""

    def test_full_pipeline_10_predictions(self):
        """10 个 predictions 端到端"""
        preds = [
            PredictionAdapter().adapt_regression(
                symbol=f"SYM{i}",
                datetime="2026-01-01",
                y_pred=0.06 - i * 0.012,  # 从 +0.06 到 -0.048
                model_type="lightgbm",
            )
            for i in range(10)
        ]
        config = PipelineConfig(
            generator={"method": "threshold", "long_threshold": 0.02, "short_threshold": -0.02, "use_short": True},
            ranker={"method": "topbottomk", "k_long": 3, "k_short": 2},
            scorer={"method": "rank"},
            allocator={"method": "equal_weight"},
            holding_period=7,
        )
        result = run_pipeline(preds, config)

        assert len(result.signals) == 10
        assert result.summary["n_long"] == 3  # TopK 3
        assert result.summary["n_short"] == 2  # BottomK 2
        # 所有权重总和 ≤ 1
        total_w = sum(s.suggested_weight for s in result.signals)
        assert total_w <= 1.0 + 1e-6
        # holding_period 已设置
        for s in result.signals:
            assert s.holding_period == 7

    def test_pipeline_save_to_registry(self, tmp_path):
        """测试保存到 registry（用临时 DB）"""
        # 临时覆盖 DB 路径
        from quantlab.ml.signal_engine import storage as storage_mod
        from quantlab.ml.signal_engine import signal_registry as reg_mod

        tmp_db = str(tmp_path / "test_signals.db")
        original_store = storage_mod._store
        original_reg = reg_mod._registry

        storage_mod._store = None
        reg_mod._registry = None
        storage_mod.DEFAULT_DB_PATH = tmp_db

        try:
            config = PipelineConfig(
                generator={"method": "regression", "use_short": False},
                save_to_registry=True,
                model_version="test_v1",
            )
            preds = [
                Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9),
                Prediction(symbol="ETH", datetime="2026-01-01", value=0.04, probability=0.8),
            ]
            result = run_pipeline(preds, config)
            assert result.metadata.get("saved_to_registry") is True

            # 验证可从 registry 查到
            from quantlab.ml.signal_engine import get_signal_registry
            reg = get_signal_registry()
            all_signals = reg.list_signals(limit=10)
            assert len(all_signals) == 2
        finally:
            # 恢复
            storage_mod._store = original_store
            reg_mod._registry = original_reg

    def test_pipeline_error_resilience(self):
        """错误 resilience：某步失败不中断"""
        config = PipelineConfig(
            generator={"method": "unknown_method"},  # 无效方法，会触发工厂兜底
        )
        preds = [Prediction(symbol="BTC", datetime="2026-01-01", value=0.05, probability=0.9)]
        result = run_pipeline(preds, config)
        # 不应该崩溃
        assert len(result.signals) >= 0
