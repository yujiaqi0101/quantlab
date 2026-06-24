"""
Asset Registry API — 资产注册中心 API 端点

提供统一的资产查询、管理接口：
  - GET  /api/v1/asset/list           列出资产
  - GET  /api/v1/asset/{asset_id}     获取资产详情
  - GET  /api/v1/asset/{asset_id}/manifest  获取 manifest
  - GET  /api/v1/asset/{asset_id}/lineage   获取血缘
  - GET  /api/v1/asset/champions       获取所有 Champion
  - GET  /api/v1/asset/families        列出所有 Family
  - GET  /api/v1/asset/summary         获取摘要
  - POST /api/v1/asset/register        注册资产
  - POST /api/v1/asset/champion/set    设置 Champion
  - POST /api/v1/asset/lineage/add     添加血缘
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..asset import (
    AssetRegistry,
    AssetType,
    AssetStatus,
    AssetRelation,
    DatasetAsset,
    FeatureSetAsset,
    LabelSetAsset,
    ModelPackageAsset,
    StrategyPackageAsset,
    RiskProfileAsset,
    DeploymentProfileAsset,
    get_asset_registry,
)

router = APIRouter(prefix="/api/v1/asset", tags=["asset"])


# ==================================================================
# 请求模型
# ==================================================================


class RegisterDatasetRequest(BaseModel):
    name: str = ""
    family: str = ""
    version: str = "1.0.0"
    dataset_id: str = ""
    symbols: List[str] = []
    start_date: str = ""
    end_date: str = ""
    frequency: str = "1d"
    n_rows: int = 0
    n_cols: int = 0
    description: str = ""
    tags: List[str] = []


class RegisterFeatureSetRequest(BaseModel):
    name: str = ""
    family: str = ""
    version: str = "1.0.0"
    feature_set_id: str = ""
    feature_ids: List[str] = []
    n_features: int = 0
    description: str = ""
    tags: List[str] = []


class RegisterLabelSetRequest(BaseModel):
    name: str = ""
    family: str = ""
    version: str = "1.0.0"
    label_set_id: str = ""
    label_id: str = ""
    label_type: str = ""
    horizon: int = 0
    description: str = ""
    tags: List[str] = []


class RegisterModelPackageRequest(BaseModel):
    name: str = ""
    family: str = ""
    version: str = "1.0.0"
    algorithm: str = ""
    model_type: str = ""
    is_classifier: bool = False
    params: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    dataset_id: str = ""
    feature_set_id: str = ""
    label_set_id: str = ""
    validation_passed: bool = False
    validation_score: float = 0.0
    validation_grade: str = "F"
    description: str = ""
    tags: List[str] = []


class RegisterStrategyPackageRequest(BaseModel):
    name: str = ""
    family: str = ""
    version: str = "1.0.0"
    strategy_id: str = ""
    model_asset_id: str = ""
    rules: Dict[str, Any] = {}
    description: str = ""
    tags: List[str] = []


class SetChampionRequest(BaseModel):
    family: str
    asset_id: str
    reason: str = ""


class AddLineageRequest(BaseModel):
    parent_asset_id: str
    child_asset_id: str
    relation: str = "DERIVED_FROM"
    note: str = ""


# ==================================================================
# 查询端点
# ==================================================================


@router.get("/summary")
async def get_summary():
    """获取资产摘要"""
    reg = get_asset_registry()
    return reg.get_summary()


@router.get("/list")
async def list_assets(
    asset_type: Optional[str] = None,
    family: Optional[str] = None,
    status: Optional[str] = None,
):
    """列出资产"""
    reg = get_asset_registry()

    at = None
    if asset_type:
        try:
            at = AssetType(asset_type)
        except ValueError:
            raise HTTPException(400, f"Unknown asset type: {asset_type}")

    st = None
    if status:
        try:
            st = AssetStatus(status)
        except ValueError:
            raise HTTPException(400, f"Unknown status: {status}")

    assets = reg.list_assets(asset_type=at, family=family, status=st)
    return {
        "total": len(assets),
        "assets": [a.to_index() for a in assets],
    }


@router.get("/{asset_id}")
async def get_asset(asset_id: str):
    """获取资产详情"""
    reg = get_asset_registry()
    asset = reg.get(asset_id)
    if asset is None:
        raise HTTPException(404, f"Asset not found: {asset_id}")
    return asset.to_dict()


@router.get("/{asset_id}/manifest")
async def get_asset_manifest(asset_id: str):
    """获取资产 manifest"""
    reg = get_asset_registry()
    manifest = reg.get_manifest(asset_id)
    if manifest is None:
        raise HTTPException(404, f"Asset manifest not found: {asset_id}")
    return manifest


@router.get("/{asset_id}/lineage")
async def get_asset_lineage(asset_id: str):
    """获取资产血缘"""
    reg = get_asset_registry()
    asset = reg.get(asset_id)
    if asset is None:
        raise HTTPException(404, f"Asset not found: {asset_id}")

    tree = reg.get_lineage(asset_id)
    ancestors = [n.to_dict() for n in reg.get_ancestors(asset_id)]
    descendants = [n.to_dict() for n in reg.get_descendants(asset_id)]
    chain = reg.get_dependency_chain(asset_id)

    return {
        "asset_id": asset_id,
        "tree": tree,
        "ancestors": ancestors,
        "descendants": descendants,
        "dependency_chain": chain,
    }


@router.get("/champions/all")
async def get_all_champions():
    """获取所有 Champion"""
    reg = get_asset_registry()
    champions = reg.get_all_champions()
    return {
        "total": len(champions),
        "champions": {
            family: asset.to_index()
            for family, asset in champions.items()
        },
    }


@router.get("/champions/{family}")
async def get_champion(family: str):
    """获取指定 Family 的 Champion"""
    reg = get_asset_registry()
    asset = reg.get_champion(family)
    if asset is None:
        raise HTTPException(404, f"No champion for family: {family}")
    return asset.to_dict()


@router.get("/families/all")
async def list_families():
    """列出所有 Family"""
    reg = get_asset_registry()
    families = reg.list_families()
    return {
        "total": len(families),
        "families": families,
    }


@router.get("/families/{family}/versions")
async def get_family_versions(family: str):
    """获取 Family 的版本历史"""
    reg = get_asset_registry()
    history = reg.get_version_history(family)
    return {
        "family": family,
        "total": len(history),
        "versions": history,
    }


# ==================================================================
# 注册端点
# ==================================================================


@router.post("/register/dataset")
async def register_dataset(req: RegisterDatasetRequest):
    """注册 Dataset 资产"""
    reg = get_asset_registry()
    asset = DatasetAsset(
        name=req.name,
        family=req.family or req.name,
        version=req.version,
        dataset_id=req.dataset_id,
        symbols=req.symbols,
        start_date=req.start_date,
        end_date=req.end_date,
        frequency=req.frequency,
        n_rows=req.n_rows,
        n_cols=req.n_cols,
        description=req.description,
        tags=req.tags,
    )
    asset_id = reg.register(asset)
    return {"asset_id": asset_id, "status": "registered"}


@router.post("/register/feature-set")
async def register_feature_set(req: RegisterFeatureSetRequest):
    """注册 FeatureSet 资产"""
    reg = get_asset_registry()
    asset = FeatureSetAsset(
        name=req.name,
        family=req.family or req.name,
        version=req.version,
        feature_set_id=req.feature_set_id,
        feature_ids=req.feature_ids,
        n_features=req.n_features or len(req.feature_ids),
        description=req.description,
        tags=req.tags,
    )
    asset_id = reg.register(asset)
    return {"asset_id": asset_id, "status": "registered"}


@router.post("/register/label-set")
async def register_label_set(req: RegisterLabelSetRequest):
    """注册 LabelSet 资产"""
    reg = get_asset_registry()
    asset = LabelSetAsset(
        name=req.name,
        family=req.family or req.name,
        version=req.version,
        label_set_id=req.label_set_id,
        label_id=req.label_id,
        label_type=req.label_type,
        horizon=req.horizon,
        description=req.description,
        tags=req.tags,
    )
    asset_id = reg.register(asset)
    return {"asset_id": asset_id, "status": "registered"}


@router.post("/register/model-package")
async def register_model_package(req: RegisterModelPackageRequest):
    """注册 ModelPackage 资产（强制 Validation 门禁）"""
    reg = get_asset_registry()
    asset = ModelPackageAsset(
        name=req.name,
        family=req.family or req.name,
        version=req.version,
        algorithm=req.algorithm,
        model_type=req.model_type,
        is_classifier=req.is_classifier,
        params=req.params,
        metrics=req.metrics,
        dataset_id=req.dataset_id,
        feature_set_id=req.feature_set_id,
        label_set_id=req.label_set_id,
        validation_passed=req.validation_passed,
        validation_score=req.validation_score,
        validation_grade=req.validation_grade,
        description=req.description,
        tags=req.tags,
    )
    try:
        asset_id = reg.register(asset)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"asset_id": asset_id, "status": "registered"}


@router.post("/register/strategy-package")
async def register_strategy_package(req: RegisterStrategyPackageRequest):
    """注册 StrategyPackage 资产"""
    reg = get_asset_registry()
    asset = StrategyPackageAsset(
        name=req.name,
        family=req.family or req.name,
        version=req.version,
        strategy_id=req.strategy_id,
        model_asset_id=req.model_asset_id,
        rules=req.rules,
        description=req.description,
        tags=req.tags,
    )
    asset_id = reg.register(asset)
    return {"asset_id": asset_id, "status": "registered"}


# ==================================================================
# 管理端点
# ==================================================================


@router.post("/champion/set")
async def set_champion(req: SetChampionRequest):
    """设置 Champion"""
    reg = get_asset_registry()
    try:
        pointer = reg.set_champion(req.family, req.asset_id, req.reason)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return pointer.to_dict()


@router.post("/lineage/add")
async def add_lineage(req: AddLineageRequest):
    """添加血缘关系"""
    reg = get_asset_registry()
    try:
        relation = AssetRelation(req.relation)
    except ValueError:
        raise HTTPException(400, f"Unknown relation: {req.relation}")

    success = reg.add_lineage(
        parent_asset_id=req.parent_asset_id,
        child_asset_id=req.child_asset_id,
        relation=relation,
        note=req.note,
    )
    if not success:
        raise HTTPException(400, "Cannot add lineage (cycle detected or asset not found)")
    return {"status": "added"}


@router.get("/search/{query}")
async def search_assets(query: str):
    """搜索资产"""
    reg = get_asset_registry()
    results = reg.search(query)
    return {
        "query": query,
        "total": len(results),
        "assets": [a.to_index() for a in results],
    }
