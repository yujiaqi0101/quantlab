"""
Alpha101 多因子 SOP 跑法（薄壳）
============================

调用通用 [run_pipeline.py] 对 AlphaMultiFactorStrategy 跑 6 stage。

公式:
    score = w9*rank(alpha9) + w40*rank(alpha40) + w49*rank(alpha49)
    alpha#9  = ts_min(close, 5) - correlation(sum(close, 5), sum(close, 20), 5)
    alpha#40 = -ts_rank(high, 10) * sign(delta(close, 1))
    alpha#49 = -ts_rank(delay(close, 10), 10) * sign(delta(close, 1))
              + sign(delta(volume / adv20, 5))

跑法:
    python examples/run_alpha_multifactor.py
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
    AlphaMultiFactorStrategy,
    ALPHA_MULTIFACTOR_PARAM_SPACE,
)

if __name__ == "__main__":
    run_sop(
        strategy_cls=AlphaMultiFactorStrategy,
        param_space=ALPHA_MULTIFACTOR_PARAM_SPACE,
        base_params={
            "w9":  1.0 / 3,
            "w40": 1.0 / 3,
            "w49": 1.0 / 3,
        },
        tag="alpha101_multi_a9_a40_a49",
        note=(
            "Alpha101 多因子: rank(a9)+rank(a40)+rank(a49) 等权融合，"
            "TopN=2，commission=3bps，slippage=2bps"
        ),
    )
