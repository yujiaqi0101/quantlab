"""
Strategy API — 策略列表 / 详情 / 校验

V2.0 重构：通过 StrategyService 统一调用，API 层不直接碰 core

端点：
  GET  /api/v1/strategies              搜索/列表
  GET  /api/v1/strategies/{id}         详情（含 parameters schema）
  POST /api/v1/strategies/{id}/validate 校验参数
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..services import get_service


router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


def _svc():
    return get_service("strategy")


@router.get("")
async def api_list_strategies(
    q: str = Query("", description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔"),
) -> List[Dict[str, Any]]:
    """列出所有策略"""
    tag_list = tags.split(",") if tags else None
    return _svc().list_strategies(q=q, tags=tag_list)


@router.get("/{strategy_id}")
async def api_get_strategy(strategy_id: str) -> Dict[str, Any]:
    """获取策略详情"""
    result = _svc().get_strategy(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")
    return result


@router.post("/{strategy_id}/validate")
async def api_validate_params(
    strategy_id: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """校验参数"""
    return _svc().validate_params(strategy_id, params)
