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
from src.models.mongodb_models import AliasMapRepository
from src.database.mongodb import get_database
import random

class LineMessageHandler:
    def __init__(self, line_bot_api, logger=None):
        self.line_bot_api = line_bot_api
        self.logger = logger
        # Initialize MongoDB repositories
        db = get_database()
        self.alias_repo = AliasMapRepository(db)
    
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
            elif message_text.startswith('/help') or message_text == '幫助' or message_text == '說明':
                self._log_info(f"[COMMAND] Matched: /help, User: {user_id}")
                self._handle_help_command(event, is_group)
            elif message_text == '開始':
                self._log_info(f"[COMMAND] Matched: 開始, User: {user_id}")
                self._handle_start_command(event)
            elif message_text.startswith('/分隊') or message_text.startswith('分隊'):
                self._log_info(f"[COMMAND] Matched: /分隊, User: {user_id}")
                self._handle_custom_team_command(event, message_text)
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
            else:
                self._send_message(event.reply_token, "❓ 未知的操作")

        except Exception as e:
            import traceback
            self._log_error(f"[ERROR] Error handling postback from {user_id}: {e}")
            self._log_error(traceback.format_exc())
            self._send_message(event.reply_token, "❌ 系統發生錯誤，請稍後再試")
    
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
        message += "🔸 /list\n"
        message += "   查看所有球員\n"
        message += "🔸 /team [隊數]\n"
        message += "   自動分隊 (預設 2 隊)\n"
        message += "🔸 /profile\n"
        message += "   查看個人資料\n"
        message += "🔸 /delete\n"
        message += "   刪除個人資料\n\n"
        message += "📖 使用範例：\n"
        if is_group:
            message += "• /group_team 2 (群組快速分隊)\n"
        message += "• /register 小明 8 7 9\n"
        message += "• /team 3\n\n"
        message += "⚠️ 注意事項：\n"
        message += "• 技能值範圍：1-10\n"
        message += "• 群組分隊會使用預設技能值\n"
        message += "• 系統會自動平衡隊伍實力"
        
        self._send_message(event.reply_token, message)
    
    def _handle_start_command(self, event):
        """處理開始指令"""
        welcome_flex = self._create_welcome_flex()
        self._send_flex_message(event.reply_token, "籃球分隊機器人", welcome_flex)
    
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
            
            # 生成隊伍
            teams = self.team_generator.generate_teams(players, num_teams)
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
                        backgroundColor="#F8F9FA",
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
                    "例如：🥛、凱、豪、金、kin、勇")
                return
            
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
                return
            
            # 使用智能分隊邏輯（自動決定隊伍數量）
            teams = self._generate_simple_teams(players)
            
            # 創建分隊結果 Flex Message
            result_flex = self._create_custom_team_result_flex(teams, mapping_info)
            
            self._send_flex_message(event.reply_token, "自定義分隊結果", result_flex)
            
        except Exception as e:
            self._log_error(f"Error in custom team command: {e}")
            self._send_message(event.reply_token, "❌ 分隊處理失敗，請稍後再試")
    
    def _is_valid_team_content(self, text):
        """檢查文字是否包含有效的成員名單格式"""
        import re
        if not text:
            return False
        
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
        
        self._log_info(f"[PARSE] Extracted member names: {member_names}")
        return member_names
    
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
        
        self._log_info(f"[PLAYERS] Created {len(players)} players for team generation")
        return players, mapping_info
    
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
        self._log_info(f"[DEBUG] Creating nano bubble for team {team_number} with color: {color}")
        
        # 測試不同的背景色設定方法
        try:
            # 方法1：確認顏色格式
            if not color.startswith('#'):
                color = f"#{color}"
            self._log_info(f"[DEBUG] Formatted color: {color}")
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
                backgroundColor=color,
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
                                color="#8C8C8C",
                                size="sm",
                                wrap=True
                            )
                        ],
                        flex=1
                    )
                ],
                spacing="md",
                paddingAll="12px"
            )
            # 暫時移除 styles 設定來測試背景色是否有影響
            # styles={
            #     "footer": {
            #         "separator": False
            #     }
            # }
        )
    
    def _create_info_nano_bubble(self, mapping_info, team_count):
        """創建資訊 nano bubble"""
        # 計算已識別和路人的數量
        identified_count = len(mapping_info.get('identified', []))
        strangers_count = len(mapping_info.get('strangers', []))
        total_count = identified_count + strangers_count
        
        # 創建進度條效果
        identified_percentage = int((identified_count / total_count * 100)) if total_count > 0 else 0
        
        # 添加調試日誌
        self._log_info(f"[DEBUG] Creating info nano bubble with backgroundColor: #4ECDC4")
        
        return BubbleContainer(
            size="nano",
            header=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="分隊資訊",
                        color="#ffffff",
                        align="start",
                        size="md",
                        gravity="center",
                        weight="bold"
                    ),
                    TextComponent(
                        text=f"已識別 {identified_percentage}%",
                        color="#ffffff",
                        align="start",
                        size="xs",
                        gravity="center",
                        margin="lg"
                    ),
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            BoxComponent(
                                layout="vertical",
                                contents=[
                                    # 使用 filler 需要特殊處理，這裡改用 text
                                    TextComponent(text=" ", size="xxs")
                                ],
                                width=f"{identified_percentage}%",
                                backgroundColor="#0D8186",
                                height="6px"
                            )
                        ],
                        backgroundColor="#9FD8E36E",
                        height="6px",
                        margin="sm"
                    )
                ],
                backgroundColor="#4ECDC4",
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
                                text=f"共分成 {team_count} 隊\n已識別 {identified_count} 人，新增 {strangers_count} 人",
                                color="#8C8C8C",
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
                backgroundColor="#F8F9FA",
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
            backgroundColor=color,
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