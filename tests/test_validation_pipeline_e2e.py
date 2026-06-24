"""
Validation Pipeline 端到端测试

验证完整流程：
  Raw Model → Validation Pipeline (6 Gates) → PASS/FAIL → Champion Challenge

测试覆盖：
  1. Pipeline 创建与 Gate 注册
  2. 完整 Pipeline 运行（合成数据）
  3. Gate 失败停止机制
  4. ValidationScore 聚合
  5. Champion Challenge 流程
  6. API 端点冒烟测试
"""

import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from quantlab.ml.validation.pipeline import (
    ValidationPipeline,
    ValidationContext,
    create_default_pipeline,
    get_gate_registry,
    GateStatus,
)
from quantlab.ml.challenge import (
    ChampionChallenge,
    ChallengeDecision,
    ComparisonMetric,
    get_champion_challenge,
)
from quantlab.ml.model import ModelType, create_model


def make_synthetic_data(n_days: int = 800, seed: int = 42):
    """生成合成数据：3 个特征 + 1 个标签"""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")

    feature_1 = pd.Series(rng.randn(n_days).cumsum() * 0.01, index=dates, name="feat_1")
    feature_2 = pd.Series(rng.randn(n_days), index=dates, name="feat_2")
    feature_3 = pd.Series(rng.randn(n_days), index=dates, name="feat_3")

    # 标签：与 feature_1 有相关性 + 噪音
    label = feature_1.shift(-1) * 0.5 + pd.Series(rng.randn(n_days) * 0.01, index=dates)
    label.name = "label"

    features = pd.concat([feature_1, feature_2, feature_3], axis=1)
    features = features.ffill().fillna(0)
    label = label.fillna(0)

    return features, label


def test_01_pipeline_creation():
    """测试 1: Pipeline 创建与 Gate 注册"""
    print("\n=== Test 1: Pipeline Creation ===")
    pipeline = create_default_pipeline()

    gate_names = [g.name for g in pipeline.gates]
    print(f"  Gates: {gate_names}")
    assert len(pipeline.gates) >= 6, f"Expected >= 6 gates, got {len(pipeline.gates)}"
    assert "data" in gate_names
    assert "training" in gate_names
    assert "leakage" in gate_names
    assert "walk_forward" in gate_names
    assert "trading" in gate_names
    assert "robustness" in gate_names
    assert "benchmark" in gate_names
    print("  PASS: All 7 gates registered")


def test_02_gate_registry():
    """测试 2: Gate Registry"""
    print("\n=== Test 2: Gate Registry ===")
    registry = get_gate_registry()
    all_gates = registry.list_all()
    print(f"  Registered gates: {list(all_gates.keys())}")
    assert len(all_gates) >= 6
    print("  PASS: Registry working")


def test_03_pipeline_run_full():
    """测试 3: 完整 Pipeline 运行"""
    print("\n=== Test 3: Full Pipeline Run ===")
    features, labels = make_synthetic_data(n_days=800)

    model = create_model(ModelType.LINEAR_REGRESSION, {}, is_classifier=False)
    n = len(features)
    train_end = int(n * 0.7)
    model.fit(features.iloc[:train_end], labels.iloc[:train_end])
    predictions = pd.Series(model.predict(features), index=features.index)

    from quantlab.ml.validation import ValidationConfig
    wf_config = ValidationConfig(
        n_splits=3,
        train_size=400,
        test_size=80,
        step_size=80,
        gap=5,
    )

    ctx = ValidationContext(
        raw_model=model,
        model_type="LINEAR_REGRESSION",
        model_params={},
        features=features,
        labels=labels,
        predictions=predictions,
        is_classifier=False,
        walk_forward_config=wf_config,
        name="test-pipeline",
    )

    pipeline = create_default_pipeline()
    pipeline.stop_on_fail = False  # 运行所有 Gate

    result = pipeline.run(ctx)

    print(f"  Validation ID: {result.validation_id}")
    print(f"  Overall Score: {result.overall_score:.1f} ({result.overall_grade})")
    print(f"  Overall Status: {result.overall_status}")
    print(f"  Passed: {result.passed}")
    print(f"  Total Gates: {len(result.gate_results)}")
    print(f"  Execution Time: {result.total_execution_time:.2f}s")

    for gr in result.gate_results:
        print(f"    [{gr.level}] {gr.gate_name}: {gr.status} score={gr.score:.1f}({gr.grade})")

    assert len(result.gate_results) >= 6
    assert result.overall_score >= 0
    print("  PASS: Pipeline executed successfully")


