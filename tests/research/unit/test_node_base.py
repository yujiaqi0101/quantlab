"""
ResearchNode 基类单元测试
"""
import pytest

from quantlab.research.frame import ResearchFrame
from quantlab.research.node.base import (
    CachePolicy,
    CostEstimate,
    Delta,
    NodeDescription,
    ResearchNode,
)
from quantlab.research.node.manifest import NodeCategory, NodeManifest, NodeMetadata
from quantlab.research.node.ports import Port, PortType


# ---------------------------------------------------------------------- #
# 测试用具体 Node 子类
# ---------------------------------------------------------------------- #
class DummyCloseNode(ResearchNode):
    """读取 close 列的简单节点"""
    id = "dummy_close"
    version = "1.0.0"
    category = NodeCategory.DATA
    inputs = []
    outputs = [Port(name="close", type=PortType.FRAME)]
    metadata = NodeMetadata(description="dummy close", cost=1)

    def compute(self, ctx):
        from quantlab.research.frame import ResearchFrame
        return ResearchFrame.from_panel(ctx["df"], name="close")


class DummyRSINode(ResearchNode):
    """需要 close 输入的指标节点"""
    id = "dummy_rsi"
    version = "1.0.0"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="close", type=PortType.FRAME, required=True)]
    outputs = [Port(name="rsi", type=PortType.FRAME)]
    metadata = NodeMetadata(description="dummy RSI", cost=3)

    def compute(self, ctx):
        from quantlab.research.frame import ResearchFrame
        return ResearchFrame.from_panel(ctx["df"], name="rsi")


# ---------------------------------------------------------------------- #
# 测试
# ---------------------------------------------------------------------- #
class TestResearchNodeIdentity:
    def test_auto_id_from_classname(self):
        class NoIdNode(ResearchNode):
            def compute(self, ctx):
                pass
        node = NoIdNode()
        assert node.id == "noidnode"

    def test_explicit_id(self):
        node = DummyCloseNode()
        assert node.id == "dummy_close"
        assert node.version == "1.0.0"
        assert node.category is NodeCategory.DATA

    def test_params_via_init(self):
        node = DummyRSINode(window=14)
        assert node.parameters["window"] == 14

    def test_params_merge(self):
        class WithParams(ResearchNode):
            id = "wp"
            parameters = {"a": 1}
            def compute(self, ctx):
                pass
        node = WithParams(a=2, b=3)
        assert node.parameters == {"a": 2, "b": 3}


class TestResearchNodeFingerprint:
    def test_stability_same_params(self):
        n1 = DummyRSINode()
        n2 = DummyRSINode()
        assert n1.fingerprint() == n2.fingerprint()

    def test_differs_by_params(self):
        n1 = DummyRSINode(window=14)
        n2 = DummyRSINode(window=21)
        assert n1.fingerprint() != n2.fingerprint()

    def test_is_hex_16(self):
        fp = DummyRSINode().fingerprint()
        assert len(fp) == 16
        int(fp, 16)  # 不报错即为合法 hex


class TestResearchNodeCapabilities:
    def test_defaults(self):
        node = DummyCloseNode()
        assert node.supports_incremental() is False
        assert node.supports_parallel() is False
        assert node.supports_gpu() is False
        assert node.cache_policy() is CachePolicy.MEMORY

    def test_update_not_implemented(self):
        node = DummyCloseNode()
        with pytest.raises(NotImplementedError, match="incremental"):
            node.update(None, None)

    def test_estimate_delta_default(self):
        node = DummyCloseNode()
        delta = node.estimate_delta(None)
        assert delta.recompute_ratio == 1.0


class TestResearchNodeLifecycle:
    def test_validate_no_schema(self):
        node = DummyRSINode()
        assert node.validate() is True

    def test_validate_with_required_port_present(self):
        node = DummyRSINode()
        schema = {"ports": ["close"]}
        assert node.validate(schema) is True

    def test_validate_with_required_port_missing(self):
        node = DummyRSINode()
        schema = {"ports": ["open"]}
        assert node.validate(schema) is False

    def test_estimate_cost_default(self):
        node = DummyRSINode()
        cost = node.estimate_cost()
        assert isinstance(cost, CostEstimate)
        assert cost.stars == 3  # metadata.cost=3

    def test_describe(self):
        node = DummyRSINode()
        desc = node.describe()
        assert isinstance(desc, NodeDescription)
        assert "RSI" in desc.summary
        assert "close" in desc.inputs_desc


class TestResearchNodeManifest:
    def test_manifest_generation(self):
        node = DummyRSINode(window=14)
        m = node.manifest()
        assert isinstance(m, NodeManifest)
        assert m.id == "dummy_rsi"
        assert m.version == "1.0.0"
        assert m.category is NodeCategory.INDICATOR
        assert len(m.inputs) == 1
        assert m.inputs[0].name == "close"
        assert m.params == {"window": 14}

    def test_manifest_fingerprint_matches_node(self):
        node = DummyRSINode(window=14)
        m = node.manifest()
        assert m.fingerprint_basis == node.fingerprint()

    def test_to_dict(self):
        node = DummyRSINode(window=14)
        d = node.to_dict()
        assert d["id"] == "dummy_rsi"
        assert d["version"] == "1.0.0"
        assert d["category"] == "indicator"
        assert d["parameters"]["window"] == 14
        caps = d["capabilities"]
        assert caps["incremental"] is False
        assert caps["cache_policy"] == "memory"


class TestResearchNodeCompute:
    def test_compute_called(self):
        import numpy as np
        import pandas as pd
        # 构造面板数据
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        rows = []
        for dt in dates:
            for sym in ("BTC", "ETH"):
                rows.append({"datetime": dt, "symbol": sym, "close": 100.0})
        df = pd.DataFrame(rows).set_index(["datetime", "symbol"])
        ctx = {"df": df}
        node = DummyCloseNode()
        rf = node.compute(ctx)
        assert isinstance(rf, ResearchFrame)
        assert rf.name == "close"
        assert len(rf) == 6


class TestResearchNodeRepr:
    def test_repr(self):
        node = DummyRSINode()
        s = repr(node)
        assert "DummyRSINode" in s
        assert "dummy_rsi" in s
