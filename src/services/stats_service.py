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
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from typing import Dict, List, Optional, Set

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
    db: Database, group_id: str, top_n: int = 5, never_top_n: int = 100
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


def get_recent_stars(db: Database, group_id: str, days: int = 30, limit: int = 5) -> Dict:
    """近 N 天出場排行。"""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    appearance_count: Counter = Counter()
    name_lookup: Dict[str, str] = {}

    for att in db.attendances.find({"date": {"$gte": cutoff}}):
        for team in att.get("teams", []):
            for m in team.get("members", []):
                key = _member_key(m)
                if not key:
                    continue
                appearance_count[key] += 1
                if m.get("name"):
                    name_lookup.setdefault(key, m["name"])

    stars = [
        {"name": name_lookup.get(key, "Unknown"), "appearances": count}
        for key, count in appearance_count.most_common(limit)
    ]
    return {"days": days, "stars": stars}


def get_dormant_members(
    db: Database,
    group_id: str,
    dormant_days: int = 30,
    min_appearances: int = 3,
    limit: int = 10,
) -> Dict:
    """常打但最近 N 天沒出現的玩家。"""
    cutoff = (date.today() - timedelta(days=dormant_days)).isoformat()
    appearance_count: Counter = Counter()
    last_seen: Dict[str, str] = {}
    name_lookup: Dict[str, str] = {}

    for att in db.attendances.find().sort("date", -1):
        d = att.get("date", "")
        for team in att.get("teams", []):
            for m in team.get("members", []):
                key = _member_key(m)
                if not key:
                    continue
                appearance_count[key] += 1
                if key not in last_seen and d:
                    last_seen[key] = d
                if m.get("name"):
                    name_lookup.setdefault(key, m["name"])

    today = date.today()
    rows = []
    for key, count in appearance_count.items():
        if count < min_appearances:
            continue
        ls = last_seen.get(key, "")
        if not ls or ls >= cutoff:
            continue
        try:
            days_ago = (today - date.fromisoformat(ls)).days
        except ValueError:
            days_ago = None
        rows.append({
            "name": name_lookup.get(key, "Unknown"),
            "appearances": count,
            "last_seen": ls,
            "days_ago": days_ago,
        })

    rows.sort(key=lambda r: (r["last_seen"], -r["appearances"]))
    return {"dormant_days": dormant_days, "min_appearances": min_appearances, "members": rows[:limit]}


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


# ─── 預期 vs 體感 回饋（Step 1/2/3） ────────────────────────────────

def get_feedback_session(db: Database) -> Optional[Dict]:
    """取最新一場 attendance 當作本週可投票場次。"""
    att = db.attendances.find_one(sort=[("date", -1)])
    if not att:
        return None
    return {
        "date": att.get("date", ""),
        "teams": [
            {
                "teamId": t.get("teamId", ""),
                "members": [
                    {"userId": m.get("userId", ""), "name": m.get("name", "?")}
                    for m in t.get("members", [])
                ],
            }
            for t in att.get("teams", [])
        ],
    }


def get_user_opinion(db: Database, date_str: str, user_id: str) -> Optional[Dict]:
    doc = db.opinions.find_one({"date": date_str, "user_id": user_id})
    if not doc:
        return None
    return {
        "played": doc.get("played"),
        "pre_ranking": doc.get("pre_ranking"),
        "post_ranking": doc.get("post_ranking"),
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


def submit_opinion(
    db: Database,
    date_str: str,
    user_id: str,
    played: bool,
    pre_ranking: Optional[List[str]],
    post_ranking: Optional[List[str]],
) -> None:
    now = datetime.now(timezone.utc)
    db.opinions.update_one(
        {"date": date_str, "user_id": user_id},
        {
            "$set": {
                "played": bool(played),
                "pre_ranking": pre_ranking,
                "post_ranking": post_ranking if played else None,
                "updated_at": now,
            },
            "$setOnInsert": {
                "date": date_str,
                "user_id": user_id,
                "created_at": now,
            },
        },
        upsert=True,
    )


def get_session_vote_counts(db: Database, date_str: str) -> Dict[str, int]:
    """某場累積的 pre/post 投票數。"""
    pre = db.opinions.count_documents({"date": date_str, "pre_ranking": {"$ne": None}})
    post = db.opinions.count_documents({"date": date_str, "post_ranking": {"$ne": None}})
    return {"pre_votes": pre, "post_votes": post}


def get_team_estimation_ranking(
    db: Database,
    min_votes: int = 3,
    top_n: int = 5,
) -> Dict[str, List[Dict]]:
    """各場每隊：預期平均名次 vs 體感平均名次。
    delta > 0 → 被高估；delta < 0 → 被低估。
    僅納入 pre 與 post 都達 min_votes 的場次。"""
    sessions: Dict[str, Dict[str, List[List[str]]]] = {}
    for op in db.opinions.find():
        ds = op.get("date")
        if not ds:
            continue
        bucket = sessions.setdefault(ds, {"pre": [], "post": []})
        if op.get("pre_ranking"):
            bucket["pre"].append(op["pre_ranking"])
        if op.get("played") and op.get("post_ranking"):
            bucket["post"].append(op["post_ranking"])

    rows: List[Dict] = []
    for ds, data in sessions.items():
        if len(data["pre"]) < min_votes or len(data["post"]) < min_votes:
            continue
        att = db.attendances.find_one({"date": ds})
        if not att:
            continue
        team_members = {
            t.get("teamId", ""): [m.get("name", "?") for m in t.get("members", [])]
            for t in att.get("teams", [])
        }
        team_ids = list(team_members.keys())

        def _avg(votes: List[List[str]]) -> Dict[str, float]:
            sums: Dict[str, float] = {tid: 0.0 for tid in team_ids}
            counts: Dict[str, int] = {tid: 0 for tid in team_ids}
            for ranking in votes:
                for idx, tid in enumerate(ranking):
                    if tid in sums:
                        sums[tid] += idx + 1
                        counts[tid] += 1
            return {tid: sums[tid] / counts[tid] for tid in team_ids if counts[tid] > 0}

        pre_avg = _avg(data["pre"])
        post_avg = _avg(data["post"])

        for tid in team_ids:
            if tid not in pre_avg or tid not in post_avg:
                continue
            rows.append({
                "date": ds,
                "team_id": tid,
                "members": team_members.get(tid, []),
                "predicted_rank": round(pre_avg[tid], 2),
                "felt_rank": round(post_avg[tid], 2),
                "delta": round(post_avg[tid] - pre_avg[tid], 2),
                "pre_votes": len(data["pre"]),
                "post_votes": len(data["post"]),
            })

    overrated = sorted(rows, key=lambda r: -r["delta"])[:top_n]
    underrated = sorted(rows, key=lambda r: r["delta"])[:top_n]
    return {"min_votes": min_votes, "overrated": overrated, "underrated": underrated}
