#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite 到 MongoDB 資料遷移腳本

使用方法:
  python scripts/migrate_sqlite_to_mongodb.py --dry-run    # 測試模式
  python scripts/migrate_sqlite_to_mongodb.py              # 正式遷移
"""

import sqlite3
import sys
import os
from datetime import datetime
from argparse import ArgumentParser

# 將專案根目錄加入 Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb import get_database, init_mongodb
from src.models.mongodb_models import (
    PlayersRepository,
    GroupsRepository,
    GroupMembersRepository
)


class SQLiteToMongoMigration:
    """SQLite 到 MongoDB 資料遷移類"""

    def __init__(self, sqlite_db_path: str, dry_run: bool = False):
        self.sqlite_db_path = sqlite_db_path
        self.dry_run = dry_run
        self.stats = {
            'players': 0,
            'groups': 0,
            'group_members': 0
        }

    def connect_sqlite(self):
        """連接到 SQLite 資料庫"""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row  # 使用字典形式存取欄位
            print(f"✓ Connected to SQLite: {self.sqlite_db_path}")
            return conn
        except Exception as e:
            print(f"✗ Failed to connect to SQLite: {e}")
            sys.exit(1)

    def migrate_players(self, sqlite_conn, players_repo: PlayersRepository):
        """遷移球員資料"""
        print("\n[1/3] Migrating players...")

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM players")
        rows = cursor.fetchall()

        print(f"  Found {len(rows)} players in SQLite")

        for row in rows:
            user_id = row['user_id']
            name = row['name']
            shooting_skill = row['shooting_skill']
            defense_skill = row['defense_skill']
            stamina = row['stamina']
            source_group = row.get('source_group')
            is_registered = bool(row.get('is_registered', 1))

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate player: {name} ({user_id})")
            else:
                success = players_repo.create(
                    user_id=user_id,
                    name=name,
                    shooting_skill=shooting_skill,
                    defense_skill=defense_skill,
                    stamina=stamina,
                    source_group_id=source_group,
                    is_registered=is_registered
                )

                if success:
                    self.stats['players'] += 1
                    print(f"  ✓ Migrated player: {name} ({user_id})")
                else:
                    print(f"  ✗ Failed to migrate player: {name} ({user_id})")

        print(f"  Migrated {self.stats['players']}/{len(rows)} players")

    def migrate_groups(self, sqlite_conn, groups_repo: GroupsRepository):
        """遷移群組資料"""
        print("\n[2/3] Migrating groups...")

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM groups")
        rows = cursor.fetchall()

        print(f"  Found {len(rows)} groups in SQLite")

        for row in rows:
            group_id = row['group_id']
            group_name = row['group_name']

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate group: {group_name} ({group_id})")
            else:
                success = groups_repo.create(
                    group_id=group_id,
                    group_name=group_name
                )

                if success:
                    self.stats['groups'] += 1
                    print(f"  ✓ Migrated group: {group_name} ({group_id})")
                else:
                    print(f"  ✗ Failed to migrate group: {group_name} ({group_id})")

        print(f"  Migrated {self.stats['groups']}/{len(rows)} groups")

    def migrate_group_members(self, sqlite_conn, group_members_repo: GroupMembersRepository):
        """遷移群組成員資料"""
        print("\n[3/3] Migrating group members...")

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM group_members")
        rows = cursor.fetchall()

        print(f"  Found {len(rows)} group members in SQLite")

        for row in rows:
            group_id = row['group_id']
            user_id = row['user_id']
            display_name = row['display_name']
            is_active = bool(row.get('is_active', 1))

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate member: {display_name} in group {group_id}")
            else:
                # 只遷移活躍成員
                if is_active:
                    success = group_members_repo.add(
                        group_id=group_id,
                        user_id=user_id,
                        display_name=display_name
                    )

                    if success:
                        self.stats['group_members'] += 1
                        print(f"  ✓ Migrated member: {display_name} to {group_id}")
                    else:
                        print(f"  ✗ Failed to migrate member: {display_name}")
                else:
                    print(f"  ⊘ Skipped inactive member: {display_name}")

        print(f"  Migrated {self.stats['group_members']}/{len(rows)} group members")

    def run(self):
        """執行完整遷移流程"""
        print("=" * 60)
        print("SQLite to MongoDB Migration Tool")
        print("=" * 60)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made to MongoDB\n")
        else:
            print("\n⚠️  LIVE MODE - Data will be migrated to MongoDB\n")

        # 連接到 SQLite
        sqlite_conn = self.connect_sqlite()

        # 初始化 MongoDB
        try:
            init_mongodb()
            db = get_database()
            print("✓ Connected to MongoDB")
        except Exception as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            sys.exit(1)

        # 創建 repositories
        players_repo = PlayersRepository(db)
        groups_repo = GroupsRepository(db)
        group_members_repo = GroupMembersRepository(db)

        # 執行遷移
        try:
            self.migrate_players(sqlite_conn, players_repo)
            self.migrate_groups(sqlite_conn, groups_repo)
            self.migrate_group_members(sqlite_conn, group_members_repo)

            # 總結
            print("\n" + "=" * 60)
            print("Migration Summary")
            print("=" * 60)
            print(f"  Players migrated:       {self.stats['players']}")
            print(f"  Groups migrated:        {self.stats['groups']}")
            print(f"  Group members migrated: {self.stats['group_members']}")
            print("=" * 60)

            if self.dry_run:
                print("\n✓ Dry run completed successfully")
                print("  Run without --dry-run to perform actual migration")
            else:
                print("\n✓ Migration completed successfully")

        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            sys.exit(1)
        finally:
            sqlite_conn.close()


def main():
    """主函數"""
    parser = ArgumentParser(description="Migrate data from SQLite to MongoDB")
    parser.add_argument(
        '--sqlite-db',
        default='basketball_teams.db',
        help='Path to SQLite database file (default: basketball_teams.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without making changes to MongoDB'
    )

    args = parser.parse_args()

    # 檢查 SQLite 檔案是否存在
    if not os.path.exists(args.sqlite_db):
        print(f"✗ SQLite database not found: {args.sqlite_db}")
        print("  Please ensure the database file exists")
        sys.exit(1)

    # 執行遷移
    migration = SQLiteToMongoMigration(
        sqlite_db_path=args.sqlite_db,
        dry_run=args.dry_run
    )
    migration.run()


if __name__ == "__main__":
    main()
