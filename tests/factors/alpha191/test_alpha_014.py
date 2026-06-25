"""
Alpha191 #14 因子单元测试
========================

验证:
    - 基本计算: CLOSE - DELAY(CLOSE, 5)
    - 数据不足返回 NaN
    - 窗口期可配置
    - 方向常量
    - 完整备注字段检查 (10 个必填字段)
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191.alpha_014 import (
    alpha_014,
    DIRECTION,
    DEFAULT_PERIOD,
)
from quantlab.factors.context import FactorContext
from quantlab.signals.alpha_014 import Alpha014Strategy


def _make_ctx(closes):
    """closes: {symbol: [close序列]}"""
    n = len(next(iter(closes.values())))
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {}
    for sym, c in closes.items():
        data[sym] = pd.DataFrame(
            {
                "open": c, "high": c, "low": c, "close": c,
                "volume": [1000.0] * n,
            },
            index=dates,
        )
    return FactorContext.from_dict(data)


def test_alpha_014_basic():
    # close = [10, 11, 12, 13, 14, 15], period=5
    # 末值 = 15 - 10 = 5
    ctx = _make_ctx({"A": [10, 11, 12, 13, 14, 15]})
    r = alpha_014(ctx, period=5)
    assert r.iloc[-1, 0] == 5
    # 前 5 期为 NaN
    assert r.iloc[:5, 0].isna().all()


def test_alpha_014_insufficient_data():
    ctx = _make_ctx({"A": [10, 11]})  # 不足 5 期
    r = alpha_014(ctx, period=5)
    assert r.isna().all().all()


def test_alpha_014_custom_period():
    ctx = _make_ctx({"A": [10, 11, 12, 13]})
    r = alpha_014(ctx, period=2)
    # 末值 = 13 - 11 = 2
    assert r.iloc[-1, 0] == 2


def test_alpha_014_direction():
    assert DIRECTION == 1  # 正向


def test_default_period():
    assert DEFAULT_PERIOD == 5


def test_strategy_signal_matches_factor():
    closes = {"A": [10, 11, 12, 13, 14, 15], "B": [20, 19, 18, 17, 16, 15]}
    ctx = _make_ctx(closes)
    s = Alpha014Strategy(period=5)
    df = s.signal(ctx)
    # A 上涨，B 下跌
    assert df.iloc[-1, 0] == 5   # A: 15-10
    assert df.iloc[-1, 1] == -5  # B: 15-20


def test_strategy_params_serializable():
    s = Alpha014Strategy(period=10)
    assert s.params() == {"period": 10}


# ---------------- 完整备注字段检查 ----------------

def _read_module_docstring():
    import sys
    mod = sys.modules.get("quantlab.factors.alpha191.alpha_014")
    return mod.__doc__ if (mod and mod.__doc__) else ""


def test_docstring_has_all_10_required_fields():
    """每个因子必须有完整备注 (10 个必填字段)。"""
    doc = _read_module_docstring()
    required_fields = [
        "公式",
        "公式解释",
        "分类",
        "信号方向",
        "数据来源与频率",
        "算子依赖",
        "背后逻辑",
        "适用场景",
        "变种与优化",
        "注意事项",
    ]
    missing = [f for f in required_fields if f not in doc]
    assert not missing, f"Alpha014 完整备注缺少字段: {missing}"
