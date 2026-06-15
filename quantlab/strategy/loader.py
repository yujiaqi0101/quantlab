"""
V4.1 Strategy Registry — Loader

策略自动发现：
  1) quantlab.signals/         内置策略（保证一定发现）
  2) <cwd>/strategies/          用户自定义策略
  3) <cwd>/plugins/*.zip        第三方策略插件（占位接口）
  4) 显式 importlib.import_module

调用方：
    from quantlab.strategy.loader import discover_all
    discover_all()
    reg = get_strategy_registry()
    reg.list()    # 包含所有发现到的策略

注意：
  - 自动发现只做"扫描 + import + 注册"
  - 失败策略自动跳过，不影响其它策略
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import os
import pkgutil
import sys
import zipimport
from pathlib import Path
from typing import Iterable, List, Optional, Type

from ..signals.base import SignalStrategy
from .base import (
    BaseStrategy,
    is_strategy_class,
)
from .registry import (
    StrategyRegistry,
    get_strategy_registry,
)


logger = logging.getLogger("quantlab.strategy.loader")


# -------------------------------------------------------------
# 内置扫描
# -------------------------------------------------------------
def discover_builtin(
    reg: Optional[StrategyRegistry] = None,
) -> int:
    """
    加载 quantlab.signals 下的内置策略（走 builtin 路径）

    注意：走显式 ID 路径（_ensure_builtin）而不是 _scan_package
          因为：
            - 显式 ID 稳定（"alpha_multifactor"）
            - 启发式对 "AlphaMultiFactor" 无法同时满足
              "MACross" 和 "AlphaMultiFactor" 两种风格
            - 内置策略 ID 应由代码控制，不应由算法推导

    返回新注册成功的数量
    """
    from .registry import _ensure_builtin

    reg = reg or get_strategy_registry()
    before = set(reg.list_ids())
    _ensure_builtin(reg)
    after = set(reg.list_ids())
    return len(after - before)


def discover_directory(
    directory: str,
    reg: Optional[StrategyRegistry] = None,
    package_prefix: str = "user_strategies",
) -> int:
    """
    扫描一个目录里所有 .py 文件
    - 目录会被加入 sys.path（按 package_prefix 命名）
    - 每个 .py 文件作为 module 被 import
    - 扫到的 SignalStrategy 子类自动注册

    用法：
        discover_directory("./strategies")
    """
    reg = reg or get_strategy_registry()
    p = Path(directory).resolve()
    if not p.is_dir():
        logger.warning(
            "discover_directory: %s is not a dir", p
        )
        return 0

    # 把目录加入 sys.path
    parent = str(p.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    n = 0
    for py in p.glob("*.py"):
        if py.name.startswith("_"):
            continue
        module_name = f"{package_prefix}.{py.stem}"
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, str(py)
            )
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            n += _register_module_classes(reg, mod)
        except Exception as exc:
            logger.warning(
                "discover_directory %s failed: %s",
                py, exc,
            )
    return n


def discover_plugin(
    plugin_path: str,
    reg: Optional[StrategyRegistry] = None,
) -> int:
    """
    加载一个第三方策略插件（.zip 形式）

    注意：
      - 此接口预留（V4.2+ 完整支持）
      - 当前实现：当作 zip 加载 + 扫 module
      - 失败抛异常，调用方决定是否重试
    """
    reg = reg or get_strategy_registry()
    p = Path(plugin_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(p)

    try:
        z = zipimport.zipimporter(str(p))
    except zipimport.ZipImportError as exc:
        raise RuntimeError(
            f"invalid plugin zip: {p} ({exc})"
        )

    # 找到 zip 里的所有 .py module 名
    # zipimporter 没有直接 list API；通过加载 __init__ 间接试
    n = 0
    # 尝试从 zip 内若干常见名字加载
    for stem in _iter_zip_modules(z):
        try:
            mod = z.load_module(stem)
        except Exception as exc:
            logger.debug(
                "skip %s: %s", stem, exc
            )
            continue
        n += _register_module_classes(reg, mod)
    return n


def _iter_zip_modules(
    z: zipimport.zipimporter,
) -> Iterable[str]:
    """
    试图列举 zipimporter 看到的模块名
    没标准 API，实践上只有 load_module 名字已知时才靠谱
    → 优先尝试常见入口
    """
    candidates = [
        "strategies",
        "plugin",
        "main",
    ]
    for name in candidates:
        try:
            if z.find_module(name) is not None:
                yield name
        except (ImportError, zipimport.ZipImportError):
            continue


# -------------------------------------------------------------
# 一站式发现
# -------------------------------------------------------------
def discover_all(
    reg: Optional[StrategyRegistry] = None,
    user_dirs: Optional[List[str]] = None,
    plugin_paths: Optional[List[str]] = None,
) -> int:
    """
    一次性发现所有策略：
      1) quantlab.signals/    （内置）
      2) user_dirs            （用户目录）
      3) plugin_paths         （插件 zip）

    返回总注册成功数
    """
    reg = reg or get_strategy_registry()
    n = 0
    n += discover_builtin(reg)
    if user_dirs:
        for d in user_dirs:
            n += discover_directory(d, reg=reg)
    if plugin_paths:
        for p in plugin_paths:
            try:
                n += discover_plugin(p, reg=reg)
            except Exception as exc:
                logger.warning(
                    "discover_plugin %s failed: %s",
                    p, exc,
                )
    return n


# -------------------------------------------------------------
# 内部：包扫描
# -------------------------------------------------------------
def _scan_package(
    reg: StrategyRegistry, package_name: str
) -> int:
    """
    用 pkgutil.iter_modules 扫一个 package 下所有子模块
    """
    try:
        pkg = importlib.import_module(package_name)
    except ImportError as exc:
        logger.warning(
            "cannot import %s: %s", package_name, exc
        )
        return 0

    n = 0
    if hasattr(pkg, "__path__"):
        for mod_info in pkgutil.iter_modules(
            getattr(pkg, "__path__")
        ):
            full = f"{package_name}.{mod_info.name}"
            try:
                mod = importlib.import_module(full)
            except Exception as exc:
                logger.debug(
                    "skip %s: %s", full, exc
                )
                continue
            n += _register_module_classes(reg, mod)
    else:
        n += _register_module_classes(reg, pkg)
    return n


def _register_module_classes(
    reg: StrategyRegistry, module
) -> int:
    """
    扫描 module 里的所有 SignalStrategy 子类
    注册到 reg
    返回新增数量
    """
    from .registry import is_builtin_class

    n = 0
    for name, obj in inspect.getmembers(
        module, inspect.isclass
    ):
        if not is_strategy_class(obj):
            continue
        # 排除从其它包 import 进来的类（只注册本 module 定义的）
        if obj.__module__ != module.__name__:
            continue
        # builtin 已注册过的 class 跳过（避免 ID 冲突）
        if is_builtin_class(obj):
            continue
        sid = _derive_id(obj, name)
        if reg.has(sid) and not reg.get(sid):
            continue
        try:
            reg.register(obj, strategy_id=sid)
            n += 1
        except ValueError:
            continue
        except Exception as exc:
            logger.warning(
                "register %s failed: %s", sid, exc
            )
    return n


def _derive_id(cls: Type, fallback_name: str) -> str:
    """
    从类名推导 ID
      MACrossStrategy     → "ma_cross"
      Alpha001Strategy    → "alpha001"
      AlphaMultiFactor    → "alpha_multi_factor"
      RSI                 → "rsi"
      MyCustom            → "my_custom"
    """
    sid = getattr(cls, "strategy_id", "")
    if sid:
        return sid
    name = cls.__name__
    if name.endswith("Strategy"):
        name = name[:-8]
    if not name:
        return fallback_name.lower()
    if name.isupper() and len(name) <= 4:
        return name.lower()
    # 复用 base._class_name_to_id 的 token 规则
    from .base import _class_name_to_id

    return _class_name_to_id(name) or fallback_name.lower()


def is_base_strategy(cls: Type) -> bool:
    try:
        return issubclass(cls, BaseStrategy)
    except TypeError:
        return False
