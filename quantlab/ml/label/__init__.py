"""
Label Lab — 标签实验室

ML Lab 第三部分：标签工程

  Label
    - label.generate(df) → pd.Series

  LabelSet (L3 升级)
    - 标签集合，可命名、版本化、复用
    - 例如：return_10d = FutureReturn10, direction_5d = UpDown5

  内置标签：
    FutureReturn5 / 10 / 20
    UpDownLabel（三分类：Up / Neutral / Down）
"""

from .base import Label, LabelRegistry, get_label_registry
from .set import LabelSet, LabelSetRegistry, get_label_set_registry
from .builtin import register_all_builtin

__all__ = [
    "Label",
    "LabelRegistry",
    "get_label_registry",
    "LabelSet",
    "LabelSetRegistry",
    "get_label_set_registry",
    "register_all_builtin",
]
