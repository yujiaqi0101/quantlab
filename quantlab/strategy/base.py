"""
V4.1 Strategy Registry — BaseStrategy

策略的"自描述"基类。
继承自 quantlab.signals.base.SignalStrategy（保持引擎契约 100% 兼容）。

为什么不让所有策略类都改：
  改 BaseStrategy 不破坏现有代码（is-a SignalStrategy）
  现有 4 个内置策略（MACross / RSI / Alpha001 / AlphaMultiFactor）
  不用改一行，立即获得 metadata() 接口

metadata() 类方法的默认行为：
  - 如果子类自己实现 → 用子类的
  - 如果子类没实现 → 从 __init__ 签名自动推导
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, List, Type

from ..signals.base import SignalStrategy
from .metadata import (
    StrategyMetadata,
    StrategyParameter,
    PARAM_TYPES,
)


logger = logging.getLogger("quantlab.strategy.base")


class BaseStrategy(SignalStrategy):
    """
    V4.1 策略基类（继承 V2 SignalStrategy）

    新增能力：
      - metadata()       策略自描述（ID / 参数 / 默认值 / 标签）
      - metadata_class() 子类可指定自己的 StrategyMetadata class
                        （用于复杂元信息场景）
    """

    # 子类可覆盖
    strategy_id: str = ""
    strategy_name: str = ""
    strategy_description: str = ""
    strategy_author: str = ""
    strategy_version: str = "1.0.0"
    strategy_tags: List[str] = []

    # ---------------------------------------------------------
    # 元数据
    # ---------------------------------------------------------
    @classmethod
    def metadata(cls) -> StrategyMetadata:
        """
        返回该策略的 StrategyMetadata

        优先级：
          1) 子类**自己**覆盖了本方法 → 用子类的
          2) 类级属性 + 自动推导
          3) 纯自动推导（从 __init__ 签名）
        """
        # 1) 子类自己实现了 metadata（注意：是 cls 自己的 __dict__）
        own_metadata = cls.__dict__.get("metadata")
        if (
            own_metadata is not None
            and callable(own_metadata)
            and own_metadata is not BaseStrategy.metadata
        ):
            meta = own_metadata()
            if isinstance(meta, StrategyMetadata):
                return meta

        # 2) 拼装 + 自动推导
        cls_name = cls.__name__
        sid = (
            getattr(cls, "strategy_id", "")
            or _class_name_to_id(cls_name)
        )
        params, defaults, space = _auto_params_from_init(
            cls
        )
        class_path = (
            f"{cls.__module__}." f"{cls_name}"
        )

        return StrategyMetadata(
            id=sid,
            name=(
                getattr(cls, "strategy_name", "")
                or _humanize(cls_name)
            ),
            description=(
                getattr(cls, "strategy_description", "")
                or (cls.__doc__ or "").strip().split(
                    "\n", 1
                )[0]
            ),
            author=getattr(cls, "strategy_author", ""),
            version=getattr(
                cls, "strategy_version", "1.0.0"
            ),
            tags=list(
                getattr(cls, "strategy_tags", [])
            ),
            parameters=params,
            default_parameters=defaults,
            param_space=space,
            class_path=class_path,
            source_path=(
                inspect.getsourcefile(cls) or ""
            ),
        )

    # ---------------------------------------------------------
    # 默认配置（子类可选覆盖）
    # ---------------------------------------------------------
    @classmethod
    def default_parameters(cls) -> Dict[str, Any]:
        """
        策略默认参数（注册表 fallback）
        子类可覆盖
        """
        return dict(cls.metadata().default_parameters)

    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        """参数搜索空间（Optimizer 用）子类可覆盖"""
        return dict(cls.metadata().param_space)


# -------------------------------------------------------------
# 工具
# -------------------------------------------------------------
def _class_name_to_id(name: str) -> str:
    """
    PascalCase → snake_case
      MACrossStrategy   → ma_cross
      Alpha001Strategy  → alpha001
      AlphaMultiFactor  → alpha_multi_factor
      RSI               → rsi
      MyCustom          → my_custom

    规则：
      - 全大写短缩写（≤4）→ 整体保留
      - 连续大写串后接小写：
          串长 ≥ 2 → 最后 1 个大写切到下一组（"MACross" → "MA"+"Cross"）
          串长 = 1 → 整体视为单词首字母（"Multi" 拼回 "Multi"）
    """
    if name.endswith("Strategy"):
        name = name[:-8]
    if not name:
        return ""
    if name.isupper() and len(name) <= 4:
        return name.lower()
    tokens: List[str] = []
    cur = ""
    for i, ch in enumerate(name):
        if i == 0:
            cur = ch
            continue
        prev = name[i - 1]
        if ch.isupper() and not prev.isupper():
            # 字母→大写 或 数字→大写：切分
            tokens.append(cur)
            cur = ch
        elif ch.isupper() and prev.isupper():
            # 连续大写
            cur += ch
        elif prev.isupper() and ch.islower():
            # 大写→小写
            if len(cur) >= 2:
                # 连续大写串长度 ≥ 2：最后 1 个大写属于小写词首字母
                # 例 "MACross" → "MA" + "Cross"
                tokens.append(cur[:-1])
                cur = cur[-1] + ch
            else:
                # 连续大写串长度 1：单词首字母大写，例 "Multi"
                cur += ch
        elif prev.isdigit() and ch.isalpha():
            # 数字→字母：切分
            tokens.append(cur)
            cur = ch
        else:
            # 同类型字符：合并
            cur += ch
    if cur:
        tokens.append(cur)
    return "_".join(t.lower() for t in tokens)


def _humanize(name: str) -> str:
    """MACrossStrategy → MACross"""
    if name.endswith("Strategy"):
        return name[:-8]
    return name


def _py_type_to_param_type(ann: Any) -> str:
    """annotation → StrategyParameter.type"""
    if ann is inspect.Parameter.empty:
        return "any"
    if ann is int:
        return "int"
    if ann is float:
        return "float"
    if ann is bool:
        return "bool"
    if ann is str:
        return "str"
    if ann is list:
        return "any"
    if ann is dict:
        return "any"
    name = str(ann).lower()
    if "int" in name:
        return "int"
    if "float" in name:
        return "float"
    if "bool" in name:
        return "bool"
    if "str" in name:
        return "str"
    if "list" in name or "tuple" in name:
        return "any"
    return "any"


def _auto_params_from_init(
    cls: Type,
) -> tuple:
    """
    从 __init__ 签名自动推导 (parameters, defaults, space)

    返回：
      parameters: List[StrategyParameter]
      defaults:   Dict[name, default_value]
      space:      Dict[name, [v1, v2, ...]]（启发式：±50% 三个点）
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return [], {}, {}

    parameters: List[StrategyParameter] = []
    defaults: Dict[str, Any] = {}
    space: Dict[str, List[Any]] = {}

    for name, p in sig.parameters.items():
        if name == "self":
            continue
        if p.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        ann = p.annotation
        ptype = _py_type_to_param_type(ann)
        default = (
            p.default
            if p.default is not inspect.Parameter.empty
            else None
        )
        # 没注解 → 从 default 值类型推断
        if ptype == "any" and default is not None:
            ptype = _py_type_to_param_type(
                type(default)
            )
        parameters.append(
            StrategyParameter(
                name=name,
                type=ptype,
                default=default,
                description="",
            )
        )
        if default is not None:
            defaults[name] = default
        # 启发式 param_space：数值型 default ± 50%，3 个点
        if (
            ptype in ("int", "float")
            and isinstance(default, (int, float))
            and default != 0
        ):
            base = float(default)
            space[name] = [
                type(default)(base * 0.5),
                default,
                type(default)(base * 1.5),
            ]

    return parameters, defaults, space


