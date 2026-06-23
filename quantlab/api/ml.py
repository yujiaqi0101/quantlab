"""
ML Lab API — 机器学习实验室后端

ML Lab 完整闭环：
  DataHub → Feature Engineering → Label Engineering → Model Training
  → Walk Forward → Backtest → Deploy

端点：
  Dataset Center
    GET  /api/v1/ml/datasets                 数据集列表
    POST /api/v1/ml/datasets                 创建数据集
    GET  /api/v1/ml/datasets/{id}            数据集详情
    GET  /api/v1/ml/datasets/{id}/stats      数据集统计
    POST /api/v1/ml/datasets/{id}/load_csv   从 CSV 加载

  Feature Lab
    GET  /api/v1/ml/features                 特征列表
    GET  /api/v1/ml/features/{id}/compute    计算特征

  Label Lab
    GET  /api/v1/ml/labels                   标签列表
    GET  /api/v1/ml/labels/{id}/generate     生成标签

  Feature Analysis
    POST /api/v1/ml/feature-analysis         特征分析

  Model Lab
    GET  /api/v1/ml/models                   支持的模型列表

  Training Center
    POST /api/v1/ml/training/jobs            提交训练任务
    GET  /api/v1/ml/training/jobs            训练任务列表
    GET  /api/v1/ml/training/jobs/{id}       训练任务详情

  Validation Center
    POST /api/v1/ml/validation/walk-forward  Walk Forward 验证

  Leakage Detector
    POST /api/v1/ml/leakage/check-data       数据泄漏检测
    POST /api/v1/ml/leakage/check-overlap    时间重叠检测

  Model Registry
    GET  /api/v1/ml/registry/versions        模型版本列表
    POST /api/v1/ml/registry/versions        注册模型版本
    GET  /api/v1/ml/registry/versions/{id}   模型版本详情

  ML Strategy Builder
    POST /api/v1/ml/strategies               构建 ML 策略
    POST /api/v1/ml/strategies/predict       策略预测
    POST /api/v1/ml/strategies/signal        策略信号
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from quantlab.ml import (
    Dataset, DatasetManager, get_dataset_manager,
    FeatureRegistry, get_feature_registry,
    LabelRegistry, get_label_registry,
    FeatureAnalyzer,
    Model, ModelType,
    TrainingJob, TrainingManager, get_training_manager,
    WalkForward, ValidationConfig,
    LeakageDetector,
    ModelVersion, ModelRegistry, get_model_registry,
    MLStrategy, MLStrategyBuilder, MLStrategyConfig,
)
from quantlab.ml.model import create_model, list_supported_models

logger = logging.getLogger("quantlab.api.ml")

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


# ==================================================================
# Pydantic 模型
# ==================================================================

class CreateDatasetRequest(BaseModel):
    name: str
    symbols: List[str] = []
    frequency: str = "1d"
    description: str = ""
    tags: List[str] = []
    scope_type: str = "single"     # single / universe
    universe_id: str = ""          # scope_type=universe 时引用的股票池


class ComputeFeatureRequest(BaseModel):
    feature_ids: List[str]
    data: List[Dict[str, Any]] = []
    symbol_column: str = ""  # 多标的数据集时指定 symbol 列名，为空则视为单标的


class GenerateLabelRequest(BaseModel):
    label_id: str
    data: List[Dict[str, Any]] = []
    symbol_column: str = ""  # 多标的数据集时指定 symbol 列名


class FeatureAnalysisRequest(BaseModel):
    feature_data: Dict[str, List[float]] = {}
    label_data: List[float] = []
    index: List[str] = []


class TrainRequest(BaseModel):
    dataset_id: str
    feature_ids: List[str]
    label_id: str
    model_type: str = "LINEAR_REGRESSION"
    model_params: Dict[str, Any] = {}
    is_classifier: bool = False
    train_ratio: float = 0.7
    val_ratio: float = 0.15


class WalkForwardRequest(BaseModel):
    feature_data: Dict[str, List[float]] = {}
    label_data: List[float] = []
    index: List[str] = []
    model_type: str = "LINEAR_REGRESSION"
    model_params: Dict[str, Any] = {}
    is_classifier: bool = False
    n_splits: int = 5
    train_size: int = 252
    test_size: int = 63
    step_size: int = 63
    gap: int = 0


class LeakageCheckDataRequest(BaseModel):
    feature_data: Dict[str, List[float]] = {}
    label_data: List[float] = []
    index: List[str] = []


class LeakageCheckOverlapRequest(BaseModel):
    train_index: List[str] = []
    test_index: List[str] = []


class RegisterVersionRequest(BaseModel):
    name: str
    model_type: str = "LIGHTGBM"
    params: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    dataset_id: str = ""
    feature_ids: List[str] = []
    label_id: str = ""
    is_classifier: bool = False
    description: str = ""
    tags: List[str] = []


class BuildStrategyRequest(BaseModel):
    feature_ids: List[str]
    label_id: str
    model_type: str = "LINEAR_REGRESSION"
    model_params: Dict[str, Any] = {}
    is_classifier: bool = False
    long_threshold: float = 0.0
    short_threshold: float = 0.0
    use_short: bool = False
    position_scale: float = 1.0
    name: str = ""
    train_data: List[Dict[str, Any]] = []


class StrategyPredictRequest(BaseModel):
    strategy_id: str
    data: List[Dict[str, Any]] = []


# 全局策略存储（内存）
_strategies: Dict[str, MLStrategy] = {}


# ==================================================================
# Dataset Center
# ==================================================================

@router.get("/datasets")
async def list_datasets():
    """数据集列表"""
    mgr = get_dataset_manager()
    return {"datasets": [ds.to_dict() for ds in mgr._datasets.values()]}


@router.post("/datasets")
async def create_dataset(req: CreateDatasetRequest):
    """创建数据集"""
    mgr = get_dataset_manager()
    ds = mgr.create_dataset(
        name=req.name,
        symbols=req.symbols,
        frequency=req.frequency,
        description=req.description,
        tags=req.tags,
        scope_type=req.scope_type,
        universe_id=req.universe_id,
    )
    return ds.to_dict()


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """数据集详情"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    return ds.to_dict()


