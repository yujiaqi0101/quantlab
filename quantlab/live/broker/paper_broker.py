"""
PaperBroker：本地按行情模拟成交

V3.1：
  1) 收到 Order → 拿 last_price → 加 0.5 tick 滑点 → 生成 Fill
  2) 维护本地 positions / cash
  3) 触发 on_fill 回调
  4) 内部 publish FillEvent 到 EventBus（V3.1 新增）

与 Backtest 的区别：
  Backtest   历史 df          理论成交
  Paper      实时行情（Replay / 真实 WS） 模拟撮合
  Live       实时行情                  真实成交

不做：L2 盘口、拆单、改单
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ...core.order import Order
from ...core.fill import Fill
from ...event.event_bus import event_bus
from ...event.event_types import FillEvent
from ...execution.tick_slippage import TickSlippage
from .base import AccountState, BrokerAdapter


class PaperBroker(BrokerAdapter):
    """
    本地模拟 broker

    用法：
        md = ReplayMarketData(data)
        md.subscribe(symbols)
        broker = PaperBroker(md, tick_size=0.01, commission_rate=0.0003)
        broker.connect()
        for tick in md.stream():
            broker.push_tick(tick.symbol, tick.price, tick.timestamp)
            broker.submit_order(order)   # 同步即时成交
    """

    name = "PAPER"

    def __init__(
        self,
        market_data,                           # MarketDataAdapter
        tick_size: float = 0.01,
        commission_rate: float = 0.0003,
        initial_cash: float = 100000.0,
    ):
        self.market_data = market_data
        self.slippage = TickSlippage(tick_size=tick_size)
        self.commission_rate = commission_rate
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}
        self.avg_prices: Dict[str, float] = {}
        self._order_seq = 0
        self._last_prices: Dict[str, float] = {}
        self._last_ts: Dict[str, Any] = {}
        self._connected = False
        self._fill_cb: Optional[Callable] = None
        self.trade_log: List[Fill] = []

        # V3.3：幂等去重（防网络重试重复下单）
        self._seen_client_order_ids: set = set()
        self._client_id_to_broker_id: Dict[str, str] = {}

    # ----------------
    # 连接
    # ----------------
    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    # ----------------
    # 下单
    # ----------------
    def submit_order(self, order: Order) -> str:
        if not self._connected:
            raise RuntimeError("PaperBroker not connected")

        # V3.3：幂等去重（client_order_id）
        cid = getattr(order, "client_order_id", "") or ""
        if cid and cid in self._seen_client_order_ids:
            # 重复提交：返回原 broker_id，不重复成交
            return self._client_id_to_broker_id.get(cid, "")
        if cid:
            self._seen_client_order_ids.add(cid)

        self._order_seq += 1
        broker_id = f"P{self._order_seq:06d}"
        if cid:
            self._client_id_to_broker_id[cid] = broker_id

        # 拿最新价
        last = self._last_prices.get(order.symbol)
        if last is None:
            last = 100.0   # 兜底

        side = "BUY" if order.quantity > 0 else "SELL"
        fill_price = self.slippage.apply(last, side)

        notional = abs(order.quantity) * fill_price
        commission = notional * self.commission_rate

        fill = Fill(
            symbol=order.symbol,
            timestamp=self._last_ts.get(order.symbol),
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
        )

        # 更新本地仓位
        self._apply_fill(fill)
        self.trade_log.append(fill)

        # 触发本地回调
        if self._fill_cb is not None:
            try:
                self._fill_cb(fill)
            except Exception:
                pass

        # V3.1：publish 到 EventBus
        event_bus.publish(FillEvent(
            type="FILL",
            timestamp=fill.timestamp,
            symbol=fill.symbol,
            quantity=fill.quantity,
            price=fill.price,
            commission=fill.commission,
        ))

        return broker_id

    def cancel_order(self, order_id: str) -> bool:
        # V3.1 简化：Paper 即时成交，没法撤
        return False

    def on_fill(self, callback: Optional[Callable]) -> None:
        self._fill_cb = callback

    # ----------------
    # 推送行情（外部喂）
    # ----------------
    def push_tick(
        self,
        symbol: str,
        price: float,
        timestamp: Any = None,
    ) -> None:
        self._last_prices[symbol] = price
        if timestamp is not None:
            self._last_ts[symbol] = timestamp

    # ----------------
    # 查询
    # ----------------
    def get_positions(self) -> Dict[str, int]:
        return dict(self.positions)

    def get_account(self) -> AccountState:
        market_value = sum(
            self.positions[s]
            * self._last_prices.get(s, 0.0)
            for s in self.positions
        )
        return AccountState(
            cash=self.cash,
            equity=self.cash + market_value,
            margin_used=0.0,
            buying_power=self.cash,
        )

    # ----------------
    # 内部
    # ----------------
    def _apply_fill(self, fill: Fill) -> None:
        prev_qty = self.positions.get(fill.symbol, 0)
        new_qty = prev_qty + fill.quantity
        self.positions[fill.symbol] = new_qty

        if new_qty == 0:
            self.avg_prices.pop(fill.symbol, None)
        elif prev_qty == 0 or (prev_qty * fill.quantity > 0):
            # 开仓 / 加仓
            old_v = abs(prev_qty) * self.avg_prices.get(
                fill.symbol, fill.price
            )
            new_v = abs(fill.quantity) * fill.price
            total = abs(prev_qty) + abs(fill.quantity)
            self.avg_prices[fill.symbol] = (
                (old_v + new_v) / total if total > 0 else fill.price
            )
        elif new_qty * prev_qty < 0:
            # 反手
            self.avg_prices[fill.symbol] = fill.price

        # 扣现金
        self.cash -= fill.quantity * fill.price
        self.cash -= fill.commission
