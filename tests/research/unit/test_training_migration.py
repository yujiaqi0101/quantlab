"""
阶段7-8 测试: 训练层迁移 + LabelAdapter + TrainingValidator + Graph模式训练
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.research import ResearchFrame
from quantlab.research.builtin import (
    CloseNode,
    FutureReturnNode,
    ReturnNode,
    RSINode,
)
from quantlab.research.graph import ResearchGraph
from quantlab.ml.training import (
    TrainingJob,
    TrainingValidator,
)


# ---------------------------------------------------------------------- #
# 1. LabelAdapterNode
# ---------------------------------------------------------------------- #
class TestLabelAdapter:
    def test_label_to_node(self):
        from quantlab.ml.label.builtin import FutureReturn
        from quantlab.research.adapters import LabelAdapterNode

        label = FutureReturn(period=5)
        node = LabelAdapterNode(label)
        assert node.id == "label.future_return_5"
        assert node.category.value == "label"
        assert len(node.outputs) == 1

    def test_compute(self):
        from quantlab.ml.label.builtin import FutureReturn
        from quantlab.research.adapters import LabelAdapterNode
        from quantlab.research.dataset_context import DatasetContext

        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=15, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC", "ETH"):
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "close": 100.0 + np.random.randn() * 3,
                })
        panel = pd.DataFrame(rows).set_index(["datetime", "symbol"])
        ctx = DatasetContext(panel=panel)
        node = LabelAdapterNode(FutureReturn(period=3))
        rf = node.compute(ctx)
        assert isinstance(rf, ResearchFrame)
        assert "future_return_3" in rf.data.columns


# ---------------------------------------------------------------------- #
# 2. TrainingValidator
# ---------------------------------------------------------------------- #
class TestTrainingValidator:
    def _make_data(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC",):
                rows.append({
                    "datetime": dt, "symbol": sym,
                    "f1": np.random.randn(),
                    "f2": np.random.randn(),
                    "y": np.random.randn(),
                })
        df = pd.DataFrame(rows).set_index(["datetime", "symbol"])
        return df

    def test_clean_split_ok(self):
        df = self._make_data()
        # 前 20 天 train, 后 10 天 test
        train_dates = df.index.get_level_values("datetime").unique()[:20]
        test_dates = df.index.get_level_values("datetime").unique()[20:]
        X_train = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(train_dates)]
        y_train = df["y"][df.index.get_level_values("datetime").isin(train_dates)]
        X_test = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(test_dates)]
        y_test = df["y"][df.index.get_level_values("datetime").isin(test_dates)]
        v = TrainingValidator()
        report = v.validate(X_train, y_train, X_test, y_test)
        assert report.ok
        assert report.errors == 0

    def test_overlap_dates_error(self):
        df = self._make_data()
        train_dates = df.index.get_level_values("datetime").unique()[:20]
        test_dates = df.index.get_level_values("datetime").unique()[15:30]  # 重叠 5 天
        X_train = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(train_dates)]
        y_train = df["y"][df.index.get_level_values("datetime").isin(train_dates)]
        X_test = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(test_dates)]
        y_test = df["y"][df.index.get_level_values("datetime").isin(test_dates)]
        v = TrainingValidator()
        report = v.validate(X_train, y_train, X_test, y_test)
        assert not report.ok
        assert report.errors >= 1
        assert any(i.category == "split" for i in report.issues)

    def test_timeseries_leakage(self):
        df = self._make_data()
        # 故意 train 包含比 test 更晚的日期
        train_dates = df.index.get_level_values("datetime").unique()[5:25]
        test_dates = df.index.get_level_values("datetime").unique()[:5]
        X_train = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(train_dates)]
        y_train = df["y"][df.index.get_level_values("datetime").isin(train_dates)]
        X_test = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(test_dates)]
        y_test = df["y"][df.index.get_level_values("datetime").isin(test_dates)]
        v = TrainingValidator()
        report = v.validate(X_train, y_train, X_test, y_test)
        assert not report.ok
        assert any(i.category == "leakage" for i in report.issues)

    def test_high_nan_warning(self):
        df = self._make_data()
        df["f1"] = np.nan
        train_dates = df.index.get_level_values("datetime").unique()[:20]
        test_dates = df.index.get_level_values("datetime").unique()[20:]
        X_train = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(train_dates)]
        y_train = df["y"][df.index.get_level_values("datetime").isin(train_dates)]
        X_test = df[["f1", "f2"]][df.index.get_level_values("datetime").isin(test_dates)]
        y_test = df["y"][df.index.get_level_values("datetime").isin(test_dates)]
        v = TrainingValidator()
        report = v.validate(X_train, y_train, X_test, y_test)
        assert report.warnings >= 1
        assert any(i.category == "data_quality" for i in report.issues)


# ---------------------------------------------------------------------- #
# 3. TrainingJob Graph 模式
# ---------------------------------------------------------------------- #
class TestTrainingJobGraphMode:
    def _make_panel(self, n=40):
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

    def _make_graph(self):
        g = ResearchGraph(name="train")
        g.add_node(CloseNode())
        g.add_node(ReturnNode(period=1))
        g.add_node(RSINode(window=5))
        g.add_node(FutureReturnNode(horizon=3))
        g.add_edge("close", "close", "return", "close")
        g.add_edge("close", "close", "rsi", "close")
        g.add_edge("close", "close", "future_return", "close")
        return g

    def test_build_from_graph(self):
        """测试 Graph 模式构建训练数据集 (不实际训练)。"""
        from quantlab.ml.dataset import Dataset, get_dataset_manager
        from quantlab.ml.model import ModelType
        panel = self._make_panel()

        # 用全局单例 manager (persist=False 避免触达 DB)
        import quantlab.ml.dataset as ds_mod
        ds_mod._dataset_manager = None  # 重置单例
        mgr = get_dataset_manager(persist=False)
        ds = Dataset(name="test_graph", symbols=["BTC", "ETH"], frequency="1d")
        ds.set_data(panel)
        mgr._datasets[ds.dataset_id] = ds

        g = self._make_graph()
        job = TrainingJob(
            dataset_id=ds.dataset_id,
            research_graph=g,
            label_node_id="future_return",
            materialize_config={
                "normalize": True,
                "train_ratio": 0.7,
                "val_ratio": 0.15,
                "test_ratio": 0.15,
            },
            model_type=ModelType.LINEAR_REGRESSION,
        )
        tds = job._build_training_dataset()
        assert tds is not None
        assert len(tds.X) > 0
        assert tds.metadata.get("mode") == "graph"
        # 测试集应单独保存
        assert tds.metadata.get("_graph_test_X") is not None
        # 清理全局单例
        ds_mod._dataset_manager = None

    def test_end_to_end_training(self):
        """端到端: Graph → Executor → Materializer → TrainingJob → Model。"""
        from quantlab.ml.dataset import Dataset, get_dataset_manager
        from quantlab.ml.model import ModelType
        panel = self._make_panel(n=50)

        # 用全局单例 manager
        import quantlab.ml.dataset as ds_mod
        ds_mod._dataset_manager = None
        mgr = get_dataset_manager(persist=False)
        ds = Dataset(name="test_e2e", symbols=["BTC", "ETH"], frequency="1d")
        ds.set_data(panel)
        mgr._datasets[ds.dataset_id] = ds

        g = self._make_graph()
        job = TrainingJob(
            dataset_id=ds.dataset_id,
            research_graph=g,
            label_node_id="future_return",
            materialize_config={"normalize": True, "train_ratio": 0.6, "val_ratio": 0.2},
            model_type=ModelType.LINEAR_REGRESSION,
            model_params={},
            save_experiment=False,
        )
        result = job.run()
        assert result.status.value == "COMPLETED", f"训练失败: {result.error}"
        assert result.n_train_samples > 0
        assert result.n_test_samples > 0
        assert result.metrics is not None
        # 清理
        ds_mod._dataset_manager = None


# ---------------------------------------------------------------------- #
# 4. 旧模式回归 (兼容性)
# ---------------------------------------------------------------------- #
class TestLegacyModeCompat:
    def test_mode2_still_works(self):
        """模式2 (feature_set_id + label_set_id) 仍可用。"""
        from quantlab.ml.training import TrainingJob
        job = TrainingJob(
            dataset_id="dummy",
            feature_set_id="dummy",
            label_set_id="dummy",
        )
        # 不实际 run (没有真实数据)，只验证字段
        assert job.feature_set_id == "dummy"
        assert job.research_graph is None

    def test_mode3_priority(self):
        """Graph 模式优先于旧模式。"""
        from quantlab.ml.training import TrainingJob
        g = ResearchGraph()
        g.add_node(CloseNode())
        job = TrainingJob(
            dataset_id="dummy",
            research_graph=g,
            label_node_id="close",
            feature_set_id="legacy",  # 旧模式字段
        )
        # 应该走 Graph 模式
        assert job.research_graph is not None
