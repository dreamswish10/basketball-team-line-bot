#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""AI 助理（src/services/ai_service.py）的單元測試。

不打真的 Claude API：用 FakeClient 依序回放預先寫好的回應，
資料庫用 mongomock。執行：pytest tests/test_ai_service.py
"""

import json
from types import SimpleNamespace

import pytest

mongomock = pytest.importorskip("mongomock")

from src.services import stats_service
from src.services.ai_service import AIAssistant, TOOLS

SCOPE = "group-1"
KNOWN = {"凱": "凱", "阿凱": "凱", "豪": "豪", "金": "金", "勇": "勇", "kin": "kin", "🥛": "🥛"}


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(name, tool_input, block_id="tu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def response(blocks, stop_reason="end_turn"):
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )


class FakeClient:
    """回放預先準備的回應，並記下每次請求的參數。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # messages 之後還會被 append，先複製一份當下的狀態
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._responses.pop(0)


def resolve_players(names):
    """模擬 LineMessageHandler._create_players_from_names（別名對應 + 去重）。"""
    players, seen = [], set()
    mapping = {"identified": [], "strangers": []}
    stranger = 1
    for name in names:
        if name in KNOWN:
            user_id = display = KNOWN[name]
            mapping["identified"].append({"input": name, "mapped": user_id})
        else:
            user_id, display = f"STRANGER_{stranger}", f"路人{stranger}"
            mapping["strangers"].append({"input": name, "stranger": display})
            stranger += 1
        if user_id not in seen:
            seen.add(user_id)
            players.append({"user_id": user_id, "name": display, "input_name": name})
    return players, mapping


@pytest.fixture
def db():
    database = mongomock.MongoClient().db
    database.attendances.insert_many([
        {"date": "2026-11-01", "teams": [
            {"teamId": "team_1", "members": [{"userId": "凱", "name": "凱"}, {"userId": "豪", "name": "豪"}]},
            {"teamId": "team_2", "members": [{"userId": "金", "name": "金"}, {"userId": "勇", "name": "勇"}]},
        ]},
        {"date": "2026-11-08", "teams": [
            {"teamId": "team_1", "members": [{"userId": "凱", "name": "凱"}, {"userId": "金", "name": "金"}]},
            {"teamId": "team_2", "members": [{"userId": "豪", "name": "豪"}]},
        ]},
    ])
    return database


def make_assistant(db, responses, stored=None):
    stored = stored if stored is not None else []
    client = FakeClient(responses)

    def store_teams(teams):
        stored.append(teams)
        return True

    def suggest_teams(groups, individuals, avoid):
        players, _ = resolve_players([n for g in groups for n in g] + individuals)
        return [([players[:3], players[3:]], 0)]

    assistant = AIAssistant(
        db,
        resolve_players=resolve_players,
        suggest_teams=suggest_teams,
        store_teams=store_teams,
        client=client,
    )
    return assistant, client, stored


def tool_result(client, request_index=-1):
    """取出某次請求裡最後一則 tool_result。"""
    block = client.requests[request_index]["messages"][-1]["content"][0]
    return block


def test_plain_answer_is_returned_and_remembered(db):
    assistant, client, _ = make_assistant(db, [response([text_block("哈囉")])])
    assert assistant.ask(SCOPE, "嗨") == "哈囉"

    request = client.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["tools"] is TOOLS
    assert "使用者訊息：\n嗨" in request["messages"][-1]["content"]

    saved = list(db.ai_conversations.find({"scope_id": SCOPE}).sort("created_at", 1))
    assert [(d["role"], d["content"]) for d in saved] == [("user", "嗨"), ("assistant", "哈囉")]


