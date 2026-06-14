#看事件引擎和vectorbt的对比
import pandas as pd

from quantlab.strategy import (
    MACrossStrategy
)

from quantlab.execution import (
    PercentageCommission,
    PercentageSlippage,
    TargetPositionExecution
)

from quantlab.engine import BarEngine

from quantlab.adapters.vectorbt_adapter import (
    VectorBTAdapter
)


# --------------------------------

# 数据

# --------------------------------

df = pd.read_csv(
    "data/sample.csv",
    parse_dates=True,
    index_col=0
)

# --------------------------------

# 同一套策略

# --------------------------------

strategy = MACrossStrategy(
    fast=20,
    slow=60
)

# --------------------------------

# EventEngine（事件驱动）

# --------------------------------

event_engine = BarEngine(

    strategy=strategy,

    execution_model=(
        TargetPositionExecution()
    ),

    commission_model=(
        PercentageCommission(
            rate=0.0003
        )
    ),

    slippage_model=(
        PercentageSlippage(
            rate=0.0002
        )
    ),

    initial_cash=100000
)

event_result = event_engine.run(df)

event_equity = (
    event_result["portfolio"]
    .equity_curve[-1]
)

# --------------------------------

# VectorBTAdapter（向量化）

# --------------------------------

vbt_adapter = VectorBTAdapter()

vbt_pf = vbt_adapter.run(
    strategy=strategy,
    data=df,
    fees=0.0003,
    init_cash=100000
)

vbt_equity = float(
    vbt_pf.value().iloc[-1]
)

# --------------------------------

# 对比输出

# --------------------------------

diff = (
    event_equity
    -
    vbt_equity
)

pct_diff = (

    abs(diff)
    /
    vbt_equity
    * 100
) if vbt_equity else 0

print()
print("=" * 50)

print(
    "EventEngine Final Equity:",
    round(event_equity, 2)
)

print(
    "VectorBT    Final Equity:",
    round(vbt_equity, 2)
)

print(
    "Diff:",
    round(diff, 2)
)

print(
    "Diff %:",
    round(pct_diff, 2),
    "%"
)

# 简单评级
if pct_diff < 5:
    verdict = "PASS (< 5%)"
elif pct_diff < 20:
    verdict = "WARN (5%~20%)"
else:
    verdict = "FAIL (> 20%)"

print(
    "Verdict:",
    verdict
)

print("=" * 50)
