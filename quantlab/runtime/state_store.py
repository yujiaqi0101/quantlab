"""
StateSnapshot：系统状态快照（V3.3 第一件事）

V3.3 核心可恢复单元：
    timestamp         时间戳
    cash              现金
    equity            净值
    positions         持仓 {symbol: {qty, avg_price, realized_pnl}}
    open_orders       未成交订单
    closed_trades     已平仓记录（最近 N 条）
    last_prices       最近价
    pnl               累计盈亏
    pnl_realized      已实现
    pnl_unrealized    未实现
    metrics_snapshot  指标快照（V3.2 metrics.snapshot()）
    version           checkpoint 版本号

序列化：
    .to_dict()      → dict（可 JSON 化）
    .from_dict(d)   → StateSnapshot
    .save(path)     → JSON
    .load(path)     → StateSnapshot
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class StateSnapshot:
    """V3.3 系统状态快照"""
    timestamp: str
    cash: float = 0.0
    equity: float = 0.0
    pnl: float = 0.0
    pnl_realized: float = 0.0
    pnl_unrealized: float = 0.0
    positions: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )
    open_orders: List[Dict[str, Any]] = field(
        default_factory=list
    )
    closed_trades: List[Dict[str, Any]] = field(
        default_factory=list
    )
    last_prices: Dict[str, float] = field(
        default_factory=dict
    )
    metrics_snapshot: Dict[str, Any] = field(
        default_factory=dict
    )
    version: int = 0
    source: str = "backtest"
    extra: Dict[str, Any] = field(
        default_factory=dict
    )

    # ---- 序列化 ----
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StateSnapshot":
        # 兼容缺字段
        return cls(
            timestamp=d.get("timestamp", _now_iso()),
            cash=float(d.get("cash", 0.0)),
            equity=float(d.get("equity", 0.0)),
            pnl=float(d.get("pnl", 0.0)),
            pnl_realized=float(d.get("pnl_realized", 0.0)),
            pnl_unrealized=float(d.get("pnl_unrealized", 0.0)),
            positions=dict(d.get("positions", {})),
            open_orders=list(d.get("open_orders", [])),
            closed_trades=list(d.get("closed_trades", [])),
            last_prices=dict(d.get("last_prices", {})),
            metrics_snapshot=dict(d.get("metrics_snapshot", {})),
            version=int(d.get("version", 0)),
            source=str(d.get("source", "backtest")),
            extra=dict(d.get("extra", {})),
        )

    def save(self, path: str) -> None:
        os.makedirs(
            os.path.dirname(path) or ".", exist_ok=True
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                self.to_dict(),
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    @classmethod
    def load(cls, path: str) -> "StateSnapshot":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ---- 工厂：从 Portfolio / Broker 抓 ----
    @classmethod
    def capture(
        cls,
        timestamp: Any = None,
        portfolio=None,
        broker=None,
        tradebook=None,
        open_orders: Optional[List[Dict]] = None,
        metrics_snap: Optional[Dict] = None,
        source: str = "backtest",
        version: int = 0,
        extra: Optional[Dict] = None,
    ) -> "StateSnapshot":
        """
        V3.3 标准 capture：
            1) 从 portfolio 拿 cash / equity / positions
            2) 从 broker 拿当前 cash / positions 做交叉对账
            3) open_orders 由 caller 传（Execution 层持引用）
            4) tradebook 提供最近 N 条 closed_trades
        """
        ts = (
            str(timestamp) if timestamp is not None else _now_iso()
        )

        cash = getattr(portfolio, "cash", 0.0)
        equity = (
            portfolio.equity() if portfolio is not None
            and hasattr(portfolio, "equity")
            else 0.0
        )
        pnl = equity - 100000.0   # 简单约定：vs 初始

        positions: Dict[str, Dict[str, Any]] = {}
        if portfolio is not None and hasattr(portfolio, "positions"):
            for s, pos in portfolio.positions.items():
                positions[s] = {
                    "qty": getattr(pos, "qty", 0),
                    "avg_price": getattr(pos, "avg_price", 0.0),
                    "realized_pnl": getattr(
                        pos, "realized_pnl", 0.0
                    ),
                }

        last_prices: Dict[str, float] = {}
        if portfolio is not None and hasattr(portfolio, "last_prices"):
            last_prices = dict(portfolio.last_prices)

        closed_trades: List[Dict] = []
        if tradebook is not None and hasattr(tradebook, "closed_trades"):
            for t in tradebook.closed_trades[-100:]:
                closed_trades.append({
                    "symbol": getattr(t, "symbol", ""),
                    "qty": getattr(t, "qty", 0),
                    "entry_price": getattr(t, "entry_price", 0.0),
                    "exit_price": getattr(t, "exit_price", 0.0),
                    "pnl": getattr(t, "pnl", 0.0),
                    "entry_time": str(getattr(t, "entry_time", "")),
                    "exit_time": str(getattr(t, "exit_time", "")),
                })

        return cls(
            timestamp=ts,
            cash=cash,
            equity=equity,
            pnl=pnl,
            pnl_realized=sum(
                p.get("realized_pnl", 0.0)
                for p in positions.values()
            ),
            pnl_unrealized=pnl - sum(
                p.get("realized_pnl", 0.0)
                for p in positions.values()
            ),
            positions=positions,
            open_orders=open_orders or [],
            closed_trades=closed_trades,
            last_prices=last_prices,
            metrics_snapshot=metrics_snap or {},
            source=source,
            version=version,
            extra=extra or {},
        )
