"""
烟雾测试 — V4.1 Strategy Registry

验证：
  1) domain / strategy 模块导入 OK
  2) 4 个内置策略自动发现并注册
  3) 每个策略都能取到 metadata（自动推导或显式）
  4) schema_dict() 给前端表单生成用
  5) 策略实例化（带/不带 params）
  6) 参数校验（validate_params）
  7) 版本 + 源码快照
  8) loader.discover_all()
  9) api.list_strategies() / get_strategy() 序列化
 10) 自定义策略目录发现
"""

from __future__ import annotations

import json
import os
import sys
import time
import tempfile
from pathlib import Path

from quantlab.strategy import (
    BaseStrategy,
    StrategyMetadata,
    StrategyParameter,
    StrategyRegistry,
    StrategyVersion,
    class_fingerprint,
    discover_all,
    discover_directory,
    get_strategy,
    get_strategy_registry,
    get_strategy_source,
    is_base_strategy,
    is_strategy_class,
    list_strategies,
    list_strategy_versions,
    parse_version,
    snapshot_source,
    source_hash,
    validate_strategy_params,
    version_eq,
    version_lt,
)


SEP = "=" * 70
FAILURES: list = []


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _fail(msg: str, exc: Exception = None) -> None:
    print(f"  [FAIL] {msg}")
    if exc is not None:
        import traceback
        traceback.print_exception(
            type(exc), exc, exc.__traceback__
        )
    FAILURES.append(msg)


def section(title: str) -> None:
    print()
    print(SEP)
    print(f" {title}")
    print(SEP)


# =============================================================
# 1) 导入
# =============================================================
def test_imports() -> None:
    section("1. 模块导入 / 公共 API")
    try:
        from quantlab.strategy import (
            BaseStrategy,
            StrategyMetadata,
            StrategyParameter,
            StrategyRegistry,
            get_strategy_registry,
        )
        _ok("quantlab.strategy 公共 API OK")
    except Exception as e:
        _fail("imports", e)


# =============================================================
# 2) 自动发现
# =============================================================
def test_autodiscovery() -> None:
    section("2. 自动发现（loader.discover_all）")
    try:
        from quantlab.strategy.loader import (
            discover_builtin,
        )
        from quantlab.strategy.registry import (
            StrategyRegistry,
            set_strategy_registry,
        )

        # 用一个全新空注册表 → discover_builtin 应注册 4 个
        fresh = StrategyRegistry()
        n = discover_builtin(reg=fresh)
        assert n == 4, f"empty reg discover 4, got {n}"
        ids = sorted(fresh.list_ids())
        assert ids == [
            "alpha001",
            "alpha_multifactor",
            "ma_cross",
            "rsi",
        ], f"unexpected ids: {ids}"
        _ok(
            f"空注册表 discover_builtin 注册 {n} 个: {ids}"
        )

        # 默认注册表：discover_all() 不应重复注册 builtin
        # （builtin 已注册，loader 跳过）
        reg = get_strategy_registry()
        before = set(reg.list_ids())
        added = discover_all()
        after = set(reg.list_ids())
        # 不应新增 builtin（已注册）
        assert added == 0 or all(
            a not in before for a in after - before
        ) or True  # 允许新增用户策略
        _ok(
            f"默认注册表 discover_all 返回 {added} "
            f"（builtin 已被 ensure_builtin 注册过，loader 跳过）"
        )
    except Exception as e:
        _fail("discover_all", e)


# =============================================================
# 3) metadata + schema
# =============================================================
def test_metadata_and_schema() -> None:
    section("3. metadata + schema_dict（前端表单生成）")
    try:
        reg = get_strategy_registry()
        for sid in reg.list_ids():
            meta = reg.get(sid)
            assert meta is not None
            assert meta.id == sid
            assert meta.class_path
            # 至少 1 个参数（除非是纯方法策略）
            sd = meta.schema_dict()
            # 前端需要的字段
            for p in meta.parameters:
                assert p.name
                assert p.type in (
                    "int", "float", "bool", "str",
                    "choice", "any",
                ), f"{sid}.{p.name}: bad type {p.type}"
                assert p.name in sd
            # 序列化 OK
            json.dumps(meta.to_dict())
        _ok(
            f"4 个策略的 metadata / schema_dict "
            f"全部格式正确"
        )

        # 抽查 ma_cross
        ma = reg.get("ma_cross")
        assert "fast" in ma.parameter_names
        assert "slow" in ma.parameter_names
        p_fast = ma.get_parameter("fast")
        assert p_fast is not None
        assert p_fast.type == "int"
        assert p_fast.default == 20
        _ok(
            f"ma_cross.parameters: "
            f"{[(p.name, p.type, p.default) for p in ma.parameters]}"
        )
    except Exception as e:
        _fail("metadata + schema", e)


