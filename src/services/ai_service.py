#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 助理服務：把 Claude 接到分隊資料上（/ai 指令）。

三件事：
1. 問問題 —— Claude 透過工具查 attendances / opinions 的統計
2. AI 分隊 —— Claude 讀歷史與筆記後決定分隊，由 save_teams 驗證並寫入今天的紀錄
3. 記憶 —— 兩層：
   - ai_conversations：每個聊天室最近的對話（短期）
   - ai_memories：Claude 用 remember / forget 工具維護的長期筆記

新增的 collection：
    ai_conversations { scope_id, role: "user"|"assistant", content, created_at }
    ai_memories      { scope_id, content, created_at }
scope_id = 群組的 group_id，或一對一聊天時的 user_id。
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database

from src.services import stats_service

try:  # SDK 需要 Python >= 3.10；缺少時 /ai 會回覆尚未設定，其他指令不受影響
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MAX_TEAM_SIZE = 3            # 3v3，與 AttendancesRepository 的限制一致
HISTORY_MESSAGES = 12        # 每次帶入的最近對話則數（user + assistant）
HISTORY_KEEP = 60            # 每個 scope 最多保留幾則對話
MAX_MEMORIES = 50            # 每個 scope 的長期筆記上限
MAX_MEMORY_CHARS = 300
MAX_TOOL_ROUNDS = 8
TIME_BUDGET_SECONDS = 45     # LINE reply token 約 1 分鐘失效，留一點餘裕
REQUEST_TIMEOUT_SECONDS = 40

SYSTEM_PROMPT = """你是一個 LINE 籃球群組的分隊助理。這個群每週打 3 對 3，每隊最多 3 人。

你能做三件事：回答關於分隊紀錄的問題、幫大家分隊、記住使用者交代的事。

資料
- 每一天最多一筆分隊紀錄（日期 + 各隊成員）。賽前賽後的隊伍強弱投票也查得到。
- 任何關於紀錄或統計的數字都要先用工具查，不要憑印象或猜測。查不到就直接說查不到。
- 球員可能有多個別名，工具會自動把別名對應到同一個人；查不到的名字會被當成「路人」。

分隊
- 使用者要你分隊時：先看最近幾場的紀錄和長期筆記，再決定隊伍。優先滿足使用者這次講的條件與筆記裡的限制，其次盡量避免跟最近幾場同樣的隊友組合，並讓各隊人數平均。
- 可以用 suggest_teams_by_algorithm 取得演算法的建議當起點再調整，也可以自己排。
- 決定後呼叫 save_teams 存成今天的紀錄（會覆蓋今天已有的紀錄）。save_teams 會驗證名單，回報錯誤就修正後再呼叫一次。
- 使用者只是假設性地問（例如「如果分三隊會怎樣」）就不要存。
- 回覆時列出各隊名單，並用一兩句話說明為什麼這樣排。

記憶
- 每則訊息開頭的「長期筆記」是你之前記下的內容，回答與分隊時都要參考。
- 使用者講到以後還用得上的事（誰受傷、誰跟誰不要同隊、誰打什麼位置、偏好的分法）就用 remember 記下來，一則筆記只寫一件事。
- 筆記過時或使用者要你忘掉時用 forget 刪除。一次性的事情不用記。

回覆格式
- 用繁體中文，口吻像球友，簡短直接。
- LINE 不會顯示 Markdown，所以不要用 **、#、表格或程式碼區塊；用換行和簡單符號排版即可。"""

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_recent_games",
        "description": "取得最近幾場的分隊紀錄（最新在前），每場包含日期與各隊成員。分隊前或被問到「上次／最近怎麼分」時使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "要幾場，預設 5，最多 30"},
            },
        },
    },
    {
        "name": "get_player_stats",
        "description": "所有球員的出場次數與最近一次出場日期，以及總場次摘要。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_teammate_stats",
        "description": "查某位球員跟每個人同隊過幾次、同一天出場幾次。回答「我最常跟誰同隊」「A 跟 B 同隊過幾次」時使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "player": {"type": "string", "description": "球員名字或別名"},
            },
            "required": ["player"],
        },
    },
    {
        "name": "get_top_pairs",
        "description": "全體最常同隊的兩人組合排行。",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "要幾組，預設 10"},
            },
        },
    },
    {
        "name": "get_feedback_ranking",
        "description": "賽前預期名次與賽後體感名次的投票結果：哪些隊伍被高估、哪些被低估。用來判斷哪種組合實際上太強或太弱。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "suggest_teams_by_algorithm",
        "description": "用既有的權重分隊演算法產生一組建議（避開最近幾場的重複組合）。只是建議，不會存檔。",
        "input_schema": {
            "type": "object",
            "properties": {
                "players": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要個別分配的球員名字",
                },
                "fixed_groups": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                    "description": "一定要同隊的組合，每組最多 3 人；沒有就給空陣列",
                },
                "avoid_recent_count": {
                    "type": "integer",
                    "description": "要避開最近幾場的組合，預設 1",
                },
            },
            "required": ["players"],
        },
    },
    {
        "name": "save_teams",
        "description": "驗證並把分隊結果存成今天的紀錄（覆蓋今天已有的紀錄）。每隊 1 到 3 人，同一個人不能出現兩次。只有使用者真的要分隊時才呼叫。",
        "input_schema": {
            "type": "object",
            "properties": {
                "teams": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                    "description": "每個元素是一隊的球員名字",
                },
            },
            "required": ["teams"],
        },
    },
    {
        "name": "remember",
        "description": "記下一則以後還用得上的長期筆記。一則只寫一件事，寫成完整句子。",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "筆記內容"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "forget",
        "description": "刪除一則長期筆記。memory_id 是筆記前面方括號裡的 id。",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
            },
            "required": ["memory_id"],
        },
    },
]


