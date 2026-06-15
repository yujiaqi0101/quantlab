"""
V4.1 Strategy Registry — 策略注册中心

核心职责：
  - 注册策略（自动生成 metadata + source snapshot）
  - 查询 metadata（前端用）
  - 构造实例（后端用）
  - 版本管理（历史可溯源）

为什么新注册表：
  - 旧 quantlab.strategy_registry（V3.x）服务 BacktestService
  - 新 V4.1 专服务前端（前端需要 metadata / schema_dict）
  - 两个共存，V4.1 注册表更完整
  - 后端 BacktestService 未来可迁到 V4.1

并发安全：线程安全，进程内单例
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from ..signals.base import SignalStrategy
from .base import (
    BaseStrategy,
    get_metadata_for_class,
    is_strategy_class,
)
from .metadata import (
    StrategyMetadata,
    StrategyParameter,
)
from .versioning import (
    StrategyVersion,
    class_fingerprint,
    parse_version,
    version_eq,
    version_lt,
)


logger = logging.getLogger("quantlab.strategy.registry")


@dataclass
class _Entry:
    """注册表内部条目"""
    cls: Type  # 策略类（可实例化）
    metadata: StrategyMetadata
    versions: List[StrategyVersion] = field(
        default_factory=list
    )


class StrategyRegistry:
    """
    V4.1 策略注册中心（线程安全，进程内单例）

    注册：
        registry.register(MACrossStrategy)
        registry.register(MyStrategy, id="my_id", ...)

    查询：
        registry.list()               → List[StrategyMetadata]
        registry.get("ma_cross")      → StrategyMetadata
        registry.get_version("ma_cross", "1.0.0")
        registry.has("ma_cross")

    构造：
        registry.create("ma_cross", {"fast": 5, "slow": 20})
        registry.create_from_metadata(meta, params)

    版本历史：
        registry.list_versions("ma_cross")
        registry.diff_versions("ma_cross", "1.0.0", "2.0.0")
    """

    def __init__(self) -> None:
        self._items: Dict[str, _Entry] = {}
        self._lock = threading.RLock()

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------
    def register(
        self,
        cls: Type,
        *,
        strategy_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        param_space: Optional[Dict[str, List[Any]]] = None,
        parameters_schema: Optional[
            List[StrategyParameter]
        ] = None,
        override: bool = False,
    ) -> None:
        """
        注册一个策略类

        参数：
          cls                  策略类（必须是 SignalStrategy 子类）
          strategy_id          自定义 ID（缺省从类名推导）
          name                 显示名（缺省从类名推导）
          description          描述
          author               作者
          version              semver（默认 "1.0.0"）
          tags                 标签
          param_space          优化搜索空间
          parameters_schema    自定义参数列表
                               （缺省从 __init__ 签名推导）
          override             已存在时是否覆盖
        """
        if not is_strategy_class(cls):
            raise TypeError(
                f"{cls!r} must be a SignalStrategy subclass"
            )

        with self._lock:
            # ---- 推导 metadata ----
            auto_meta = get_metadata_for_class(cls)

            sid = strategy_id or auto_meta.id
            if not sid:
                raise ValueError(
                    f"strategy_id cannot be empty for {cls}"
                )

            if sid in self._items and not override:
                raise ValueError(
                    f"strategy_id {sid!r} already registered. "
                    f"Use override=True to replace."
                )

            # ---- 构建完整的 StrategyMetadata ----
            final_params: List[StrategyParameter]
            if parameters_schema:
                final_params = list(parameters_schema)
            else:
                final_params = list(auto_meta.parameters)

            # param_space 覆盖
            space: Dict[str, Any] = dict(auto_meta.param_space)
            if param_space:
                space.update(param_space)

            # default_parameters
            defaults: Dict[str, Any] = {}
            for p in final_params:
                if p.default is not None:
                    defaults[p.name] = p.default

            meta = StrategyMetadata(
                id=sid,
                name=name or auto_meta.name,
                description=(
                    description or auto_meta.description
                ),
                author=author or auto_meta.author,
                version=version,
                tags=tags or list(auto_meta.tags),
                parameters=final_params,
                default_parameters=defaults,
                param_space=space,
                class_path=auto_meta.class_path,
                source_path=auto_meta.source_path,
            )

            # ---- 源码快照 ----
            from .versioning import snapshot_source
            src = snapshot_source(cls)
            fp = class_fingerprint(cls)
            ver = StrategyVersion(
                strategy_id=sid,
                version=version,
                class_path=meta.class_path,
                fingerprint=fp,
                source=src,
            )

            entry = _Entry(cls=cls, metadata=meta)
            entry.versions.append(ver)
            self._items[sid] = entry

            logger.info(
                "registered strategy: %s v%s (%s)",
                sid, version, meta.class_path,
            )

    def unregister(self, strategy_id: str) -> bool:
        with self._lock:
            return self._items.pop(strategy_id, None) is not None

    def has(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._items

    # ---------------------------------------------------------
    # 查询
    # ---------------------------------------------------------
    def get(
        self, strategy_id: str
    ) -> Optional[StrategyMetadata]:
        """取元数据（前端最常用）"""
        with self._lock:
            e = self._items.get(strategy_id)
            return e.metadata if e else None

    def get_class(self, strategy_id: str) -> Type:
        """取策略类（构造实例用）"""
        with self._lock:
            e = self._items.get(strategy_id)
        if e is None:
            raise KeyError(
                f"strategy_id {strategy_id!r} not registered. "
                f"known: {self.list_ids()}"
            )
        return e.cls

    def list(self) -> List[StrategyMetadata]:
        """所有策略元数据（列表页用）"""
        with self._lock:
            return [
                e.metadata for e in self._items.values()
            ]

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._items.keys())

    # ---------------------------------------------------------
    # 版本
    # ---------------------------------------------------------
    def list_versions(
        self, strategy_id: str
    ) -> List[StrategyVersion]:
        """策略所有历史版本"""
        with self._lock:
            e = self._items.get(strategy_id)
            return list(e.versions) if e else []

    def get_version(
        self,
        strategy_id: str,
        version: str,
    ) -> Optional[StrategyVersion]:
        """精确取某版本（缺省取最新）"""
        with self._lock:
            e = self._items.get(strategy_id)
        if not e:
            return None
        if version == "latest":
            # 取最新（按 semver）
            vs = sorted(
                e.versions,
                key=lambda v: parse_version(v.version),
                reverse=True,
            )
            return vs[0] if vs else None
        for v in e.versions:
            if v.version == version:
                return v
        return None

    def current_version(
        self, strategy_id: str
    ) -> Optional[StrategyVersion]:
        return self.get_version(strategy_id, "latest")

    # ---------------------------------------------------------
    # 构造
    # ---------------------------------------------------------
    def create(
        self,
        strategy_id: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        version: str = "latest",
    ) -> SignalStrategy:
        """
        构造策略实例

        参数：
          strategy_id  策略 ID
          params       参数字典
          version      版本（默认 latest）
        """
        meta = self.get(strategy_id)
        if meta is None:
            raise KeyError(
                f"strategy_id {strategy_id!r} not found"
            )

        # 取指定版本（或 latest）
        ver = self.get_version(strategy_id, version)
        if ver is None:
            raise KeyError(
                f"version {version!r} for "
                f"{strategy_id!r} not found"
            )

        with self._lock:
            cls = self._items[strategy_id].cls

        # 参数：params > defaults
        merged: Dict[str, Any] = dict(meta.default_parameters)
        if params:
            # 校验
            errors = meta.validate_params(params)
            if errors:
                raise ValueError(
                    f"invalid params: {errors}"
                )
            merged.update(params)

        # 只保留 cls.__init__ 接受的参数
        filtered = _filter_accepted(cls, merged)
        return cls(**filtered)

    def create_from_metadata(
        self,
        meta: StrategyMetadata,
        params: Optional[Dict[str, Any]] = None,
    ) -> SignalStrategy:
        """从 StrategyMetadata + 参数构造实例（不依赖注册表）"""
        return self.create(meta.id, params)

    # ---------------------------------------------------------
    # 工具
    # ---------------------------------------------------------
    def search(
        self,
        q: str = "",
        *,
        tags: Optional[List[str]] = None,
        has_param: Optional[str] = None,
    ) -> List[StrategyMetadata]:
        """
        搜索策略（前端搜索框用）

        参数：
          q          关键词（匹配 id / name / description）
          tags       必须包含的标签（AND）
          has_param  必须有某参数名
        """
        results = self.list()
        if q:
            ql = q.lower()
            results = [
                m
                for m in results
                if (
                    ql in m.id.lower()
                    or ql in m.name.lower()
                    or ql in m.description.lower()
                )
            ]
        if tags:
            results = [
                m
                for m in results
                if all(t in m.tags for t in tags)
            ]
        if has_param:
            results = [
                m
                for m in results
                if has_param in m.parameter_names
            ]
        return results


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


# -------------------------------------------------------------
# 全局单例
# -------------------------------------------------------------
import inspect

_default: Optional[StrategyRegistry] = None
_default_lock = threading.Lock()

# 记录已被 builtin 注册过的策略 class
# loader 扫描时遇到这些 class 直接跳过（避免与 builtin ID 冲突）
_BUILTIN_CLASSES: set = set()
_BUILTIN_CLASSES_LOCK = threading.Lock()


def get_strategy_registry() -> StrategyRegistry:
    """获取（或创建）V4.1 全局注册表"""
    global _default
    with _default_lock:
        if _default is None:
            _default = StrategyRegistry()
            _ensure_builtin(_default)
    return _default


def set_strategy_registry(reg: StrategyRegistry) -> None:
    """替换全局注册表（用于测试）"""
    global _default, _BUILTIN_CLASSES
    with _default_lock:
        _default = reg
    with _BUILTIN_CLASSES_LOCK:
        _BUILTIN_CLASSES.clear()


def is_builtin_class(cls: Type) -> bool:
    """是否被 builtin 显式注册过（loader 跳过这些）"""
    with _BUILTIN_CLASSES_LOCK:
        return cls in _BUILTIN_CLASSES


def _ensure_builtin(reg: StrategyRegistry) -> None:
    """注册 4 个内置策略（幂等）"""
    from ..signals import (
        MACrossStrategy,
        RSIStrategy,
        Alpha001Strategy,
        AlphaMultiFactorStrategy,
    )

    _register_builtin(
        reg,
        MACrossStrategy,
        strategy_id="ma_cross",
        name="MA Cross",
        description="双均线交叉策略（多标的）",
        tags=["classic", "trend"],
        param_space={
            "fast": [5, 10, 20, 30, 50],
            "slow": [30, 60, 90, 120],
        },
    )

    _register_builtin(
        reg,
        RSIStrategy,
        strategy_id="rsi",
        name="RSI",
        description="RSI 超买超卖均值回归",
        tags=["mean_reversion", "oscillator"],
        parameters_schema=[
            StrategyParameter(
                name="period",
                type="int",
                default=14,
                min_value=2,
                max_value=100,
                description="RSI 计算周期",
            ),
            StrategyParameter(
                name="oversold",
                type="float",
                default=30.0,
                min_value=0.0,
                max_value=50.0,
                description="超卖阈值",
            ),
            StrategyParameter(
                name="overbought",
                type="float",
                default=70.0,
                min_value=50.0,
                max_value=100.0,
                description="超买阈值",
            ),
            StrategyParameter(
                name="use_trend_filter",
                type="bool",
                default=False,
                description="是否叠加趋势过滤",
            ),
            StrategyParameter(
                name="trend_period",
                type="int",
                default=200,
                min_value=20,
                max_value=500,
                description="趋势过滤周期",
            ),
        ],
        param_space={
            "period": [7, 14, 21],
            "oversold": [20.0, 30.0],
            "overbought": [70.0, 80.0],
        },
    )

    _register_builtin(
        reg,
        Alpha001Strategy,
        strategy_id="alpha001",
        name="Alpha 001",
        description="WorldQuant Alpha101 #001",
        tags=["alpha101", "selection"],
        param_space={"period": [6, 10, 20]},
    )

    _register_builtin(
        reg,
        AlphaMultiFactorStrategy,
        strategy_id="alpha_multifactor",
        name="Alpha Multi-Factor",
        description="Alpha009+040+049 多因子合成",
        tags=["alpha101", "selection"],
        param_space={"w9": [0.0, 1.0 / 3, 0.5]},
    )


def _register_builtin(
    reg: StrategyRegistry,
    cls: Type,
    **kwargs,
) -> None:
    try:
        sid = kwargs.get(
            "strategy_id", cls.__name__
        )
        if not reg.has(sid):
            reg.register(cls, **kwargs)
            with _BUILTIN_CLASSES_LOCK:
                _BUILTIN_CLASSES.add(cls)
    except Exception as exc:
        logger.warning(
            "register builtin %s failed: %s",
            kwargs.get("strategy_id", cls.__name__),
            exc,
        )
