#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackEvent
import os
from config import Config
from models import init_db, Player
from line_handler import LineMessageHandler

app = Flask(__name__)
app.config.from_object(Config)

# LINE Bot 設定
line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])

# 初始化資料庫
init_db()

# LINE 訊息處理器
message_handler = LineMessageHandler(line_bot_api)

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

@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "basketball-team-generator"}

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)