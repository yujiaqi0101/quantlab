"""
ResearchNode — 统一计算单元基类

采用能力接口 (capability interface)，非复杂继承树。
统一替代旧 quantlab.ml.feature.Feature (compute(df)->Series)
       与 quantlab.factor.FactorInfo (compute(ctx)->DataFrame)。

所有子类只需实现 compute()，其余能力按需覆写。
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .ports import Port, PortType
from .manifest import NodeCategory, NodeManifest, NodeMetadata

if TYPE_CHECKING:
    from ..frame import ResearchFrame


# ---------------------------------------------------------------------- #
# 辅助类型
# ---------------------------------------------------------------------- #
@dataclass
class CostEstimate:
    """节点计算成本估计"""
    stars: int = 1               # 1-5 星级，越高越昂贵
    time_complexity: str = "O(n)"  # 时间复杂度描述
    memory_mb: float = 0.0        # 估计内存占用

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stars": self.stars,
            "time_complexity": self.time_complexity,
            "memory_mb": self.memory_mb,
        }


@dataclass
class NodeDescription:
    """节点人可读描述"""
    summary: str = ""
    inputs_desc: Dict[str, str] = field(default_factory=dict)
    outputs_desc: Dict[str, str] = field(default_factory=dict)
    example: str = ""


class CachePolicy(str, Enum):
    """节点缓存策略"""
    NONE = "none"               # 不缓存
    MEMORY = "memory"          # L1 内存 (廉价、频繁复用)
    DISK = "disk"              # L2 磁盘 (昂贵、跨执行复用)
    RESEARCH_ASSET = "research_asset"  # L3 研究资产 (高价值、长期沉淀)


@dataclass
class Delta:
    """增量变更估计"""
    affected_range: Optional[str] = None   # 受影响时间范围
    recompute_ratio: float = 1.0            # 需重算比例 (0=无需, 1=全量)


# ---------------------------------------------------------------------- #
# ResearchNode 基类
# ---------------------------------------------------------------------- #
class ResearchNode(ABC):
    """
    所有研究节点的统一抽象 — Atomic Research Unit

    生命周期: Created → Validated → Compiled → Executed → Cached → Expired

    子类只需实现 compute()。能力方法 (supports_incremental 等) 按需覆写。
    """

    # ------------------------------------------------------------------ #
    # 身份 (子类可覆写为类属性或实例属性)
    # ------------------------------------------------------------------ #
    id: str = ""
    version: str = "1.0.0"
    category: NodeCategory = NodeCategory.CUSTOM

    # 输入输出端口声明
    inputs: List[Port] = []
    outputs: List[Port] = []

    # 参数与元信息
    parameters: Dict[str, Any] = {}
    metadata: NodeMetadata = NodeMetadata()

    def __init__(self, **params: Any) -> None:
        """
        子类可通过 __init__ 传入参数，或直接用类属性声明。

        示例:
            class RSI14(ResearchNode):
                id = "rsi14"
                category = NodeCategory.INDICATOR
                inputs = [Port(name="close", type=PortType.FRAME)]
                outputs = [Port(name="rsi", type=PortType.FRAME)]

                def compute(self, ctx):
                    close = ctx.frame_store.get("close")
                    ...
        """
        # 合并传入参数到 parameters
        if params:
            base = dict(self.parameters) if self.parameters else {}
            base.update(params)
            self.parameters = base
        # 确保 id 非空
        if not self.id:
            cls_name = self.__class__.__name__.lower()
            self.id = cls_name

    # ------------------------------------------------------------------ #
    # 生命周期方法 (部分抽象，部分有默认实现)
    # ------------------------------------------------------------------ #
    def validate(self, schema: Optional[Dict[str, Any]] = None) -> bool:
        """校验输入 schema 是否满足声明的 required 端口。"""
        if schema is None:
            return True
        available = set(schema.get("ports", []) or schema.get("columns", []))
        for port in self.inputs:
            if port.required and port.name not in available:
                return False
        return True

    def fingerprint(self) -> str:
        """基于 id+version+params+代码 计算稳定指纹 (用于缓存 key)。"""
        h = hashlib.sha256()
        h.update(self.id.encode("utf-8"))
        h.update(self.version.encode("utf-8"))
        params_str = json.dumps(self.parameters, sort_keys=True, ensure_ascii=False, default=str)
        h.update(params_str.encode("utf-8"))
        # 类名作为代码身份的一部分
        h.update(self.__class__.__name__.encode("utf-8"))
        return h.hexdigest()[:16]

    def estimate_cost(self) -> CostEstimate:
        """估计计算成本。默认 1 星。子类可覆写。"""
        return CostEstimate(stars=self.metadata.cost)

    def describe(self) -> NodeDescription:
        """人可读描述。"""
        return NodeDescription(
            summary=self.metadata.description or self.id,
            inputs_desc={p.name: p.description for p in self.inputs},
            outputs_desc={p.name: p.description for p in self.outputs},
        )

    @abstractmethod
    def compute(self, ctx: Any) -> "ResearchFrame":
        """
        核心计算 — 子类必须实现。

        Args:
            ctx: ExecutionContext (在 executor.py 定义)
                - ctx.frame_store.get(port_name) → 上游 ResearchFrame
                - ctx.dataset_ctx.get_column("close") → 原始数据
                - ctx.cache → CacheManager
                - ctx.logger → Logger
        Returns:
            ResearchFrame
        """
        ...

    # ------------------------------------------------------------------ #
    # 能力声明 (默认全部 False/NONE，子类按需覆写)
    # ------------------------------------------------------------------ #
    def supports_incremental(self) -> bool:
        """是否支持增量计算。"""
        return False

    def supports_parallel(self) -> bool:
        """是否可并行执行。"""
        return False

    def supports_gpu(self) -> bool:
        """是否可用 GPU 加速。"""
        return False

    def cache_policy(self) -> CachePolicy:
        """缓存策略。默认 L1 内存。"""
        return CachePolicy.MEMORY

    # ------------------------------------------------------------------ #
    # 增量能力 (supports_incremental=True 时子类实现)
    # ------------------------------------------------------------------ #
    def update(self, ctx: Any, changeset: Any) -> "ResearchFrame":
        """增量计算。默认抛出 NotImplementedError。"""
        raise NotImplementedError(
            f"{self.id} does not support incremental. "
            "Override update() and set supports_incremental()=True."
        )

    def save_state(self, store: Any) -> None:
        """保存有状态节点的计算状态。"""
        pass

    def load_state(self, store: Any) -> None:
        """加载有状态节点的计算状态。"""
        pass

    def invalidate(self, dirty_range: Any) -> None:
        """标记脏范围。"""
        pass

    def estimate_delta(self, changeset: Any) -> Delta:
        """估计增量变更影响。默认全量重算。"""
        return Delta(recompute_ratio=1.0)

    # ------------------------------------------------------------------ #
    # Manifest 生成
    # ------------------------------------------------------------------ #
    def manifest(self) -> NodeManifest:
        """生成节点清单 (可序列化、可持久化)。"""
        return NodeManifest(
            id=self.id,
            version=self.version,
            category=self.category,
            inputs=list(self.inputs),
            outputs=list(self.outputs),
            params=dict(self.parameters),
            metadata=self.metadata,
            fingerprint_basis=self.fingerprint(),
            deprecated=self.metadata.deprecated,
        )

    # ------------------------------------------------------------------ #
    # 便捷
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "category": self.category.value,
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "parameters": dict(self.parameters),
            "metadata": self.metadata.to_dict(),
            "fingerprint": self.fingerprint(),
            "capabilities": {
                "incremental": self.supports_incremental(),
                "parallel": self.supports_parallel(),
                "gpu": self.supports_gpu(),
                "cache_policy": self.cache_policy().value,
            },
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, version={self.version!r}, category={self.category.value})"
