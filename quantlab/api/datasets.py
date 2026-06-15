"""
Dataset API — 数据集列表 / 详情 / 预览 / 统计 / 校验

V4.3 重写：接入 DatasetRegistry

端点：
  GET  /api/v1/datasets                  数据集列表（支持搜索/标签过滤）
  GET  /api/v1/datasets/{id}             数据集详情（含 schema）
  GET  /api/v1/datasets/{id}/symbols     数据集标的列表
  GET  /api/v1/datasets/{id}/preview     数据预览（前100行）
  GET  /api/v1/datasets/{id}/stats       数据统计
  GET  /api/v1/datasets/{id}/validate    数据校验
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from ..dataset.registry import get_dataset_registry
from ..dataset.catalog import DataCatalog


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


# ---- 启动时自动扫描 ----
_catalog_initialized = False


def _ensure_catalog() -> None:
    """首次请求时自动扫描 data/ 目录"""
    global _catalog_initialized
    if _catalog_initialized:
        return
    catalog = DataCatalog()
    catalog.scan()
    _catalog_initialized = True


@router.get("")
async def api_list_datasets(
    q: str = Query("", description="搜索关键词"),
    tag: Optional[str] = Query(None, description="按标签过滤"),
    asset_type: Optional[str] = Query(None, description="按资产类型过滤"),
    frequency: Optional[str] = Query(None, description="按频率过滤"),
) -> List[Dict[str, Any]]:
    """列出所有数据集（支持搜索/标签过滤）"""
    _ensure_catalog()
    registry = get_dataset_registry()

    if q:
        datasets = registry.search(q)
    elif tag or asset_type or frequency:
        datasets = registry.list(tag=tag, asset_type=asset_type, frequency=frequency)
    else:
        datasets = registry.list()

    return [d.to_dict() for d in datasets]


@router.get("/{dataset_id}")
async def api_get_dataset(dataset_id: str) -> Dict[str, Any]:
    """数据集详情（含 schema、version）"""
    _ensure_catalog()
    registry = get_dataset_registry()
    meta = registry.get(dataset_id)
    if meta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return meta.to_dict()


@router.get("/{dataset_id}/symbols")
async def api_list_symbols(dataset_id: str) -> List[str]:
    """数据集标的列表"""
    _ensure_catalog()
    registry = get_dataset_registry()
    meta = registry.get(dataset_id)
    if meta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return [s.strip() for s in meta.symbol.split(",") if s.strip()]


@router.get("/{dataset_id}/preview")
async def api_preview_dataset(
    dataset_id: str,
    n: int = Query(100, description="预览行数"),
) -> Dict[str, Any]:
    """数据预览（前 n 行，前端表格预览用）"""
    _ensure_catalog()
    registry = get_dataset_registry()
    meta = registry.get(dataset_id)
    if meta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return registry.preview(dataset_id, n=n)


@router.get("/{dataset_id}/stats")
async def api_dataset_stats(dataset_id: str) -> Dict[str, Any]:
    """数据统计（行数/缺失/重复）"""
    _ensure_catalog()
    registry = get_dataset_registry()
    meta = registry.get(dataset_id)
    if meta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return registry.stats(dataset_id)


@router.get("/{dataset_id}/validate")
async def api_validate_dataset(dataset_id: str) -> Dict[str, Any]:
    """数据校验（时间递增/缺失/重复/OHLC合法性）"""
    _ensure_catalog()
    registry = get_dataset_registry()
    meta = registry.get(dataset_id)
    if meta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return registry.validate(dataset_id)