# -------------------------------------------------------------
# 公共 API
# -------------------------------------------------------------
def is_base_strategy(cls: Type) -> bool:
    """判断一个类是否是 BaseStrategy（含子类）"""
    try:
        return isinstance(cls, type) and issubclass(
            cls, BaseStrategy
        )
    except TypeError:
        return False


def is_strategy_class(cls: Type) -> bool:
    """
    兼容判断：是否是"可注册策略类"

    - BaseStrategy 子类（新） → True
    - SignalStrategy 子类（旧，未升级） → True
    - 抽象基类（自身有未实现方法） → False
    - 其它                              → False
    """
    try:
        if not (isinstance(cls, type) and (
            issubclass(cls, BaseStrategy)
            or issubclass(cls, SignalStrategy)
        )):
            return False
    except TypeError:
        return False
    # 排除抽象基类（自身有 __abstractmethods__）
    if getattr(cls, "__abstractmethods__", None):
        return False
    # 排除基类自身
    if cls in (BaseStrategy, SignalStrategy):
        return False
    return True


def get_metadata_for_class(
    cls: Type,
) -> StrategyMetadata:
    """
    从一个策略类取 StrategyMetadata
    - BaseStrategy 子类 → 调 cls.metadata()
    - 旧 SignalStrategy 子类 → 临时构造一个 BaseStrategy
                                走 _auto_params_from_init
    """
    if is_base_strategy(cls):
        return cls.metadata()  # type: ignore[arg-type]
    # 旧策略：调 BaseStrategy.metadata() 模板
    return BaseStrategy.metadata.__func__(cls)  # type: ignore[attr-defined]
