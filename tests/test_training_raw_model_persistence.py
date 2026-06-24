"""
Phase 1 单元测试：Training Center 产出 Raw Model

验证内容：
  1. TrainingJob.run() 训练完成后，Raw Model 被持久化到 ModelStore
  2. Experiment.model_version_id 非空
  3. ModelStore.load() 能加载 Raw Model
  4. Raw Model 的 lifecycle == DRAFT
  5. Raw Model 的 family 命名规则 = {model_type}_{experiment_name}

测试策略：
  - 使用合成数据（内存中），不依赖数据库，不写入数据库
  - 使用临时目录作为 ModelStore 的 root_dir，避免污染正式存储
  - mock TrainingJob._build_training_dataset 返回合成 TrainingDataset
"""

import sys
import os
import tempfile
import shutil
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from quantlab.ml.training.job import TrainingJob, TrainingResult, TrainingStatus
from quantlab.ml.pipeline import TrainingDataset
from quantlab.ml.model import ModelType
from quantlab.ml.registry import LifecycleStatus
from quantlab.ml.registry.model_store import ModelStore, get_model_store
import quantlab.ml.registry.model_store as model_store_module


def make_synthetic_training_data(n_days: int = 500, seed: int = 42) -> TrainingDataset:
    """生成合成训练数据（不写入数据库）"""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")

    f1 = pd.Series(rng.randn(n_days).cumsum() * 0.01, index=dates, name="feat_1")
    f2 = pd.Series(rng.randn(n_days), index=dates, name="feat_2")
    f3 = pd.Series(rng.randn(n_days), index=dates, name="feat_3")

    # 标签：与 f1 有相关性 + 噪音
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


def test_01_raw_model_persisted():
    """测试 1: 训练完成后 Raw Model 被持久化"""
    print("\n=== Test 1: Raw Model Persisted ===")

    # 使用临时目录，避免污染正式存储
    tmp_dir = tempfile.mkdtemp(prefix="quantlab_test_models_")
    original_store = model_store_module._model_store
    model_store_module._model_store = ModelStore(tmp_dir)

    try:
        # 构造合成数据
        tds = make_synthetic_training_data(n_days=500)

        # 创建 TrainingJob
        job = TrainingJob(
            dataset_id="test_synthetic",
            feature_set_id="test_fs",
            label_set_id="test_ls",
            model_type=ModelType.LINEAR_REGRESSION,
            model_params={},
            name="test_raw_model",
            save_experiment=True,
        )

        # mock _build_training_dataset，返回合成数据（不查数据库）
        job._build_training_dataset = lambda: tds

        # 运行训练
        result = job.run()

        # 验证训练成功
        assert result.status == TrainingStatus.COMPLETED, \
            f"Training failed: {result.error}"
        print(f"  Training completed: {result.job_id}")
        print(f"  IC: {result.metrics.ic:.4f}")

        # 验证 model_version_id 非空
        assert result.model_version_id, "model_version_id should not be empty"
        print(f"  model_version_id: {result.model_version_id}")

        # 验证 Experiment.model_version_id 非空
        assert result.experiment_id, "experiment_id should not be empty"
        from quantlab.ml.experiment import get_experiment_tracker
        tracker = get_experiment_tracker()
        exp = tracker.get(result.experiment_id)
        assert exp is not None, "Experiment not found"
        assert exp.model_version_id == result.model_version_id, \
            f"Experiment.model_version_id mismatch: {exp.model_version_id} vs {result.model_version_id}"
        print(f"  Experiment.model_version_id: {exp.model_version_id}")

        # 验证 ModelStore 中存在该 version
        store = get_model_store()
        assert store.exists(result.model_version_id), \
            f"Raw Model not found in ModelStore: {result.model_version_id}"
        print(f"  Raw Model exists in ModelStore: True")

        # 验证能加载 Raw Model
        version, model = store.load(result.model_version_id)
        assert version is not None, "Failed to load ModelVersion"
        assert model is not None, "Failed to load model object"
        print(f"  Raw Model loaded: {version.name}")

        # 验证 lifecycle == DRAFT
        assert version.lifecycle == LifecycleStatus.DRAFT, \
            f"Expected DRAFT, got {version.lifecycle}"
        print(f"  lifecycle: {version.lifecycle.value}")

        # 验证 family 命名规则
        expected_family = f"LINEAR_REGRESSION_test_raw_model"
        assert version.family == expected_family, \
            f"Expected family={expected_family}, got {version.family}"
        print(f"  family: {version.family}")

        # 验证 model.pkl 文件存在
        model_path = store._model_path(version.family, version.version_number)
        assert os.path.exists(model_path), f"model.pkl not found: {model_path}"
        print(f"  model.pkl exists: {model_path}")

        # 验证 metadata.json 文件存在
        metadata_path = store._metadata_path(version.family, version.version_number)
        assert os.path.exists(metadata_path), f"metadata.json not found: {metadata_path}"
        print(f"  metadata.json exists: {metadata_path}")

        # 验证 to_dict 输出 model_version_id
        result_dict = result.to_dict()
        assert result_dict["model_version_id"] == result.model_version_id
        print(f"  to_dict().model_version_id: {result_dict['model_version_id']}")

        print("  PASS: Raw Model persisted correctly")
        return result

    finally:
        # 恢复原始 ModelStore 单例
        model_store_module._model_store = original_store
        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"  Cleaned up temp dir: {tmp_dir}")


