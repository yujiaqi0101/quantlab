"""
Alpha Factory API — V3.0

端点：
  GET  /api/v1/alpha/overview              全局概览
  POST /api/v1/alpha/generate              批量生成 Alpha
  GET  /api/v1/alpha/list                  列出 Alpha
  GET  /api/v1/alpha/search                搜索 Alpha
  GET  /api/v1/alpha/leaderboard           排行榜
  GET  /api/v1/alpha/{id}                  Alpha 详情
  DELETE /api/v1/alpha/{id}                删除 Alpha
  POST /api/v1/alpha/evaluate              批量评估
  POST /api/v1/alpha/screen                筛选候选
  GET  /api/v1/alpha/pool                  候选池
  POST /api/v1/alpha/pool/promote/{id}     提升为生产
  POST /api/v1/alpha/correlation           相关性矩阵
  POST /api/v1/alpha/decay/{id}            衰减分析
  POST /api/v1/alpha/combine               组合 Alpha
  POST /api/v1/alpha/portfolio             组合构建
  PUT  /api/v1/alpha/{id}/status           更新状态
  PUT  /api/v1/alpha/{id}/tags             更新标签
  PUT  /api/v1/alpha/{id}/note             更新备注
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ..services import get_service

router = APIRouter(prefix="/api/v1/alpha", tags=["alpha"])


def _svc():
    return get_service("alpha")


# ---- Pydantic 模型 ----

class GenerateRequest(BaseModel):
    factor_name: str = Field(..., description="因子名称")
    methods: Optional[List[str]] = Field(None, description="生成方法: threshold/crossover/zero_cross")


class GenerateBatchRequest(BaseModel):
    factor_names: List[str] = Field(..., description="因子名称列表")
    methods: Optional[List[str]] = Field(None, description="生成方法")


class EvaluateRequest(BaseModel):
    factor_name: Optional[str] = Field(None, description="限定因子")
    dataset_id: Optional[str] = Field(None, description="数据集 ID")


class ScreenRequest(BaseModel):
    ic_min: float = Field(0.03, description="IC 下限")
    ir_min: float = Field(0.5, description="IR 下限")
    coverage_min: float = Field(0.05, description="覆盖率下限")


class CorrelationRequest(BaseModel):
    alpha_ids: Optional[List[str]] = Field(None, description="Alpha ID 列表")
    method: str = Field("spearman", description="相关系数方法")
    threshold: float = Field(0.8, description="冗余阈值")


class DecayRequest(BaseModel):
    periods: Optional[List[int]] = Field(None, description="前瞻周期")


class CombineRequest(BaseModel):
    alpha_ids: List[str] = Field(..., description="要组合的 Alpha ID")
    method: str = Field("weighted", description="组合方法: and/or/weighted/majority")
    weights: Optional[Dict[str, float]] = Field(None, description="权重")
    name: Optional[str] = Field(None, description="组合名称")


class PortfolioRequest(BaseModel):
    method: str = Field("ic_weight", description="权重方法: equal/ic_weight/score_weight")
    max_alphas: int = Field(20, description="最多 Alpha 数")


class StatusRequest(BaseModel):
    status: str = Field(..., description="状态: draft/evaluated/candidate/production/archived")


class TagsRequest(BaseModel):
    tags: List[str] = Field(..., description="标签列表")


class NoteRequest(BaseModel):
    note: str = Field(..., description="备注")


# ---- V3.0 Alpha Graph ----

class EvolveRequest(BaseModel):
    parent_alpha_id: str = Field(..., description="父 Alpha ID")
    mutations: Optional[List[str]] = Field(None, description="变异类型: threshold/window/operator")

class EvolveBatchRequest(BaseModel):
    alpha_ids: List[str] = Field(..., description="父 Alpha ID 列表")
    mutations: Optional[List[str]] = Field(None, description="变异类型")

class ClusterRequest(BaseModel):
    n_clusters: Optional[int] = Field(None, description="簇数（None 自动确定）")
    method: str = Field("genome", description="聚类方法: kmeans/hierarchical/genome")


# ---- 端点 ----

@router.get("/overview")
async def api_get_overview() -> Dict[str, Any]:
    """全局概览"""
    return _svc().get_overview()


@router.post("/generate")
async def api_generate(req: GenerateRequest) -> List[Dict[str, Any]]:
    """从因子批量生成 Alpha"""
    return _svc().generate_alphas(req.factor_name, req.methods)


@router.post("/generate/batch")
async def api_generate_batch(req: GenerateBatchRequest) -> Dict[str, List[Dict[str, Any]]]:
    """批量生成"""
    return _svc().generate_batch(req.factor_names, req.methods)


@router.get("/list")
async def api_list_alphas(
    status: Optional[str] = Query(None, description="按状态过滤"),
    factor_name: Optional[str] = Query(None, description="按因子过滤"),
    limit: int = Query(100, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """列出 Alpha"""
    return _svc().list_alphas(status=status, factor_name=factor_name, limit=limit)


@router.get("/search")
async def api_search_alphas(
    q: str = Query("", description="模糊搜索"),
    ic_min: Optional[float] = Query(None, description="IC 下限"),
    ir_min: Optional[float] = Query(None, description="IR 下限"),
    coverage_min: Optional[float] = Query(None, description="覆盖率下限"),
    score_min: Optional[float] = Query(None, description="评分下限"),
    limit: int = Query(100, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """搜索 Alpha"""
    return _svc().search_alphas(
        q=q, ic_min=ic_min, ir_min=ir_min,
        coverage_min=coverage_min, score_min=score_min, limit=limit,
    )


@router.get("/leaderboard")
async def api_get_leaderboard(
    metric: str = Query("score", description="排名指标: score/ic/ir/coverage/sharpe"),
    limit: int = Query(20, description="返回数量"),
    factor_name: Optional[str] = Query(None, description="限定因子"),
) -> List[Dict[str, Any]]:
    """排行榜"""
    return _svc().get_leaderboard(metric=metric, limit=limit, factor_name=factor_name)


@router.get("/{alpha_id}")
async def api_get_alpha(alpha_id: str) -> Dict[str, Any]:
    """Alpha 详情"""
    result = _svc().get_alpha(alpha_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return result


@router.delete("/{alpha_id}")
async def api_delete_alpha(alpha_id: str) -> Dict[str, str]:
    """删除 Alpha"""
    ok = _svc().delete_alpha(alpha_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return {"status": "deleted", "id": alpha_id}


@router.post("/screen")
async def api_screen_candidates(req: ScreenRequest) -> List[Dict[str, Any]]:
    """筛选候选"""
    return _svc().screen_candidates(
        ic_min=req.ic_min, ir_min=req.ir_min, coverage_min=req.coverage_min,
    )


@router.get("/pool")
async def api_get_pool(
    factor_name: Optional[str] = Query(None, description="按因子过滤"),
    limit: int = Query(100, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """候选池"""
    return _svc().get_candidates(factor_name=factor_name, limit=limit)


@router.get("/pool/stats")
async def api_get_pool_stats() -> Dict[str, Any]:
    """候选池统计"""
    return _svc().get_pool_stats()


@router.post("/pool/promote/{alpha_id}")
async def api_promote_alpha(alpha_id: str) -> Dict[str, Any]:
    """提升为生产"""
    ok = _svc().promote_alpha(alpha_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return {"alpha_id": alpha_id, "status": "production"}


@router.post("/combine")
async def api_combine_alphas(req: CombineRequest) -> Dict[str, Any]:
    """组合 Alpha"""
    return _svc().combine_alphas(
        alpha_ids=req.alpha_ids,
        method=req.method,
        weights=req.weights,
        name=req.name,
    )


@router.post("/portfolio")
async def api_construct_portfolio(req: PortfolioRequest) -> Dict[str, Any]:
    """组合构建"""
    return _svc().construct_portfolio(method=req.method, max_alphas=req.max_alphas)


@router.put("/{alpha_id}/status")
async def api_set_status(alpha_id: str, req: StatusRequest) -> Dict[str, Any]:
    """更新状态"""
    ok = _svc().update_alpha_status(alpha_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return {"alpha_id": alpha_id, "status": req.status}


@router.put("/{alpha_id}/tags")
async def api_set_tags(alpha_id: str, req: TagsRequest) -> Dict[str, Any]:
    """更新标签"""
    ok = _svc().update_alpha_tags(alpha_id, req.tags)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return {"alpha_id": alpha_id, "tags": req.tags}


@router.put("/{alpha_id}/note")
async def api_set_note(alpha_id: str, req: NoteRequest) -> Dict[str, Any]:
    """更新备注"""
    ok = _svc().update_alpha_note(alpha_id, req.note)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return {"alpha_id": alpha_id, "note": req.note}


# ---- V3.0 Alpha Graph 端点 ----

@router.get("/graph/{alpha_id}/genome")
async def api_get_genome(alpha_id: str) -> Dict[str, Any]:
    """获取 Alpha 基因组"""
    result = _svc().get_genome(alpha_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alpha '{alpha_id}' not found")
    return result


@router.get("/graph/diff")
async def api_diff_genomes(
    alpha_id_1: str = Query(..., description="Alpha ID 1"),
    alpha_id_2: str = Query(..., description="Alpha ID 2"),
) -> Dict[str, Any]:
    """比较两个 Alpha 基因组差异"""
    result = _svc().diff_genomes(alpha_id_1, alpha_id_2)
    if result is None:
        raise HTTPException(status_code=404, detail="Alpha not found")
    return result


@router.get("/graph/{alpha_id}/similar")
async def api_find_similar(
    alpha_id: str,
    threshold: float = Query(0.8, description="相似度阈值"),
) -> List[Dict[str, Any]]:
    """找出与目标 Alpha 相似的其他 Alpha"""
    return _svc().find_similar_alphas(alpha_id, threshold)


@router.post("/graph/cluster")
async def api_cluster_alphas(req: ClusterRequest) -> Dict[str, Any]:
    """聚类 Alpha → Alpha 家族"""
    return _svc().cluster_alphas(n_clusters=req.n_clusters, method=req.method)


@router.get("/graph/{alpha_id}/ancestors")
async def api_get_ancestors(alpha_id: str) -> List[Dict[str, Any]]:
    """获取 Alpha 祖先链"""
    return _svc().get_ancestors(alpha_id)


@router.get("/graph/{alpha_id}/children")
async def api_get_children(alpha_id: str) -> List[Dict[str, Any]]:
    """获取 Alpha 子节点"""
    return _svc().get_children(alpha_id)


@router.get("/graph/{alpha_id}/tree")
async def api_get_family_tree(alpha_id: str) -> Dict[str, Any]:
    """获取 Family Tree"""
    return _svc().get_family_tree(alpha_id)


@router.get("/graph/data")
async def api_get_graph_data(
    alpha_ids: Optional[str] = Query(None, description="Alpha ID 列表（逗号分隔）"),
) -> Dict[str, Any]:
    """获取图可视化数据（节点 + 边）"""
    ids = alpha_ids.split(",") if alpha_ids else None
    return _svc().get_graph_data(ids)


@router.get("/graph/stats")
async def api_get_lineage_stats() -> Dict[str, Any]:
    """血缘统计"""
    return _svc().get_lineage_stats()


@router.post("/graph/evolve")
async def api_evolve_alpha(req: EvolveRequest) -> Dict[str, Any]:
    """进化单个 Alpha（自动变异 + 评估）"""
    # 注意：实际使用需要 factor_data 和 price_df，这里仅创建变异 Alpha
    # 完整评估需要通过 Jupyter/CLI 传入数据
    from ..research.alpha_graph.genome import AlphaGenome
    from ..research.alpha.alpha import Alpha
    alpha = _svc()._store.get(req.parent_alpha_id)
    if alpha is None:
        raise HTTPException(status_code=404, detail=f"Alpha '{req.parent_alpha_id}' not found")

    genome = AlphaGenome.from_alpha(alpha)
    mutations = req.mutations or ["threshold", "window"]

    child_genomes = []
    for m in mutations:
        if m == "threshold":
            child_genomes.extend(genome.mutate_threshold())
        elif m == "window":
            child_genomes.extend(genome.mutate_window())
        elif m == "operator":
            child_genomes.extend(genome.mutate_operator())

    children = []
    for g in child_genomes:
        child = g.to_alpha()
        if child.name and child.factor_name:
            children.append(child)

    _svc()._store.save_batch(children)

    # 记录血缘
    for child in children:
        _svc()._lineage.add_relation(
            req.parent_alpha_id, child.alpha_id,
            relation_type="evolution",
            metadata={"mutations": mutations},
        )

    return {
        "parent_id": req.parent_alpha_id,
        "parent_name": alpha.name,
        "children": [c.to_dict() for c in children],
        "count": len(children),
    }


@router.post("/graph/evolve/batch")
async def api_evolve_batch(req: EvolveBatchRequest) -> Dict[str, Any]:
    """批量进化"""
    results = []
    for aid in req.alpha_ids:
        alpha = _svc()._store.get(aid)
        if alpha is None:
            continue

        genome = AlphaGenome.from_alpha(alpha)
        mutations = req.mutations or ["threshold", "window"]

        child_genomes = []
        for m in mutations:
            if m == "threshold":
                child_genomes.extend(genome.mutate_threshold())
            elif m == "window":
                child_genomes.extend(genome.mutate_window())
            elif m == "operator":
                child_genomes.extend(genome.mutate_operator())

        children = []
        for g in child_genomes:
            child = g.to_alpha()
            if child.name and child.factor_name:
                children.append(child)

        _svc()._store.save_batch(children)

        for child in children:
            _svc()._lineage.add_relation(aid, child.alpha_id, "evolution", {"mutations": mutations})

        results.append({
            "parent_id": aid,
            "parent_name": alpha.name,
            "children_count": len(children),
        })

    return {"results": results, "total_parents": len(req.alpha_ids)}


# ---- V3.0 Research Mode 端点 ----

class CrossSectionEvaluateRequest(BaseModel):
    n_quantiles: int = Field(5, description="分组数")

class HybridEvaluateRequest(BaseModel):
    top_n: int = Field(50, description="截面选 Top N")
    combine_method: str = Field("and", description="组合方法: and/or")

class WeightRequest(BaseModel):
    alpha_ids: List[str] = Field(..., description="Alpha ID 列表")
    method: str = Field("ic_weight", description="权重方法: equal/ic_weight/score_weight/risk_parity")

class ContributionRequest(BaseModel):
    alpha_ids: List[str] = Field(..., description="Alpha ID 列表")
    weights: Optional[Dict[str, float]] = Field(None, description="权重")

class StabilityRequest(BaseModel):
    alpha_id: str = Field(..., description="Alpha ID")

class RegimeRequest(BaseModel):
    window: int = Field(60, description="滚动窗口")

class AlphaRegimeRequest(BaseModel):
    alpha_id: str = Field(..., description="Alpha ID")

class AlphaRegimeBatchRequest(BaseModel):
    alpha_ids: List[str] = Field(..., description="Alpha ID 列表")


@router.post("/cross-section/evaluate")
async def api_evaluate_cross_section(req: CrossSectionEvaluateRequest) -> Dict[str, Any]:
    """截面 Alpha 评估（需要通过 Jupyter/CLI 传入数据）"""
    return {"message": "Use AlphaService.evaluate_cross_section() with factor_values and forward_returns DataFrames", "n_quantiles": req.n_quantiles}


@router.post("/hybrid/evaluate")
async def api_evaluate_hybrid(req: HybridEvaluateRequest) -> Dict[str, Any]:
    """混合 Alpha 评估（需要通过 Jupyter/CLI 传入数据）"""
    return {"message": "Use AlphaService.evaluate_hybrid() with cross_section_signal, time_series_signal, and forward_returns DataFrames", "top_n": req.top_n}


@router.post("/weights")
async def api_compute_weights(req: WeightRequest) -> Dict[str, Any]:
    """计算 Alpha 权重"""
    return _svc().compute_weights(req.alpha_ids, req.method)


@router.post("/contribution")
async def api_compute_contribution(req: ContributionRequest) -> Dict[str, Any]:
    """Alpha 收益贡献归因（需要通过 Jupyter/CLI 传入 returns_df）"""
    return {"message": "Use AlphaService.compute_contribution() with returns_df DataFrame", "alpha_ids": req.alpha_ids}


@router.post("/stability")
async def api_analyze_stability(req: StabilityRequest) -> Dict[str, Any]:
    """Alpha 稳定性分析"""
    return _svc().analyze_stability(req.alpha_id)


@router.post("/regime/identify")
async def api_identify_regimes(req: RegimeRequest) -> Dict[str, Any]:
    """识别市场状态（需要通过 Jupyter/CLI 传入 price_df）"""
    return {"message": "Use AlphaService.identify_regimes() with price_df DataFrame", "window": req.window}


@router.post("/regime/alpha")
async def api_analyze_alpha_regime(req: AlphaRegimeRequest) -> Dict[str, Any]:
    """分析 Alpha 在不同市场环境下的表现"""
    return {"message": "Use AlphaService.analyze_alpha_regime() with price_df and factor_values", "alpha_id": req.alpha_id}


@router.post("/regime/alpha/batch")
async def api_analyze_alpha_regime_batch(req: AlphaRegimeBatchRequest) -> Dict[str, Any]:
    """批量分析 Alpha 环境适应性"""
    return {"message": "Use AlphaService.analyze_alpha_regime_batch() with price_df and factor_data", "alpha_ids": req.alpha_ids}


# ---- V2 Pipeline — 统一研究调度 ----

class PipelineRunRequest(BaseModel):
    """Pipeline 执行请求"""
    pipeline_type: str = Field("single_experiment", description="Pipeline 类型: single_experiment/parameter_sweep/alpha_batch")
    name: str = Field("", description="Pipeline 名称")
    dataset_id: str = Field("default", description="数据集 ID")
    symbols: Optional[List[str]] = Field(None, description="标的列表")
    start: Optional[str] = Field(None, description="开始日期")
    end: Optional[str] = Field(None, description="结束日期")
    factors: Optional[List[Dict[str, Any]]] = Field(None, description="因子配置列表")
    strategy_id: str = Field("", description="策略 ID")
    strategy_params: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    param_space: Optional[Dict[str, List[Any]]] = Field(None, description="参数扫描空间")
    metric: str = Field("sharpe", description="排序指标")
    top_n: int = Field(10, description="Top N")
    factor_names: Optional[List[str]] = Field(None, description="Alpha 批处理因子列表")
    methods: Optional[List[str]] = Field(None, description="Alpha 生成方法")
    ic_min: float = Field(0.03, description="IC 最小阈值")
    ir_min: float = Field(0.5, description="IR 最小阈值")


class PipelineHistoryRequest(BaseModel):
    limit: int = Field(20, description="返回条数")


@router.post("/pipeline/run")
async def api_pipeline_run(req: PipelineRunRequest) -> Dict[str, Any]:
    """
    执行 Research Pipeline

    统一入口，支持三种模式：
      - single_experiment  单策略单次回测
      - parameter_sweep    参数网格搜索
      - alpha_batch        Alpha 批量生成+评估+排序
    """
    from ..research.pipeline.context import PipelineType

    try:
        pt = PipelineType(req.pipeline_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown pipeline type: {req.pipeline_type}")

    svc = _svc()

    if pt == PipelineType.SINGLE_EXPERIMENT:
        result = svc.run_single(
            name=req.name,
            dataset_id=req.dataset_id,
            symbols=req.symbols,
            start=req.start,
            end=req.end,
            factors=req.factors,
            strategy_id=req.strategy_id,
            strategy_params=req.strategy_params,
        )
    elif pt == PipelineType.PARAMETER_SWEEP:
        result = svc.run_sweep(
            name=req.name,
            dataset_id=req.dataset_id,
            strategy_id=req.strategy_id,
            param_space=req.param_space,
            metric=req.metric,
            top_n=req.top_n,
            strategy_params=req.strategy_params,
        )
    elif pt == PipelineType.ALPHA_BATCH:
        result = svc.run_alpha_batch(
            name=req.name,
            factor_names=req.factor_names,
            methods=req.methods,
            ic_min=req.ic_min,
            ir_min=req.ir_min,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported pipeline type: {pt}")

    return result.to_dict()


@router.get("/pipeline/history")
async def api_pipeline_history(limit: int = 20) -> Dict[str, Any]:
    """查询 Pipeline 执行历史"""
    return {"history": _svc().get_pipeline_history(limit)}


@router.get("/pipeline/stats")
async def api_pipeline_stats() -> Dict[str, Any]:
    """Pipeline 统计信息"""
    return _svc().get_pipeline_stats()
