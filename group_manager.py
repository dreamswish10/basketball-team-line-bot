#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
群組管理模組 - 處理 LINE 群組成員管理和分隊功能
"""

from typing import List, Optional, Dict
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from models import Player, Group, GroupMember, GroupDatabase, PlayerDatabase
import logging

class GroupManager:
    def __init__(self, line_bot_api: LineBotApi):
        self.line_bot_api = line_bot_api
        self.logger = logging.getLogger(__name__)
    
    def register_group(self, group_id: str, group_name: str = None) -> bool:
        """註冊群組到資料庫"""
        try:
            group = Group(group_id, group_name)
            return GroupDatabase.create_group(group)
        except Exception as e:
            self.logger.error(f"Error registering group {group_id}: {e}")
            return False
    
    def fetch_group_members(self, group_id: str) -> List[Dict]:
        """從 LINE API 獲取群組成員清單"""
        try:
            # 獲取群組成員 ID 列表
            member_ids = self.line_bot_api.get_group_member_ids(group_id)
            
            members = []
            for user_id in member_ids:
                try:
                    # 獲取成員個人資料
                    profile = self.line_bot_api.get_group_member_profile(group_id, user_id)
                    members.append({
                        'user_id': user_id,
                        'display_name': profile.display_name,
                        'picture_url': getattr(profile, 'picture_url', None),
                        'status_message': getattr(profile, 'status_message', None)
                    })
                    
                    # 短暫延遲避免 API 限制
                    import time
                    time.sleep(0.1)
                    
                except LineBotApiError as e:
                    self.logger.warning(f"Failed to get profile for user {user_id}: {e}")
                    # 如果無法獲取個人資料，仍然加入成員清單
                    members.append({
                        'user_id': user_id,
                        'display_name': f"成員_{user_id[:8]}",
                        'picture_url': None,
                        'status_message': None
                    })
            
            return members
            
        except LineBotApiError as e:
            self.logger.error(f"Failed to fetch group members: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching group members: {e}")
            return []
    
    def sync_group_members(self, group_id: str) -> int:
        """同步群組成員到資料庫"""
        try:
            # 從 LINE API 獲取最新成員清單
            api_members = self.fetch_group_members(group_id)
            
            if not api_members:
                self.logger.warning(f"No members found for group {group_id}")
                return 0
            
            # 先註冊群組（如果不存在）
            self.register_group(group_id)
            
            synced_count = 0
            for member_data in api_members:
                try:
                    # 添加到群組成員表
                    member = GroupMember(
                        group_id=group_id,
                        user_id=member_data['user_id'],
                        display_name=member_data['display_name']
                    )
                    
                    if GroupDatabase.add_group_member(member):
                        synced_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error syncing member {member_data['user_id']}: {e}")
            
            self.logger.info(f"Synced {synced_count} members for group {group_id}")
            return synced_count
            
        except Exception as e:
            self.logger.error(f"Error syncing group members: {e}")
            return 0
    
    def create_group_players(self, group_id: str, default_skills: Dict = None) -> List[Player]:
        """為群組成員創建球員資料（使用預設技能值）"""
        default_skills = default_skills or {
            'shooting_skill': 5,
            'defense_skill': 5,
            'stamina': 5
        }
        
        try:
            # 獲取群組成員
            group_members = GroupDatabase.get_group_members(group_id)
            
            created_players = []
            for member in group_members:
                # 檢查是否已經有球員資料
                existing_player = PlayerDatabase.get_player(member.user_id)
                
                if existing_player:
                    # 如果已有註冊球員，更新來源群組
                    if not existing_player.source_group:
                        existing_player.source_group = group_id
                        PlayerDatabase.create_player(existing_player)
                    created_players.append(existing_player)
                else:
                    # 創建新的群組成員球員資料
                    player = Player(
                        user_id=member.user_id,
                        name=member.display_name,
                        shooting_skill=default_skills['shooting_skill'],
                        defense_skill=default_skills['defense_skill'],
                        stamina=default_skills['stamina'],
                        source_group=group_id,
                        is_registered=False  # 標記為群組成員而非註冊球員
                    )
                    
                    if PlayerDatabase.create_player(player):
                        created_players.append(player)
            
            return created_players
            
        except Exception as e:
            self.logger.error(f"Error creating group players: {e}")
            return []
    
    def get_group_players_for_team(self, group_id: str, include_registered: bool = True) -> List[Player]:
        """獲取用於分隊的群組球員清單"""
        try:
            if include_registered:
                # 同時獲取註冊球員和群組成員
                all_players = PlayerDatabase.get_all_players()
                group_players = [p for p in all_players if p.source_group == group_id]
            else:
                # 只獲取群組成員
                group_players = PlayerDatabase.get_group_players(group_id)
                group_players = [p for p in group_players if not p.is_registered]
            
            return group_players
            
        except Exception as e:
            self.logger.error(f"Error getting group players: {e}")
            return []
    
    def auto_setup_group_team(self, group_id: str) -> List[Player]:
        """自動設定群組分隊（一鍵式操作）"""
        try:
            # 1. 同步群組成員
            synced_count = self.sync_group_members(group_id)
            self.logger.info(f"Synced {synced_count} members")
            
            # 2. 創建球員資料
            players = self.create_group_players(group_id)
            self.logger.info(f"Created {len(players)} players")
            
            # 3. 返回可用於分隊的球員清單
            return players
            
        except Exception as e:
            self.logger.error(f"Error auto-setting up group team: {e}")
            return []
    
    def get_group_stats(self, group_id: str) -> Dict:
        """獲取群組統計資訊"""
        try:
            group_members = GroupDatabase.get_group_members(group_id)
            group_players = PlayerDatabase.get_group_players(group_id)
            
            registered_players = [p for p in group_players if p.is_registered]
            member_players = [p for p in group_players if not p.is_registered]
            
            stats = {
                'total_members': len(group_members),
                'total_players': len(group_players),
                'registered_players': len(registered_players),
                'member_players': len(member_players),
                'coverage_rate': len(group_players) / len(group_members) if group_members else 0
            }
            
            if group_players:
                stats['avg_rating'] = sum(p.overall_rating for p in group_players) / len(group_players)
                stats['avg_shooting'] = sum(p.shooting_skill for p in group_players) / len(group_players)
                stats['avg_defense'] = sum(p.defense_skill for p in group_players) / len(group_players)
                stats['avg_stamina'] = sum(p.stamina for p in group_players) / len(group_players)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting group stats: {e}")
            return {}
    
    def remove_inactive_members(self, group_id: str) -> int:
        """移除已退出群組的成員"""
        try:
            # 獲取當前 API 成員清單
            current_members = self.fetch_group_members(group_id)
            current_user_ids = {m['user_id'] for m in current_members}
            
            # 獲取資料庫中的成員清單
            db_members = GroupDatabase.get_group_members(group_id)
            
            removed_count = 0
            for db_member in db_members:
                if db_member.user_id not in current_user_ids:
                    # 成員已退出，標記為非活動
                    if GroupDatabase.remove_group_member(group_id, db_member.user_id):
                        removed_count += 1
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error removing inactive members: {e}")
            return 0

# 工具函數
def suggest_group_team_sizes(member_count: int) -> List[tuple]:
    """建議群組分隊方案"""
    suggestions = []
    
    if member_count >= 4:
        # 2隊方案
        team_size = member_count // 2
        suggestions.append((2, f"2隊 (每隊約{team_size}人) - 經典對戰"))
    
    if member_count >= 6:
        # 3隊方案
        team_size = member_count // 3
        suggestions.append((3, f"3隊 (每隊約{team_size}人) - 輪替對戰"))
    
    if member_count >= 8:
        # 4隊方案
        team_size = member_count // 4
        suggestions.append((4, f"4隊 (每隊約{team_size}人) - 淘汰賽"))
    
    return suggestions

if __name__ == "__main__":
    # 測試功能（需要真實的 LINE Bot API token）
    print("群組管理模組已準備就緒")
    print("主要功能：")
    print("1. 同步群組成員")
    print("2. 創建群組球員資料")
    print("3. 群組分隊管理")
    print("4. 群組統計資訊")