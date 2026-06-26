"""
QuantLab Research OS — 研究操作系统

从 "Feature 列表" 升级为 "Research Graph" 范式的统一计算层。

核心抽象:
    ResearchFrame  — (datetime, symbol) MultiIndex 统一数据契约
    ResearchNode   — 统一计算单元 (替代 Feature + FactorInfo)
    NodeManifest   — 节点元数据 (可序列化、可版本化)
    Port           — 节点输入输出端口声明

后续模块 (graph/executor/cache/materializer/incremental) 分阶段实现。
"""

from .frame import ResearchFrame
from .node import (
    NodeCategory,
    NodeManifest,
    NodeMetadata,
    Port,
    PortType,
    ResearchNode,
)

__version__ = "0.1.0"

__all__ = [
    "ResearchFrame",
    "ResearchNode",
    "NodeManifest",
    "NodeMetadata",
    "NodeCategory",
    "Port",
    "PortType",
]
