"""
Research API 集成测试
======================

覆盖：
1. Node Registry 查询（list/get/categories）
2. Graph CRUD（create/list/get/add_node/add_edge）
3. Compile
4. Execute
5. Materialize
"""
import os
import sys

# 让 tests 目录可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import numpy as np
import pandas as pd
import pytest

from quantlab.api import research as api
from quantlab.research.graph import ResearchGraph
from quantlab.research.node.registry import get_registry


# ---------- fixtures ----------

def _make_panel(n=40):
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rows = []
    for dt in dates:
        for sym in ("BTC", "ETH"):
            close = 100.0 + np.random.randn() * 5
            rows.append({
                "datetime": dt, "symbol": sym,
                "open": close - 0.5, "high": close + 1, "low": close - 1,
                "close": close, "volume": 1000.0,
            })
    return pd.DataFrame(rows).set_index(["datetime", "symbol"])


@pytest.fixture(autouse=True)
def _clear_graphs():
    api._GRAPHS.clear()
    yield
    api._GRAPHS.clear()


@pytest.fixture(autouse=True)
def _reset_dataset_manager():
    """每个测试用独立的 DatasetManager 单例避免污染。"""
    import quantlab.ml.dataset as ds_mod
    ds_mod._dataset_manager = None
    yield
    ds_mod._dataset_manager = None


def _register_panel_dataset(panel, dataset_id="test_api_panel"):
    from quantlab.ml.dataset import Dataset, get_dataset_manager
    mgr = get_dataset_manager(persist=False)
    ds = Dataset(name=dataset_id, symbols=["BTC", "ETH"], frequency="1d")
    ds.set_data(panel)
    mgr._datasets[ds.dataset_id] = ds
    return ds.dataset_id


# ---------- 1. Node Registry ----------

class TestNodeRegistry:
    def test_list_categories(self):
        cats = api.list_node_categories()
        assert "data" in cats
        assert "transform" in cats

    def test_list_nodes(self):
        ns = api.list_nodes()
        assert len(ns) > 0
        # 每项都有 node_id
        assert all(n.node_id for n in ns)

    def test_list_nodes_by_category(self):
        data_nodes = api.list_nodes(category="data")
        assert len(data_nodes) > 0
        assert all(n.category == "data" for n in data_nodes)

    def test_get_node(self):
        ns = api.list_nodes()
        nid = ns[0].node_id
        info = api.get_node(nid)
        assert info.node_id == nid

    def test_get_node_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            api.get_node("nonexistent_node")
        assert exc.value.status_code == 404


# ---------- 2. Graph CRUD ----------

class TestGraphCRUD:
    def test_create_graph(self):
        result = api.create_graph(api.CreateGraphRequest(name="g1"))
        assert "graph_id" in result
        assert result["name"] == "g1"
        assert result["n_nodes"] == 0

    def test_list_graphs(self):
        api.create_graph(api.CreateGraphRequest(name="g1"))
        api.create_graph(api.CreateGraphRequest(name="g2"))
        graphs = api.list_graphs()
        assert len(graphs) == 2

    def test_get_graph(self):
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        detail = api.get_graph(gid)
        assert detail["name"] == "g1"
        assert detail["nodes"] == []

    def test_get_graph_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            api.get_graph("nonexistent")
        assert exc.value.status_code == 404

    def test_add_node(self):
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        # 添加已注册的 close 节点
        result = api.add_node(gid, api.AddNodeRequest(node_id="close"))
        assert result["node_id"] == "close"
        assert result["n_nodes"] == 1

    def test_add_node_with_params(self):
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        # return 节点接受 period 参数
        result = api.add_node(gid, api.AddNodeRequest(node_id="return", params={"period": 5}))
        assert result["n_nodes"] == 1

    def test_add_edge(self):
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        api.add_node(gid, api.AddNodeRequest(node_id="close"))
        api.add_node(gid, api.AddNodeRequest(node_id="return"))
        e = api.add_edge(gid, api.AddEdgeRequest(
            src_node="close", src_port="close",
            dst_node="return", dst_port="close",
        ))
        assert e["n_edges"] == 1


# ---------- 3. Compile ----------

class TestCompile:
    def test_compile_dag(self):
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        api.add_node(gid, api.AddNodeRequest(node_id="close"))
        api.add_node(gid, api.AddNodeRequest(node_id="return"))
        api.add_edge(gid, api.AddEdgeRequest(
            src_node="close", src_port="close",
            dst_node="return", dst_port="close",
        ))
        resp = api.compile_graph(gid)
        assert resp.is_dag is True
        assert resp.n_nodes == 2
        assert resp.n_edges == 1
        assert len(resp.topological_order) == 2
        # close 必须在 return 前
        assert resp.topological_order.index("close") < resp.topological_order.index("return")


# ---------- 4. Execute ----------

class TestExecute:
    def test_execute_simple_graph(self):
        panel = _make_panel()
        ds_id = _register_panel_dataset(panel)

        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        api.add_node(gid, api.AddNodeRequest(node_id="close"))
        api.add_node(gid, api.AddNodeRequest(node_id="return"))
        api.add_edge(gid, api.AddEdgeRequest(
            src_node="close", src_port="close",
            dst_node="return", dst_port="close",
        ))

        resp = api.execute_graph(gid, api.ExecuteRequest(dataset_id=ds_id))
        assert resp.status == "ok"
        assert resp.n_outputs >= 1
        assert "close" in resp.outputs
        assert "return" in resp.outputs

    def test_execute_dataset_not_found(self):
        from fastapi import HTTPException
        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        api.add_node(gid, api.AddNodeRequest(node_id="close"))
        with pytest.raises(HTTPException) as exc:
            api.execute_graph(gid, api.ExecuteRequest(dataset_id="nonexistent"))
        assert exc.value.status_code == 404


# ---------- 5. Materialize ----------

class TestMaterialize:
    def test_materialize_end_to_end(self):
        panel = _make_panel(n=50)
        ds_id = _register_panel_panel(panel)

        r = api.create_graph(api.CreateGraphRequest(name="g1"))
        gid = r["graph_id"]
        api.add_node(gid, api.AddNodeRequest(node_id="close"))
        api.add_node(gid, api.AddNodeRequest(node_id="return"))
        api.add_node(gid, api.AddNodeRequest(node_id="future_return"))
        api.add_edge(gid, api.AddEdgeRequest(src_node="close", src_port="close", dst_node="return", dst_port="close"))
        api.add_edge(gid, api.AddEdgeRequest(src_node="close", src_port="close", dst_node="future_return", dst_port="close"))

        result = api.materialize(gid, api.MaterializeRequest(
            dataset_id=ds_id,
            label_node_id="future_return",
            normalize=True,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        ))
        assert result["n_features"] > 0
        assert result["n_train"] > 0
        assert result["n_test"] > 0
        assert result["label_name"] != ""


def _register_panel_panel(panel, dataset_id="test_api_mat"):
    """避免 fixture 名字冲突的别名。"""
    return _register_panel_dataset(panel, dataset_id)
