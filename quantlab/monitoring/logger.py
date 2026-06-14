"""
TradeLogger：统一日志（V3.2）

V2.5 已有 LiveLogger（3 路：orders / trades / errors）
V3.2 增强：
    1) 统一字段: timestamp / event_type / symbol / action / price / qty / pnl / source
    2) JSON Lines 输出（grep / awk / ELK 友好）
    3) source 区分 backtest / paper / live
    4) 共享 EventBus 监听：自动 log OrderEvent / FillEvent

V2.5 旧接口 (LiveLogger.order / .trade / .reject) 保持兼容
    通过 monitoring.__init__ 走 Re-export
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class LogRecord:
    """统一日志记录"""
    timestamp: str
    event_type: str        # ORDER / FILL / REJECT / ERROR / METRIC / ALERT / KILL
    source: str            # backtest / paper / live
    symbol: str = ""
    action: str = ""       # BUY / SELL / CLOSE / RAISE / ...
    price: float = 0.0
    qty: int = 0
    pnl: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def to_json(self) -> str:
        d = {
            "ts": self.timestamp,
            "event": self.event_type,
            "source": self.source,
            "symbol": self.symbol,
            "action": self.action,
            "price": self.price,
            "qty": self.qty,
            "pnl": self.pnl,
            "trace_id": self.trace_id,
        }
        d.update(self.extra)
        return json.dumps(d, ensure_ascii=False, default=str)


class TradeLogger:
    """
    V3.2 TradeLogger

    用法：
        logger = TradeLogger(source="paper", log_dir="logs")
        rec = LogRecord(
            timestamp=ts, event_type="FILL", source="paper",
            symbol="AAPL", action="BUY", price=150.0, qty=10,
        )
        logger.log(rec)

    V2.5 兼容：
        logger.order(local_id, symbol, qty, ts)
        logger.trade(symbol, qty, price, ts)
        logger.reject(symbol, qty, reason)
        logger.error(msg)
    """

    def __init__(
        self,
        source: str = "backtest",
        log_dir: str = "logs",
        log_to_console: bool = True,
    ):
        self.source = source
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # 主 logger
        self._logger = logging.getLogger(f"quantlab.monitor.{source}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            # 文件
            path = os.path.join(
                log_dir, f"events_{source}.log"
            )
            fh = RotatingFileHandler(
                path,
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setFormatter(
                logging.Formatter("%(message)s")
            )
            self._logger.addHandler(fh)

            # 控制台
            if log_to_console:
                ch = logging.StreamHandler(sys.stdout)
                ch.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(name)s] %(message)s"
                    )
                )
                self._logger.addHandler(ch)

    # ---- 统一接口 ----
    def log(self, record: LogRecord) -> None:
        self._logger.info(record.to_json())

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    # ---- V2.5 兼容旧接口 ----
    def order(
        self,
        local_id: str,
        symbol: str,
        qty: int,
        ts: Any,
    ) -> None:
        self._logger.info(
            LogRecord(
                timestamp=str(ts) if ts is not None else _now_iso(),
                event_type="ORDER",
                source=self.source,
                symbol=symbol,
                action="BUY" if qty > 0 else "SELL",
                qty=qty,
                extra={"local_id": local_id},
            ).to_json()
        )

    def trade(
        self,
        symbol: str,
        qty: int,
        price: float,
        ts: Any,
    ) -> None:
        self._logger.info(
            LogRecord(
                timestamp=str(ts) if ts is not None else _now_iso(),
                event_type="FILL",
                source=self.source,
                symbol=symbol,
                action="BUY" if qty > 0 else "SELL",
                price=price,
                qty=qty,
            ).to_json()
        )

    def reject(
        self,
        symbol: str,
        qty: int,
        reason: str,
    ) -> None:
        self._logger.warning(
            LogRecord(
                timestamp=_now_iso(),
                event_type="REJECT",
                source=self.source,
                symbol=symbol,
                qty=qty,
                extra={"reason": reason},
            ).to_json()
        )

    def kill(
        self,
        reason: str,
        pnl: float = 0.0,
    ) -> None:
        self._logger.error(
            LogRecord(
                timestamp=_now_iso(),
                event_type="KILL",
                source=self.source,
                pnl=pnl,
                extra={"reason": reason},
            ).to_json()
        )


def new_trace_id() -> str:
    """生成链路 ID（4 字节十六进制）"""
    return uuid.uuid4().hex[:8]
