"""
Order：下单

V3.1 字段扩展：
  symbol      必填
  quantity    必填（>0 买入，<0 卖出）
  id          本地单号（L000001），可选，引擎 / OrderManager 填
  side        "BUY" / "SELL"，由 quantity 自动派生，亦可显式覆盖
  price       下单价格（MARKET 时可空）
  order_type  "MARKET" / "LIMIT"，默认 MARKET
  status      状态机 NEW / PARTIAL / FILLED / CANCELLED / REJECTED
  created_at  本地创建时间
  filled_qty  已成交数量

V1/V2 的旧调用 Order(symbol=..., quantity=...) 仍然有效：
  所有新字段都有默认值，slots=True 不影响。

撮合器生成 Order 列表
由 Execution / Broker 统一执行 → 产生 Fill
"""
from dataclasses import dataclass, field
from typing import Optional


# 状态枚举用字符串常量（兼容 dataclass(slots=True) 不支持 Enum 默认值的简单做法）
ORDER_STATUS_NEW = "NEW"
ORDER_STATUS_PARTIAL = "PARTIAL"
ORDER_STATUS_FILLED = "FILLED"
ORDER_STATUS_CANCELLED = "CANCELLED"
ORDER_STATUS_REJECTED = "REJECTED"

ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"

SIDE_BUY = "BUY"
SIDE_SELL = "SELL"


def _infer_side(quantity: int) -> str:
    return SIDE_BUY if quantity >= 0 else SIDE_SELL


@dataclass(slots=True)
class Order:

    symbol: str
    quantity: int

    # V3.1 新增字段（全部有默认值，向后兼容）
    id: str = ""
    side: str = ""
    price: Optional[float] = None
    order_type: str = ORDER_TYPE_MARKET
    status: str = ORDER_STATUS_NEW
    created_at: Optional[object] = None
    filled_qty: int = 0
    reject_reason: str = ""

    # V3.3：客户端幂等 ID（防网络重试重复下单）
    client_order_id: str = ""

    def __post_init__(self):
        # 自动派生 side
        if not self.side:
            self.side = _infer_side(self.quantity)
        # V3.3：自动生成 client_order_id
        if not self.client_order_id:
            import uuid
            self.client_order_id = uuid.uuid4().hex[:12]
