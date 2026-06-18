"""
Paper Exchange — 模拟交易所

T1 第六模块：模拟成交 / 手续费 / 滑点 / 延迟

第一版：
  fee = 0.001 (0.1%)
  slippage = 0.0005 (0.05%)

  接收 OrderRequest → 生成 Fill → 推送回调

用法：
    from quantlab.execution.paper_exchange import PaperExchange

    exchange = PaperExchange()
    exchange.update_price("BTCUSDT", 50000)
    fill = exchange.match_order(order_req)
"""

from .exchange import PaperExchange, ExchangeConfig
from .models import ExchangeFill, ExchangeQuote

__all__ = [
    "PaperExchange",
    "ExchangeConfig",
    "ExchangeFill",
    "ExchangeQuote",
]
