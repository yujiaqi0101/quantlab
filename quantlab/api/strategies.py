"""
Strategy API — 策略列表 / 详情 / 校验

对应前端 Strategy Explorer + Strategy Detail + Parameter Builder

端点：
  GET  /api/v1/strategies              搜索/列表
  GET  /api/v1/strategies/{id}         详情（含 parameters schema）
  POST /api/v1/strategies/{id}/validate 校验参数
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from ..strategy.api import (
    list_strategies,
    get_strategy,
    validate_strategy_params,
)


router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@router.get("")
async def api_list_strategies(
    q: str = Query("", description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔"),
) -> List[Dict[str, Any]]:
    """列出所有策略（前端策略树 / 搜索框）"""
    tag_list = tags.split(",") if tags else None
    return list_strategies(q=q, tags=tag_list)


@router.get("/{strategy_id}")
async def api_get_strategy(strategy_id: str) -> Dict[str, Any]:
    """获取策略详情（含 parameters schema，前端表单生成用）"""
    result = get_strategy(strategy_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")
    return result


@router.post("/{strategy_id}/validate")
async def api_validate_params(
    strategy_id: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """校验参数合法性（前端表单提交前可先校验）"""
    return validate_strategy_params(strategy_id, params)
