#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime
from typing import List, Optional

DATABASE_NAME = 'basketball_teams.db'

class Player:
    def __init__(self, user_id: str, name: str, shooting_skill: int = 5, 
                 defense_skill: int = 5, stamina: int = 5, created_at: str = None):
        self.user_id = user_id
        self.name = name
        self.shooting_skill = max(1, min(10, shooting_skill))  # 限制在 1-10 範圍
        self.defense_skill = max(1, min(10, defense_skill))
        self.stamina = max(1, min(10, stamina))
        self.created_at = created_at or datetime.now().isoformat()
    
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
            'created_at': self.created_at
        }
    
    def __str__(self):
        return f"{self.name} (投籃:{self.shooting_skill}, 防守:{self.defense_skill}, 體力:{self.stamina}, 總評:{self.overall_rating:.1f})"

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
                    (user_id, name, shooting_skill, defense_skill, stamina, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (player.user_id, player.name, player.shooting_skill, 
                      player.defense_skill, player.stamina, player.created_at))
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
                    SELECT user_id, name, shooting_skill, defense_skill, stamina, created_at
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
                    SELECT user_id, name, shooting_skill, defense_skill, stamina, created_at
                    FROM players ORDER BY created_at DESC
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

def init_db():
    """初始化資料庫"""
    with PlayerDatabase.get_connection() as conn:
        cursor = conn.cursor()
        
        # 創建球員表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                shooting_skill INTEGER NOT NULL CHECK (shooting_skill >= 1 AND shooting_skill <= 10),
                defense_skill INTEGER NOT NULL CHECK (defense_skill >= 1 AND defense_skill <= 10),
                stamina INTEGER NOT NULL CHECK (stamina >= 1 AND stamina <= 10),
                created_at TEXT NOT NULL
            )
        ''')
        
        # 創建分隊記錄表（可選，用於記錄歷史分隊）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
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