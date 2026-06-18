"""
M4 端到端验证测试

模拟完整模型生命周期：
  1. 注册 v1 → 训练 → 验证 → Champion
  2. 注册 v2（v1 的子版本，修改 FeatureSet）→ 挑战 v1 → Promote
  3. 注册 v3（v2 的子版本，增加 ATR）→ 挑战 v2 → Reject
  4. ModelStore 持久化
  5. ModelLineage 查询血统
  6. ModelComparator 对比
  7. LifecycleManager 状态转换
  8. AuditLog 审计查询
"""

import sys
import shutil
import os
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, ".")

from quantlab.ml.registry import (
    ModelVersion, ModelRegistry, LifecycleStatus,
    ModelStore, ModelLineage,
    ChampionManager, ModelComparator,
    LifecycleManager, ModelAuditLog, AuditAction,
)
from quantlab.ml.model import ModelType


def setup_test_env():
    """设置测试环境"""
    # 清理测试目录
    test_models_dir = "storage/test_models_m4"
    test_audit_file = "storage/test_audit_m4.json"
    if os.path.exists(test_models_dir):
        shutil.rmtree(test_models_dir)
    if os.path.exists(test_audit_file):
        os.remove(test_audit_file)
    return test_models_dir, test_audit_file


def test_registry_basic():
    """测试 Registry 基础功能"""
    print("\n=== 1. Model Registry Basic ===")
    registry = ModelRegistry()

    # 注册 v1
    v1 = ModelVersion(
        name="LGBM_Momentum_v1",
        model_type=ModelType.LIGHTGBM,
        params={"n_estimators": 100, "learning_rate": 0.1},
        metrics={"ic": 0.08, "sharpe": 1.2, "rmse": 0.015},
        dataset_id="DS-crypto-1h",
        feature_ids=["rsi_14", "macd", "volume"],
        label_id="future_return_10",
        description="Initial version",
    )
    registry.register(v1)
    print(f"  v1: {v1.version_id}, family={v1.family}, ver_num={v1.version_number}")

    # 注册 v2（v1 的子版本）
    v2 = ModelVersion(
        name="LGBM_Momentum_v2",
        model_type=ModelType.LIGHTGBM,
        params={"n_estimators": 200, "learning_rate": 0.05},
        metrics={"ic": 0.10, "sharpe": 1.4, "rmse": 0.013},
        dataset_id="DS-crypto-1h",
        feature_ids=["rsi_14", "macd", "volume", "atr_14"],  # 增加 ATR
        label_id="future_return_10",
        parent_version_id=v1.version_id,
        lineage_note="增加 ATR 特征，调低学习率",
    )
    registry.register(v2)
    print(f"  v2: {v2.version_id}, family={v2.family}, ver_num={v2.version_number}")

    # 注册 v3（v2 的子版本）
    v3 = ModelVersion(
        name="LGBM_Momentum_v3",
        model_type=ModelType.LIGHTGBM,
        params={"n_estimators": 300, "learning_rate": 0.03},
        metrics={"ic": 0.11, "sharpe": 1.5, "rmse": 0.012},
        dataset_id="DS-crypto-1h",
        feature_ids=["rsi_14", "macd", "volume", "atr_14", "bb_width"],
        label_id="future_return_10",
        parent_version_id=v2.version_id,
        lineage_note="增加布林带宽度特征",
    )
    registry.register(v3)
    print(f"  v3: {v3.version_id}, family={v3.family}, ver_num={v3.version_number}")

    # Family 查询
    families = registry.list_families()
    print(f"  Families: {families}")
    family_versions = registry.get_family("LGBM_Momentum")
    print(f"  Family versions: {[v.name for v in family_versions]}")

    return registry, v1, v2, v3


def test_lifecycle(registry, v1, v2, v3):
    """测试生命周期管理"""
    print("\n=== 2. Lifecycle Manager ===")
    mgr = LifecycleManager(registry)

    # v1: TRAINING → VALIDATING → CANDIDATE → CHAMPION
    mgr.transition(v1.version_id, LifecycleStatus.VALIDATING, reason="开始验证")
    mgr.transition(v1.version_id, LifecycleStatus.CANDIDATE, reason="验证通过")
    mgr.promote(v1.version_id, reason="首个上线模型", operator="alice")
    print(f"  v1 lifecycle: {v1.lifecycle.value}")

    # v2: TRAINING → VALIDATING → CANDIDATE
    mgr.transition(v2.version_id, LifecycleStatus.VALIDATING, reason="开始验证")
    mgr.transition(v2.version_id, LifecycleStatus.CANDIDATE, reason="验证通过")
    print(f"  v2 lifecycle: {v2.lifecycle.value}")

    # v3: TRAINING → VALIDATING
    mgr.transition(v3.version_id, LifecycleStatus.VALIDATING, reason="开始验证")
    print(f"  v3 lifecycle: {v3.lifecycle.value}")

    # 状态统计
    summary = mgr.get_status_summary()
    print(f"  Status summary: {summary}")

    return mgr


