"""
Adapters — 旧体系到新 ResearchNode 体系的适配层

  - LabelAdapter: 旧 Label → LabelNode
  - FeatureAdapter: 旧 Feature → ResearchNode (后续)
"""
from .label_adapter import LabelAdapterNode, register_labels_to_node_registry

__all__ = ["LabelAdapterNode", "register_labels_to_node_registry"]
