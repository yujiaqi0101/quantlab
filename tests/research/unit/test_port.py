"""
Port 单元测试
"""
import pytest

from quantlab.research.node.ports import Port, PortType


class TestPortType:
    def test_enum_values(self):
        assert PortType.SERIES.value == "series"
        assert PortType.FRAME.value == "frame"
        assert PortType.PANEL.value == "panel"
        assert PortType.SCALAR.value == "scalar"
        assert PortType.REFERENCE.value == "reference"

    def test_from_string(self):
        assert PortType("frame") is PortType.FRAME
        assert PortType("series") is PortType.SERIES


class TestPort:
    def test_creation_defaults(self):
        p = Port(name="close")
        assert p.name == "close"
        assert p.type is PortType.FRAME
        assert p.required is True
        assert p.description == ""
        assert p.default is None

    def test_creation_full(self):
        p = Port(
            name="window",
            type=PortType.SCALAR,
            required=False,
            description="rolling window",
            default=14,
        )
        assert p.name == "window"
        assert p.type is PortType.SCALAR
        assert p.required is False
        assert p.description == "rolling window"
        assert p.default == 14

    def test_to_dict(self):
        p = Port(name="rsi", type=PortType.FRAME, description="RSI output")
        d = p.to_dict()
        assert d["name"] == "rsi"
        assert d["type"] == "frame"
        assert d["required"] is True
        assert d["description"] == "RSI output"

    def test_from_dict_roundtrip(self):
        p = Port(name="close", type=PortType.FRAME, required=True, description="close price")
        d = p.to_dict()
        p2 = Port.from_dict(d)
        assert p2.name == p.name
        assert p2.type is p.type
        assert p2.required == p.required
        assert p2.description == p.description

    def test_from_dict_defaults(self):
        p = Port.from_dict({"name": "x"})
        assert p.name == "x"
        assert p.type is PortType.FRAME
        assert p.required is True
