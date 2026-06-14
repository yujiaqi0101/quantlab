"""
ReplayEngine：完整重放 live event flow（V3.3 第六件事）

用途：
    1) 实盘某天亏了
    2) 取那天的 ticks + event_log
    3) 用同一份 strategy / execution 重新跑
    4) 比对原 record vs replay 是否一致

与 ReplayMarketData 的区别：
    ReplayMarketData  只重放行情
    ReplayEngine      重放"行情 + 决策 + 下单 + 成交"全链路
                       → 模拟实盘"断点续跑 + 复盘"能力
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .state_store import StateSnapshot
from .checkpoint import CheckpointManager
from .recovery import RecoveryManager
from ..event.event_bus import event_bus


@dataclass
class ReplayResult:
    """Replay 结果：每根 bar 的"重放应该" vs "实际" """
    bar_index: int
    timestamp: Any
    replayed_action: Optional[str] = None   # 应该是 BUY/SELL/HOLD
    recorded_action: Optional[str] = None   # 实际记录的
    diff: bool = False


class ReplayEngine:
    """
    V3.3 ReplayEngine

    用法：
        # 从 checkpoint 恢复
        cm = CheckpointManager(base_dir="checkpoints")
        rec = RecoveryManager(cm)
        snap = rec.boot()

        re = ReplayEngine(
            data=data_dict,
            snapshot=snap,
            strategy=strategy,
            constructor=constructor,
            execution=exec_,
            event_log_path="logs/events_paper.log",
        )
        results = re.run()
        mismatches = re.diff_summary(results)
    """

    def __init__(
        self,
        data,                        # Dict[symbol, DataFrame]
        snapshot: Optional[StateSnapshot],
        strategy,
        constructor,                 # PortfolioConstruction
        execution,
        event_log_path: Optional[str] = None,
        start_bar: int = 0,
    ):
        self.data = data
        self.snapshot = snapshot
        self.strategy = strategy
        self.constructor = constructor
        self.execution = execution
        self.event_log_path = event_log_path
        self.start_bar = start_bar

        self._recorded_actions: Dict[int, str] = {}
        if event_log_path and os.path.exists(event_log_path):
            self._load_event_log(event_log_path)

    # ---- 公共 API ----
    def run(self) -> List[ReplayResult]:
        """重放从 start_bar 之后的所有 bar"""
        from ..data.context import StrategyContext
        from ..data.cache import factor_cache

        factor_cache.clear()
        str_ctx = StrategyContext(self.data, factor_cache)
        signal = self.strategy.signal(str_ctx)

        results: List[ReplayResult] = []
        sym0 = list(self.data.keys())[0]
        all_ts = list(self.data[sym0].index)

        for i in range(self.start_bar, len(all_ts)):
            ts = all_ts[i]
            if i == 0:
                continue

            prev_scores = signal.iloc[i - 1].to_dict()
            target = self.constructor.construct(prev_scores, ts)
            orders = self.execution.submit(target)

            action = self._infer_action(orders)
            recorded = self._recorded_actions.get(i, "")

            results.append(ReplayResult(
                bar_index=i,
                timestamp=ts,
                replayed_action=action,
                recorded_action=recorded,
                diff=(action != recorded)
                if recorded else False,
            ))

        return results

    def diff_summary(
        self, results: List[ReplayResult]
    ) -> Dict[str, int]:
        n = len(results)
        diffs = sum(1 for r in results if r.diff)
        return {
            "total": n,
            "diffs": diffs,
            "consistent": n - diffs,
        }

    # ---- 内部 ----
    def _infer_action(self, orders) -> Optional[str]:
        if not orders:
            return "HOLD"
        sym = orders[0].symbol
        side = orders[0].side
        return f"{side}:{sym}"

    def _load_event_log(self, path: str) -> None:
        """
        从 event_log 反推每根 bar 实际做了什么
        简化：用每个 fill 的 timestamp 落到的 bar index
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("event") != "FILL":
                        continue
                    ts = rec.get("ts", "")
                    action = f"{rec.get('action','')}:{rec.get('symbol','')}"
                    # 用 ts 落到的 bar
                    idx = self._bar_index_of(ts)
                    if idx is not None:
                        self._recorded_actions[idx] = action
        except Exception:
            pass

    def _bar_index_of(self, ts_str: str) -> Optional[int]:
        if not ts_str or not self.data:
            return None
        sym0 = list(self.data.keys())[0]
        all_ts = list(self.data[sym0].index)
        # 时间戳直接对比
        try:
            import pandas as pd
            target = pd.Timestamp(ts_str)
            for i, t in enumerate(all_ts):
                if pd.Timestamp(t) == target:
                    return i
        except Exception:
            return None
        return None
