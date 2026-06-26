"""
Research API — Research Graph Studio 后端
============================================

暴露新 Research OS 生命周期接口：
  - Node Registry 查询
  - Graph CRUD
  - Compile / Execute / Cache
  - Materialize

端点 (前缀 /api/v1/research):
  GET  /nodes                 Node 列表 (?category=xxx)
  GET  /nodes/categories      分类列表
  GET  /nodes/{node_id}       Node 详情
  POST /graphs                创建 Graph
  GET  /graphs                Graph 列表
  GET  /graphs/{graph_id}     Graph 详情
  POST /graphs/{graph_id}/nodes    添加节点
  POST /graphs/{graph_id}/edges    添加边
  POST /graphs/{graph_id}/compile  编译
  POST /graphs/{graph_id}/execute  执行
  GET  /graphs/{graph_id}/cache    缓存查询
  POST /graphs/{graph_id}/invalidate 缓存失效
  POST /graphs/{graph_id}/materialize 生成训练数据集
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..research.graph import ResearchGraph
from ..research.node.registry import get_registry
from ..research.node.manifest import NodeCategory

logger = logging.getLogger("quantlab.api.research")

router = APIRouter(prefix="/api/v1/research", tags=["research"])


# ---------- 内存级 Graph 存储（生产可换 Redis/DB） ----------
_GRAPHS: Dict[str, ResearchGraph] = {}


# ---------- 请求/响应模型 ----------

class NodeInfoResponse(BaseModel):
    node_id: str
    version: str
    category: str
    description: str = ""
    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []


class CreateGraphRequest(BaseModel):
    name: str
    description: str = ""


class AddNodeRequest(BaseModel):
    node_id: str   # 已注册的 node id（直接引用）
    params: Dict[str, Any] = Field(default_factory=dict)


class AddEdgeRequest(BaseModel):
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str


class ExecuteRequest(BaseModel):
    dataset_id: str
    mode: str = "sequential"  # "sequential" | "parallel"


class MaterializeRequest(BaseModel):
    dataset_id: str
    label_node_id: str
    feature_node_ids: List[str] = Field(default_factory=list)  # 空=自动选非 label
    normalize: bool = True
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15


class CompileResponse(BaseModel):
    graph_id: str
    n_nodes: int
    n_edges: int
    topological_order: List[str]
    is_dag: bool = True


class ExecuteResponse(BaseModel):
    graph_id: str
    status: str = "ok"
    n_outputs: int
    outputs: Dict[str, Any] = {}
    executed: List[str] = []
    cached: List[str] = []


# ---------- 1. Node Registry ----------

@router.get("/nodes", response_model=List[NodeInfoResponse])
def list_nodes(category: Optional[str] = None) -> List[NodeInfoResponse]:
    """列出所有注册的 Node（可按 category 过滤）。"""
    reg = get_registry()
    items = reg.list_nodes()
    out = []
    cat_filter = NodeCategory(category) if category else None
    for item in items:
        cls = reg.get(item["id"], item["version"])
        if cls is None:
            continue
        try:
            inst = cls()
        except Exception:
            continue
        if cat_filter is not None and inst.category != cat_filter:
            continue
        m = inst.manifest()
        out.append(NodeInfoResponse(
            node_id=m.id,
            version=m.version,
            category=m.category.value if hasattr(m.category, "value") else str(m.category),
            description=m.metadata.description if m.metadata else "",
            inputs=[{"name": p.name, "type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in (inst.inputs or [])],
            outputs=[{"name": p.name, "type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in (inst.outputs or [])],
        ))
    return out


@router.get("/nodes/categories", response_model=List[str])
def list_node_categories() -> List[str]:
    """列出所有 Node 分类。"""
    return [c.value if hasattr(c, "value") else str(c) for c in NodeCategory]


@router.get("/nodes/{node_id}", response_model=NodeInfoResponse)
def get_node(node_id: str) -> NodeInfoResponse:
    """查询单个 Node 详情。"""
    reg = get_registry()
    cls = reg.get_latest(node_id)
    if cls is None:
        raise HTTPException(404, f"Node not found: {node_id}")
    try:
        inst = cls()
    except Exception as e:
        raise HTTPException(500, f"Instantiate failed: {e}")
    m = inst.manifest()
    return NodeInfoResponse(
        node_id=m.id,
        version=m.version,
        category=m.category.value if hasattr(m.category, "value") else str(m.category),
        description=m.metadata.description if m.metadata else "",
        inputs=[{"name": p.name, "type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in (inst.inputs or [])],
        outputs=[{"name": p.name, "type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in (inst.outputs or [])],
    )


# ---------- 2. Graph CRUD ----------

@router.post("/graphs")
def create_graph(req: CreateGraphRequest) -> Dict[str, Any]:
    """创建空 Graph。"""
    g = ResearchGraph(name=req.name)
    gid = f"graph-{uuid.uuid4().hex[:8]}"
    _GRAPHS[gid] = g
    return {"graph_id": gid, "name": req.name, "n_nodes": 0, "n_edges": 0}


@router.get("/graphs")
def list_graphs() -> List[Dict[str, Any]]:
    """列出所有 Graph。"""
    out = []
    for gid, g in _GRAPHS.items():
        out.append({
            "graph_id": gid,
            "name": g.name,
            "n_nodes": len(g.nodes()),
            "n_edges": len(g.edges()),
        })
    return out


@router.get("/graphs/{graph_id}")
def get_graph(graph_id: str) -> Dict[str, Any]:
    """Graph 详情。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    return {
        "graph_id": graph_id,
        "name": g.name,
        "nodes": [{"id": n.id, "category": str(n.category)} for n in g.nodes()],
        "edges": [
            {"src": e.source_node, "dst": e.target_node, "src_port": e.source_port, "dst_port": e.target_port}
            for e in g.edges()
        ],
    }


