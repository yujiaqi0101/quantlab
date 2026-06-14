"""
CheckpointManager：定期保存（V3.3 第二件事）

策略：
    by_time        每隔 N 秒
    by_ticks       每隔 N 根 bar
    by_trades      每成交 N 笔
    by_signal      每次发信号

用法：
    cm = CheckpointManager(
        strategy="by_ticks", interval=100,
        base_dir="checkpoints",
    )
    for i, ts in enumerate(bar_iter):
        if cm.should_save(tick=i, trade_count=...):
            snap = StateSnapshot.capture(...)
            cm.save(snap)
    cm.save(snap)  # 末次必存
"""

from __future__ import annotations

import os
import time
from typing import Optional

from .state_store import StateSnapshot


class CheckpointManager:
    """
    V3.3 CheckpointManager

    写入路径：
        checkpoints/
            meta.json           {latest: 5, count: 12}
            0001.json
            0002.json
            ...
    """

    def __init__(
        self,
        strategy: str = "by_ticks",
        interval: int = 100,
        base_dir: str = "checkpoints",
        max_keep: int = 20,
    ):
        if strategy not in (
            "by_time",
            "by_ticks",
            "by_trades",
            "by_signal",
        ):
            raise ValueError(f"unknown strategy: {strategy}")
        self.strategy = strategy
        self.interval = int(interval)
        self.base_dir = base_dir
        self.max_keep = int(max_keep)
        os.makedirs(base_dir, exist_ok=True)
        self._counter = 0
        self._last_save_time = time.time()
        self._meta_path = os.path.join(base_dir, "meta.json")
        # 复用历史 counter
        if os.path.exists(self._meta_path):
            try:
                import json
                with open(
                    self._meta_path, "r", encoding="utf-8"
                ) as f:
                    meta = json.load(f)
                self._counter = int(meta.get("count", 0))
            except Exception:
                self._counter = 0

    # ---- 决策 ----
    def should_save(
        self,
        tick: int = 0,
        trade_count: int = 0,
        signal: bool = False,
    ) -> bool:
        if self.strategy == "by_ticks":
            return tick > 0 and tick % self.interval == 0
        if self.strategy == "by_trades":
            return (
                trade_count > 0
                and trade_count % self.interval == 0
            )
        if self.strategy == "by_time":
            now = time.time()
            return (
                now - self._last_save_time
                >= self.interval
            )
        if self.strategy == "by_signal":
            return signal
        return False

    # ---- 落盘 ----
    def save(self, snapshot: StateSnapshot) -> str:
        self._counter += 1
        snapshot.version = self._counter
        path = os.path.join(
            self.base_dir,
            f"{self._counter:06d}.json",
        )
        snapshot.save(path)
        self._last_save_time = time.time()
        self._write_meta(latest=self._counter)
        self._gc()
        return path

    def latest(self) -> Optional[StateSnapshot]:
        if self._counter == 0:
            return None
        path = os.path.join(
            self.base_dir, f"{self._counter:06d}.json"
        )
        if not os.path.exists(path):
            return None
        return StateSnapshot.load(path)

    def _write_meta(self, latest: int) -> None:
        import json
        meta = {
            "latest": latest,
            "count": self._counter,
        }
        with open(
            self._meta_path, "w", encoding="utf-8"
        ) as f:
            json.dump(meta, f, indent=2)

    def _gc(self) -> None:
        if self.max_keep <= 0:
            return
        # 留最近 max_keep 个
        for i in range(1, self._counter - self.max_keep + 1):
            path = os.path.join(
                self.base_dir, f"{i:06d}.json"
            )
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
