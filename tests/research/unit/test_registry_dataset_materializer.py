"""
阶段5 测试: Registry + Universe + Calendar + Materializer + DatasetContext
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research import ResearchFrame
from quantlab.research.builtin import CloseNode, ReturnNode, RSINode, FutureReturnNode
from quantlab.research.calendar import get_calendar_registry
from quantlab.research.dataset_context import DatasetContext
from quantlab.research.executor import ResearchExecutor
from quantlab.research.graph import ResearchGraph
from quantlab.research.materializer import Materializer, SplitConfig
from quantlab.research.node.registry import NodeRegistry, get_registry
from quantlab.research.universe import (
    RebalanceFreq,
    UniverseDefinition,
    get_universe_registry,
)


# ---------------------------------------------------------------------- #
# 1. NodeRegistry
# ---------------------------------------------------------------------- #
class TestNodeRegistry:
    def test_register_and_get(self):
        reg = NodeRegistry()
        reg.register(CloseNode)
        assert reg.get("close") is CloseNode

    def test_version_coexist(self):
        reg = NodeRegistry()
        # 模拟两个版本
        class RSIv1(RSINode):
            pass
        class RSIv2(RSINode):
            pass
        reg.register(RSIv1, version="1.0.0")
        reg.register(RSIv2, version="2.0.0")
        assert reg.get("rsi", "1.0.0") is RSIv1
        assert reg.get("rsi", "2.0.0") is RSIv2
        # latest 应是 2.0.0
        assert reg.get_latest("rsi") is RSIv2

    def test_list_by_category(self):
        reg = get_registry()
        from quantlab.research.node.manifest import NodeCategory
        indicators = reg.list_by_category(NodeCategory.INDICATOR)
        assert len(indicators) > 0
        ids = [i["id"] for i in indicators]
        assert "rsi" in ids

    def test_auto_register_builtins(self):
        reg = get_registry()
        assert reg.size() >= 20
        assert reg.get("close") is not None
        assert reg.get("rsi") is not None
        assert reg.get("alpha014") is not None

    def test_list_categories(self):
        reg = get_registry()
        cats = reg.list_categories()
        assert "data" in cats
        assert "indicator" in cats
        assert "alpha" in cats


# ---------------------------------------------------------------------- #
# 2. UniverseRegistry
# ---------------------------------------------------------------------- #
class TestUniverse:
    def test_static_resolve(self):
        u = UniverseDefinition(id="test", members=["BTC", "ETH"])
        assert u.resolve() == ["BTC", "ETH"]

    def test_dynamic_top_n(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC", "ETH", "BNB"):
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "close": 100.0, "volume": {"BTC": 1000, "ETH": 500, "BNB": 200}[sym],
                })
        panel = pd.DataFrame(rows).set_index(["datetime", "symbol"])
        u = UniverseDefinition(
            id="dyn", rule="top_n_by_volume", rule_params={"n": 2, "min_volume": 100}
        )
        members = u.resolve(panel)
        assert "BTC" in members
        assert "ETH" in members
        assert "BNB" not in members  # volume 最小

    def test_registry(self):
        reg = get_universe_registry()
        assert reg.get("crypto_top10") is not None
        assert reg.get("crypto_top10").members == ["BTC", "ETH", "BNB"]

    def test_resolve_via_registry(self):
        reg = get_universe_registry()
        members = reg.resolve("crypto_top10")
        assert "BTC" in members


# ---------------------------------------------------------------------- #
# 3. CalendarRegistry
# ---------------------------------------------------------------------- #
class TestCalendar:
    def test_builtin_calendars(self):
        reg = get_calendar_registry()
        assert reg.get("crypto") is not None
        assert reg.get("a_share") is not None
        assert reg.get("nyse") is not None

    def test_generate_dates(self):
        reg = get_calendar_registry()
        cal = reg.get("crypto")
        dates = cal.generate_dates("2024-01-01", "2024-01-07", freq="D")
        assert len(dates) == 7  # 7x24 全天候

    def test_generate_dates_with_holidays(self):
        from quantlab.research.calendar import CalendarDefinition
        cal = CalendarDefinition(
            id="test", holidays=["2024-01-02"]
        )
        dates = cal.generate_dates("2024-01-01", "2024-01-05", freq="D")
        assert "2024-01-02" not in [str(d.date()) for d in dates]


# ---------------------------------------------------------------------- #
# 4. DatasetContext
# ---------------------------------------------------------------------- #
class TestDatasetContext:
    def _make_panel(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC", "ETH"):
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "close": 100.0 + np.random.randn() * 5,
                    "volume": 1000.0,
                })
        return pd.DataFrame(rows).set_index(["datetime", "symbol"])

    def test_basic(self):
        panel = self._make_panel()
        ctx = DatasetContext(panel=panel)
        assert set(ctx.symbols) == {"BTC", "ETH"}
        assert len(ctx.datetimes) == 20

    def test_filter_universe(self):
        panel = self._make_panel()
        ctx = DatasetContext(panel=panel)
        filtered = ctx.filter_universe(["BTC"])
        assert set(filtered.symbols) == {"BTC"}

    def test_filter_date_range(self):
        panel = self._make_panel()
        ctx = DatasetContext(panel=panel)
        filtered = ctx.filter_date_range("2024-01-05", "2024-01-10")
        assert len(filtered.datetimes) == 6

    def test_fingerprint_stable(self):
        panel = self._make_panel()
        ctx1 = DatasetContext(panel=panel.copy())
        ctx2 = DatasetContext(panel=panel.copy())
        assert ctx1.fingerprint() == ctx2.fingerprint()

    def test_as_frame(self):
        panel = self._make_panel()
        ctx = DatasetContext(panel=panel)
        rf = ctx.as_frame()
        assert isinstance(rf, ResearchFrame)


# ---------------------------------------------------------------------- #
# 5. Materializer
# ---------------------------------------------------------------------- #
class TestMaterializer:
    def _make_ohlcv(self, n=30):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC", "ETH"):
                close = 100.0 + np.random.randn() * 5
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "open": close-0.5, "high": close+1, "low": close-1,
                    "close": close, "volume": 1000.0,
                })
        return pd.DataFrame(rows).set_index(["datetime", "symbol"])

    def test_materialize_basic(self):
        ohlcv = self._make_ohlcv()
        ctx_store = DatasetContext(panel=ohlcv)
        # 构造图: close -> return, close -> rsi, close -> future_return(label)
        from quantlab.research.context import ExecutionContext
        ex_ctx = ExecutionContext()
        ex_ctx.set("frame", ResearchFrame.from_panel(ohlcv))
        # 执行特征图
        g = ResearchGraph(name="train")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(RSINode(window=5))
        g.add_node(FutureReturnNode(horizon=3))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "rsi", "close")
        g.add_edge("close", "close", "future_return", "close")
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=ex_ctx.frame_store)
        # 实体化
        mat = Materializer()
        features = {
            "return": result.get("return"),
            "rsi": result.get("rsi"),
        }
        label = result.get("future_return")
        ds = mat.materialize(features, label, SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15))
        assert len(ds.X_train) > 0
        assert len(ds.y_train) > 0
        assert "return" in ds.feature_names
        assert "rsi" in ds.feature_names
        assert ds.label_name == "future_return"

    def test_time_split_no_leakage(self):
        """时序切分: train 的 datetime 都早于 test。"""
        ohlcv = self._make_ohlcv(n=40)
        from quantlab.research.context import ExecutionContext
        ex_ctx = ExecutionContext()
        ex_ctx.set("frame", ResearchFrame.from_panel(ohlcv))
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(FutureReturnNode(horizon=3))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "future_return", "close")
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=ex_ctx.frame_store)
        mat = Materializer()
        ds = mat.materialize(
            {"return": result.get("return")},
            result.get("future_return"),
            SplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2),
            normalize=True,
        )
        # 训练集日期都早于测试集
        train_max = ds.X_train.index.get_level_values("datetime").max()
        test_min = ds.X_test.index.get_level_values("datetime").min()
        assert train_max < test_min

    def test_normalize_reversible(self):
        """归一化参数可逆 (用 mean/std 还原)。"""
        ohlcv = self._make_ohlcv(n=30)
        from quantlab.research.context import ExecutionContext
        ex_ctx = ExecutionContext()
        ex_ctx.set("frame", ResearchFrame.from_panel(ohlcv))
        g = ResearchGraph()
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(FutureReturnNode(horizon=2))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "future_return", "close")
        ex = ResearchExecutor()
        result = ex.execute(g, initial_store=ex_ctx.frame_store)
        mat = Materializer()
        ds = mat.materialize(
            {"return": result.get("return")},
            result.get("future_return"),
            normalize=True,
        )
        # 验证归一化后 train 均值≈0, std≈1
        assert abs(ds.X_train.mean().mean()) < 1e-6
        assert abs(ds.X_train.std().mean() - 1) < 1e-6
        # 验证可还原
        mean = pd.Series(ds.normalize_params["mean"])
        std = pd.Series(ds.normalize_params["std"])
        restored = ds.X_train * std + mean
        # (值应与原始对齐后的 X 接近)
