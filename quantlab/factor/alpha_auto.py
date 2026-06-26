"""
自动注册 Alpha191 / Alpha101 所有因子
====================================
通过 dir() 反射模块内的 alpha_XXX 因子函数与对应的 DIRECTION 常量。
"""
from __future__ import annotations

import re
from typing import Optional

from ..factors import alpha191 as _a191
from ..factors import alpha101 as _a101
from .registry import get_registry


# ---------- Alpha191 大类粗分类映射（按编号区间） ----------
# 参考国泰君安报告8大类：量价/均值回复/动量/波动率/相关性/成交量/价格/基准
_ALPHA191_CATEGORY = {
    "volume_price":    "cross_sectional",
    "mean_reversion":  "momentum",
    "momentum":        "momentum",
    "volatility":      "volatility",
    "correlation":     "cross_sectional",
    "volume":          "volume",
    "price":           "trend",
    "benchmark":       "composite",
}


def _extract_doc_category(doc: Optional[str]) -> str:
    """从因子文档字符串中提取'分类:'后面的类别标签。"""
    if not doc:
        return "cross_sectional"
    m = re.search(r"分类:\s*([^\n]+)", doc)
    if not m:
        return "cross_sectional"
    cat = m.group(1).strip().lower()
    for k, v in _ALPHA191_CATEGORY.items():
        if k in cat:
            return v
    return "cross_sectional"


def _extract_doc_first_line(doc: Optional[str], default: str) -> str:
    """从 docstring 第一行提取简要描述。"""
    if not doc:
        return default
    lines = [l.strip() for l in doc.strip().splitlines() if l.strip()]
    for line in lines:
        if line.startswith("=") or line.startswith("#") or line.startswith("-"):
            continue
        # 跳过 "Alpha191 #1 — xxx" 或 "Alpha101 #1: xxx" 格式，取后半段
        if "—" in line:
            return line.split("—", 1)[1].strip()
        if "：" in line:
            return line.split("：", 1)[1].strip()
        if ":" in line and not line.startswith("公式"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Alpha"):
            continue
        return line
    return default


def _register_alpha_module(module, source: str, default_category: str, name_prefix: str = "", keep_suffix: bool = True) -> int:
    """反射模块并注册全部 alpha_XXX 因子，返回注册数量。

    Args:
        module:         因子模块（alpha191 / alpha101）
        source:         来源标识
        default_category: 默认分类
        name_prefix:    注册名前缀（alpha101 加前缀避免冲突）
        keep_suffix:    True  → 注册名 = prefix + fname (如 a101_alpha_001)
                        False → 注册名 = prefix + 三位编号 (如 a101_001)
    """
    reg = get_registry()
    count = 0
    factor_names = [n for n in dir(module) if re.match(r"^alpha_\d{3}$", n)]
    for fname in factor_names:
        fn = getattr(module, fname)
        if not callable(fn):
            continue
        dir_const = fname.upper() + "_DIRECTION"
        direction = getattr(module, dir_const, 0) or 0
        doc = getattr(fn, "__doc__", None)
        if source == "alpha191":
            cat = _extract_doc_category(doc)
        else:
            cat = default_category
        desc = _extract_doc_first_line(doc, fname)
        if keep_suffix:
            reg_name = name_prefix + fname
        else:
            num = fname.split("_")[1]
            reg_name = f"{name_prefix}{num}"
        if reg_name in reg:
            continue
        try:
            reg.register(
                name=reg_name,
                category=cat,
                description=desc,
                fn=fn,
                direction=int(direction),
                source=source,
                params={},
            )
            count += 1
        except Exception:
            continue
    return count


def _register() -> None:
    n191 = _register_alpha_module(_a191, source="alpha191", default_category="cross_sectional", name_prefix="", keep_suffix=True)
    n101 = _register_alpha_module(_a101, source="alpha101", default_category="composite", name_prefix="a101_", keep_suffix=False)
    globals()["_registered_count"] = (n191, n101)


_register()
