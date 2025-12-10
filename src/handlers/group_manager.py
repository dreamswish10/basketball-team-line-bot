#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
群組管理模組 - 處理 LINE 群組成員管理和分隊功能
"""

from typing import List, Optional, Dict
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from src.models.player import Player, Group, GroupMember
from src.models.mongodb_models import (
    PlayersRepository,
    GroupsRepository,
    GroupMembersRepository,
    DivisionsRepository
)
import logging


class GroupManager:
    def __init__(self, line_bot_api: LineBotApi,
                 players_repo: PlayersRepository = None,
                 groups_repo: GroupsRepository = None,
                 group_members_repo: GroupMembersRepository = None,
                 divisions_repo: DivisionsRepository = None):
        self.line_bot_api = line_bot_api
        self.players_repo = players_repo
        self.groups_repo = groups_repo
        self.group_members_repo = group_members_repo
        self.divisions_repo = divisions_repo
        self.logger = logging.getLogger(__name__)

    def register_group(self, group_id: str, group_name: str = None) -> bool:
        """註冊群組到資料庫"""
        try:
            return self.groups_repo.create(group_id, group_name or f"群組_{group_id[:8]}")
        except Exception as e:
            self.logger.error(f"Error registering group {group_id}: {e}")
            return False

    def fetch_group_members(self, group_id: str) -> List[Dict]:
        """從 LINE API 獲取群組成員清單"""
        try:
            # 獲取群組成員 ID 列表
            member_ids = self.line_bot_api.get_group_member_ids(group_id)

            # 記錄獲取到的成員 ID 數量
            self.logger.info(f"[GROUP_MEMBER_FETCH] Group {group_id}: Found {len(member_ids)} members")

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

                    # 記錄每個成功獲取的成員
                    self.logger.info(
                        f"[GROUP_MEMBER_FETCH] ✓ User ID: {user_id}, "
                        f"Display Name: {profile.display_name}"
                    )

                    # 短暫延遲避免 API 限制
                    import time
                    time.sleep(0.1)

                except LineBotApiError as e:
                    self.logger.warning(f"Failed to get profile for user {user_id}: {e}")
                    # 如果無法獲取個人資料，仍然加入成員清單
                    fallback_name = f"成員_{user_id[:8]}"
                    members.append({
                        'user_id': user_id,
                        'display_name': fallback_name,
                        'picture_url': None,
                        'status_message': None
                    })

                    # 記錄使用備用名稱的成員
                    self.logger.warning(
                        f"[GROUP_MEMBER_FETCH] ⚠ User ID: {user_id}, "
                        f"Display Name: {fallback_name} (fallback)"
                    )

            # 總結日誌
            self.logger.info(
                f"[GROUP_MEMBER_FETCH] Group {group_id}: "
                f"Successfully fetched {len(members)} member profiles"
            )

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
            self.logger.info(f"[GROUP_MEMBER_SYNC] Starting sync for group {group_id}")

            # 從 LINE API 獲取最新成員清單
            api_members = self.fetch_group_members(group_id)

            if not api_members:
                self.logger.warning(f"No members found for group {group_id}")
                return 0

            # 記錄即將同步的成員總數
            self.logger.info(
                f"[GROUP_MEMBER_SYNC] Group {group_id}: "
                f"Syncing {len(api_members)} members to database"
            )

            # 先註冊群組（如果不存在）
            self.register_group(group_id)

            synced_count = 0
            for member_data in api_members:
                try:
                    # 添加到群組成員表
                    if self.group_members_repo.add(
                        group_id=group_id,
                        user_id=member_data['user_id'],
                        display_name=member_data['display_name']
                    ):
                        synced_count += 1
                        # 記錄成功同步的成員
                        self.logger.info(
                            f"[GROUP_MEMBER_SYNC] ✓ Synced - "
                            f"User ID: {member_data['user_id']}, "
                            f"Display Name: {member_data['display_name']}"
                        )
                    else:
                        # 記錄同步失敗的情況
                        self.logger.warning(
                            f"[GROUP_MEMBER_SYNC] ✗ Failed to sync - "
                            f"User ID: {member_data['user_id']}, "
                            f"Display Name: {member_data['display_name']}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Error syncing member {member_data['user_id']} "
                        f"({member_data['display_name']}): {e}"
                    )

            # 更新群組的成員數量
            self.groups_repo.update_member_count(group_id, synced_count)
            self.groups_repo.update_last_sync(group_id)

            # 更詳細的總結日誌
            self.logger.info(
                f"[GROUP_MEMBER_SYNC] Group {group_id}: "
                f"Successfully synced {synced_count}/{len(api_members)} members"
            )
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
            group_members_docs = self.group_members_repo.get_all(group_id, active_only=True)

            created_players = []
            for member_doc in group_members_docs:
                # 檢查是否已經有球員資料
                existing_player_doc = self.players_repo.get(member_doc['user_id'])

                if existing_player_doc:
                    # 如果已有註冊球員，更新來源群組
                    if not existing_player_doc.get('source_group_id'):
                        self.players_repo.create(
                            user_id=existing_player_doc['user_id'],
                            name=existing_player_doc['name'],
                            shooting_skill=existing_player_doc['skills']['shooting'],
                            defense_skill=existing_player_doc['skills']['defense'],
                            stamina=existing_player_doc['skills']['stamina'],
                            source_group_id=group_id,
                            is_registered=existing_player_doc.get('is_registered', True)
                        )
                    # 將 MongoDB document 轉換為 Player 物件
                    created_players.append(Player.from_dict(existing_player_doc))
                else:
                    # 創建新的群組成員球員資料
                    self.players_repo.create(
                        user_id=member_doc['user_id'],
                        name=member_doc['display_name'],
                        shooting_skill=default_skills['shooting_skill'],
                        defense_skill=default_skills['defense_skill'],
                        stamina=default_skills['stamina'],
                        source_group_id=group_id,
                        is_registered=False  # 標記為群組成員而非註冊球員
                    )

                    # 創建 Player 物件
                    player = Player(
                        user_id=member_doc['user_id'],
                        name=member_doc['display_name'],
                        shooting_skill=default_skills['shooting_skill'],
                        defense_skill=default_skills['defense_skill'],
                        stamina=default_skills['stamina'],
                        source_group=group_id,
                        is_registered=False
                    )
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
                all_players_docs = self.players_repo.get_all(sort_by_registered=True)
                group_players = [
                    Player.from_dict(doc) for doc in all_players_docs
                    if doc.get('source_group_id') == group_id
                ]
            else:
                # 只獲取群組成員
                group_players_docs = self.players_repo.get_by_group(group_id)
                group_players = [
                    Player.from_dict(doc) for doc in group_players_docs
                    if not doc.get('is_registered', True)
                ]

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
            group_members_docs = self.group_members_repo.get_all(group_id, active_only=True)
            group_players_docs = self.players_repo.get_by_group(group_id)

            # 轉換為 Player 物件
            group_players = [Player.from_dict(doc) for doc in group_players_docs]

            registered_players = [p for p in group_players if p.is_registered]
            member_players = [p for p in group_players if not p.is_registered]

            stats = {
                'total_members': len(group_members_docs),
                'total_players': len(group_players),
                'registered_players': len(registered_players),
                'member_players': len(member_players),
                'coverage_rate': len(group_players) / len(group_members_docs) if group_members_docs else 0
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
            db_members_docs = self.group_members_repo.get_all(group_id, active_only=True)

            removed_count = 0
            for db_member_doc in db_members_docs:
                if db_member_doc['user_id'] not in current_user_ids:
                    # 成員已退出，標記為非活動
                    if self.group_members_repo.deactivate(group_id, db_member_doc['user_id']):
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
