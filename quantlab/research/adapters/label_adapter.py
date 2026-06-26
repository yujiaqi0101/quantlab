"""
LabelAdapter — 旧 Label 体系到 LabelNode 的适配层

把 quantlab.ml.label.Label 包装成 ResearchNode，统一注册到 NodeRegistry。
"""
from __future__ import annotations

from typing import Any, List

import pandas as pd

from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeManifest, NodeMetadata
from ..node.ports import Port, PortType


class LabelAdapterNode(ResearchNode):
    """把旧 Label 包装成 ResearchNode。"""

    def __init__(self, label, version: str = "1.0.0") -> None:
        self._label = label
        self._id = f"label.{label.label_id}"
        self._version = version
        self._category = NodeCategory.LABEL
        self._inputs = [Port(name="close", type=PortType.FRAME, description="close 价格")]
        self._outputs = [Port(name=label.label_id, type=PortType.FRAME, description=label.description)]

    @property
    def id(self) -> str:
        return self._id

    @property
    def version(self) -> str:
        return self._version

    @property
    def category(self):
        return self._category

    @property
    def inputs(self):
        return self._inputs

    @property
    def outputs(self):
        return self._outputs

    def compute(self, ctx: Any) -> ResearchFrame:
        # 兼容多种 ctx 类型: dict / DatasetContext / ExecutionContext / ResearchFrame / DataFrame
        panel = None
        # 1. DatasetContext 直接有 panel 属性
        if hasattr(ctx, "panel"):
            panel = ctx.panel
        # 2. ResearchFrame 有 data 属性
        elif hasattr(ctx, "data") and isinstance(ctx.data, pd.DataFrame):
            panel = ctx.data
        # 3. dict-like
        elif hasattr(ctx, "get"):
            try:
                frame = ctx.get("frame")
                if frame is not None:
                    panel = frame.data if hasattr(frame, "data") else frame
            except (TypeError, KeyError):
                pass
        # 4. ExecutionContext 有 frame_store
        if panel is None and hasattr(ctx, "frame_store"):
            store = ctx.frame_store
            if hasattr(store, "get"):
                frame = store.get("frame")
                if frame is not None:
                    panel = frame.data if hasattr(frame, "data") else frame
        # 5. 直接是 DataFrame
        if panel is None and isinstance(ctx, pd.DataFrame):
            panel = ctx
        if panel is None:
            raise ValueError("LabelAdapterNode 需要 panel/frame 输入")
        # 调用旧 Label.generate
        series = self._label.generate(panel)
        # 输出为单列 ResearchFrame
        if isinstance(series, pd.Series):
            if isinstance(series.index, pd.MultiIndex):
                out_df = series.to_frame(name=self._label.label_id)
            else:
                # 单 index，需要重建 MultiIndex (与 panel 对齐)
                out_df = series.to_frame(name=self._label.label_id)
                out_df.index = panel.index
        else:
            out_df = pd.DataFrame({self._label.label_id: series}, index=panel.index)
        return ResearchFrame.from_panel(out_df, name=self._label.label_id)

    def manifest(self) -> NodeManifest:
        return NodeManifest(
            node_id=self.id,
            version=self.version,
            category=self.category,
            inputs=self.inputs,
            outputs=self.outputs,
            params={"label_id": self._label.label_id, "label_type": self._label.label_type},
            metadata=NodeMetadata(
                description=self._label.description,
                tags=["label", "adapted"],
            ),
        )


def register_labels_to_node_registry() -> int:
    """把所有旧 Label 注册为 LabelNode 到 NodeRegistry。"""
    from ...ml.label import get_label_registry
    from ..node.registry import get_registry

    reg = get_registry()
    label_reg = get_label_registry()
    count = 0
    for label in label_reg.list_labels():
        try:
            reg.register(LabelAdapterNode)
            count += 1
        except Exception:
            pass
    return count


__all__ = ["LabelAdapterNode", "register_labels_to_node_registry"]
