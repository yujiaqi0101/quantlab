"""
Research OS 数据库迁移脚本
==========================

一次性将旧 ML Lab DB 迁移到 Research OS Schema：

  1. 备份 ml_lab.db → ml_lab.db.backup_<timestamp>
  2. 新建 7 张 research_* 表 + 2 张 universe/calendar 表
  3. ALTER datasets 表（dataset_type / calendar_id / adjustment）
  4. ALTER training_jobs 表（research_graph_id / label_node_id / materialize_config_json / materialized_dataset_id）
  5. 重命名 feature_sets → feature_sets_deprecated、label_sets → label_sets_deprecated

幂等：表已存在则跳过，列已存在则跳过。

用法：
    python scripts/migrate_research_os.py [--db-path storage/ml_lab.db] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import time
from typing import List


# ---------- 新表 DDL ----------

NEW_TABLES_DDL: List[str] = [
    # ---- Research 核心表 ----
    """
    CREATE TABLE IF NOT EXISTS research_graphs (
        graph_id        TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        description     TEXT DEFAULT '',
        nodes_json      TEXT DEFAULT '[]',     -- [{id, category, version, params}]
        edges_json      TEXT DEFAULT '[]',     -- [{src_node, src_port, dst_node, dst_port}]
        fingerprint     TEXT DEFAULT '',
        created_at      TEXT DEFAULT '',
        updated_at      TEXT DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_runs (
        run_id          TEXT PRIMARY KEY,
        graph_id        TEXT NOT NULL,
        dataset_id      TEXT DEFAULT '',
        status          TEXT DEFAULT 'PENDING',  -- PENDING / RUNNING / OK / ERROR
        mode            TEXT DEFAULT 'sequential',
        outputs_json    TEXT DEFAULT '{}',
        executed_json   TEXT DEFAULT '[]',
        cached_json     TEXT DEFAULT '[]',
        errors_json     TEXT DEFAULT '{}',
        started_at      TEXT DEFAULT '',
        finished_at     TEXT DEFAULT '',
        duration_ms     INTEGER DEFAULT 0,
        FOREIGN KEY (graph_id) REFERENCES research_graphs(graph_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_cache (
        cache_key       TEXT PRIMARY KEY,
        node_id         TEXT NOT NULL,
        version         TEXT DEFAULT '1.0.0',
        fingerprint     TEXT DEFAULT '',
        cache_level     TEXT DEFAULT 'memory',  -- memory / parquet / featurestore / artifact / redis
        size_bytes      INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT '',
        last_hit_at     TEXT DEFAULT '',
        hit_count       INTEGER DEFAULT 0,
        payload_path    TEXT DEFAULT ''          -- parquet/artifact 文件路径
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_node_registry (
        node_id         TEXT NOT NULL,
        version         TEXT NOT NULL,
        category        TEXT DEFAULT 'custom',
        class_name      TEXT DEFAULT '',
        module          TEXT DEFAULT '',
        manifest_json   TEXT DEFAULT '{}',
        registered_at   TEXT DEFAULT '',
        deprecated      INTEGER DEFAULT 0,
        PRIMARY KEY (node_id, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_changesets (
        changeset_id    TEXT PRIMARY KEY,
        source          TEXT DEFAULT '',         -- dataset / cache / manual
        op              TEXT DEFAULT '',         -- append / update / delete
        affected_json   TEXT DEFAULT '[]',       -- 影响的 node_id 列表
        created_at      TEXT DEFAULT '',
        applied_at      TEXT DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_state (
        state_key       TEXT PRIMARY KEY,
        node_id         TEXT NOT NULL,
        state_json      TEXT DEFAULT '{}',
        updated_at      TEXT DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS research_materialized (
        materialized_id TEXT PRIMARY KEY,
        graph_id        TEXT NOT NULL,
        dataset_id      TEXT DEFAULT '',
        label_node_id   TEXT DEFAULT '',
        feature_node_ids_json TEXT DEFAULT '[]',
        n_train         INTEGER DEFAULT 0,
        n_val           INTEGER DEFAULT 0,
        n_test          INTEGER DEFAULT 0,
        feature_names_json TEXT DEFAULT '[]',
        label_name      TEXT DEFAULT '',
        normalize_params_json TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT '',
        FOREIGN KEY (graph_id) REFERENCES research_graphs(graph_id)
    )
    """,
    # ---- Universe / Calendar ----
    """
    CREATE TABLE IF NOT EXISTS universes (
        universe_id     TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        description     TEXT DEFAULT '',
        type            TEXT DEFAULT 'static',   -- static / dynamic
        symbols_json    TEXT DEFAULT '[]',      -- static 模式
        rule_json       TEXT DEFAULT '{}',      -- dynamic 模式
        created_at      TEXT DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calendars (
        calendar_id     TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        description     TEXT DEFAULT '',
        timezone        TEXT DEFAULT 'UTC',
        sessions_json   TEXT DEFAULT '[]',       -- 交易日列表
        created_at      TEXT DEFAULT ''
    )
    """,
]


# ---------- datasets / training_jobs ALTER ----------

DATASETS_NEW_COLUMNS = [
    ("dataset_type", "TEXT DEFAULT 'panel'"),    # panel / timeseries / cross_section
    ("calendar_id", "TEXT DEFAULT ''"),
    ("adjustment", "TEXT DEFAULT 'none'"),       # none / forward / backward
]

TRAINING_JOBS_NEW_COLUMNS = [
    ("research_graph_id", "TEXT DEFAULT ''"),
    ("label_node_id", "TEXT DEFAULT ''"),
    ("feature_node_ids_json", "TEXT DEFAULT '[]'"),
    ("materialize_config_json", "TEXT DEFAULT '{}'"),
    ("materialized_dataset_id", "TEXT DEFAULT ''"),
]


# ---------- 主流程 ----------

def backup_db(db_path: str) -> str:
    """备份 DB 文件，返回备份路径。"""
    if not os.path.exists(db_path):
        print(f"[WARN] DB file not found: {db_path} (skip backup)")
        return ""
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{ts}"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Backup: {db_path} -> {backup_path}")
    return backup_path


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def migrate(db_path: str, dry_run: bool = False) -> None:
    print(f"\n=== Research OS Migration ===")
    print(f"DB: {db_path}")
    print(f"Dry run: {dry_run}")

    # 1. 备份
    if not dry_run:
        backup_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 2. 新建表
    print("\n[1/4] Creating new tables...")
    import re
    for ddl in NEW_TABLES_DDL:
        m = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", ddl)
        table_name = m.group(1) if m else "?"
        already = table_exists(cur, table_name)
        if not dry_run:
            cur.executescript(ddl)
        status = "SKIP (exists)" if already else "CREATED"
        print(f"  - {table_name}: {status}")

    # 3. ALTER datasets
    print("\n[2/4] ALTER datasets table...")
    if not table_exists(cur, "datasets"):
        print("  - SKIP (datasets table not found)")
    else:
        for col, col_def in DATASETS_NEW_COLUMNS:
            if column_exists(cur, "datasets", col):
                print(f"  - datasets.{col}: SKIP (exists)")
            else:
                if not dry_run:
                    cur.execute(f"ALTER TABLE datasets ADD COLUMN {col} {col_def}")
                print(f"  - datasets.{col}: ADDED")

    # 4. ALTER training_jobs
    print("\n[3/4] ALTER training_jobs table...")
    if not table_exists(cur, "training_jobs"):
        print("  - SKIP (training_jobs table not found)")
    else:
        for col, col_def in TRAINING_JOBS_NEW_COLUMNS:
            if column_exists(cur, "training_jobs", col):
                print(f"  - training_jobs.{col}: SKIP (exists)")
            else:
                if not dry_run:
                    cur.execute(f"ALTER TABLE training_jobs ADD COLUMN {col} {col_def}")
                print(f"  - training_jobs.{col}: ADDED")

    # 5. 重命名旧表 (feature_sets → feature_sets_deprecated)
    print("\n[4/4] Renaming deprecated tables...")
    for old_name, new_name in [
        ("feature_sets", "feature_sets_deprecated"),
        ("label_sets", "label_sets_deprecated"),
    ]:
        if table_exists(cur, old_name) and not table_exists(cur, new_name):
            if not dry_run:
                cur.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
            print(f"  - {old_name} -> {new_name}: RENAMED")
        elif table_exists(cur, new_name):
            print(f"  - {old_name} -> {new_name}: SKIP (target exists)")
        else:
            print(f"  - {old_name}: SKIP (not found)")

    if not dry_run:
        conn.commit()
    conn.close()

    print("\n=== Migration Complete ===\n")


def main():
    parser = argparse.ArgumentParser(description="Research OS DB Migration")
    parser.add_argument("--db-path", default="storage/ml_lab.db", help="SQLite DB path")
    parser.add_argument("--dry-run", action="store_true", help="只打印不执行")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    if not os.path.exists(os.path.dirname(db_path) or "."):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    migrate(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
