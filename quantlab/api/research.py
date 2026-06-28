"""
Research API — Research Graph Studio 后端
============================================

对接前端 researchGraph.ts：
  - Node Registry 查询
  - Graph CRUD（创建/查询/节点/边/删除）
  - Compile / Execute
  - Cache 管理
  - Materialize（生成训练集）

端点 (前缀 /api/v1/research):
  GET  /nodes                      Node 列表 (?category=xxx)
  GET  /nodes/categories           分类列表
  GET  /nodes/{node_id}            Node 详情
  POST /graphs                     创建 Graph
  GET  /graphs                     Graph 列表
  GET  /graphs/{graph_id}          Graph 详情
  DELETE /graphs/{graph_id}        删除 Graph
  POST /graphs/{graph_id}/nodes    添加节点
  DELETE /graphs/{graph_id}/nodes/{node_id}  删除节点
  POST /graphs/{graph_id}/edges    添加边
  DELETE /graphs/{graph_id}/edges  删除边
  POST /graphs/{graph_id}/compile  编译
  POST /graphs/{graph_id}/execute  执行
  GET  /cache/stats                全局缓存统计
  POST /cache/invalidate           缓存失效
  POST /graphs/{graph_id}/materialize 生成训练数据集
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..research.graph import ResearchGraph
from ..research.node.registry import get_registry
from ..research.node.manifest import NodeCategory, NodeManifest

logger = logging.getLogger("quantlab.api.research")

router = APIRouter(prefix="/api/v1/research", tags=["research"])


class GraphState:
    """包装 ResearchGraph 及元数据"""

    def __init__(self, name: str, description: str = ""):
        self.graph_id = f"graph-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.description = description
        self.graph = ResearchGraph(name=name)
        self.node_types: Dict[str, str] = {}
        self.node_params: Dict[str, Dict[str, Any]] = {}
        self.node_versions: Dict[str, str] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def touch(self):
        self.updated_at = datetime.now(timezone.utc).isoformat()


_GRAPHS: Dict[str, GraphState] = {}


def _node_manifest_to_dict(m: NodeManifest) -> Dict[str, Any]:
    return {
        "id": m.id,
        "version": m.version,
        "category": m.category.value if hasattr(m.category, "value") else str(m.category),
        "inputs": [{"name": p.name, "port_type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in m.inputs],
        "outputs": [{"name": p.name, "port_type": p.type.value if hasattr(p.type, "value") else str(p.type)} for p in m.outputs],
        "params_schema": m.params,
        "metadata": {
            "description": m.metadata.description,
            "author": m.metadata.author,
            "cost": m.metadata.cost,
            "deprecated": m.metadata.deprecated,
            "tags": list(m.metadata.tags),
        },
    }


def _graph_to_dict(state: GraphState) -> Dict[str, Any]:
    nodes = []
    for nid in state.graph.node_ids():
        nodes.append({
            "node_id": nid,
            "node_type": state.node_types.get(nid, ""),
            "version": state.node_versions.get(nid, "1.0.0"),
            "params": state.node_params.get(nid, {}),
        })
    edges = []
    for e in state.graph.edges():
        edges.append({
            "src_node": e.source_node,
            "src_port": e.source_port,
            "dst_node": e.target_node,
            "dst_port": e.target_port,
        })
    return {
        "graph_id": state.graph_id,
        "name": state.name,
        "description": state.description,
        "nodes": nodes,
        "edges": edges,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


# ---------- 请求/响应模型 ----------

class CreateGraphRequest(BaseModel):
    name: str
    description: str = ""


class AddNodeRequest(BaseModel):
    node_id: str
    node_type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class AddEdgeRequest(BaseModel):
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str


class ExecuteRequest(BaseModel):
    dataset_id: str
    mode: str = "sequential"


class InvalidateCacheRequest(BaseModel):
    node_id: Optional[str] = None


class MaterializeRequest(BaseModel):
    dataset_id: str
    label_node_id: str
    feature_node_ids: List[str] = Field(default_factory=list)
    normalize: bool = True
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15


# ---------- 1. Node Registry ----------

@router.get("/nodes")
def list_nodes(category: Optional[str] = None) -> List[Dict[str, Any]]:
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
        out.append(_node_manifest_to_dict(m))
    return out


@router.get("/nodes/categories")
def list_node_categories() -> List[str]:
    return [c.value if hasattr(c, "value") else str(c) for c in NodeCategory]


@router.get("/nodes/{node_id}")
def get_node(node_id: str, version: Optional[str] = None) -> Dict[str, Any]:
    reg = get_registry()
    if version:
        cls = reg.get(node_id, version)
    else:
        cls = reg.get_latest(node_id)
    if cls is None:
        raise HTTPException(404, f"Node not found: {node_id}")
    try:
        inst = cls()
    except Exception as e:
        raise HTTPException(500, f"Instantiate failed: {e}")
    m = inst.manifest()
    return _node_manifest_to_dict(m)


# ---------- 2. Graph CRUD ----------

@router.post("/graphs")
def create_graph(req: CreateGraphRequest) -> Dict[str, Any]:
    state = GraphState(name=req.name, description=req.description)
    _GRAPHS[state.graph_id] = state
    return _graph_to_dict(state)


@router.get("/graphs")
def list_graphs() -> List[Dict[str, Any]]:
    return [_graph_to_dict(s) for s in _GRAPHS.values()]


@router.get("/graphs/{graph_id}")
def get_graph(graph_id: str) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    return _graph_to_dict(state)


@router.delete("/graphs/{graph_id}")
def delete_graph(graph_id: str) -> Dict[str, Any]:
    if graph_id not in _GRAPHS:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    del _GRAPHS[graph_id]
    return {"ok": True}


@router.post("/graphs/{graph_id}/nodes")
def add_node(graph_id: str, req: AddNodeRequest) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    reg = get_registry()
    cls = reg.get_latest(req.node_type)
    if cls is None:
        raise HTTPException(404, f"Node type not registered: {req.node_type}")
    try:
        inst = cls(**req.params) if req.params else cls()
    except Exception as e:
        raise HTTPException(400, f"Instantiate failed: {e}")
    inst.id = req.node_id
    try:
        state.graph.add_node(inst)
    except Exception as e:
        raise HTTPException(400, f"Add node failed: {e}")
    state.node_types[req.node_id] = req.node_type
    state.node_params[req.node_id] = dict(req.params)
    state.node_versions[req.node_id] = inst.version
    state.touch()
    return {"ok": True}


@router.delete("/graphs/{graph_id}/nodes/{node_id}")
def remove_node(graph_id: str, node_id: str) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        state.graph.remove_node(node_id)
    except Exception as e:
        raise HTTPException(400, f"Remove node failed: {e}")
    state.node_types.pop(node_id, None)
    state.node_params.pop(node_id, None)
    state.node_versions.pop(node_id, None)
    state.touch()
    return {"ok": True}


@router.post("/graphs/{graph_id}/edges")
def add_edge(graph_id: str, req: AddEdgeRequest) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        state.graph.add_edge(req.src_node, req.src_port, req.dst_node, req.dst_port)
    except Exception as e:
        raise HTTPException(400, f"Add edge failed: {e}")
    state.touch()
    return {"ok": True}


@router.delete("/graphs/{graph_id}/edges")
def remove_edge(
    graph_id: str,
    src_node: str = Query(...),
    src_port: str = Query(...),
    dst_node: str = Query(...),
    dst_port: str = Query(...),
) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    try:
        state.graph.remove_edge(src_node, src_port, dst_node, dst_port)
    except Exception as e:
        raise HTTPException(400, f"Remove edge failed: {e}")
    state.touch()
    return {"ok": True}


# ---------- 3. Compile / Execute / Cache ----------

@router.post("/graphs/{graph_id}/compile")
def compile_graph(graph_id: str) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    errors: List[str] = []
    warnings: List[str] = []
    topo_order: List[str] = []
    ok = True
    try:
        compiled = state.graph.compile()
        topo_order = list(compiled.topo_order)
    except Exception as e:
        ok = False
        errors.append(str(e))
        logger.warning(f"compile failed: {e}")
    return {
        "graph_id": graph_id,
        "ok": ok,
        "topological_order": topo_order,
        "errors": errors,
        "warnings": warnings,
    }


@router.post("/graphs/{graph_id}/execute")
def execute_graph(graph_id: str, req: ExecuteRequest) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
        raise HTTPException(404, f"Graph not found: {graph_id}")
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    start = time.time()
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
        result = executor.execute(state.graph, initial_store=store, mode=req.mode)

        outputs: Dict[str, Any] = {}
        for nid, rf in result.outputs.items():
            if hasattr(rf, "data") and isinstance(rf.data, pd.DataFrame):
                outputs[nid] = {"shape": list(rf.data.shape), "name": getattr(rf, "name", "")}
            else:
                outputs[nid] = {"value": str(rf)[:200]}

        duration_ms = int((time.time() - start) * 1000)
        status = "ERROR" if result.errors else "OK"

        return {
            "run_id": run_id,
            "graph_id": graph_id,
            "status": status,
            "outputs": outputs,
            "executed_nodes": list(result.executed),
            "cached_nodes": list(result.cached),
            "errors": dict(result.errors),
            "duration_ms": duration_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("execute_graph failed")
        duration_ms = int((time.time() - start) * 1000)
        return {
            "run_id": run_id,
            "graph_id": graph_id,
            "status": "ERROR",
            "outputs": {},
            "executed_nodes": [],
            "cached_nodes": [],
            "errors": {"_global": str(e)},
            "duration_ms": duration_ms,
        }


@router.get("/cache/stats")
def get_cache_stats(graph_id: Optional[str] = None) -> Dict[str, Any]:
    total_entries = 0
    total_size = 0
    total_hits = 0
    total_misses = 0
    by_level: Dict[str, Dict[str, int]] = {
        "memory": {"count": 0, "size_bytes": 0},
        "parquet": {"count": 0, "size_bytes": 0},
        "featurestore": {"count": 0, "size_bytes": 0},
    }
    try:
        from ..research.cache import get_cache_manager
        cm = get_cache_manager()
        if hasattr(cm, "stats"):
            s = cm.stats()
            mem = s.get("memory")
            if mem:
                by_level["memory"]["count"] = mem.get("entries", 0)
                total_entries += mem.get("entries", 0)
                total_hits += mem.get("hits", 0)
                total_misses += mem.get("misses", 0)
            pq = s.get("parquet")
            if pq:
                by_level["parquet"]["count"] = pq.get("entries", 0)
                by_level["parquet"]["size_bytes"] = pq.get("total_bytes", 0)
                total_entries += pq.get("entries", 0)
                total_size += pq.get("total_bytes", 0)
                total_hits += pq.get("hits", 0)
                total_misses += pq.get("misses", 0)
            manifest_n = s.get("manifest_entries", 0)
            if manifest_n > total_entries:
                total_entries = manifest_n
    except Exception as e:
        logger.debug(f"cache stats unavailable: {e}")
    total_access = total_hits + total_misses
    hit_rate = (total_hits / total_access) if total_access > 0 else 0.0
    return {
        "total_entries": total_entries,
        "total_size_bytes": total_size,
        "hit_rate": hit_rate,
        "by_level": by_level,
    }


@router.post("/cache/invalidate")
def invalidate_cache(req: Optional[InvalidateCacheRequest] = None) -> Dict[str, Any]:
    n = 0
    try:
        from ..research.cache import get_cache_manager
        cm = get_cache_manager()
        node_id = req.node_id if req else None
        if node_id and hasattr(cm, "invalidate_node"):
            cm.invalidate_node(node_id)
            n = 1
        elif hasattr(cm, "invalidate_all"):
            n = cm.invalidate_all()
    except Exception as e:
        logger.warning(f"invalidate failed (ignored): {e}")
    return {"invalidated": n}


# ---------- 4. Materialize ----------

@router.post("/graphs/{graph_id}/materialize")
def materialize(graph_id: str, req: MaterializeRequest) -> Dict[str, Any]:
    state = _GRAPHS.get(graph_id)
    if state is None:
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
        result = executor.execute(state.graph, initial_store=store)

        if result.errors:
            raise HTTPException(500, f"Graph execution had errors: {result.errors}")

        if req.label_node_id not in result.outputs:
            raise HTTPException(400, f"Label node not in outputs: {req.label_node_id}")
        label_frame = result.outputs[req.label_node_id]

        if req.feature_node_ids:
            feat_ids = req.feature_node_ids
        else:
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
