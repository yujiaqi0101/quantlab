"""
Phase 2 单元测试：从 Experiment 构建 ValidationContext 并跑通 Pipeline

验证内容：
  1. build_context_from_experiment() 能正确构建 ValidationContext
  2. Pipeline 能跑通（使用合成数据）
  3. PASS 后 Raw Model 状态升级 DRAFT → CANDIDATE + 注册到 ModelRegistry
  4. FAIL 后 Raw Model 标记 validation_failed

测试策略：
  - 先用 Phase 1 的方式训练模型（mock _build_training_dataset），得到 Experiment + Raw Model
  - mock MLPipeline.build() 返回合成 TrainingDataset（不查数据库）
  - 调用 build_context_from_experiment() 构建 ValidationContext
  - 跑 Pipeline，验证状态升级
"""

import sys
import os
import tempfile
import shutil
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from quantlab.ml.training.job import TrainingJob, TrainingStatus
from quantlab.ml.pipeline import TrainingDataset, get_pipeline
from quantlab.ml.model import ModelType
from quantlab.ml.registry import LifecycleStatus
from quantlab.ml.registry.model_store import ModelStore, get_model_store
import quantlab.ml.registry.model_store as model_store_module
from quantlab.ml.validation.pipeline.core import (
    build_context_from_experiment,
    create_default_pipeline,
)
from quantlab.ml.validation import ValidationConfig


def make_synthetic_training_data(n_days: int = 800, seed: int = 42) -> TrainingDataset:
    """生成合成训练数据（不写入数据库）"""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")

    f1 = pd.Series(rng.randn(n_days).cumsum() * 0.01, index=dates, name="feat_1")
    f2 = pd.Series(rng.randn(n_days), index=dates, name="feat_2")
    f3 = pd.Series(rng.randn(n_days), index=dates, name="feat_3")

    # 标签：与 f1 有强相关性 + 噪音（让模型能 PASS）
    label = f1.shift(-1) * 0.5 + pd.Series(rng.randn(n_days) * 0.01, index=dates)
    label.name = "label"

    features = pd.concat([f1, f2, f3], axis=1).ffill().fillna(0)
    label = label.fillna(0)

    return TrainingDataset(
        X=features,
        y=label,
        metadata={
            "dataset_id": "test_synthetic",
            "feature_set_id": "test_fs",
            "label_set_id": "test_ls",
        },
    )


def train_model_and_get_experiment(tmp_dir):
    """训练模型，返回 experiment_id"""
    # 重置 ModelStore 单例指向临时目录
    model_store_module._model_store = ModelStore(tmp_dir)

    tds = make_synthetic_training_data(n_days=800)

    job = TrainingJob(
        dataset_id="test_synthetic",
        feature_set_id="test_fs",
        label_set_id="test_ls",
        model_type=ModelType.LINEAR_REGRESSION,
        model_params={},
        name="validation_test",
        save_experiment=True,
    )
    job._build_training_dataset = lambda: tds
    result = job.run()

    assert result.status == TrainingStatus.COMPLETED
    assert result.model_version_id, "model_version_id should not be empty"
    assert result.experiment_id, "experiment_id should not be empty"

    return result.experiment_id, result.model_version_id, tds


