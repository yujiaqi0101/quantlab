"""
Signal Engine API — ML Lab 信号引擎后端
==========================================

端点 (均以 /api/v1/signal-engine 为前缀):
  POST /generate              运行 pipeline 生成信号
  GET  /templates             模板列表
  GET  /templates/{name}      单个模板详情
  GET  /signals               信号列表 (?symbol=&direction=&limit=)
  GET  /signals/{signal_id}   单个信号详情
  GET  /registry/versions     版本列表 (?signal_id=)
  GET  /registry/versions/{version_id}  单个版本详情
  POST /validate              验证信号
  GET  /explain/{signal_id}   信号解释
  POST /adapt                 手动调 Adapter（调试用）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..ml.signal_engine import (
    PipelineConfig,
    Prediction,
    PredictionAdapter,
    Signal,
    SignalDirection,
    SignalValidator,
    ExplainabilityEngine,
    get_signal_registry,
    get_template,
    list_templates,
    run_pipeline,
)

logger = logging.getLogger("quantlab.api.signal_engine")

router = APIRouter(prefix="/api/v1/signal-engine", tags=["signal-engine"])


# ---------- 请求/响应模型 ----------

class PredictionItem(BaseModel):
    symbol: str
    datetime: str
    value: float
    probability: float = 0.0
    model_type: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerateRequest(BaseModel):
    predictions: List[PredictionItem]
    config: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    save_to_registry: bool = False
    model_version: str = ""
    dataset_id: str = ""


class AdaptRequest(BaseModel):
    model_type: str = "lightgbm"
    outputs: List[Any]
    symbols: List[str]
    datetime: str
    y_probas: Optional[List[List[float]]] = None


class ValidateRequest(BaseModel):
    signal_ids: List[str] = Field(default_factory=list)
    returns_data: Dict[str, List[float]] = Field(default_factory=dict)
    returns_index: List[str] = Field(default_factory=list)


# ---------- Pipeline 运行 ----------

@router.post("/generate")
async def generate_signals(req: GenerateRequest):
    """运行 pipeline 生成信号"""
    # 转换 Prediction
    predictions = [
        Prediction(
            symbol=p.symbol,
            datetime=p.datetime,
            value=p.value,
            probability=p.probability,
            model_type=p.model_type,
            metadata=p.metadata,
        )
        for p in req.predictions
    ]

    # 构造 config
    config_dict = req.config or {}
    if req.save_to_registry:
        config_dict["save_to_registry"] = True
    if req.model_version:
        config_dict["model_version"] = req.model_version
    if req.dataset_id:
        config_dict["dataset_id"] = req.dataset_id
    config = PipelineConfig.from_dict(config_dict) if config_dict else PipelineConfig()

    # 行情数据 provider（简化：从 market_data 字典构造）
    market_data_provider = None
    if req.market_data:
        md = req.market_data

        def _provider(symbol: str, datetime: str) -> Optional[Dict[str, Any]]:
            return md.get(symbol, {}).get(datetime)

        market_data_provider = _provider

    try:
        signal_set = run_pipeline(predictions, config, market_data_provider)
        return signal_set.to_dict()
    except Exception as e:
        logger.error(f"Generate signals failed: {e}", exc_info=True)
        raise HTTPException(500, f"Generate failed: {e}")


# ---------- 模板 ----------

@router.get("/templates")
async def get_templates():
    """模板列表"""
    templates = list_templates()
    return {"templates": [t.to_dict() for t in templates], "total": len(templates)}


@router.get("/templates/{name}")
async def get_template_detail(name: str):
    """单个模板详情"""
    t = get_template(name)
    if not t:
        raise HTTPException(404, f"Template {name} not found")
    return t.to_dict()


# ---------- 信号查询 ----------

@router.get("/signals")
async def list_signals(
    symbol: str = "",
    direction: str = "",
    limit: int = 100,
    offset: int = 0,
):
    """信号列表"""
    reg = get_signal_registry()
    signals = reg.list_signals(symbol=symbol, direction=direction, limit=limit, offset=offset)
    total = reg.count_signals(symbol=symbol, direction=direction)
    return {"signals": [s.to_dict() for s in signals], "total": total}


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    """单个信号详情"""
    reg = get_signal_registry()
    sig = reg.get_signal(signal_id)
    if not sig:
        raise HTTPException(404, f"Signal {signal_id} not found")
    return sig.to_dict()


# ---------- 版本管理 ----------

@router.get("/registry/versions")
async def list_versions(signal_id: str = ""):
    """版本列表（signal_id 可选，不传则返回全部）"""
    reg = get_signal_registry()
    versions = reg.list_versions(signal_id)
    return {"versions": [v.to_dict() for v in versions], "total": len(versions)}


@router.get("/registry/versions/{version_id}")
async def get_version(version_id: str):
    """单个版本详情"""
    reg = get_signal_registry()
    v = reg.get_version(version_id)
    if not v:
        raise HTTPException(404, f"Version {version_id} not found")
    return v.to_dict()


# ---------- 验证 ----------

@router.post("/validate")
async def validate_signals(req: ValidateRequest):
    """验证信号"""
    reg = get_signal_registry()
    signals: List[Signal] = []
    for sid in req.signal_ids:
        s = reg.get_signal(sid)
        if s:
            signals.append(s)
    if not signals:
        raise HTTPException(404, "No signals found")

    # 构造 returns DataFrame
    if not req.returns_data or not req.returns_index:
        raise HTTPException(400, "returns_data and returns_index are required")
    df = pd.DataFrame(req.returns_data, index=pd.to_datetime(req.returns_index))

    validator = SignalValidator()
    report = validator.validate(signals, df)
    return report.to_dict()


# ---------- 解释 ----------

@router.get("/explain/{signal_id}")
async def explain_signal(signal_id: str):
    """信号解释"""
    reg = get_signal_registry()
    sig = reg.get_signal(signal_id)
    if not sig:
        raise HTTPException(404, f"Signal {signal_id} not found")
    trace = ExplainabilityEngine().explain(sig)
    return trace.to_dict()


# ---------- 适配（调试用） ----------

@router.post("/adapt")
async def adapt_predictions(req: AdaptRequest):
    """手动调 Adapter（调试用）"""
    adapter = PredictionAdapter()
    predictions: List[Dict[str, Any]] = []
    for i, output in enumerate(req.outputs):
        symbol = req.symbols[i] if i < len(req.symbols) else f"sym_{i}"
        y_proba = req.y_probas[i] if req.y_probas and i < len(req.y_probas) else None
        pred = adapter.adapt_auto(
            symbol=symbol,
            datetime=req.datetime,
            output=output,
            model_type=req.model_type,
            y_proba=y_proba,
        )
        predictions.append(pred.to_dict())
    return {"predictions": predictions, "total": len(predictions)}
