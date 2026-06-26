"""
NodeManifest 单元测试
"""
import pytest

from quantlab.research.node.ports import Port, PortType
from quantlab.research.node.manifest import NodeCategory, NodeManifest, NodeMetadata


class TestNodeCategory:
    def test_values(self):
        assert NodeCategory.DATA.value == "data"
        assert NodeCategory.INDICATOR.value == "indicator"
        assert NodeCategory.ALPHA.value == "alpha"
        assert NodeCategory.LABEL.value == "label"

    def test_from_string(self):
        assert NodeCategory("indicator") is NodeCategory.INDICATOR


class TestNodeMetadata:
    def test_defaults(self):
        m = NodeMetadata()
        assert m.description == ""
        assert m.author == ""
        assert m.cost == 1
        assert m.deprecated is False
        assert m.tags == []

    def test_to_dict_roundtrip(self):
        m = NodeMetadata(description="RSI", author="yujiaqi", cost=3, tags=["momentum"])
        d = m.to_dict()
        m2 = NodeMetadata.from_dict(d)
        assert m2.description == "RSI"
        assert m2.author == "yujiaqi"
        assert m2.cost == 3
        assert m2.tags == ["momentum"]


class TestNodeManifest:
    def _make(self, **kw):
        return NodeManifest(
            id="rsi14",
            version="1.0.0",
            category=NodeCategory.INDICATOR,
            inputs=[Port(name="close", type=PortType.FRAME)],
            outputs=[Port(name="rsi", type=PortType.FRAME)],
            params={"window": 14},
            metadata=NodeMetadata(description="RSI 14", cost=2),
            **kw,
        )

    def test_creation(self):
        m = self._make()
        assert m.id == "rsi14"
        assert m.version == "1.0.0"
        assert m.category is NodeCategory.INDICATOR
        assert len(m.inputs) == 1
        assert m.inputs[0].name == "close"
        assert m.params["window"] == 14

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            NodeManifest(id="")

    def test_default_version(self):
        m = NodeManifest(id="x")
        assert m.version == "1.0.0"

    def test_deprecated_propagates(self):
        m = NodeManifest(id="x", deprecated=True)
        assert m.metadata.deprecated is True

    def test_to_dict_from_dict_roundtrip(self):
        m = self._make()
        d = m.to_dict()
        m2 = NodeManifest.from_dict(d)
        assert m2.id == m.id
        assert m2.version == m.version
        assert m2.category is m.category
        assert m2.params == m.params
        assert len(m2.inputs) == len(m.inputs)
        assert m2.inputs[0].name == "close"

    def test_to_json_from_json_roundtrip(self):
        m = self._make()
        s = m.to_json()
        m2 = NodeManifest.from_json(s)
        assert m2.id == m.id
        assert m2.params["window"] == 14

    def test_fingerprint_stability(self):
        """相同参数 → 相同指纹。"""
        m1 = self._make()
        m2 = self._make()
        assert m1.fingerprint() == m2.fingerprint()

    def test_fingerprint_differs_by_params(self):
        m1 = NodeManifest(id="rsi", params={"window": 14})
        m2 = NodeManifest(id="rsi", params={"window": 21})
        assert m1.fingerprint() != m2.fingerprint()

    def test_fingerprint_differs_by_version(self):
        m1 = NodeManifest(id="rsi", version="1.0.0")
        m2 = NodeManifest(id="rsi", version="2.0.0")
        assert m1.fingerprint() != m2.fingerprint()

    def test_same_identity(self):
        m1 = NodeManifest(id="rsi", version="1.0.0")
        m2 = NodeManifest(id="rsi", version="2.0.0")
        assert m1.same_identity(m2) is True

    def test_same_version(self):
        m1 = NodeManifest(id="rsi", version="1.0.0")
        m2 = NodeManifest(id="rsi", version="1.0.0")
        m3 = NodeManifest(id="rsi", version="2.0.0")
        assert m1.same_version(m2) is True
        assert m1.same_version(m3) is False

    def test_repr(self):
        m = self._make()
        s = repr(m)
        assert "rsi14" in s
        assert "1.0.0" in s
