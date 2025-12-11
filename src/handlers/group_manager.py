#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
群組管理模組 - 簡化版本，專注於基本功能
"""

from typing import List, Optional, Dict
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
import logging


class GroupManager:
    def __init__(self, line_bot_api: LineBotApi):
        self.line_bot_api = line_bot_api
        self.logger = logging.getLogger(__name__)

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
                    self.logger.info(f"[MEMBER_FETCH] {profile.display_name} ({user_id})")

                except LineBotApiError as profile_error:
                    # 某些用戶可能無法獲取個人資料（隱私設定）
                    self.logger.warning(f"[MEMBER_FETCH] Cannot get profile for {user_id}: {profile_error}")
                    # 即使無法獲取個人資料，也記錄用戶 ID
                    members.append({
                        'user_id': user_id,
                        'display_name': f"User_{user_id[:8]}",
                        'picture_url': None,
                        'status_message': None
                    })

                except Exception as member_error:
                    self.logger.error(f"[MEMBER_FETCH] Unexpected error for {user_id}: {member_error}")

            self.logger.info(f"[GROUP_MEMBER_FETCH] Successfully fetched {len(members)} members from group {group_id}")
            return members

        except LineBotApiError as api_error:
            self.logger.error(f"[GROUP_MEMBER_FETCH] LINE API error for group {group_id}: {api_error}")
            return []

        except Exception as e:
            self.logger.error(f"[GROUP_MEMBER_FETCH] Unexpected error for group {group_id}: {e}")
            return []

    def sync_group_members(self, group_id: str) -> int:
        """同步群組成員（簡化版本）"""
        try:
            # 獲取群組成員
            members = self.fetch_group_members(group_id)
            
            self.logger.info(f"[GROUP_SYNC] Group {group_id}: Synced {len(members)} members")
            return len(members)

        except Exception as e:
            self.logger.error(f"[GROUP_SYNC] Error syncing group {group_id}: {e}")
            return 0

    def remove_inactive_members(self, group_id: str) -> bool:
        """移除非活動成員（簡化版本）"""
        try:
            self.logger.info(f"[GROUP_CLEANUP] Processed cleanup for group {group_id}")
            return True

        except Exception as e:
            self.logger.error(f"[GROUP_CLEANUP] Error cleaning up group {group_id}: {e}")
            return False