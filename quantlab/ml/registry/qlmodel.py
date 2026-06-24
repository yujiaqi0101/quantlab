"""
.qlmodel 导入/导出（M6）

  QuantLab Model Package = zip 包

  LGBM_Momentum_v3.qlmodel
  ├── manifest.yaml
  ├── model.pkl
  ├── metrics.json
  ├── validation.json
  ├── training.yaml
  ├── lineage.json
  ├── snapshot/
  │   ├── feature_set.yaml
  │   └── label_set.yaml
  └── artifacts/

  优势：
    ✅ 可以导入/导出
    ✅ 可以版本管理
    ✅ 可以备份
    ✅ 可以分享
    ✅ 可以回滚
    ✅ 可以直接部署到 Runtime
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from typing import Optional

from .package import ModelPackage, QLMODEL_EXTENSION
from .model_store import ModelStore

logger = logging.getLogger("quantlab.ml.registry.qlmodel")


def export_package(
    pkg: ModelPackage,
    output_path: str,
    include_model: bool = True,
) -> str:
    """
    导出 ModelPackage 为 .qlmodel 文件

    Args:
        pkg: ModelPackage 对象
        output_path: 输出路径（如 "LGBM_Momentum_v3.qlmodel"）
        include_model: 是否包含 model.pkl（大文件可排除）

    Returns:
        导出的文件路径
    """
    if not output_path.endswith(QLMODEL_EXTENSION):
        output_path += QLMODEL_EXTENSION

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 保存到临时目录
        pkg.save(tmp_dir)

        # 如果不包含 model，删除 model.pkl
        if not include_model:
            model_path = os.path.join(tmp_dir, "model.pkl")
            if os.path.exists(model_path):
                os.remove(model_path)

        # 打包为 zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmp_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    arcname = os.path.relpath(fp, tmp_dir)
                    zf.write(fp, arcname)

    logger.info(f"ModelPackage exported: {pkg.manifest.id} → {output_path}")
    return output_path


def export_from_store(
    store: ModelStore,
    version_id: str,
    output_path: str,
    include_model: bool = True,
) -> Optional[str]:
    """
    从 ModelStore 导出指定版本为 .qlmodel

    Args:
        store: ModelStore
        version_id: 版本 ID
        output_path: 输出路径
        include_model: 是否包含 model.pkl

    Returns:
        导出的文件路径，或 None（如果版本不存在）
    """
    pkg = store.load_package(version_id, load_model=include_model)
    if pkg is None:
        logger.warning(f"Version not found: {version_id}")
        return None
    return export_package(pkg, output_path, include_model=include_model)


def import_package(
    qlmodel_path: str,
    store: ModelStore,
    family: str = "",
    version_number: Optional[int] = None,
) -> Optional[ModelPackage]:
    """
    导入 .qlmodel 文件到 ModelStore

    Args:
        qlmodel_path: .qlmodel 文件路径
        store: ModelStore
        family: 目标族名（空则使用 manifest 中的）
        version_number: 目标版本号（空则使用 manifest 中的）

    Returns:
        导入的 ModelPackage，或 None（如果失败）
    """
    if not os.path.exists(qlmodel_path):
        logger.error(f"File not found: {qlmodel_path}")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 解压
        with zipfile.ZipFile(qlmodel_path, "r") as zf:
            zf.extractall(tmp_dir)

        # 加载
        pkg = ModelPackage.load(tmp_dir, load_model=True)

        # 覆盖 family / version_number
        if family:
            pkg.manifest.family = family
            pkg.manifest.id = f"{family}_v{pkg.manifest.version}"
        if version_number is not None:
            pkg.manifest.version = version_number
            pkg.manifest.id = f"{pkg.manifest.family}_v{version_number}"

        # 生成新的 version_id
        import uuid
        pkg.version_id = f"MV-{uuid.uuid4().hex[:8]}"

        # 保存到 store
        store.save_package(pkg)
        logger.info(f"ModelPackage imported: {pkg.manifest.id} → store")
        return pkg


def import_to_registry(
    qlmodel_path: str,
    store: ModelStore,
    registry=None,
    family: str = "",
    version_number: Optional[int] = None,
) -> Optional[ModelPackage]:
    """
    导入 .qlmodel 并注册到 Registry

    Args:
        qlmodel_path: .qlmodel 文件路径
        store: ModelStore
        registry: ModelRegistry（空则使用默认）
        family: 目标族名
        version_number: 目标版本号

    Returns:
        导入的 ModelPackage
    """
    pkg = import_package(qlmodel_path, store, family, version_number)
    if pkg is None:
        return None

    if registry is None:
        from .registry import get_model_registry
        registry = get_model_registry()

    # 注册到 Registry
    from .registry import ModelVersion, LifecycleStatus
    from ..model import ModelType

    try:
        model_type = ModelType(pkg.manifest.model_type)
    except ValueError:
        model_type = ModelType.LIGHTGBM

    version = ModelVersion(
        version_id=pkg.version_id,
        name=pkg.manifest.id,
        model_type=model_type,
        params=pkg.manifest.params,
        metrics=pkg.metrics,
        dataset_id=pkg.manifest.dataset_id,
        feature_ids=(
            pkg.feature_set_snapshot.feature_ids
            if pkg.feature_set_snapshot else []
        ),
        label_id=(
            pkg.label_set_snapshot.label_id
            if pkg.label_set_snapshot else ""
        ),
        is_classifier=pkg.manifest.is_classifier,
        created_at=pkg.manifest.created_at,
        description=pkg.manifest.description,
        tags=pkg.manifest.tags,
        family=pkg.manifest.family,
        version_number=pkg.manifest.version,
        lifecycle=LifecycleStatus.TRAINING,
    )
    if pkg.model is not None:
        version.set_model(pkg.model)

    registry.register(version)
    logger.info(f"ModelPackage imported + registered: {pkg.manifest.id}")
    return pkg
