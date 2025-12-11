#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, PostbackEvent,
    JoinEvent, MemberJoinedEvent, MemberLeftEvent, LeaveEvent
)
import os
from src.config import Config
from src.database.mongodb import init_mongodb, get_database
from src.models.player import Player
from src.models.mongodb_models import (
    PlayersRepository,
    GroupsRepository,
    GroupMembersRepository,
    DivisionsRepository,
    AttendancesRepository,
    AliasMapRepository
)
from src.handlers.line_handler import LineMessageHandler
from src.handlers.group_manager import GroupManager

app = Flask(__name__)
app.config.from_object(Config)

# LINE Bot 設定
line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])

# 初始化 MongoDB
init_mongodb()

# 取得 MongoDB database instance
db = get_database()

# 初始化 Repositories
players_repo = PlayersRepository(db)
groups_repo = GroupsRepository(db)
group_members_repo = GroupMembersRepository(db)
divisions_repo = DivisionsRepository(db)
attendances_repo = AttendancesRepository(db)
alias_map_repo = AliasMapRepository(db)

def setup_hardcoded_aliases():
    """設定硬編碼的別名（內部使用）"""
    try:
        alias_repo = AliasMapRepository(db)
        
        # 硬編碼的別名設定 - 內部成員別名 (增強格式)
        # 直接使用成員名稱作為用戶 ID，無需 LINE User ID
        hardcoded_aliases = {
            # 內部團隊成員別名設定
            "勇": {
                "exact": ["勇"],
                "patterns": ["*勇*", "勇*"],
                "regex": [r"\d+勇", r"勇\d+"]
            },
            "舊": {
                "exact": ["舊"],
                "patterns": ["*舊*", "舊*"],
                "regex": [r"\d+舊", r"舊\d+"]
            },
            "宇": {
                "exact": ["宇"],
                "patterns": ["*宇*", "宇*"],
                "regex": [r"\d+宇", r"宇\d+"]
            },
            "傑": {
                "exact": ["傑"],
                "patterns": ["*傑*", "傑*"],
                "regex": [r"\d+傑", r"傑\d+"]
            },
            "豪": {
                "exact": ["豪"],
                "patterns": ["*豪*", "豪*"],
                "regex": [r"\d+豪", r"豪\d+"]
            },
            "翔": {
                "exact": ["翔"],
                "patterns": ["*翔*", "翔*"],
                "regex": [r"\d+翔", r"翔\d+"]
            },
            "華": {
                "exact": ["華"],
                "patterns": ["*華*", "華*"],
                "regex": [r"\d+華", r"華\d+"]
            },
            "圈": {
                "exact": ["圈"],
                "patterns": ["*圈*", "圈*"],
                "regex": [r"\d+圈", r"圈\d+"]
            },
            "小明": {
                "exact": ["小明"],
                "patterns": ["*小明*", "小明*"],
                "regex": [r"\d+小明", r"小明\d+"]
            },
            "軍": {
                "exact": ["軍"],
                "patterns": ["*軍*", "軍*"],
                "regex": [r"\d+軍", r"軍\d+"]
            },
            "展": {
                "exact": ["展"],
                "patterns": ["*展*", "展*"],
                "regex": [r"\d+展", r"展\d+"]
            },
            "盟": {
                "exact": ["盟"],
                "patterns": ["*盟*", "盟*"],
                "regex": [r"\d+盟", r"盟\d+"]
            },
            "小林": {
                "exact": ["小林"],
                "patterns": ["*小林*", "小林*"],
                "regex": [r"\d+小林", r"小林\d+"]
            },
            "諴": {
                "exact": ["諴"],
                "patterns": ["*諴*", "諴*"],
                "regex": [r"\d+諴", r"諴\d+"]
            },
            "榮": {
                "exact": ["榮"],
                "patterns": ["*榮*", "榮*"],
                "regex": [r"\d+榮", r"榮\d+"]
            },
            "細": {
                "exact": ["細"],
                "patterns": ["*細*", "細*"],
                "regex": [r"\d+細", r"細\d+"]
            },
            "69": {
                "exact": ["69"],
                "patterns": ["*69*"],  # 數字名稱主要使用精確和模式匹配
                "regex": []
            },
            "凱": {
                "exact": ["凱"],
                "patterns": ["*凱*", "凱*"],
                "regex": [r"\d+凱", r"凱\d+"]
            },
            "奶": {
                "exact": ["奶"],
                "patterns": ["*奶*", "奶*", "*🥛", "🥛*", "*鴻", "鴻*"],
                "regex": [r"\d+奶", r"奶\d+"]
            },
            "金毛": {
                "exact": ["金毛"],
                "patterns": ["*金", "金*"],
                "regex": [r"\d+金毛", r"金毛\d+"]
            },
            "張律": {
                "exact": ["張律"],
                "patterns": ["*張律*", "張律*"],
                "regex": [r"\d+張律", r"張律\d+"]
            },  
            "Akin": {
                "exact": ["Akin"],
                "patterns": ["*Akin*", "Akin*", "kin*", "*kin"],
                "regex": [r"\d+Akin", r"Akin\d+"] 
            }
        }
        
        setup_count = 0
        
        for user_id, aliases in hardcoded_aliases.items():
            # 檢查是否已存在，避免重複設定
            existing_aliases = alias_repo.get_aliases_by_user_id(user_id)
            
            # 判斷是否為空（新格式或舊格式）
            is_empty = False
            if isinstance(existing_aliases, dict):
                # 新格式：檢查所有類型是否都為空
                is_empty = (not existing_aliases.get("exact") and 
                           not existing_aliases.get("patterns") and 
                           not existing_aliases.get("regex"))
            else:
                # 舊格式：檢查列表是否為空
                is_empty = not existing_aliases
                
            if is_empty:
                if alias_repo.create_or_update_alias(user_id, aliases):
                    # 格式化輸出別名信息
                    alias_info = []
                    if aliases.get("exact"):
                        alias_info.append(f"精確: {aliases['exact']}")
                    if aliases.get("patterns"):
                        alias_info.append(f"模式: {aliases['patterns']}")
                    if aliases.get("regex"):
                        alias_info.append(f"正則: {aliases['regex']}")
                    
                    app.logger.info(f"✅ 設定別名: {user_id} -> {'; '.join(alias_info)}")
                    setup_count += 1
                else:
                    app.logger.warning(f"❌ 設定別名失敗: {user_id}")
            else:
                app.logger.info(f"ℹ️ 用戶 {user_id} 已有別名，跳過設定")
                
        if setup_count > 0:
            app.logger.info(f"🎯 新增別名設定完成，共 {setup_count} 位用戶")
        else:
            app.logger.info("ℹ️ 所有別名已存在，無需設定")
            
    except Exception as e:
        app.logger.error(f"⚠️ 設定別名失敗: {e}")

