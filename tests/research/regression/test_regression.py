"""
回归测试 — 旧 Feature/Label 体系 vs 新 NodeRegistry 输出一致性

验证新 Research OS 通过 Adapter 输出与旧体系一致。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from quantlab.research import ResearchFrame, ResearchGraph
from quantlab.research.builtin.data import CloseNode
from quantlab.research.builtin.label import FutureReturnNode
from quantlab.research.context import FrameStore
from quantlab.research.executor import ResearchExecutor


def _make_panel(n_periods=100):
    """模拟面板。"""
    rng = np.random.default_rng(11)
    dates = pd.date_range("2024-01-01", periods=n_periods, freq="h")
    records = []
    for sym in ["BTCUSDT", "ETHUSDT"]:
        prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n_periods)))
        for t in range(n_periods):
            records.append({
                "datetime": dates[t], "symbol": sym,
                "open": prices[t], "high": prices[t], "low": prices[t],
                "close": prices[t], "volume": 1000.0, "vwap": prices[t],
            })
    return pd.DataFrame(records).set_index(["datetime", "symbol"])


class TestFutureReturnConsistency:
    """FutureReturnNode 输出应与直接计算一致。"""

    def test_future_return_matches_direct_calculation(self):
        """FutureReturnNode 输出 == 直接 shift(-horizon)/close - 1。"""
        panel = _make_panel(100)
        horizon = 5

        # 直接计算（旧体系方式）
        close = panel["close"].unstack()
        expected = (close.shift(-horizon) / close - 1).stack().dropna()
        expected.name = "future_return"

        # 通过 Graph 计算（新体系）
        frame = ResearchFrame.from_panel(panel)
        g = ResearchGraph(name="regression")
        g.add_node(CloseNode(id="close"))
        g.add_node(FutureReturnNode(id="future_return", horizon=horizon))
        g.add_edge("close", "close", "future_return", "close")

        store = FrameStore()
        store.set("frame", frame)
        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)

        assert not result.errors
        actual = result.outputs["future_return"].data["future_return"].dropna()

        # 对齐比较
        common = expected.index.intersection(actual.index)
        assert len(common) > 0
        np.testing.assert_allclose(
            actual.loc[common].values,
            expected.loc[common].values,
            rtol=1e-6,
            err_msg="FutureReturnNode output diverges from direct calculation",
        )
        print(f"\n[REG] {len(common)} rows consistent (rtol=1e-6)")


class TestCloseNodeConsistency:
    """CloseNode 输出应等于原始 close 列。"""

    def test_close_node_equals_raw_column(self):
        """CloseNode 输出 == panel['close']。"""
        panel = _make_panel(50)

        frame = ResearchFrame.from_panel(panel)
        g = ResearchGraph(name="close_regression")
        g.add_node(CloseNode(id="close"))

        store = FrameStore()
        store.set("frame", frame)
        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)

        assert not result.errors
        actual = result.outputs["close"].data["close"]
        expected = panel["close"]

        pd.testing.assert_series_equal(
            actual.sort_index(),
            expected.sort_index(),
            check_names=False,
            check_dtype=False,
        )
        print(f"\n[REG] CloseNode {len(actual)} rows == raw column")
