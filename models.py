#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime
from typing import List, Optional

DATABASE_NAME = 'basketball_teams.db'

class Player:
    def __init__(self, user_id: str, name: str, shooting_skill: int = 5, 
                 defense_skill: int = 5, stamina: int = 5, created_at: str = None,
                 source_group: str = None, is_registered: bool = True):
        self.user_id = user_id
        self.name = name
        self.shooting_skill = max(1, min(10, shooting_skill))  # 限制在 1-10 範圍
        self.defense_skill = max(1, min(10, defense_skill))
        self.stamina = max(1, min(10, stamina))
        self.created_at = created_at or datetime.now().isoformat()
        self.source_group = source_group  # 來源群組 ID
        self.is_registered = is_registered  # 是否為正式註冊（vs 群組成員）
    
    @property
    def overall_rating(self) -> float:
        """計算球員總體評分"""
        return (self.shooting_skill + self.defense_skill + self.stamina) / 3
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'shooting_skill': self.shooting_skill,
            'defense_skill': self.defense_skill,
            'stamina': self.stamina,
            'overall_rating': self.overall_rating,
            'created_at': self.created_at,
            'source_group': self.source_group,
            'is_registered': self.is_registered
        }
    
    def __str__(self):
        source = "群組成員" if not self.is_registered else "已註冊"
        return f"{self.name} ({source}) (投籃:{self.shooting_skill}, 防守:{self.defense_skill}, 體力:{self.stamina}, 總評:{self.overall_rating:.1f})"

class Group:
    def __init__(self, group_id: str, group_name: str = None, created_at: str = None):
        self.group_id = group_id
        self.group_name = group_name or f"群組_{group_id[:8]}"
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'created_at': self.created_at
        }

class GroupMember:
    def __init__(self, group_id: str, user_id: str, display_name: str, 
                 is_active: bool = True, joined_at: str = None):
        self.group_id = group_id
        self.user_id = user_id
        self.display_name = display_name
        self.is_active = is_active
        self.joined_at = joined_at or datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'joined_at': self.joined_at
        }

