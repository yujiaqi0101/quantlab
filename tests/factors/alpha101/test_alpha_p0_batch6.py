"""
Alpha101 P0 长窗口因子单元测试 (批次6)
========================================

覆盖: #19, #24, #32
长窗口因子，需 250+ 日历史数据。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101 import (
    alpha_019, alpha_024, alpha_032,
    ALPHA019_DIRECTION, ALPHA024_DIRECTION, ALPHA032_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=300):
    """长数据 (5 标的 × 300 日)，覆盖 250 日长窗口。"""
    dates = pd.date_range("2025-01-02", periods=n, freq="B")
    rng = np.random.default_rng(1)
    data = {}
    for sym in ["A", "B", "C", "D", "E"]:
        close = 100 + rng.normal(0, 1, n).cumsum()
        close = close.astype(float)
        df = pd.DataFrame(
            {
                "open": close + rng.normal(0, 0.5, n),
                "high": close + np.abs(rng.normal(0, 1, n)),
                "low": close - np.abs(rng.normal(0, 1, n)),
                "close": close,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "vwap": close + rng.normal(0, 0.3, n),
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


@pytest.mark.parametrize(
    "name,func,direction,warmup",
    [
        ("alpha_019", alpha_019, ALPHA019_DIRECTION, 251),
        ("alpha_024", alpha_024, ALPHA024_DIRECTION, 200),
        ("alpha_032", alpha_032, ALPHA032_DIRECTION, 235),
    ],
)
def test_long_factor_basic(name, func, direction, warmup):
    ctx = _make_ctx(n=300)
    r = func(ctx)
    assert r.shape == ctx.close.shape, f"{name} 形状不一致"
    # 首期 NaN
    assert r.iloc[0].isna().all(), f"{name} 首期应为 NaN"
    # 预热期前 NaN (warmup-2 索引，即前一期)
    assert r.iloc[warmup - 2].isna().all(), f"{name} 第 {warmup-1} 期应仍为 NaN"
    # 预热期后有值 (warmup 索引)
    assert not r.iloc[warmup].isna().all(), f"{name} 第 {warmup+1} 期应有值"
    # 末尾期有值
    assert not r.iloc[-1].isna().all(), f"{name} 末尾期应有值"


def test_direction_constants():
    assert ALPHA019_DIRECTION == 1
    assert ALPHA024_DIRECTION == -1
    assert ALPHA032_DIRECTION == 1


@pytest.mark.parametrize(
    "modpath",
    [
        "quantlab.factors.alpha101.alpha_019",
        "quantlab.factors.alpha101.alpha_024",
        "quantlab.factors.alpha101.alpha_032",
    ],
)
def test_docstring_has_all_10_required_fields(modpath):
    import importlib

    mod = importlib.import_module(modpath)
    doc = mod.__doc__ or ""
    required = [
        "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
        "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
    ]
    for f in required:
        assert f in doc, f"{modpath} 缺少字段: {f}"