# 在服務啟動時設定別名
setup_hardcoded_aliases()

# LINE 訊息處理器
message_handler = LineMessageHandler(
    line_bot_api,
    app.logger
)

# 群組管理器 (傳遞 repositories)
group_manager = GroupManager(
    line_bot_api,
    players_repo=players_repo,
    groups_repo=groups_repo,
    group_members_repo=group_members_repo,
    divisions_repo=divisions_repo
)

@app.route("/")
def hello():
    return "籃球分隊 LINE Bot 服務運行中 🏀"

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # 獲取 request body
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    app.logger.info("[WEBHOOK] Received webhook request")
    app.logger.info(f"[WEBHOOK] Signature: {signature[:20]}...")

    # 驗證 webhook 簽名
    try:
        app.logger.info("[WEBHOOK] Verifying signature...")
        handler.handle(body, signature)
        app.logger.info("[WEBHOOK] Signature verified successfully")
    except InvalidSignatureError:
        app.logger.error("[ERROR] Invalid signature - webhook verification failed")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message_text = event.message.text
    source_type = event.source.type

    app.logger.info(f"[WEBHOOK] Message event received")
    app.logger.info(f"[WEBHOOK] User ID: {user_id}")
    app.logger.info(f"[WEBHOOK] Source Type: {source_type}")
    app.logger.info(f"[WEBHOOK] Message Text: '{message_text}'")

    message_handler.handle_text_message(event)

@handler.add(PostbackEvent)
def handle_postback(event):
    message_handler.handle_postback_event(event)

@handler.add(JoinEvent)
def handle_join(event):
    """處理 Bot 加入群組事件"""
    if hasattr(event.source, 'group_id'):
        group_id = event.source.group_id

        # 增強：更詳細的開始日誌
        app.logger.info(f"[GROUP_JOIN] ========================================")
        app.logger.info(f"[GROUP_JOIN] Bot joined group: {group_id}")
        app.logger.info(f"[GROUP_JOIN] Starting member synchronization...")

        try:
            # 自動同步群組成員
            synced_count = group_manager.sync_group_members(group_id)

            # 新增：記錄同步結果
            app.logger.info(
                f"[GROUP_JOIN] Member synchronization completed: "
                f"{synced_count} members synced"
            )

            # 發送歡迎訊息
            welcome_message = (
                "🏀 籃球分隊機器人已加入群組！\n\n"
                "群組專用功能：\n"
                "🔹 /group_team - 使用群組成員分隊\n"
                "🔹 /group_players - 查看群組成員\n"
                "🔹 /group_stats - 群組統計資訊\n\n"
                "個人功能：\n"
                "🔹 /register - 詳細註冊\n"
                "🔹 /help - 完整說明"
            )

            line_bot_api.push_message(group_id, TextSendMessage(text=welcome_message))

            # 新增：記錄完成
            app.logger.info(f"[GROUP_JOIN] Welcome message sent to group {group_id}")
            app.logger.info(f"[GROUP_JOIN] ========================================")

        except Exception as e:
            app.logger.error(f"[GROUP_JOIN] Error handling join event: {e}")
            app.logger.info(f"[GROUP_JOIN] ========================================")

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    """處理新成員加入群組事件"""
    if hasattr(event.source, 'group_id'):
        group_id = event.source.group_id
        joined_users = event.joined.members
        
        app.logger.info(f"New members joined group {group_id}: {len(joined_users)} users")
        
        try:
            # 重新同步群組成員
            group_manager.sync_group_members(group_id)
            
        except Exception as e:
            app.logger.error(f"Error handling member joined event: {e}")

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    """處理成員離開群組事件"""
    if hasattr(event.source, 'group_id'):
        group_id = event.source.group_id
        left_users = event.left.members
        
        app.logger.info(f"Members left group {group_id}: {len(left_users)} users")
        
        try:
            # 移除非活動成員
            group_manager.remove_inactive_members(group_id)
            
        except Exception as e:
            app.logger.error(f"Error handling member left event: {e}")

@handler.add(LeaveEvent)
def handle_leave(event):
    """處理 Bot 離開群組事件"""
    if hasattr(event.source, 'group_id'):
        group_id = event.source.group_id
        app.logger.info(f"Bot left group: {group_id}")
        
        try:
            # 清理群組資料（可選）
            # 這裡可以選擇保留資料供將來使用，或清理資料
            pass
            
        except Exception as e:
            app.logger.error(f"Error handling leave event: {e}")

@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "basketball-team-generator"}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)