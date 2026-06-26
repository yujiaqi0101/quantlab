"""
集成测试 — 端到端训练闭环 / 增量一致性 / Cache 失效

使用 BTC/ETH/SOL 风格模拟面板（不写入 DB），验证完整流程：
  Graph 构建 → 编译 → 执行 → Materialize → 训练集
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
from quantlab.research.builtin.transform import ReturnNode
from quantlab.research.builtin.label import FutureReturnNode
from quantlab.research.context import FrameStore
from quantlab.research.executor import ResearchExecutor
from quantlab.research.materializer import Materializer, SplitConfig


def _make_crypto_panel(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"), n_periods=300):
    """生成 BTC/ETH/SOL 风格面板（模拟，不写入 DB）。"""
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", periods=n_periods, freq="h")
    records = []
    base_prices = {"BTCUSDT": 40000, "ETHUSDT": 2000, "SOLUSDT": 100}
    for sym in symbols:
        p0 = base_prices[sym]
        rets = rng.normal(0, 0.02, n_periods)
        prices = p0 * np.exp(np.cumsum(rets))
        for t in range(n_periods):
            price = prices[t]
            records.append({
                "datetime": dates[t], "symbol": sym,
                "open": price * 0.99, "high": price * 1.01,
                "low": price * 0.98, "close": price,
                "volume": float(rng.integers(10000, 100000)),
                "vwap": price,
            })
    return pd.DataFrame(records).set_index(["datetime", "symbol"])


class TestEndToEndTrainingPipeline:
    """端到端训练闭环。"""

    def test_full_pipeline_produces_training_set(self):
        """完整流程：Graph → Execute → Materialize → TrainingDataset。"""
        panel = _make_crypto_panel()
        frame = ResearchFrame.from_panel(panel)

        # 构建 Graph
        g = ResearchGraph(name="e2e_alpha")
        g.add_node(CloseNode(id="close"))
        g.add_node(ReturnNode(id="return"))
        g.add_node(FutureReturnNode(id="future_return", horizon=5))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "future_return", "close")

        # 执行
        store = FrameStore()
        store.set("frame", frame)
        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)
        assert not result.errors
        assert "return" in result.outputs
        assert "future_return" in result.outputs

        # Materialize
        m = Materializer()
        tds = m.materialize(
            feature_frames={"return": result.outputs["return"]},
            label_frame=result.outputs["future_return"],
            split_config=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
            normalize=True,
        )
        assert len(tds.X_train) > 0
        assert len(tds.X_test) > 0
        assert len(tds.y_train) == len(tds.X_train)
        print(f"\n[E2E] train={len(tds.X_train)} val={len(tds.X_val)} test={len(tds.X_test)}")


class TestIncrementalConsistency:
    """增量一致性：append 数据后结果应与全量一致。"""

    def test_append_preserves_historical_results(self):
        """append 新数据后，历史部分结果不变。"""
        panel = _make_crypto_panel(n_periods=200)
        frame = ResearchFrame.from_panel(panel)

        g = ResearchGraph(name="inc_consistency")
        g.add_node(CloseNode(id="close"))
        g.add_node(ReturnNode(id="return"))
        g.add_edge("close", "close", "return", "close")

        executor = ResearchExecutor()

        # 全量
        store1 = FrameStore()
        store1.set("frame", frame)
        r1 = executor.execute(g, initial_store=store1)
        assert not r1.errors
        ret1 = r1.outputs["return"].data

        # append 50 行
        new_records = []
        last_dt = panel.index.get_level_values("datetime").max()
        new_dates = pd.date_range(last_dt + pd.Timedelta(hours=1), periods=50, freq="h")
        for sym in panel.index.get_level_values("symbol").unique():
            for dt in new_dates:
                new_records.append({
                    "datetime": dt, "symbol": sym,
                    "open": 100, "high": 101, "low": 99, "close": 100,
                    "volume": 5000.0, "vwap": 100,
                })
        panel2 = pd.concat([panel, pd.DataFrame(new_records).set_index(["datetime", "symbol"])])

        store2 = FrameStore()
        store2.set("frame", ResearchFrame.from_panel(panel2))
        r2 = executor.execute(g, initial_store=store2)
        assert not r2.errors
        ret2 = r2.outputs["return"].data

        # 历史部分（前 200 周期）应一致
        common_idx = ret1.index.intersection(ret2.index)
        assert len(common_idx) > 0
        pd.testing.assert_frame_equal(
            ret1.loc[common_idx].sort_index(),
            ret2.loc[common_idx].sort_index(),
            check_dtype=False,
        )
        print(f"\n[INC] historical {len(common_idx)} rows consistent, new rows: {len(ret2) - len(ret1)}")


class TestCacheInvalidation:
    """Cache 命中与失效。"""

    def test_different_input_different_output(self):
        """不同输入产生不同输出（无错误缓存）。"""
        panel1 = _make_crypto_panel(n_periods=100)
        panel2 = _make_crypto_panel(n_periods=100)
        # 修改 panel2 的 close
        panel2 = panel2.copy()
        panel2["close"] = panel2["close"] * 2

        g = ResearchGraph(name="cache_test")
        g.add_node(CloseNode(id="close"))

        executor = ResearchExecutor()

        store1 = FrameStore()
        store1.set("frame", ResearchFrame.from_panel(panel1))
        r1 = executor.execute(g, initial_store=store1)

        store2 = FrameStore()
        store2.set("frame", ResearchFrame.from_panel(panel2))
        r2 = executor.execute(g, initial_store=store2)

        assert not r1.errors and not r2.errors
        # 不同输入应产生不同输出
        v1 = r1.outputs["close"].data["close"].mean()
        v2 = r2.outputs["close"].data["close"].mean()
        assert abs(v2 - 2 * v1) < 0.01, f"Expected v2≈2*v1, got v1={v1} v2={v2}"
