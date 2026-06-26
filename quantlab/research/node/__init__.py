"""
Research Node — 节点抽象层

ResearchNode 是 QuantLab 唯一的数据计算语言，统一替代旧 Feature + FactorInfo。
"""

from .ports import Port, PortType
from .manifest import NodeCategory, NodeManifest, NodeMetadata
from .base import ResearchNode
from .registry import NodeRegistry, get_registry

__all__ = [
    "Port",
    "PortType",
    "NodeCategory",
    "NodeManifest",
    "NodeMetadata",
    "ResearchNode",
    "NodeRegistry",
    "get_registry",
]
