"""
EventLog：事件持久化（V3.3 第九件事）

V3.3 必备：
    - 所有事件落盘
    - 启动时可选 replay

支持事件：
    MARKET  (price tick)
    SIGNAL  (strategy decision)
    ORDER   (intent to trade)
    FILL    (actual fill)
    RISK    (risk check pass/fail)
    STATE   (state snapshot)
    META    (start, shutdown, etc.)

与 monitoring/tracer.py 的区别：
    tracer  →  链路追踪（带 trace_id 短暂）
    event_log →  业务事件（append-only，可重放）

存储：
    logs/events/{source}/{YYYY-MM-DD}.jsonl
    一行一个事件（JSON Lines）
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class EventLog:
    """
    V3.3 事件日志

    用法：
        elog = EventLog(source="paper", base_dir="logs/events")
        elog.append("MARKET", symbol="AAPL", price=150.0)
        elog.append("ORDER", symbol="AAPL", qty=10, price=150.0)
        events = elog.read_today()
    """

    def __init__(
        self,
        source: str = "backtest",
        base_dir: str = "logs/events",
    ):
        self.source = source
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self._lock = threading.Lock()
        # 预生成当日文件
        self._current_path = self._make_path()
        self._fh = open(
            self._current_path, "a", encoding="utf-8"
        )

    def _make_path(self) -> str:
        day = datetime.utcnow().strftime("%Y-%m-%d")
        d = os.path.join(self.base_dir, self.source)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{day}.jsonl")

    def _maybe_roll(self) -> None:
        # 日期变化时滚一个文件
        new_path = self._make_path()
        if new_path != self._current_path:
            try:
                self._fh.close()
            except Exception:
                pass
            self._current_path = new_path
            self._fh = open(
                new_path, "a", encoding="utf-8"
            )

    def append(
        self,
        event_type: str,
        trace_id: str = "",
        **payload: Any,
    ) -> None:
        """记一条事件"""
        rec = {
            "ts": _now_iso(),
            "source": self.source,
            "event": event_type,
            "trace_id": trace_id,
        }
        rec.update(payload)
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self._lock:
            self._maybe_roll()
            try:
                self._fh.write(line + "\n")
                self._fh.flush()
            except Exception:
                pass

    def read_today(self) -> List[Dict]:
        path = self._current_path
        return self._read_file(path)

    def read_all(self) -> List[Dict]:
        out: List[Dict] = []
        d = os.path.join(self.base_dir, self.source)
        if not os.path.isdir(d):
            return out
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".jsonl"):
                continue
            out.extend(
                self._read_file(os.path.join(d, fname))
            )
        return out

    def _read_file(self, path: str) -> List[Dict]:
        out: List[Dict] = []
        if not os.path.exists(path):
            return out
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    def close(self) -> None:
        with self._lock:
            try:
                self._fh.close()
            except Exception:
                pass

    # ---- 装饰器 ----
    def wrap(self, event_type: str, **static):
        """装饰器：把函数调用的输入输出记到事件日志"""
        def deco(fn):
            def wrapper(*args, **kwargs):
                self.append(event_type, **static)
                return fn(*args, **kwargs)
            return wrapper
        return deco