@router.post("/graphs/{graph_id}/nodes")
def add_node(graph_id: str, req: AddNodeRequest) -> Dict[str, Any]:
    """向 Graph 添加节点（从 Registry 实例化已注册节点类）。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    reg = get_registry()
    cls = reg.get_latest(req.node_id)
    if cls is None:
        raise HTTPException(404, f"Node not registered: {req.node_id}")
    try:
        inst = cls(**req.params) if req.params else cls()
    except Exception as e:
        raise HTTPException(400, f"Instantiate failed: {e}")
    try:
        g.add_node(inst)
    except Exception as e:
        raise HTTPException(400, f"Add node failed: {e}")
    return {"node_id": inst.id, "n_nodes": len(g.nodes())}


@router.post("/graphs/{graph_id}/edges")
def add_edge(graph_id: str, req: AddEdgeRequest) -> Dict[str, Any]:
    """向 Graph 添加边。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        g.add_edge(req.src_node, req.src_port, req.dst_node, req.dst_port)
    except Exception as e:
        raise HTTPException(400, f"Add edge failed: {e}")
    return {"n_edges": len(g.edges())}


# ---------- 3. Compile / Execute / Cache ----------

@router.post("/graphs/{graph_id}/compile", response_model=CompileResponse)
def compile_graph(graph_id: str) -> CompileResponse:
    """编译 Graph：拓扑排序 + DAG 校验。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        compiled = g.compile()
        order = list(compiled.topo_order) if hasattr(compiled, "topo_order") else list(g.node_ids())
        return CompileResponse(
            graph_id=graph_id,
            n_nodes=len(g.nodes()),
            n_edges=len(g.edges()),
            topological_order=order,
            is_dag=True,
        )
    except Exception as e:
        logger.warning(f"compile failed: {e}")
        return CompileResponse(
            graph_id=graph_id,
            n_nodes=len(g.nodes()),
            n_edges=len(g.edges()),
            topological_order=[],
            is_dag=False,
        )


@router.post("/graphs/{graph_id}/execute", response_model=ExecuteResponse)
def execute_graph(graph_id: str, req: ExecuteRequest) -> ExecuteResponse:
    """执行 Graph：加载 Dataset → 包装为 FrameStore → Executor。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        from ..research.context import ExecutionContext, FrameStore
        from ..research.executor import ResearchExecutor
        from ..ml.dataset import get_dataset_manager
        from ..research import ResearchFrame

        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(404, f"Dataset not found: {req.dataset_id}")

        panel = ds.get_data()
        frame = ResearchFrame.from_panel(panel)
        store = FrameStore()
        store.set("frame", frame)

        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store, mode=req.mode)

        outputs = {}
        for nid, rf in result.outputs.items():
            if hasattr(rf, "data") and isinstance(rf.data, pd.DataFrame):
                outputs[nid] = {"shape": list(rf.data.shape), "name": getattr(rf, "name", "")}
            else:
                outputs[nid] = {"value": str(rf)[:200]}

        return ExecuteResponse(
            graph_id=graph_id,
            status="error" if result.errors else "ok",
            n_outputs=len(outputs),
            outputs=outputs,
            executed=list(result.executed),
            cached=list(result.cached),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("execute_graph failed")
        raise HTTPException(500, f"Execute failed: {e}")


@router.get("/graphs/{graph_id}/cache")
def get_cache(graph_id: str) -> Dict[str, Any]:
    """查询 Graph 缓存状态（占位：返回节点列表）。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    return {
        "graph_id": graph_id,
        "nodes": [{"node_id": nid, "cached": False} for nid in g.node_ids()],
    }


@router.post("/graphs/{graph_id}/invalidate")
def invalidate_cache(graph_id: str) -> Dict[str, Any]:
    """失效 Graph 内所有节点缓存。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    n = 0
    try:
        from ..research.cache import get_cache_manager
        cm = get_cache_manager()
        for nid in g.node_ids():
            if hasattr(cm, "invalidate_node"):
                cm.invalidate_node(nid)
            n += 1
    except Exception as e:
        logger.warning(f"invalidate failed (ignored): {e}")
    return {"graph_id": graph_id, "invalidated": n}


# ---------- 4. Materialize ----------

@router.post("/graphs/{graph_id}/materialize")
def materialize(graph_id: str, req: MaterializeRequest) -> Dict[str, Any]:
    """完整流程：加载 → 执行 → Materialize → 返回统计。"""
    g = _GRAPHS.get(graph_id)
    if g is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        from ..research.context import FrameStore
        from ..research.executor import ResearchExecutor
        from ..research.materializer import Materializer, SplitConfig
        from ..ml.dataset import get_dataset_manager
        from ..research import ResearchFrame

        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(404, f"Dataset not found: {req.dataset_id}")

        panel = ds.get_data()
        frame = ResearchFrame.from_panel(panel)
        store = FrameStore()
        store.set("frame", frame)

        executor = ResearchExecutor()
        result = executor.execute(g, initial_store=store)

        if result.errors:
            raise HTTPException(500, f"Graph execution had errors: {result.errors}")

        # 选 label_frame
        if req.label_node_id not in result.outputs:
            raise HTTPException(400, f"Label node not in outputs: {req.label_node_id}")
        label_frame = result.outputs[req.label_node_id]

        # 选 feature_frames
        if req.feature_node_ids:
            feat_ids = req.feature_node_ids
        else:
            # 自动选：非 label 节点且输出是 FRAME 类
            feat_ids = [nid for nid in result.outputs.keys() if nid != req.label_node_id]
        feature_frames = {}
        for nid in feat_ids:
            if nid in result.outputs:
                feature_frames[nid] = result.outputs[nid]

        m = Materializer()
        split = SplitConfig(
            train_ratio=req.train_ratio,
            val_ratio=req.val_ratio,
            test_ratio=req.test_ratio,
        )
        tds = m.materialize(
            feature_frames=feature_frames,
            label_frame=label_frame,
            split_config=split,
            normalize=req.normalize,
        )
        return {
            "graph_id": graph_id,
            "n_features": len(tds.feature_names),
            "n_train": len(tds.X_train),
            "n_val": len(tds.X_val) if tds.X_val is not None else 0,
            "n_test": len(tds.X_test) if tds.X_test is not None else 0,
            "label_name": tds.label_name,
            "feature_names": tds.feature_names,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("materialize failed")
        raise HTTPException(500, f"Materialize failed: {e}")
