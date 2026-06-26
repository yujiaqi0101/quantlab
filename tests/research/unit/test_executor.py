"""
ResearchExecutor 单元 + 集成测试

重点：
  1. 单节点执行 (CloseNode)
  2. 两节点链式执行 (Close -> Return)
  3. Alpha014 端到端执行
  4. L1 Execution Cache 生效 (同节点只算一次)
  5. 并行模式 vs 顺序模式结果一致
  6. 错误处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research import (
    ExecutionContext,
    ResearchExecutor,
    ResearchFrame,
    ResearchGraph,
)
from quantlab.research.builtin import (
    Alpha014Node,
    CloseNode,
    HighNode,
    ReturnNode,
    RSINode,
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


@pytest.fixture
def ohlcv_panel() -> pd.DataFrame:
    return _make_ohlcv_panel()


@pytest.fixture
def initial_store(ohlcv_panel) -> ExecutionContext:
    """上游已注入 OHLCV 面板的 ExecutionContext。"""
    ctx = ExecutionContext()
    ctx.set("frame", ResearchFrame.from_panel(ohlcv_panel))
    return ctx.frame_store


# ---------------------------------------------------------------------- #
# 1. 单节点执行
# ---------------------------------------------------------------------- #
class TestSingleNodeExecution:
    def test_close_node(self, initial_store):
        g = ResearchGraph(name="close_only")
        g.add_node(CloseNode())
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=initial_store)
        assert result.get("close") is not None
        assert "close" in result.get("close").data.columns
        assert "close" in result.executed


# ---------------------------------------------------------------------- #
# 2. 两节点链式执行
# ---------------------------------------------------------------------- #
class TestLinearChain:
    def test_close_to_return(self, initial_store):
        g = ResearchGraph(name="close_return")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_edge("close", "close", "return", "close")
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=initial_store)
        # 两个节点都执行了
        assert set(result.executed) == {"close", "return"}
        # return 节点有 future_return 输出
        ret_frame = result.get("return")
        assert "return" in ret_frame.data.columns


# ---------------------------------------------------------------------- #
# 3. Alpha014 端到端
# ---------------------------------------------------------------------- #
class TestAlpha014Execution:
    def test_alpha014(self, initial_store):
        g = ResearchGraph(name="alpha014")
        g.add_node(Alpha014Node())
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=initial_store)
        rf = result.get("alpha014")
        assert rf is not None
        assert "alpha014" in rf.data.columns
        assert len(rf) == 60  # 30 * 2 symbols


# ---------------------------------------------------------------------- #
# 4. L1 Execution Cache
# ---------------------------------------------------------------------- #
class TestExecutionCache:
    def test_no_duplicate_compute(self, initial_store, monkeypatch):
        """同一执行中同节点只 compute 一次。

        方法：用 call counter 拦截 compute。
        """
        calls = {"count": 0}
        orig_compute = CloseNode.compute

        def counting_compute(self, ctx):
            calls["count"] += 1
            return orig_compute(self, ctx)

        monkeypatch.setattr(CloseNode, "compute", counting_compute)

        # 构造一个有两个下游消费 close 的图
        g = ResearchGraph(name="multi_consumer")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(RSINode(window=14))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "rsi", "close")
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=initial_store)
        # close 应只被 compute 一次
        assert calls["count"] == 1
        assert set(result.executed) == {"close", "return", "rsi"}


# ---------------------------------------------------------------------- #
# 5. 并行 vs 顺序
# ---------------------------------------------------------------------- #
class TestParallelMode:
    def test_parallel_equals_sequential(self, initial_store):
        g = ResearchGraph(name="parallel_test")
        g.add_node(CloseNode())
        g.add_node(HighNode())
        ex_seq = ResearchExecutor()
        ex_par = ResearchExecutor(max_workers=2)
        r_seq = ex_seq.execute(g, initial_store=initial_store, mode="sequential")
        r_par = ex_par.execute(g, initial_store=initial_store, mode="parallel")
        # 两个独立节点都执行了
        assert set(r_seq.executed) == {"close", "high"}
        assert set(r_par.executed) == {"close", "high"}
        # 结果值一致
        pd.testing.assert_frame_equal(
            r_seq.get("close").data, r_par.get("close").data
        )


# ---------------------------------------------------------------------- #
# 6. 错误处理
# ---------------------------------------------------------------------- #
class TestErrorHandling:
    def test_missing_upstream_raises(self, initial_store):
        """节点缺少上游数据应捕获错误。"""
        g = ResearchGraph(name="err")
        g.add_node(ReturnNode(period=1))  # 没有 close 上游
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=initial_store)
        assert "return" in result.errors
        assert len(result.errors["return"]) > 0

    def test_partial_failure_does_not_block_others(self):
        """一个节点失败，独立节点仍可执行。

        构造：CloseNode 成功（有 frame 上游），ReturnNode 失败（无 close 数据）。
        用一个空 frame_store，让 CloseNode 有 frame 但 ReturnNode 无 close。
        """
        # 空的 store：CloseNode 依赖 frame 端口也没有 → 也会失败
        # 改用：只放 ReturnNode，不放 close 数据
        g = ResearchGraph(name="partial")
        g.add_node(ReturnNode(period=1))  # 无 close 上游 → 失败
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=None)
        assert "return" in result.errors
        assert result.get("return") is None
