"""
Dataset API — 数据集列表 / 详情 / 预览 / 统计 / 校验

V2.0 重构：通过 DatasetService 统一调用，API 层不直接碰 core

端点：
  GET  /api/v1/datasets                  数据集列表
  GET  /api/v1/datasets/{id}             数据集详情
  GET  /api/v1/datasets/{id}/symbols     标的列表
  GET  /api/v1/datasets/{id}/preview     数据预览
  GET  /api/v1/datasets/{id}/stats       数据统计
  GET  /api/v1/datasets/{id}/validate    数据校验
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..services import get_service


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def _svc():
    return get_service("dataset")


@router.get("")
async def api_list_datasets(
    q: str = Query("", description="搜索关键词"),
    tag: Optional[str] = Query(None, description="按标签过滤"),
    asset_type: Optional[str] = Query(None, description="按资产类型过滤"),
    frequency: Optional[str] = Query(None, description="按频率过滤"),
) -> List[Dict[str, Any]]:
    """列出所有数据集"""
    return _svc().list_datasets(q=q, tag=tag, asset_type=asset_type, frequency=frequency)


@router.get("/{dataset_id}")
async def api_get_dataset(dataset_id: str) -> Dict[str, Any]:
    """数据集详情"""
    result = _svc().get_dataset(dataset_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return result


@router.get("/{dataset_id}/symbols")
async def api_list_symbols(dataset_id: str) -> List[str]:
    """数据集标的列表"""
    symbols = _svc().get_symbols(dataset_id)
    if not symbols:
        result = _svc().get_dataset(dataset_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return symbols


@router.get("/{dataset_id}/preview")
async def api_preview_dataset(
    dataset_id: str,
    n: int = Query(100, description="预览行数"),
) -> Dict[str, Any]:
    """数据预览"""
    ds = _svc().get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return _svc().preview(dataset_id, n=n)


@router.get("/{dataset_id}/stats")
async def api_dataset_stats(dataset_id: str) -> Dict[str, Any]:
    """数据统计"""
    ds = _svc().get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return _svc().stats(dataset_id)


@router.get("/{dataset_id}/validate")
async def api_validate_dataset(dataset_id: str) -> Dict[str, Any]:
    """数据校验"""
    ds = _svc().get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return _svc().validate(dataset_id)
