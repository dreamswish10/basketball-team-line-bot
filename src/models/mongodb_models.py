#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)


class PlayersRepository:
    """球員資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.players

    def create(self, user_id: str, name: str, shooting_skill: int,
               defense_skill: int, stamina: int, source_group_id: str = None,
               is_registered: bool = True) -> bool:
        """建立或更新球員"""
        try:
            player_doc = {
                "user_id": user_id,
                "name": name,
                "skills": {
                    "shooting": max(1, min(10, shooting_skill)),
                    "defense": max(1, min(10, defense_skill)),
                    "stamina": max(1, min(10, stamina))
                },
                "source_group_id": source_group_id,
                "is_registered": is_registered,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "participation_summary": {
                    "total_divisions": 0,
                    "last_n_participations": []
                }
            }

            result = self.collection.replace_one(
                {"user_id": user_id},
                player_doc,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error creating player: {e}")
            return False

    def get(self, user_id: str) -> Optional[Dict]:
        """根據 user_id 獲取球員"""
        try:
            return self.collection.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error getting player: {e}")
            return None

    def get_all(self, sort_by_registered: bool = True) -> List[Dict]:
        """獲取所有球員"""
        try:
            if sort_by_registered:
                return list(self.collection.find().sort([
                    ("is_registered", -1),
                    ("created_at", -1)
                ]))
            else:
                return list(self.collection.find().sort("created_at", -1))
        except Exception as e:
            logger.error(f"Error getting all players: {e}")
            return []

    def get_by_group(self, group_id: str) -> List[Dict]:
        """獲取特定群組的所有球員"""
        try:
            return list(self.collection.find(
                {"source_group_id": group_id}
            ).sort([
                ("is_registered", -1),
                ("created_at", -1)
            ]))
        except Exception as e:
            logger.error(f"Error getting group players: {e}")
            return []

    def delete(self, user_id: str) -> bool:
        """刪除球員"""
        try:
            result = self.collection.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting player: {e}")
            return False

    def count(self) -> int:
        """獲取球員總數"""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting players: {e}")
            return 0

    def update_skills(self, user_id: str, shooting: int, defense: int, stamina: int) -> bool:
        """更新球員技能"""
        try:
            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "skills.shooting": max(1, min(10, shooting)),
                        "skills.defense": max(1, min(10, defense)),
                        "skills.stamina": max(1, min(10, stamina)),
                        "updated_at": datetime.now()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating player skills: {e}")
            return False

    def add_participation(self, user_id: str, division_id: ObjectId,
                          team_number: int, skills_snapshot: Dict,
                          participated_at: datetime, limit: int = 10) -> bool:
        """新增球員參賽記錄"""
        try:
            participation_data = {
                "division_id": division_id,
                "team_number": team_number,
                "participated_at": participated_at,
                "skills_snapshot": skills_snapshot
            }

            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"participation_summary.total_divisions": 1},
                    "$push": {
                        "participation_summary.last_n_participations": {
                            "$each": [participation_data],
                            "$slice": -limit  # 只保留最後 N 筆
                        }
                    },
                    "$set": {"updated_at": datetime.now()}
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error adding participation: {e}")
            return False


class GroupsRepository:
    """群組資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.groups

    def create(self, group_id: str, group_name: str,
               default_skills: Dict = None) -> bool:
        """建立或更新群組"""
        try:
            if default_skills is None:
                default_skills = {"shooting": 5, "defense": 5, "stamina": 5}

            group_doc = {
                "group_id": group_id,
                "group_name": group_name,
                "settings": {
                    "default_skills": default_skills,
                    "participation_tracking_limit": 10
                },
                "created_at": datetime.now(),
                "last_sync_at": datetime.now(),
                "member_count": 0,
                "active": True
            }

            result = self.collection.replace_one(
                {"group_id": group_id},
                group_doc,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False

    def get(self, group_id: str) -> Optional[Dict]:
        """獲取群組"""
        try:
            return self.collection.find_one({"group_id": group_id})
        except Exception as e:
            logger.error(f"Error getting group: {e}")
            return None

    def update_last_sync(self, group_id: str) -> bool:
        """更新最後同步時間"""
        try:
            result = self.collection.update_one(
                {"group_id": group_id},
                {"$set": {"last_sync_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last sync: {e}")
            return False

    def update_member_count(self, group_id: str, count: int) -> bool:
        """更新成員數量"""
        try:
            result = self.collection.update_one(
                {"group_id": group_id},
                {"$set": {"member_count": count}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating member count: {e}")
            return False


class GroupMembersRepository:
    """群組成員資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.group_members

    def add(self, group_id: str, user_id: str, display_name: str,
            player_ref: ObjectId = None) -> bool:
        """新增群組成員"""
        try:
            member_doc = {
                "group_id": group_id,
                "user_id": user_id,
                "display_name": display_name,
                "is_active": True,
                "joined_at": datetime.now(),
                "left_at": None,
                "player_ref": player_ref
            }

            result = self.collection.replace_one(
                {"group_id": group_id, "user_id": user_id},
                member_doc,
                upsert=True
            )

            return result.acknowledged

        except Exception as e:
            logger.error(f"Error adding group member: {e}")
            return False

    def get_all(self, group_id: str, active_only: bool = True) -> List[Dict]:
        """獲取群組所有成員"""
        try:
            query = {"group_id": group_id}
            if active_only:
                query["is_active"] = True

            return list(self.collection.find(query).sort("joined_at", 1))

        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            return []

    def deactivate(self, group_id: str, user_id: str) -> bool:
        """停用群組成員（設為非活動）"""
        try:
            result = self.collection.update_one(
                {"group_id": group_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "left_at": datetime.now()
                    }
                }
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error deactivating member: {e}")
            return False

    def update_player_ref(self, group_id: str, user_id: str, player_ref: ObjectId) -> bool:
        """更新成員的 player 引用"""
        try:
            result = self.collection.update_one(
                {"group_id": group_id, "user_id": user_id},
                {"$set": {"player_ref": player_ref}}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating player ref: {e}")
            return False


class DivisionsRepository:
    """分隊記錄資料庫操作類"""

    def __init__(self, db: Database):
        self.collection = db.divisions

    def create(self, division_name: str, teams_data: List[Dict],
               num_teams: int, group_id: str = None,
               balance_score: float = 0.0, algorithm_used: str = "greedy_randomized",
               created_by_user_id: str = None) -> Optional[ObjectId]:
        """建立分隊記錄"""
        try:
            division_doc = {
                "division_name": division_name,
                "group_id": group_id,
                "num_teams": num_teams,
                "teams": teams_data,
                "balance_score": balance_score,
                "algorithm_used": algorithm_used,
                "created_at": datetime.now(),
                "created_by_user_id": created_by_user_id,
                "deleted": False,
                "deleted_at": None,
                "deleted_by_user_id": None,
                "notes": None
            }

            result = self.collection.insert_one(division_doc)
            return result.inserted_id

        except Exception as e:
            logger.error(f"Error creating division: {e}")
            return None

    def get_by_id(self, division_id: ObjectId) -> Optional[Dict]:
        """根據 ID 獲取分隊記錄"""
        try:
            return self.collection.find_one({"_id": division_id})
        except Exception as e:
            logger.error(f"Error getting division: {e}")
            return None

    def get_recent(self, group_id: str = None, limit: int = 5,
                   include_deleted: bool = False) -> List[Dict]:
        """獲取最近的分隊記錄"""
        try:
            query = {}

            if group_id:
                query["group_id"] = group_id

            if not include_deleted:
                query["deleted"] = {"$ne": True}

            return list(self.collection.find(query)
                        .sort("created_at", -1)
                        .limit(limit))

        except Exception as e:
            logger.error(f"Error getting recent divisions: {e}")
            return []

    def get_by_player(self, user_id: str, limit: int = 10) -> List[Dict]:
        """獲取球員參與過的分隊記錄"""
        try:
            query = {
                "teams.players.user_id": user_id,
                "deleted": {"$ne": True}
            }

            return list(self.collection.find(query)
                        .sort("created_at", -1)
                        .limit(limit))

        except Exception as e:
            logger.error(f"Error getting player divisions: {e}")
            return []

    def soft_delete(self, division_id: ObjectId, deleted_by_user_id: str) -> bool:
        """軟刪除分隊記錄"""
        try:
            result = self.collection.update_one(
                {"_id": division_id},
                {
                    "$set": {
                        "deleted": True,
                        "deleted_at": datetime.now(),
                        "deleted_by_user_id": deleted_by_user_id
                    }
                }
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error soft deleting division: {e}")
            return False

    def restore(self, division_id: ObjectId) -> bool:
        """還原已刪除的分隊記錄"""
        try:
            result = self.collection.update_one(
                {"_id": division_id},
                {
                    "$set": {
                        "deleted": False,
                        "deleted_at": None,
                        "deleted_by_user_id": None
                    }
                }
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error restoring division: {e}")
            return False

    def update_notes(self, division_id: ObjectId, notes: str) -> bool:
        """更新分隊記錄備註"""
        try:
            result = self.collection.update_one(
                {"_id": division_id},
                {"$set": {"notes": notes}}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating division notes: {e}")
            return False

    def count(self, group_id: str = None, include_deleted: bool = False) -> int:
        """計算分隊記錄數量"""
        try:
            query = {}

            if group_id:
                query["group_id"] = group_id

            if not include_deleted:
                query["deleted"] = {"$ne": True}

            return self.collection.count_documents(query)

        except Exception as e:
            logger.error(f"Error counting divisions: {e}")
            return 0
