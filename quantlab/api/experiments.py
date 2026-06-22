"""
Experiments API — 回测实验管理

端点：
  GET    /api/v1/experiments                     列表（支持筛选）
  POST   /api/v1/experiments/search              高级搜索
  GET    /api/v1/experiments/{id}                详情
  DELETE /api/v1/experiments/{id}                删除
  GET    /api/v1/experiments/{id}/equity         权益曲线
  GET    /api/v1/experiments/{id}/trades         交易记录
  POST   /api/v1/experiments/compare             对比
  GET    /api/v1/experiments/{id}/tags            标签列表
  POST   /api/v1/experiments/{id}/tags            添加标签
  DELETE /api/v1/experiments/{id}/tags            删除标签
  GET    /api/v1/experiments/tags/list            所有可用标签
  PUT    /api/v1/experiments/{id}/status          设置状态
  PUT    /api/v1/experiments/{id}/favorite        设置收藏
  PUT    /api/v1/experiments/{id}/folder          设置文件夹
  GET    /api/v1/experiments/folders/list         文件夹列表
  GET    /api/v1/experiments/{id}/analytics       分析数据
  GET    /api/v1/experiments/rank                 排行榜
  PUT    /api/v1/experiments/{id}/note            设置备注
  PUT    /api/v1/experiments/{id}/parent          设置父实验
  GET    /api/v1/experiments/{id}/lineage         血缘关系
  GET    /api/v1/experiments/{id}/activity        活动记录
  GET    /api/v1/experiments/timeline/global      全局时间线
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("quantlab.api.experiments")

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])

# ---- SQLite 存储 ----
DB_PATH = os.environ.get("EXPERIMENTS_DB", "storage/experiments.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS experiments (
            id                TEXT PRIMARY KEY,
            name              TEXT DEFAULT '',
            strategy          TEXT DEFAULT '',
            created_at        TEXT DEFAULT '',
            tag               TEXT DEFAULT '',
            note              TEXT DEFAULT '',
            dataset_id        TEXT DEFAULT '',
            dataset_version   TEXT DEFAULT '',
            strategy_version  TEXT DEFAULT '',
            final_equity      REAL DEFAULT 0,
            total_return      REAL DEFAULT 0,
            sharpe            REAL DEFAULT 0,
            max_drawdown      REAL DEFAULT 0,
            trade_count       INTEGER DEFAULT 0,
            win_rate          REAL DEFAULT 0,
            source            TEXT DEFAULT 'backtest',
            params            TEXT DEFAULT '{}',
            tags_json         TEXT DEFAULT '[]',
            status            TEXT DEFAULT 'normal',
            folder            TEXT DEFAULT '',
            favorite          INTEGER DEFAULT 0,
            parent_id         TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS experiment_tags (
            experiment_id TEXT,
            tag           TEXT,
            PRIMARY KEY (experiment_id, tag)
        );
        CREATE TABLE IF NOT EXISTS experiment_activity (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            action        TEXT,
            detail        TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );
    """)
    return conn


# ---- 请求模型 ----

class SearchRequest(BaseModel):
    q: Optional[str] = None
    strategy: Optional[str] = None
    dataset_id: Optional[str] = None
    sharpe_gt: Optional[float] = None
    sharpe_lt: Optional[float] = None
    return_gt: Optional[float] = None
    return_lt: Optional[float] = None
    max_dd_lt: Optional[float] = None
    trade_count_gt: Optional[int] = None
    tags: Optional[List[str]] = None
    limit: int = 50


class CompareRequest(BaseModel):
    experiment_ids: List[str]
    include_equity: bool = True
    include_trades: bool = False


class StatusRequest(BaseModel):
    status: str


class FavoriteRequest(BaseModel):
    favorite: bool


class FolderRequest(BaseModel):
    folder: str


class NoteRequest(BaseModel):
    note: str


class ParentRequest(BaseModel):
    parent_id: str


class TagAddRequest(BaseModel):
    tag: str


