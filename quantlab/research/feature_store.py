"""
FeatureStore — V4.5 特征存储

职责：
  - 保存研究结果（因子值、信号、中间 DataFrame）
  - 计算一次，以后直接 load
  - 元数据追踪：谁算的、基于什么数据、什么公式
  - 与 ResearchCache 集成，自动缓存

用法：
    fs = FeatureStore(cache=ResearchCache())
    fs.save("rsi14", df_rsi, dataset="btcusdt_1m", formula="rsi(close, 14)")
    df = fs.load("rsi14")
    meta = fs.get_metadata("rsi14")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from .cache import ResearchCache

logger = logging.getLogger("quantlab.research.feature_store")


# ------------------------------------------------------------------
# FeatureMetadata
# ------------------------------------------------------------------
@dataclass(slots=True)
class FeatureMetadata:
    """特征元数据"""
    name: str
    dataset: str = ""
    creator: str = ""
    created_at: str = ""
    formula: str = ""
    version: str = "1"
    dtype: str = ""           # "dataframe" / "series"
    shape: str = ""           # "(300, 5)"
    columns: str = ""         # "AAPL,MSFT,GOOG"
    description: str = ""
    tags: str = ""            # "momentum,technical"
    dependencies: str = ""    # "close,ma20"


# ------------------------------------------------------------------
# FeatureStore
# ------------------------------------------------------------------
class FeatureStore:
    """
    特征存储

    底层用 ResearchCache 做持久化，
    额外维护一份 _metadata.json 追踪所有特征的元信息。

    key 约定："{category}:{name}"  category ∈ {"feature", "signal", "intermediate"}
    """

    def __init__(
        self,
        cache: Optional[ResearchCache] = None,
        store_dir: str = "storage/feature_store",
    ) -> None:
        self.cache = cache or ResearchCache(
            cache_dir=os.path.join(store_dir, "_cache")
        )
        self.store_dir = store_dir
        self._meta: Dict[str, FeatureMetadata] = {}
        os.makedirs(store_dir, exist_ok=True)
        self._load_meta()

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------
    def save(
        self,
        name: str,
        value: Any,
        dataset: str = "",
        formula: str = "",
        creator: str = "",
        version: str = "1",
        description: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> FeatureMetadata:
        """
        保存特征

        自动写入 ResearchCache + 元数据
        """
        key = f"feature:{name}"
        # 写 cache
        self.cache.put(
            key, value,
            category="feature",
            version=version,
            metadata={"name": name, "dataset": dataset},
        )
        # 元数据
        meta = FeatureMetadata(
            name=name,
            dataset=dataset,
            creator=creator or "research_session",
            created_at=_now_iso(),
            formula=formula,
            version=version,
            dtype=_dtype_of(value),
            shape=str(getattr(value, "shape", "")),
            columns=_columns_of(value),
            description=description,
            tags=",".join(tags or []),
            dependencies=",".join(dependencies or []),
        )
        self._meta[name] = meta
        self._save_meta()
        logger.info(f"feature saved: {name} (shape={meta.shape})")
        return meta

    def load(self, name: str, version: Optional[str] = None) -> Optional[Any]:
        """加载特征"""
        key = f"feature:{name}"
        return self.cache.get(key, version=version)

    def has(self, name: str, version: Optional[str] = None) -> bool:
        key = f"feature:{name}"
        return self.cache.has(key, version=version)

    def get_metadata(self, name: str) -> Optional[FeatureMetadata]:
        return self._meta.get(name)

    def delete(self, name: str) -> bool:
        key = f"feature:{name}"
        removed = self.cache.invalidate(key)
        self._meta.pop(name, None)
        self._save_meta()
        return removed

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def list_features(
        self,
        dataset: Optional[str] = None,
        tag: Optional[str] = None,
        creator: Optional[str] = None,
    ) -> List[FeatureMetadata]:
        """列出所有特征，可选过滤"""
        results = list(self._meta.values())
        if dataset:
            results = [m for m in results if m.dataset == dataset]
        if tag:
            results = [m for m in results if tag in m.tags]
        if creator:
            results = [m for m in results if m.creator == creator]
        return results

    def search(self, keyword: str) -> List[FeatureMetadata]:
        """按关键词搜索（name / formula / description / tags）"""
        kw = keyword.lower()
        return [
            m for m in self._meta.values()
            if kw in m.name.lower()
            or kw in m.formula.lower()
            or kw in m.description.lower()
            or kw in m.tags.lower()
        ]

    def stats(self) -> Dict[str, Any]:
        total = len(self._meta)
        by_dataset: Dict[str, int] = {}
        by_dtype: Dict[str, int] = {}
        for m in self._meta.values():
            by_dataset[m.dataset] = by_dataset.get(m.dataset, 0) + 1
            by_dtype[m.dtype] = by_dtype.get(m.dtype, 0) + 1
        return {
            "total_features": total,
            "by_dataset": by_dataset,
            "by_dtype": by_dtype,
            "cache_stats": self.cache.stats(),
        }

    # ------------------------------------------------------------------
    # 高级：compute + save 一步到位
    # ------------------------------------------------------------------
    def compute(
        self,
        name: str,
        fn: Callable,
        *args,
        force: bool = False,
        **kwargs,
    ) -> Any:
        """
        计算特征（如果已缓存则直接 load，除非 force=True）

        用法：
            rsi14 = fs.compute("rsi14", lambda: rsi(ctx, 14))
        """
        if not force and self.has(name):
            val = self.load(name)
            if val is not None:
                logger.info(f"feature cache hit: {name}")
                return val
        logger.info(f"feature computing: {name}")
        value = fn(*args, **kwargs)
        self.save(name, value)
        return value

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _meta_path(self) -> str:
        return os.path.join(self.store_dir, "_metadata.json")

    def _load_meta(self):
        mp = self._meta_path()
        if not os.path.exists(mp):
            return
        try:
            with open(mp, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, d in raw.items():
                self._meta[k] = FeatureMetadata(**d)
        except Exception:
            self._meta = {}

    def _save_meta(self):
        mp = self._meta_path()
        try:
            raw = {k: asdict(v) for k, v in self._meta.items()}
            with open(mp, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"feature meta save fail: {e}")


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def _dtype_of(value: Any) -> str:
    if isinstance(value, pd.DataFrame):
        return "dataframe"
    elif isinstance(value, pd.Series):
        return "series"
    return "object"


def _columns_of(value: Any) -> str:
    if isinstance(value, pd.DataFrame):
        return ",".join(str(c) for c in value.columns[:20])
    return ""
