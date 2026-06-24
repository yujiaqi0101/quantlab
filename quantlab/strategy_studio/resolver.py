"""
DependencyResolver — 依赖解析器

职责：
  1. 解析 Strategy 的所有 ref 引用
  2. 构建依赖图（Strategy → Model → FeatureSet → Dataset 等）
  3. 验证依赖完整性（所有 ref 指向的 Package 是否存在）

依赖图示例：
  Strategy
    ├── Model (ref://Momentum_LGBM@1.2.0)
    │   ├── FeatureSet (ref://Momentum_v2@1.0)
    │   │   └── Dataset (ref://crypto_1h@1.0)
    │   └── LabelSet (ref://FutureReturn10@1.0)
    ├── Signal (ref://ProbabilitySignal@1.0)
    ├── Position (ref://VolatilitySizing@2.0)
    ├── Risk (ref://CryptoBasicRisk@1.1)
    ├── Execution (ref://PaperExecution@1.0)
    └── Observe (ref://StandardObserve@1.0)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..asset_package.base import PackageType, Ref, parse_ref
from ..asset_package.registry import PackageRegistry, get_package_registry
from ..asset_package.types import StrategyPackage

logger = logging.getLogger("quantlab.strategy_studio.resolver")


# ==================================================================
# 数据结构
# ==================================================================

@dataclass
class DependencyNode:
    """依赖图节点"""
    ref: str                           # ref://name@version
    pkg_type: PackageType              # Package 类型
    name: str
    version: str
    exists: bool = False              # 是否存在（已注册）
    children: List["DependencyNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref": self.ref,
            "type": self.pkg_type.value,
            "name": self.name,
            "version": self.version,
            "exists": self.exists,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class DependencyGraph:
    """依赖图"""
    root: DependencyNode               # Strategy 节点
    all_nodes: List[DependencyNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root.to_dict(),
            "all_refs": [n.ref for n in self.all_nodes],
            "missing_refs": [n.ref for n in self.all_nodes if not n.exists],
        }

    @property
    def is_complete(self) -> bool:
        """所有依赖是否都存在"""
        return all(n.exists for n in self.all_nodes)

    @property
    def missing_refs(self) -> List[str]:
        """缺失的 ref 列表"""
        return [n.ref for n in self.all_nodes if not n.exists]


@dataclass
class ValidationResult:
    """依赖验证结果"""
    passed: bool
    graph: DependencyGraph
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "graph": self.graph.to_dict(),
        }


# ==================================================================
# DependencyResolver
# ==================================================================

class DependencyResolver:
    """
    依赖解析器

    用法：
        resolver = DependencyResolver()
        graph = resolver.resolve(strategy)
        result = resolver.validate(graph)
        if result.passed:
            print("All dependencies OK")
    """

    def __init__(self, registry: Optional[PackageRegistry] = None) -> None:
        self.registry = registry or get_package_registry()

    def resolve(self, strategy: StrategyPackage) -> DependencyGraph:
        """
        解析策略的所有依赖，构建依赖图

        Strategy → Model / Signal / Position / Risk / Execution / Observe
        """
        all_nodes: List[DependencyNode] = []

        # Strategy 根节点
        root = DependencyNode(
            ref=f"ref://{strategy.name}@{strategy.version}",
            pkg_type=PackageType.STRATEGY,
            name=strategy.name,
            version=strategy.version,
            exists=True,  # Strategy 本身正在构建
        )

        # 直接依赖
        direct_deps = [
            (PackageType.MODEL, strategy.model_ref),
            (PackageType.SIGNAL, strategy.signal_ref),
            (PackageType.POSITION, strategy.position_ref),
            (PackageType.RISK, strategy.risk_ref),
            (PackageType.EXECUTION, strategy.execution_ref),
            (PackageType.OBSERVE, strategy.observe_ref),
        ]

        for pkg_type, ref_str in direct_deps:
            if not ref_str:
                logger.warning(f"Empty ref for {pkg_type.value} in strategy {strategy.name}")
                continue
            node = self._resolve_node(pkg_type, ref_str)
            root.children.append(node)
            all_nodes.append(node)

        return DependencyGraph(root=root, all_nodes=all_nodes)

    def _resolve_node(self, pkg_type: PackageType, ref_str: str) -> DependencyNode:
        """解析单个依赖节点"""
        ref = parse_ref(ref_str)
        exists = self.registry.exists(pkg_type, ref.name, ref.version)
        node = DependencyNode(
            ref=ref_str,
            pkg_type=pkg_type,
            name=ref.name,
            version=ref.version,
            exists=exists,
        )
        if not exists:
            logger.warning(f"Dependency not found: {ref_str}")
        return node

    def validate(self, graph: DependencyGraph) -> ValidationResult:
        """验证依赖完整性"""
        errors = []
        warnings = []

        if graph.is_complete:
            logger.info("All dependencies resolved successfully")
        else:
            for missing in graph.missing_refs:
                errors.append(f"Missing dependency: {missing}")
            logger.error(f"Missing dependencies: {graph.missing_refs}")

        return ValidationResult(
            passed=graph.is_complete,
            graph=graph,
            errors=errors,
            warnings=warnings,
        )