def test_previous_turns_are_sent_as_history(db):
    assistant, client, _ = make_assistant(
        db, [response([text_block("一")]), response([text_block("二")])]
    )
    assistant.ask(SCOPE, "第一題")
    assistant.ask(SCOPE, "第二題")

    messages = client.requests[1]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "第一題"   # 歷史只存原始訊息，不含日期與筆記
    assert messages[1]["content"] == "一"
    # 別的聊天室看不到這段對話
    assert assistant._load_history("other-group") == []


def test_tool_loop_feeds_results_back(db):
    assistant, client, _ = make_assistant(db, [
        response([tool_block("get_teammate_stats", {"player": "阿凱"})], "tool_use"),
        response([text_block("你最常跟豪、金同隊")]),
    ])
    assert assistant.ask(SCOPE, "我是凱，我最常跟誰同隊") == "你最常跟豪、金同隊"

    block = tool_result(client)
    assert block["tool_use_id"] == "tu_1" and block["is_error"] is False
    data = json.loads(block["content"])
    assert data["player"] == "凱" and data["appearances"] == 2
    by_name = {t["name"]: t for t in data["teammates"]}
    assert by_name["豪"] == {"name": "豪", "times_same_team": 1, "times_same_session": 2}
    assert by_name["金"] == {"name": "金", "times_same_team": 1, "times_same_session": 2}
    assert by_name["勇"] == {"name": "勇", "times_same_team": 0, "times_same_session": 1}


def test_parallel_tool_calls_return_in_one_message(db):
    assistant, client, _ = make_assistant(db, [
        response([
            tool_block("get_recent_games", {"limit": 1}, "a"),
            tool_block("get_top_pairs", {}, "b"),
        ], "tool_use"),
        response([text_block("好")]),
    ])
    assistant.ask(SCOPE, "最近怎麼分")
    results = client.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    games = json.loads(results[0]["content"])
    assert games == [{"date": "2026-11-08", "teams": [["凱", "金"], ["豪"]]}]


def test_save_teams_stores_resolved_players(db):
    assistant, client, stored = make_assistant(db, [
        response([tool_block("save_teams", {"teams": [["阿凱", "金", "小白"], ["豪", "勇"]]})], "tool_use"),
        response([text_block("分好了")]),
    ])
    assistant.ask(SCOPE, "幫忙分隊")

    data = json.loads(tool_result(client)["content"])
    assert data["saved"] is True
    assert data["teams"] == [["凱", "金", "路人1"], ["豪", "勇"]]
    assert data["unknown_players"] == [{"input": "小白", "saved_as": "路人1"}]
    assert [[p["user_id"] for p in team] for team in stored[0]] == [
        ["凱", "金", "STRANGER_1"], ["豪", "勇"]
    ]


@pytest.mark.parametrize("teams, expected", [
    ([["凱", "豪", "金", "勇"]], "每隊最多 3 人"),
    ([["凱", "豪"], ["凱", "金"]], "名字重複出現"),
    ([["凱", "豪"], ["阿凱", "金"]], "同一個人"),       # 別名指向同一人
    ([["凱"], []], "是空的"),
    ([], "非空的陣列"),
    ("凱,豪", "非空的陣列"),
])
def test_save_teams_rejects_invalid_teams(db, teams, expected):
    assistant, client, stored = make_assistant(db, [
        response([tool_block("save_teams", {"teams": teams})], "tool_use"),
        response([text_block("抱歉")]),
    ])
    assistant.ask(SCOPE, "幫忙分隊")
    block = tool_result(client)
    assert block["is_error"] is True and expected in block["content"]
    assert stored == []


def test_suggest_teams_uses_algorithm_and_does_not_save(db):
    names = ["凱", "豪", "金", "勇", "kin"]
    assistant, client, stored = make_assistant(db, [
        response([tool_block("suggest_teams_by_algorithm", {"players": names})], "tool_use"),
        response([text_block("建議如下")]),
    ])
    assistant.ask(SCOPE, "如果今天這五個人會怎麼分")
    data = json.loads(tool_result(client)["content"])
    assert data["teams"] == [["凱", "豪", "金"], ["勇", "kin"]] and data["saved"] is False
    assert stored == []