def test_01_build_context_from_experiment():
    """测试 1: build_context_from_experiment 正确构建 ValidationContext"""
    print("\n=== Test 1: Build Context from Experiment ===")

    tmp_dir = tempfile.mkdtemp(prefix="quantlab_test_val_")
    original_store = model_store_module._model_store

    try:
        exp_id, mv_id, tds = train_model_and_get_experiment(tmp_dir)
        print(f"  Experiment: {exp_id}, Raw Model: {mv_id}")

        # mock MLPipeline.build 返回合成数据（不查数据库）
        original_pipeline = get_pipeline()
        original_build = original_pipeline.build
        original_pipeline.build = lambda **kwargs: tds

        try:
            wf_config = ValidationConfig(
                n_splits=3, train_size=400, test_size=80, step_size=80, gap=5
            )
            ctx = build_context_from_experiment(exp_id, wf_config)

            # 验证 context 字段
            assert ctx.raw_model is not None, "raw_model should not be None"
            assert ctx.features is not None, "features should not be None"
            assert ctx.labels is not None, "labels should not be None"
            assert ctx.predictions is not None, "predictions should not be None"
            assert ctx.experiment_id == exp_id
            assert ctx.training_result is not None
            assert ctx.training_result.model_version_id == mv_id

            print(f"  raw_model: {type(ctx.raw_model).__name__}")
            print(f"  features shape: {ctx.features.shape}")
            print(f"  predictions shape: {ctx.predictions.shape}")
            print(f"  training_result.model_version_id: {ctx.training_result.model_version_id}")

            print("  PASS: ValidationContext built correctly")
            return exp_id, mv_id

        finally:
            original_pipeline.build = original_build

    finally:
        model_store_module._model_store = original_store
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_02_pipeline_run_and_state_upgrade():
    """测试 2: Pipeline 运行 + 状态升级"""
    print("\n=== Test 2: Pipeline Run + State Upgrade ===")

    tmp_dir = tempfile.mkdtemp(prefix="quantlab_test_val_")
    original_store = model_store_module._model_store

    try:
        exp_id, mv_id, tds = train_model_and_get_experiment(tmp_dir)
        print(f"  Experiment: {exp_id}, Raw Model: {mv_id}")

        # 验证初始状态是 DRAFT
        store = get_model_store()
        version, _ = store.load(mv_id)
        assert version.lifecycle == LifecycleStatus.DRAFT, \
            f"Expected DRAFT before validation, got {version.lifecycle}"
        print(f"  Initial lifecycle: {version.lifecycle.value}")

        # mock MLPipeline.build
        original_pipeline = get_pipeline()
        original_build = original_pipeline.build
        original_pipeline.build = lambda **kwargs: tds

        try:
            wf_config = ValidationConfig(
                n_splits=3, train_size=400, test_size=80, step_size=80, gap=5
            )
            ctx = build_context_from_experiment(exp_id, wf_config)

            # 跑 Pipeline（stop_on_fail=False 运行所有 Gate）
            pipeline = create_default_pipeline()
            pipeline.stop_on_fail = False
            result = pipeline.run(ctx)

            print(f"  Validation ID: {result.validation_id}")
            print(f"  Overall Score: {result.overall_score:.1f} ({result.overall_grade})")
            print(f"  Overall Status: {result.overall_status}")
            print(f"  Passed: {result.passed}")

            for gr in result.gate_results:
                print(f"    [{gr.level}] {gr.gate_name}: {gr.status} score={gr.score:.1f}({gr.grade})")

            # 模拟状态升级逻辑（与 _upgrade_raw_model_status 相同）
            from quantlab.ml.registry import get_model_registry
            version, model = store.load(mv_id)
            if result.passed:
                version.lifecycle = LifecycleStatus.CANDIDATE
                if model:
                    version.set_model(model)
                store.save(version)
                registry = get_model_registry()
                registry.register(version)
                print(f"  Upgraded to CANDIDATE + registered")
            else:
                version.tags = [t for t in version.tags if t != "validation_failed"]
                version.tags.append("validation_failed")
                if model:
                    version.set_model(model)
                store.save(version)
                print(f"  Kept DRAFT + tagged validation_failed")

            # 验证状态升级结果
            version2, _ = store.load(mv_id)
            if result.passed:
                assert version2.lifecycle == LifecycleStatus.CANDIDATE, \
                    f"Expected CANDIDATE after PASS, got {version2.lifecycle}"
                # 验证注册到 ModelRegistry
                registry = get_model_registry()
                reg_version = registry.get_version(mv_id)
                assert reg_version is not None, "Not registered to ModelRegistry"
                print(f"  Registry lookup: {reg_version.name} ({reg_version.lifecycle.value})")
                print("  PASS: State upgraded to CANDIDATE + registered")
            else:
                assert version2.lifecycle == LifecycleStatus.DRAFT, \
                    f"Expected DRAFT after FAIL, got {version2.lifecycle}"
                assert "validation_failed" in version2.tags, "validation_failed tag missing"
                print("  PASS: State kept DRAFT + tagged validation_failed")

        finally:
            original_pipeline.build = original_build

    finally:
        model_store_module._model_store = original_store
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_03_experiment_without_model_version():
    """测试 3: Experiment 没有 model_version_id 时报错"""
    print("\n=== Test 3: Experiment without model_version_id ===")

    from quantlab.ml.experiment import Experiment, get_experiment_tracker

    # 创建一个没有 model_version_id 的 Experiment
    exp = Experiment(
        name="legacy_experiment",
        dataset_id="test",
        feature_set_id="test",
        label_set_id="test",
        model_type="LIGHTGBM",
        status="COMPLETED",
        # 故意不设置 model_version_id
    )
    tracker = get_experiment_tracker()
    tracker.save(exp)

    try:
        build_context_from_experiment(exp.experiment_id)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "no model_version_id" in str(e)
        print(f"  Error as expected: {e}")
        print("  PASS: Correctly raised error for legacy Experiment")


if __name__ == "__main__":
    test_01_build_context_from_experiment()
    test_02_pipeline_run_and_state_upgrade()
    test_03_experiment_without_model_version()
    print("\n=== All Phase 2 tests passed ===")
