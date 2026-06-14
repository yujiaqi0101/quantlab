"""
AlertManager：告警规则引擎（V3.2）

V3.2 规则集（V1 简化）：
    pnl_threshold       异常 PnL（绝对值或相对）
    slippage_threshold  单笔成交滑点过大
    consecutive_loss    连续 N 笔亏损
    fill_failure        成交失败
    drawdown_breach     回撤超过阈值

通道（V3.2 stub）：
    console             控制台 print
    log                 写 logs/alerts.log
    webhook             POST 到外部 URL（V3.2 留 stub）

每条 alert 含：
    rule_name, level (info/warn/critical), message, payload, ts
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Dict, List, Optional


ALERT_LEVEL_INFO = "INFO"
ALERT_LEVEL_WARN = "WARN"
ALERT_LEVEL_CRITICAL = "CRITICAL"


@dataclass
class Alert:
    rule_name: str
    level: str
    message: str
    payload: Dict = field(default_factory=dict)
    timestamp: str = ""


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class AlertRule:
    """规则基类"""
    name: str = "BASE"

    def check(
        self,
        snapshot: Dict,
    ) -> Optional[Alert]:
        # True → return None (no alert)
        # False / 触发条件 → return Alert(...)
        ...


class PnLThresholdRule(AlertRule):
    """P&L 跌幅超过阈值触发"""
    name = "PNL_THRESHOLD"

    def __init__(self, max_loss_pnl: float = -1000.0):
        self.max_loss_pnl = max_loss_pnl

    def check(self, snapshot):
        pnl = snapshot.get("pnl", 0.0)
        if pnl <= self.max_loss_pnl:
            return Alert(
                rule_name=self.name,
                level=ALERT_LEVEL_CRITICAL,
                message=f"PnL {pnl:.2f} 跌穿阈值 {self.max_loss_pnl}",
                payload={"pnl": pnl},
            )
        return None


class DrawdownBreachRule(AlertRule):
    """回撤超过阈值触发"""
    name = "DRAWDOWN_BREACH"

    def __init__(self, max_dd: float = -0.10):
        self.max_dd = max_dd

    def check(self, snapshot):
        dd = snapshot.get("drawdown", 0.0)
        if dd <= self.max_dd:
            return Alert(
                rule_name=self.name,
                level=ALERT_LEVEL_CRITICAL,
                message=(
                    f"Drawdown {dd*100:.2f}% 跌穿"
                    f" {self.max_dd*100:.2f}%"
                ),
                payload={"drawdown": dd},
            )
        return None


class ConsecutiveLossRule(AlertRule):
    """连续亏损 N 笔触发"""
    name = "CONSECUTIVE_LOSS"

    def __init__(self, n: int = 5):
        self.n = n
        self._recent: List[float] = []

    def check(self, snapshot):
        # 需要外部把 trade pnl 灌进 snapshot["last_pnl"]
        last = snapshot.get("last_pnl")
        if last is not None:
            self._recent.append(last)
            if len(self._recent) > 20:
                self._recent = self._recent[-20:]

        if len(self._recent) < self.n:
            return None
        if all(p < 0 for p in self._recent[-self.n:]):
            return Alert(
                rule_name=self.name,
                level=ALERT_LEVEL_WARN,
                message=(
                    f"连续 {self.n} 笔亏损，"
                    f"最近 PnL={self._recent[-self.n:]}"
                ),
                payload={
                    "n": self.n,
                    "pnl_seq": self._recent[-self.n:],
                },
            )
        return None


class FillFailureRule(AlertRule):
    """成交失败率过高"""
    name = "FILL_FAILURE"

    def __init__(self, max_failure_rate: float = 0.30):
        self.max_failure_rate = max_failure_rate

    def check(self, snapshot):
        n_trade = snapshot.get("trade_count", 0)
        n_reject = snapshot.get("reject_count", 0)
        total = n_trade + n_reject
        if total < 5:
            return None
        rate = n_reject / total
        if rate >= self.max_failure_rate:
            return Alert(
                rule_name=self.name,
                level=ALERT_LEVEL_WARN,
                message=(
                    f"拒单率 {rate*100:.1f}% "
                    f">= {self.max_failure_rate*100:.1f}%"
                ),
                payload={
                    "rate": rate,
                    "trade": n_trade,
                    "reject": n_reject,
                },
            )
        return None


class AlertManager:
    """
    V3.2 告警管理

    用法：
        am = AlertManager(log_dir="logs")
        am.add_rule(PnLThresholdRule(max_loss_pnl=-500))
        am.add_rule(DrawdownBreachRule(max_dd=-0.10))
        am.add_rule(ConsecutiveLossRule(n=5))
        am.add_rule(FillFailureRule(max_failure_rate=0.30))
        # 在主循环里：
        am.check_and_dispatch(snapshot)
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self._webhook_urls: List[str] = []

        # alerts log
        self._logger = logging.getLogger(
            "quantlab.alerts"
        )
        self._logger.setLevel(logging.WARNING)
        self._logger.propagate = False
        if not self._logger.handlers:
            fh = RotatingFileHandler(
                os.path.join(log_dir, "alerts.log"),
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(message)s"
                )
            )
            self._logger.addHandler(fh)

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def add_webhook(self, url: str) -> None:
        self._webhook_urls.append(url)

    def check_and_dispatch(
        self,
        snapshot: Dict,
    ) -> List[Alert]:
        fired: List[Alert] = []
        for rule in self.rules:
            alert = rule.check(snapshot)
            if alert is None:
                continue
            alert.timestamp = _now_iso()
            self.alerts.append(alert)
            self._dispatch(alert)
            fired.append(alert)
        return fired

    def _dispatch(self, alert: Alert) -> None:
        # console
        print(
            f"[ALERT {alert.level} {alert.rule_name}] "
            f"{alert.message}"
        )
        # log
        self._logger.warning(json.dumps({
            "ts": alert.timestamp,
            "rule": alert.rule_name,
            "level": alert.level,
            "message": alert.message,
            "payload": alert.payload,
        }, ensure_ascii=False))
        # webhook stub
        for url in self._webhook_urls:
            try:
                # V3.2 stub
                # 用户自行实现：requests.post(url, json=asdict(alert))
                pass
            except Exception:
                pass