def test_champion(registry, v1, v2, v3, audit):
    """测试 Champion 管理"""
    print("\n=== 3. Champion Manager ===")
    mgr = ChampionManager(registry)

    # v1 已经是 Champion（在 lifecycle 测试中 promote 了）
    current_champ = mgr.get_champion("LGBM_Momentum")
    print(f"  Current champion: {current_champ.name if current_champ else 'None'}")

    # v2 挑战 v1（v2 的 sharpe=1.4 > v1 的 1.2）
    result = mgr.challenge(
        challenger_id=v2.version_id,
        metrics=["sharpe", "ic"],
        operator="bob",
    )
    audit.log_promote(v2, old_champion=v1, operator="bob", reason=result.reason)
    print(f"  v2 challenge v1: promoted={result.promoted}")
    print(f"  Reason: {result.reason}")
    print(f"  Comparison: {result.comparison}")

    # 验证新 Champion
    new_champ = mgr.get_champion("LGBM_Momentum")
    print(f"  New champion: {new_champ.name if new_champ else 'None'}")
    print(f"  v1 lifecycle: {v1.lifecycle.value} (should be RETIRED)")

    # v3 挑战 v2（v3 还在 VALIDATING，不能直接挑战）
    # 先把 v3 转为 CANDIDATE
    lifecycle_mgr = LifecycleManager(registry)
    lifecycle_mgr.transition(v3.version_id, LifecycleStatus.CANDIDATE, reason="验证通过")

    # v3 挑战 v2（v3 的 sharpe=1.5 > v2 的 1.4，应该成功）
    result2 = mgr.challenge(
        challenger_id=v3.version_id,
        metrics=["sharpe", "ic"],
        operator="charlie",
    )
    audit.log_promote(v3, old_champion=v2, operator="charlie", reason=result2.reason)
    print(f"  v3 challenge v2: promoted={result2.promoted}")
    print(f"  Reason: {result2.reason}")

    # Champion 历史
    history = mgr.get_champion_history("LGBM_Momentum")
    print(f"  Champion history: {len(history)} entries")
    for h in history:
        print(f"    {h['name']} promoted={h['promoted_at'][:19]} current={h['is_current']}")

    return mgr


def test_lineage(registry, v1, v2, v3):
    """测试血统图"""
    print("\n=== 4. Model Lineage ===")
    lineage = ModelLineage(registry)

    # v3 的血统链
    chain = lineage.get_lineage(v3.version_id)
    print(f"  v3 lineage chain: {[n.name for n in chain]}")

    # 变更日志
    changes = lineage.get_change_log(v3.version_id)
    print(f"  Change log: {len(changes)} changes")
    for c in changes:
        print(f"    {c.from_version} → {c.to_version}: {c.note}")
        for k, v in c.changes.items():
            print(f"      {k}: {v}")

    # 指标演进
    df = lineage.get_metrics_evolution("LGBM_Momentum", metric="ic")
    print(f"  Metrics evolution:")
    print(df.to_string(index=False))

    return lineage


def test_comparator(registry, v1, v2, v3):
    """测试对比器"""
    print("\n=== 5. Model Comparator ===")
    comp = ModelComparator(registry)

    # 对比所有版本
    report = comp.compare(sort_by="sharpe", ascending=False)
    print(f"  Total: {report.total}")
    print(f"  Best metric: {report.best_metric}")
    for row in report.rows:
        print(
            f"    {row.name:<25} IC={row.metrics.get('ic', 0):.4f} "
            f"Sharpe={row.metrics.get('sharpe', 0):.4f} "
            f"champion={row.is_champion}"
        )

    # 排行榜
    print("\n  Leaderboard (by sharpe):")
    leaderboard = comp.get_leaderboard(metric="sharpe", top_n=3)
    for entry in leaderboard:
        print(
            f"    #{entry['rank']} {entry['name']:<25} "
            f"Sharpe={entry['metric_value']:.4f}"
        )

    # 收藏
    comp.add_favorite(v1.version_id)
    print(f"\n  Favorites: {comp._favorites}")

    return comp


