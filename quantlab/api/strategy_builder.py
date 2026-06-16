"""
Strategy Builder API — V5.0 可视化策略构建

端点：
  GET  /api/v1/strategy-builder/templates       模板列表
  POST /api/v1/strategy-builder/create           创建策略规格
  GET  /api/v1/strategy-builder/specs            列出已保存规格
  GET  /api/v1/strategy-builder/specs/{id}       获取规格详情
  DELETE /api/v1/strategy-builder/specs/{id}     删除规格
  POST /api/v1/strategy-builder/compile          编译策略
  POST /api/v1/strategy-builder/preview          预览策略信号
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..strategy_builder import (
    StrategyBuilder,
    StrategySpec,
    SignalRule,
    PositionConfig,
    RiskConfig,
    STRATEGY_TEMPLATES,
)

router = APIRouter(prefix="/api/v1/strategy-builder", tags=["strategy-builder"])

# ---- 全局 Builder 实例 ----
_builder = StrategyBuilder()


# ============================================================
# Request Models
# ============================================================

class SignalRuleRequest(BaseModel):
    type: str = "threshold"
    factor: str = ""
    op: str = "<"
    value: float = 30.0
    direction: str = "long"
    fast_factor: str = ""
    slow_factor: str = ""


class CreateStrategyRequest(BaseModel):
    name: str
    signals: List[SignalRuleRequest]
    signal_logic: str = "AND"
    position: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class CompileRequest(BaseModel):
    spec_id: str


class PreviewRequest(BaseModel):
    spec_id: str
    dataset_id: str = "default"
    symbol: str = ""
    bars: int = 200


# ============================================================
# Endpoints
# ============================================================

@router.get("/templates")
async def api_list_templates() -> List[Dict[str, Any]]:
    """列出策略模板"""
    return [
        {
            "key": key,
            **STRATEGY_TEMPLATES[key],
        }
        for key in STRATEGY_TEMPLATES
    ]


@router.post("/create")
async def api_create_strategy(req: CreateStrategyRequest) -> Dict[str, Any]:
    """创建策略规格"""
    signals = [s.model_dump() for s in req.signals]
    spec = _builder.create_spec(
        name=req.name,
        signals=signals,
        signal_logic=req.signal_logic,
        position=req.position,
        risk=req.risk,
        description=req.description,
        tags=req.tags,
    )
    return spec.to_dict()


@router.get("/specs")
async def api_list_specs() -> List[Dict[str, Any]]:
    """列出已保存的策略规格"""
    return _builder.list_specs()


@router.get("/specs/{spec_id}")
async def api_get_spec(spec_id: str) -> Dict[str, Any]:
    """获取策略规格详情"""
    spec = _builder.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec '{spec_id}' not found")
    return spec.to_dict()


@router.delete("/specs/{spec_id}")
async def api_delete_spec(spec_id: str) -> Dict[str, Any]:
    """删除策略规格"""
    ok = _builder.delete_spec(spec_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Spec '{spec_id}' not found")
    return {"deleted": True, "spec_id": spec_id}


@router.post("/compile")
async def api_compile_strategy(req: CompileRequest) -> Dict[str, Any]:
    """编译策略规格为可运行的 Strategy 类"""
    spec = _builder.get_spec(req.spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec '{req.spec_id}' not found")

    try:
        strategy_cls = _builder.compile(spec)
        return {
            "spec_id": req.spec_id,
            "name": spec.name,
            "class_name": strategy_cls.__name__,
            "compiled": True,
            "signal_count": len(spec.signals),
            "signal_logic": spec.signal_logic,
            "position": spec.position.to_dict(),
            "risk": spec.risk.to_dict(),
            "message": f"Strategy '{spec.name}' compiled successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")


@router.post("/preview")
async def api_preview_strategy(req: PreviewRequest) -> Dict[str, Any]:
    """预览策略信号（模拟）"""
    spec = _builder.get_spec(req.spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec '{req.spec_id}' not found")

    # Mock 预览：生成模拟信号序列
    import numpy as np
    rng = np.random.RandomState(42)

    n_bars = req.bars
    # 根据信号逻辑生成模拟信号
    signals = []
    for rule in spec.signals:
        # 随机生成信号
        sig = rng.choice([0, 1, -1], size=n_bars, p=[0.6, 0.25, 0.15])
        signals.append(sig)

    # 组合
    if spec.signal_logic == "AND":
        combined = np.ones(n_bars)
        for s in signals:
            combined = combined * s
    elif spec.signal_logic == "OR":
        combined = np.zeros(n_bars)
        for s in signals:
            combined = combined + s
        combined = np.where(combined > 0, 1, np.where(combined < 0, -1, 0))
    else:  # MAJORITY
        combined = sum(signals)
        combined = np.where(combined > 0, 1, np.where(combined < 0, -1, 0))

    # 统计
    long_count = int(np.sum(combined == 1))
    short_count = int(np.sum(combined == -1))
    neutral_count = int(np.sum(combined == 0))

    return {
        "spec_id": req.spec_id,
        "name": spec.name,
        "total_bars": n_bars,
        "long_count": long_count,
        "short_count": short_count,
        "neutral_count": neutral_count,
        "long_pct": round(long_count / n_bars * 100, 1),
        "short_pct": round(short_count / n_bars * 100, 1),
        "signal_timeline": combined.tolist()[:100],  # 前100个
        "signal_logic": spec.signal_logic,
        "position": spec.position.to_dict(),
        "risk": spec.risk.to_dict(),
    }


@router.post("/from-template")
async def api_create_from_template(template_key: str, name: Optional[str] = None) -> Dict[str, Any]:
    """从模板创建策略规格"""
    if template_key not in STRATEGY_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template '{template_key}' not found")

    tmpl = STRATEGY_TEMPLATES[template_key]
    spec = _builder.create_spec(
        name=name or tmpl["name"],
        signals=tmpl["signals"],
        signal_logic=tmpl.get("signal_logic", "AND"),
        position=tmpl.get("position"),
        risk=tmpl.get("risk"),
        description=tmpl.get("description", ""),
        tags=tmpl.get("tags", []),
    )
    return spec.to_dict()