class PlayerDatabase:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DATABASE_NAME)
    
    @staticmethod
    def create_player(player: Player) -> bool:
        """新增球員"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO players 
                    (user_id, name, shooting_skill, defense_skill, stamina, created_at, source_group, is_registered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (player.user_id, player.name, player.shooting_skill, 
                      player.defense_skill, player.stamina, player.created_at,
                      player.source_group, player.is_registered))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating player: {e}")
            return False
    
    @staticmethod
    def get_player(user_id: str) -> Optional[Player]:
        """根據 user_id 獲取球員"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, name, shooting_skill, defense_skill, stamina, created_at, source_group, is_registered
                    FROM players WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                if row:
                    return Player(*row)
                return None
        except Exception as e:
            print(f"Error getting player: {e}")
            return None
    
    @staticmethod
    def get_all_players() -> List[Player]:
        """獲取所有球員"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, name, shooting_skill, defense_skill, stamina, created_at, source_group, is_registered
                    FROM players ORDER BY is_registered DESC, created_at DESC
                ''')
                rows = cursor.fetchall()
                return [Player(*row) for row in rows]
        except Exception as e:
            print(f"Error getting all players: {e}")
            return []
    
    @staticmethod
    def delete_player(user_id: str) -> bool:
        """刪除球員"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM players WHERE user_id = ?', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting player: {e}")
            return False
    
    @staticmethod
    def get_player_count() -> int:
        """獲取球員總數"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM players')
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting player count: {e}")
            return 0
    
    @staticmethod
    def get_group_players(group_id: str) -> List[Player]:
        """獲取特定群組的所有球員（包括註冊和群組成員）"""
        try:
            with PlayerDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, name, shooting_skill, defense_skill, stamina, created_at, source_group, is_registered
                    FROM players WHERE source_group = ? ORDER BY is_registered DESC, created_at DESC
                ''', (group_id,))
                rows = cursor.fetchall()
                return [Player(*row) for row in rows]
        except Exception as e:
            print(f"Error getting group players: {e}")
            return []

class GroupDatabase:
    @staticmethod
    def get_connection():
        return PlayerDatabase.get_connection()
    
    @staticmethod
    def create_group(group: Group) -> bool:
        """新增群組"""
        try:
            with GroupDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO groups 
                    (group_id, group_name, created_at)
                    VALUES (?, ?, ?)
                ''', (group.group_id, group.group_name, group.created_at))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating group: {e}")
            return False
    
    @staticmethod
    def add_group_member(member: GroupMember) -> bool:
        """新增群組成員"""
        try:
            with GroupDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO group_members 
                    (group_id, user_id, display_name, is_active, joined_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (member.group_id, member.user_id, member.display_name, 
                      member.is_active, member.joined_at))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding group member: {e}")
            return False
    
    @staticmethod
    def get_group_members(group_id: str) -> List[GroupMember]:
        """獲取群組所有成員"""
        try:
            with GroupDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT group_id, user_id, display_name, is_active, joined_at
                    FROM group_members WHERE group_id = ? AND is_active = 1
                    ORDER BY joined_at ASC
                ''', (group_id,))
                rows = cursor.fetchall()
                return [GroupMember(*row) for row in rows]
        except Exception as e:
            print(f"Error getting group members: {e}")
            return []
    
    @staticmethod
    def remove_group_member(group_id: str, user_id: str) -> bool:
        """移除群組成員（設為非活動）"""
        try:
            with GroupDatabase.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE group_members SET is_active = 0 
                    WHERE group_id = ? AND user_id = ?
                ''', (group_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing group member: {e}")
            return False

def init_db():
    """初始化資料庫"""
    with PlayerDatabase.get_connection() as conn:
        cursor = conn.cursor()
        
        # 創建球員表（更新版本支援群組功能）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                shooting_skill INTEGER NOT NULL CHECK (shooting_skill >= 1 AND shooting_skill <= 10),
                defense_skill INTEGER NOT NULL CHECK (defense_skill >= 1 AND defense_skill <= 10),
                stamina INTEGER NOT NULL CHECK (stamina >= 1 AND stamina <= 10),
                created_at TEXT NOT NULL,
                source_group TEXT DEFAULT NULL,
                is_registered BOOLEAN DEFAULT 1
            )
        ''')
        
        # 創建群組表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # 創建群組成員表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                joined_at TEXT NOT NULL,
                UNIQUE(group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups (group_id)
            )
        ''')
        
        # 創建分隊記錄表（擴展支援群組）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_data TEXT NOT NULL,
                group_id TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups (group_id)
            )
        ''')
        
        # 為舊資料添加新欄位（如果不存在）
        try:
            cursor.execute('ALTER TABLE players ADD COLUMN source_group TEXT DEFAULT NULL')
        except sqlite3.OperationalError:
            pass  # 欄位已存在
        
        try:
            cursor.execute('ALTER TABLE players ADD COLUMN is_registered BOOLEAN DEFAULT 1')
        except sqlite3.OperationalError:
            pass  # 欄位已存在
            
        conn.commit()

# 測試功能
if __name__ == "__main__":
    init_db()
    
    # 測試資料
    test_player = Player("test_user_123", "測試球員", 8, 7, 6)
    print(f"創建測試球員: {test_player}")
    
    # 測試資料庫操作
    if PlayerDatabase.create_player(test_player):
        print("球員創建成功")
        
        retrieved_player = PlayerDatabase.get_player("test_user_123")
        if retrieved_player:
            print(f"獲取球員: {retrieved_player}")
        
        all_players = PlayerDatabase.get_all_players()
        print(f"總共有 {len(all_players)} 位球員")
        
        PlayerDatabase.delete_player("test_user_123")
        print("測試球員已刪除")