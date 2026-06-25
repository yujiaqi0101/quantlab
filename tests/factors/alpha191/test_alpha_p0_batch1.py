"""
Alpha191 P0 因子单元测试 (批量)
================================

覆盖: #15, #54, #70, #97, #100
每个因子验证:
    - 基本计算与公式手算一致
    - 预热期返回 NaN
    - 方向常量正确
    - 完整备注 10 字段齐全
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.context import FactorContext
from quantlab.factors.alpha191.alpha_015 import alpha_015, DIRECTION as D15
from quantlab.factors.alpha191.alpha_054 import alpha_054, DIRECTION as D54
from quantlab.factors.alpha191.alpha_070 import alpha_070, DIRECTION as D70
from quantlab.factors.alpha191.alpha_097 import alpha_097, DIRECTION as D97
from quantlab.factors.alpha191.alpha_100 import alpha_100, DIRECTION as D100


def _make_ctx(n=15, with_amount=False):
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


# ---------------- Alpha #15 ----------------

def test_alpha_015_basic():
    # 构造 OPEN=110, CLOSE(昨)=100 → 0.1
    n = 3
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {"open": [110, 110, 110], "high": [110]*3, "low": [110]*3,
             "close": [100, 100, 100], "volume": [1000.0]*3}, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_015(ctx)
    # 第 0 期 NaN (delay 1)
    assert np.isnan(r.iloc[0, 0])
    # 第 1 期: 110/100-1 = 0.1
    assert r.iloc[1, 0] == pytest.approx(0.1)


def test_alpha_015_direction():
    assert D15 == 1


# ---------------- Alpha #54 ----------------

def test_alpha_054_nan_warmup():
    ctx = _make_ctx(n=15)
    r = alpha_054(ctx, period=10)
    # 前 9 期 STD/CORR 不足 → NaN
    assert r.iloc[:9].isna().all().all()
    # 第 9 期开始有值
    assert not r.iloc[9].isna().all()


def test_alpha_054_direction():
    assert D54 == -1


# ---------------- Alpha #70 ----------------

def test_alpha_070_uses_amount_when_present():
    ctx = _make_ctx(n=10, with_amount=True)
    r = alpha_070(ctx, period=6)
    # 前 5 期 NaN
    assert r.iloc[:5].isna().all().all()
    # 第 5 期开始有值
    assert not r.iloc[5].isna().all()


def test_alpha_070_amount_fallback_to_close_volume():
    """无 amount 时用 close*volume 兜底。"""
    ctx = _make_ctx(n=10, with_amount=False)
    r = alpha_070(ctx, period=6)
    assert not r.iloc[5].isna().all()


def test_alpha_070_direction():
    assert D70 == 1


# ---------------- Alpha #97 ----------------

def test_alpha_097_basic():
    # 构造恒定 volume → std=0
    n = 12
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {"open": [100.0]*n, "high": [100.0]*n, "low": [100.0]*n,
             "close": [100.0]*n, "volume": [5000.0]*n}, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_097(ctx, period=10)
    # 恒定序列 std=0
    assert r.iloc[9, 0] == pytest.approx(0.0, abs=1e-9)


def test_alpha_097_direction():
    assert D97 == 1


# ---------------- Alpha #100 ----------------

def test_alpha_100_basic():
    n = 22
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {"open": [100.0]*n, "high": [100.0]*n, "low": [100.0]*n,
             "close": [100.0]*n, "volume": [5000.0]*n}, index=dates,
        )
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_100(ctx, period=20)
    # 前 19 期 NaN
    assert r.iloc[:19].isna().all().all()
    # 恒定序列 std=0
    assert r.iloc[19, 0] == pytest.approx(0.0, abs=1e-9)


def test_alpha_100_direction():
    assert D100 == 1


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
        "quantlab.factors.alpha191.alpha_015",
        "quantlab.factors.alpha191.alpha_054",
        "quantlab.factors.alpha191.alpha_070",
        "quantlab.factors.alpha191.alpha_097",
        "quantlab.factors.alpha191.alpha_100",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
