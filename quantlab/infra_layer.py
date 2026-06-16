"""
QuantLab V2.0 — Infrastructure Layer

基础设施：事件/存储/缓存/队列/数据库

所有基础设施组件集中管理。
上层（services/research/studio）通过本模块访问基础设施。
"""

# --- Event Bus ---
from .event.event_bus import EventBus
from .event.event_types import Event, MarketEvent, SignalEvent

# --- Storage ---
from .research.database import Database
from .research.artifact import ArtifactStore, Artifact
from .research.cache import ResearchCache

# --- Data ---
from .data.cache import factor_cache
from .data.datasource import DataSource
from .data.dataset_loader import DataLoader

# --- Task Queue ---
from .runtime.task_manager import TaskManager, TaskCallback

# --- Dataset ---
from .dataset.catalog import DataCatalog
from .dataset.loader import CSVLoader, ParquetLoader
from .dataset.registry import DatasetRegistry

__infra_all__ = [
    "EventBus", "Event", "MarketEvent", "SignalEvent",
    "Database", "ArtifactStore", "Artifact", "ResearchCache",
    "factor_cache", "DataSource", "DataLoader",
    "TaskManager", "TaskCallback",
    "DatasetCatalog", "CSVLoader", "ParquetLoader", "DatasetRegistry",
]
