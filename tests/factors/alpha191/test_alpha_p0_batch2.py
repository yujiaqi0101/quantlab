"""
Alpha191 P0 因子单元测试 (批次2)
================================

覆盖: #95, #118, #127
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.context import FactorContext
from quantlab.factors.alpha191.alpha_095 import alpha_095, DIRECTION as D95
from quantlab.factors.alpha191.alpha_118 import alpha_118, DIRECTION as D118
from quantlab.factors.alpha191.alpha_127 import alpha_127, DIRECTION as D127


def _make_ctx(n=25, with_amount=False):
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B"]:
        df = pd.DataFrame(
            {
                "open": rng.uniform(90, 110, n),
                "high": rng.uniform(100, 120, n),
                "low": rng.uniform(80, 100, n),
                "close": rng.uniform(95, 115, n),
                "volume": rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        if with_amount:
            df["amount"] = df["close"] * df["volume"]
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #95 ----------------

def test_alpha_095_basic():
    ctx = _make_ctx(n=25, with_amount=True)
    r = alpha_095(ctx, period=20)
    # 前 19 期 NaN
    assert r.iloc[:19].isna().all().all()
    # 第 19 期开始有值
    assert not r.iloc[19].isna().all()


def test_alpha_095_direction():
    assert D95 == 1


# ---------------- Alpha #118 ----------------

def test_alpha_118_basic():
    # 构造上影=下影 → 比值 100
    n = 22
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [105.0]*n, "low": [95.0]*n,
                "close": [100.0]*n, "volume": [1000.0]*n,
            }, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_118(ctx, period=20)
    # 上影=5, 下影=5 → 5*20 / (5*20) * 100 = 100
    assert r.iloc[19, 0] == pytest.approx(100.0)


def test_alpha_118_zero_lower_returns_nan():
    # 下影=0 → 分母=0 → NaN
    n = 22
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [105.0]*n, "low": [100.0]*n,
                "close": [100.0]*n, "volume": [1000.0]*n,
            }, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_118(ctx, period=20)
    assert np.isnan(r.iloc[19, 0])


def test_alpha_118_direction():
    assert D118 == 1


# ---------------- Alpha #127 ----------------

def test_alpha_127_basic():
    # 恒定 close → 回撤=0 → RMS=0
    n = 25
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [100.0]*n, "low": [100.0]*n,
                "close": [100.0]*n, "volume": [1000.0]*n,
            }, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_127(ctx, period=12)
    # 预热期 = ts_max(12) + ts_mean(12) - 1 = 22 期
    # 前 22 期 NaN
    assert r.iloc[:22].isna().all().all()
    # 恒定价格 → 回撤 0 → RMS 0
    assert r.iloc[22, 0] == pytest.approx(0.0, abs=1e-9)


def test_alpha_127_positive_drawdown():
    # close 递减 → 每期都低于最高 → 回撤 > 0 → RMS > 0
    n = 30
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    closes = [120.0 - i for i in range(n)]
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes, "low": closes,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_127(ctx, period=12)
    # 预热 22 期后: 回撤 > 0 → RMS > 0
    assert r.iloc[22, 0] > 0


def test_alpha_127_direction():
    assert D127 == 1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


def _module_doc(modname):
    import sys
    mod = sys.modules.get(modname)
    return mod.__doc__ if (mod and mod.__doc__) else ""


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_095",
        "quantlab.factors.alpha191.alpha_118",
        "quantlab.factors.alpha191.alpha_127",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
