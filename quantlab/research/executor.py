"""
ResearchExecutor — 研究图执行引擎

职责：
  1. 接收 CompiledGraph 或 ResearchGraph，拓扑序遍历
  2. 缓存检查 (L1 Execution Cache：同一执行内同节点只算一次)
  3. 调用 Node.compute(ctx)，将输出写入 frame_store
  4. 按 port 名传递 ResearchFrame 到下游节点的输入端口
  5. 支持并行执行同层无依赖节点 (mode="parallel")
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .context import ExecutionContext, FrameStore
from .frame import ResearchFrame
from .graph import CompiledGraph, ResearchGraph
from .node.base import ResearchNode

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """执行结果。"""

    outputs: Dict[str, ResearchFrame] = field(default_factory=dict)
    node_count: int = 0
    executed: List[str] = field(default_factory=list)
    cached: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    def get(self, node_id: str) -> Optional[ResearchFrame]:
        return self.outputs.get(node_id)


class ResearchExecutor:
    """研究图执行器。"""

    def __init__(self, max_workers: int = 4, verbose: bool = False) -> None:
        self.max_workers = max_workers
        self.verbose = verbose
        if verbose:
            logging.basicConfig(level=logging.INFO)

    def execute(
        self,
        graph: ResearchGraph,
        initial_store: Optional[FrameStore] = None,
        mode: str = "sequential",
    ) -> ExecutionResult:
        """执行图。

        Args:
            graph       : ResearchGraph
            initial_store : 初始 FrameStore (上游节点已写入的数据)
            mode        : "sequential" | "parallel"
        """
        compiled = graph.compile()
        return self._execute_compiled(graph, compiled, initial_store, mode)

    def execute_compiled(
        self,
        graph: ResearchGraph,
        compiled: CompiledGraph,
        initial_store: Optional[FrameStore] = None,
        mode: str = "sequential",
    ) -> ExecutionResult:
        return self._execute_compiled(graph, compiled, initial_store, mode)

    def _execute_compiled(
        self,
        graph: ResearchGraph,
        compiled: CompiledGraph,
        initial_store: Optional[FrameStore],
        mode: str,
    ) -> ExecutionResult:
        ctx = ExecutionContext(frame_store=initial_store)
        result = ExecutionResult(node_count=compiled.node_count)

        for layer in compiled.execution_plan:
            if mode == "parallel" and len(layer) > 1:
                self._execute_layer_parallel(graph, layer, ctx, result)
            else:
                for node_id in layer:
                    self._execute_node(graph, node_id, ctx, result)

        return result

    def _execute_layer_parallel(
        self,
        graph: ResearchGraph,
        layer: List[str],
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """并行执行同层节点。"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._compute_node, graph, nid, ctx): nid for nid in layer
            }
            for future in as_completed(futures):
                nid = futures[future]
                try:
                    frame = future.result()
                    self._publish_output(graph, nid, frame, ctx, result)
                except Exception as e:
                    result.errors[nid] = str(e)
                    logger.error("node %s failed: %s", nid, e)

    def _execute_node(
        self,
        graph: ResearchGraph,
        node_id: str,
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        try:
            frame = self._compute_node(graph, node_id, ctx)
            self._publish_output(graph, node_id, frame, ctx, result)
        except Exception as e:
            result.errors[node_id] = str(e)
            logger.error("node %s failed: %s", node_id, e)

    def _compute_node(
        self, graph: ResearchGraph, node_id: str, ctx: ExecutionContext
    ) -> ResearchFrame:
        """调用 node.compute(ctx)，L1 Execution Cache 生效。"""
        # L1 cache: 同一执行内缓存
        if node_id in ctx._cached_outputs:
            return ctx._cached_outputs[node_id]
        node = graph.get_node(node_id)
        if node is None:
            raise RuntimeError(f"node not found: {node_id}")
        frame = node.compute(ctx)
        ctx._cached_outputs[node_id] = frame
        return frame

    def _publish_output(
        self,
        graph: ResearchGraph,
        node_id: str,
        frame: ResearchFrame,
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """把节点输出按 port 名写入 frame_store，供下游节点消费。"""
        node = graph.get_node(node_id)
        result.outputs[node_id] = frame
        if node_id not in ctx._cached_outputs:
            ctx._cached_outputs[node_id] = frame
        # 默认行为：把节点每个 output port 写入 frame_store[port_name]
        for port in node.outputs:
            ctx.frame_store.set(port.name, frame)
        # 按边精确转发：source_node:source_port -> target_node:target_port
        # 这里简化：port 名一致即转发 (后续可支持 alias)
        result.executed.append(node_id)
        if self.verbose:
            logger.info("executed node: %s", node_id)
