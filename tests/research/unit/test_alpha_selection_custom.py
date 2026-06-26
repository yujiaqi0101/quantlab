"""
Alpha / Selection / Custom 节点单元测试
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research import ExecutionContext, ResearchFrame
from quantlab.research.builtin import (
    Alpha014Node,
    CustomNode,
    LambdaNode,
    LiquidityFilterNode,
    UniverseFilterNode,
)


def _make_ohlcv_panel(n: int = 30, symbols=("BTC", "ETH")) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rows = []
    for dt in dates:
        for sym in symbols:
            close = 100.0 + np.random.randn() * 5
            rows.append(
                {
                    "datetime": dt,
                    "symbol": sym,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000.0 + np.random.rand() * 500,
                }
            )
    return pd.DataFrame(rows).set_index(["datetime", "symbol"])


def _make_ctx(frame: pd.DataFrame = None) -> ExecutionContext:
    ctx = ExecutionContext()
    if frame is not None:
        ctx.set("frame", ResearchFrame.from_panel(frame))
    return ctx


@pytest.fixture
def ohlcv_panel() -> pd.DataFrame:
    return _make_ohlcv_panel()


class TestAlphaNode:
    def test_alpha014_compute(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        node = Alpha014Node()
        rf = node.compute(ctx)
        assert "alpha014" in rf.data.columns
        assert len(rf) == len(ohlcv_panel)

    def test_alpha014_manifest(self):
        node = Alpha014Node()
        m = node.manifest()
        assert m.category.value == "alpha"
        assert m.id == "alpha014"

    def test_alpha014_fingerprint_stable(self):
        assert Alpha014Node().fingerprint() == Alpha014Node().fingerprint()


class TestSelectionNodes:
    def test_universe_filter_keep_all(self, ohlcv_panel):
        """所有 volume >= 1000，min=500 应全部保留。"""
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = UniverseFilterNode(min_volume=500).compute(ctx)
        assert len(rf) == len(ohlcv_panel)

    def test_universe_filter_strict(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = UniverseFilterNode(min_volume=1500).compute(ctx)
        assert len(rf) < len(ohlcv_panel)

    def test_liquidity_filter(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = LiquidityFilterNode(window=5, min_avg_volume=500).compute(ctx)
        assert rf.name == "liquid"

    def test_missing_volume_raises(self, ohlcv_panel):
        df = ohlcv_panel.drop(columns=["volume"])
        ctx = _make_ctx(frame=df)
        with pytest.raises(ValueError, match="volume"):
            UniverseFilterNode().compute(ctx)


class TestCustomNodes:
    def test_custom_subclass(self, ohlcv_panel):
        class DoubleCloseNode(CustomNode):
            id = "double_close"

            def compute_func(self, frame, ctx):
                return frame.data[["close"]] * 2

        ctx = _make_ctx(frame=ohlcv_panel)
        rf = DoubleCloseNode().compute(ctx)
        assert "close" in rf.data.columns
        # 值翻倍
        assert (rf.data["close"] == ohlcv_panel["close"] * 2).all()

    def test_lambda_node(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        node = LambdaNode(func=lambda frame, ctx: frame.data[["close"]])
        rf = node.compute(ctx)
        assert "close" in rf.data.columns

    def test_custom_base_not_implemented(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        with pytest.raises(NotImplementedError):
            CustomNode().compute(ctx)
