"""
Builtin 节点单元测试

覆盖 6 类节点：DATA / TRANSFORM / INDICATOR / AGGREGATION / RANKING / LABEL
重点验证：
  1. 单节点 compute 正确性
  2. 链式节点端口名匹配 (CloseNode -> ReturnNode -> ...)
  3. 参数化 (window/period/horizon)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research import ExecutionContext, ResearchFrame
from quantlab.research.builtin import (
    ATRNode,
    CloseNode,
    CrossSectionRankNode,
    DiffNode,
    DirectionNode,
    EMANode,
    FutureReturnNode,
    HighNode,
    LogNode,
    MACDNode,
    NormalizeNode,
    PercentileNode,
    ReturnNode,
    RollingMaxNode,
    RollingMeanNode,
    RollingMinNode,
    RollingStdNode,
    RSINode,
    SMANode,
    VolumeNode,
    VWAPNode,
    ZScoreNode,
)


# ---------------------------------------------------------------------- #
# Fixtures
# ---------------------------------------------------------------------- #
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
    df = pd.DataFrame(rows).set_index(["datetime", "symbol"])
    return df


def _make_ctx(frame: pd.DataFrame = None, close: ResearchFrame = None) -> ExecutionContext:
    ctx = ExecutionContext()
    if frame is not None:
        ctx.set("frame", ResearchFrame.from_panel(frame))
    if close is not None:
        ctx.set("close", close)
    return ctx


@pytest.fixture
def ohlcv_panel() -> pd.DataFrame:
    return _make_ohlcv_panel()


@pytest.fixture
def close_frame(ohlcv_panel) -> ResearchFrame:
    ctx = _make_ctx(frame=ohlcv_panel)
    return CloseNode().compute(ctx)


# ---------------------------------------------------------------------- #
# DATA
# ---------------------------------------------------------------------- #
class TestDataNodes:
    def test_close_node(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = CloseNode().compute(ctx)
        assert rf.name == "close"
        assert "close" in rf.data.columns
        assert len(rf) == 60  # 30 * 2

    def test_high_node(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = HighNode().compute(ctx)
        assert "high" in rf.data.columns

    def test_volume_node(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = VolumeNode().compute(ctx)
        assert "volume" in rf.data.columns

    def test_vwap_node_approx(self, ohlcv_panel):
        """无 vwap 列时用 (H+L+C)/3 近似。"""
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = VWAPNode().compute(ctx)
        assert "vwap" in rf.data.columns

    def test_missing_column_raises(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        # 自定义一个不存在的列节点
        class FakeNode(CloseNode):
            column = "nonexistent"
        with pytest.raises(ValueError, match="not in frame columns"):
            FakeNode().compute(ctx)


# ---------------------------------------------------------------------- #
# TRANSFORM
# ---------------------------------------------------------------------- #
class TestTransformNodes:
    def test_return_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = ReturnNode(period=1).compute(ctx)
        assert "return" in rf.data.columns
        # 每个标的第一期 pct_change 为 NaN
        for sym in ("BTC", "ETH"):
            first = rf.data.xs(sym, level="symbol").iloc[0]["return"]
            assert pd.isna(first)

    def test_diff_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = DiffNode(period=1).compute(ctx)
        assert "diff" in rf.data.columns

    def test_log_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = LogNode().compute(ctx)
        assert "log" in rf.data.columns
        # log(100) ≈ 4.6
        vals = rf.data["log"].dropna()
        assert vals.between(4.0, 5.5).all()

    def test_zscore_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = ZScoreNode(window=5).compute(ctx)
        assert "zscore" in rf.data.columns

    def test_normalize_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = NormalizeNode(window=20).compute(ctx)
        assert "normalize" in rf.data.columns

    def test_chain_close_to_return(self, ohlcv_panel):
        """链式：CloseNode -> ReturnNode 端口名匹配。"""
        ctx = _make_ctx(frame=ohlcv_panel)
        close_rf = CloseNode().compute(ctx)
        ctx.set("close", close_rf)
        ret_rf = ReturnNode(period=1).compute(ctx)
        assert len(ret_rf) == len(close_rf)


# ---------------------------------------------------------------------- #
# INDICATOR
# ---------------------------------------------------------------------- #
class TestIndicatorNodes:
    def test_rsi_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = RSINode(window=14).compute(ctx)
        assert "rsi" in rf.data.columns
        # RSI 填充 50，应在 0-100
        vals = rf.data["rsi"]
        assert vals.between(0, 100).all()

    def test_sma_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = SMANode(window=5).compute(ctx)
        assert "sma" in rf.data.columns
        # 前 4 期为 NaN
        for sym in ("BTC", "ETH"):
            sub = rf.data.xs(sym, level="symbol")
            assert sub["sma"].iloc[:4].isna().all()
            assert sub["sma"].iloc[5:].notna().all()

    def test_ema_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = EMANode(window=12).compute(ctx)
        assert "ema" in rf.data.columns

    def test_macd_node(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = MACDNode(fast=12, slow=26, signal=9).compute(ctx)
        assert "macd" in rf.data.columns

    def test_atr_node(self, ohlcv_panel):
        ctx = _make_ctx(frame=ohlcv_panel)
        rf = ATRNode(window=14).compute(ctx)
        assert "atr" in rf.data.columns
        assert (rf.data["atr"].dropna() >= 0).all()


# ---------------------------------------------------------------------- #
# AGGREGATION
# ---------------------------------------------------------------------- #
class TestAggregationNodes:
    def test_rolling_mean(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = RollingMeanNode(window=5).compute(ctx)
        assert "rolling_mean" in rf.data.columns

    def test_rolling_std(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = RollingStdNode(window=5).compute(ctx)
        assert (rf.data["rolling_std"].dropna() >= 0).all()

    def test_rolling_max(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = RollingMaxNode(window=5).compute(ctx)
        assert "rolling_max" in rf.data.columns

    def test_rolling_min(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = RollingMinNode(window=5).compute(ctx)
        assert "rolling_min" in rf.data.columns


# ---------------------------------------------------------------------- #
# RANKING
# ---------------------------------------------------------------------- #
class TestRankingNodes:
    def test_cs_rank(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = CrossSectionRankNode().compute(ctx)
        assert "cs_rank" in rf.data.columns
        # 2 个标的，pct rank 应为 0.5 和 1.0
        vals = rf.data["cs_rank"].dropna().unique()
        assert set(vals).issubset({0.5, 1.0})

    def test_percentile(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = PercentileNode().compute(ctx)
        assert "percentile" in rf.data.columns


# ---------------------------------------------------------------------- #
# LABEL
# ---------------------------------------------------------------------- #
class TestLabelNodes:
    def test_future_return(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = FutureReturnNode(horizon=5).compute(ctx)
        assert "future_return" in rf.data.columns
        # 最后 5 期 NaN (shift -5)
        for sym in ("BTC", "ETH"):
            sub = rf.data.xs(sym, level="symbol")
            assert sub["future_return"].iloc[-5:].isna().all()
            assert sub["future_return"].iloc[:-5].notna().all()

    def test_direction(self, close_frame):
        ctx = _make_ctx(close=close_frame)
        rf = DirectionNode(horizon=5).compute(ctx)
        assert "direction" in rf.data.columns
        vals = set(rf.data["direction"].dropna().unique())
        assert vals.issubset({-1.0, 0.0, 1.0})


# ---------------------------------------------------------------------- #
# Manifest & 参数化
# ---------------------------------------------------------------------- #
class TestNodeManifest:
    def test_rsi_manifest(self):
        node = RSINode(window=21)
        m = node.manifest()
        assert m.id == "rsi"
        assert m.category.value == "indicator"
        assert m.params["window"] == 21

    def test_fingerprint_differs_by_window(self):
        assert RSINode(window=14).fingerprint() != RSINode(window=21).fingerprint()

    def test_full_chain_fingerprints(self):
        """链式节点指纹独立。"""
        nodes = [CloseNode(), ReturnNode(period=1), RSINode(window=14)]
        fps = [n.fingerprint() for n in nodes]
        assert len(set(fps)) == 3  # 三个不同指纹