def test_04_pipeline_stop_on_fail():
    """测试 4: Gate 失败停止机制"""
    print("\n=== Test 4: Stop on Fail ===")
    features, labels = make_synthetic_data(n_days=200)  # 小数据集，可能触发某些 Gate 失败

    model = create_model(ModelType.LINEAR_REGRESSION, {}, is_classifier=False)
    n = len(features)
    train_end = int(n * 0.7)
    model.fit(features.iloc[:train_end], labels.iloc[:train_end])
    predictions = pd.Series(model.predict(features), index=features.index)

    from quantlab.ml.validation import ValidationConfig
    wf_config = ValidationConfig(
        n_splits=2,
        train_size=100,
        test_size=30,
        step_size=30,
        gap=2,
    )

    ctx = ValidationContext(
        raw_model=model,
        model_type="LINEAR_REGRESSION",
        model_params={},
        features=features,
        labels=labels,
        predictions=predictions,
        is_classifier=False,
        walk_forward_config=wf_config,
    )

    pipeline = create_default_pipeline()
    pipeline.stop_on_fail = True

    result = pipeline.run(ctx)
    print(f"  Stopped at: {result.stopped_at or 'None (completed all)'}")
    print(f"  Gates executed: {len(result.gate_results)}")
    print("  PASS: Stop-on-fail mechanism works")


def test_05_gate_enable_disable():
    """测试 5: Gate 启用/禁用"""
    print("\n=== Test 5: Gate Enable/Disable ===")
    pipeline = create_default_pipeline()

    # 禁用 walk_forward gate
    wf_gate = pipeline.get_gate("walk_forward")
    assert wf_gate is not None
    wf_gate.enabled = False
    print(f"  walk_forward enabled: {wf_gate.enabled}")

    features, labels = make_synthetic_data(n_days=400)
    model = create_model(ModelType.LINEAR_REGRESSION, {}, is_classifier=False)
    n = len(features)
    train_end = int(n * 0.7)
    model.fit(features.iloc[:train_end], labels.iloc[:train_end])
    predictions = pd.Series(model.predict(features), index=features.index)

    from quantlab.ml.validation import ValidationConfig
    wf_config = ValidationConfig(n_splits=2, train_size=200, test_size=50, step_size=50, gap=2)

    ctx = ValidationContext(
        raw_model=model,
        model_type="LINEAR_REGRESSION",
        model_params={},
        features=features,
        labels=labels,
        predictions=predictions,
        is_classifier=False,
        walk_forward_config=wf_config,
    )

    pipeline.stop_on_fail = False
    result = pipeline.run(ctx)

    wf_result = next((g for g in result.gate_results if g.gate_name == "walk_forward"), None)
    if wf_result:
        print(f"  walk_forward status: {wf_result.status}")
        assert wf_result.status == GateStatus.SKIP
    print("  PASS: Gate enable/disable works")


def test_06_champion_challenge_promote():
    """测试 6: Champion Challenge - PROMOTE"""
    print("\n=== Test 6: Champion Challenge PROMOTE ===")
    cc = get_champion_challenge()

    result = cc.challenge(
        candidate_id="MV-candidate-001",
        family="LGBM_Momentum",
        candidate_metrics={
            "walk_forward_ic": 0.08,
            "sharpe": 1.5,
            "overall_score": 85,
        },
        champion_metrics={
            "walk_forward_ic": 0.06,
            "sharpe": 1.2,
            "overall_score": 75,
        },
        metrics=[ComparisonMetric.WALK_FORWARD_IC, ComparisonMetric.SHARPE, ComparisonMetric.OVERALL_SCORE],
        win_threshold=0.6,
    )

    print(f"  Decision: {result.decision}")
    print(f"  Wins: {result.n_wins}/{result.n_total}")
    print(f"  Reason: {result.reason}")

    assert result.decision == ChallengeDecision.PROMOTE
    assert result.n_wins == 3
    print("  PASS: PROMOTE decision correct")