# ---- 辅助 ----

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["params"] = json.loads(d.get("params") or "{}")
    except (json.JSONDecodeError, TypeError):
        d["params"] = {}
    try:
        d["tags_json"] = json.loads(d.get("tags_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["tags_json"] = []
    return d


# ---- 端点 ----

@router.get("")
async def list_experiments(
    strategy: Optional[str] = None,
    dataset_id: Optional[str] = None,
    tag: Optional[str] = None,
    sharpe_min: Optional[float] = None,
    max_dd_max: Optional[float] = None,
    return_min: Optional[float] = None,
    limit: int = 50,
):
    conn = _get_conn()
    clauses = []
    params_list: list = []
    if strategy:
        clauses.append("strategy = ?")
        params_list.append(strategy)
    if dataset_id:
        clauses.append("dataset_id = ?")
        params_list.append(dataset_id)
    if tag:
        clauses.append("tag = ?")
        params_list.append(tag)
    if sharpe_min is not None:
        clauses.append("sharpe >= ?")
        params_list.append(sharpe_min)
    if max_dd_max is not None:
        clauses.append("max_drawdown <= ?")
        params_list.append(max_dd_max)
    if return_min is not None:
        clauses.append("total_return >= ?")
        params_list.append(return_min)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM experiments{where} ORDER BY created_at DESC LIMIT ?",
        params_list + [limit],
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


@router.post("/search")
async def search_experiments(req: SearchRequest):
    conn = _get_conn()
    clauses = []
    params_list: list = []
    if req.q:
        clauses.append("(name LIKE ? OR strategy LIKE ?)")
        params_list += [f"%{req.q}%", f"%{req.q}%"]
    if req.strategy:
        clauses.append("strategy = ?")
        params_list.append(req.strategy)
    if req.dataset_id:
        clauses.append("dataset_id = ?")
        params_list.append(req.dataset_id)
    if req.sharpe_gt is not None:
        clauses.append("sharpe > ?")
        params_list.append(req.sharpe_gt)
    if req.sharpe_lt is not None:
        clauses.append("sharpe < ?")
        params_list.append(req.sharpe_lt)
    if req.return_gt is not None:
        clauses.append("total_return > ?")
        params_list.append(req.return_gt)
    if req.return_lt is not None:
        clauses.append("total_return < ?")
        params_list.append(req.return_lt)
    if req.max_dd_lt is not None:
        clauses.append("max_drawdown < ?")
        params_list.append(req.max_dd_lt)
    if req.trade_count_gt is not None:
        clauses.append("trade_count > ?")
        params_list.append(req.trade_count_gt)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM experiments{where} ORDER BY created_at DESC LIMIT ?",
        params_list + [req.limit],
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


@router.get("/tags/list")
async def list_all_tags():
    conn = _get_conn()
    rows = conn.execute("SELECT DISTINCT tag FROM experiment_tags ORDER BY tag").fetchall()
    conn.close()
    return {r["tag"]: r["tag"] for r in rows}


@router.get("/folders/list")
async def list_folders():
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT folder FROM experiments WHERE folder != '' ORDER BY folder"
    ).fetchall()
    conn.close()
    return [r["folder"] for r in rows]


@router.get("/rank")
async def get_leaderboard(
    metric: str = "sharpe",
    top: int = 20,
    strategy: Optional[str] = None,
):
    allowed = {"sharpe", "total_return", "win_rate", "final_equity"}
    if metric not in allowed:
        metric = "sharpe"
    conn = _get_conn()
    where = " WHERE strategy = ?" if strategy else ""
    params_list = [strategy] if strategy else []
    rows = conn.execute(
        f"SELECT * FROM experiments{where} ORDER BY {metric} DESC LIMIT ?",
        params_list + [top],
    ).fetchall()
    conn.close()
    result = []
    for i, r in enumerate(_row_to_dict(r) for r in rows):
        r["rank"] = i + 1
        result.append(r)
    return result


@router.get("/timeline/global")
async def global_timeline(limit: int = 50):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT a.*, e.name, e.strategy, e.status FROM experiment_activity a "
        "LEFT JOIN experiments e ON a.experiment_id = e.id "
        "ORDER BY a.created_at DESC LIMIT ?",
        [limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/compare")
async def compare_experiments(req: CompareRequest):
    conn = _get_conn()
    placeholders = ",".join("?" * len(req.experiment_ids))
    rows = conn.execute(
        f"SELECT * FROM experiments WHERE id IN ({placeholders})",
        req.experiment_ids,
    ).fetchall()
    experiments = [_row_to_dict(r) for r in rows]
    equity_curves = {}
    for exp in experiments:
        equity_curves[exp["id"]] = {
            "experiment_id": exp["id"],
            "timestamps": [],
            "equity": [],
        }
    conn.close()
    return {
        "experiments": experiments,
        "equity_curves": equity_curves,
        "param_diff": {},
        "metrics_comparison": {e["id"]: {k: e.get(k) for k in ("sharpe", "total_return", "max_drawdown", "win_rate")} for e in experiments},
    }


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM experiments WHERE id = ?", [experiment_id]).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, f"Experiment {experiment_id} not found")
    return _row_to_dict(row)


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM experiments WHERE id = ?", [experiment_id])
    conn.execute("DELETE FROM experiment_tags WHERE experiment_id = ?", [experiment_id])
    conn.execute("DELETE FROM experiment_activity WHERE experiment_id = ?", [experiment_id])
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/{experiment_id}/equity")
async def get_equity_curve(experiment_id: str):
    return {"experiment_id": experiment_id, "timestamps": [], "equity": []}


@router.get("/{experiment_id}/trades")
async def get_trades(experiment_id: str):
    return []


@router.get("/{experiment_id}/tags")
async def get_tags(experiment_id: str):
    conn = _get_conn()
    rows = conn.execute("SELECT tag FROM experiment_tags WHERE experiment_id = ?", [experiment_id]).fetchall()
    conn.close()
    return [r["tag"] for r in rows]


@router.post("/{experiment_id}/tags")
async def add_tag(experiment_id: str, req: TagAddRequest):
    conn = _get_conn()
    conn.execute("INSERT OR IGNORE INTO experiment_tags (experiment_id, tag) VALUES (?, ?)", [experiment_id, req.tag])
    conn.commit()
    rows = conn.execute("SELECT tag FROM experiment_tags WHERE experiment_id = ?", [experiment_id]).fetchall()
    conn.close()
    return {"tags": [r["tag"] for r in rows]}


@router.delete("/{experiment_id}/tags")
async def remove_tag(experiment_id: str, req: TagAddRequest):
    conn = _get_conn()
    conn.execute("DELETE FROM experiment_tags WHERE experiment_id = ? AND tag = ?", [experiment_id, req.tag])
    conn.commit()
    rows = conn.execute("SELECT tag FROM experiment_tags WHERE experiment_id = ?", [experiment_id]).fetchall()
    conn.close()
    return {"tags": [r["tag"] for r in rows]}


@router.put("/{experiment_id}/status")
async def set_status(experiment_id: str, req: StatusRequest):
    conn = _get_conn()
    conn.execute("UPDATE experiments SET status = ? WHERE id = ?", [req.status, experiment_id])
    conn.commit()
    conn.close()
    return {"status": req.status}


@router.put("/{experiment_id}/favorite")
async def set_favorite(experiment_id: str, req: FavoriteRequest):
    conn = _get_conn()
    conn.execute("UPDATE experiments SET favorite = ? WHERE id = ?", [1 if req.favorite else 0, experiment_id])
    conn.commit()
    conn.close()
    return {"favorite": req.favorite}


@router.put("/{experiment_id}/folder")
async def set_folder(experiment_id: str, req: FolderRequest):
    conn = _get_conn()
    conn.execute("UPDATE experiments SET folder = ? WHERE id = ?", [req.folder, experiment_id])
    conn.commit()
    conn.close()
    return {"folder": req.folder}


@router.get("/{experiment_id}/analytics")
async def get_analytics(experiment_id: str):
    return {
        "drawdown_curve": [],
        "monthly_returns": {},
        "annual_returns": {},
        "rolling_sharpe": [],
        "rolling_drawdown": [],
        "rolling_volatility": [],
        "rolling_start_index": 0,
        "extended_metrics": {},
        "pnl_distribution": {"counts": [], "edges": []},
        "holding_stats": {"avg_days": 0, "max_days": 0, "min_days": 0, "median_days": 0},
        "top_winners": [],
        "top_losers": [],
    }


@router.put("/{experiment_id}/note")
async def set_note(experiment_id: str, req: NoteRequest):
    conn = _get_conn()
    conn.execute("UPDATE experiments SET note = ? WHERE id = ?", [req.note, experiment_id])
    conn.commit()
    conn.close()
    return {"note": req.note}


@router.put("/{experiment_id}/parent")
async def set_parent(experiment_id: str, req: ParentRequest):
    conn = _get_conn()
    conn.execute("UPDATE experiments SET parent_id = ? WHERE id = ?", [req.parent_id, experiment_id])
    conn.commit()
    conn.close()
    return {"parent_id": req.parent_id}


@router.get("/{experiment_id}/lineage")
async def get_lineage(experiment_id: str):
    return {
        "experiment_id": experiment_id,
        "ancestors": [],
        "children": [],
        "siblings": [],
        "family": {"id": experiment_id, "name": "", "strategy": "", "params": {}, "created_at": "", "parent_id": "", "status": ""},
    }


@router.get("/{experiment_id}/activity")
async def get_activity(experiment_id: str, limit: int = 50):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM experiment_activity WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
        [experiment_id, limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
