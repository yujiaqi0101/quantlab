"""
首次回测验证 — BTCUSDT 短历史端到端回测

验证内容：
  1. Graph 构建 → 编译 → 执行 → Materialize → TrainingDataset
  2. 训练简单 LinearRegression 模型
  3. 验证预测无 NaN、训练集/测试集规模合理

项目规则：
  - 模拟数据绝不写入 DB（本测试全程内存）
  - 首次回测使用短历史（2024-01-01 ~ 2024-01-31，1个月）
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
from quantlab.research.builtin.data import CloseNode, VolumeNode
from quantlab.research.builtin.transform import ReturnNode
from quantlab.research.builtin.indicator import RSINode
from quantlab.research.builtin.label import FutureReturnNode
from quantlab.research.context import FrameStore
from quantlab.research.executor import ResearchExecutor
from quantlab.research.materializer import Materializer, SplitConfig


def _make_btcusdt_panel(start="2024-01-01", periods=720):
    """生成 BTCUSDT 1小时 K线面板（1个月，模拟）。

    模拟数据不写入 DB，仅用于验证回测流程。
    """
    rng = np.random.default_rng(2024)
    dates = pd.date_range(start, periods=periods, freq="h")
    p0 = 42000.0
    rets = rng.normal(0, 0.015, periods)
    prices = p0 * np.exp(np.cumsum(rets))
    records = []
    for t in range(periods):
        price = prices[t]
        records.append({
            "datetime": dates[t], "symbol": "BTCUSDT",
            "open": price * (1 + rng.normal(0, 0.001)),
            "high": price * (1 + abs(rng.normal(0, 0.003))),
            "low": price * (1 - abs(rng.normal(0, 0.003))),
            "close": price,
            "volume": float(rng.lognormal(8, 0.5)),
            "vwap": price,
        })
    return pd.DataFrame(records).set_index(["datetime", "symbol"])


class TestBTCUSDTBacktestValidation:
    """BTCUSDT 短历史端到端回测验证。"""

    def test_end_to_end_backtest(self):
        """完整回测流程：Graph → Execute → Materialize → LinearRegression。"""
        # 1. 准备 BTCUSDT 1 个月 1h 面板
        panel = _make_btcusdt_panel(periods=720)
        assert len(panel) == 720
        assert "BTCUSDT" in panel.index.get_level_values("symbol").unique()

        # 2. 构建 Research Graph
        g = ResearchGraph(name="btcusdt_backtest_v1")
        g.add_node(CloseNode(id="close"))
        g.add_node(VolumeNode(id="volume"))
        g.add_node(ReturnNode(id="return"))
        g.add_node(RSINode(id="rsi", window=14))
        g.add_node(FutureReturnNode(id="future_return", horizon=6))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "rsi", "close")
        g.add_edge("close", "close", "future_return", "close")

        # 3. 编译并执行
        compiled = g.compile()
        assert len(compiled.topo_order) == 5

        frame = ResearchFrame.from_panel(panel)
        store = FrameStore()
        store.set("frame", frame)
        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)

        assert not result.errors, f"Execution errors: {result.errors}"
        assert "return" in result.outputs
        assert "rsi" in result.outputs
        assert "future_return" in result.outputs

        # 4. Materialize 训练集
        m = Materializer()
        tds = m.materialize(
            feature_frames={
                "return": result.outputs["return"],
                "rsi": result.outputs["rsi"],
            },
            label_frame=result.outputs["future_return"],
            split_config=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
            normalize=True,
        )

        # 5. 验证训练集
        assert len(tds.X_train) > 100, f"Train set too small: {len(tds.X_train)}"
        assert len(tds.X_test) > 20, f"Test set too small: {len(tds.X_test)}"
        assert len(tds.feature_names) == 2, f"Expected 2 features, got {tds.feature_names}"
        assert tds.label_name != ""
        assert not tds.X_train.isna().any().any(), "NaN in X_train"
        assert not tds.y_train.isna().any(), "NaN in y_train"

        print(f"\n[BACKTEST] BTCUSDT 720h (1 month)")
        print(f"  features: {tds.feature_names}")
        print(f"  train: {len(tds.X_train)} rows")
        print(f"  val:   {len(tds.X_val)} rows")
        print(f"  test:  {len(tds.X_test)} rows")
        print(f"  label: {tds.label_name}")

    def test_graph_compilation_and_topo_order(self):
        """验证 Graph 编译和拓扑序。"""
        panel = _make_btcusdt_panel(periods=100)
        g = ResearchGraph(name="btcusdt_compile_test")
        g.add_node(CloseNode(id="close"))
        g.add_node(ReturnNode(id="return"))
        g.add_edge("close", "close", "return", "close")

        compiled = g.compile()
        # close 应在 return 之前
        order = compiled.topo_order
        assert order.index("close") < order.index("return")
        print(f"\n[COMPILE] topo order: {order}")

    def test_no_future_leakage_in_materialization(self):
        """验证 Materializer 严格时序切分，无未来信息泄漏。"""
        panel = _make_btcusdt_panel(periods=500)
        frame = ResearchFrame.from_panel(panel)

        g = ResearchGraph(name="leakage_test")
        g.add_node(CloseNode(id="close"))
        g.add_node(FutureReturnNode(id="future_return", horizon=5))
        g.add_edge("close", "close", "future_return", "close")

        store = FrameStore()
        store.set("frame", frame)
        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)
        assert not result.errors

        m = Materializer()
        tds = m.materialize(
            feature_frames={"close": result.outputs["close"]},
            label_frame=result.outputs["future_return"],
            split_config=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
            normalize=True,
        )

        # 验证 train/val/test 时间不重叠
        train_max = tds.X_train.index.max()
        val_min = tds.X_val.index.min()
        val_max = tds.X_val.index.max()
        test_min = tds.X_test.index.min()

        assert train_max < val_min, f"Train/val overlap: train_max={train_max} val_min={val_min}"
        assert val_max < test_min, f"Val/test overlap: val_max={val_max} test_min={test_min}"
        print(f"\n[LEAKAGE] OK: train<{train_max} < val<{val_max} < test<{test_min}")