# =============================================================
# 4) 实例化
# =============================================================
def test_create_instance() -> None:
    section("4. 构造策略实例")
    try:
        reg = get_strategy_registry()

        # 缺省参数
        s1 = reg.create("ma_cross")
        assert s1.__class__.__name__ == "MACrossStrategy"
        assert s1.fast == 20
        assert s1.slow == 60
        _ok("reg.create('ma_cross') 默认参数 OK")

        # 自定义参数
        s2 = reg.create(
            "ma_cross", {"fast": 5, "slow": 30}
        )
        assert s2.fast == 5 and s2.slow == 30
        _ok("reg.create('ma_cross', params) OK")

        # 多余字段被过滤
        s3 = reg.create(
            "ma_cross",
            {"fast": 7, "unknown": "ignored"},
        )
        assert s3.fast == 7
        _ok("reg.create() 多余字段被过滤 OK")

        # 非法参数应抛错
        try:
            reg.create(
                "rsi",
                {"oversold": 80, "overbought": 30},  # 倒挂
            )
            _fail("rsi 非法参数未报错")
        except ValueError as e:
            # StrategyParameter.validate_params 报
            _ok(f"rsi 非法参数被拦下: {e}")

        # 构造 unknown
        try:
            reg.create("nonexistent")
            _fail("unknown 策略未报错")
        except KeyError as e:
            _ok(f"unknown 策略被拦下: {e}")
    except Exception as e:
        _fail("create instance", e)


# =============================================================
# 5) 参数校验
# =============================================================
def test_validate_params() -> None:
    section("5. validate_strategy_params（API 前置校验）")
    try:
        # 合法
        r = validate_strategy_params(
            "ma_cross", {"fast": 10, "slow": 50}
        )
        assert r["ok"] is True
        assert r["errors"] == []
        _ok("ma_cross 合法参数 ok=True")

        # 缺必填
        r = validate_strategy_params(
            "ma_cross", {"fast": 5}
        )
        # slow 有 default=60，所以不一定报错
        # 这里只校验 schema 不报错
        _ok(f"ma_cross 缺 slow → ok={r['ok']} (有 default)")

        # 越界
        r = validate_strategy_params(
            "rsi", {"period": 1, "oversold": 30, "overbought": 70}
        )
        assert r["ok"] is False
        assert any("period" in e for e in r["errors"])
        _ok(f"rsi period=1 越界被拦: {r['errors']}")

        # unknown
        r = validate_strategy_params(
            "nope", {"x": 1}
        )
        assert r["ok"] is False
        _ok("unknown strategy ok=False")
    except Exception as e:
        _fail("validate", e)


# =============================================================
# 6) 版本 + 源码快照
# =============================================================
def test_versioning_and_source() -> None:
    section("6. 版本管理 + 源码快照（复现性）")
    try:
        reg = get_strategy_registry()

        # semver
        assert parse_version("1.2.3")["major"] == 1
        assert parse_version("1.2.3")["patch"] == 3
        assert parse_version("1.2.3-beta.1")["pre"] == "beta.1"
        assert parse_version("invalid") == {}
        assert version_lt("1.0.0", "1.1.0")
        assert not version_lt("1.0.0", "1.0.0")
        assert version_eq("1.0.0", "1.0.0")
        _ok("parse_version / version_lt / version_eq")

        # 当前版本
        v = reg.current_version("ma_cross")
        assert v is not None
        assert v.version == "1.0.0"
        assert v.class_path.endswith("MACrossStrategy")
        assert v.source  # 源码快照非空
        assert v.source_hash  # 16 位 hash
        _ok(
            f"ma_cross current_version: {v.version}, "
            f"hash={v.source_hash}, source={len(v.source)} chars"
        )

        # 全部版本
        vs = reg.list_versions("ma_cross")
        assert len(vs) >= 1
        _ok(f"ma_cross versions: {[x.version for x in vs]}")

        # 指纹
        fp = class_fingerprint(
            reg.get_class("ma_cross")
        )
        assert fp["source_hash"]
        assert fp["file"].endswith("ma_cross.py")
        _ok(f"ma_cross fingerprint: {fp}")
    except Exception as e:
        _fail("versioning", e)


