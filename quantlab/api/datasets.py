"""
Datasets API — 数据集管理（统一存储版）

端点：
  GET /api/v1/datasets              列表
  GET /api/v1/datasets/{id}         详情
  GET /api/v1/datasets/{id}/preview  预览
  GET /api/v1/datasets/{id}/symbols  标的列表
  GET /api/v1/datasets/{id}/stats    统计信息

所有数据通过 DatasetManager 统一管理，持久化到 storage/ml_lab.db + Parquet。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..ml.dataset import get_dataset_manager

logger = logging.getLogger("quantlab.api.datasets")

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def _ds_to_dict(ds) -> dict:
    """将 Dataset 对象转换为前端期望的响应格式（兼容原 datasets.db 结构）"""
    symbols = ds.symbols if isinstance(ds.symbols, list) else [ds.symbols]
    symbol_str = ",".join(symbols)
    return {
        "dataset_id": ds.dataset_id,
        "name": ds.name,
        "symbol": symbol_str,
        "frequency": ds.frequency,
        "asset_type": ds.asset_type,
        "start_time": ds.start_date,
        "end_time": ds.end_date,
        "rows": 0,  # 实际行数在加载后才有
        "storage_path": ds.storage_path,
        "storage_format": ds.storage_format,
        "schema": ds.schema,
        "tags": ds.tags,
        "is_ohlcv": ds.is_ohlcv,
        "coverage": ds.coverage,
        "description": ds.description,
        "created_at": ds.created_at,
        "has_data": ds.get_data() is not None,
    }


@router.get("")
async def list_datasets(q: Optional[str] = None, tag: Optional[str] = None):
    """列出所有数据集"""
    mgr = get_dataset_manager()
    datasets = mgr.list_datasets()

    result = []
    for ds in datasets:
        d = _ds_to_dict(ds)
        # 过滤
        if q:
            if q.lower() not in ds.name.lower() and q.lower() not in ",".join(ds.symbols).lower():
                continue
        if tag:
            if tag not in ds.tags:
                continue
        result.append(d)
    # 按名称排序
    result.sort(key=lambda x: x["name"])
    return result


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """数据集详情"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset {dataset_id} not found")
    return _ds_to_dict(ds)


@router.get("/{dataset_id}/preview")
async def get_preview(dataset_id: str, n: int = 100):
    """数据预览"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset {dataset_id} not found")

    # 尝试加载数据
    df = ds.get_data()
    if df is None:
        mgr.load_dataset_data(dataset_id)
        df = ds.get_data()

    if df is None or len(df) == 0:
        return {
            "dataset_id": dataset_id,
            "symbols": ds.symbols,
            "preview": {},
        }

    preview_data = df.head(n)
    return {
        "dataset_id": dataset_id,
        "symbols": ds.symbols,
        "preview": {
            "columns": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "rows": preview_data.values.tolist(),
            "index": [str(idx) for idx in preview_data.index.tolist()],
        },
    }


@router.get("/{dataset_id}/symbols")
async def get_symbols(dataset_id: str):
    """标的列表"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset {dataset_id} not found")
    return ds.symbols


@router.get("/{dataset_id}/stats")
async def get_stats(dataset_id: str):
    """数据统计"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset {dataset_id} not found")

    # 尝试加载数据
    df = ds.get_data()
    if df is None:
        mgr.load_dataset_data(dataset_id)
        df = ds.get_data()

    if df is None or len(df) == 0:
        return {
            "dataset_id": dataset_id,
            "row_count": 0,
            "null_counts": {},
            "dtypes": {},
        }

    return {
        "dataset_id": dataset_id,
        "row_count": len(df),
        "null_counts": {c: int(df[c].isnull().sum()) for c in df.columns},
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
    }
