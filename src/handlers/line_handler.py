#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import List
from linebot.models import (
    TextSendMessage, QuickReply, QuickReplyButton, MessageAction,
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    PostbackAction, URIAction, PostbackEvent
)

# 處理不同版本的 SpacerComponent 導入 - 使用安全的方式
SPACER_AVAILABLE = False
try:
    from linebot.models import SpacerComponent
    SPACER_AVAILABLE = True
except ImportError:
    try:
        from linebot.models.flex_message import SpacerComponent
        SPACER_AVAILABLE = True
    except ImportError:
        try:
            from linebot.models import Spacer as SpacerComponent
            SPACER_AVAILABLE = True
        except ImportError:
            # SpacerComponent 不可用，我們將使用替代方案
            SpacerComponent = None
from src.models.mongodb_models import AliasMapRepository, AttendancesRepository
from src.database.mongodb import get_database
import random

class LineMessageHandler:
    def __init__(self, line_bot_api, logger=None):
        import linebot
        self.line_bot_api = line_bot_api
        self.logger = logger
        
        # 記錄 LINE Bot SDK 版本
        self._log_info(f"=== LINE Bot SDK Version: {linebot.__version__} ===")
        
        # Initialize MongoDB repositories
        db = get_database()
        self.alias_repo = AliasMapRepository(db)
        self.attendances_repo = AttendancesRepository(db)
        
        # 暫存多組分隊結果 (key: user_id, value: {"options": [...], "mapping_info": {...}, "timestamp": ...})
        self.pending_team_selections = {}
    
    def _store_pending_team_selection(self, user_id, team_options, mapping_info):
        """暫存使用者的分隊選項"""
        import time
        
        self.pending_team_selections[user_id] = {
            "options": team_options,
            "mapping_info": mapping_info,
            "timestamp": time.time()
        }
        
        # 清理超過 10 分鐘的暫存資料
        self._cleanup_expired_selections()
        
        self._log_info(f"[PENDING] Stored {len(team_options)} team options for user {user_id}")
    
    def _get_pending_team_selection(self, user_id):
        """獲取使用者的暫存分隊選項"""
        return self.pending_team_selections.get(user_id)
    
    def _remove_pending_team_selection(self, user_id):
        """移除使用者的暫存分隊選項"""
        if user_id in self.pending_team_selections:
            del self.pending_team_selections[user_id]
            self._log_info(f"[PENDING] Removed pending selection for user {user_id}")
    
    def _cleanup_expired_selections(self):
        """清理超過時限的暫存選項 (10分鐘)"""
        import time
        
        current_time = time.time()
        expired_users = []
        
        for user_id, data in self.pending_team_selections.items():
            if current_time - data["timestamp"] > 600:  # 10分鐘
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.pending_team_selections[user_id]
            self._log_info(f"[PENDING] Cleaned up expired selection for user {user_id}")
    
    def _create_gradient_background(self, color, angle="0deg"):
        """創建線性漸層背景 - 解決 backgroundColor 不顯示的問題"""
        return {
            "type": "linearGradient",
            "angle": angle,
            "startColor": color,
            "endColor": color  # 相同顏色創造純色效果
        }
    
    def _create_spacer(self, size="md", margin=None):
        """創建間距組件 - 安全的 SpacerComponent 替代方案"""
        if SPACER_AVAILABLE and SpacerComponent:
            # 如果 SpacerComponent 可用，使用它
            if margin:
                return SpacerComponent(size=size, margin=margin)
            else:
                return SpacerComponent(size=size)
        else:
            # 使用 TextComponent 作為替代間距方案
            size_map = {
                "xs": "xxs",
                "sm": "xs", 
                "md": "sm",
                "lg": "md",
                "xl": "lg",
                "xxl": "xl"
            }
            text_size = size_map.get(size, "sm")
            
            spacer_text = TextComponent(
                text=" ",  # 空白字符作為間距
                size=text_size,
                color="#FFFFFF00",  # 透明色
                margin=margin
            )
            return spacer_text

    def _has_brackets(self, text):
        """檢查文字是否包含方括號（支援半形和全形）"""
        if not text:
            return False
        
        # 檢查半形方括號
        has_half_width = '[' in text and ']' in text
        # 檢查全形方括號
        has_full_width = '［' in text and '］' in text
        
        return has_half_width or has_full_width
    
    def _get_bracket_pattern(self):
        """獲取支援半形和全形方括號的正則表達式模式"""
        # 支援半形 [] 和全形 ［］
        return r'[\[［]([^\]］]+)[\]］]'

    def _remove_duplicate_names(self, names, case_sensitive=True):
        """移除名稱列表中的重複項，保持順序"""
        if not names:
            return []
        
        seen = set()
        unique_names = []
        duplicates_removed = []
        
        for name in names:
            # 決定比較用的鍵
            compare_key = name if case_sensitive else name.lower()
            
            if compare_key not in seen:
                seen.add(compare_key)
                unique_names.append(name)
            else:
                duplicates_removed.append(name)
        
        if duplicates_removed:
            self._log_info(f"[DEDUP] Removed duplicate names: {duplicates_removed}")
        
        return unique_names

    def _log_info(self, message):
        """安全的 info 日誌"""
        if self.logger:
            self.logger.info(message)
        else:
            print(f"[INFO] {message}")

    def _log_warning(self, message):
        """安全的 warning 日誌"""
        if self.logger:
            self.logger.warning(message)
        else:
            print(f"[WARNING] {message}")

    def _log_error(self, message):
        """安全的 error 日誌"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"[ERROR] {message}")

    def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
         # 只處理以斜線 / 開頭的訊息
        if not message_text.startswith("/"):
            # 非指令訊息不處理
            return

        try:
            # 檢查是否為群組訊息
            is_group = hasattr(event.source, 'group_id')
            group_id = getattr(event.source, 'group_id', None)

            # 記錄收到的訊息
            self._log_info(f"[MESSAGE] User: {user_id}, Text: '{message_text}', Source: {'Group' if is_group else 'Private'}")
            if is_group:
                self._log_info(f"[GROUP] Group ID: {group_id}")
            
            # 根據指令路由到不同的處理函數
            if message_text.startswith('/group_team') or message_text.startswith('群組分隊'):
                self._log_info(f"[COMMAND] Matched: /group_team, User: {user_id}")
                if is_group:
                    self._handle_group_team_command(event, message_text, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/group_players') or message_text.startswith('群組成員'):
                self._log_info(f"[COMMAND] Matched: /group_players, User: {user_id}")
                if is_group:
                    self._handle_group_players_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/group_stats') or message_text.startswith('群組統計'):
                self._log_info(f"[COMMAND] Matched: /group_stats, User: {user_id}")
                if is_group:
                    self._handle_group_stats_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/sync') or message_text.startswith('同步成員'):
                self._log_info(f"[COMMAND] Matched: /sync, User: {user_id}")
                if is_group:
                    self._handle_sync_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/register') or message_text.startswith('註冊'):
                self._log_info(f"[COMMAND] Matched: /register, User: {user_id}")
                self._handle_register_command(event, message_text, group_id)
            elif message_text.startswith('/list') or message_text == '球員列表':
                self._log_info(f"[COMMAND] Matched: /list, User: {user_id}")
                self._handle_list_command(event)
            elif message_text.startswith('/team') or message_text.startswith('分隊'):
                self._log_info(f"[COMMAND] Matched: /team, User: {user_id}")
                self._handle_team_command(event, message_text)
            elif message_text.startswith('/profile') or message_text == '我的資料':
                self._log_info(f"[COMMAND] Matched: /profile, User: {user_id}")
                self._handle_profile_command(event, user_id)
            elif message_text.startswith('/delete') or message_text == '刪除資料':
                self._log_info(f"[COMMAND] Matched: /delete, User: {user_id}")
                self._handle_delete_command(event, user_id)
            elif message_text.startswith('/test-fullbox') or message_text == '填滿測試':
                self._log_info(f"[COMMAND] Matched: /test-fullbox, User: {user_id}")
                self._handle_test_fullbox_command(event)
            elif message_text.startswith('/test-position') or message_text == '位置測試':
                self._log_info(f"[COMMAND] Matched: /test-position, User: {user_id}")
                self._handle_test_position_command(event)
            elif message_text.startswith('/test-minimal') or message_text == '最簡測試':
                self._log_info(f"[COMMAND] Matched: /test-minimal, User: {user_id}")
                self._handle_test_minimal_command(event)
            elif message_text.startswith('/test-standard') or message_text == '標準測試':
                self._log_info(f"[COMMAND] Matched: /test-standard, User: {user_id}")
                self._handle_test_standard_command(event)
            elif message_text.startswith('/test') or message_text == '測試':
                self._log_info(f"[COMMAND] Matched: /test, User: {user_id}")
                self._handle_test_command(event)
            elif message_text.startswith('/help') or message_text == '幫助' or message_text == '說明':
                self._log_info(f"[COMMAND] Matched: /help, User: {user_id}")
                self._handle_help_command(event, is_group)
            elif message_text == '開始':
                self._log_info(f"[COMMAND] Matched: 開始, User: {user_id}")
                self._handle_start_command(event)
            elif message_text.startswith('/權重分隊') or message_text.startswith('權重分隊'):
                self._log_info(f"[COMMAND] Matched: /權重分隊, User: {user_id}")
                self._handle_weighted_team_command(event, message_text)
            elif message_text.startswith('/分隊') or message_text.startswith('分隊'):
                self._log_info(f"[COMMAND] Matched: /分隊, User: {user_id}")
                self._handle_custom_team_command(event, message_text)
            elif message_text.startswith('/查詢') or message_text.startswith('/query') or message_text == '查詢' or message_text == 'query':
                parts = message_text.split(maxsplit=1)
                if len(parts) > 1:
                    target_name = parts[1].strip()   # 這就是你要拿來當 user_id 的人名
                else:
                    target_name = None 
                self._log_info(f"[COMMAND] Matched: /查詢, User: {target_name}")
                self._handle_query_command(event, target_name)
            elif message_text.startswith('/add_user') or message_text.startswith('新增使用者'):
                self._log_info(f"[COMMAND] Matched: /add_user, User: {user_id}")
                self._handle_add_user_command(event, message_text)
            elif message_text.startswith('/remove_user') or message_text.startswith('移除使用者'):
                self._log_info(f"[COMMAND] Matched: /remove_user, User: {user_id}")
                self._handle_remove_user_command(event, message_text)
            elif message_text.startswith('/record') or message_text.startswith('記錄') or message_text.startswith('/記錄'):
                self._log_info(f"[COMMAND] Matched: /record, User: {user_id}")
                self._handle_record_command(event, message_text)
            else:
                self._log_warning(f"[UNKNOWN] Command not recognized: '{message_text}', User: {user_id}")
                self._handle_unknown_command(event, is_group)
                
        except Exception as e:
            import traceback
            self._log_error(f"[ERROR] Error handling message from {user_id}: {e}")
            self._log_error(traceback.format_exc())
            self._send_message(event.reply_token, "❌ 系統發生錯誤，請稍後再試")
    
    def handle_postback_event(self, event):
        """處理 Postback 事件"""
        user_id = event.source.user_id
        data = event.postback.data

        self._log_info(f"[POSTBACK] User: {user_id}, Data: '{data}'")

        try:
            # 解析 postback 數據
            if data == "action=register_help":
                self._send_message(event.reply_token, 
                    "📝 球員註冊說明\n\n"
                    "格式：/register 姓名 投籃 防守 體力\n"
                    "技能範圍：1-10\n\n"
                    "範例：\n"
                    "/register 小明 8 7 9\n"
                    "/register 小華 6 9 8")
            elif data == "action=list_players":
                self._handle_list_command(event)
            elif data == "action=team_help":
                self._send_message(event.reply_token,
                    "🏀 分隊說明\n\n"
                    "格式：/team [隊數]\n"
                    "預設：2隊\n\n"
                    "範例：\n"
                    "/team 2\n"
                    "/team 3")
            elif data == "action=help":
                self._handle_help_command(event)
            elif data == "action=profile":
                self._handle_profile_command(event, user_id)
            elif data.startswith("action=group_team"):
                # 解析群組 ID
                if "&group_id=" in data:
                    group_id = data.split("&group_id=")[1]
                    self._handle_group_team_command(event, "/group_team", group_id)
                else:
                    self._send_message(event.reply_token, "❌ 無法識別群組資訊")
            elif data.startswith("action=group_reteam"):
                # 重新分隊
                if "&group_id=" in data:
                    group_id = data.split("&group_id=")[1]
                    self._handle_group_team_command(event, "/group_team", group_id)
                else:
                    self._send_message(event.reply_token, "❌ 無法識別群組資訊")
            elif data == "action=reteam":
                # 自定義分隊重新分隊
                self._send_message(event.reply_token, 
                    "🔄 如需重新分隊，請重新發送成員名稱訊息\n\n"
                    "例如：日：🥛、凱、豪")
            elif data == "action=team_help":
                # 分隊說明
                self._send_message(event.reply_token,
                    "🏀 智能分隊說明\n\n"
                    "📋 分隊規則：\n"
                    "• 人數 ≤ 4：不分隊\n"
                    "• 人數 > 4：智能分配\n"
                    "• 每隊最多 3 人\n\n"
                    "🎯 特殊分配：\n"
                    "• 7人 → 3,2,2 隊\n"
                    "• 10人 → 3,3,2,2 隊\n\n"
                    "💡 使用方法：\n"
                    "直接發送成員名稱，用逗號、頓號分隔\n"
                    "例如：🥛、凱、豪、金、kin、勇")
            elif data.startswith("action=select_team"):
                # 處理分隊選擇
                self._handle_team_selection_postback(event, data)
            else:
                self._send_message(event.reply_token, "❓ 未知的操作")

        except Exception as e:
            import traceback
            self._log_error(f"[ERROR] Error handling postback from {user_id}: {e}")
            self._log_error(traceback.format_exc())
            self._send_message(event.reply_token, "❌ 系統發生錯誤，請稍後再試")
    
    def _handle_team_selection_postback(self, event, data):
        """處理分隊選擇 postback 事件"""
        try:
            user_id = event.source.user_id
            
            # 解析 postback data: action=select_team&option=1&user_id=...
            parts = data.split('&')
            option_number = None
            postback_user_id = None
            
            for part in parts:
                if part.startswith('option='):
                    option_number = int(part.split('=')[1])
                elif part.startswith('user_id='):
                    postback_user_id = part.split('=')[1]
            
            # 驗證參數
            if option_number is None or postback_user_id is None:
                self._send_message(event.reply_token, "❌ 無效的選擇參數")
                return
            
            # 檢查是否為原始發起分隊的使用者
            if user_id != postback_user_id:
                self._send_message(event.reply_token, "❌ 只有發起分隊的使用者可以選擇結果")
                return
            
            # 獲取暫存的分隊選項
            pending_selection = self._get_pending_team_selection(user_id)
            if not pending_selection:
                self._send_message(event.reply_token, 
                    "❌ 分隊選項已過期，請重新發起分隊\n\n"
                    "💡 提示：選擇時限為10分鐘")
                return
            
            team_options = pending_selection["options"]
            mapping_info = pending_selection["mapping_info"]
            
            # 驗證選項編號
            if option_number < 1 or option_number > len(team_options):
                self._send_message(event.reply_token, "❌ 無效的選項編號")
                return
            
            # 獲取選中的分隊結果
            selected_teams = team_options[option_number - 1]
            
            # 儲存選中的分隊結果到資料庫
            self._store_team_result(selected_teams, context="custom")
            
            # 移除暫存的選項
            self._remove_pending_team_selection(user_id)
            
            # 創建最終結果 Flex Message
            result_flex = self._create_custom_team_result_flex(selected_teams, mapping_info)
            
            # 發送確認訊息
            self._send_flex_message(event.reply_token, f"✅ 已確認選項 {option_number}", result_flex)
            
            self._log_info(f"[TEAM_SELECT] User {user_id} selected option {option_number}")
            
        except Exception as e:
            self._log_error(f"Error handling team selection postback: {e}")
            self._send_message(event.reply_token, "❌ 處理選擇失敗，請稍後再試")
    
    def _handle_register_command(self, event, message_text, group_id=None):
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
                
                # 已移除 Player 註冊功能
                self._send_message(event.reply_token, "❌ 球員註冊功能已移除，請使用自定義分隊功能")
                return
        
        # 如果沒有匹配到任何格式
        self._send_message(event.reply_token, 
            "❌ 格式錯誤\n\n正確格式：\n"
            "🔸 /register 姓名 投籃 防守 體力\n"
            "🔸 /register 姓名 (使用預設值 5)\n\n"
            "範例：/register 小明 8 7 9"
        )
    
    def _handle_list_command(self, event):
        """處理球員列表指令 - 已移除"""
        self._send_message(event.reply_token, "❌ 球員列表功能已移除，請使用自定義分隊功能")
    
    def _handle_team_command(self, event, message_text):
        """處理分隊指令 - 已移除"""
        self._send_message(event.reply_token, "❌ 傳統分隊功能已移除，請使用自定義分隊功能")
    
    def _handle_profile_command(self, event, user_id):
        """處理個人資料查詢指令 - 已移除"""
        self._send_message(event.reply_token, "❌ 個人資料功能已移除，請使用自定義分隊功能")
    
    def _handle_delete_command(self, event, user_id):
        """處理刪除資料指令 - 已移除"""
        self._send_message(event.reply_token, "❌ 刪除功能已移除，請使用自定義分隊功能")
    
    def _handle_help_command(self, event, is_group=False):
        """處理幫助指令"""
        message = "🏀 籃球分隊機器人使用說明\n\n"
        
        if is_group:
            message += "📱 群組專用指令：\n"
            message += "🔸 /group_team [隊數]\n"
            message += "   使用群組成員自動分隊\n"
            message += "🔸 /group_players\n"
            message += "   查看群組成員清單\n"
            message += "🔸 /group_stats\n"
            message += "   群組統計資訊\n"
            message += "🔸 /sync\n"
            message += "   手動同步群組成員\n\n"
        
        message += "📝 個人指令：\n"
        message += "🔸 /register 姓名 投籃 防守 體力\n"
        message += "   註冊球員 (技能值 1-10)\n"
        message += "🔸 /add_user 姓名\n"
        message += "   新增球員\n"
        message += "🔸 /remove_user 姓名\n"
        message += "   移除球員\n"
        message += "🔸 /list\n"
        message += "   查看所有球員\n"
        message += "🔸 /team [隊數]\n"
        message += "   自動分隊 (預設 2 隊)\n"
        message += "🔸 /profile\n"
        message += "   查看個人資料\n"
        message += "🔸 /delete\n"
        message += "   刪除個人資料\n"
        message += "🔸 /分隊 成員名單\n"
        message += "   自訂分隊 (支援方括號群組)\n"
        message += "🔸 /權重分隊 成員名單\n"
        message += "   避免與最近5次重複的分隊\n"
        message += "🔸 /record 隊伍1:成員 隊伍2:成員\n"
        message += "   手動記錄分隊結果\n"
        message += "🔸 /查詢\n"
        message += "   查看個人組隊記錄\n\n"
        message += "📖 使用範例：\n"
        if is_group:
            message += "• /group_team 2 (群組快速分隊)\n"
        message += "• /register 小明 8 7 9\n"
        message += "• /add_user 小華\n"
        message += "• /remove_user 小李\n"
        message += "• /team 3\n"
        message += "• /分隊 [小明,小華] 小李 小強\n"
        message += "• /權重分隊 小明,小華,小李,小強\n"
        message += "• /record 隊伍1:小明,小華 隊伍2:小李,小強\n\n"
        message += "⚠️ 注意事項：\n"
        message += "• 技能值範圍：1-10\n"
        message += "• 群組分隊會使用預設技能值\n"
        message += "• 系統會自動平衡隊伍實力"
        
        self._send_message(event.reply_token, message)
    
    def _handle_start_command(self, event):
        """處理開始指令"""
        welcome_flex = self._create_welcome_flex()
        self._send_flex_message(event.reply_token, "籃球分隊機器人", welcome_flex)
    
    def _handle_test_command(self, event):
        """處理測試指令 - 發送簡單背景色測試 Bubble"""
        self._log_info("=== 發送測試 Bubble ===")
        
        # 創建三種不同的測試 bubble
        test_bubbles = [
            self._create_test_bubble_1(),  # 標準 bubble 紅色背景
            self._create_test_bubble_2(),  # nano bubble 藍色背景  
            self._create_test_bubble_3()   # 綠色背景，不同位置
        ]
        
        # 發送測試 carousel
        from linebot.models import FlexSendMessage, CarouselContainer
        
        carousel = CarouselContainer(contents=test_bubbles)
        flex_message = FlexSendMessage(alt_text="背景色測試", contents=carousel)
        
        try:
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            self._log_info("✅ 測試 Bubble 已發送")
        except Exception as e:
            self._log_error(f"❌ 發送測試 Bubble 失敗: {e}")
            self._send_message(event.reply_token, f"❌ 測試失敗: {str(e)}")
    
    def _handle_test_standard_command(self, event):
        """處理標準測試指令 - 發送標準大小背景色測試 Bubble"""
        self._log_info("=== 發送標準大小測試 Bubble ===")
        
        # 創建標準大小的測試 bubble
        standard_bubble = self._create_standard_test_bubble()
        
        # 發送單個 bubble (不是 carousel)
        from linebot.models import FlexSendMessage
        
        flex_message = FlexSendMessage(alt_text="標準背景色測試", contents=standard_bubble)
        
        try:
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            self._log_info("✅ 標準測試 Bubble 已發送")
        except Exception as e:
            self._log_error(f"❌ 發送標準測試 Bubble 失敗: {e}")
            self._send_message(event.reply_token, f"❌ 標準測試失敗: {str(e)}")
    
    def _handle_test_minimal_command(self, event):
        """處理最簡測試指令 - 發送最簡化的背景色測試"""
        self._log_info("=== 發送最簡化背景色測試 ===")
        
        # 創建3個最簡化測試 bubble：不同顏色格式 + 不同位置
        test_bubbles = [
            self._create_minimal_test_1(),  # 大寫hex #FF0000
            self._create_minimal_test_2(),  # 小寫hex #00ff00  
            self._create_minimal_test_3()   # 短格式 #00F
        ]
        
        # 發送測試 carousel
        from linebot.models import FlexSendMessage, CarouselContainer
        
        carousel = CarouselContainer(contents=test_bubbles)
        flex_message = FlexSendMessage(alt_text="最簡背景色測試", contents=carousel)
        
        try:
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            self._log_info("✅ 最簡測試已發送")
        except Exception as e:
            self._log_error(f"❌ 發送最簡測試失敗: {e}")
            self._send_message(event.reply_token, f"❌ 最簡測試失敗: {str(e)}")
    
    def _handle_test_position_command(self, event):
        """處理位置測試指令 - 測試header, body, footer不同位置的背景色"""
        self._log_info("=== 發送位置背景色測試 ===")
        
        # 創建3個測試不同位置的 bubble
        test_bubbles = [
            self._create_position_test_header(),  # header背景色
            self._create_position_test_body(),    # body背景色
            self._create_position_test_footer()   # footer背景色
        ]
        
        # 發送測試 carousel
        from linebot.models import FlexSendMessage, CarouselContainer
        
        carousel = CarouselContainer(contents=test_bubbles)
        flex_message = FlexSendMessage(alt_text="位置背景色測試", contents=carousel)
        
        try:
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            self._log_info("✅ 位置測試已發送")
        except Exception as e:
            self._log_error(f"❌ 發送位置測試失敗: {e}")
            self._send_message(event.reply_token, f"❌ 位置測試失敗: {str(e)}")
    
    def _handle_test_fullbox_command(self, event):
        """處理填滿測試指令 - 測試用整個box填滿bubble營造背景色"""
        self._log_info("=== 發送填滿Box背景色測試 ===")
        
        # 創建3個不同的填滿box方案
        test_bubbles = [
            self._create_fullbox_absolute(),    # 絕對定位填滿
            self._create_fullbox_percentage(),  # 100%尺寸填滿
            self._create_fullbox_gradient()     # 線性漸層填滿
        ]
        
        # 發送測試 carousel
        from linebot.models import FlexSendMessage, CarouselContainer
        
        carousel = CarouselContainer(contents=test_bubbles)
        flex_message = FlexSendMessage(alt_text="填滿Box背景色測試", contents=carousel)
        
        try:
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            self._log_info("✅ 填滿測試已發送")
        except Exception as e:
            self._log_error(f"❌ 發送填滿測試失敗: {e}")
            self._send_message(event.reply_token, f"❌ 填滿測試失敗: {str(e)}")
    
    def _create_test_bubble_1(self):
        """測試 Bubble 1: nano 大小，header 紅色背景"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建測試 Bubble 1 - nano 大小，header 紅色背景 #FF0000")
        
        return BubbleContainer(
            size="nano",  # 修正：統一使用 nano 尺寸
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="測試 1 - 紅色",
                        color="#ffffff",
                        weight="bold",
                        size="md"  # nano bubble 使用 md 而非 lg
                    ),
                    TextComponent(
                        text="nano bubble 測試",
                        color="#ffffff", 
                        size="xs"  # 調整為 nano bubble 適當大小
                    )
                ],
                background=self._create_gradient_background("#FF0000"),  # 紅色背景
                paddingAll="12px"  # nano bubble 使用較小 padding
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="header 紅色背景測試",
                        size="sm",
                        color="#333333",
                        wrap=True
                    )
                ],
                paddingAll="12px"
            )
        )
    
    def _create_test_bubble_2(self):
        """測試 Bubble 2: nano 大小，header 藍色背景"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建測試 Bubble 2 - nano 大小，header 藍色背景 #0066FF")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="測試 2 - 藍色",
                        color="#ffffff",
                        weight="bold",
                        size="md"
                    )
                ],
                background=self._create_gradient_background("#0066FF"),  # 藍色背景
                paddingAll="12px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="nano bubble 藍色背景測試",
                        size="sm",
                        color="#333333",
                        wrap=True
                    )
                ],
                paddingAll="12px"
            )
        )
    
    def _create_test_bubble_3(self):
        """測試 Bubble 3: body 綠色背景 (非 header)"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建測試 Bubble 3 - body 綠色背景 #00AA00")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="測試 3 - 綠色",
                        color="#ffffff",
                        weight="bold",
                        size="md"
                    )
                ],
                background=self._create_gradient_background("#666666"),  # 灰色背景  
                paddingAll="12px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="body 有綠色背景",
                        size="sm",
                        color="#ffffff",  # 白色文字配綠色背景
                        wrap=True
                    )
                ],
                background=self._create_gradient_background("#00AA00"),  # 綠色背景在 body
                paddingAll="12px"
            )
        )
    
    def _create_standard_test_bubble(self):
        """創建標準大小的背景色測試 Bubble"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建標準測試 Bubble - 標準大小，header 橙色背景 #FF6B35")
        
        return BubbleContainer(
            # 不指定 size，默認為標準大小
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="標準測試 - 橙色",
                        color="#ffffff",
                        weight="bold",
                        size="lg"
                    ),
                    TextComponent(
                        text="標準大小 bubble",
                        color="#ffffff",
                        size="md",
                        margin="sm"
                    ),
                    TextComponent(
                        text="測試 header 背景色",
                        color="#ffffff",
                        size="sm",
                        margin="sm"
                    )
                ],
                background=self._create_gradient_background("#FF6B35"),  # 橙色背景
                paddingAll="20px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="如果背景色功能正常，上方 header 應該顯示為橙色背景",
                        size="md",
                        color="#333333",
                        wrap=True
                    ),
                    TextComponent(
                        text="這是標準大小的 Bubble，比 nano 更大更詳細",
                        size="sm",
                        color="#666666",
                        wrap=True,
                        margin="md"
                    )
                ],
                paddingAll="20px"
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="⚡ 標準尺寸背景色測試",
                        size="sm",
                        color="#999999",
                        align="center"
                    )
                ],
                paddingAll="12px"
            )
        )
    
    def _create_minimal_test_1(self):
        """最簡測試1: 大寫hex顏色 #FF0000 (紅色)"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建最簡測試1 - 大寫hex #FF0000")
        
        return BubbleContainer(
            size="nano",
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="紅色",
                        color="#ffffff",
                        weight="bold"
                    )
                ],
                background=self._create_gradient_background("#FF0000"),  # 大寫hex紅色
                paddingAll="20px"
            )
        )
    
    def _create_minimal_test_2(self):
        """最簡測試2: 小寫hex顏色 #00ff00 (綠色)"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建最簡測試2 - 小寫hex #00ff00")
        
        return BubbleContainer(
            size="nano", 
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="綠色",
                        color="#ffffff",
                        weight="bold"
                    )
                ],
                background=self._create_gradient_background("#00ff00"),  # 小寫hex綠色
                paddingAll="20px"
            )
        )
    
    def _create_minimal_test_3(self):
        """最簡測試3: 短格式hex顏色 #00F (藍色)"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建最簡測試3 - 短格式hex #00F")
        
        return BubbleContainer(
            size="nano",
            body=BoxComponent(
                layout="vertical", 
                contents=[
                    TextComponent(
                        text="藍色",
                        color="#ffffff",
                        weight="bold"
                    )
                ],
                background=self._create_gradient_background("#00F"),  # 短格式hex藍色 
                paddingAll="20px"
            )
        )
    
    def _create_position_test_header(self):
        """位置測試1: header 背景色"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建位置測試1 - header 背景色 #FF6B35")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Header",
                        color="#ffffff",
                        weight="bold",
                        align="center"
                    )
                ],
                background=self._create_gradient_background("#FF6B35"),  # header 橙色背景
                paddingAll="16px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="測試header背景色",
                        size="sm",
                        color="#333333",
                        align="center"
                    )
                ],
                paddingAll="16px"
            )
        )
    
    def _create_position_test_body(self):
        """位置測試2: body 背景色"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建位置測試2 - body 背景色 #4ECDC4")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Body測試",
                        color="#333333",
                        weight="bold",
                        align="center"
                    )
                ],
                paddingAll="16px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Body",
                        color="#ffffff",
                        weight="bold",
                        align="center"
                    )
                ],
                background=self._create_gradient_background("#4ECDC4"),  # body 青色背景
                paddingAll="16px"
            )
        )
    
    def _create_position_test_footer(self):
        """位置測試3: footer 背景色"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建位置測試3 - footer 背景色 #A17DF5")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Footer測試",
                        color="#333333",
                        weight="bold",
                        align="center"
                    )
                ],
                paddingAll="16px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="測試footer背景色",
                        size="sm",
                        color="#333333",
                        align="center"
                    )
                ],
                paddingAll="16px"
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Footer",
                        color="#ffffff",
                        weight="bold",
                        align="center"
                    )
                ],
                background=self._create_gradient_background("#A17DF5"),  # footer 紫色背景
                paddingAll="16px"
            )
        )
    
    def _create_fullbox_absolute(self):
        """填滿測試1: 絕對定位填滿整個bubble"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建填滿測試1 - 絕對定位填滿 #FF6B35")
        
        return BubbleContainer(
            size="nano",
            body=BoxComponent(
                layout="vertical",
                contents=[
                    # 背景 box - 絕對定位填滿整個區域
                    BoxComponent(
                        layout="vertical",
                        contents=[],  # 空內容，只用作背景
                        position="absolute",
                        offsetTop="0px",
                        offsetBottom="0px",
                        offsetStart="0px", 
                        offsetEnd="0px",
                        background=self._create_gradient_background("#FF6B35")  # 橙色背景
                    ),
                    # 內容 box - 相對定位在背景之上
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text="絕對定位",
                                color="#ffffff",
                                weight="bold",
                                align="center",
                                size="md"
                            ),
                            TextComponent(
                                text="填滿背景",
                                color="#ffffff",
                                align="center",
                                size="sm",
                                margin="sm"
                            )
                        ],
                        position="relative",
                        paddingAll="16px"
                    )
                ]
            )
        )
    
    def _create_fullbox_percentage(self):
        """填滿測試2: 100%尺寸填滿bubble"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建填滿測試2 - 100%尺寸填滿 #4ECDC4")
        
        return BubbleContainer(
            size="nano",
            body=BoxComponent(
                layout="vertical",
                contents=[
                    # 背景 box - 100% 寬度和高度
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text="100%尺寸",
                                color="#ffffff",
                                weight="bold",
                                align="center",
                                size="md"
                            ),
                            TextComponent(
                                text="填滿背景",
                                color="#ffffff",
                                align="center",
                                size="sm",
                                margin="sm"
                            )
                        ],
                        width="100%",
                        height="100%",
                        background=self._create_gradient_background("#4ECDC4"),  # 青色背景
                        paddingAll="16px"
                    )
                ],
                paddingAll="0px"  # 移除外層padding讓內部box完全填滿
            )
        )
    
    def _create_fullbox_gradient(self):
        """填滿測試3: 線性漸層作為背景填滿"""
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        
        self._log_info("創建填滿測試3 - 線性漸層填滿 #A17DF5")
        
        # 創建線性漸層背景
        gradient_background = {
            "type": "linearGradient",
            "angle": "0deg",
            "startColor": "#A17DF5",  # 紫色
            "endColor": "#A17DF5"     # 同色創造純色效果
        }
        
        return BubbleContainer(
            size="nano", 
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="線性漸層",
                        color="#ffffff",
                        weight="bold",
                        align="center",
                        size="md"
                    ),
                    TextComponent(
                        text="背景填滿",
                        color="#ffffff",
                        align="center",
                        size="sm",
                        margin="sm"
                    )
                ],
                background=gradient_background,  # 使用漸層背景
                paddingAll="16px"
            )
        )
    
    def _handle_unknown_command(self, event, is_group=False):
        """處理未知指令"""
        message = "❓ 不認識的指令\n\n"
        message += "請使用以下指令：\n"
        message += "🔸 /help - 查看使用說明\n"
        if is_group:
            message += "🔸 /group_team - 群組快速分隊\n"
            message += "🔸 /group_players - 群組成員清單\n"
        message += "🔸 /register - 註冊球員\n"
        message += "🔸 /list - 球員列表\n"
        message += "🔸 /team - 開始分隊"
        
        self._send_message(event.reply_token, message)
    
    # === 群組專用指令處理函數 ===
    
    def _handle_group_team_command(self, event, message_text, group_id):
        """處理群組分隊指令"""
        try:
            # 解析隊伍數量
            num_teams = 2  # 預設 2 隊
            
            patterns = [
                r'/group_team\s+(\d+)',  # /group_team 3
                r'群組分隊\s+(\d+)',      # 群組分隊 3
            ]
            
            for pattern in patterns:
                match = re.match(pattern, message_text)
                if match:
                    try:
                        num_teams = int(match.group(1))
                    except ValueError:
                        pass
                    break
            
            # 自動設定群組分隊
            players = self.group_manager.auto_setup_group_team(group_id)
            
            if len(players) < 2:
                self._send_message(event.reply_token, 
                    "❌ 群組成員不足，至少需要 2 位成員才能分隊\n\n"
                    "請確認：\n"
                    "1. 群組有足夠的成員\n"
                    "2. 機器人有讀取群組成員的權限")
                return
            
            # 驗證隊伍數量
            if num_teams < 2:
                self._send_message(event.reply_token, "❌ 至少需要分成 2 隊")
                return
            
            if num_teams > len(players):
                self._send_message(event.reply_token, 
                    f"❌ 隊伍數量 ({num_teams}) 不能超過成員數量 ({len(players)})")
                return
            
            # 生成隊伍 (使用智能分隊邏輯)
            teams = self._generate_simple_teams(players, num_teams)
            
            # 儲存分隊結果到資料庫
            self._store_team_result(teams, context="group")
            
            team_flex = self._create_group_team_result_flex(teams, group_id)
            self._send_flex_message(event.reply_token, "群組分隊結果", team_flex)
            
        except Exception as e:
            print(f"Error handling group team command: {e}")
            self._send_message(event.reply_token, "❌ 群組分隊失敗，請稍後再試")
    
    def _handle_group_players_command(self, event, group_id):
        """處理群組成員清單指令"""
        try:
            # 同步群組成員（確保資料最新）
            synced_count = self.group_manager.sync_group_members(group_id)
            
            # 獲取群組球員
            players = self.group_manager.get_group_players_for_team(group_id)
            
            if not players:
                message = "📋 群組成員清單\n\n"
                message += "目前沒有偵測到群組成員\n\n"
                message += "可能原因：\n"
                message += "• 機器人缺少讀取群組成員權限\n"
                message += "• 群組成員較少\n"
                message += "• 需要手動同步：/sync"
                self._send_message(event.reply_token, message)
                return
            
            group_list_flex = self._create_group_player_list_flex(players, group_id)
            self._send_flex_message(event.reply_token, "群組成員清單", group_list_flex)
            
        except Exception as e:
            print(f"Error handling group players command: {e}")
            self._send_message(event.reply_token, "❌ 獲取群組成員失敗，請稍後再試")
    
    def _handle_group_stats_command(self, event, group_id):
        """處理群組統計指令"""
        try:
            stats = self.group_manager.get_group_stats(group_id)
            
            if not stats:
                self._send_message(event.reply_token, "❌ 無法獲取群組統計資訊")
                return
            
            message = "📊 群組統計資訊\n\n"
            message += f"👥 群組總成員：{stats.get('total_members', 0)} 人\n"
            message += f"🏀 可分隊成員：{stats.get('total_players', 0)} 人\n"
            message += f"✅ 已註冊球員：{stats.get('registered_players', 0)} 人\n"
            message += f"👤 群組成員：{stats.get('member_players', 0)} 人\n\n"
            
            if stats.get('avg_rating'):
                message += f"⭐ 平均評分：{stats['avg_rating']:.1f}/10\n"
                message += f"🎯 平均投籃：{stats['avg_shooting']:.1f}/10\n"
                message += f"🛡️ 平均防守：{stats['avg_defense']:.1f}/10\n"
                message += f"💪 平均體力：{stats['avg_stamina']:.1f}/10\n\n"
            
            # 分隊建議
            from group_manager import suggest_group_team_sizes
            suggestions = suggest_group_team_sizes(stats.get('total_players', 0))
            if suggestions:
                message += "💡 分隊建議：\n"
                for _, description in suggestions[:2]:
                    message += f"• {description}\n"
            
            self._send_message(event.reply_token, message)
            
        except Exception as e:
            print(f"Error handling group stats command: {e}")
            self._send_message(event.reply_token, "❌ 獲取群組統計失敗，請稍後再試")
    
    def _handle_sync_command(self, event, group_id):
        """處理手動同步指令"""
        try:
            synced_count = self.group_manager.sync_group_members(group_id)
            
            if synced_count > 0:
                message = f"✅ 同步完成！\n\n"
                message += f"已同步 {synced_count} 位群組成員\n"
                message += f"使用 /group_players 查看成員清單"
            else:
                message = "⚠️ 同步完成，但未偵測到新成員\n\n"
                message += "可能原因：\n"
                message += "• 所有成員都已同步\n"
                message += "• 機器人缺少讀取權限\n"
                message += "• 群組成員較少"
            
            self._send_message(event.reply_token, message)
            
        except Exception as e:
            print(f"Error handling sync command: {e}")
            self._send_message(event.reply_token, "❌ 同步失敗，請稍後再試")
    
    def _send_message(self, reply_token, message_text, quick_reply=None):
        """發送訊息"""
        try:
            self._log_info(f"[SEND] Sending message: '{message_text[:50]}...' to token: {reply_token[:10]}...")
            message = TextSendMessage(text=message_text, quick_reply=quick_reply)
            self.line_bot_api.reply_message(reply_token, message)
            self._log_info(f"[SUCCESS] Message sent successfully")
        except Exception as e:
            import traceback
            self._log_error(f"[ERROR] Error sending message: {e}")
            self._log_error(traceback.format_exc())
    
    def _send_flex_message(self, reply_token, alt_text, flex_content):
        """發送 Flex Message"""
        try:
            self._log_info(f"[SEND] Sending flex message: '{alt_text}' to token: {reply_token[:10]}...")
            message = FlexSendMessage(alt_text=alt_text, contents=flex_content)
            self.line_bot_api.reply_message(reply_token, message)
            self._log_info(f"[SUCCESS] Flex message sent successfully")
        except Exception as e:
            import traceback
            self._log_error(f"[ERROR] Error sending flex message: {e}")
            self._log_error(traceback.format_exc())
    
    # === Flex Message 模板函數 ===
    
    def _create_welcome_flex(self):
        """創建歡迎訊息 Flex Message"""
        bubble = BubbleContainer(
            direction="ltr",
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="🏀 籃球分隊機器人",
                        weight="bold",
                        size="xl",
                        align="center",
                        color="#FF6B35"
                    ),
                    SeparatorComponent(margin="md"),
                    self._create_spacer(size="sm"),
                    TextComponent(
                        text="歡迎使用智能籃球分隊系統！",
                        size="md",
                        align="center",
                        wrap=True,
                        color="#333333"
                    ),
                    self._create_spacer(size="md"),
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text="✨ 主要功能",
                                weight="bold",
                                size="md",
                                color="#4A90E2"
                            ),
                            TextComponent(
                                text="• 球員註冊與管理\n• 技能評估系統\n• 智能平衡分隊\n• 多種分隊模式",
                                size="sm",
                                wrap=True,
                                margin="sm",
                                color="#666666"
                            )
                        ],
                        background=self._create_gradient_background("#F8F9FA"),
                        paddingAll="md",
                        cornerRadius="8px",
                        margin="md"
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="📝 註冊球員",
                            data="action=register_help"
                        ),
                        style="primary",
                        color="#FF6B35"
                    ),
                    ButtonComponent(
                        action=PostbackAction(
                            label="📋 球員列表",
                            data="action=list_players"
                        ),
                        style="secondary"
                    ),
                    ButtonComponent(
                        action=PostbackAction(
                            label="🏀 開始分隊",
                            data="action=team_help"
                        ),
                        style="secondary"
                    ),
                    ButtonComponent(
                        action=PostbackAction(
                            label="❓ 使用說明",
                            data="action=help"
                        ),
                        style="link"
                    )
                ],
                spacing="sm"
            )
        )
        return bubble
    
    # 已移除 _create_register_success_flex - 不再使用 Player 類

    # 已移除 _create_skill_bar - 不再使用 Player 類
    # 已移除所有 Player 相關的 Flex Message 方法
    
    # 已移除 _is_custom_team_message - 改用 /分隊 指令觸發
    
    def _extract_reply_content(self, event):
        """提取回覆訊息的內容"""
        try:
            # 檢查是否有回覆訊息
            if hasattr(event.message, 'quoted_message_id') and event.message.quoted_message_id:
                self._log_info(f"[REPLY] Detected reply to message: {event.message.quoted_message_id}")
                
                # 注意：LINE Bot API 通常無法直接獲取被回覆訊息的內容
                # 這裡需要根據實際的 LINE Bot SDK 版本來實作
                # 目前先返回 None，表示無法獲取回覆內容
                self._log_warning(f"[REPLY] Cannot fetch replied message content with current LINE Bot API")
                return None
            
            return None
            
        except Exception as e:
            self._log_error(f"Error extracting reply content: {e}")
            return None
    
    def _handle_custom_team_command(self, event, message_text):
        """處理自定義分隊指令"""
        import re
        
        try:
            # 提取要處理的內容
            target_text = None
            
            # 1. 先檢查是否有回覆訊息
            reply_content = self._extract_reply_content(event)
            if reply_content:
                target_text = reply_content
                self._log_info(f"[TEAM_CMD] Using reply content: {target_text[:50]}...")
            else:
                # 2. 檢查指令後是否有內容
                # 移除 /分隊 或 分隊 前綴
                clean_command = re.sub(r'^/?分隊\s*', '', message_text).strip()
                if clean_command:
                    target_text = clean_command
                    self._log_info(f"[TEAM_CMD] Using command content: {target_text[:50]}...")
                else:
                    # 3. 沒有內容可處理
                    self._send_message(event.reply_token, 
                        "❌ 請提供成員名單\n\n"
                        "使用方式：\n"
                        "🔸 /分隊 🥛、凱、豪、金\n"
                        "🔸 回覆包含成員名單的訊息，然後輸入 /分隊")
                    return
            
            # 檢查內容是否包含成員名稱分隔符
            if not self._is_valid_team_content(target_text):
                self._send_message(event.reply_token,
                    "❌ 無法識別成員名單\n\n"
                    "請確保成員名稱用逗號、頓號分隔\n"
                    "或使用方括號群組分隊：[隊友1,隊友2] 個別成員\n"
                    "支援半形 [] 或全形 ［］ 方括號\n"
                    "例如：🥛、凱、豪、金、kin、勇")
                return
            
            user_id = event.source.user_id
            
            # 檢查是否使用方括號群組分隊（支援半形和全形）
            if self._has_brackets(target_text):
                # 使用新的群組解析
                groups, individual_members = self._parse_bracket_groups(target_text)
                
                if not groups and not individual_members:
                    self._send_message(event.reply_token, 
                        "❌ 無法解析方括號群組格式\n\n"
                        "請使用正確格式：[隊友1,隊友2] 個別成員1 個別成員2\n"
                        "支援半形 [] 或全形 ［］ 方括號\n"
                        "每個群組最多3人")
                    return
                
                # 檢查是否所有群組都超過隊伍限制
                invalid_groups = [group for group in groups if len(group) > 3]
                if invalid_groups:
                    self._send_message(event.reply_token, 
                        f"❌ 發現超過3人的群組: {invalid_groups}\n\n"
                        "每個群組最多3人（3vs3比賽限制）")
                    return
                
                # 計算總人數
                total_count = sum(len(group) for group in groups) + len(individual_members)
                
                if total_count < 1:
                    self._send_message(event.reply_token, "❌ 請至少輸入 1 位成員")
                    return
                
                # 人數太少不需分隊
                if total_count <= 4:
                    # 合併所有成員
                    all_names = []
                    for group in groups:
                        all_names.extend(group)
                    all_names.extend(individual_members)
                    
                    players, mapping_info = self._create_players_from_names(all_names)
                    
                    message = f"👥 人數太少，不需分隊\n\n"
                    message += f"成員名單 ({len(players)}人):\n"
                    for i, player in enumerate(players, 1):
                        message += f"{i}. {player['name']}\n"
                    message += "\n💡 建議直接一起打球！"
                    
                    self._send_message(event.reply_token, message)
                    self._store_team_result([players], context="custom_group")
                    return
                
                # 使用新的群組分隊邏輯生成選項
                team_options = self._generate_multiple_team_options_with_groups(groups, individual_members, num_options=3)
                
                # 為映射信息，需要所有成員的列表
                all_names = []
                for group in groups:
                    all_names.extend(group)
                all_names.extend(individual_members)
                _, mapping_info = self._create_players_from_names(all_names)
                
                # 暫存分隊選項供使用者選擇
                self._store_pending_team_selection(user_id, team_options, mapping_info)
                
                # 創建分隊選擇 Flex Message
                selection_flex = self._create_team_selection_flex(team_options, mapping_info, user_id)
                
                # 發送分隊選項 Carousel
                self._send_flex_message(event.reply_token, "🎲 請選擇群組分隊方案", selection_flex)
                return
            
            # 原有的隨機分隊邏輯
            # 解析成員名稱
            member_names = self._parse_member_names(target_text)
            if len(member_names) < 1:
                self._send_message(event.reply_token, "❌ 請至少輸入 1 位成員名稱")
                return
            
            # 通過別名映射創建球員列表
            players, mapping_info = self._create_players_from_names(member_names)
            
            if len(players) < 1:
                self._send_message(event.reply_token, "❌ 無法創建球員列表")
                return
            
            # 檢查人數是否需要分隊
            if len(players) <= 4:
                # 人數少，不需分隊，發送簡單文字訊息
                message = f"👥 人數太少，不需分隊\n\n"
                message += f"成員名單 ({len(players)}人):\n"
                for i, player in enumerate(players, 1):
                    message += f"{i}. {player['name']}\n"
                message += "\n💡 建議直接一起打球！"
                
                self._send_message(event.reply_token, message)
                
                # 直接儲存到資料庫（不需選擇）
                self._store_team_result([players], context="custom")
                return
            
            # 生成多組分隊選項
            team_options = self._generate_multiple_team_options(players, num_options=3)
            
            # 暫存分隊選項供使用者選擇
            self._store_pending_team_selection(user_id, team_options, mapping_info)
            
            # 創建分隊選擇 Flex Message（單一 Carousel 包含 3 個選項）
            selection_flex = self._create_team_selection_flex(team_options, mapping_info, user_id)
            
            # 發送分隊選項 Carousel
            self._send_flex_message(event.reply_token, "請選擇分隊方案", selection_flex)
            
        except Exception as e:
            self._log_error(f"Error in custom team command: {e}")
            self._send_message(event.reply_token, "❌ 分隊處理失敗，請稍後再試")

    def _handle_weighted_team_command(self, event, message_text):
        """處理權重分隊指令 - 避免與最近歷史重複"""
        import re

        try:
            # 提取要處理的內容
            target_text = None

            # 1. 先檢查是否有回覆訊息
            reply_content = self._extract_reply_content(event)
            if reply_content:
                target_text = reply_content
                self._log_info(f"[WEIGHTED_CMD] Using reply content: {target_text[:50]}...")
            else:
                # 2. 檢查指令後是否有內容
                # 移除 /權重分隊 或 權重分隊 前綴
                clean_command = re.sub(r'^/?權重分隊\s*', '', message_text).strip()
                if clean_command:
                    target_text = clean_command
                    self._log_info(f"[WEIGHTED_CMD] Using command content: {target_text[:50]}...")
                else:
                    # 3. 沒有內容可處理
                    self._send_message(event.reply_token,
                        "❌ 請提供成員名單\n\n"
                        "使用方式：\n"
                        "🔸 /權重分隊 🥛、凱、豪、金\n"
                        "🔸 /權重分隊 3 🥛、凱、豪、金  (只參考最近3次記錄)\n"
                        "🔸 回覆包含成員名單的訊息，然後輸入 /權重分隊\n\n"
                        "💡 權重分隊會避免與最近N次分隊結果相同（預設1次）")
                    return

            # 解析可選的歷史次數參數
            avoid_recent_count = 1  # 預設值
            parts = target_text.split(maxsplit=1)
            if parts and parts[0].isdigit():
                count = int(parts[0])
                if 1 <= count <= 99:
                    avoid_recent_count = count
                    target_text = parts[1] if len(parts) > 1 else ''
                    self._log_info(f"[WEIGHTED_CMD] Custom avoid_recent_count={avoid_recent_count}")

            # 檢查內容是否包含成員名稱分隔符
            if not self._is_valid_team_content(target_text):
                self._send_message(event.reply_token,
                    "❌ 無法識別成員名單\n\n"
                    "請確保成員名稱用逗號、頓號分隔\n"
                    "或使用方括號群組分隊：[隊友1,隊友2] 個別成員\n"
                    "支援半形 [] 或全形 ［］ 方括號\n"
                    "例如：🥛、凱、豪、金、kin、勇")
                return

            user_id = event.source.user_id

            # 檢查是否使用方括號群組分隊（支援半形和全形）
            if self._has_brackets(target_text):
                # 使用新的群組解析
                groups, individual_members = self._parse_bracket_groups(target_text)

                if not groups and not individual_members:
                    self._send_message(event.reply_token,
                        "❌ 無法解析方括號群組格式\n\n"
                        "請使用正確格式：[隊友1,隊友2] 個別成員1 個別成員2\n"
                        "支援半形 [] 或全形 ［］ 方括號\n"
                        "每個群組最多3人")
                    return

                # 檢查是否所有群組都超過隊伍限制
                invalid_groups = [group for group in groups if len(group) > 3]
                if invalid_groups:
                    self._send_message(event.reply_token,
                        f"❌ 發現超過3人的群組: {invalid_groups}\n\n"
                        "每個群組最多3人（3vs3比賽限制）")
                    return

                # 計算總人數
                total_count = sum(len(group) for group in groups) + len(individual_members)
                self._log_info(f"[WEIGHTED_CMD] Parsed {len(groups)} groups, {len(individual_members)} individuals, total={total_count}")
                self._log_info(f"[WEIGHTED_CMD] Total {total_count} players, using bracket_group mode")

                if total_count < 1:
                    self._send_message(event.reply_token, "❌ 請至少輸入 1 位成員")
                    return

                # 人數太少不需分隊
                if total_count <= 4:
                    # 合併所有成員
                    all_names = []
                    for group in groups:
                        all_names.extend(group)
                    all_names.extend(individual_members)

                    players, mapping_info = self._create_players_from_names(all_names)

                    message = f"👥 人數太少，不需分隊\n\n"
                    message += f"成員名單 ({len(players)}人):\n"
                    for i, player in enumerate(players, 1):
                        message += f"{i}. {player['name']}\n"
                    message += "\n💡 建議直接一起打球！"

                    self._send_message(event.reply_token, message)
                    self._store_team_result([players], context="weighted_group")
                    return

                # 獲取上次分隊記錄（在產生新分隊前）
                last_attendance = self._get_last_team_attendance()

                # 使用權重分隊邏輯生成選項（避免與歷史重複）- 只生成1個最佳方案
                team_options = self._generate_weighted_team_options_with_groups(groups, individual_members, num_options=1, avoid_recent_count=avoid_recent_count)

                # 直接使用第一個（最佳）選項
                selected_teams, similarity_score = team_options[0]

                # 儲存分隊結果到資料庫
                self._store_team_result(selected_teams, context="weighted_group")
                self._log_info(f"[WEIGHTED_CMD] Final result: {len(selected_teams)} teams, stored to DB")

                # 格式化並發送結果訊息（包含上次分隊比較）
                result_message = self._format_weighted_team_result(selected_teams, last_attendance, similarity_score, avoid_recent_count)
                self._send_message(event.reply_token, result_message)
                return

            # 無方括號的權重分隊邏輯
            # 解析成員名稱
            member_names = self._parse_member_names(target_text)
            self._log_info(f"[WEIGHTED_CMD] Parsed 0 groups, {len(member_names)} individuals, total={len(member_names)}")
            self._log_info(f"[WEIGHTED_CMD] Total {len(member_names)} players, using normal mode")
            if len(member_names) < 1:
                self._send_message(event.reply_token, "❌ 請至少輸入 1 位成員名稱")
                return

            # 通過別名映射創建球員列表
            players, mapping_info = self._create_players_from_names(member_names)

            if len(players) < 1:
                self._send_message(event.reply_token, "❌ 無法創建球員列表")
                return

            # 檢查人數是否需要分隊
            if len(players) <= 4:
                # 人數少，不需分隊，發送簡單文字訊息
                message = f"👥 人數太少，不需分隊\n\n"
                message += f"成員名單 ({len(players)}人):\n"
                for i, player in enumerate(players, 1):
                    message += f"{i}. {player['name']}\n"
                message += "\n💡 建議直接一起打球！"

                self._send_message(event.reply_token, message)

                # 直接儲存到資料庫（不需選擇）
                self._store_team_result([players], context="weighted")
                return

            # 獲取上次分隊記錄（在產生新分隊前）
            last_attendance = self._get_last_team_attendance()

            # 使用權重分隊邏輯生成選項（將所有成員視為個別成員，無群組）- 只生成1個最佳方案
            team_options = self._generate_weighted_team_options_with_groups([], member_names, num_options=1, avoid_recent_count=avoid_recent_count)

            # 直接使用第一個（最佳）選項
            selected_teams, similarity_score = team_options[0]

            # 儲存分隊結果到資料庫
            self._store_team_result(selected_teams, context="weighted")
            self._log_info(f"[WEIGHTED_CMD] Final result: {len(selected_teams)} teams, stored to DB")

            # 格式化並發送結果訊息（包含上次分隊比較）
            result_message = self._format_weighted_team_result(selected_teams, last_attendance, similarity_score, avoid_recent_count)
            self._send_message(event.reply_token, result_message)

        except Exception as e:
            self._log_error(f"Error in weighted team command: {e}")
            self._send_message(event.reply_token, "❌ 權重分隊處理失敗，請稍後再試")

    def _handle_query_command(self, event, user_id):
        """處理查詢指令，顯示用戶近五次組隊記錄"""
        try:
            # 查詢用戶近五次出席記錄
            attendances = self.attendances_repo.get_user_attendances(user_id, limit=5)
            
            if not attendances:
                self._send_message(event.reply_token, 
                    "📋 查無組隊記錄\n\n"
                    "你還沒有參與過任何分隊活動。\n"
                    "開始使用 /分隊 來參與組隊吧！")
                return
            
            # 格式化出席資料
            formatted_data = self._format_user_attendance_data(attendances, user_id)
            
            if not formatted_data:
                self._send_message(event.reply_token, "❌ 資料處理失敗，請稍後再試")
                return
            
            # 創建查詢結果 Flex Message
            query_flex = self._create_attendance_query_flex(formatted_data)
            
            # 發送結果
            self._send_flex_message(event.reply_token, "📋 近五次組隊記錄", query_flex)
            
        except Exception as e:
            self._log_error(f"Error in query command: {e}")
            self._send_message(event.reply_token, "❌ 查詢失敗，請稍後再試")
    
    def _handle_add_user_command(self, event, message_text):
        """處理新增使用者指令"""
        try:
            # 解析新增指令：/add_user 姓名 或 新增使用者 姓名
            patterns = [
                r'/add_user\s+(.+)',
                r'新增使用者\s+(.+)'
            ]
            
            user_name = None
            for pattern in patterns:
                match = re.match(pattern, message_text.strip())
                if match:
                    user_name = match.group(1).strip()
                    break
            
            if not user_name:
                self._send_message(event.reply_token, 
                    "❌ 格式錯誤\n\n正確格式：\n"
                    "🔸 /add_user 姓名\n"
                    "🔸 新增使用者 姓名\n\n"
                    "範例：/add_user 小明"
                )
                return
            
            # 檢查是否已經存在
            existing_user = self.alias_repo.find_user_by_alias(user_name)
            if existing_user:
                self._send_message(event.reply_token, f"⚠️ 使用者 '{user_name}' 已存在")
                return
            
            # 新增使用者到別名映射（使用姓名作為唯一 ID）
            success = self.alias_repo.create_or_update_alias(user_name, [user_name])
            
            if success:
                self._log_info(f"[ADD_USER] Successfully added user: {user_name}")
                self._send_message(event.reply_token, f"✅ 成功新增使用者：{user_name}")
            else:
                self._send_message(event.reply_token, "❌ 新增使用者失敗，請稍後再試")
                
        except Exception as e:
            self._log_error(f"Error in add_user command: {e}")
            self._send_message(event.reply_token, "❌ 新增使用者失敗，請稍後再試")
    
    def _handle_remove_user_command(self, event, message_text):
        """處理移除使用者指令"""
        try:
            # 解析移除指令：/remove_user 姓名 或 移除使用者 姓名
            patterns = [
                r'/remove_user\s+(.+)',
                r'移除使用者\s+(.+)'
            ]
            
            user_name = None
            for pattern in patterns:
                match = re.match(pattern, message_text.strip())
                if match:
                    user_name = match.group(1).strip()
                    break
            
            if not user_name:
                self._send_message(event.reply_token, 
                    "❌ 格式錯誤\n\n正確格式：\n"
                    "🔸 /remove_user 姓名\n"
                    "🔸 移除使用者 姓名\n\n"
                    "範例：/remove_user 小明"
                )
                return
            
            # 檢查使用者是否存在
            existing_user = self.alias_repo.find_user_by_alias(user_name)
            if not existing_user:
                self._send_message(event.reply_token, f"⚠️ 找不到使用者：{user_name}")
                return
            
            # 移除使用者
            success = self.alias_repo.delete_user_aliases(existing_user)
            
            if success:
                self._log_info(f"[REMOVE_USER] Successfully removed user: {user_name}")
                self._send_message(event.reply_token, f"✅ 成功移除使用者：{user_name}")
            else:
                self._send_message(event.reply_token, "❌ 移除使用者失敗，請稍後再試")
                
        except Exception as e:
            self._log_error(f"Error in remove_user command: {e}")
            self._send_message(event.reply_token, "❌ 移除使用者失敗，請稍後再試")
    
    def _handle_record_command(self, event, message_text):
        """處理手動記錄分隊結果指令"""
        try:
            # 提取記錄內容
            import re
            
            # 移除指令前綴
            content = re.sub(r'^(/record|記錄|/記錄)\s*', '', message_text).strip()
            
            if not content:
                self._send_message(event.reply_token, 
                    "❌ 請提供分隊結果\n\n"
                    "使用格式：\n"
                    "🔸 /record 隊伍1:小明,小華,小李 隊伍2:阿強,阿勇,阿豪\n"
                    "🔸 記錄 team1:player1,player2 team2:player3,player4")
                return
            
            # 解析分隊結果
            teams_data = self._parse_record_input(content)
            
            if not teams_data:
                self._send_message(event.reply_token, 
                    "❌ 無法解析分隊格式\n\n"
                    "請使用正確格式：隊伍名:成員1,成員2 隊伍名:成員3,成員4\n"
                    "例如：隊伍1:小明,小華 隊伍2:阿強,阿勇")
                return
            
            # 驗證分隊結果
            validation_error = self._validate_teams_data(teams_data)
            if validation_error:
                self._send_message(event.reply_token, validation_error)
                return
            
            # 轉換為球員對象並存儲
            teams_with_players = []
            total_mapping_info = {'identified': [], 'strangers': []}
            
            for team_data in teams_data:
                team_players, team_mapping = self._create_players_from_names(team_data['members'])
                if team_players:
                    teams_with_players.append(team_players)
                    # 合併映射資訊
                    total_mapping_info['identified'].extend(team_mapping['identified'])
                    total_mapping_info['strangers'].extend(team_mapping['strangers'])
            
            if not teams_with_players:
                self._send_message(event.reply_token, "❌ 無法創建有效的分隊結果")
                return
            
            # 儲存到資料庫
            self._store_team_result(teams_with_players, context="manual_record")
            
            # 創建成功回覆訊息
            success_message = "✅ 分隊結果已成功記錄\n\n"
            for i, team in enumerate(teams_with_players, 1):
                success_message += f"隊伍{i} ({len(team)}人):\n"
                for player in team:
                    success_message += f"• {player['name']}\n"
                success_message += "\n"
            
            # 添加映射資訊
            if total_mapping_info['identified'] or total_mapping_info['strangers']:
                success_message += "📋 成員映射:\n"
                if total_mapping_info['identified']:
                    identified_strs = [f"{item['input']}→{item['mapped']}" for item in total_mapping_info['identified']]
                    success_message += f"已識別: {', '.join(identified_strs)}\n"
                if total_mapping_info['strangers']:
                    stranger_strs = [f"{item['input']}→{item['stranger']}" for item in total_mapping_info['strangers']]
                    success_message += f"新成員: {', '.join(stranger_strs)}\n"
            
            self._send_message(event.reply_token, success_message)
            self._log_info(f"[RECORD] Successfully recorded teams for {len(teams_with_players)} teams")
            
        except Exception as e:
            self._log_error(f"Error in record command: {e}")
            self._send_message(event.reply_token, "❌ 記錄分隊結果失敗，請稍後再試")
    
    def _parse_record_input(self, input_text):
        """解析記錄指令的輸入格式"""
        import re
        
        # 支援格式：隊伍1:成員1,成員2 隊伍2:成員3,成員4
        # 或者：team1:player1,player2 team2:player3,player4
        teams_data = []
        
        # 使用正則表達式分割隊伍
        # 匹配格式：隊伍名:成員列表
        team_pattern = r'([^:]+):([^:]*?)(?=\s+[^:,]+:|$)'
        team_matches = re.findall(team_pattern, input_text)
        
        if not team_matches:
            self._log_info("[RECORD_PARSE] No team pattern matches found")
            return []
        
        for team_name, members_str in team_matches:
            team_name = team_name.strip()
            members_str = members_str.strip()
            
            if not team_name or not members_str:
                continue
            
            # 解析成員名稱
            separators = r'[、，,]'
            member_parts = re.split(separators, members_str)
            
            members = []
            for part in member_parts:
                name = part.strip()
                if name and len(name) >= 1:
                    members.append(name)
            
            if members:
                teams_data.append({
                    'team_name': team_name,
                    'members': members
                })
        
        self._log_info(f"[RECORD_PARSE] Parsed {len(teams_data)} teams: {[(team['team_name'], team['members']) for team in teams_data]}")
        return teams_data
    
    def _validate_teams_data(self, teams_data):
        """驗證分隊資料"""
        if not teams_data:
            return "❌ 沒有找到有效的分隊資料"
        
        if len(teams_data) < 2:
            return "❌ 至少需要2個隊伍"
        
        total_members = 0
        for team in teams_data:
            team_size = len(team['members'])
            total_members += team_size
            
            if team_size == 0:
                return f"❌ 隊伍 '{team['team_name']}' 沒有成員"
            
            if team_size > 3:
                return f"❌ 隊伍 '{team['team_name']}' 超過3人限制 ({team_size}人)"
        
        if total_members < 2:
            return "❌ 總人數太少，至少需要2人"
        
        # 檢查成員名稱重複
        all_members = []
        for team in teams_data:
            all_members.extend(team['members'])
        
        duplicates = []
        seen = set()
        for member in all_members:
            if member in seen:
                duplicates.append(member)
            seen.add(member)
        
        if duplicates:
            return f"❌ 發現重複的成員: {', '.join(duplicates)}"
        
        return None  # 無錯誤
    
    def _is_valid_team_content(self, text):
        """檢查文字是否包含有效的成員名單格式"""
        import re
        if not text:
            return False
        
        # 檢查是否包含方括號（支援半形和全形）
        if self._has_brackets(text):
            return True
        
        # 檢查是否包含分隔符
        separators = r'[、，,]'
        if re.search(separators, text):
            return True
        
        # 如果沒有分隔符，檢查是否至少有一個字符（單人也可以）
        clean_text = re.sub(r'^[^：:]*[：:]', '', text).strip()
        return len(clean_text) > 0
    
    def _parse_member_names(self, message_text):
        """解析訊息中的成員名稱"""
        import re
        
        # 移除前綴（如 "日："）
        clean_text = re.sub(r'^[^：:]*[：:]', '', message_text).strip()
        
        # 使用多種分隔符分割
        separators = r'[、，,]'
        parts = re.split(separators, clean_text)
        
        # 清理和過濾
        member_names = []
        for part in parts:
            name = part.strip()
            if name and len(name) >= 1:  # 最少1個字符
                member_names.append(name)
        
        # 移除重複名稱
        unique_member_names = self._remove_duplicate_names(member_names, case_sensitive=False)
        
        self._log_info(f"[PARSE] Extracted member names: {member_names}")
        if len(unique_member_names) != len(member_names):
            self._log_info(f"[PARSE] After deduplication: {unique_member_names}")
        
        return unique_member_names
    
    def _parse_bracket_teams(self, message_text):
        """解析包含方括號的預定義分隊格式（支援半形和全形方括號）"""
        import re
        
        # 移除前綴（如 "日："）
        clean_text = re.sub(r'^[^：:]*[：:]', '', message_text).strip()
        
        # 查找所有方括號內容：[成員1,成員2,成員3] 或 ［成員1,成員2,成員3］
        bracket_pattern = self._get_bracket_pattern()
        bracket_matches = re.findall(bracket_pattern, clean_text)
        
        if not bracket_matches:
            self._log_info("[BRACKET_PARSE] No valid bracket patterns found")
            return []
        
        predefined_teams = []
        team_counter = 1
        
        for bracket_content in bracket_matches:
            # 解析方括號內的成員名稱
            separators = r'[、，,]'
            member_parts = re.split(separators, bracket_content.strip())
            
            team_members = []
            for part in member_parts:
                name = part.strip()
                if name and len(name) >= 1:
                    team_members.append(name)
            
            # 限制每隊最多3人（3vs3）
            if len(team_members) > 3:
                self._log_info(f"[BRACKET_PARSE] Team {team_counter} has {len(team_members)} members, limiting to 3")
                team_members = team_members[:3]
            
            if team_members:
                predefined_teams.append({
                    'team_name': f'隊伍{team_counter}',
                    'members': team_members
                })
                team_counter += 1
        
        self._log_info(f"[BRACKET_PARSE] Extracted {len(predefined_teams)} predefined teams")
        for i, team in enumerate(predefined_teams):
            self._log_info(f"[BRACKET_PARSE] Team {i+1}: {team['members']}")
        
        return predefined_teams
    
    def _parse_bracket_groups(self, message_text):
        """解析包含方括號的群組格式，支援混合個別成員和群組（支援半形和全形方括號）"""
        import re
        
        # 移除前綴（如 "日："）
        clean_text = re.sub(r'^[^：:]*[：:]', '', message_text).strip()
        
        # 先提取所有方括號內容（支援半形和全形）
        bracket_pattern = self._get_bracket_pattern()
        bracket_matches = re.findall(bracket_pattern, clean_text)
        
        # 移除方括號部分，獲得剩餘的個別成員
        text_without_brackets = re.sub(bracket_pattern, '', clean_text).strip()
        
        groups = []
        individual_members = []
        
        # 解析方括號群組
        for bracket_content in bracket_matches:
            separators = r'[、，,]'
            member_parts = re.split(separators, bracket_content.strip())
            
            group_members = []
            for part in member_parts:
                name = part.strip()
                if name and len(name) >= 1:
                    group_members.append(name)
            
            # 限制每個群組最多3人（因為是3vs3）
            if len(group_members) > 3:
                self._log_info(f"[GROUP_PARSE] Group has {len(group_members)} members, limiting to 3")
                group_members = group_members[:3]
            
            # 移除群組內重複名稱
            unique_group_members = self._remove_duplicate_names(group_members, case_sensitive=False)
            
            if unique_group_members:
                groups.append(unique_group_members)
        
        # 解析剩餘的個別成員
        if text_without_brackets:
            separators = r'[、，,\s]+'  # 包含空白字符
            individual_parts = re.split(separators, text_without_brackets)
            
            for part in individual_parts:
                name = part.strip()
                if name and len(name) >= 1:
                    individual_members.append(name)
        
        # 移除個別成員列表中的重複名稱
        unique_individual_members = self._remove_duplicate_names(individual_members, case_sensitive=False)
        
        # 移除個別成員中與群組成員重複的名稱（群組優先）
        all_group_members = set()
        for group in groups:
            for member in group:
                all_group_members.add(member.lower())
        
        final_individual_members = []
        cross_duplicates_removed = []
        for member in unique_individual_members:
            if member.lower() not in all_group_members:
                final_individual_members.append(member)
            else:
                cross_duplicates_removed.append(member)
        
        if cross_duplicates_removed:
            self._log_info(f"[GROUP_PARSE] Removed individual members already in groups: {cross_duplicates_removed}")
        
        self._log_info(f"[GROUP_PARSE] Extracted {len(groups)} groups and {len(final_individual_members)} individual members")
        for i, group in enumerate(groups):
            self._log_info(f"[GROUP_PARSE] Group {i+1}: {group}")
        if final_individual_members:
            self._log_info(f"[GROUP_PARSE] Individual members: {final_individual_members}")
        
        return groups, final_individual_members
    
    def _create_players_from_names(self, member_names):
        """通過別名映射創建球員列表"""
        players = []
        mapping_info = {
            'identified': [],
            'strangers': []
        }
        stranger_count = 1
        
        for name in member_names:
            # 嘗試通過別名映射查找用戶
            user_id = self.alias_repo.find_user_by_alias(name)
            
            if user_id:
                # 找到已知用戶
                display_name = user_id  # 使用映射到的用戶ID作為顯示名稱
                mapping_info['identified'].append({
                    'input': name,
                    'mapped': user_id
                })
                self._log_info(f"[ALIAS] Mapped '{name}' -> '{user_id}'")
            else:
                # 創建路人
                display_name = f"路人{stranger_count}"
                user_id = f"STRANGER_{stranger_count}"
                mapping_info['strangers'].append({
                    'input': name,
                    'stranger': display_name
                })
                stranger_count += 1
                self._log_info(f"[STRANGER] Created '{name}' -> '{display_name}'")
            
            # 創建簡單的球員字典（不使用 Player 對象）
            player = {
                "user_id": user_id,
                "name": display_name,
                "input_name": name
            }
            players.append(player)
        
        # 基於 user_id 去除重複球員
        unique_players = []
        seen_user_ids = set()
        duplicate_players_removed = []
        
        for player in players:
            if player['user_id'] not in seen_user_ids:
                seen_user_ids.add(player['user_id'])
                unique_players.append(player)
            else:
                duplicate_players_removed.append(player['input_name'])
        
        if duplicate_players_removed:
            self._log_info(f"[PLAYERS_DEDUP] Removed duplicate players by user_id: {duplicate_players_removed}")
        
        self._log_info(f"[PLAYERS] Created {len(unique_players)} unique players for team generation")
        return unique_players, mapping_info
    
    def _generate_simple_teams(self, players, num_teams=2):
        """智能分隊方法：考慮人數限制和隊伍大小"""
        total_players = len(players)
        
        # 人數小於等於4時不分隊
        if total_players <= 4:
            self._log_info(f"[TEAMS] {total_players} players <= 4, keeping all in one team")
            return [players]
        
        # 計算最佳隊伍數量和分配方式
        optimal_teams = self._calculate_optimal_team_distribution(total_players)
        
        # 隨機打亂球員順序
        shuffled_players = players.copy()
        random.shuffle(shuffled_players)
        
        # 根據最佳分配創建隊伍
        teams = []
        player_index = 0
        
        for team_size in optimal_teams:
            team = []
            for _ in range(team_size):
                if player_index < len(shuffled_players):
                    team.append(shuffled_players[player_index])
                    player_index += 1
            teams.append(team)
        
        self._log_info(f"[TEAMS] Generated {len(teams)} teams with sizes {[len(team) for team in teams]} from {total_players} players")
        return teams
    
    def _generate_multiple_team_options(self, players, num_options=3):
        """生成多組不同的分隊選項"""
        total_players = len(players)
        
        # 人數小於等於4時不分隊，直接回傳單一選項
        if total_players <= 4:
            self._log_info(f"[MULTI_TEAMS] {total_players} players <= 4, returning single option")
            return [[players]]
        
        # 計算最佳隊伍數量和分配方式
        optimal_teams = self._calculate_optimal_team_distribution(total_players)
        
        options = []
        max_attempts = 50  # 避免無限循環
        attempts = 0
        
        while len(options) < num_options and attempts < max_attempts:
            attempts += 1
            
            # 使用不同的隨機種子
            shuffled_players = players.copy()
            random.shuffle(shuffled_players)
            
            # 根據最佳分配創建隊伍
            teams = []
            player_index = 0
            
            for team_size in optimal_teams:
                team = []
                for _ in range(team_size):
                    if player_index < len(shuffled_players):
                        team.append(shuffled_players[player_index])
                        player_index += 1
                teams.append(team)
            
            # 檢查這組結果是否與已存在的選項重複
            is_duplicate = False
            for existing_option in options:
                if self._is_team_arrangement_same(teams, existing_option):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                options.append(teams)
                self._log_info(f"[MULTI_TEAMS] Generated option {len(options)}: {[len(team) for team in teams]} teams")
        
        # 如果無法生成足夠的不同選項，用現有的選項填補
        while len(options) < num_options:
            # 重新生成一組，即使可能重複
            shuffled_players = players.copy()
            random.shuffle(shuffled_players)
            
            teams = []
            player_index = 0
            
            for team_size in optimal_teams:
                team = []
                for _ in range(team_size):
                    if player_index < len(shuffled_players):
                        team.append(shuffled_players[player_index])
                        player_index += 1
                teams.append(team)
            
            options.append(teams)
            self._log_info(f"[MULTI_TEAMS] Added fallback option {len(options)}")
        
        self._log_info(f"[MULTI_TEAMS] Generated {len(options)} team options for {total_players} players")
        return options
    
    def _generate_multiple_team_options_with_groups(self, player_groups, individual_players, num_options=3):
        """生成多組分隊選項，支援方括號群組

        Args:
            player_groups: 群組列表
            individual_players: 個別成員列表
            num_options: 要生成的選項數量
        """
        # 將群組轉換為player格式並計算總人數
        all_player_objects = []

        # 為每個群組創建player對象
        group_player_objects = []
        for group_names in player_groups:
            group_players, _ = self._create_players_from_names(group_names)
            group_player_objects.append(group_players)
            all_player_objects.extend(group_players)

        # 為個別成員創建player對象
        individual_player_objects = []
        if individual_players:
            individual_player_objects, _ = self._create_players_from_names(individual_players)
            all_player_objects.extend(individual_player_objects)

        total_players = len(all_player_objects)

        # 人數小於等於4時不分隊
        if total_players <= 4:
            self._log_info(f"[GROUP_TEAMS] {total_players} players <= 4, returning single option")
            return [[all_player_objects]]

        # 計算最佳隊伍分配
        optimal_teams = self._calculate_optimal_team_distribution(total_players)

        # 生成候選方案
        options = []
        max_attempts = num_options * 10
        attempts = 0

        while len(options) < num_options and attempts < max_attempts:
            attempts += 1

            # 創建分隊單位列表（群組 + 個別成員）
            allocation_units = []

            # 添加群組（作為不可分割的單位）
            for group_players in group_player_objects:
                allocation_units.append({
                    'type': 'group',
                    'players': group_players,
                    'size': len(group_players)
                })

            # 添加個別成員
            for player in individual_player_objects:
                allocation_units.append({
                    'type': 'individual',
                    'players': [player],
                    'size': 1
                })

            # 隨機打亂分配順序
            random.shuffle(allocation_units)

            # 分配到隊伍
            teams = [[] for _ in range(len(optimal_teams))]
            team_sizes = [0] * len(optimal_teams)

            for unit in allocation_units:
                # 找到能容納此單位的隊伍
                best_team_idx = None
                for i, max_size in enumerate(optimal_teams):
                    if team_sizes[i] + unit['size'] <= max_size:
                        if best_team_idx is None or team_sizes[i] < team_sizes[best_team_idx]:
                            best_team_idx = i

                if best_team_idx is not None:
                    teams[best_team_idx].extend(unit['players'])
                    team_sizes[best_team_idx] += unit['size']
                else:
                    # 無法分配，這個分配方案無效
                    teams = None
                    break

            if teams is None:
                continue

            # 過濾掉空隊伍
            teams = [team for team in teams if len(team) > 0]

            # 檢查是否與已有選項重複
            is_duplicate = False
            for existing_teams in options:
                if self._is_team_arrangement_same(teams, existing_teams):
                    is_duplicate = True
                    break

            if not is_duplicate:
                options.append(teams)
                self._log_info(f"[GROUP_TEAMS] Generated option {len(options)}: {[len(team) for team in teams]} teams")

        # 如果選項不足，填補剩餘
        while len(options) < num_options and len(options) > 0:
            options.append(options[0])  # 複製第一個選項

        # 如果完全無法生成選項，回退到簡單分隊
        if len(options) == 0:
            self._log_warning("[GROUP_TEAMS] Could not generate valid team options, falling back to simple teams")
            return self._generate_multiple_team_options(all_player_objects, num_options)

        self._log_info(f"[GROUP_TEAMS] Generated {len(options)} team options for {total_players} players with groups")
        return options

    def _generate_weighted_team_options_with_groups(self, player_groups, individual_players, num_options=3, avoid_recent_count=1):
        """生成多組分隊選項，支援方括號群組，並避免與最近歷史重複

        Args:
            player_groups: 群組列表
            individual_players: 個別成員列表
            num_options: 要生成的選項數量
            avoid_recent_count: 要避免的最近歷史記錄數量
        """
        # 將群組轉換為player格式並計算總人數
        all_player_objects = []

        # 為每個群組創建player對象
        group_player_objects = []
        for group_names in player_groups:
            group_players, _ = self._create_players_from_names(group_names)
            group_player_objects.append(group_players)
            all_player_objects.extend(group_players)

        # 為個別成員創建player對象
        individual_player_objects = []
        if individual_players:
            individual_player_objects, _ = self._create_players_from_names(individual_players)
            all_player_objects.extend(individual_player_objects)

        total_players = len(all_player_objects)
        self._log_info(f"[WEIGHTED_TEAMS] Input: {len(player_groups)} groups, {len(individual_players)} individuals")

        # 人數小於等於4時不分隊
        if total_players <= 4:
            self._log_info(f"[WEIGHTED_TEAMS] {total_players} players <= 4, returning single option")
            return [[all_player_objects]]

        # 計算最佳隊伍分配
        optimal_teams = self._calculate_optimal_team_distribution(total_players)
        self._log_info(f"[WEIGHTED_TEAMS] Optimal distribution: {optimal_teams} (total={total_players})")

        # 獲取歷史分隊記錄
        history = self._get_recent_team_history(avoid_recent_count)
        self._log_info(f"[WEIGHTED_TEAMS] Using {len(history)} historical records to avoid similar teams")

        # 生成候選方案 (收集更多候選以便篩選)
        candidates = []  # [(teams, similarity_score), ...]
        max_attempts = num_options * 10  # 生成更多候選
        attempts = 0

        while len(candidates) < num_options * 3 and attempts < max_attempts:
            attempts += 1

            # 創建分隊單位列表（群組 + 個別成員）
            allocation_units = []

            # 添加群組（作為不可分割的單位）
            for group_players in group_player_objects:
                allocation_units.append({
                    'type': 'group',
                    'players': group_players,
                    'size': len(group_players)
                })

            # 添加個別成員
            for player in individual_player_objects:
                allocation_units.append({
                    'type': 'individual',
                    'players': [player],
                    'size': 1
                })

            # 隨機打亂分配順序
            random.shuffle(allocation_units)

            # 分配到隊伍
            teams = [[] for _ in range(len(optimal_teams))]
            team_sizes = [0] * len(optimal_teams)

            for unit in allocation_units:
                # 找到能容納此單位的隊伍
                best_team_idx = None
                for i, max_size in enumerate(optimal_teams):
                    if team_sizes[i] + unit['size'] <= max_size:
                        if best_team_idx is None or team_sizes[i] < team_sizes[best_team_idx]:
                            best_team_idx = i

                if best_team_idx is not None:
                    teams[best_team_idx].extend(unit['players'])
                    team_sizes[best_team_idx] += unit['size']
                else:
                    # 無法分配，這個分配方案無效
                    teams = None
                    break

            if teams is None:
                continue

            # 過濾掉空隊伍
            teams = [team for team in teams if len(team) > 0]

            # 檢查是否與已有候選重複
            is_duplicate = False
            for existing_teams, _ in candidates:
                if self._is_team_arrangement_same(teams, existing_teams):
                    is_duplicate = True
                    break

            if not is_duplicate:
                # 計算與歷史記錄的相似度分數
                similarity_score = self._calculate_team_similarity_score(teams, history)
                candidates.append((teams, similarity_score))
                self._log_info(f"[WEIGHTED_TEAMS] Generated candidate {len(candidates)}: {[len(team) for team in teams]} teams, similarity_score={similarity_score}")

        self._log_info(f"[WEIGHTED_TEAMS] Generation complete: {attempts} attempts, {len(candidates)} valid candidates")

        # 按相似度分數排序，選擇分數最低的（與歷史最不相似）
        candidates.sort(key=lambda x: x[1])

        if candidates:
            worst_idx = min(num_options - 1, len(candidates) - 1)
            self._log_info(f"[WEIGHTED_TEAMS] Best option score={candidates[0][1]}, worst considered={candidates[worst_idx][1]}")

        # 選擇最佳選項
        options = []
        for teams, score in candidates[:num_options]:
            options.append((teams, score))  # 包含 score
            self._log_info(f"[WEIGHTED_TEAMS] Selected option with similarity_score={score}")

        # 如果選項不足，填補剩餘
        while len(options) < num_options and len(options) > 0:
            options.append(options[0])  # 複製第一個選項

        # 如果完全無法生成選項，回退到簡單分隊
        if len(options) == 0:
            self._log_warning("[WEIGHTED_TEAMS] Could not generate valid team options, falling back to simple teams")
            simple_teams = self._generate_multiple_team_options(all_player_objects, num_options)
            return [(teams, 0) for teams in simple_teams]  # fallback 時 score 設為 0

        self._log_info(f"[WEIGHTED_TEAMS] Generated {len(options)} team options for {total_players} players with groups (history-aware)")
        return options

    def _is_team_arrangement_same(self, teams1, teams2):
        """檢查兩組分隊安排是否相同"""
        if len(teams1) != len(teams2):
            return False
        
        # 為每組隊伍創建成員ID集合進行比較
        teams1_sets = []
        teams2_sets = []
        
        for team in teams1:
            team_ids = set(player.get('user_id', player.get('name', '')) for player in team)
            teams1_sets.append(team_ids)
        
        for team in teams2:
            team_ids = set(player.get('user_id', player.get('name', '')) for player in team)
            teams2_sets.append(team_ids)
        
        # 排序集合以便比較
        teams1_sets.sort(key=lambda s: tuple(sorted(s)))
        teams2_sets.sort(key=lambda s: tuple(sorted(s)))
        
        return teams1_sets == teams2_sets

    def _extract_pairs_from_team_sets(self, team_sets):
        """從 team_sets (frozenset of frozensets) 提取所有配對

        Args:
            team_sets: frozenset of frozensets，每個內層 frozenset 代表一隊的成員 ID

        Returns:
            frozenset: 所有配對的集合，每個配對是 frozenset([id1, id2])
        """
        pairs = set()
        for team in team_sets:
            members = list(team)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    pairs.add(frozenset([members[i], members[j]]))
        return frozenset(pairs)

    def _get_recent_team_history(self, limit=5):
        """獲取最近 N 次的分隊記錄，轉換為可比較的格式

        Args:
            limit: 要獲取的歷史記錄數量

        Returns:
            List[tuple]: 每個元素是 (team_sets, pair_sets) 的 tuple
                        - team_sets: frozenset of frozensets (每隊的 user_id 組合)
                        - pair_sets: frozenset of frozensets (所有兩兩配對)
        """
        try:
            self._log_info(f"[HISTORY] Querying last {limit} attendance records")
            recent_attendances = self.attendances_repo.get_recent_attendances(limit)
            history = []

            for i, attendance in enumerate(recent_attendances):
                teams = attendance.get('teams', [])
                teams_count = len(teams)
                self._log_info(f"[HISTORY] Record {i+1}: date={attendance.get('date')}, {teams_count} teams")
                if not teams:
                    continue

                # 將每次分隊轉換為 frozenset of frozensets
                team_sets = []
                for team in teams:
                    members = team.get('members', [])
                    # 使用 userId 作為識別，如果沒有則使用 name
                    member_ids = frozenset(
                        member.get('userId', member.get('name', ''))
                        for member in members
                    )
                    if member_ids:  # 跳過空隊伍
                        team_sets.append(member_ids)

                if team_sets:
                    team_sets_frozen = frozenset(team_sets)
                    pair_sets = self._extract_pairs_from_team_sets(team_sets_frozen)
                    history.append((team_sets_frozen, pair_sets))

            self._log_info(f"[HISTORY] Retrieved {len(history)} recent team records")
            return history

        except Exception as e:
            self._log_error(f"[HISTORY] Error getting recent team history: {e}")
            return []

    def _calculate_team_similarity_score(self, teams, history):
        """計算分隊方案與歷史記錄的相似度分數

        Args:
            teams: 當前分隊方案 (list of lists of player dicts)
            history: 歷史記錄 (list of tuples: (team_sets, pair_sets))

        Returns:
            int: 相似度分數 (0=完全不同, 越高越相似)
                 - 完全相同的分隊: +100
                 - 完全相同的隊伍: +10 per team
                 - 相同的配對: +1 per pair
        """
        if not history:
            return 0

        # 將當前分隊轉換為可比較的格式
        current_team_sets = []
        for team in teams:
            member_ids = frozenset(
                player.get('user_id', player.get('name', ''))
                for player in team
            )
            if member_ids:
                current_team_sets.append(member_ids)

        current_arrangement = frozenset(current_team_sets)
        current_pairs = self._extract_pairs_from_team_sets(current_arrangement)

        score = 0

        for past_team_sets, past_pairs in history:
            # 檢查是否完全相同
            if current_arrangement == past_team_sets:
                score += 100  # 完全相同給很高的懲罰分數
                self._log_info(f"[SIMILARITY] Found exact match with history (+100)")
                continue

            # 計算相同的隊伍組合數量 (+10 per team)
            same_teams = len(current_arrangement & past_team_sets)
            if same_teams > 0:
                score += same_teams * 10
                self._log_info(f"[SIMILARITY] Found {same_teams} same team(s) with a history record (+{same_teams * 10})")

            # 計算相同的配對數量 (+1 per pair)
            same_pairs = len(current_pairs & past_pairs)
            if same_pairs > 0:
                score += same_pairs
                self._log_info(f"[SIMILARITY] Found {same_pairs} same pair(s) with a history record (+{same_pairs})")

        self._log_info(f"[SIMILARITY] Final score={score} (compared with {len(history)} records)")
        return score

    def _calculate_optimal_team_distribution(self, total_players):
        """計算最佳隊伍分配方式（每隊最多3人）"""
        if total_players <= 4:
            return [total_players]
        
        # 基於每隊最多3人的原則計算分配
        if total_players == 5:
            return [3, 2]  # 5人: 3,2
        elif total_players == 6:
            return [3, 3]  # 6人: 3,3
        elif total_players == 7:
            return [3, 2, 2]  # 7人: 3,2,2
        elif total_players == 8:
            return [3, 3, 2]  # 8人: 3,3,2
        elif total_players == 9:
            return [3, 3, 3]  # 9人: 3,3,3
        elif total_players == 10:
            return [3, 3, 2, 2]  # 10人: 3,3,2,2
        elif total_players == 11:
            return [3, 3, 3, 2]  # 11人: 3,3,3,2
        elif total_players == 12:
            return [3, 3, 3, 3]  # 12人: 3,3,3,3
        else:
            # 對於更多人數，優先創建3人隊伍，剩餘的分成2人或3人隊伍
            teams_of_3 = total_players // 3
            remaining = total_players % 3
            
            distribution = [3] * teams_of_3
            
            if remaining == 1:
                # 如果剩1人，從最後一個3人隊調1人過來組成2人隊
                if teams_of_3 > 0:
                    distribution[-1] = 2
                    distribution.append(2)
                else:
                    distribution = [1]
            elif remaining == 2:
                # 剩2人直接組成2人隊
                distribution.append(2)
            # remaining == 0 時不需要額外處理
            
            return distribution
    
    def _create_custom_team_result_message(self, teams, mapping_info):
        """創建自定義分隊結果訊息"""
        total_players = sum(len(team) for team in teams)
        message = "🏀 **自定義分隊結果**\n\n"
        
        # 顯示成員映射資訊
        if mapping_info['identified']:
            message += "✅ **已識別成員：**\n"
            for item in mapping_info['identified']:
                message += f"• {item['input']} → {item['mapped']}\n"
            message += "\n"
        
        if mapping_info['strangers']:
            message += "👤 **新增路人：**\n"
            for item in mapping_info['strangers']:
                message += f"• {item['input']} → {item['stranger']}\n"
            message += "\n"
        
        # 顯示分隊邏輯說明
        if total_players <= 4:
            message += "ℹ️ **分隊說明：**\n"
            message += f"• 總人數 {total_players} 人 ≤ 4 人，不進行分隊\n"
            message += "• 所有成員在同一隊，適合小組活動\n\n"
        else:
            message += "ℹ️ **分隊說明：**\n"
            message += f"• 總人數 {total_players} 人，採用智能分隊\n"
            message += "• 每隊最多 3 人，確保比賽平衡\n\n"
        
        # 顯示分隊結果
        message += "🏆 **分隊結果：**\n\n"
        
        if len(teams) == 1:
            # 只有一隊時的特殊顯示
            team = teams[0]
            message += f"**全體成員** ({len(team)} 人)\n"
            for j, player in enumerate(team, 1):
                message += f"{j}. {player['name']}\n"
        else:
            # 多隊時的正常顯示
            for i, team in enumerate(teams, 1):
                message += f"**隊伍 {i}** ({len(team)} 人)\n"
                for j, player in enumerate(team, 1):
                    message += f"{j}. {player['name']}\n"
                message += "\n"
        
        return message
    
    def _create_team_selection_flex(self, team_options, mapping_info, user_id):
        """創建分隊選擇 Flex Message (單一 Carousel 包含 3 個選項 bubble)"""
        bubbles = []
        option_colors = ["#FF6B35", "#4ECDC4", "#A17DF5"]
        
        # 如果只有一組選項（人數 <= 4），直接返回簡單結果
        if len(team_options) == 1 and len(team_options[0]) == 1:
            return self._create_simple_team_bubble(team_options[0][0], mapping_info)
        
        # 為每個分隊選項創建簡潔的選項 bubble
        for option_idx, teams in enumerate(team_options):
            color = option_colors[option_idx % len(option_colors)]
            option_bubble = self._create_team_option_bubble(teams, option_idx + 1, color, user_id)
            bubbles.append(option_bubble)
        
        # 創建單一 Carousel 包含所有選項
        carousel = CarouselContainer(contents=bubbles)
        return carousel
    
    
    def _create_team_option_bubble(self, teams, option_number, color, user_id):
        """創建單一分隊選項的 bubble"""
        from datetime import datetime
        
        # 為每個隊伍創建獨立的 TextComponent
        team_components = []
        for i, team in enumerate(teams, 1):
            member_names = [player['name'] for player in team]
            if len(member_names) <= 3:
                # 3人以下顯示所有成員
                team_text = f"隊伍{i}: " + "、".join(member_names)
            else:
                # 3人以上顯示前3人 + 人數
                team_text = f"隊伍{i}: " + "、".join(member_names[:3]) + f"等{len(member_names)}人"
            
            team_component = TextComponent(
                text=team_text,
                size="sm",  # 從 xs 改為 sm 提升可讀性
                color="#333333",
                wrap=True,
                margin="xs" if i > 1 else None  # 第一隊不需要 margin，其他隊加上間距
            )
            team_components.append(team_component)
        
        return BubbleContainer(
            # 移除 size="nano" 使用標準尺寸，提供更多橫向空間
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=f"選項 {option_number}",
                        color="#ffffff",
                        align="center",
                        size="lg",
                        weight="bold"
                    ),
                    TextComponent(
                        text=f"共{len(teams)}隊",
                        color="#ffffff",
                        align="center",
                        size="sm",
                        margin="sm"
                    )
                ],
                background=self._create_gradient_background(color),
                paddingAll="20px"  # 標準尺寸可以用更多 padding
            ),
            body=BoxComponent(
                layout="vertical",
                contents=team_components,
                paddingAll="20px",  # 增加 padding 提供更好的視覺空間
                spacing="xs"  # 保持緊湊的隊伍間距
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label=f"選擇這組",
                            data=f"action=select_team&option={option_number}&user_id={user_id}"
                        ),
                        style="primary",
                        color=color
                    )
                ],
                paddingAll="16px"  # 稍微增加 footer padding
            )
        )

    def _create_custom_team_result_flex(self, teams, mapping_info):
        """創建自定義分隊結果 Flex Message (官方 Carousel 樣式)"""
        bubbles = []
        team_colors = ["#27ACB2", "#FF6B6E", "#A17DF5", "#4ECDC4", "#45B7D1", "#96CEB4"]
        
        # 如果只有一隊且人數 <= 4，返回簡單 bubble
        if len(teams) == 1 and len(teams[0]) <= 4:
            return self._create_simple_team_bubble(teams[0], mapping_info)
        
        # 為每個隊伍創建 nano bubble
        for i, team in enumerate(teams):
            color = team_colors[i % len(team_colors)]
            self._log_info(f"[DEBUG] Team {i+1}: Selected color = {color} from index {i % len(team_colors)}")
            team_bubble = self._create_nano_team_bubble(team, i + 1, color)
            bubbles.append(team_bubble)
        
        # 如果有映射資訊，添加資訊 bubble
        if mapping_info['identified'] or mapping_info['strangers']:
            info_bubble = self._create_info_nano_bubble(mapping_info, len(teams))
            bubbles.insert(0, info_bubble)  # 放在第一位
        
        # 創建 Carousel
        carousel = CarouselContainer(contents=bubbles)
        return carousel
    
    def _create_nano_team_bubble(self, team, team_number, color):
        """創建 nano 尺寸的隊伍 Bubble"""
        # 添加調試日誌
        self._log_info(f"[DEBUG] Creating nano bubble for team {team_number} with linearGradient background: {color}")
        
        # 確保顏色格式正確
        try:
            if not color.startswith('#'):
                color = f"#{color}"
            self._log_info(f"[DEBUG] Using linearGradient with color: {color}")
        except Exception as e:
            self._log_error(f"[DEBUG] Error formatting color: {e}")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=f"隊伍 {team_number}",
                        color="#ffffff",
                        align="start",
                        size="md",
                        gravity="center",
                        weight="bold"
                    ),
                    TextComponent(
                        text=f"{len(team)} 人",
                        color="#ffffff",
                        align="start",
                        size="xs",
                        gravity="center",
                        margin="lg"
                    )
                ],
                background=self._create_gradient_background(color),
                paddingTop="19px",
                paddingAll="12px",
                paddingBottom="16px"
            ),
            body=BoxComponent(
                layout="vertical",
                contents=[
                    BoxComponent(
                        layout="horizontal",
                        contents=[
                            TextComponent(
                                text=self._format_team_members(team),
                                color="#333333",
                                size="sm",
                                wrap=True
                            )
                        ],
                        flex=1
                    )
                ],
                spacing="md",
                paddingAll="12px"
            ),
            styles={
                "footer": {
                    "separator": False
                }
            }
        )
    
    def _create_info_nano_bubble(self, mapping_info, team_count):
        """創建資訊 nano bubble - 簡潔的白底黑字設計"""
        from datetime import datetime
        
        # 獲取當前月日
        now = datetime.now()
        date_str = f"{now.month}/{now.day}"
        
        return BubbleContainer(
            size="nano",
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=date_str,
                        color="#333333",
                        align="center",
                        size="lg",
                        weight="bold",
                        margin="md"
                    ),
                    TextComponent(
                        text=f"共分成 {team_count} 隊",
                        color="#333333",
                        align="center",
                        size="sm",
                        margin="sm"
                    )
                ],
                spacing="sm",
                paddingAll="16px"
            )
        )
    
    def _store_team_result(self, teams, context="custom"):
        """儲存分隊結果到資料庫"""
        try:
            from datetime import datetime
            
            # 獲取當前日期作為key
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # 轉換團隊格式為 AttendancesRepository 需要的格式
            formatted_teams = []
            for i, team in enumerate(teams, 1):
                team_data = {
                    "teamId": f"team_{i}",
                    "members": []
                }
                
                for player in team:
                    member = {
                        "userId": player.get("user_id", f"unknown_{i}"),
                        "name": player.get("name", "Unknown")
                    }
                    team_data["members"].append(member)
                
                formatted_teams.append(team_data)
            
            # 儲存到資料庫
            success = self.attendances_repo.create_or_update_attendance(current_date, formatted_teams)
            
            if success:
                total_players = sum(len(team) for team in teams)
                self._log_info(f"[DB_STORE] Successfully stored {len(formatted_teams)} teams with {total_players} players for {current_date}")
            else:
                self._log_warning(f"[DB_STORE] Failed to store team data for {current_date}")
            
            return success
            
        except Exception as e:
            self._log_error(f"[DB_STORE] Error storing team result: {e}")
            return False

    def _get_last_team_attendance(self):
        """獲取最近一次分隊記錄的完整資料"""
        try:
            recent = self.attendances_repo.get_recent_attendances(1)
            return recent[0] if recent else None
        except Exception as e:
            self._log_error(f"Error getting last team attendance: {e}")
            return None

    def _format_weighted_team_result(self, teams, last_attendance, similarity_score=None, avoid_recent_count=1):
        """格式化權重分隊結果，包含與上次分隊的比較"""
        message = "🎲 權重分隊結果"
        if similarity_score is not None:
            message += f" (相似度: {similarity_score}, 參考{avoid_recent_count}次)"
        message += "\n\n"

        # 顯示本次分隊結果
        message += "📋 本次分隊：\n"
        for i, team in enumerate(teams, 1):
            names = [p['name'] for p in team]
            message += f"  隊伍 {i}: {', '.join(names)}\n"

        # 顯示上次分隊結果
        if last_attendance:
            last_date = last_attendance.get('date', '未知日期')
            message += f"\n📜 上次分隊 ({last_date})：\n"
            for i, team in enumerate(last_attendance.get('teams', []), 1):
                members = team.get('members', [])
                names = [m.get('name', m.get('userId', '?')) for m in members]
                message += f"  隊伍 {i}: {', '.join(names)}\n"
        else:
            message += "\n📜 上次分隊：無記錄\n"

        return message

    def _format_user_attendance_data(self, attendances, user_id):
        """格式化用戶出席資料為顯示格式"""
        try:
            formatted_records = []
            
            for attendance in attendances:
                date = attendance.get('date', 'Unknown')
                teams = attendance.get('teams', [])
                
                # 找出用戶所在的隊伍
                user_team_id = None
                user_team_index = None
                
                for i, team in enumerate(teams):
                    members = team.get('members', [])
                    for member in members:
                        if member.get('userId') == user_id:
                            user_team_id = team.get('teamId')
                            user_team_index = i + 1
                            break
                    if user_team_id:
                        break
                
                if not user_team_id:
                    # 如果找不到用戶在哪一隊，跳過這筆記錄
                    continue
                
                # 格式化日期顯示 (YYYY-MM-DD -> MM/DD)
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    display_date = f"{date_obj.month}/{date_obj.day}"
                except:
                    display_date = date
                
                # 建立完整陣容資訊
                team_lineups = []
                for i, team in enumerate(teams, 1):
                    members = team.get('members', [])
                    member_names = []
                    
                    for member in members:
                        name = member.get('name', 'Unknown')
                        # 如果是當前用戶，標示為【你】
                        if member.get('userId') == user_id:
                            name = f"【{name}】"
                        member_names.append(name)
                    
                    team_lineup = f"、".join(member_names)
                    team_lineups.append(team_lineup)
                
                record = {
                    'date': date,
                    'display_date': display_date,
                    'user_team_index': user_team_index,
                    'total_teams': len(teams),
                    'team_lineups': team_lineups
                }
                
                formatted_records.append(record)
            
            self._log_info(f"[QUERY] Formatted {len(formatted_records)} attendance records for user {user_id}")
            return formatted_records
            
        except Exception as e:
            self._log_error(f"[QUERY] Error formatting attendance data: {e}")
            return []
    
    def _create_attendance_query_flex(self, formatted_records):
        """創建查詢結果的 Flex Message"""
        try:
            if len(formatted_records) == 1:
                # 只有一筆記錄，直接使用 BubbleContainer
                return self._create_single_attendance_bubble(formatted_records[0])
            else:
                # 多筆記錄，使用 CarouselContainer
                bubbles = []
                for record in formatted_records:
                    bubble = self._create_single_attendance_bubble(record)
                    bubbles.append(bubble)
                
                return CarouselContainer(contents=bubbles)
        
        except Exception as e:
            self._log_error(f"[QUERY] Error creating attendance query flex: {e}")
            # Fallback: 簡單文字顯示
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="❌ 顯示格式錯誤",
                            size="lg",
                            weight="bold",
                            color="#FF6B35"
                        )
                    ]
                )
            )
    
    def _create_single_attendance_bubble(self, record):
        """創建單一出席記錄的 bubble"""
        try:
            display_date = record.get('display_date', 'Unknown')
            user_team_index = record.get('user_team_index', 1)
            total_teams = record.get('total_teams', 1)
            team_lineups = record.get('team_lineups', [])
            
            # Header: 日期 + 用戶隊伍資訊
            header_text = f"{display_date}"
            
            # Body: 完整陣容列表
            body_contents = []
            
            lineup = team_lineups[user_team_index - 1]
            body_contents.append(
                TextComponent(
                    text=f"{lineup}",
                    size="sm",
                    color="#333333",
                    wrap=True
                )
            )
            
            return BubbleContainer(
                size="nano",
                header=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=header_text,
                            color="#ffffff",
                            align="center",
                            size="md",
                            weight="bold"
                        )
                    ],
                    background=self._create_gradient_background("#4A90E2"),
                    paddingAll="12px"
                ),
                body=BoxComponent(
                    layout="vertical",
                    contents=body_contents,
                    spacing="xs",
                    paddingAll="12px"
                )
            )
            
        except Exception as e:
            self._log_error(f"[QUERY] Error creating single attendance bubble: {e}")
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="❌ 記錄顯示錯誤",
                            color="#FF6B35"
                        )
                    ]
                )
            )
    
    def _create_simple_team_bubble(self, team, mapping_info):
        """為 ≤4 人創建簡單 bubble"""
        return BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="👥 人數太少，不需分隊",
                        weight="bold",
                        size="lg",
                        align="center",
                        color="#FF6B35"
                    ),
                    SeparatorComponent(margin="md"),
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text=f"成員名單 ({len(team)}人):",
                                weight="bold",
                                size="md",
                                color="#333333",
                                margin="md"
                            )
                        ] + [
                            TextComponent(
                                text=f"{i+1}. {player['name']}",
                                size="sm",
                                color="#666666",
                                margin="sm"
                            ) for i, player in enumerate(team)
                        ] + [
                            TextComponent(
                                text="💡 建議直接一起打球！",
                                size="sm",
                                color="#28A745",
                                margin="md",
                                weight="bold"
                            )
                        ]
                    )
                ],
                spacing="sm",
                paddingAll="16px"
            ),
            footer=self._create_team_result_footer()
        )
    
    def _format_team_members(self, team):
        """格式化隊伍成員為字串"""
        member_names = [player['name'] for player in team]
        if len(member_names) <= 3:
            return "、".join(member_names)
        else:
            return "、".join(member_names[:3]) + f"等{len(member_names)}人"
    
    def _create_member_mapping_section(self, mapping_info):
        """創建成員映射區塊"""
        contents = []
        
        if mapping_info['identified']:
            contents.append(
                TextComponent(
                    text="✅ 已識別成員",
                    weight="bold", 
                    size="md",
                    color="#28A745"
                )
            )
            
            for item in mapping_info['identified']:
                contents.append(
                    BoxComponent(
                        layout="baseline",
                        contents=[
                            TextComponent(
                                text=f"• {item['input']}",
                                size="sm",
                                color="#333333",
                                flex=0
                            ),
                            TextComponent(
                                text="→",
                                size="sm", 
                                color="#999999",
                                flex=0,
                                margin="sm"
                            ),
                            TextComponent(
                                text=item['mapped'],
                                size="sm",
                                color="#28A745",
                                weight="bold",
                                margin="sm"
                            )
                        ],
                        margin="xs"
                    )
                )
        
        if mapping_info['strangers']:
            if mapping_info['identified']:
                contents.append(self._create_spacer(size="sm"))
            
            contents.append(
                TextComponent(
                    text="👤 新增路人",
                    weight="bold",
                    size="md", 
                    color="#6C757D"
                )
            )
            
            for item in mapping_info['strangers']:
                contents.append(
                    BoxComponent(
                        layout="baseline",
                        contents=[
                            TextComponent(
                                text=f"• {item['input']}",
                                size="sm",
                                color="#333333",
                                flex=0
                            ),
                            TextComponent(
                                text="→", 
                                size="sm",
                                color="#999999",
                                flex=0,
                                margin="sm"
                            ),
                            TextComponent(
                                text=item['stranger'],
                                size="sm",
                                color="#6C757D",
                                weight="bold",
                                margin="sm"
                            )
                        ],
                        margin="xs"
                    )
                )
        
        return contents
    
    def _create_team_info_section(self, total_players):
        """創建分隊說明區塊"""
        if total_players <= 4:
            description = f"總人數 {total_players} 人 ≤ 4 人，不進行分隊\n所有成員在同一隊，適合小組活動"
        else:
            description = f"總人數 {total_players} 人，採用智能分隊\n每隊最多 3 人，確保比賽平衡"
        
        return [
            BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="ℹ️ 分隊說明",
                        weight="bold",
                        size="md",
                        color="#4A90E2"
                    ),
                    TextComponent(
                        text=description,
                        size="sm",
                        wrap=True,
                        margin="sm",
                        color="#666666"
                    )
                ],
                background=self._create_gradient_background("#F8F9FA"),
                paddingAll="md",
                cornerRadius="8px"
            )
        ]
    
    def _create_teams_display_section(self, teams):
        """創建分隊顯示區塊"""
        contents = [
            TextComponent(
                text="🏆 分隊結果",
                weight="bold",
                size="lg",
                color="#FF6B35"
            ),
            self._create_spacer(size="sm")
        ]
        
        # 隊伍顏色配置
        team_colors = ["#007BFF", "#28A745", "#DC3545", "#6F42C1", "#FD7E14", "#20C997"]
        
        if len(teams) == 1:
            # 只有一隊時的特殊顯示
            team = teams[0]
            team_card = self._create_team_card("全體成員", team, "#FF6B35")
            contents.append(team_card)
        else:
            # 多隊時的正常顯示
            for i, team in enumerate(teams):
                color = team_colors[i % len(team_colors)]
                team_card = self._create_team_card(f"隊伍 {i+1}", team, color)
                contents.append(team_card)
                if i < len(teams) - 1:  # 不是最後一隊
                    contents.append(self._create_spacer(size="sm"))
        
        return contents
    
    def _create_team_card(self, team_name, players, color):
        """創建單個隊伍卡片"""
        member_texts = []
        for j, player in enumerate(players, 1):
            member_texts.append(
                TextComponent(
                    text=f"{j}. {player['name']}",
                    size="sm",
                    color="#333333"
                )
            )
        
        return BoxComponent(
            layout="vertical",
            contents=[
                BoxComponent(
                    layout="baseline",
                    contents=[
                        TextComponent(
                            text=team_name,
                            weight="bold",
                            size="md",
                            color="#FFFFFF",
                            flex=0
                        ),
                        TextComponent(
                            text=f"({len(players)} 人)",
                            size="sm",
                            color="#FFFFFF",
                            align="end"
                        )
                    ]
                ),
                self._create_spacer(size="sm"),
                BoxComponent(
                    layout="vertical",
                    contents=member_texts,
                    spacing="xs"
                )
            ],
            background=self._create_gradient_background(color),
            paddingAll="md",
            cornerRadius="8px"
        )
    
    def _create_team_result_footer(self):
        """創建分隊結果 Footer"""
        return BoxComponent(
            layout="vertical",
            contents=[
                ButtonComponent(
                    action=PostbackAction(
                        label="🔄 重新分隊",
                        data="action=reteam"
                    ),
                    style="primary",
                    color="#FF6B35"
                ),
                ButtonComponent(
                    action=PostbackAction(
                        label="❓ 分隊說明",
                        data="action=team_help"
                    ),
                    style="link"
                )
            ],
            spacing="sm"
        )

# 測試功能
if __name__ == "__main__":
    # 這裡可以加入單元測試
    print("LINE Bot 訊息處理器已準備就緒")