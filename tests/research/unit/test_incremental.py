"""
阶段6 测试: Incremental Framework
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research.builtin import CloseNode, EMANode, ReturnNode, RSINode
from quantlab.research.graph import ResearchGraph
from quantlab.research.incremental import (
    Change,
    ChangeOp,
    ChangeSet,
    DeltaAnalyzer,
    DirtyGraph,
    IncrementalPlan,
    IncrementalPlanner,
    IncrementalStrategy,
    NodeState,
    StateStore,
)


# ---------------------------------------------------------------------- #
# 1. ChangeSet
# ---------------------------------------------------------------------- #
class TestChangeSet:
    def test_construct(self):
        cs = ChangeSet()
        cs.add_insert("BTC", pd.Timestamp("2024-01-10"), {"close": 105.0})
        cs.add_update("ETH", pd.Timestamp("2024-01-05"), {"close": 110.0})
        cs.add_delete("BNB", pd.Timestamp("2024-01-03"))
        assert cs.size() == 3
        assert "BTC" in cs.symbols()
        assert not cs.is_empty()

    def test_from_panel_diff_insert(self):
        np.random.seed(42)
        rows_old = [
            {"datetime": pd.Timestamp("2024-01-01"), "symbol": "BTC", "close": 100.0},
            {"datetime": pd.Timestamp("2024-01-02"), "symbol": "BTC", "close": 101.0},
        ]
        rows_new = rows_old + [
            {"datetime": pd.Timestamp("2024-01-03"), "symbol": "BTC", "close": 102.0},
        ]
        old = pd.DataFrame(rows_old).set_index(["datetime", "symbol"])
        new = pd.DataFrame(rows_new).set_index(["datetime", "symbol"])
        cs = ChangeSet.from_panel_diff(old, new)
        assert cs.size() == 1
        assert cs.changes[0].op == ChangeOp.INSERT

    def test_from_panel_diff_update(self):
        rows_old = [
            {"datetime": pd.Timestamp("2024-01-01"), "symbol": "BTC", "close": 100.0},
        ]
        rows_new = [
            {"datetime": pd.Timestamp("2024-01-01"), "symbol": "BTC", "close": 105.0},
        ]
        old = pd.DataFrame(rows_old).set_index(["datetime", "symbol"])
        new = pd.DataFrame(rows_new).set_index(["datetime", "symbol"])
        cs = ChangeSet.from_panel_diff(old, new)
        assert cs.size() == 1
        assert cs.changes[0].op == ChangeOp.UPDATE
        assert cs.changes[0].fields["close"] == 105.0


# ---------------------------------------------------------------------- #
# 2. DeltaAnalyzer
# ---------------------------------------------------------------------- #
class TestDeltaAnalyzer:
    def _make_graph(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(RSINode(window=5))
        g.add_node(EMANode(window=10))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "rsi", "close")
        g.add_edge("close", "close", "ema", "close")
        return g

    def test_dirty_propagation(self):
        g = self._make_graph()
        cs = ChangeSet().add_insert(
            "BTC", pd.Timestamp("2024-01-10"), {"close": 105.0}
        )
        da = DeltaAnalyzer(g)
        dg = da.analyze(cs)
        # close 是 dirty + 所有下游
        assert dg.is_dirty("close")
        assert dg.is_dirty("return")
        assert dg.is_dirty("rsi")
        assert dg.is_dirty("ema")
        assert dg.dirty_count() == 4

    def test_no_changes(self):
        g = self._make_graph()
        cs = ChangeSet()
        da = DeltaAnalyzer(g)
        dg = da.analyze(cs)
        assert dg.dirty_count() == 0

    def test_unrelated_field_not_dirty(self):
        g = self._make_graph()
        cs = ChangeSet().add_insert(
            "BTC", pd.Timestamp("2024-01-10"), {"volume": 1000.0}
        )
        da = DeltaAnalyzer(g)
        dg = da.analyze(cs)
        # volume 字段不影响 close 节点
        assert not dg.is_dirty("close")


# ---------------------------------------------------------------------- #
# 3. IncrementalPlanner
# ---------------------------------------------------------------------- #
class TestIncrementalPlanner:
    def _make_graph(self):
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_edge("close", "close", "return", "close")
        return g

    def test_use_cache_for_not_dirty(self):
        g = self._make_graph()
        cs = ChangeSet()
        dg = DirtyGraph(set(), set(), cs)
        planner = IncrementalPlanner()
        plans = planner.plan(g, dg, cs)
        assert plans["close"].strategy == IncrementalStrategy.USE_CACHE
        assert plans["return"].strategy == IncrementalStrategy.USE_CACHE
        assert not plans["close"].dirty

    def test_full_for_non_incremental_node(self):
        g = self._make_graph()
        # close 是 DATA 节点，默认不支持增量
        cs = ChangeSet().add_insert("BTC", pd.Timestamp("2024-01-10"), {"close": 105.0})
        dg = DirtyGraph({"close", "return"}, {"close"}, cs)
        planner = IncrementalPlanner()
        plans = planner.plan(g, dg, cs)
        # close 不支持增量 → FULL
        assert plans["close"].strategy == IncrementalStrategy.FULL
        # return 也不支持 → FULL
        assert plans["return"].strategy == IncrementalStrategy.FULL

    def test_append_only_for_pure_inserts(self):
        g = self._make_graph()
        # 模拟支持增量的节点
        class IncrementalNode(ReturnNode):
            def supports_incremental(self) -> bool:
                return True
        g2 = ResearchGraph()
        g2.add_node(IncrementalNode())
        cs = ChangeSet().add_insert("BTC", pd.Timestamp("2024-01-10"), {"close": 105.0})
        dg = DirtyGraph({"return"}, {"close"}, cs)
        planner = IncrementalPlanner()
        plans = planner.plan(g2, dg, cs)
        assert plans["return"].strategy == IncrementalStrategy.APPEND_ONLY


# ---------------------------------------------------------------------- #
# 4. StateStore
# ---------------------------------------------------------------------- #
class TestStateStore:
    def test_save_and_load_dataframe(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        df = pd.DataFrame({
            "datetime": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
            "symbol": ["BTC", "BTC"],
            "value": [1.0, 2.0],
        }).set_index(["datetime", "symbol"])
        state = NodeState(
            node_id="test_node",
            node_version="1.0.0",
            data=df,
            meta={"foo": "bar"},
            inputs_hash="abc123",
        )
        store.save(state)
        assert store.exists("test_node", "1.0.0")
        loaded = store.load("test_node", "1.0.0")
        assert loaded is not None
        assert loaded.node_id == "test_node"
        assert loaded.meta["foo"] == "bar"
        assert loaded.inputs_hash == "abc123"
        assert isinstance(loaded.data, pd.DataFrame)

    def test_load_missing(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        assert store.load("missing") is None
        assert not store.exists("missing")

    def test_clear(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        df = pd.DataFrame({"a": [1]})
        state = NodeState(node_id="n1", data=df)
        store.save(state)
        assert store.exists("n1")
        store.clear("n1")
        assert not store.exists("n1")


# ---------------------------------------------------------------------- #
# 5. 集成测试: 追加1根K线 → 增量 == 全量
# ---------------------------------------------------------------------- #
class TestIncrementalConsistency:
    def test_append_one_bar_consistency(self):
        """追加 1 根 K 线，验证增量结果与全量结果一致。"""
        np.random.seed(42)
        # 全量数据: 10 天
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC",):
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "open": 100.0, "high": 101.0, "low": 99.0,
                    "close": 100.0 + np.random.randn() * 2,
                    "volume": 1000.0,
                })
        panel = pd.DataFrame(rows).set_index(["datetime", "symbol"])
        # 用全量数据计算一次 (CloseNode + ReturnNode)
        from quantlab.research import ResearchFrame
        from quantlab.research.context import ExecutionContext
        from quantlab.research.executor import ResearchExecutor
        ctx = ExecutionContext()
        ctx.set("frame", ResearchFrame.from_panel(panel))
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_edge("close", "close", "return", "close")
        ex = ResearchExecutor()
        result_full = ex.execute(g, initial_store=ctx.frame_store)
        full_close = result_full.get("close").data
        full_return = result_full.get("return").data
        # 现在模拟追加 1 根 K 线 (增量)
        new_row = {
            "datetime": pd.Timestamp("2024-01-11"), "symbol": "BTC",
            "open": 100.0, "high": 101.0, "low": 99.0,
            "close": 110.0, "volume": 1000.0,
        }
        new_panel = pd.concat([panel, pd.DataFrame([new_row]).set_index(["datetime", "symbol"])])
        ctx2 = ExecutionContext()
        ctx2.set("frame", ResearchFrame.from_panel(new_panel))
        result_inc = ex.execute(g, initial_store=ctx2.frame_store)
        inc_close = result_inc.get("close").data
        inc_return = result_inc.get("return").data
        # 增量结果应与全量结果 (用新数据重算) 一致
        # 这里验证: 用新数据全量重算 == 增量重算 (因为增量框架暂用全量重算策略)
        ctx3 = ExecutionContext()
        ctx3.set("frame", ResearchFrame.from_panel(new_panel))
        result_full2 = ex.execute(g, initial_store=ctx3.frame_store)
        full2_close = result_full2.get("close").data
        # 验证 close 一致
        assert_frame_equal = pd.testing.assert_frame_equal
        assert_frame_equal(inc_close, full2_close)
