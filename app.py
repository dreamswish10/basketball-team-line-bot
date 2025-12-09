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
from config import Config
from models import init_db, Player
from line_handler import LineMessageHandler
from group_manager import GroupManager

app = Flask(__name__)
app.config.from_object(Config)

# LINE Bot 設定
line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])

# 初始化資料庫
init_db()

# LINE 訊息處理器
message_handler = LineMessageHandler(line_bot_api)

# 群組管理器
group_manager = GroupManager(line_bot_api)

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

    # 驗證 webhook 簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message_handler.handle_text_message(event)

@handler.add(PostbackEvent)
def handle_postback(event):
    message_handler.handle_postback_event(event)

@handler.add(JoinEvent)
def handle_join(event):
    """處理 Bot 加入群組事件"""
    if hasattr(event.source, 'group_id'):
        group_id = event.source.group_id
        app.logger.info(f"Bot joined group: {group_id}")
        
        try:
            # 自動同步群組成員
            group_manager.sync_group_members(group_id)
            
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
            
        except Exception as e:
            app.logger.error(f"Error handling join event: {e}")

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