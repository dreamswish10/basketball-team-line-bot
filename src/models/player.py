#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Optional


class Player:
    """球員資料模型類"""

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
        """轉換為字典格式"""
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

    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        """從字典建立 Player 實例"""
        # 支援 MongoDB document 格式
        if 'skills' in data:
            return cls(
                user_id=data['user_id'],
                name=data['name'],
                shooting_skill=data['skills']['shooting'],
                defense_skill=data['skills']['defense'],
                stamina=data['skills']['stamina'],
                created_at=data.get('created_at', datetime.now()).isoformat() if isinstance(
                    data.get('created_at'), datetime) else data.get('created_at'),
                source_group=data.get('source_group_id'),
                is_registered=data.get('is_registered', True)
            )
        # 支援舊的 SQLite 格式
        else:
            return cls(
                user_id=data['user_id'],
                name=data['name'],
                shooting_skill=data.get('shooting_skill', 5),
                defense_skill=data.get('defense_skill', 5),
                stamina=data.get('stamina', 5),
                created_at=data.get('created_at'),
                source_group=data.get('source_group'),
                is_registered=data.get('is_registered', True)
            )

    def __str__(self):
        source = "群組成員" if not self.is_registered else "已註冊"
        return f"{self.name} ({source}) (投籃:{self.shooting_skill}, 防守:{self.defense_skill}, 體力:{self.stamina}, 總評:{self.overall_rating:.1f})"


class Group:
    """群組資料模型類"""

    def __init__(self, group_id: str, group_name: str = None, created_at: str = None):
        self.group_id = group_id
        self.group_name = group_name or f"群組_{group_id[:8]}"
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'group_id': self.group_id,
            'group_name': self.group_name,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Group':
        """從字典建立 Group 實例"""
        return cls(
            group_id=data['group_id'],
            group_name=data.get('group_name'),
            created_at=data.get('created_at', datetime.now()).isoformat() if isinstance(
                data.get('created_at'), datetime) else data.get('created_at')
        )


class GroupMember:
    """群組成員資料模型類"""

    def __init__(self, group_id: str, user_id: str, display_name: str,
                 is_active: bool = True, joined_at: str = None):
        self.group_id = group_id
        self.user_id = user_id
        self.display_name = display_name
        self.is_active = is_active
        self.joined_at = joined_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'joined_at': self.joined_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GroupMember':
        """從字典建立 GroupMember 實例"""
        return cls(
            group_id=data['group_id'],
            user_id=data['user_id'],
            display_name=data['display_name'],
            is_active=data.get('is_active', True),
            joined_at=data.get('joined_at', datetime.now()).isoformat() if isinstance(
                data.get('joined_at'), datetime) else data.get('joined_at')
        )
