"""
Dataset — 数据集对象

ML Lab 第一部分：训练数据管理

  Dataset
    - dataset_id
    - name
    - symbols
    - start_date / end_date
    - frequency

  DatasetManager
    - 创建 / 查询 / 加载
    - 统计：样本量 / 缺失值 / 字段
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.dataset")


@dataclass
class DatasetStats:
    """数据集统计信息"""
    n_rows: int = 0
    n_cols: int = 0
    n_symbols: int = 0
    n_missing: int = 0
    missing_pct: float = 0.0
    columns: List[str] = field(default_factory=list)
    dtypes: Dict[str, str] = field(default_factory=dict)
    date_range: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "n_symbols": self.n_symbols,
            "n_missing": self.n_missing,
            "missing_pct": round(self.missing_pct, 4),
            "columns": self.columns,
            "dtypes": self.dtypes,
            "date_range": self.date_range,
        }


@dataclass
class Dataset:
    """
    数据集

    用法：
        ds = Dataset(
            name="Crypto_1H",
            symbols=["BTC", "ETH", "SOL"],
            start_date="2020-01-01",
            end_date="2025-01-01",
            frequency="1h",
        )
        ds.set_data(df)
        stats = ds.get_stats()
    """
    dataset_id: str = field(default_factory=lambda: f"DS-{uuid.uuid4().hex[:8]}")
    name: str = ""
    symbols: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    frequency: str = "1d"          # 1m / 5m / 15m / 1h / 4h / 1d
    description: str = ""
    tags: List[str] = field(default_factory=list)
    # 统一存储扩展字段（合并自原 datasets.db）
    asset_type: str = "crypto"     # crypto / stock / futures
    storage_path: str = ""
    storage_format: str = "parquet"
    schema: Dict[str, Any] = field(default_factory=lambda: {"columns": [], "column_names": [], "has_ohlcv": True})
    is_ohlcv: bool = True
    coverage: str = ""
    # Universe 支持：scope_type=single 时用 symbols，scope_type=universe 时用 universe_id
    scope_type: str = "single"     # single / universe
    universe_id: str = ""          # 引用 universe 定义（如 "CSI300", "ALL_A"）
    _data: Optional[pd.DataFrame] = None
    _has_data_flag: bool = False  # DB 持久化的 has_data 标志（不依赖内存）
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()

    def set_data(self, df: pd.DataFrame) -> None:
        """设置数据"""
        self._data = df
        self._has_data_flag = df is not None and len(df) > 0
        if df is not None and len(df) > 0:
            # 自动推断日期范围
            if isinstance(df.index, pd.DatetimeIndex):
                self.start_date = str(df.index.min())
                self.end_date = str(df.index.max())

    def get_data(self) -> Optional[pd.DataFrame]:
        """获取数据（内存无数据时从 Parquet 加载）"""
        if self._data is not None:
            return self._data
        # 尝试从 Parquet 持久化加载
        try:
            from quantlab.ml.storage import get_parquet_store
            ps = get_parquet_store()
            df = ps.load_dataset_data(self.dataset_id)
            if df is not None:
                self._data = df
                return df
        except Exception:
            pass
        return None

    def get_stats(self) -> DatasetStats:
        """获取统计信息"""
        if self._data is None:
            return DatasetStats()

        df = self._data
        n_missing = int(df.isnull().sum().sum())
        total_cells = df.shape[0] * df.shape[1]

        # 动态推断 n_symbols：优先从 symbol 列去重计数，否则取元信息 symbols 长度
        if "symbol" in df.columns:
            n_symbols = df["symbol"].nunique()
        elif len(self.symbols) > 0:
            n_symbols = len(self.symbols)
        else:
            n_symbols = 1

        date_range = []
        if isinstance(df.index, pd.DatetimeIndex):
            date_range = [str(df.index.min()), str(df.index.max())]

        return DatasetStats(
            n_rows=df.shape[0],
            n_cols=df.shape[1],
            n_symbols=n_symbols,
            n_missing=n_missing,
            missing_pct=n_missing / total_cells if total_cells > 0 else 0,
            columns=list(df.columns),
            dtypes={c: str(df[c].dtype) for c in df.columns},
            date_range=date_range,
        )

    def preview(self, n: int = 10) -> Dict:
        """预览数据"""
        if self._data is None:
            return {"head": [], "tail": [], "describe": {}}
        df = self._data
        return {
            "head": df.head(n).to_dict(orient="records"),
            "tail": df.tail(n).to_dict(orient="records"),
            "describe": df.describe().to_dict() if len(df) > 0 else {},
        }

    def to_dict(self) -> Dict:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "symbols": self.symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency": self.frequency,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "has_data": self._has_data_flag or self._data is not None,
            # 统一存储扩展字段
            "asset_type": self.asset_type,
            "storage_path": self.storage_path,
            "storage_format": self.storage_format,
            "schema": self.schema,
            "is_ohlcv": self.is_ohlcv,
            "coverage": self.coverage,
            # Universe 支持
            "scope_type": self.scope_type,
            "universe_id": self.universe_id,
        }


class DatasetManager:
    """
    数据集管理器

    用法：
        mgr = get_dataset_manager()
        ds = mgr.create_dataset(name="Crypto_1H", symbols=["BTC", "ETH"])
        mgr.load_csv("Crypto_1H", "data/btc_1h.csv")
        stats = mgr.get_stats("Crypto_1H")

    持久化（M2 新增）：
        mgr = DatasetManager(persist=True)        # 开启 SQLite + Parquet 持久化
        mgr.load_from_store()                      # 从 DB 恢复所有 Dataset
        # create / load_csv / remove_dataset 会自动同步到 DB 和 Parquet
    """

    def __init__(self, persist: bool = False) -> None:
        self._datasets: Dict[str, Dataset] = {}
        self._persist = persist
        self._store = None
        self._parquet = None
        if persist:
            from ..storage import get_ml_store, get_parquet_store
            self._store = get_ml_store()
            self._parquet = get_parquet_store()

    def create_dataset(
        self,
        name: str,
        symbols: List[str],
        frequency: str = "1d",
        description: str = "",
        tags: Optional[List[str]] = None,
        asset_type: str = "crypto",
        is_ohlcv: bool = True,
        scope_type: str = "single",
        universe_id: str = "",
    ) -> Dataset:
        """创建数据集"""
        ds = Dataset(
            name=name,
            symbols=symbols,
            frequency=frequency,
            description=description,
            tags=tags or [],
            asset_type=asset_type,
            is_ohlcv=is_ohlcv,
            scope_type=scope_type,
            universe_id=universe_id,
        )
        self._datasets[ds.dataset_id] = ds
        if self._persist and self._store:
            self._store.save_dataset(ds.to_dict(), has_data=False)
        logger.info(f"Dataset created: {ds.dataset_id} ({name})")
        return ds

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        return self._datasets.get(dataset_id)

    def get_by_name(self, name: str) -> Optional[Dataset]:
        for ds in self._datasets.values():
            if ds.name == name:
                return ds
        return None

    def list_datasets(self) -> List[Dataset]:
        return list(self._datasets.values())

    def remove_dataset(self, dataset_id: str) -> bool:
        # 从内存移除
        removed = dataset_id in self._datasets
        if removed:
            self._datasets.pop(dataset_id)
        # 从 SQLite 移除
        if self._persist and self._store:
            self._store.delete_dataset(dataset_id)
            removed = True
        # 从 Parquet 移除
        if self._parquet:
            if self._parquet.delete_dataset_data(dataset_id):
                removed = True
        return removed

    def load_csv(self, dataset_id: str, filepath: str) -> bool:
        """从 CSV 加载数据"""
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        try:
            df = self._read_csv_smart(filepath)
            ds.set_data(df)
            self._infer_symbols(ds, df)
            self._check_multi_symbol(ds, df)
            if self._persist and self._parquet:
                self._parquet.save_dataset_data(dataset_id, df)
                if self._store:
                    # 回写完整元信息（symbols/start_date/end_date/has_data）
                    self._store.save_dataset(ds.to_dict(), has_data=True)
            logger.info(f"CSV loaded: {filepath} → {ds.dataset_id} ({df.shape})")
            return True
        except Exception as e:
            logger.error(f"CSV load failed: {e}")
            return False

    def load_dataframe(self, dataset_id: str, df: pd.DataFrame) -> bool:
        """从 DataFrame 加载数据"""
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        ds.set_data(df)
        self._infer_symbols(ds, df)
        self._check_multi_symbol(ds, df)
        if self._persist and self._parquet:
            self._parquet.save_dataset_data(dataset_id, df)
            if self._store:
                self._store.save_dataset(ds.to_dict(), has_data=True)
        return True

    def _infer_symbols(self, ds: Dataset, df: pd.DataFrame) -> None:
        """从数据自动推断 symbols：如果元信息为空且数据含 symbol 列，则自动填充"""
        if ds.symbols or "symbol" not in df.columns:
            return
        # 过滤 NaN（NaN 是 float，不能和 str 一起 sorted）
        inferred = sorted([s for s in df["symbol"].unique().tolist() if pd.notna(s)])
        ds.symbols = inferred
        logger.info(f"Inferred {len(inferred)} symbols for dataset {ds.dataset_id}")

    def _read_csv_smart(self, filepath: str) -> pd.DataFrame:
        """智能读取 CSV：自动检测时间列作为索引，保留 symbol 列

        支持的 CSV 格式：
        1. 第一列是时间（单标的）: datetime,open,close,...
        2. 有 trade_date/date/datetime 列（多标的）: symbol,trade_date,open,close,...
        3. 第一列是 symbol（多标的）: symbol,trade_date,open,close,...
        """
        # 先不带 index_col 读取，检查列结构
        df = pd.read_csv(filepath, nrows=5)

        time_col_candidates = ["trade_date", "date", "datetime", "time", "timestamp"]

        # 找到时间列
        time_col = None
        for col in time_col_candidates:
            if col in df.columns:
                time_col = col
                break

        # 重新完整读取
        if time_col:
            # 有明确的时间列：用时间列做索引，保留其他所有列（包括 symbol）
            df = pd.read_csv(filepath, parse_dates=[time_col])
            df = df.set_index(time_col)
        else:
            # 没有明确时间列：检查第一列是否像时间
            first_col = df.columns[0]
            try:
                test = pd.read_csv(filepath, nrows=2)
                pd.to_datetime(test[first_col])
                # 第一列是时间，用 index_col=0
                df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            except (ValueError, TypeError):
                # 第一列不是时间（可能是 symbol 等），不设索引
                df = pd.read_csv(filepath)

        return df

    def _check_multi_symbol(self, ds: Dataset, df: pd.DataFrame) -> None:
        """检测多标的数据：如果同一天有多行但没有 symbol 列，发出警告并自动设置 scope_type"""
        if "symbol" in df.columns:
            # 有 symbol 列，根据标的数量自动设置 scope_type
            n_symbols = df["symbol"].nunique()
            if n_symbols > 1 and ds.scope_type == "single":
                ds.scope_type = "universe"
                logger.info(f"Auto-set scope_type=universe for dataset {ds.dataset_id} ({n_symbols} symbols)")
            return

        # 没有 symbol 列，但可能是多标的堆叠数据
        # 检测方式：如果 index 是日期，同一天有多行
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
            dup_dates = df.index.duplicated().sum()
            if dup_dates > 0:
                n_per_date = df.groupby(df.index.date).size()
                avg_per_date = n_per_date.mean()
                logger.warning(
                    f"Dataset {ds.dataset_id} appears to be multi-symbol "
                    f"(avg {avg_per_date:.0f} rows/date, {dup_dates} duplicate dates) "
                    f"but has no 'symbol' column. "
                    f"Feature computation will produce INCORRECT results. "
                    f"Please add a 'symbol' column to identify each row's instrument."
                )
                ds.scope_type = "universe"

    def get_stats(self, dataset_id: str) -> Optional[DatasetStats]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return ds.get_stats()

    def preview(self, dataset_id: str, n: int = 10) -> Optional[Dict]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return ds.preview(n)

    def to_dict(self) -> Dict:
        return {
            "total": len(self._datasets),
            "datasets": [ds.to_dict() for ds in self._datasets.values()],
        }

    # ------------------------------------------------------------------
    # 持久化：从 DB 恢复
    # ------------------------------------------------------------------

    def load_from_store(self) -> int:
        """
        从 SQLite 恢复所有 Dataset 元信息到内存。
        数据 DataFrame 不自动加载（按需调用 load_dataset_data）。
        返回恢复的 Dataset 数量。
        """
        if not self._store:
            return 0
        rows = self._store.list_datasets()
        count = 0
        for row in rows:
            if row["dataset_id"] in self._datasets:
                continue
            # symbols 可能是 JSON 字符串或逗号分隔字符串
            symbols_raw = row["symbols"]
            if isinstance(symbols_raw, str):
                if symbols_raw.startswith("["):
                    import json
                    try:
                        symbols = json.loads(symbols_raw)
                    except (json.JSONDecodeError, TypeError):
                        symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
                else:
                    symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
            else:
                symbols = symbols_raw if isinstance(symbols_raw, list) else []

            ds = Dataset(
                name=row["name"],
                symbols=symbols,
                frequency=row["frequency"],
                description=row["description"],
                tags=row["tags"],
                asset_type=row.get("asset_type", "crypto"),
                storage_path=row.get("storage_path", ""),
                storage_format=row.get("storage_format", "parquet"),
                schema=row.get("schema", {"columns": [], "column_names": [], "has_ohlcv": True}),
                is_ohlcv=row.get("is_ohlcv", True),
                coverage=row.get("coverage", ""),
                scope_type=row.get("scope_type", "single"),
                universe_id=row.get("universe_id", ""),
            )
            # 覆盖为 DB 中的 id 和时间戳，保持一致
            ds.dataset_id = row["dataset_id"]
            ds.created_at = row["created_at"]
            ds.start_date = row["start_date"]
            ds.end_date = row["end_date"]
            ds._has_data_flag = row.get("has_data", False)
            self._datasets[ds.dataset_id] = ds
            count += 1
        logger.info(f"Loaded {count} datasets from store")
        return count

    def seed_sample_datasets(self) -> int:
        """
        注入示例数据集（合并自原 datasets.db 的种子数据）。
        只添加不存在的样本，已存在的跳过。
        返回新增数量。
        """
        samples = [
            ("BTC_1h", "BTC/USDT 1H", "BTCUSDT", "1h", "crypto", "2023-01-01", "2025-06-01", 17520, "crypto", "BTC"),
            ("ETH_1h", "ETH/USDT 1H", "ETHUSDT", "1h", "crypto", "2023-01-01", "2025-06-01", 17520, "crypto", "ETH"),
            ("SOL_4h", "SOL/USDT 4H", "SOLUSDT", "4h", "crypto", "2023-06-01", "2025-06-01", 4380, "crypto", "SOL"),
            ("BNB_1d", "BNB/USDT 1D", "BNBUSDT", "1d", "crypto", "2022-01-01", "2025-06-01", 1248, "crypto", "BNB"),
            ("BTC_5m", "BTC/USDT 5M", "BTCUSDT", "5m", "crypto", "2024-01-01", "2025-06-01", 148032, "crypto", "BTC"),
            ("ETH_15m", "ETH/USDT 15M", "ETHUSDT", "15m", "crypto", "2024-01-01", "2025-06-01", 49344, "crypto", "ETH"),
            ("MULTI_1h", "Multi-Crypto 1H", "BTCUSDT,ETHUSDT,SOLUSDT", "1h", "crypto", "2023-01-01", "2025-06-01", 52560, "crypto", "multi"),
        ]
        count = 0
        for s in samples:
            ds_id, name, symbol, freq, asset_type, start, end, rows, tag, _ = s
            if ds_id in self._datasets:
                continue
            symbols_list = [sym.strip() for sym in symbol.split(",") if sym.strip()]
            ds = Dataset(
                name=name,
                symbols=symbols_list,
                frequency=freq,
                description=f"{name} sample dataset",
                tags=[tag],
                asset_type=asset_type,
                is_ohlcv=True,
            )
            ds.dataset_id = ds_id
            ds.start_date = start
            ds.end_date = end
            ds.storage_format = "parquet"
            ds.schema = {
                "columns": [
                    {"name": "open", "dtype": "float64", "role": "price", "description": "Open price"},
                    {"name": "high", "dtype": "float64", "role": "price", "description": "High price"},
                    {"name": "low", "dtype": "float64", "role": "price", "description": "Low price"},
                    {"name": "close", "dtype": "float64", "role": "price", "description": "Close price"},
                    {"name": "volume", "dtype": "float64", "role": "volume", "description": "Volume"},
                ],
                "column_names": ["open", "high", "low", "close", "volume"],
                "has_ohlcv": True,
            }
            ds.coverage = f"{start} ~ {end}"
            self._datasets[ds_id] = ds
            if self._persist and self._store:
                # 生成模拟 OHLCV 数据并保存到 Parquet
                df = self._generate_sample_ohlcv(symbols_list, freq, start, end)
                ds.set_data(df)
                self._parquet.save_dataset_data(ds_id, df)
                self._store.save_dataset(ds.to_dict(), has_data=True)
            count += 1
        logger.info(f"Seeded {count} sample datasets")
        return count

    def _generate_sample_ohlcv(
        self, symbols: List[str], freq: str, start: str, end: str
    ) -> pd.DataFrame:
        """生成模拟 OHLCV 数据（用于示例数据集）"""
        freq_map = {"5m": "5min", "15m": "15min", "1h": "1H", "4h": "4H", "1d": "1D"}
        pd_freq = freq_map.get(freq, "1H")
        # 限制行数，避免生成过多数据
        max_rows = 2000
        dates = pd.date_range(start=start, end=end, freq=pd_freq)
        if len(dates) > max_rows:
            dates = dates[-max_rows:]
        rows = []
        for sym in symbols:
            base_price = 100.0 if sym != "BTCUSDT" else 30000.0
            # 随机游走 + 轻微趋势
            np.random.seed(hash(sym) % 2**31)
            returns = np.random.normal(0.0002, 0.02, len(dates))
            prices = base_price * np.exp(np.cumsum(returns))
            for i, dt in enumerate(dates):
                close = prices[i]
                open_ = close * (1 + np.random.uniform(-0.005, 0.005))
                high = max(open_, close) * (1 + np.random.uniform(0, 0.01))
                low = min(open_, close) * (1 - np.random.uniform(0, 0.01))
                volume = np.random.uniform(1e6, 1e8)
                rows.append({
                    "symbol": sym,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                })
        df = pd.DataFrame(rows, index=pd.DatetimeIndex(dates.repeat(len(symbols)), name="trade_date"))
        return df

    def load_dataset_data(self, dataset_id: str) -> bool:
        """从 Parquet 加载 Dataset 数据到内存（按需加载）"""
        if not self._parquet:
            return False
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        df = self._parquet.load_dataset_data(dataset_id)
        if df is None:
            return False
        ds.set_data(df)
        self._infer_symbols(ds, df)
        return True


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_dataset_manager: Optional[DatasetManager] = None


def get_dataset_manager(persist: bool = True) -> DatasetManager:
    """
    获取 DatasetManager 单例。

    Args:
        persist: 是否开启 SQLite + Parquet 持久化（默认 True）
                 首次创建时会自动从 DB 恢复已有 Dataset 元信息
                 如果 DB 为空则注入示例数据
    """
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager(persist=persist)
        if persist:
            _dataset_manager.load_from_store()
            # 注入示例数据集（只添加不存在的）
            _dataset_manager.seed_sample_datasets()
    return _dataset_manager
