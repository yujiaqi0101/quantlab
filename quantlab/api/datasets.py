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

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..ml.dataset import get_dataset_manager

logger = logging.getLogger("quantlab.api.datasets")

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def _ds_to_dict(ds) -> dict:
    """将 Dataset 对象转换为前端期望的响应格式（兼容原 datasets.db 结构）"""
    symbols = ds.symbols if isinstance(ds.symbols, list) else [ds.symbols]
    symbol_str = ",".join(symbols)

    # 动态计算行数
    df = ds.get_data()
    row_count = len(df) if df is not None else 0

    # 动态计算日期范围
    start_time = ds.start_date
    end_time = ds.end_date
    if df is not None:
        # 优先从 DatetimeIndex 推断
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
            if not start_time:
                start_time = str(df.index.min())
            if not end_time:
                end_time = str(df.index.max())
        # 其次从 trade_date / date 列推断
        for col in ("trade_date", "date", "datetime"):
            if col in df.columns and len(df) > 0:
                try:
                    dates = pd.to_datetime(df[col])
                    if not start_time:
                        start_time = str(dates.min())
                    if not end_time:
                        end_time = str(dates.max())
                except Exception:
                    pass
                break

    return {
        "dataset_id": ds.dataset_id,
        "name": ds.name,
        "symbol": symbol_str,
        "frequency": ds.frequency,
        "asset_type": ds.asset_type,
        "start_time": start_time,
        "end_time": end_time,
        "rows": row_count,
        "storage_path": ds.storage_path,
        "storage_format": ds.storage_format,
        "schema": ds.schema,
        "tags": ds.tags,
        "is_ohlcv": ds.is_ohlcv,
        "coverage": ds.coverage,
        "description": ds.description,
        "created_at": ds.created_at,
        "has_data": df is not None,
        "scope_type": ds.scope_type,
        "universe_id": ds.universe_id,
    }


@router.get("")
async def list_datasets(q: Optional[str] = None, tag: Optional[str] = None):
    """列出所有数据集"""
    mgr = get_dataset_manager()
    datasets = mgr.list_datasets()

    result = []
    for ds in datasets:
        d = _ds_to_dict(ds)
        # 过滤：搜索 name / symbols / universe_id
        if q:
            q_lower = q.lower()
            match = (
                q_lower in ds.name.lower()
                or q_lower in ",".join(ds.symbols).lower()
                or q_lower in ds.universe_id.lower()
            )
            if not match:
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

    # 尝试加载数据，确保详情页能显示行数和日期范围
    if ds.get_data() is None:
        mgr.load_dataset_data(dataset_id)

    return _ds_to_dict(ds)


@router.get("/{dataset_id}/preview")
async def get_preview(dataset_id: str, n: int = 100, symbol: Optional[str] = None):
    """数据预览（按 symbol 分组，匹配前端 PreviewData 结构）

    - symbol 参数：指定要预览的标的，为空时返回第一个标的的预览
    - 多标的数据集只返回单个标的的预览，避免响应体过大
    """
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
            "symbols": ds.symbols if ds.symbols else [],
            "preview": {},
        }

    # 多标的数据集：按 symbol 分组
    if "symbol" in df.columns:
        all_symbols = sorted([s for s in df["symbol"].unique().tolist() if pd.notna(s)])
        # 只预览请求的 symbol，默认取第一个
        target_symbol = symbol if symbol and symbol in all_symbols else (all_symbols[0] if all_symbols else None)
        preview = {}
        if target_symbol:
            group_df = df[df["symbol"] == target_symbol].head(n)
            display_df = group_df.drop(columns=["symbol"])
            preview[target_symbol] = {
                "columns": list(display_df.columns),
                "dtypes": {c: str(display_df[c].dtype) for c in display_df.columns},
                "rows": display_df.values.tolist(),
                "index": [str(idx) for idx in group_df.index.tolist()],
            }
        return {
            "dataset_id": dataset_id,
            "symbols": all_symbols,
            "preview": preview,
        }

    # 单标的数据集
    preview_df = df.head(n)
    key = ds.symbols[0] if ds.symbols else ds.name
    preview = {
        key: {
            "columns": list(preview_df.columns),
            "dtypes": {c: str(preview_df[c].dtype) for c in preview_df.columns},
            "rows": preview_df.values.tolist(),
            "index": [str(idx) for idx in preview_df.index.tolist()],
        }
    }
    symbols = ds.symbols if ds.symbols else [key]

    return {
        "dataset_id": dataset_id,
        "symbols": symbols,
        "preview": preview,
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