@router.get("/datasets/{dataset_id}/stats")
async def get_dataset_stats(dataset_id: str):
    """数据集统计"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    return ds.get_stats().to_dict()


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """删除数据集（含元信息和 Parquet 数据）"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    success = mgr.remove_dataset(dataset_id)
    if not success:
        raise HTTPException(400, f"Failed to delete dataset: {dataset_id}")
    return {"status": "ok", "dataset_id": dataset_id}


@router.post("/datasets/{dataset_id}/load_csv")
async def load_csv(dataset_id: str, file: UploadFile = File(...)):
    """从 CSV 加载数据"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        success = mgr.load_csv(dataset_id, tmp_path)
        if not success:
            raise HTTPException(400, "Failed to load CSV")
        return {"status": "ok", "dataset_id": dataset_id}
    finally:
        os.unlink(tmp_path)


# ==================================================================
# Feature Lab
# ==================================================================

@router.get("/features")
async def list_features(category: str = ""):
    """特征列表"""
    reg = get_feature_registry()
    return reg.to_dict()


@router.post("/features/compute")
async def compute_features(req: ComputeFeatureRequest):
    """计算特征（支持多标的按 symbol 分组计算）"""
    reg = get_feature_registry()
    df = pd.DataFrame(req.data)
    if df.empty or not req.feature_ids:
        return {"features": {}, "index": []}

    # 多标的数据集：按 symbol_column 分组计算，避免不同标的的价格序列串在一起
    if req.symbol_column and req.symbol_column in df.columns:
        parts = []
        for _sym, group_df in df.groupby(req.symbol_column):
            group_result = reg.compute_many(req.feature_ids, group_df)
            # 把 symbol 列加回去
            group_result[req.symbol_column] = _sym
            parts.append(group_result)
        if not parts:
            return {"features": {}, "index": []}
        result = pd.concat(parts)
        result = result.sort_index()
        return {
            "features": result.to_dict(orient="list"),
            "index": [str(i) for i in result.index],
        }

    # 单标的：直接计算
    result = reg.compute_many(req.feature_ids, df)
    return {
        "features": result.to_dict(orient="list"),
        "index": [str(i) for i in result.index],
    }


# ==================================================================
# Label Lab
# ==================================================================

@router.get("/labels")
async def list_labels():
    """标签列表"""
    reg = get_label_registry()
    return reg.to_dict()


@router.post("/labels/generate")
async def generate_label(req: GenerateLabelRequest):
    """生成标签（支持多标的按 symbol 分组生成）"""
    reg = get_label_registry()
    df = pd.DataFrame(req.data)
    if df.empty:
        return {"label": [], "index": []}

    # 多标的数据集：按 symbol_column 分组生成
    if req.symbol_column and req.symbol_column in df.columns:
        parts = []
        for _sym, group_df in df.groupby(req.symbol_column):
            label = reg.generate(req.label_id, group_df)
            if label is not None:
                label_df = label.to_frame()
                label_df[req.symbol_column] = _sym
                parts.append(label_df)
        if not parts:
            raise HTTPException(404, f"Label not found: {req.label_id}")
        result = pd.concat(parts).sort_index()
        label_col = [c for c in result.columns if c != req.symbol_column][0]
        return {
            "label": result[label_col].tolist(),
            "index": [str(i) for i in result.index],
        }

    # 单标的
    label = reg.generate(req.label_id, df)
    if label is None:
        raise HTTPException(404, f"Label not found: {req.label_id}")
    return {
        "label": label.tolist(),
        "index": [str(i) for i in label.index],
    }


# ==================================================================
# Feature Analysis
# ==================================================================

@router.post("/feature-analysis")
async def feature_analysis(req: FeatureAnalysisRequest):
    """特征分析"""
    if not req.feature_data or not req.label_data:
        raise HTTPException(400, "feature_data and label_data are required")

    index = pd.to_datetime(req.index) if req.index else None
    features = pd.DataFrame(req.feature_data, index=index)
    label = pd.Series(req.label_data, index=index, name="label")

    analyzer = FeatureAnalyzer()
    results = analyzer.analyze(features, label)
    return {
        "results": [r.to_dict() for r in results],
        "correlation_matrix": analyzer.correlation_matrix(features).to_dict(),
    }


@router.get("/feature-analysis/quick")
async def feature_analysis_quick(dataset_id: str = ""):
    """基于 dataset 快速计算特征分析（无需训练任务）"""
    ds_mgr = get_dataset_manager()
    datasets = ds_mgr.list_datasets()
    logger.info(f"feature-analysis/quick: found {len(datasets)} datasets")

    # 选择有数据的 dataset
    ds = None
    if dataset_id:
        ds = ds_mgr.get_dataset(dataset_id)
        logger.info(f"  requested dataset {dataset_id}: found={ds is not None}")
    if not ds or not ds._has_data_flag:
        # 用 _has_data_flag 筛选（不触发 Parquet 加载），优先选小数据集
        candidates = [d for d in datasets if d._has_data_flag]
        # 优先选非 HS300 的大数据集（示例数据集通常 2000 行）
        candidates.sort(key=lambda d: 0 if d.dataset_id != "DS-7e2f0c69" else 1)
        for d in candidates:
            logger.info(f"  checking dataset {d.dataset_id}: flag={d._has_data_flag}")
            ds = d
            break

    if not ds or ds.get_data() is None:
        return {"results": [], "correlation_matrix": {}, "source": "no_data"}

    df = ds.get_data()
    # 限制数据量，避免在大数据集上做全量计算导致事件循环阻塞
    MAX_ROWS_FOR_QUICK_ANALYSIS = 5000
    if len(df) > MAX_ROWS_FOR_QUICK_ANALYSIS:
        logger.info(
            f"feature-analysis/quick: sampling {MAX_ROWS_FOR_QUICK_ANALYSIS} rows "
            f"from {len(df)} (dataset {ds.dataset_id})"
        )
        df = df.tail(MAX_ROWS_FOR_QUICK_ANALYSIS).copy()
    from quantlab.ml.feature import get_feature_registry
    from quantlab.ml.label import get_label_registry
    feat_reg = get_feature_registry()
    label_reg = get_label_registry()

    # 计算所有可用特征
    feature_data = {}
    for fid, feat in feat_reg._features.items():
        try:
            vals = feat.compute(df)
            if vals is not None and len(vals) > 0:
                feature_data[fid] = vals.tolist()
        except Exception as e:
            logger.warning(f"Feature {fid} compute failed: {e}")

    # 计算第一个可用标签
    label_data = []
    label_name = ""
    for lid, lab in label_reg._labels.items():
        try:
            vals = lab.generate(df)
            if vals is not None and len(vals) > 0:
                label_data = vals.tolist()
                label_name = lid
                break
        except Exception as e:
            logger.warning(f"Label {lid} compute failed: {e}")

    if not feature_data or not label_data:
        return {"results": [], "correlation_matrix": {}, "source": "no_features"}

    # 对齐长度
    min_len = min(len(v) for v in feature_data.values())
    min_len = min(min_len, len(label_data))
    feature_data = {k: v[:min_len] for k, v in feature_data.items()}
    label_data = label_data[:min_len]

    features_df = pd.DataFrame(feature_data)
    label_s = pd.Series(label_data, name=label_name or "label")

    analyzer = FeatureAnalyzer()
    analysis_results = analyzer.analyze(features_df, label_s)
    return {
        "results": [r.to_dict() for r in analysis_results],
        "correlation_matrix": analyzer.correlation_matrix(features_df).to_dict(),
        "source": "quick_analysis",
        "dataset_id": ds.dataset_id,
        "label": label_name,
    }


@router.get("/feature-analysis/from-job/{job_id}")
async def feature_analysis_from_job(job_id: str):
    """基于已完成的训练任务自动计算特征分析"""
    mgr = get_training_manager()
    job = mgr.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    result = mgr.get_result(job_id)
    if not result or result.status != "COMPLETED":
        raise HTTPException(400, "Job not completed yet")

    # 从 dataset 加载数据
    ds_mgr = get_dataset_manager()
    ds = ds_mgr.get_dataset(job.dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset {job.dataset_id} not found")

    try:
        from quantlab.ml.storage import get_ml_store
        store = get_ml_store()
        df = store.load_dataset_data(job.dataset_id)
    except Exception:
        # 如果没有实际数据，用 feature importance 生成简化结果
        fi = result.feature_importance or {}
        total = sum(fi.values()) or 1
        results = []
        for fname, imp in fi.items():
            results.append({
                "feature_name": fname,
                "ic": 0.0,
                "rank_ic": 0.0,
                "mutual_info": round(imp / total, 4),
                "ic_std": 0.0,
                "ic_ir": 0.0,
                "n_samples": result.n_test_samples or 0,
                "importance": imp,
                "importance_pct": round(imp / total * 100, 2),
            })
        return {"results": results, "correlation_matrix": {}, "source": "feature_importance"}

    # 有实际数据时，计算完整分析
    # 限制数据量，避免在大数据集上做全量计算导致事件循环阻塞
    MAX_ROWS_FOR_JOB_ANALYSIS = 5000
    if df is not None and len(df) > MAX_ROWS_FOR_JOB_ANALYSIS:
        logger.info(
            f"feature-analysis/from-job: sampling {MAX_ROWS_FOR_JOB_ANALYSIS} rows "
            f"from {len(df)} (dataset {job.dataset_id})"
        )
        df = df.tail(MAX_ROWS_FOR_JOB_ANALYSIS).copy()
    from quantlab.ml.feature import get_feature_registry
    from quantlab.ml.label import get_label_registry
    feat_reg = get_feature_registry()
    label_reg = get_label_registry()

    feature_data = {}
    for fid in job.feature_ids:
        feat = feat_reg.get(fid)
        if feat:
            try:
                feature_data[fid] = feat.compute(df).tolist()
            except Exception:
                pass

    label_obj = label_reg.get(job.label_id)
    label_data = []
    if label_obj:
        try:
            label_data = label_obj.generate(df).tolist()
        except Exception:
            pass

    if not feature_data or not label_data:
        # fallback to feature importance
        fi = result.feature_importance or {}
        total = sum(fi.values()) or 1
        results = []
        for fname, imp in fi.items():
            results.append({
                "feature_name": fname,
                "ic": 0.0,
                "rank_ic": 0.0,
                "mutual_info": round(imp / total, 4),
                "ic_std": 0.0,
                "ic_ir": 0.0,
                "n_samples": result.n_test_samples or 0,
                "importance": imp,
                "importance_pct": round(imp / total * 100, 2),
            })
        return {"results": results, "correlation_matrix": {}, "source": "feature_importance"}

    min_len = min(len(v) for v in feature_data.values())
    min_len = min(min_len, len(label_data))
    feature_data = {k: v[:min_len] for k, v in feature_data.items()}
    label_data = label_data[:min_len]

    analyzer = FeatureAnalyzer()
    features_df = pd.DataFrame(feature_data)
    label_s = pd.Series(label_data, name="label")
    analysis_results = analyzer.analyze(features_df, label_s)
    return {
        "results": [r.to_dict() for r in analysis_results],
        "correlation_matrix": analyzer.correlation_matrix(features_df).to_dict(),
        "source": "full_analysis",
    }


@router.get("/feature-importance/from-job/{job_id}")
async def feature_importance_from_job(job_id: str):
    """基于已完成的训练任务获取特征重要性"""
    mgr = get_training_manager()
    job = mgr.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    result = mgr.get_result(job_id)
    if not result or result.status != "COMPLETED":
        raise HTTPException(400, "Job not completed yet")

    fi = result.feature_importance or {}
    if not fi:
        raise HTTPException(404, "No feature importance data in this job")

    total = sum(fi.values()) or 1
    details = []
    for rank, (fname, imp) in enumerate(sorted(fi.items(), key=lambda x: -x[1]), 1):
        details.append({
            "rank": rank,
            "feature": fname,
            "importance": imp,
            "normalized": round(imp / total, 6),
        })

    return {
        "gain": {
            "details": details,
            "model_type": job.model_type.value if hasattr(job.model_type, 'value') else str(job.model_type),
            "n_features": len(fi),
        }
    }


# ==================================================================
# Model Lab
# ==================================================================

@router.get("/models")
async def list_models():
    """支持的模型列表"""
    return {"models": list_supported_models()}


# ==================================================================
# Training Center
# ==================================================================

@router.post("/training/jobs")
async def submit_training(req: TrainRequest):
    """提交训练任务"""
    try:
        model_type = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    job = TrainingJob(
        dataset_id=req.dataset_id,
        feature_ids=req.feature_ids,
        label_id=req.label_id,
        model_type=model_type,
        model_params=req.model_params,
        is_classifier=req.is_classifier,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
    )
    mgr = get_training_manager()
    result = mgr.submit(job)
    return result.to_dict()


@router.get("/training/jobs")
async def list_training_jobs():
    """训练任务列表"""
    mgr = get_training_manager()
    return {"jobs": mgr.list_jobs(), "status": mgr.get_status()}


@router.get("/training/jobs/{job_id}")
async def get_training_job(job_id: str):
    """训练任务详情"""
    mgr = get_training_manager()
    job = mgr.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    result = mgr.get_result(job_id)
    return {
        "job": job.to_dict(),
        "result": result.to_dict() if result else None,
    }


# ==================================================================
# M2 第八部分：Training Queue（异步训练）
# ==================================================================

from quantlab.ml.training import get_training_queue, TrainingStatus


@router.post("/training/queue/submit")
async def queue_submit_training(req: TrainRequest):
    """
    异步提交训练任务到队列（立即返回 job_id）

    状态：Pending → Running → Completed / Failed
    """
    try:
        try:
            model_type = ModelType(req.model_type)
        except ValueError:
            raise HTTPException(400, f"Unknown model type: {req.model_type}")

        job = TrainingJob(
            dataset_id=req.dataset_id,
            feature_ids=req.feature_ids,
            label_id=req.label_id,
            model_type=model_type,
            model_params=req.model_params,
            is_classifier=req.is_classifier,
            train_ratio=req.train_ratio,
            val_ratio=req.val_ratio,
        )
        queue = get_training_queue()
        job_id = queue.submit(job)
        return {"job_id": job_id, "status": "PENDING", "queue_status": queue.get_queue_status()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Submit failed: {e}")


@router.get("/training/queue/status")
async def queue_status():
    """获取训练队列状态"""
    queue = get_training_queue()
    return queue.get_queue_status()


@router.get("/training/queue/jobs")
async def queue_list_jobs(status: Optional[str] = None):
    """列出队列中的任务"""
    queue = get_training_queue()
    status_filter = TrainingStatus(status) if status else None
    return {"jobs": queue.list_jobs(status=status_filter), "queue_status": queue.get_queue_status()}


@router.get("/training/queue/jobs/{job_id}")
async def queue_get_job(job_id: str):
    """获取队列任务详情"""
    queue = get_training_queue()
    entry = queue.get_entry(job_id)
    if not entry:
        raise HTTPException(404, f"Job not found: {job_id}")
    result = queue.get_result(job_id)
    return {
        "entry": entry.to_dict(),
        "result": result.to_dict() if result else None,
    }


@router.delete("/training/queue/jobs/{job_id}")
async def queue_cancel_job(job_id: str):
    """取消队列任务（仅 Pending 状态可取消）"""
    queue = get_training_queue()
    if not queue.cancel(job_id):
        raise HTTPException(400, f"Cannot cancel job: {job_id} (not in PENDING state)")
    return {"job_id": job_id, "status": "CANCELLED"}


@router.post("/training/queue/clear")
async def queue_clear_completed():
    """清理已完成/失败的任务"""
    queue = get_training_queue()
    n = queue.clear_completed()
    return {"cleared": n, "queue_status": queue.get_queue_status()}


# ==================================================================
# Validation Center
# ==================================================================

@router.post("/validation/walk-forward")
async def walk_forward_validation(req: WalkForwardRequest):
    """Walk Forward 验证"""
    try:
        model_type = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    index = pd.to_datetime(req.index) if req.index else None
    features = pd.DataFrame(req.feature_data, index=index)
    label = pd.Series(req.label_data, index=index, name="label")

    config = ValidationConfig(
        n_splits=req.n_splits,
        train_size=req.train_size,
        test_size=req.test_size,
        step_size=req.step_size,
        gap=req.gap,
    )
    wf = WalkForward(config)
    result = wf.run(
        features=features,
        label=label,
        model_type=model_type,
        model_params=req.model_params,
        is_classifier=req.is_classifier,
    )
    return result.to_dict()


# ==================================================================
# Leakage Detector
# ==================================================================

@router.post("/leakage/check-data")
async def leakage_check_data(req: LeakageCheckDataRequest):
    """数据泄漏检测"""
    index = pd.to_datetime(req.index) if req.index else None
    features = pd.DataFrame(req.feature_data, index=index)
    label = pd.Series(req.label_data, index=index, name="label")

    detector = LeakageDetector()
    report = detector.check_data(features, label)
    return report.to_dict()


@router.post("/leakage/check-overlap")
async def leakage_check_overlap(req: LeakageCheckOverlapRequest):
    """时间重叠检测"""
    train_idx = pd.Index(req.train_index)
    test_idx = pd.Index(req.test_index)
    detector = LeakageDetector()
    report = detector.check_time_overlap(train_idx, test_idx)
    return report.to_dict()


# ==================================================================
# Model Registry
# ==================================================================

@router.get("/registry/versions")
async def list_model_versions(model_type: str = ""):
    """模型版本列表"""
    reg = get_model_registry()
    mt = ModelType(model_type) if model_type else None
    versions = reg.list_versions(model_type=mt)
    return {"versions": [v.to_dict() for v in versions]}


@router.post("/registry/versions")
async def register_model_version(req: RegisterVersionRequest):
    """注册模型版本"""
    try:
        model_type = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    reg = get_model_registry()
    version = ModelVersion(
        name=req.name,
        model_type=model_type,
        params=req.params,
        metrics=req.metrics,
        dataset_id=req.dataset_id,
        feature_ids=req.feature_ids,
        label_id=req.label_id,
        is_classifier=req.is_classifier,
        description=req.description,
        tags=req.tags,
    )
    vid = reg.register(version)
    return {"version_id": vid, "status": "ok"}


@router.get("/registry/versions/{version_id}")
async def get_model_version(version_id: str):
    """模型版本详情"""
    reg = get_model_registry()
    version = reg.get_version(version_id)
    if not version:
        raise HTTPException(404, f"Version not found: {version_id}")
    return version.to_dict(include_model=True)


# ==================================================================
# ML Strategy Builder
# ==================================================================

@router.post("/strategies")
async def build_strategy(req: BuildStrategyRequest):
    """构建 ML 策略"""
    try:
        model_type = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    df = pd.DataFrame(req.train_data)
    if df.empty:
        raise HTTPException(400, "train_data is required")

    builder = MLStrategyBuilder()
    try:
        model = builder.train(
            df=df,
            feature_ids=req.feature_ids,
            label_id=req.label_id,
            model_type=model_type,
            model_params=req.model_params,
            is_classifier=req.is_classifier,
        )
    except Exception as e:
        raise HTTPException(400, f"Training failed: {e}")

    strategy = builder.build(
        feature_ids=req.feature_ids,
        label_id=req.label_id,
        model=model,
        model_type=model_type,
        is_classifier=req.is_classifier,
        long_threshold=req.long_threshold,
        short_threshold=req.short_threshold,
        use_short=req.use_short,
        position_scale=req.position_scale,
        name=req.name,
    )

    _strategies[strategy.strategy_id] = strategy
    return strategy.to_dict()


@router.post("/strategies/predict")
async def strategy_predict(req: StrategyPredictRequest):
    """策略预测"""
    strategy = _strategies.get(req.strategy_id)
    if not strategy:
        raise HTTPException(404, f"Strategy not found: {req.strategy_id}")

    df = pd.DataFrame(req.data)
    if df.empty:
        raise HTTPException(400, "data is required")

    preds = strategy.predict(df)
    signals = strategy.signal(df)
    positions = strategy.position(df)

    return {
        "predictions": preds.tolist(),
        "signals": signals.tolist(),
        "positions": positions.tolist(),
        "index": [str(i) for i in preds.index],
    }


@router.get("/strategies")
async def list_strategies():
    """策略列表"""
    return {
        "strategies": [
            s.to_dict() for s in _strategies.values()
        ]
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """策略详情"""
    strategy = _strategies.get(strategy_id)
    if not strategy:
        raise HTTPException(404, f"Strategy not found: {strategy_id}")
    return strategy.to_dict()


# ==================================================================
# L2: FeatureSet — 特征集合
# ==================================================================

from quantlab.ml.feature import FeatureSet, FeatureSetRegistry, get_feature_set_registry
from quantlab.ml.label import LabelSet, LabelSetRegistry, get_label_set_registry
from quantlab.ml.experiment import Experiment, get_experiment_tracker
from quantlab.ml.search import GridSearch, RandomSearch
from quantlab.ml.comparison import ModelArena, ModelResult, compare_models, get_model_arena
from quantlab.ml.feature_analysis import (
    FeatureImportanceAnalyzer,
    compute_gain_importance,
    compute_permutation_importance,
)


class FeatureSetRequest(BaseModel):
    name: str
    feature_ids: List[str] = []
    description: str = ""
    version: str = "1.0"
    tags: List[str] = []


@router.get("/feature-sets")
async def list_feature_sets(tag: str = ""):
    """FeatureSet 列表"""
    reg = get_feature_set_registry()
    sets = reg.list_all(tag=tag if tag else None)
    return {
        "total": len(sets),
        "sets": [fs.to_dict() for fs in sets],
    }


@router.post("/feature-sets")
async def create_feature_set(req: FeatureSetRequest):
    """创建 FeatureSet"""
    reg = get_feature_set_registry()
    if reg.get(req.name):
        raise HTTPException(400, f"FeatureSet already exists: {req.name}")
    fs = FeatureSet(
        name=req.name,
        feature_ids=req.feature_ids,
        description=req.description,
        version=req.version,
        tags=req.tags,
    )
    reg.register(fs)
    return fs.to_dict()


@router.get("/feature-sets/{name}")
async def get_feature_set(name: str):
    """FeatureSet 详情"""
    reg = get_feature_set_registry()
    fs = reg.get(name)
    if not fs:
        raise HTTPException(404, f"FeatureSet not found: {name}")
    return fs.to_dict()


# ==================================================================
# L3: LabelSet — 标签集合
# ==================================================================

class LabelSetRequest(BaseModel):
    name: str
    label_id: str
    description: str = ""
    version: str = "1.0"
    label_type: str = "regression"
    classes: List[str] = []
    tags: List[str] = []


@router.get("/label-sets")
async def list_label_sets(tag: str = ""):
    """LabelSet 列表"""
    reg = get_label_set_registry()
    sets = reg.list_all(tag=tag if tag else None)
    return {
        "total": len(sets),
        "sets": [ls.to_dict() for ls in sets],
    }


@router.post("/label-sets")
async def create_label_set(req: LabelSetRequest):
    """创建 LabelSet"""
    reg = get_label_set_registry()
    if reg.get(req.name):
        raise HTTPException(400, f"LabelSet already exists: {req.name}")
    ls = LabelSet(
        name=req.name,
        label_id=req.label_id,
        description=req.description,
        version=req.version,
        label_type=req.label_type,
        classes=req.classes,
        tags=req.tags,
    )
    reg.register(ls)
    return ls.to_dict()


@router.get("/label-sets/{name}")
async def get_label_set(name: str):
    """LabelSet 详情"""
    reg = get_label_set_registry()
    ls = reg.get(name)
    if not ls:
        raise HTTPException(404, f"LabelSet not found: {name}")
    return ls.to_dict()


# ==================================================================
# L5: Experiment Tracker — 实验追踪
# ==================================================================

@router.get("/experiments")
async def list_experiments(
    tag: str = "",
    status: str = "",
    model_type: str = "",
):
    """实验列表"""
    tracker = get_experiment_tracker()
    exps = tracker.list_all(
        tag=tag if tag else None,
        status=status if status else None,
        model_type=model_type if model_type else None,
    )
    return {
        "total": len(exps),
        "experiments": [e.to_dict() for e in exps],
    }


@router.get("/experiments/leaderboard")
async def get_experiment_leaderboard(metric: str = "ic", limit: int = 20):
    """实验排行榜"""
    tracker = get_experiment_tracker()
    return {
        "metric": metric,
        "leaderboard": tracker.get_leaderboard(metric=metric, limit=limit),
    }


@router.get("/experiments/summary")
async def get_experiment_summary():
    """实验统计"""
    tracker = get_experiment_tracker()
    return tracker.get_summary()


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """实验详情"""
    tracker = get_experiment_tracker()
    exp = tracker.get(experiment_id)
    if not exp:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")
    return exp.to_dict()


# ==================================================================
# L6: Hyperparameter Search — 超参搜索
# ==================================================================

class GridSearchRequest(BaseModel):
    dataset_id: str
    feature_set_id: str = ""
    label_set_id: str = ""
    feature_ids: List[str] = []
    label_id: str = ""
    model_type: str = "LIGHTGBM"
    param_grid: Dict[str, List[Any]] = {}
    metric: str = "ic"
    is_classifier: bool = False
    train_ratio: float = 0.7
    val_ratio: float = 0.15


class RandomSearchRequest(BaseModel):
    dataset_id: str
    feature_set_id: str = ""
    label_set_id: str = ""
    feature_ids: List[str] = []
    label_id: str = ""
    model_type: str = "LIGHTGBM"
    param_space: Dict[str, Any] = {}
    n_trials: int = 10
    metric: str = "ic"
    is_classifier: bool = False
    train_ratio: float = 0.7
    val_ratio: float = 0.15


@router.post("/search/grid")
async def run_grid_search_api(req: GridSearchRequest):
    """网格搜索"""
    from quantlab.ml.pipeline import get_pipeline
    from quantlab.ml.search import GridSearch as _GS

    try:
        mt = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    pipeline = get_pipeline()

    # 构建 TrainingDataset
    if req.feature_set_id and req.label_set_id:
        tds = pipeline.build(
            dataset_id=req.dataset_id,
            feature_set_id=req.feature_set_id,
            label_set_id=req.label_set_id,
        )
    elif req.feature_ids and req.label_id:
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(404, f"Dataset not found: {req.dataset_id}")
        df = ds.get_data()
        if df is None:
            raise HTTPException(400, f"Dataset has no data: {req.dataset_id}")
        tds = pipeline.build_from_raw(
            df=df,
            feature_ids=req.feature_ids,
            label_id=req.label_id,
        )
    else:
        raise HTTPException(400, "Must specify feature_set_id+label_set_id or feature_ids+label_id")

    search = _GS(
        model_type=mt,
        param_grid=req.param_grid,
        metric=req.metric,
        is_classifier=req.is_classifier,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
    )
    result = search.run(tds)
    return result.to_dict()


@router.post("/search/random")
async def run_random_search_api(req: RandomSearchRequest):
    """随机搜索"""
    from quantlab.ml.pipeline import get_pipeline
    from quantlab.ml.search import RandomSearch as _RS

    try:
        mt = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    pipeline = get_pipeline()

    if req.feature_set_id and req.label_set_id:
        tds = pipeline.build(
            dataset_id=req.dataset_id,
            feature_set_id=req.feature_set_id,
            label_set_id=req.label_set_id,
        )
    elif req.feature_ids and req.label_id:
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(404, f"Dataset not found: {req.dataset_id}")
        df = ds.get_data()
        if df is None:
            raise HTTPException(400, f"Dataset has no data: {req.dataset_id}")
        tds = pipeline.build_from_raw(
            df=df,
            feature_ids=req.feature_ids,
            label_id=req.label_id,
        )
    else:
        raise HTTPException(400, "Must specify feature_set_id+label_set_id or feature_ids+label_id")

    # 转换 param_space（JSON 中的 tuple 会变成 list）
    param_space = {}
    for k, v in req.param_space.items():
        if isinstance(v, list) and len(v) == 2:
            param_space[k] = tuple(v)
        else:
            param_space[k] = v

    search = _RS(
        model_type=mt,
        param_space=param_space,
        n_trials=req.n_trials,
        metric=req.metric,
        is_classifier=req.is_classifier,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
    )
    result = search.run(tds)
    return result.to_dict()


# ==================================================================
# L9: Model Comparison — Model Arena
# ==================================================================

class ComparisonRequest(BaseModel):
    dataset_id: str
    feature_set_id: str = ""
    label_set_id: str = ""
    feature_ids: List[str] = []
    label_id: str = ""
    model_types: List[str] = ["LINEAR_REGRESSION", "LIGHTGBM"]
    is_classifier: bool = False
    train_ratio: float = 0.7
    val_ratio: float = 0.15


@router.post("/comparison/run")
async def run_model_comparison(req: ComparisonRequest):
    """运行模型对比"""
    from quantlab.ml.pipeline import get_pipeline

    # 解析模型类型
    try:
        model_types = [ModelType(m) for m in req.model_types]
    except ValueError as e:
        raise HTTPException(400, f"Unknown model type: {e}")

    pipeline = get_pipeline()

    if req.feature_set_id and req.label_set_id:
        tds = pipeline.build(
            dataset_id=req.dataset_id,
            feature_set_id=req.feature_set_id,
            label_set_id=req.label_set_id,
        )
    elif req.feature_ids and req.label_id:
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(404, f"Dataset not found: {req.dataset_id}")
        df = ds.get_data()
        if df is None:
            raise HTTPException(400, f"Dataset has no data: {req.dataset_id}")
        tds = pipeline.build_from_raw(
            df=df,
            feature_ids=req.feature_ids,
            label_id=req.label_id,
        )
    else:
        raise HTTPException(400, "Must specify feature_set_id+label_set_id or feature_ids+label_id")

    arena = compare_models(
        tds=tds,
        model_types=model_types,
        is_classifier=req.is_classifier,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
    )
    return {
        "leaderboard": arena.get_leaderboard(metric="ic"),
        "total": len(arena.list_all()),
    }


@router.get("/comparison/arena")
async def get_arena():
    """获取 Model Arena"""
    arena = get_model_arena()
    return arena.to_dict()


@router.get("/comparison/leaderboard")
async def get_arena_leaderboard(metric: str = "ic", ascending: bool = False):
    """获取排行榜"""
    arena = get_model_arena()
    return {
        "metric": metric,
        "leaderboard": arena.get_leaderboard(metric=metric, ascending=ascending),
    }


# ==================================================================
# L8: Feature Importance — 特征重要性
# ==================================================================

class ImportanceRequest(BaseModel):
    feature_data: Dict[str, List[float]] = {}
    label_data: List[float] = []
    index: List[str] = []
    model_type: str = "LIGHTGBM"
    model_params: Dict[str, Any] = {}
    is_classifier: bool = False
    methods: List[str] = ["gain"]
    train_ratio: float = 0.7


@router.post("/feature-importance")
async def compute_feature_importance(req: ImportanceRequest):
    """计算特征重要性"""
    if not req.feature_data or not req.label_data:
        raise HTTPException(400, "feature_data and label_data are required")

    try:
        mt = ModelType(req.model_type)
    except ValueError:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    # 构建 DataFrame
    X = pd.DataFrame(req.feature_data)
    if req.index:
        X.index = pd.to_datetime(req.index)
    y = pd.Series(req.label_data, index=X.index, name="label")

    # 切分训练
    n = len(X)
    train_end = int(n * req.train_ratio)
    X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]

    # 训练模型
    model = create_model(
        model_type=mt,
        params=req.model_params,
        is_classifier=req.is_classifier,
    )
    model.fit(X_train, y_train)

    # 计算重要性
    analyzer = FeatureImportanceAnalyzer()
    results = analyzer.analyze(model, X=X, y=y, methods=req.methods)

    return {
        "method": req.methods,
        "results": {k: v.to_dict() for k, v in results.items()},
    }


# ==================================================================
# M1: Diagnostics — 特征诊断 + 标签诊断
# ==================================================================

from quantlab.ml.diagnostics import (
    FeatureDiagnostics,
    LabelDiagnostics,
)


class FeatureDiagnosticsRequest(BaseModel):
    """特征诊断请求"""
    feature_data: Dict[str, List[float]] = {}
    index: List[str] = []


class LabelDiagnosticsRequest(BaseModel):
    """标签诊断请求"""
    label_data: List[float] = []
    index: List[str] = []
    label_type: str = ""        # 留空则自动推断；可显式指定 regression / classification


@router.post("/diagnostics/features")
async def feature_diagnostics(req: FeatureDiagnosticsRequest):
    """
    特征诊断（M1 必做）

    自动统计每个特征的：
      - missing_rate   缺失率
      - inf_count      无穷值数量
      - zero_rate      零值率
      - variance       方差
      - n_unique       唯一值数

    自动标红坏特征：
      - 全为空 / 全为 0
      - 方差接近 0
      - 含 inf
      - 常量特征
    """
    if not req.feature_data:
        raise HTTPException(400, "feature_data is required")

    index = pd.to_datetime(req.index) if req.index else None
    X = pd.DataFrame(req.feature_data, index=index)

    diag = FeatureDiagnostics()
    report = diag.report(X)
    return report.to_dict()


@router.post("/diagnostics/labels")
async def label_diagnostics(req: LabelDiagnosticsRequest):
    """
    标签诊断（M1 必做）

    统计：
      - label_distribution   标签分布
      - n_missing / n_inf
      - variance（回归）/ class_distribution（分类）

    报警：
      - 标签严重失衡（如 上涨 95% / 下跌 5%）
      - 标签全为空 / 含 inf / 方差为 0
    """
    if not req.label_data:
        raise HTTPException(400, "label_data is required")

    index = pd.to_datetime(req.index) if req.index else None
    y = pd.Series(req.label_data, index=index, name="label")

    diag = LabelDiagnostics()
    label_type = req.label_type if req.label_type else None
    report = diag.report(y, label_type=label_type)
    return report.to_dict()


@router.post("/diagnostics/training-dataset")
async def training_dataset_diagnostics(req: TrainRequest):
    """
    一键诊断：基于 dataset_id + feature_ids + label_id
    自动构建 TrainingDataset 并运行 Feature + Label 诊断
    """
    from quantlab.ml import get_pipeline

    pipeline = get_pipeline()
    try:
        tds = pipeline.build_from_raw(
            df=_load_dataset_df(req.dataset_id),
            feature_ids=req.feature_ids,
            label_id=req.label_id,
            dropna=False,           # 诊断时不丢 NaN，否则看不出问题
        )
    except Exception as e:
        raise HTTPException(400, f"Build TrainingDataset failed: {e}")

    feat_diag = FeatureDiagnostics().report(tds.X)
    label_diag = LabelDiagnostics().report(tds.y)

    return {
        "n_samples": len(tds),
        "n_features": tds.X.shape[1],
        "feature_diagnostics": feat_diag.to_dict(),
        "label_diagnostics": label_diag.to_dict(),
    }


def _load_dataset_df(dataset_id: str) -> pd.DataFrame:
    """从 DatasetManager 加载数据 DataFrame"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    df = ds.get_data()
    if df is None:
        raise HTTPException(400, f"Dataset has no data: {dataset_id}")
    return df