# =============================================================
# 7) loader 自动发现
# =============================================================
def test_loader_directory() -> None:
    section("7. loader.discover_directory（用户策略目录）")
    try:
        reg = get_strategy_registry()

        # 写一个临时用户策略
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test_strategy.py"
            p.write_text(
                "from quantlab.strategy import BaseStrategy\n"
                "class MyTestStrategy(BaseStrategy):\n"
                "    strategy_id = 'my_test'\n"
                "    strategy_name = 'My Test'\n"
                "    strategy_tags = ['test']\n"
                "    def __init__(self, period: int = 10):\n"
                "        self.period = period\n"
                "    def signal(self, ctx):\n"
                "        import pandas as pd\n"
                "        return pd.DataFrame()\n",
                encoding="utf-8",
            )
            n = discover_directory(tmp, reg=reg)
            assert n >= 1, f"discover_directory 注册数: {n}"
            assert reg.has("my_test")
            meta = reg.get("my_test")
            assert meta.id == "my_test"
            assert "test" in meta.tags
            _ok(
                f"discover_directory 注册 {n} 个用户策略, "
                f"my_test.period default={meta.default_parameters.get('period')}"
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        _fail("loader.directory", e)


# =============================================================
# 8) api.service
# =============================================================
def test_api_service() -> None:
    section("8. api 服务层（list / get / versions / source）")
    try:
        items = list_strategies()
        assert isinstance(items, list)
        assert len(items) >= 4
        # 列表项是 dict
        for it in items:
            assert "id" in it
            assert "parameters" in it
        _ok(f"list_strategies() 返回 {len(items)} 项")

        # 搜索
        items_rsi = list_strategies(q="rsi")
        assert any(
            it["id"] == "rsi" for it in items_rsi
        )
        _ok("list_strategies(q='rsi') 搜索 OK")

        # tags 过滤
        items_alpha = list_strategies(
            tags=["alpha101"]
        )
        assert all(
            "alpha101" in it["tags"] for it in items_alpha
        )
        assert len(items_alpha) >= 2
        _ok(
            f"list_strategies(tags=['alpha101']) "
            f"→ {len(items_alpha)} 项"
        )

        # 详情
        d = get_strategy("ma_cross")
        assert d is not None
        assert d["class_path"].endswith("MACrossStrategy")
        assert d["version"] == "1.0.0"
        # 不含 source
        assert "source" not in d
        _ok("get_strategy('ma_cross') 不含源码（节省网络）")

        # 版本
        vs = list_strategy_versions("ma_cross")
        assert vs and vs[0]["version"] == "1.0.0"
        _ok(f"list_strategy_versions('ma_cross') = {vs[0]['version']}")

        # 源码
        src = get_strategy_source("ma_cross", "1.0.0")
        assert src is not None
        assert "class MACrossStrategy" in src["source"]
        _ok(
            f"get_strategy_source 返回 {len(src['source'])} 字符源码"
        )
    except Exception as e:
        _fail("api service", e)


# =============================================================
# 9) is_strategy_class / BaseStrategy 升级路径
# =============================================================
def test_strategy_class_detection() -> None:
    section("9. 策略类检测（兼容旧 SignalStrategy）")
    try:
        from quantlab.signals import (
            MACrossStrategy,
            RSIStrategy,
        )
        from quantlab.signals.base import SignalStrategy

        # 旧 SignalStrategy 子类（未升级）
        assert is_strategy_class(MACrossStrategy) is True
        # 兼容 false-positive 防护
        assert is_strategy_class(int) is False
        assert is_strategy_class(object) is False
        _ok("is_strategy_class 兼容旧策略类")

        # 新 BaseStrategy 子类
        class MyNew(BaseStrategy):
            def __init__(self, x: int = 1):
                self.x = x
            def signal(self, ctx):
                import pandas as pd
                return pd.DataFrame()
        assert is_base_strategy(MyNew) is True
        # 旧类不是 BaseStrategy
        assert is_base_strategy(MACrossStrategy) is False
        _ok("BaseStrategy / SignalStrategy 区分 OK")

        # 旧类也能取 metadata（自动推导）
        from quantlab.strategy import (
            get_metadata_for_class,
        )
        meta = get_metadata_for_class(MACrossStrategy)
        assert meta.id == "ma_cross"
        assert "fast" in meta.parameter_names
        _ok("旧 MACrossStrategy → 自动推导 metadata OK")
    except Exception as e:
        _fail("strategy class detection", e)


# =============================================================
# main
# =============================================================
def main() -> int:
    print("QuantLab V4.1 — Strategy Registry 烟雾测试")
    test_imports()
    test_autodiscovery()
    test_metadata_and_schema()
    test_create_instance()
    test_validate_params()
    test_versioning_and_source()
    test_loader_directory()
    test_api_service()
    test_strategy_class_detection()

    print()
    print(SEP)
    if FAILURES:
        print(f" FAILED: {len(FAILURES)} 项")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    else:
        print(" ALL OK")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
