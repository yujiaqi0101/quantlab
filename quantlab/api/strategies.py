"""
Strategies API — 策略管理

端点：
  GET  /api/v1/strategies              列表
  GET  /api/v1/strategies/{id}         详情
  POST /api/v1/strategies/{id}/validate 参数校验
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("quantlab.api.strategies")

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])

DB_PATH = os.environ.get("STRATEGIES_DB", "storage/strategies.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS strategies (
            id          TEXT PRIMARY KEY,
            name        TEXT DEFAULT '',
            description TEXT DEFAULT '',
            version     TEXT DEFAULT '1.0.0',
            tags_json   TEXT DEFAULT '[]',
            params_json TEXT DEFAULT '[]',
            param_space_json TEXT DEFAULT '{}',
            class_path  TEXT DEFAULT '',
            category    TEXT DEFAULT ''
        );
    """)
    count = conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
    if count == 0:
        samples = [
            ("sma_cross", "SMA Crossover", "Simple moving average crossover strategy", "1.0.0",
             ["trend", "classic"], "quantlab.strategies.sma_cross",
             [{"name": "fast_period", "type": "int", "default": 10, "min_value": 2, "max_value": 100, "step": 1, "description": "Fast SMA period"},
              {"name": "slow_period", "type": "int", "default": 30, "min_value": 5, "max_value": 200, "step": 1, "description": "Slow SMA period"}],
             {"fast_period": [5, 10, 20, 30], "slow_period": [20, 30, 50, 60]}, "trend"),
            ("rsi_reversal", "RSI Reversal", "RSI overbought/oversold mean reversion", "1.0.0",
             ["mean_reversion", "oscillator"], "quantlab.strategies.rsi_reversal",
             [{"name": "period", "type": "int", "default": 14, "min_value": 2, "max_value": 50, "step": 1, "description": "RSI period"},
              {"name": "overbought", "type": "float", "default": 70.0, "min_value": 50.0, "max_value": 95.0, "step": 1.0, "description": "Overbought threshold"},
              {"name": "oversold", "type": "float", "default": 30.0, "min_value": 5.0, "max_value": 50.0, "step": 1.0, "description": "Oversold threshold"}],
             {"period": [7, 14, 21], "overbought": [65, 70, 75, 80], "oversold": [20, 25, 30, 35]}, "mean_reversion"),
            ("bollinger_breakout", "Bollinger Breakout", "Bollinger Bands breakout strategy", "1.1.0",
             ["volatility", "breakout"], "quantlab.strategies.bollinger_breakout",
             [{"name": "period", "type": "int", "default": 20, "min_value": 5, "max_value": 50, "step": 1, "description": "BB period"},
              {"name": "num_std", "type": "float", "default": 2.0, "min_value": 1.0, "max_value": 4.0, "step": 0.5, "description": "Number of standard deviations"}],
             {"period": [10, 20, 30], "num_std": [1.5, 2.0, 2.5, 3.0]}, "volatility"),
            ("macd_trend", "MACD Trend Following", "MACD-based trend following strategy", "1.0.0",
             ["trend", "momentum"], "quantlab.strategies.macd_trend",
             [{"name": "fast_period", "type": "int", "default": 12, "min_value": 2, "max_value": 50, "step": 1, "description": "Fast EMA period"},
              {"name": "slow_period", "type": "int", "default": 26, "min_value": 5, "max_value": 100, "step": 1, "description": "Slow EMA period"},
              {"name": "signal_period", "type": "int", "default": 9, "min_value": 2, "max_value": 30, "step": 1, "description": "Signal line period"}],
             {"fast_period": [8, 12, 16], "slow_period": [20, 26, 32], "signal_period": [7, 9, 12]}, "trend"),
            ("dual_ma_momentum", "Dual MA Momentum", "Dual moving average with momentum filter", "1.2.0",
             ["trend", "momentum"], "quantlab.strategies.dual_ma_momentum",
             [{"name": "fast_period", "type": "int", "default": 10, "min_value": 2, "max_value": 100, "step": 1, "description": "Fast MA period"},
              {"name": "slow_period", "type": "int", "default": 30, "min_value": 5, "max_value": 200, "step": 1, "description": "Slow MA period"},
              {"name": "momentum_period", "type": "int", "default": 14, "min_value": 2, "max_value": 50, "step": 1, "description": "Momentum lookback"},
              {"name": "use_classifier", "type": "bool", "default": False, "description": "Use classifier instead of regressor"}],
             {"fast_period": [5, 10, 20], "slow_period": [20, 30, 50], "momentum_period": [7, 14, 21]}, "trend"),
        ]
        for s in samples:
            # 元组结构: (id, name, desc, version, tags, class_path, params, param_space, category)
            conn.execute(
                "INSERT OR IGNORE INTO strategies (id, name, description, version, tags_json, params_json, param_space_json, class_path, category) VALUES (?,?,?,?,?,?,?,?,?)",
                [s[0], s[1], s[2], s[3], json.dumps(s[4]), json.dumps(s[6]), json.dumps(s[7]), s[5], s[8]],
            )
        conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["tags"] = json.loads(d.pop("tags_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["tags"] = []
    try:
        d["parameters"] = json.loads(d.pop("params_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["parameters"] = []
    try:
        d["param_space"] = json.loads(d.pop("param_space_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        d["param_space"] = {}
    return d


@router.get("")
async def list_strategies(q: Optional[str] = None, tags: Optional[str] = None):
    conn = _get_conn()
    clauses = []
    params_list: list = []
    if q:
        clauses.append("(name LIKE ? OR description LIKE ?)")
        params_list += [f"%{q}%", f"%{q}%"]
    if tags:
        clauses.append("tags_json LIKE ?")
        params_list.append(f"%{tags}%")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(f"SELECT * FROM strategies{where} ORDER BY name", params_list).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM strategies WHERE id = ?", [strategy_id]).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, f"Strategy {strategy_id} not found")
    return _row_to_dict(row)


class ValidateRequest(BaseModel):
    params: Dict[str, Any]


@router.post("/{strategy_id}/validate")
async def validate_params(strategy_id: str, req: ValidateRequest):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM strategies WHERE id = ?", [strategy_id]).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, f"Strategy {strategy_id} not found")
    errors = []
    try:
        params_def = json.loads(row["params_json"])
    except (json.JSONDecodeError, TypeError):
        params_def = []
    for p in params_def:
        name = p.get("name", "")
        if name in req.params:
            val = req.params[name]
            if p.get("min_value") is not None and val < p["min_value"]:
                errors.append(f"{name} must be >= {p['min_value']}")
            if p.get("max_value") is not None and val > p["max_value"]:
                errors.append(f"{name} must be <= {p['max_value']}")
    return {"ok": len(errors) == 0, "errors": errors}
