"""
V4.0 Application Layer — 全局策略注册表

为什么单独放一个：
  - Application 层的多个 Service（Backtest / Optimizer / Runtime）
    都要按 strategy_id 拿 strategy class
  - 这里维护**对外**注册表（service 用）
  - runtime.supervisor.StrategyRegistry 是 V3.4 **运行时**注册表
    给 PortfolioSupervisor 用，定位不同

注册表返回 domain.StrategyDefinition：
  - 包含 class_path、parameters_schema、default_parameters
  - 前端可直接基于此生成表单

用法：
    from quantlab.strategy_registry import (
        get_strategy_registry,
    )
    reg = get_strategy_registry()
    defn = reg.get("ma_cross")
    defn.parameters_schema   # → 表单字段
"""

from __future__ import annotations

import inspect
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from .domain.strategy import (
    StrategyDefinition,
    ParamSchema,
)
from .signals.base import SignalStrategy


logger = logging.getLogger("quantlab.strategy_registry")


@dataclass
class _Entry:
    """注册表内部条目：class + 对外定义"""
    cls: Type
    definition: StrategyDefinition


class StrategyRegistry:
    """
    进程内全局策略注册表（线程安全）

    - register(id, cls, ...)         注册一个策略
    - create(id, params=...)         构造一个实例
    - get(id)                        取 StrategyDefinition
    - get_class(id)                  取 class（service 内部用）
    - list()                         列出全部 StrategyDefinition
    - list_ids()                     仅 ID
    - has(id)
    - unregister(id)
    """

    def __init__(self) -> None:
        self._items: Dict[str, _Entry] = {}
        self._lock = threading.RLock()

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------
    def register(
        self,
        strategy_id: str,
        cls: Type,
        name: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        default_params: Optional[Dict[str, Any]] = None,
        param_space: Optional[Dict[str, Any]] = None,
        parameters_schema: Optional[List[ParamSchema]] = None,
        override: bool = False,
    ) -> None:
        """
        注册一个策略。

        - parameters_schema 缺省时，按 cls.__init__ 签名自动推导
        - class_path 自动从 cls 生成
        """
        if not inspect.isclass(cls) or not issubclass(
            cls, SignalStrategy
        ):
            raise TypeError(
                f"{cls!r} must be a subclass of SignalStrategy"
            )
        with self._lock:
            if (
                strategy_id in self._items
                and not override
            ):
                raise ValueError(
                    f"strategy_id {strategy_id!r} already registered"
                )

            schema = parameters_schema or _auto_schema(cls)
            class_path = (
                f"{cls.__module__}." f"{cls.__name__}"
            )
            defn = StrategyDefinition(
                id=strategy_id,
                name=name or cls.__name__,
                class_path=class_path,
                description=description,
                parameters_schema=list(schema),
                default_parameters=dict(
                    default_params or {}
                ),
                param_space=dict(param_space or {}),
                tags=list(tags or []),
            )
            self._items[strategy_id] = _Entry(
                cls=cls, definition=defn
            )
        logger.info(
            "strategy registered: %s → %s",
            strategy_id, class_path,
        )

    def unregister(self, strategy_id: str) -> bool:
        with self._lock:
            return self._items.pop(strategy_id, None) is not None

    def has(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._items

    def get(
        self, strategy_id: str
    ) -> Optional[StrategyDefinition]:
        with self._lock:
            e = self._items.get(strategy_id)
            return e.definition if e else None

    def get_class(self, strategy_id: str) -> Type:
        with self._lock:
            e = self._items.get(strategy_id)
        if e is None:
            raise KeyError(
                f"strategy_id {strategy_id!r} not registered"
            )
        return e.cls

    def list(self) -> List[StrategyDefinition]:
        with self._lock:
            return [e.definition for e in self._items.values()]

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._items.keys())

    # ---------------------------------------------------------
    # 构造
    # ---------------------------------------------------------
    def create(
        self,
        strategy_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SignalStrategy:
        """
        构造一个 strategy 实例

        - params 为空 → 用注册时的 default_parameters
        - 多余字段会被过滤（前端可能传未知字段）
        """
        e = self.get(strategy_id) and self._items.get(
            strategy_id
        )
        if e is None:
            raise KeyError(
                f"strategy_id {strategy_id!r} not registered. "
                f"known: {self.list_ids()}"
            )

        merged = dict(e.definition.default_parameters)
        if params:
            merged.update(params)

        filtered = _filter_accepted(e.cls, merged)
        return e.cls(**filtered)


# -------------------------------------------------------------
# 工具
# -------------------------------------------------------------
def _filter_accepted(
    cls: Type, params: Dict[str, Any]
) -> Dict[str, Any]:
    """只保留 cls.__init__ 接受的参数名"""
    try:
        sig = inspect.signature(cls.__init__)
        accepted = set(sig.parameters.keys())
    except (TypeError, ValueError):
        return params
    return {k: v for k, v in params.items() if k in accepted}


def _auto_schema(cls: Type) -> List[ParamSchema]:
    """从 __init__ 签名自动推导 ParamSchema 列表"""
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return []

    out: List[ParamSchema] = []
    for name, p in sig.parameters.items():
        if name == "self":
            continue
        ann = p.annotation
        type_name = _py_type_to_name(ann)
        out.append(
            ParamSchema(
                name=name,
                type=type_name,
                default=(
                    p.default
                    if p.default is not inspect.Parameter.empty
                    else None
                ),
                description="",
            )
        )
    return out


def _py_type_to_name(ann: Any) -> str:
    """annotation → ParamSchema.type 字符串"""
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
    name = str(ann).lower()
    if "int" in name:
        return "int"
    if "float" in name:
        return "float"
    if "bool" in name:
        return "bool"
    if "str" in name:
        return "str"
    return "any"


# -------------------------------------------------------------
# 全局单例 + 内置策略注册
# -------------------------------------------------------------
_default: Optional[StrategyRegistry] = None
_default_lock = threading.Lock()
_builtin_registered: bool = False
_builtin_lock = threading.Lock()


def get_strategy_registry() -> StrategyRegistry:
    """获取（或创建）全局注册表，并保证内置策略已注册"""
    global _default
    with _default_lock:
        if _default is None:
            _default = StrategyRegistry()
    _ensure_builtin(_default)
    return _default


def set_strategy_registry(reg: StrategyRegistry) -> None:
    """替换全局注册表（用于测试）"""
    global _default, _builtin_registered
    with _default_lock:
        _default = reg
    with _builtin_lock:
        _builtin_registered = False
    _ensure_builtin(reg)


def _ensure_builtin(reg: StrategyRegistry) -> None:
    """注册 quantlab 自带的策略（幂等）"""
    global _builtin_registered
    with _builtin_lock:
        if _builtin_registered:
            return

    # 延迟 import，避免循环
    from .signals import (
        MACrossStrategy,
        RSIStrategy,
        Alpha001Strategy,
        AlphaMultiFactorStrategy,
        RSI_PARAM_SPACE,
        ALPHA001_PARAM_SPACE,
        ALPHA_MULTIFACTOR_PARAM_SPACE,
    )
    from .domain.strategy import (
        make_ma_cross_definition,
        make_rsi_definition,
    )

    # 1) ma_cross（用 domain factory 注入）
    if not reg.has("ma_cross"):
        try:
            ma_def = make_ma_cross_definition()
            reg.register(
                strategy_id=ma_def.id,
                cls=MACrossStrategy,
                name=ma_def.name,
                description=ma_def.description,
                tags=ma_def.tags,
                default_params=ma_def.default_parameters,
                param_space=ma_def.param_space,
                parameters_schema=ma_def.parameters_schema,
            )
        except Exception as exc:
            logger.warning(
                "register ma_cross failed: %s", exc
            )

    # 2) rsi
    if not reg.has("rsi"):
        try:
            rsi_def = make_rsi_definition()
            reg.register(
                strategy_id=rsi_def.id,
                cls=RSIStrategy,
                name=rsi_def.name,
                description=rsi_def.description,
                tags=rsi_def.tags,
                default_params=rsi_def.default_parameters,
                param_space=(
                    dict(RSI_PARAM_SPACE)
                    if RSI_PARAM_SPACE
                    else rsi_def.param_space
                ),
                parameters_schema=rsi_def.parameters_schema,
            )
        except Exception as exc:
            logger.warning(
                "register rsi failed: %s", exc
            )

    # 3) alpha001
    if not reg.has("alpha001"):
        try:
            reg.register(
                strategy_id="alpha001",
                cls=Alpha001Strategy,
                name="Alpha 001",
                description="WorldQuant Alpha 101 - 001",
                tags=["alpha101", "selection"],
                param_space=(
                    dict(ALPHA001_PARAM_SPACE)
                    if ALPHA001_PARAM_SPACE else None
                ),
            )
        except Exception as exc:
            logger.warning(
                "register alpha001 failed: %s", exc
            )

    # 4) alpha_multifactor
    if not reg.has("alpha_multifactor"):
        try:
            reg.register(
                strategy_id="alpha_multifactor",
                cls=AlphaMultiFactorStrategy,
                name="Alpha Multi-Factor",
                description="多因子合成",
                tags=["alpha101", "selection"],
                param_space=(
                    dict(ALPHA_MULTIFACTOR_PARAM_SPACE)
                    if ALPHA_MULTIFACTOR_PARAM_SPACE else None
                ),
            )
        except Exception as exc:
            logger.warning(
                "register alpha_multifactor failed: %s", exc
            )

    with _builtin_lock:
        _builtin_registered = True
