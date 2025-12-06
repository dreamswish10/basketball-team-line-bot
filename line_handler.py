#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import List
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from models import Player, PlayerDatabase
from team_algorithm import TeamGenerator

class LineMessageHandler:
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api
        self.team_generator = TeamGenerator()
    
    def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        try:
            # 根據指令路由到不同的處理函數
            if message_text.startswith('/register') or message_text.startswith('註冊'):
                self._handle_register_command(event, message_text)
            elif message_text.startswith('/list') or message_text == '球員列表':
                self._handle_list_command(event)
            elif message_text.startswith('/team') or message_text.startswith('分隊'):
                self._handle_team_command(event, message_text)
            elif message_text.startswith('/profile') or message_text == '我的資料':
                self._handle_profile_command(event, user_id)
            elif message_text.startswith('/delete') or message_text == '刪除資料':
                self._handle_delete_command(event, user_id)
            elif message_text.startswith('/help') or message_text == '幫助' or message_text == '說明':
                self._handle_help_command(event)
            elif message_text == '開始':
                self._handle_start_command(event)
            else:
                self._handle_unknown_command(event)
                
        except Exception as e:
            print(f"Error handling message: {e}")
            self._send_message(event.reply_token, "❌ 系統發生錯誤，請稍後再試")
    
    def _handle_register_command(self, event, message_text):
        """處理球員註冊指令"""
        user_id = event.source.user_id
        
        # 解析註冊指令：/register 姓名 投籃技能 防守技能 體力
        patterns = [
            r'/register\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)',  # /register name 8 7 9
            r'註冊\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)',      # 註冊 name 8 7 9
            r'/register\s+(.+)',                           # /register name (使用預設值)
            r'註冊\s+(.+)',                                # 註冊 name (使用預設值)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, message_text)
            if match:
                name = match.group(1).strip()
                
                if len(match.groups()) >= 4:  # 有技能參數
                    try:
                        shooting = int(match.group(2))
                        defense = int(match.group(3))
                        stamina = int(match.group(4))
                    except ValueError:
                        self._send_message(event.reply_token, "❌ 技能值必須是數字 (1-10)")
                        return
                else:  # 只有姓名，使用預設技能值
                    shooting = defense = stamina = 5
                
                # 驗證技能值範圍
                if not all(1 <= skill <= 10 for skill in [shooting, defense, stamina]):
                    self._send_message(event.reply_token, "❌ 技能值必須在 1-10 範圍內")
                    return
                
                # 創建球員
                player = Player(user_id, name, shooting, defense, stamina)
                
                if PlayerDatabase.create_player(player):
                    message = f"✅ 註冊成功！\n\n"
                    message += f"👤 球員：{player.name}\n"
                    message += f"🎯 投籃：{player.shooting_skill}/10\n"
                    message += f"🛡️ 防守：{player.defense_skill}/10\n"
                    message += f"💪 體力：{player.stamina}/10\n"
                    message += f"⭐ 總評：{player.overall_rating:.1f}/10"
                    
                    self._send_message(event.reply_token, message)
                else:
                    self._send_message(event.reply_token, "❌ 註冊失敗，請稍後再試")
                return
        
        # 如果沒有匹配到任何格式
        self._send_message(event.reply_token, 
            "❌ 格式錯誤\n\n正確格式：\n"
            "🔸 /register 姓名 投籃 防守 體力\n"
            "🔸 /register 姓名 (使用預設值 5)\n\n"
            "範例：/register 小明 8 7 9"
        )
    
    def _handle_list_command(self, event):
        """處理球員列表指令"""
        players = PlayerDatabase.get_all_players()
        
        if not players:
            message = "📋 目前沒有註冊的球員\n\n"
            message += "使用 /register 指令註冊球員"
        else:
            message = f"📋 球員列表 (共 {len(players)} 人)\n\n"
            
            for i, player in enumerate(players, 1):
                message += f"{i}. {player.name}\n"
                message += f"   投籃:{player.shooting_skill} 防守:{player.defense_skill} 體力:{player.stamina} "
                message += f"(總評:{player.overall_rating:.1f})\n"
            
            # 提供分隊建議
            suggestions = self.team_generator.suggest_optimal_teams(len(players))
            if suggestions:
                message += f"\n💡 分隊建議：\n"
                for num_teams, description in suggestions:
                    message += f"🔸 {description}\n"
        
        self._send_message(event.reply_token, message)
    
    def _handle_team_command(self, event, message_text):
        """處理分隊指令"""
        players = PlayerDatabase.get_all_players()
        
        if len(players) < 2:
            self._send_message(event.reply_token, "❌ 至少需要 2 位球員才能分隊")
            return
        
        # 解析隊伍數量
        num_teams = 2  # 預設 2 隊
        
        patterns = [
            r'/team\s+(\d+)',  # /team 3
            r'分隊\s+(\d+)',    # 分隊 3
        ]
        
        for pattern in patterns:
            match = re.match(pattern, message_text)
            if match:
                try:
                    num_teams = int(match.group(1))
                except ValueError:
                    pass
                break
        
        # 驗證隊伍數量
        if num_teams < 2:
            self._send_message(event.reply_token, "❌ 至少需要分成 2 隊")
            return
        
        if num_teams > len(players):
            self._send_message(event.reply_token, f"❌ 隊伍數量 ({num_teams}) 不能超過球員數量 ({len(players)})")
            return
        
        # 生成隊伍
        try:
            teams = self.team_generator.generate_teams(players, num_teams)
            message = self.team_generator.format_teams_message(teams)
            self._send_message(event.reply_token, message)
        except Exception as e:
            print(f"Error generating teams: {e}")
            self._send_message(event.reply_token, "❌ 分隊失敗，請稍後再試")
    
    def _handle_profile_command(self, event, user_id):
        """處理個人資料查詢指令"""
        player = PlayerDatabase.get_player(user_id)
        
        if player:
            message = f"👤 個人資料\n\n"
            message += f"姓名：{player.name}\n"
            message += f"🎯 投籃：{player.shooting_skill}/10\n"
            message += f"🛡️ 防守：{player.defense_skill}/10\n"
            message += f"💪 體力：{player.stamina}/10\n"
            message += f"⭐ 總評：{player.overall_rating:.1f}/10\n"
            message += f"📅 註冊時間：{player.created_at[:10]}"
        else:
            message = "❌ 您還沒有註冊\n\n"
            message += "使用 /register 指令註冊球員"
        
        self._send_message(event.reply_token, message)
    
    def _handle_delete_command(self, event, user_id):
        """處理刪除資料指令"""
        if PlayerDatabase.delete_player(user_id):
            message = "✅ 您的球員資料已刪除"
        else:
            message = "❌ 刪除失敗或您還沒有註冊"
        
        self._send_message(event.reply_token, message)
    
    def _handle_help_command(self, event):
        """處理幫助指令"""
        message = "🏀 籃球分隊機器人使用說明\n\n"
        message += "📝 基本指令：\n"
        message += "🔸 /register 姓名 投籃 防守 體力\n"
        message += "   註冊球員 (技能值 1-10)\n"
        message += "🔸 /list\n"
        message += "   查看所有球員\n"
        message += "🔸 /team [隊數]\n"
        message += "   自動分隊 (預設 2 隊)\n"
        message += "🔸 /profile\n"
        message += "   查看個人資料\n"
        message += "🔸 /delete\n"
        message += "   刪除個人資料\n\n"
        message += "📖 使用範例：\n"
        message += "• /register 小明 8 7 9\n"
        message += "• /team 3\n"
        message += "• 分隊 2\n\n"
        message += "⚠️ 注意事項：\n"
        message += "• 技能值範圍：1-10\n"
        message += "• 至少需要 2 位球員才能分隊\n"
        message += "• 系統會自動平衡隊伍實力"
        
        self._send_message(event.reply_token, message)
    
    def _handle_start_command(self, event):
        """處理開始指令"""
        message = "🏀 歡迎使用籃球分隊機器人！\n\n"
        message += "請先註冊球員資料：\n"
        message += "/register 姓名 投籃 防守 體力\n\n"
        message += "範例：/register 小明 8 7 9\n\n"
        message += "需要幫助請輸入：/help"
        
        # 添加快速回覆按鈕
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="📝 註冊球員", text="/register ")),
            QuickReplyButton(action=MessageAction(label="📋 球員列表", text="/list")),
            QuickReplyButton(action=MessageAction(label="🏀 開始分隊", text="/team")),
            QuickReplyButton(action=MessageAction(label="❓ 使用說明", text="/help")),
        ])
        
        self._send_message(event.reply_token, message, quick_reply=quick_reply)
    
    def _handle_unknown_command(self, event):
        """處理未知指令"""
        message = "❓ 不認識的指令\n\n"
        message += "請使用以下指令：\n"
        message += "🔸 /help - 查看使用說明\n"
        message += "🔸 /register - 註冊球員\n"
        message += "🔸 /list - 球員列表\n"
        message += "🔸 /team - 開始分隊"
        
        self._send_message(event.reply_token, message)
    
    def _send_message(self, reply_token, message_text, quick_reply=None):
        """發送訊息"""
        try:
            message = TextSendMessage(text=message_text, quick_reply=quick_reply)
            self.line_bot_api.reply_message(reply_token, message)
        except Exception as e:
            print(f"Error sending message: {e}")

# 測試功能
if __name__ == "__main__":
    # 這裡可以加入單元測試
    print("LINE Bot 訊息處理器已準備就緒")