def test_02_raw_model_version_increment():
    """测试 2: 同 family 下多次训练，版本号递增"""
    print("\n=== Test 2: Version Number Increment ===")

    tmp_dir = tempfile.mkdtemp(prefix="quantlab_test_models_")
    original_store = model_store_module._model_store
    model_store_module._model_store = ModelStore(tmp_dir)

    try:
        tds = make_synthetic_training_data(n_days=500)

        # 第一次训练
        job1 = TrainingJob(
            dataset_id="test_synthetic",
            feature_set_id="test_fs",
            label_set_id="test_ls",
            model_type=ModelType.LINEAR_REGRESSION,
            model_params={},
            name="increment_test",
            save_experiment=False,  # 不保存 Experiment，只测 ModelStore
        )
        job1._build_training_dataset = lambda: tds
        result1 = job1.run()
        assert result1.status == TrainingStatus.COMPLETED
        print(f"  First training: model_version_id={result1.model_version_id}")

        # 第二次训练（同 family）
        job2 = TrainingJob(
            dataset_id="test_synthetic",
            feature_set_id="test_fs",
            label_set_id="test_ls",
            model_type=ModelType.LINEAR_REGRESSION,
            model_params={},
            name="increment_test",
            save_experiment=False,
        )
        job2._build_training_dataset = lambda: tds
        result2 = job2.run()
        assert result2.status == TrainingStatus.COMPLETED
        print(f"  Second training: model_version_id={result2.model_version_id}")

        # 验证版本号递增
        store = get_model_store()
        v1, _ = store.load(result1.model_version_id)
        v2, _ = store.load(result2.model_version_id)
        assert v2.version_number == v1.version_number + 1, \
            f"Expected version_number {v1.version_number + 1}, got {v2.version_number}"
        print(f"  Version numbers: v{v1.version_number} → v{v2.version_number}")

        # 验证 version_id 不同
        assert result1.model_version_id != result2.model_version_id
        print(f"  version_ids are different: True")

        print("  PASS: Version number increments correctly")

    finally:
        model_store_module._model_store = original_store
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_03_training_failure_no_raw_model():
    """测试 3: 训练失败时不持久化 Raw Model"""
    print("\n=== Test 3: Training Failure ===")

    tmp_dir = tempfile.mkdtemp(prefix="quantlab_test_models_")
    original_store = model_store_module._model_store
    model_store_module._model_store = ModelStore(tmp_dir)

    try:
        # 构造空数据集，触发训练失败
        empty_tds = TrainingDataset(
            X=pd.DataFrame(),
            y=pd.Series(),
            metadata={},
        )

        job = TrainingJob(
            dataset_id="test_synthetic",
            feature_set_id="test_fs",
            label_set_id="test_ls",
            model_type=ModelType.LINEAR_REGRESSION,
            model_params={},
            name="fail_test",
            save_experiment=True,
        )
        job._build_training_dataset = lambda: empty_tds
        result = job.run()

        # 验证训练失败
        assert result.status == TrainingStatus.FAILED, \
            f"Expected FAILED, got {result.status}"
        print(f"  Training failed as expected: {result.error}")

        # 验证 model_version_id 为空
        assert not result.model_version_id, \
            "model_version_id should be empty on failure"
        print(f"  model_version_id is empty: True")

        print("  PASS: No Raw Model on failure")

    finally:
        model_store_module._model_store = original_store
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_01_raw_model_persisted()
    test_02_raw_model_version_increment()
    test_03_training_failure_no_raw_model()
    print("\n=== All Phase 1 tests passed ===")
