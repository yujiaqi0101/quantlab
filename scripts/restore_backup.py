"""
Research OS 回滚脚本
======================

一键从备份还原 DB。

用法：
    python scripts/restore_backup.py --backup storage/ml_lab.db.backup_20260626_120000
    python scripts/restore_backup.py --latest                  # 用最近一次备份
    python scripts/restore_backup.py --list                     # 列出所有备份
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys


def list_backups(db_path: str) -> list:
    """列出所有备份文件（按时间倒序）。"""
    pattern = f"{db_path}.backup_*"
    backups = sorted(glob.glob(pattern), reverse=True)
    return backups


def find_latest_backup(db_path: str) -> str:
    backups = list_backups(db_path)
    return backups[0] if backups else ""


def restore(backup_path: str, db_path: str, force: bool = False) -> None:
    print(f"=== Restore DB ===")
    print(f"Backup: {backup_path}")
    print(f"Target: {db_path}")

    if not os.path.exists(backup_path):
        print(f"[ERROR] Backup not found: {backup_path}")
        sys.exit(1)

    if os.path.exists(db_path) and not force:
        # 自动再备份一次当前 DB（防止误操作）
        auto_backup = f"{db_path}.pre_restore_{os.path.basename(backup_path)}"
        shutil.copy2(db_path, auto_backup)
        print(f"[OK] Auto-backup current DB -> {auto_backup}")

    shutil.copy2(backup_path, db_path)
    print(f"[OK] Restored: {backup_path} -> {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Restore DB from backup")
    parser.add_argument("--db-path", default="storage/ml_lab.db")
    parser.add_argument("--backup", default="", help="指定备份文件路径")
    parser.add_argument("--latest", action="store_true", help="用最近一次备份")
    parser.add_argument("--list", action="store_true", help="列出所有备份")
    parser.add_argument("--force", action="store_true", help="跳过自动备份")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)

    if args.list:
        backups = list_backups(db_path)
        if not backups:
            print("No backups found.")
            return
        print(f"Backups for {db_path}:")
        for b in backups:
            size = os.path.getsize(b) / 1024
            print(f"  - {b}  ({size:.1f} KB)")
        return

    backup_path = args.backup
    if args.latest or not backup_path:
        backup_path = find_latest_backup(db_path)
        if not backup_path:
            print(f"[ERROR] No backup found for {db_path}")
            sys.exit(1)
        print(f"[INFO] Using latest backup: {backup_path}")

    restore(backup_path, db_path, force=args.force)


if __name__ == "__main__":
    main()
