"""
V4.1 Strategy Registry — Service Layer（API 友好）

API 层（FastAPI）应**只**调用本文件的纯函数，不直接碰 Registry。

为什么：
  - 未来要加：缓存、限流、权限、字段过滤、响应包装
  - 全部在 service 层做，API 层只做参数解析 + 返回
  - service 层无 web 依赖，可独立测试

对应 API 端点（V4.2 FastAPI 阶段会接进来）:
  GET  /api/v1/strategies                → list_strategies()
  GET  /api/v1/strategies/{id}           → get_strategy(id)
  GET  /api/v1/strategies/{id}/versions  → list_strategy_versions(id)
  GET  /api/v1/strategies/{id}/source    → get_strategy_source(id, ver)
  POST /api/v1/strategies/{id}/validate  → validate_strategy_params()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .registry import (
    StrategyRegistry,
    get_strategy_registry,
)
from .versioning import StrategyVersion


logger = logging.getLogger("quantlab.strategy.api")


# -------------------------------------------------------------
# 列表 / 详情
# -------------------------------------------------------------
def list_strategies(
    q: str = "",
    tags: Optional[List[str]] = None,
    has_param: Optional[str] = None,
    reg: Optional[StrategyRegistry] = None,
) -> List[Dict[str, Any]]:
    """
    列出所有策略（前端策略中心 / 搜索框）

    返回精简字典（不含源码，节省网络）：
      [
        {
          "id": "ma_cross",
          "name": "MA Cross",
          "description": "...",
          "version": "1.0.0",
          "tags": ["classic", "trend"],
          "parameters": [
            {"name": "fast", "type": "int",
             "default": 20, "min": 5, "max": 100, ...},
            ...
          ],
          "param_space": {"fast": [...], "slow": [...]},
          "class_path": "quantlab.signals.MACrossStrategy",
        },
        ...
      ]
    """
    reg = reg or get_strategy_registry()
    items = reg.search(q=q, tags=tags, has_param=has_param)
    return [m.to_dict() for m in items]


def get_strategy(
    strategy_id: str,
    reg: Optional[StrategyRegistry] = None,
) -> Optional[Dict[str, Any]]:
    """
    单个策略详情（前端策略详情页 / 表单生成用）

    返回完整 metadata 字典
    """
    reg = reg or get_strategy_registry()
    m = reg.get(strategy_id)
    if m is None:
        return None
    return m.to_dict()


def list_strategy_versions(
    strategy_id: str,
    reg: Optional[StrategyRegistry] = None,
) -> List[Dict[str, Any]]:
    """列出策略的所有历史版本"""
    reg = reg or get_strategy_registry()
    vs = reg.list_versions(strategy_id)
    return [
        {
            "version": v.version,
            "source_hash": v.source_hash,
            "class_path": v.class_path,
            "registered_at": v.registered_at,
            "fingerprint": dict(v.fingerprint),
        }
        for v in vs
    ]


def get_strategy_source(
    strategy_id: str,
    version: str = "latest",
    reg: Optional[StrategyRegistry] = None,
) -> Optional[Dict[str, Any]]:
    """
    取策略源码（复现实验用，前端一般不调用）

    返回：
      {
        "strategy_id": "ma_cross",
        "version": "1.0.0",
        "class_path": "...",
        "source": "<源码字符串>",
        "source_hash": "...",
        "fingerprint": {...}
      }
    """
    reg = reg or get_strategy_registry()
    v = reg.get_version(strategy_id, version)
    if v is None:
        return None
    return {
        "strategy_id": v.strategy_id,
        "version": v.version,
        "class_path": v.class_path,
        "source": v.source,
        "source_hash": v.source_hash,
        "fingerprint": dict(v.fingerprint),
    }


# -------------------------------------------------------------
# 校验
# -------------------------------------------------------------
def validate_strategy_params(
    strategy_id: str,
    params: Dict[str, Any],
    reg: Optional[StrategyRegistry] = None,
) -> Dict[str, Any]:
    """
    前端表单提交前可以先调一下，校验参数合法性

    返回：
      {"ok": True, "errors": []}
      {"ok": False, "errors": ["fast: expect int, ..."]}
    """
    reg = reg or get_strategy_registry()
    m = reg.get(strategy_id)
    if m is None:
        return {
            "ok": False,
            "errors": [
                f"strategy_id {strategy_id!r} not found"
            ],
        }
    errors = m.validate_params(params)
    return {"ok": len(errors) == 0, "errors": errors}


# -------------------------------------------------------------
# 构造（一般后端用，前端不直接调）
# -------------------------------------------------------------
def create_strategy(
    strategy_id: str,
    params: Optional[Dict[str, Any]] = None,
    version: str = "latest",
    reg: Optional[StrategyRegistry] = None,
) -> Dict[str, Any]:
    """
    服务端构造策略实例（一般不通过 API 暴露给前端）

    返回 {"cls": <class>, "instance": <obj>, "params": {...}}
    """
    reg = reg or get_strategy_registry()
    inst = reg.create(strategy_id, params, version=version)
    m = reg.get(strategy_id)
    return {
        "cls": inst.__class__,
        "instance": inst,
        "params": dict(
            params
            or (m.default_parameters if m else {})
        ),
        "metadata_id": m.id if m else None,
        "version": m.version if m else None,
    }
