#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
統計服務：將 attendances 集合聚合成可顯示的視覺化資料。

attendances 集合 schema（src/database/mongodb.py:107-111）：
{
    "date": "YYYY-MM-DD",
    "teams": [
        { "teamId": "team_1",
          "members": [{"userId": "...", "name": "..."}, ...] },
        ...
    ],
    "updated_at": datetime
}

⚠️ 目前以整個 DB 為統計範圍（不分群），因為 attendances 沒有 group_id，
且 group_members collection 尚無寫入路徑。`group_id` 參數保留只為相容呼叫端。
"""

from collections import Counter
from itertools import combinations
from typing import Dict, List, Set

from pymongo.database import Database


def _member_key(member: Dict) -> str:
    """偏好 userId，缺少時退回名字；都沒有則回空字串（呼叫端應跳過）。"""
    return member.get("userId") or member.get("name") or ""


def get_recent_divisions(db: Database, group_id: str, limit: int = 20) -> List[Dict]:
    """回傳最近 N 場分隊紀錄（最新在前）。"""
    raw = list(db.attendances.find().sort("date", -1).limit(limit))
    out = []
    for att in raw:
        teams = []
        for team in att.get("teams", []):
            members = [
                {
                    "userId": m.get("userId", ""),
                    "name": m.get("name", "Unknown"),
                    "in_group": True,
                }
                for m in team.get("members", [])
            ]
            teams.append({"teamId": team.get("teamId", ""), "members": members})
        out.append({"date": att.get("date", ""), "teams": teams})
    return out


def get_player_stats(db: Database, group_id: str) -> List[Dict]:
    """每位玩家的出場次數與最近一次出場日期（全 DB）。"""
    appearance_count: Counter = Counter()
    last_seen: Dict[str, str] = {}
    name_lookup: Dict[str, str] = {}

    for att in db.attendances.find().sort("date", -1):
        date = att.get("date", "")
        for team in att.get("teams", []):
            for m in team.get("members", []):
                key = _member_key(m)
                if not key:
                    continue
                appearance_count[key] += 1
                if key not in last_seen and date:
                    last_seen[key] = date
                if m.get("name"):
                    name_lookup.setdefault(key, m["name"])

    rows = [
        {
            "userId": key,
            "name": name_lookup.get(key, "Unknown"),
            "appearances": count,
            "last_seen": last_seen.get(key, ""),
        }
        for key, count in appearance_count.items()
    ]
    rows.sort(key=lambda r: (-r["appearances"], r["name"]))
    return rows


def get_pair_cooccurrence(db: Database, group_id: str, top_n: int = 5) -> Dict[str, List[Dict]]:
    """兩兩同隊次數，最常 top_n 組。"""
    pair_counter: Counter = Counter()
    name_lookup: Dict[str, str] = {}

    for att in db.attendances.find():
        for team in att.get("teams", []):
            keys_in_team = []
            for m in team.get("members", []):
                key = _member_key(m)
                if not key:
                    continue
                keys_in_team.append(key)
                if m.get("name"):
                    name_lookup.setdefault(key, m["name"])
            for a, b in combinations(sorted(set(keys_in_team)), 2):
                pair_counter[(a, b)] += 1

    most_common = [
        {
            "userA": a, "nameA": name_lookup.get(a, "Unknown"),
            "userB": b, "nameB": name_lookup.get(b, "Unknown"),
            "count": count,
        }
        for (a, b), count in pair_counter.most_common(top_n)
    ]
    return {"most_common": most_common}


def get_trio_cooccurrence(
    db: Database, group_id: str, top_n: int = 5, never_top_n: int = 10
) -> Dict[str, List[Dict]]:
    """三人同隊統計：最常 top_n 組 + 還沒同隊過 never_top_n 組。
    『還沒同隊』按三人出場總場次 desc 排（越活躍越優先）。"""
    trio_counter: Counter = Counter()
    appearance_count: Counter = Counter()
    name_lookup: Dict[str, str] = {}
    appeared: Set[str] = set()

    for att in db.attendances.find():
        for team in att.get("teams", []):
            keys_in_team = []
            for m in team.get("members", []):
                key = _member_key(m)
                if not key:
                    continue
                keys_in_team.append(key)
                appeared.add(key)
                appearance_count[key] += 1
                if m.get("name"):
                    name_lookup.setdefault(key, m["name"])
            for a, b, c in combinations(sorted(set(keys_in_team)), 3):
                trio_counter[(a, b, c)] += 1

    def _names(a, b, c):
        return [name_lookup.get(a, "Unknown"),
                name_lookup.get(b, "Unknown"),
                name_lookup.get(c, "Unknown")]

    most_common = [
        {"names": _names(a, b, c), "count": count}
        for (a, b, c), count in trio_counter.most_common(top_n)
    ]

    never_candidates = []
    for a, b, c in combinations(sorted(appeared), 3):
        if (a, b, c) in trio_counter:
            continue
        combined = appearance_count[a] + appearance_count[b] + appearance_count[c]
        never_candidates.append((combined, a, b, c))
    never_candidates.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
    never_together = [
        {
            "names": _names(a, b, c),
            "combined_appearances": combined,
        }
        for combined, a, b, c in never_candidates[:never_top_n]
    ]

    return {"most_common": most_common, "never_together": never_together}


def get_group_summary(db: Database, group_id: str) -> Dict:
    """整體摘要：總場次、不重複玩家數、平均隊伍規模、最近一場日期。"""
    total_sessions = 0
    team_size_sum = 0
    team_count = 0
    latest_date = ""
    unique_players: Set[str] = set()

    for att in db.attendances.find().sort("date", -1):
        total_sessions += 1
        if not latest_date:
            latest_date = att.get("date", "")
        for team in att.get("teams", []):
            members = team.get("members", [])
            if not members:
                continue
            team_size_sum += len(members)
            team_count += 1
            for m in members:
                key = _member_key(m)
                if key:
                    unique_players.add(key)

    avg_team_size = round(team_size_sum / team_count, 2) if team_count else 0

    return {
        "group_id": group_id,
        "group_name": "",
        "active_members": len(unique_players),
        "total_sessions": total_sessions,
        "avg_team_size": avg_team_size,
        "latest_session_date": latest_date,
    }