def test_remember_then_notes_appear_in_next_prompt(db):
    assistant, client, _ = make_assistant(db, [
        response([tool_block("remember", {"content": "凱跟豪不要同隊"})], "tool_use"),
        response([text_block("記住了")]),
        response([text_block("我記得一件事")]),
    ])
    assistant.ask(SCOPE, "記住凱跟豪不要同隊")
    memories = assistant.list_memories(SCOPE)
    assert [m["content"] for m in memories] == ["凱跟豪不要同隊"]

    assistant.ask(SCOPE, "你記得什麼")
    prompt = client.requests[2]["messages"][-1]["content"]
    assert f"[{memories[0]['id']}] 凱跟豪不要同隊" in prompt


def test_forget_only_deletes_within_scope(db):
    assistant, client, _ = make_assistant(db, [
        response([tool_block("remember", {"content": "金是中鋒"})], "tool_use"),
        response([text_block("好")]),
    ])
    assistant.ask(SCOPE, "記住金是中鋒")
    memory_id = assistant.list_memories(SCOPE)[0]["id"]

    wrong_scope = assistant._run_tool("other-group", "forget", {"memory_id": memory_id})
    assert wrong_scope["is_error"] is True
    assert len(assistant.list_memories(SCOPE)) == 1

    assert assistant._run_tool(SCOPE, "forget", {"memory_id": memory_id})["is_error"] is False
    assert assistant.list_memories(SCOPE) == []
    assert assistant._run_tool(SCOPE, "forget", {"memory_id": "not-an-id"})["is_error"] is True


def test_unknown_tool_and_bad_input_are_reported_to_model(db):
    assistant, _, _ = make_assistant(db, [])
    assert assistant._run_tool(SCOPE, "drop_database", {})["is_error"] is True
    assert assistant._run_tool(SCOPE, "get_recent_games", "oops")["is_error"] is True
    assert assistant._run_tool(SCOPE, "remember", {"content": "  "})["is_error"] is True
    unknown = json.loads(assistant._run_tool(SCOPE, "get_teammate_stats", {"player": "路人甲"})["content"])
    assert unknown["found"] is False


def test_reset_clears_conversation_but_keeps_memories(db):
    assistant, _, _ = make_assistant(db, [
        response([tool_block("remember", {"content": "金是中鋒"})], "tool_use"),
        response([text_block("好")]),
    ])
    assistant.ask(SCOPE, "記住金是中鋒")
    assert assistant.reset_conversation(SCOPE) == 2
    assert assistant._load_history(SCOPE) == []
    assert len(assistant.list_memories(SCOPE)) == 1


def test_api_failure_returns_message_and_saves_nothing(db):
    assistant, client, _ = make_assistant(db, [])
    client.beta.messages.create = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    answer = assistant.ask(SCOPE, "嗨")
    assert answer.startswith("⚠️")
    assert db.ai_conversations.count_documents({}) == 0


def test_refusal_and_runaway_tool_loop_stop_cleanly(db):
    assistant, _, _ = make_assistant(db, [response([], "refusal")])
    assert assistant.ask(SCOPE, "x").startswith("⚠️")

    looping = [response([tool_block("get_player_stats", {})], "tool_use") for _ in range(20)]
    assistant, client, _ = make_assistant(db, looping)
    assert "步驟太多" in assistant.ask(SCOPE, "x")
    assert len(client.requests) == 8


def test_not_configured_without_key_or_client(db, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assistant = AIAssistant(db, resolve_players, lambda *a: [], lambda t: True)
    assert "尚未設定" in assistant.ask(SCOPE, "嗨")


def test_teammate_stats_for_player_without_games(db):
    result = stats_service.get_teammate_stats(db, "kin")
    assert result == {"player": "kin", "appearances": 0, "teammates": []}