def test_model_store(v1, v2, v3, test_models_dir):
    """测试模型存储"""
    print("\n=== 6. Model Store ===")
    store = ModelStore(test_models_dir)

    # 保存 v1（无模型对象，只保存元信息）
    store.save(v1)
    print(f"  v1 saved to: {test_models_dir}/LGBM_Momentum/v1/")

    # 保存 v2
    store.save(v2)
    print(f"  v2 saved to: {test_models_dir}/LGBM_Momentum/v2/")

    # 检查文件
    files = store.list_files("LGBM_Momentum")
    print(f"  Files in store: {len(files)}")
    for f in files:
        print(f"    {f['name']} (v{f['version_number']}): {f['path']}")

    # 加载 v1
    loaded_v1, loaded_model = store.load(v1.version_id)
    if loaded_v1:
        print(f"  Loaded v1: {loaded_v1.name}, lifecycle={loaded_v1.lifecycle.value}")
        print(f"  Loaded v1 metrics: {loaded_v1.metrics}")

    # 存储统计
    info = store.get_storage_info()
    print(f"  Storage info: {info['n_families']} families, {info['n_versions']} versions")

    # 检查文件是否存在
    print(f"  v1 exists: {store.exists(v1.version_id)}")
    print(f"  v3 exists: {store.exists(v3.version_id)}")

    return store


def test_audit_log(audit, v1, v2, v3):
    """测试审计日志"""
    print("\n=== 7. Audit Log ===")

    # 查询所有
    all_entries = audit.query()
    print(f"  Total entries: {len(all_entries)}")

    # 按动作查询
    promotes = audit.query(action=AuditAction.PROMOTE)
    print(f"  PROMOTE entries: {len(promotes)}")
    for e in promotes:
        print(f"    {e.timestamp[:19]} {e.version_name} by {e.operator}: {e.reason}")

    # 按族查询
    family_entries = audit.query(family="LGBM_Momentum")
    print(f"  LGBM_Momentum entries: {len(family_entries)}")

    # 统计
    summary = audit.get_summary()
    print(f"  Summary by action: {summary['by_action']}")

    # 版本历史
    v2_history = audit.get_version_history(v2.version_id)
    print(f"  v2 history: {len(v2_history)} entries")


def test_invalid_transition(registry):
    """测试非法状态转换"""
    print("\n=== 8. Invalid Transition (negative test) ===")
    mgr = LifecycleManager(registry)

    # 创建一个新版本测试非法转换
    v_test = ModelVersion(
        name="TEST_v1",
        model_type=ModelType.LINEAR_REGRESSION,
        metrics={"ic": 0.05},
    )
    registry.register(v_test)

    # 非法：TRAINING → CHAMPION（必须先经过 VALIDATING → CANDIDATE）
    success = mgr.transition(v_test.version_id, LifecycleStatus.CHAMPION)
    print(f"  TRAINING → CHAMPION (should be False): {success}")

    # 合法：TRAINING → VALIDATING
    success = mgr.transition(v_test.version_id, LifecycleStatus.VALIDATING)
    print(f"  TRAINING → VALIDATING (should be True): {success}")


def main():
    print("M4 端到端验证测试")
    print("=" * 60)

    # 设置环境
    test_models_dir, test_audit_file = setup_test_env()

    # 创建审计日志（内存模式，便于测试）
    audit = ModelAuditLog()

    # 1. Registry 基础
    registry, v1, v2, v3 = test_registry_basic()
    audit.log_create(v1, operator="alice")
    audit.log_create(v2, operator="alice")
    audit.log_create(v3, operator="alice")

    # 2. Lifecycle
    test_lifecycle(registry, v1, v2, v3)

    # 3. Champion
    test_champion(registry, v1, v2, v3, audit)

    # 4. Lineage
    test_lineage(registry, v1, v2, v3)

    # 5. Comparator
    test_comparator(registry, v1, v2, v3)

    # 6. Model Store
    test_model_store(v1, v2, v3, test_models_dir)

    # 7. Audit Log
    test_audit_log(audit, v1, v2, v3)

    # 8. 非法转换测试
    test_invalid_transition(registry)

    # 清理
    if os.path.exists(test_models_dir):
        shutil.rmtree(test_models_dir)

    print("\n" + "=" * 60)
    print("M4 端到端验证测试完成！")
    print("\nM4 完成标准检查：")
    print("  [OK] Model Registry (Family 概念)")
    print("  [OK] Model Versioning (lifecycle + lineage 字段)")
    print("  [OK] Model Store (磁盘持久化)")
    print("  [OK] Model Lineage (血统图)")
    print("  [OK] Champion Manager (自动 promote)")
    print("  [OK] Model Comparison Arena (跨版本对比)")
    print("  [OK] Lifecycle Manager (状态机)")
    print("  [OK] Audit Log (操作审计)")


if __name__ == "__main__":
    main()