# ==================================================================
# M2: Metrics Engine + Experiment Comparator
# ==================================================================

from quantlab.ml.metrics import compute_all_metrics
from quantlab.ml.experiment import (
    ExperimentComparator,
    compare_experiments,
)


class MetricsComputeRequest(BaseModel):
    """指标计算请求"""
    y_true: List[float] = []
    y_pred: List[float] = []
    y_proba: Optional[List[float]] = None
    is_classifier: bool = False
    annualization: int = 252
    positive_label: float = 1.0


@router.post("/metrics/compute")
async def compute_metrics(req: MetricsComputeRequest):
    """
    Metrics Engine — 计算量化指标

    优先级：
      IC ★★★★★ / RankIC ★★★★★ / Sharpe ★★★★★
      Precision ★★★★☆ / Recall ★★★★☆ / AUC ★★★★☆
      Accuracy ★★

    回归：IC / RankIC / Sharpe / MAE / MSE / RMSE / R2
    分类：Accuracy / Precision / Recall / AUC / IC
    """
    if not req.y_true or not req.y_pred:
        raise HTTPException(400, "y_true and y_pred are required")
    if len(req.y_true) != len(req.y_pred):
        raise HTTPException(400, "y_true and y_pred must have same length")

    result = compute_all_metrics(
        y_true=req.y_true,
        y_pred=req.y_pred,
        is_classifier=req.is_classifier,
        y_proba=req.y_proba,
        annualization=req.annualization,
        positive_label=req.positive_label,
    )
    return result.to_dict()


class ExperimentCompareRequest(BaseModel):
    """实验对比请求"""
    experiment_ids: List[str] = []
    metrics_to_compare: Optional[List[str]] = None


@router.post("/experiments/compare")
async def compare_experiments_api(req: ExperimentCompareRequest):
    """
    Experiment Comparator — 实验对比

    比较：
      EXP_001 VS EXP_002

    输出：
      指标       Exp1     Exp2     Diff
      IC         0.08     0.11     +0.03
      Sharpe     1.4      1.6      +0.20
    """
    if len(req.experiment_ids) < 2:
        raise HTTPException(400, "At least 2 experiment_ids required")

    tracker = get_experiment_tracker()
    experiments = []
    for eid in req.experiment_ids:
        exp = tracker.get(eid)
        if not exp:
            raise HTTPException(404, f"Experiment not found: {eid}")
        experiments.append(exp)

    report = compare_experiments(
        experiments=experiments,
        metrics_to_compare=req.metrics_to_compare,
    )
    return report.to_dict()


# ==================================================================
# L15: Feature Importance — 特征重要性
# ==================================================================
