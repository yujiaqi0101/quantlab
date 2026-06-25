"""
信号策略层 (signals)
====================

SignalStrategy 基类: 策略只产出 DataFrame(date × symbol) 的信号，
不关心仓位计算、订单生成、撮合等下游逻辑。

具体策略封装因子为可回测的信号:
    - MACrossStrategy / RSIStrategy (技术指标类)
    - Alpha014Strategy 等 (Alpha 因子类)

约束 (遵循 STRATEGY_DEV_GUIDE):
    - 必须继承 SignalStrategy
    - __init__ 参数必须可被 int/str 序列化 (支持子进程并行)
    - 新代码统一走 quantlab.signals.base 子模块
"""