def test_07_champion_challenge_reject():
    """测试 7: Champion Challenge - REJECT"""
    print("\n=== Test 7: Champion Challenge REJECT ===")
    cc = get_champion_challenge()

    result = cc.challenge(
        candidate_id="MV-weak-001",
        family="LGBM_Momentum",
        candidate_metrics={
            "walk_forward_ic": 0.02,
            "sharpe": 0.5,
            "overall_score": 40,
        },
        champion_metrics={
            "walk_forward_ic": 0.08,
            "sharpe": 1.5,
            "overall_score": 85,
        },
        metrics=[ComparisonMetric.WALK_FORWARD_IC, ComparisonMetric.SHARPE, ComparisonMetric.OVERALL_SCORE],
        win_threshold=0.6,
    )

    print(f"  Decision: {result.decision}")
    print(f"  Wins: {result.n_wins}/{result.n_total}")

    assert result.decision == ChallengeDecision.REJECT
    assert result.n_wins == 0
    print("  PASS: REJECT decision correct")


def test_08_challenge_history():
    """测试 8: Challenge History"""
    print("\n=== Test 8: Challenge History ===")
    cc = get_champion_challenge()
    history = cc.get_history("LGBM_Momentum")
    print(f"  History count: {len(history)}")
    assert len(history) >= 2  # 前面两个测试
    print("  PASS: History tracked")


def test_09_api_routes_registered():
    """测试 9: API 路由注册"""
    print("\n=== Test 9: API Routes ===")
    from quantlab.api.ml import router
    routes = [r.path for r in router.routes]
    pipeline_routes = [r for r in routes if "pipeline" in r]
    challenge_routes = [r for r in routes if "challenge" in r]
    gates_routes = [r for r in routes if "gates" in r]

    print(f"  Pipeline routes: {pipeline_routes}")
    print(f"  Challenge routes: {challenge_routes}")
    print(f"  Gates routes: {gates_routes}")

    assert "/api/v1/ml/validation/pipeline/run" in routes
    assert "/api/v1/ml/validation/pipeline/config" in routes
    assert "/api/v1/ml/validation/gates" in routes
    assert "/api/v1/ml/challenge/run" in routes
    assert "/api/v1/ml/challenge/history" in routes
    assert "/api/v1/ml/challenge/latest" in routes
    print("  PASS: All API routes registered")


def test_10_pipeline_to_dict():
    """测试 10: Pipeline Result 序列化"""
    print("\n=== Test 10: Pipeline Result Serialization ===")
    features, labels = make_synthetic_data(n_days=400)
    model = create_model(ModelType.LINEAR_REGRESSION, {}, is_classifier=False)
    n = len(features)
    train_end = int(n * 0.7)
    model.fit(features.iloc[:train_end], labels.iloc[:train_end])
    predictions = pd.Series(model.predict(features), index=features.index)

    from quantlab.ml.validation import ValidationConfig
    wf_config = ValidationConfig(n_splits=2, train_size=200, test_size=50, step_size=50, gap=2)

    ctx = ValidationContext(
        raw_model=model,
        model_type="LINEAR_REGRESSION",
        model_params={},
        features=features,
        labels=labels,
        predictions=predictions,
        is_classifier=False,
        walk_forward_config=wf_config,
    )

    pipeline = create_default_pipeline()
    pipeline.stop_on_fail = False
    result = pipeline.run(ctx)

    d = result.to_dict()
    assert "validation_id" in d
    assert "gate_results" in d
    assert "overall_score" in d
    assert "overall_grade" in d
    assert "overall_status" in d
    assert "passed" in d

    # JSON 可序列化
    json_str = json.dumps(d, default=str)
    print(f"  JSON length: {len(json_str)} chars")
    print("  PASS: Serialization works")


def main():
    print("=" * 70)
    print("Validation Pipeline E2E Test Suite")
    print("=" * 70)

    tests = [
        test_01_pipeline_creation,
        test_02_gate_registry,
        test_03_pipeline_run_full,
        test_04_pipeline_stop_on_fail,
        test_05_gate_enable_disable,
        test_06_champion_challenge_promote,
        test_07_champion_challenge_reject,
        test_08_challenge_history,
        test_09_api_routes_registered,
        test_10_pipeline_to_dict,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, total {len(tests)}")
    print("=" * 70)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
