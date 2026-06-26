"""验证迁移脚本的表结构。"""
import os
import sqlite3
import subprocess
import sys

import pytest

DB_PATH = os.path.abspath("storage/test_research_with_legacy.db")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture(autouse=True)
def _setup_test_db():
    """每个测试前：删除旧 DB → 创建空 DB → 迁移新 DB（产生备份）。"""
    import glob
    # 清理
    for f in [DB_PATH] + glob.glob(f"{DB_PATH}.backup_*") + glob.glob(f"{DB_PATH}.pre_restore_*"):
        if os.path.exists(f):
            os.remove(f)
    # 创建空 DB 文件，让迁移脚本可以备份
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "wb") as fp:
        fp.write(b"")  # 空文件，sqlite3 会初始化
    # 执行迁移
    result = subprocess.run(
        [sys.executable, "scripts/migrate_research_os.py", "--db-path", DB_PATH],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, f"Setup migrate failed: {result.stderr}"
    yield
    # 清理
    for f in [DB_PATH] + glob.glob(f"{DB_PATH}.backup_*") + glob.glob(f"{DB_PATH}.pre_restore_*"):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def test_new_tables_created():
    """迁移后应包含 9 张新表。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()

    expected = {
        "research_graphs", "research_runs", "research_cache",
        "research_node_registry", "research_changesets", "research_state",
        "research_materialized", "universes", "calendars",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"


def test_idempotent():
    """二次执行应全部 SKIP，不报错。"""
    result = subprocess.run(
        [sys.executable, "scripts/migrate_research_os.py", "--db-path", DB_PATH],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, f"Second migrate failed: {result.stderr}"
    assert "SKIP (exists)" in result.stdout


def test_backup_created():
    """迁移后应有备份文件。"""
    import glob
    backups = glob.glob(f"{DB_PATH}.backup_*")
    assert len(backups) > 0, "No backup file created"


def test_restore():
    """回滚脚本可还原。"""
    import glob
    backups = sorted(glob.glob(f"{DB_PATH}.backup_*"))
    assert backups, "No backup to restore from"
    latest = backups[-1]

    result = subprocess.run(
        [sys.executable, "scripts/restore_backup.py",
         "--db-path", DB_PATH, "--backup", latest, "--force"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, f"Restore failed: {result.stderr}"
    assert "Restored" in result.stdout
