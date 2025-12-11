#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Dict, Any
from datetime import datetime
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)


class AttendancesRepository:
    """出席記錄資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.attendances

    def create_or_update_attendance(self, date: str, teams: List[Dict]) -> bool:
        """建立或更新指定日期的出席記錄"""
        try:
            # 驗證每隊最多3個成員
            for team in teams:
                if len(team.get('members', [])) > 3:
                    logger.warning(f"Team {team.get('teamId')} has more than 3 members")
                    return False

            attendance_doc = {
                "date": date,
                "teams": teams,
                "updated_at": datetime.now()
            }

            result = self.collection.replace_one(
                {"date": date},
                attendance_doc,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error creating/updating attendance: {e}")
            return False

    def get_attendance_by_date(self, date: str) -> Optional[Dict]:
        """根據日期獲取出席記錄"""
        try:
            return self.collection.find_one({"date": date})
        except Exception as e:
            logger.error(f"Error getting attendance by date: {e}")
            return None

    def get_recent_attendances(self, limit: int = 10) -> List[Dict]:
        """獲取最近的出席記錄"""
        try:
            return list(self.collection.find().sort("date", -1).limit(limit))
        except Exception as e:
            logger.error(f"Error getting recent attendances: {e}")
            return []

    def get_user_attendances(self, user_id: str, limit: int = 10) -> List[Dict]:
        """獲取特定用戶的出席記錄"""
        try:
            query = {"teams.members.userId": user_id}
            return list(self.collection.find(query).sort("date", -1).limit(limit))
        except Exception as e:
            logger.error(f"Error getting user attendances: {e}")
            return []

    def add_user_to_team(self, date: str, team_id: str, user_id: str, name: str) -> bool:
        """將用戶添加到指定日期的隊伍中"""
        try:
            # 檢查當前隊伍成員數量
            attendance = self.get_attendance_by_date(date)
            if not attendance:
                # 創建新的出席記錄
                teams = [{
                    "teamId": team_id,
                    "members": [{"userId": user_id, "name": name}]
                }]
                return self.create_or_update_attendance(date, teams)

            # 查找目標隊伍
            teams = attendance.get("teams", [])
            target_team = None
            for team in teams:
                if team["teamId"] == team_id:
                    target_team = team
                    break

            if not target_team:
                # 創建新隊伍
                teams.append({
                    "teamId": team_id,
                    "members": [{"userId": user_id, "name": name}]
                })
            else:
                # 檢查隊伍成員數量限制
                if len(target_team["members"]) >= 3:
                    logger.warning(f"Team {team_id} is full (3 members maximum)")
                    return False
                
                # 檢查用戶是否已在隊伍中
                for member in target_team["members"]:
                    if member["userId"] == user_id:
                        logger.info(f"User {user_id} already in team {team_id}")
                        return True

                # 添加用戶到隊伍
                target_team["members"].append({"userId": user_id, "name": name})

            return self.create_or_update_attendance(date, teams)

        except Exception as e:
            logger.error(f"Error adding user to team: {e}")
            return False

    def remove_user_from_attendance(self, date: str, user_id: str) -> bool:
        """從指定日期的出席記錄中移除用戶"""
        try:
            attendance = self.get_attendance_by_date(date)
            if not attendance:
                return True  # 沒有記錄，視為成功

            teams = attendance.get("teams", [])
            for team in teams:
                team["members"] = [member for member in team["members"] 
                                if member["userId"] != user_id]

            # 移除空隊伍
            teams = [team for team in teams if len(team["members"]) > 0]

            return self.create_or_update_attendance(date, teams)

        except Exception as e:
            logger.error(f"Error removing user from attendance: {e}")
            return False

    def get_attendances_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """獲取指定日期範圍內的出席記錄"""
        try:
            query = {
                "date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            return list(self.collection.find(query).sort("date", 1))
        except Exception as e:
            logger.error(f"Error getting attendances by date range: {e}")
            return []


class AliasMapRepository:
    """別名對應資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.aliasMap

    def create_or_update_alias(self, user_id: str, aliases) -> bool:
        """建立或更新用戶的別名列表
        
        Args:
            user_id: 用戶ID
            aliases: 可以是 List[str] 或 Dict，支援以下格式：
                    - List[str]: 傳統格式，只有精確匹配
                    - Dict: 增強格式 {"exact": [...], "patterns": [...], "regex": [...]}
        """
        try:
            # 處理不同的別名格式
            if isinstance(aliases, list):
                # 傳統格式：純字符串列表
                cleaned_aliases = list(set([alias.strip() for alias in aliases if alias.strip()]))
                alias_doc = {
                    "userId": user_id,
                    "aliases": {
                        "exact": cleaned_aliases,
                        "patterns": [],
                        "regex": []
                    },
                    "updated_at": datetime.now()
                }
            elif isinstance(aliases, dict):
                # 增強格式：支援不同匹配類型
                alias_doc = {
                    "userId": user_id,
                    "aliases": {
                        "exact": list(set([alias.strip() for alias in aliases.get("exact", []) if alias.strip()])),
                        "patterns": list(set([pattern.strip() for pattern in aliases.get("patterns", []) if pattern.strip()])),
                        "regex": list(set([regex.strip() for regex in aliases.get("regex", []) if regex.strip()]))
                    },
                    "updated_at": datetime.now()
                }
            else:
                logger.error("Invalid aliases format")
                return False

            result = self.collection.replace_one(
                {"userId": user_id},
                alias_doc,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error creating/updating alias: {e}")
            return False

    def get_aliases_by_user_id(self, user_id: str) -> Dict:
        """根據用戶ID獲取別名列表
        
        Returns:
            Dict: {"exact": [...], "patterns": [...], "regex": [...]} 或舊格式的 List[str]
        """
        try:
            doc = self.collection.find_one({"userId": user_id})
            if not doc:
                return {"exact": [], "patterns": [], "regex": []}
            
            aliases = doc.get("aliases", [])
            
            # 向後兼容：如果是舊格式(list)，轉換為新格式
            if isinstance(aliases, list):
                return {"exact": aliases, "patterns": [], "regex": []}
            
            # 新格式：直接返回
            return aliases
            
        except Exception as e:
            logger.error(f"Error getting aliases by user ID: {e}")
            return {"exact": [], "patterns": [], "regex": []}

    def find_user_by_alias(self, alias: str) -> Optional[str]:
        """根據別名查找用戶ID，支援多種匹配模式
        
        匹配優先級：
        1. 精確匹配 (exact)
        2. 模式匹配 (patterns) - 支援 * 通配符  
        3. 正則匹配 (regex)
        4. 模糊匹配 (向後兼容)
        """
        try:
            import re
            import fnmatch
            
            # 獲取所有別名文檔
            all_docs = list(self.collection.find())
            
            for doc in all_docs:
                user_id = doc["userId"]
                aliases = doc.get("aliases", [])
                
                # 處理向後兼容：舊格式 (list)
                if isinstance(aliases, list):
                    # 精確匹配
                    if alias in aliases:
                        return user_id
                    # 模糊匹配（包含）
                    for old_alias in aliases:
                        if alias.lower() in old_alias.lower():
                            return user_id
                    continue
                
                # 新格式 (dict)
                exact_aliases = aliases.get("exact", [])
                patterns = aliases.get("patterns", [])
                regex_patterns = aliases.get("regex", [])
                
                # 1. 精確匹配
                if alias in exact_aliases:
                    return user_id
                
                # 2. 模式匹配 (支援 * 通配符)
                for pattern in patterns:
                    if fnmatch.fnmatch(alias, pattern):
                        return user_id
                
                # 3. 正則匹配
                for regex_pattern in regex_patterns:
                    try:
                        if re.match(regex_pattern, alias, re.IGNORECASE):
                            return user_id
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {regex_pattern}")
                        continue
                
                # 4. 模糊匹配（向後兼容）- 在 exact aliases 中搜索
                for exact_alias in exact_aliases:
                    if alias.lower() in exact_alias.lower():
                        return user_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by alias: {e}")
            return None

    def add_alias_to_user(self, user_id: str, new_alias: str) -> bool:
        """為用戶添加新別名"""
        try:
            new_alias = new_alias.strip()
            if not new_alias:
                return False

            result = self.collection.update_one(
                {"userId": user_id},
                {
                    "$addToSet": {"aliases": new_alias},
                    "$set": {"updated_at": datetime.now()}
                },
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error adding alias to user: {e}")
            return False

    def remove_alias_from_user(self, user_id: str, alias: str) -> bool:
        """從用戶移除指定別名"""
        try:
            result = self.collection.update_one(
                {"userId": user_id},
                {
                    "$pull": {"aliases": alias},
                    "$set": {"updated_at": datetime.now()}
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error removing alias from user: {e}")
            return False

    def get_all_aliases(self) -> List[Dict]:
        """獲取所有用戶的別名對應"""
        try:
            return list(self.collection.find())
        except Exception as e:
            logger.error(f"Error getting all aliases: {e}")
            return []

    def delete_user_aliases(self, user_id: str) -> bool:
        """刪除用戶的所有別名"""
        try:
            result = self.collection.delete_one({"userId": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting user aliases: {e}")
            return False

    def search_aliases(self, search_term: str) -> List[Dict]:
        """搜索包含特定詞彙的別名"""
        try:
            regex_pattern = {"$regex": search_term, "$options": "i"}
            return list(self.collection.find({"aliases": regex_pattern}))
        except Exception as e:
            logger.error(f"Error searching aliases: {e}")
            return []