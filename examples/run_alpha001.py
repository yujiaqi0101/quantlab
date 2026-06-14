"""
Alpha101 #001 SOP 跑法（薄壳）
==========================

调用通用 [run_pipeline.py] 对 Alpha001Strategy 跑 6 stage。
所有 SOP 行为（基线 / 双引擎 / 网格 / WF / 入库 / 反例）
都在 run_pipeline.run_sop() 里实现。

公式:
    alpha = rank(MA(close, period)) - rank(close)

跑法:
    python examples/run_alpha001.py
"""
import os
import sys

# 让脚本无论从项目根还是 examples/ 子目录直接跑都能找到 quantlab 包
# 也让 examples/ 内的 run_pipeline 能被相对导入
_PKG_PARENT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_pipeline import run_sop
from quantlab.signals import (
    Alpha001Strategy,
    ALPHA001_PARAM_SPACE,
)

if __name__ == "__main__":
    run_sop(
        strategy_cls=Alpha001Strategy,
        param_space=ALPHA001_PARAM_SPACE,
        base_params={
            "period": 10,
        },
        tag="alpha101_cross_sectional",
        note=(
            "Alpha101 #001: rank(MA(close,10)) - rank(close)，"
            "TopN=2，commission=3bps，slippage=2bps"
        ),
    )