class ToolInputError(Exception):
    """工具參數有問題；訊息會回給模型讓它修正。"""


def _as_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _as_name_list(value: Any, field: str) -> List[str]:
    if not isinstance(value, list):
        raise ToolInputError(f"{field} 必須是字串陣列")
    names = [str(v).strip() for v in value if str(v).strip()]
    return names


class AIAssistant:
    """Claude 驅動的分隊助理。

    resolve_players(names) -> (players, mapping_info)
        既有的別名對應（LineMessageHandler._create_players_from_names）
    suggest_teams(groups, individuals, avoid_recent_count) -> [(teams, score), ...]
        既有的權重分隊演算法
    store_teams(teams) -> bool
        既有的寫入邏輯（存成今天的 attendance）
    """

    def __init__(
        self,
        db: Database,
        resolve_players: Callable,
        suggest_teams: Callable,
        store_teams: Callable,
        client: Any = None,
        model: Optional[str] = None,
        effort: Optional[str] = None,
        logger: Any = None,
    ):
        self.db = db
        self._resolve_players = resolve_players
        self._suggest_teams = suggest_teams
        self._store_teams = store_teams
        self._client = client
        self.model = model or os.getenv("AI_MODEL") or DEFAULT_MODEL
        self.effort = effort or os.getenv("AI_EFFORT") or "medium"
        self.logger = logger

    # ------------------------------------------------------------------ 基本

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def is_configured(self) -> bool:
        if self._client is not None:
            return True
        return anthropic is not None and bool(
            os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        )

    def _get_client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(
                timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
            )
        return self._client

    # ------------------------------------------------------------------ 記憶

    def list_memories(self, scope_id: str) -> List[Dict[str, str]]:
        cursor = self.db.ai_memories.find({"scope_id": scope_id}).sort("created_at", 1)
        return [{"id": str(doc["_id"]), "content": doc.get("content", "")} for doc in cursor]

    def _load_history(self, scope_id: str) -> List[Dict[str, str]]:
        docs = list(
            self.db.ai_conversations.find({"scope_id": scope_id})
            .sort("created_at", -1)
            .limit(HISTORY_MESSAGES)
        )
        docs.reverse()
        history = [{"role": d["role"], "content": d["content"]} for d in docs]
        # API 要求第一則是 user
        while history and history[0]["role"] != "user":
            history.pop(0)
        return history

    def _save_turn(self, scope_id: str, user_text: str, answer: str) -> None:
        now = _utcnow()
        self.db.ai_conversations.insert_many(
            [
                {"scope_id": scope_id, "role": "user", "content": user_text, "created_at": now},
                {
                    "scope_id": scope_id,
                    "role": "assistant",
                    "content": answer,
                    # 晚 1 毫秒，確保排序時 assistant 在 user 之後
                    "created_at": now + timedelta(milliseconds=1),
                },
            ]
        )
        # 只保留最近 HISTORY_KEEP 則
        old = list(
            self.db.ai_conversations.find({"scope_id": scope_id}, {"_id": 1})
            .sort("created_at", -1)
            .skip(HISTORY_KEEP)
        )
        if old:
            self.db.ai_conversations.delete_many({"_id": {"$in": [d["_id"] for d in old]}})

    def reset_conversation(self, scope_id: str) -> int:
        """清掉短期對話（長期筆記保留）。回傳刪除的則數。"""
        return self.db.ai_conversations.delete_many({"scope_id": scope_id}).deleted_count

    # ------------------------------------------------------------------ 工具

    def _tool_get_recent_games(self, scope_id: str, args: Dict) -> Any:
        limit = _as_int(args.get("limit"), 5, 1, 30)
        games = stats_service.get_recent_divisions(self.db, scope_id, limit=limit)
        return [
            {
                "date": g["date"],
                "teams": [[m["name"] for m in t["members"]] for t in g["teams"]],
            }
            for g in games
        ]

    def _tool_get_player_stats(self, scope_id: str, args: Dict) -> Any:
        summary = stats_service.get_group_summary(self.db, scope_id)
        players = stats_service.get_player_stats(self.db, scope_id)
        return {
            "total_sessions": summary["total_sessions"],
            "latest_session_date": summary["latest_session_date"],
            "players": [
                {"name": p["name"], "appearances": p["appearances"], "last_seen": p["last_seen"]}
                for p in players
            ],
        }

    def _tool_get_teammate_stats(self, scope_id: str, args: Dict) -> Any:
        name = str(args.get("player", "")).strip()
        if not name:
            raise ToolInputError("player 不能是空的")
        players, mapping = self._resolve_players([name])
        if mapping.get("strangers"):
            return {"found": False, "message": f"找不到叫「{name}」的球員（別名表裡沒有）"}
        key = players[0]["user_id"]
        result = stats_service.get_teammate_stats(self.db, key)
        result["found"] = True
        return result

    def _tool_get_top_pairs(self, scope_id: str, args: Dict) -> Any:
        top_n = _as_int(args.get("top_n"), 10, 1, 50)
        pairs = stats_service.get_pair_cooccurrence(self.db, scope_id, top_n=top_n)
        return [
            {"players": [p["nameA"], p["nameB"]], "times_same_team": p["count"]}
            for p in pairs["most_common"]
        ]

    def _tool_get_feedback_ranking(self, scope_id: str, args: Dict) -> Any:
        ranking = stats_service.get_team_estimation_ranking(self.db)
        ranking["note"] = (
            "名次 1 = 最強。delta = 體感名次 - 預期名次；"
            "delta > 0 表示實際比預期弱（被高估），delta < 0 表示實際比預期強（被低估）。"
        )
        return ranking

    def _tool_suggest_teams_by_algorithm(self, scope_id: str, args: Dict) -> Any:
        individuals = _as_name_list(args.get("players", []), "players")
        raw_groups = args.get("fixed_groups") or []
        if not isinstance(raw_groups, list):
            raise ToolInputError("fixed_groups 必須是陣列的陣列")
        groups = [g for g in (_as_name_list(g, "fixed_groups") for g in raw_groups) if g]
        for group in groups:
            if len(group) > MAX_TEAM_SIZE:
                raise ToolInputError(f"固定同隊的組合最多 {MAX_TEAM_SIZE} 人：{group}")
        total = len(individuals) + sum(len(g) for g in groups)
        if total == 0:
            raise ToolInputError("沒有任何球員")
        if total <= 4:
            return {"message": f"只有 {total} 人，演算法不分隊（4 人以下直接一起打）。"}

        avoid = _as_int(args.get("avoid_recent_count"), 1, 1, 30)
        options = self._suggest_teams(groups, individuals, avoid)
        teams, score = options[0]
        return {
            "teams": [[p["name"] for p in team] for team in teams],
            "similarity_to_recent": score,
            "avoid_recent_count": avoid,
            "saved": False,
        }

    def _tool_save_teams(self, scope_id: str, args: Dict) -> Any:
        raw_teams = args.get("teams")
        if not isinstance(raw_teams, list) or not raw_teams:
            raise ToolInputError("teams 必須是非空的陣列")
        teams_names = [_as_name_list(t, "teams") for t in raw_teams]

        for index, names in enumerate(teams_names, 1):
            if not names:
                raise ToolInputError(f"隊伍 {index} 是空的")
            if len(names) > MAX_TEAM_SIZE:
                raise ToolInputError(f"隊伍 {index} 有 {len(names)} 人，每隊最多 {MAX_TEAM_SIZE} 人")

        all_names = [n for names in teams_names for n in names]
        if len(set(all_names)) != len(all_names):
            dup = sorted({n for n in all_names if all_names.count(n) > 1})
            raise ToolInputError(f"名字重複出現：{dup}")

        # 一次解析所有名字（路人編號才不會重複），再照輸入名字分回各隊
        players, mapping = self._resolve_players(all_names)
        by_input = {p["input_name"]: p for p in players}
        missing = [n for n in all_names if n not in by_input]
        if missing:
            raise ToolInputError(
                f"這些名字跟名單裡其他名字是同一個人（別名重複）：{missing}"
            )

        teams = [[by_input[n] for n in names] for names in teams_names]
        if not self._store_teams(teams):
            raise ToolInputError("寫入資料庫失敗")

        return {
            "saved": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "teams": [[p["name"] for p in team] for team in teams],
            "unknown_players": [
                {"input": s["input"], "saved_as": s["stranger"]}
                for s in mapping.get("strangers", [])
            ],
        }

    def _tool_remember(self, scope_id: str, args: Dict) -> Any:
        content = str(args.get("content", "")).strip()
        if not content:
            raise ToolInputError("content 不能是空的")
        if len(content) > MAX_MEMORY_CHARS:
            raise ToolInputError(f"筆記太長（上限 {MAX_MEMORY_CHARS} 字），請濃縮成一件事")
        if self.db.ai_memories.count_documents({"scope_id": scope_id}) >= MAX_MEMORIES:
            raise ToolInputError(f"筆記已達上限 {MAX_MEMORIES} 則，請先用 forget 刪掉過時的")
        result = self.db.ai_memories.insert_one(
            {"scope_id": scope_id, "content": content, "created_at": _utcnow()}
        )
        return {"saved": True, "memory_id": str(result.inserted_id)}

    def _tool_forget(self, scope_id: str, args: Dict) -> Any:
        memory_id = str(args.get("memory_id", "")).strip()
        try:
            oid = ObjectId(memory_id)
        except (InvalidId, TypeError):
            raise ToolInputError(f"memory_id 格式不對：{memory_id}")
        deleted = self.db.ai_memories.delete_one({"_id": oid, "scope_id": scope_id}).deleted_count
        if not deleted:
            raise ToolInputError(f"找不到這則筆記：{memory_id}")
        return {"deleted": True}

    def _run_tool(self, scope_id: str, name: str, args: Any) -> Dict[str, Any]:
        """執行一個工具，回傳 tool_result 的 content / is_error。"""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None or name not in {t["name"] for t in TOOLS}:
            return {"content": f"沒有這個工具：{name}", "is_error": True}
        if not isinstance(args, dict):
            return {"content": "工具參數必須是物件", "is_error": True}
        try:
            result = handler(scope_id, args)
        except ToolInputError as e:
            return {"content": str(e), "is_error": True}
        except Exception as e:  # 工具內部錯誤也回給模型，讓它能換個方式回答
            self._log(f"[AI] tool {name} failed: {e!r}")
            return {"content": f"工具執行失敗：{e}", "is_error": True}
        return {"content": json.dumps(result, ensure_ascii=False, default=str), "is_error": False}

    # ------------------------------------------------------------------ 對話

    def _build_user_content(self, scope_id: str, user_text: str) -> str:
        memories = self.list_memories(scope_id)
        if memories:
            notes = "\n".join(f"[{m['id']}] {m['content']}" for m in memories)
        else:
            notes = "（目前沒有）"
        today = datetime.now()
        weekday = "一二三四五六日"[today.weekday()]
        return (
            f"今天日期：{today.strftime('%Y-%m-%d')}（星期{weekday}）\n"
            f"長期筆記：\n{notes}\n\n"
            f"使用者訊息：\n{user_text}"
        )

    def ask(self, scope_id: str, user_text: str) -> str:
        """回答一則訊息。一定回傳可以直接傳給使用者的文字，不會丟例外。"""
        if not self.is_configured():
            return "⚠️ AI 功能尚未設定（缺少 ANTHROPIC_API_KEY）"

        messages: List[Dict[str, Any]] = self._load_history(scope_id)
        messages.append({"role": "user", "content": self._build_user_content(scope_id, user_text)})

        try:
            answer = self._converse(scope_id, messages)
        except Exception as e:
            self._log(f"[AI] request failed: {e!r}")
            return _describe_error(e)

        try:
            self._save_turn(scope_id, user_text, answer)
        except Exception as e:
            self._log(f"[AI] failed to save conversation: {e!r}")
        return answer

    def _converse(self, scope_id: str, messages: List[Dict[str, Any]]) -> str:
        client = self._get_client()
        deadline = time.monotonic() + TIME_BUDGET_SECONDS

        for round_number in range(1, MAX_TOOL_ROUNDS + 1):
            response = client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": self.effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
            usage = getattr(response, "usage", None)
            self._log(
                f"[AI] round {round_number} stop_reason={response.stop_reason} "
                f"in={getattr(usage, 'input_tokens', '?')} out={getattr(usage, 'output_tokens', '?')}"
            )

            text = "\n".join(
                block.text for block in response.content if block.type == "text" and block.text
            ).strip()

            if response.stop_reason == "refusal":
                return "⚠️ 這個問題我沒辦法回答，換個問法試試。"

            if response.stop_reason != "tool_use":
                if response.stop_reason == "max_tokens" and text:
                    text += "\n\n（回覆太長被截斷了）"
                return text or "⚠️ 我沒有產生回覆，請再問一次。"

            # 執行這一輪要求的所有工具，結果放在同一則 user 訊息裡
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                outcome = self._run_tool(scope_id, block.name, block.input)
                self._log(f"[AI] tool {block.name} error={outcome['is_error']}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": outcome["content"],
                        "is_error": outcome["is_error"],
                    }
                )
            messages.append({"role": "user", "content": results})

            if time.monotonic() > deadline:
                return "⚠️ 這題查太久了，我先停下來。請把問題縮小一點再問一次。"

        return "⚠️ 這題需要的步驟太多，我先停下來。請把問題拆小一點再問。"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _describe_error(error: Exception) -> str:
    """把 API 錯誤轉成給使用者看的訊息。"""
    if anthropic is not None:
        if isinstance(error, anthropic.AuthenticationError):
            return "⚠️ AI 的 API key 無效，請檢查 ANTHROPIC_API_KEY。"
        if isinstance(error, anthropic.PermissionDeniedError):
            return "⚠️ AI 的 API key 沒有權限使用這個模型。"
        if isinstance(error, anthropic.RateLimitError):
            return "⚠️ AI 現在太忙（被限流），請稍等一下再問。"
        if isinstance(error, anthropic.APITimeoutError):
            return "⚠️ AI 回應逾時，請再問一次。"
        if isinstance(error, anthropic.APIConnectionError):
            return "⚠️ 連不上 AI 服務，請稍後再試。"
        if isinstance(error, anthropic.APIStatusError):
            if error.status_code >= 500:
                return "⚠️ AI 服務暫時有問題，請稍後再試。"
            return f"⚠️ AI 請求被拒絕（{error.status_code}），請看伺服器 log。"
    return "⚠️ AI 處理失敗，請稍後再試。"
