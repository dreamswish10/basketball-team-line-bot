#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
統計服務：將 attendances 集合聚合成可顯示的視覺化資料。

attendances 集合 schema（src/database/mongodb.py:107-111）：
{
    "date": "YYYY-MM-DD",                       # unique
    "teams": [
        { "teamId": "team_1",
          "members": [{"userId": "...", "name": "..."}, ...] },
        ...
    ],
    "updated_at": datetime
}

attendances 不含 group_id，因此本服務的「群組過濾」採用：
僅納入「至少一位成員出現在 group_members(group_id) 的 active 名單」的 attendance；
團隊內若有他群成員一併顯示（不過濾隊內人員），讓使用者看到完整當日分隊。

呼叫端負責先用 LIFF id_token 驗身分並確認該使用者是該 group 的 active member。
"""

from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, List, Set

from pymongo.database import Database


def _get_group_user_ids(db: Database, group_id: str) -> Set[str]:
    """取得指定群組目前 active 的所有成員 user_id。"""
    cursor = db.group_members.find(
        {"group_id": group_id, "is_active": True},
        {"user_id": 1, "_id": 0},
    )
    return {doc["user_id"] for doc in cursor if doc.get("user_id")}


def _attendance_involves_group(attendance: Dict, group_user_ids: Set[str]) -> bool:
    for team in attendance.get("teams", []):
        for member in team.get("members", []):
            if member.get("userId") in group_user_ids:
                return True
    return False


def get_recent_divisions(db: Database, group_id: str, limit: int = 20) -> List[Dict]:
    """
    回傳最近 N 場分隊紀錄（最新在前），只含與該群組相關的場次。

    Returns: [
        { "date": "YYYY-MM-DD",
          "teams": [
              { "teamId": "team_1",
                "members": [{"userId": "...", "name": "...", "in_group": True/False}, ...] },
              ...
          ] },
        ...
    ]
    """
    group_user_ids = _get_group_user_ids(db, group_id)
    if not group_user_ids:
        return []

    # 多抓一些以利過濾後仍有足量資料
    raw = list(
        db.attendances.find().sort("date", -1).limit(max(limit * 3, 50))
    )

    out = []
    for att in raw:
        if not _attendance_involves_group(att, group_user_ids):
            continue
        teams = []
        for team in att.get("teams", []):
            members = []
            for m in team.get("members", []):
                members.append({
                    "userId": m.get("userId", ""),
                    "name": m.get("name", "Unknown"),
                    "in_group": m.get("userId") in group_user_ids,
                })
            teams.append({"teamId": team.get("teamId", ""), "members": members})
        out.append({"date": att.get("date", ""), "teams": teams})
        if len(out) >= limit:
            break
    return out


def get_player_stats(db: Database, group_id: str) -> List[Dict]:
    """
    每位群組成員的出場次數與最近一次出場日期。
    僅統計 group_members 內 active 的 user_id。
    """
    group_user_ids = _get_group_user_ids(db, group_id)
    if not group_user_ids:
        return []

    appearance_count: Counter = Counter()
    last_seen: Dict[str, str] = {}
    name_lookup: Dict[str, str] = {}

    cursor = db.attendances.find().sort("date", -1)
    for att in cursor:
        date = att.get("date", "")
        for team in att.get("teams", []):
            for m in team.get("members", []):
                uid = m.get("userId")
                if uid not in group_user_ids:
                    continue
                appearance_count[uid] += 1
                if uid not in last_seen and date:
                    last_seen[uid] = date
                if m.get("name"):
                    name_lookup.setdefault(uid, m["name"])

    # 補上沒出場過的成員名字
    for member in db.group_members.find(
        {"group_id": group_id, "is_active": True},
        {"user_id": 1, "display_name": 1, "_id": 0},
    ):
        uid = member.get("user_id")
        if uid and uid not in name_lookup:
            name_lookup[uid] = member.get("display_name") or "Unknown"

    rows = []
    for uid in group_user_ids:
        rows.append({
            "userId": uid,
            "name": name_lookup.get(uid, "Unknown"),
            "appearances": appearance_count.get(uid, 0),
            "last_seen": last_seen.get(uid, ""),
        })
    rows.sort(key=lambda r: (-r["appearances"], r["name"]))
    return rows


def get_pair_cooccurrence(db: Database, group_id: str, top_n: int = 10) -> Dict[str, List[Dict]]:
    """
    計算群組成員兩兩同隊的次數。
    回傳 {"most_common": [...], "least_common": [...]}，每筆含名字與次數。
    least_common 僅包含至少出場過一次的玩家配對（雙方都有 appearance）。
    """
    group_user_ids = _get_group_user_ids(db, group_id)
    if len(group_user_ids) < 2:
        return {"most_common": [], "least_common": []}

    pair_counter: Counter = Counter()
    name_lookup: Dict[str, str] = {}
    appeared: Set[str] = set()

    for att in db.attendances.find():
        for team in att.get("teams", []):
            uids_in_team = []
            for m in team.get("members", []):
                uid = m.get("userId")
                if uid in group_user_ids:
                    uids_in_team.append(uid)
                    appeared.add(uid)
                    if m.get("name"):
                        name_lookup.setdefault(uid, m["name"])
            for a, b in combinations(sorted(set(uids_in_team)), 2):
                pair_counter[(a, b)] += 1

    # 為從未同隊但都有出場的配對補 0
    full_pairs: Dict[tuple, int] = {}
    for a, b in combinations(sorted(appeared), 2):
        full_pairs[(a, b)] = pair_counter.get((a, b), 0)

    def _format(pair, count):
        a, b = pair
        return {
            "userA": a, "nameA": name_lookup.get(a, "Unknown"),
            "userB": b, "nameB": name_lookup.get(b, "Unknown"),
            "count": count,
        }

    sorted_pairs = sorted(full_pairs.items(), key=lambda kv: kv[1])
    most_common = [_format(p, c) for p, c in sorted_pairs[::-1][:top_n]]
    least_common = [_format(p, c) for p, c in sorted_pairs[:top_n]]
    return {"most_common": most_common, "least_common": least_common}


def get_group_summary(db: Database, group_id: str) -> Dict:
    """
    群組整體摘要：總場次、活躍成員數、平均隊伍規模、最近一場日期。
    """
    group_user_ids = _get_group_user_ids(db, group_id)
    active_member_count = len(group_user_ids)

    total_sessions = 0
    team_size_sum = 0
    team_count = 0
    latest_date = ""

    if group_user_ids:
        for att in db.attendances.find().sort("date", -1):
            if not _attendance_involves_group(att, group_user_ids):
                continue
            total_sessions += 1
            if not latest_date:
                latest_date = att.get("date", "")
            for team in att.get("teams", []):
                members = team.get("members", [])
                if members:
                    team_size_sum += len(members)
                    team_count += 1

    avg_team_size = round(team_size_sum / team_count, 2) if team_count else 0

    group_doc = db.groups.find_one({"group_id": group_id}) or {}

    return {
        "group_id": group_id,
        "group_name": group_doc.get("group_name", ""),
        "active_members": active_member_count,
        "total_sessions": total_sessions,
        "avg_team_size": avg_team_size,
        "latest_session_date": latest_date,
    }
