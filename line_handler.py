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
from models import Player, PlayerDatabase, GroupDatabase
from team_algorithm import TeamGenerator
from group_manager import GroupManager

class LineMessageHandler:
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api
        self.team_generator = TeamGenerator()
        self.group_manager = GroupManager(line_bot_api)
    
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
    
    def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        try:
            # 檢查是否為群組訊息
            is_group = hasattr(event.source, 'group_id')
            group_id = getattr(event.source, 'group_id', None)
            
            # 根據指令路由到不同的處理函數
            if message_text.startswith('/group_team') or message_text.startswith('群組分隊'):
                if is_group:
                    self._handle_group_team_command(event, message_text, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/group_players') or message_text.startswith('群組成員'):
                if is_group:
                    self._handle_group_players_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/group_stats') or message_text.startswith('群組統計'):
                if is_group:
                    self._handle_group_stats_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/sync') or message_text.startswith('同步成員'):
                if is_group:
                    self._handle_sync_command(event, group_id)
                else:
                    self._send_message(event.reply_token, "❌ 此指令只能在群組中使用")
            elif message_text.startswith('/register') or message_text.startswith('註冊'):
                self._handle_register_command(event, message_text, group_id)
            elif message_text.startswith('/list') or message_text == '球員列表':
                self._handle_list_command(event)
            elif message_text.startswith('/team') or message_text.startswith('分隊'):
                self._handle_team_command(event, message_text)
            elif message_text.startswith('/profile') or message_text == '我的資料':
                self._handle_profile_command(event, user_id)
            elif message_text.startswith('/delete') or message_text == '刪除資料':
                self._handle_delete_command(event, user_id)
            elif message_text.startswith('/help') or message_text == '幫助' or message_text == '說明':
                self._handle_help_command(event, is_group)
            elif message_text == '開始':
                self._handle_start_command(event)
            else:
                self._handle_unknown_command(event, is_group)
                
        except Exception as e:
            print(f"Error handling message: {e}")
            self._send_message(event.reply_token, "❌ 系統發生錯誤，請稍後再試")
    
    def handle_postback_event(self, event):
        """處理 Postback 事件"""
        user_id = event.source.user_id
        data = event.postback.data
        
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
            else:
                self._send_message(event.reply_token, "❓ 未知的操作")
                
        except Exception as e:
            print(f"Error handling postback: {e}")
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
                
                # 創建球員
                player = Player(user_id, name, shooting, defense, stamina, 
                              source_group=group_id, is_registered=True)
                
                if PlayerDatabase.create_player(player):
                    register_flex = self._create_register_success_flex(player)
                    self._send_flex_message(event.reply_token, "球員註冊成功", register_flex)
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
        list_flex = self._create_player_list_flex(players)
        self._send_flex_message(event.reply_token, "球員列表", list_flex)
    
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
            team_flex = self._create_team_result_flex(teams)
            self._send_flex_message(event.reply_token, "分隊結果", team_flex)
        except Exception as e:
            print(f"Error generating teams: {e}")
            self._send_message(event.reply_token, "❌ 分隊失敗，請稍後再試")
    
    def _handle_profile_command(self, event, user_id):
        """處理個人資料查詢指令"""
        player = PlayerDatabase.get_player(user_id)
        
        if player:
            profile_flex = self._create_profile_flex(player)
            self._send_flex_message(event.reply_token, "個人資料", profile_flex)
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
            message = TextSendMessage(text=message_text, quick_reply=quick_reply)
            self.line_bot_api.reply_message(reply_token, message)
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def _send_flex_message(self, reply_token, alt_text, flex_content):
        """發送 Flex Message"""
        try:
            message = FlexSendMessage(alt_text=alt_text, contents=flex_content)
            self.line_bot_api.reply_message(reply_token, message)
        except Exception as e:
            print(f"Error sending flex message: {e}")
    
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
    
    def _create_register_success_flex(self, player: Player):
        """創建球員註冊成功 Flex Message"""
        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="✅ 註冊成功！",
                        weight="bold",
                        size="xl",
                        align="center",
                        color="#28A745"
                    ),
                    SeparatorComponent(margin="md"),
                    self._create_spacer(size="md"),
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text=f"👤 {player.name}",
                                weight="bold",
                                size="lg",
                                align="center",
                                color="#333333"
                            ),
                            self._create_spacer(size="md"),
                            self._create_skill_bar("🎯 投籃", player.shooting_skill),
                            self._create_spacer(size="sm"),
                            self._create_skill_bar("🛡️ 防守", player.defense_skill),
                            self._create_spacer(size="sm"),
                            self._create_skill_bar("💪 體力", player.stamina),
                            self._create_spacer(size="md"),
                            BoxComponent(
                                layout="baseline",
                                contents=[
                                    TextComponent(
                                        text="⭐ 總體評分：",
                                        size="sm",
                                        color="#666666",
                                        flex=0
                                    ),
                                    TextComponent(
                                        text=f"{player.overall_rating:.1f}/10",
                                        weight="bold",
                                        size="md",
                                        color="#FF6B35",
                                        align="end"
                                    )
                                ]
                            )
                        ],
                        backgroundColor="#F8F9FA",
                        paddingAll="md",
                        cornerRadius="8px"
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="📋 查看所有球員",
                            data="action=list_players"
                        ),
                        style="primary",
                        color="#4A90E2"
                    ),
                    ButtonComponent(
                        action=PostbackAction(
                            label="🏀 開始分隊",
                            data="action=team_help"
                        ),
                        style="secondary"
                    )
                ],
                spacing="sm"
            )
        )
        return bubble

    def _create_skill_bar(self, skill_name: str, skill_value: int):
        """創建技能條組件"""
        # 計算技能條的填充比例
        filled_bars = skill_value
        empty_bars = 10 - skill_value
        skill_bar = "█" * filled_bars + "░" * empty_bars
        
        return BoxComponent(
            layout="baseline",
            contents=[
                TextComponent(
                    text=skill_name,
                    size="sm",
                    color="#666666",
                    flex=0
                ),
                self._create_spacer(size="sm"),
                TextComponent(
                    text=skill_bar,
                    size="xs",
                    color="#FF6B35",
                    flex=0
                ),
                TextComponent(
                    text=f"{skill_value}",
                    weight="bold",
                    size="sm",
                    color="#333333",
                    align="end"
                )
            ]
        )
    
    def _create_player_list_flex(self, players: List[Player]):
        """創建球員列表 Flex Message"""
        if not players:
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="📋 球員列表",
                            weight="bold",
                            size="xl",
                            align="center",
                            color="#4A90E2"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="目前沒有註冊的球員",
                            align="center",
                            color="#666666"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="快來註冊第一位球員吧！",
                            align="center",
                            size="sm",
                            color="#999999"
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
                        )
                    ]
                )
            )

        # 創建球員卡片列表
        bubbles = []
        for i, player in enumerate(players[:10]):  # 限制最多顯示10個球員
            player_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"👤 {player.name}",
                            weight="bold",
                            size="md",
                            color="#333333"
                        ),
                        self._create_spacer(size="sm"),
                        self._create_mini_skill_display(player),
                        self._create_spacer(size="sm"),
                        BoxComponent(
                            layout="baseline",
                            contents=[
                                TextComponent(
                                    text="總評：",
                                    size="sm",
                                    color="#666666",
                                    flex=0
                                ),
                                TextComponent(
                                    text=f"{player.overall_rating:.1f}/10",
                                    weight="bold",
                                    color="#FF6B35",
                                    align="end"
                                )
                            ]
                        )
                    ]
                )
            )
            bubbles.append(player_bubble)

        # 添加總結卡片
        summary_bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="📊 統計資訊",
                        weight="bold",
                        size="md",
                        color="#4A90E2"
                    ),
                    SeparatorComponent(margin="sm"),
                    self._create_spacer(size="sm"),
                    TextComponent(
                        text=f"總球員數：{len(players)} 人",
                        size="sm",
                        color="#333333"
                    ),
                    self._create_spacer(size="xs"),
                    TextComponent(
                        text=f"平均評分：{sum(p.overall_rating for p in players)/len(players):.1f}",
                        size="sm",
                        color="#666666"
                    ),
                    self._create_spacer(size="sm"),
                    *self._create_team_suggestions(len(players))
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="🏀 開始分隊",
                            data="action=team_help"
                        ),
                        style="primary",
                        color="#4A90E2"
                    )
                ]
            ) if len(players) >= 2 else None
        )
        bubbles.append(summary_bubble)

        return CarouselContainer(contents=bubbles)

    def _create_mini_skill_display(self, player: Player):
        """創建迷你技能顯示"""
        return BoxComponent(
            layout="horizontal",
            contents=[
                BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(text="🎯", size="xs", align="center"),
                        TextComponent(text=str(player.shooting_skill), size="xs", align="center", color="#FF6B35")
                    ],
                    flex=1
                ),
                BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(text="🛡️", size="xs", align="center"),
                        TextComponent(text=str(player.defense_skill), size="xs", align="center", color="#4A90E2")
                    ],
                    flex=1
                ),
                BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(text="💪", size="xs", align="center"),
                        TextComponent(text=str(player.stamina), size="xs", align="center", color="#28A745")
                    ],
                    flex=1
                )
            ],
            backgroundColor="#F8F9FA",
            paddingAll="sm",
            cornerRadius="8px"
        )

    def _create_team_suggestions(self, player_count: int):
        """創建分隊建議"""
        suggestions = self.team_generator.suggest_optimal_teams(player_count)
        if not suggestions:
            return [TextComponent(text="需要更多球員才能分隊", size="xs", color="#999999")]
        
        suggestion_texts = []
        for num_teams, description in suggestions[:2]:  # 只顯示前2個建議
            suggestion_texts.append(
                TextComponent(
                    text=f"• {description}",
                    size="xs",
                    color="#666666"
                )
            )
        return suggestion_texts
    
    def _create_team_result_flex(self, teams: List[List[Player]]):
        """創建分隊結果 Flex Message"""
        if not teams:
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="❌ 分隊失敗",
                            weight="bold",
                            size="xl",
                            align="center",
                            color="#DC3545"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="目前沒有足夠的球員進行分隊",
                            align="center",
                            wrap=True,
                            color="#666666"
                        )
                    ]
                )
            )

        bubbles = []
        stats = self.team_generator.get_team_stats(teams)
        
        # 為每個隊伍創建卡片
        team_colors = ["#FF6B35", "#4A90E2", "#28A745", "#FD7E14", "#6F42C1"]
        
        for i, (team, stat) in enumerate(zip(teams, stats)):
            color = team_colors[i % len(team_colors)]
            
            team_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"🔥 第 {i+1} 隊",
                            weight="bold",
                            size="lg",
                            align="center",
                            color=color
                        ),
                        TextComponent(
                            text=f"平均評分：{stat['avg_rating']:.1f}",
                            size="sm",
                            align="center",
                            color="#666666",
                            margin="sm"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="sm"),
                        *self._create_team_players_list(team),
                        self._create_spacer(size="md"),
                        self._create_team_stats_display(stat, color)
                    ]
                )
            )
            bubbles.append(team_bubble)
        
        # 添加總結統計卡片
        if len(stats) >= 2:
            ratings = [s['avg_rating'] for s in stats if s['player_count'] > 0]
            balance_score = 10 - (max(ratings) - min(ratings)) if ratings else 0
            
            summary_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="⚖️ 分隊總結",
                            weight="bold",
                            size="lg",
                            align="center",
                            color="#6F42C1"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="md"),
                        BoxComponent(
                            layout="baseline",
                            contents=[
                                TextComponent(
                                    text="隊伍平衡度：",
                                    size="sm",
                                    color="#666666",
                                    flex=0
                                ),
                                TextComponent(
                                    text=f"{balance_score:.1f}/10",
                                    weight="bold",
                                    size="md",
                                    color="#FF6B35",
                                    align="end"
                                )
                            ]
                        ),
                        self._create_spacer(size="sm"),
                        TextComponent(
                            text=self._get_balance_comment(balance_score),
                            size="sm",
                            wrap=True,
                            align="center",
                            color="#666666"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text=f"總共 {sum(len(team) for team in teams)} 位球員",
                            size="xs",
                            align="center",
                            color="#999999"
                        )
                    ]
                ),
                footer=BoxComponent(
                    layout="vertical",
                    contents=[
                        ButtonComponent(
                            action=PostbackAction(
                                label="🔄 重新分隊",
                                data="action=team_help"
                            ),
                            style="secondary"
                        )
                    ]
                )
            )
            bubbles.append(summary_bubble)

        return CarouselContainer(contents=bubbles)

    def _create_team_players_list(self, team: List[Player]):
        """創建隊伍球員列表"""
        if not team:
            return [TextComponent(text="⚠️ 無球員", size="sm", color="#999999", align="center")]
        
        player_components = []
        for j, player in enumerate(team, 1):
            player_components.append(
                BoxComponent(
                    layout="baseline",
                    contents=[
                        TextComponent(
                            text=f"{j}.",
                            size="sm",
                            color="#666666",
                            flex=0
                        ),
                        self._create_spacer(size="sm"),
                        TextComponent(
                            text=player.name,
                            size="sm",
                            color="#333333",
                            flex=1
                        ),
                        TextComponent(
                            text=f"{player.overall_rating:.1f}",
                            weight="bold",
                            size="sm",
                            color="#FF6B35",
                            align="end",
                            flex=0
                        )
                    ],
                    margin="xs"
                )
            )
        return player_components

    def _create_team_stats_display(self, stat: dict, color: str):
        """創建隊伍統計顯示"""
        return BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(
                    text="📊 技能統計",
                    weight="bold",
                    size="sm",
                    color=color
                ),
                self._create_spacer(size="xs"),
                BoxComponent(
                    layout="horizontal",
                    contents=[
                        BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(text="🎯", size="xs", align="center"),
                                TextComponent(text=f"{stat['avg_shooting']:.1f}", size="xs", align="center", color="#FF6B35")
                            ],
                            flex=1
                        ),
                        BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(text="🛡️", size="xs", align="center"),
                                TextComponent(text=f"{stat['avg_defense']:.1f}", size="xs", align="center", color="#4A90E2")
                            ],
                            flex=1
                        ),
                        BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(text="💪", size="xs", align="center"),
                                TextComponent(text=f"{stat['avg_stamina']:.1f}", size="xs", align="center", color="#28A745")
                            ],
                            flex=1
                        )
                    ],
                    backgroundColor="#F8F9FA",
                    paddingAll="sm",
                    cornerRadius="8px"
                )
            ]
        )

    def _get_balance_comment(self, balance_score: float) -> str:
        """根據平衡度得分返回評語"""
        if balance_score >= 9:
            return "🌟 完美平衡！隊伍實力非常均等"
        elif balance_score >= 7:
            return "👍 平衡良好，可以開始比賽了"
        elif balance_score >= 5:
            return "⚠️ 略有差距，但還算公平"
        else:
            return "🔄 建議重新分隊獲得更好平衡"
    
    def _create_profile_flex(self, player: Player):
        """創建個人資料 Flex Message"""
        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="👤 個人資料",
                        weight="bold",
                        size="xl",
                        align="center",
                        color="#4A90E2"
                    ),
                    SeparatorComponent(margin="md"),
                    self._create_spacer(size="md"),
                    TextComponent(
                        text=player.name,
                        weight="bold",
                        size="lg",
                        align="center",
                        color="#333333"
                    ),
                    self._create_spacer(size="lg"),
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(
                                text="🏀 技能評估",
                                weight="bold",
                                size="md",
                                color="#FF6B35",
                                margin="none"
                            ),
                            self._create_spacer(size="md"),
                            self._create_skill_bar("🎯 投籃", player.shooting_skill),
                            self._create_spacer(size="sm"),
                            self._create_skill_bar("🛡️ 防守", player.defense_skill),
                            self._create_spacer(size="sm"),
                            self._create_skill_bar("💪 體力", player.stamina),
                            self._create_spacer(size="md"),
                            SeparatorComponent(),
                            self._create_spacer(size="md"),
                            BoxComponent(
                                layout="baseline",
                                contents=[
                                    TextComponent(
                                        text="⭐ 總體評分",
                                        weight="bold",
                                        color="#333333",
                                        flex=0
                                    ),
                                    TextComponent(
                                        text=f"{player.overall_rating:.1f}/10",
                                        weight="bold",
                                        size="lg",
                                        color="#FF6B35",
                                        align="end"
                                    )
                                ]
                            ),
                            self._create_spacer(size="md"),
                            BoxComponent(
                                layout="baseline",
                                contents=[
                                    TextComponent(
                                        text="📅 註冊時間",
                                        size="sm",
                                        color="#666666",
                                        flex=0
                                    ),
                                    TextComponent(
                                        text=player.created_at[:10],
                                        size="sm",
                                        color="#666666",
                                        align="end"
                                    )
                                ]
                            )
                        ],
                        backgroundColor="#F8F9FA",
                        paddingAll="md",
                        cornerRadius="8px"
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="📋 查看所有球員",
                            data="action=list_players"
                        ),
                        style="secondary"
                    ),
                    ButtonComponent(
                        action=PostbackAction(
                            label="🏀 開始分隊",
                            data="action=team_help"
                        ),
                        style="primary",
                        color="#4A90E2"
                    )
                ],
                spacing="sm"
            )
        )
        return bubble
    
    # === 群組專用 Flex Message 模板函數 ===
    
    def _create_group_player_list_flex(self, players: List[Player], group_id: str):
        """創建群組成員清單 Flex Message"""
        if not players:
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="📋 群組成員清單",
                            weight="bold",
                            size="xl",
                            align="center",
                            color="#4A90E2"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="目前沒有偵測到群組成員",
                            align="center",
                            color="#666666"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="請使用 /sync 同步群組成員",
                            align="center",
                            size="sm",
                            color="#999999"
                        )
                    ]
                )
            )

        # 創建群組成員卡片列表
        bubbles = []
        registered_players = [p for p in players if p.is_registered]
        member_players = [p for p in players if not p.is_registered]
        
        # 顯示註冊球員
        for i, player in enumerate(registered_players[:5]):
            player_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"✅ {player.name}",
                            weight="bold",
                            size="md",
                            color="#28A745"
                        ),
                        TextComponent(
                            text="已註冊球員",
                            size="sm",
                            color="#666666",
                            margin="sm"
                        ),
                        self._create_spacer(size="sm"),
                        self._create_mini_skill_display(player),
                        self._create_spacer(size="sm"),
                        BoxComponent(
                            layout="baseline",
                            contents=[
                                TextComponent(
                                    text="總評：",
                                    size="sm",
                                    color="#666666",
                                    flex=0
                                ),
                                TextComponent(
                                    text=f"{player.overall_rating:.1f}/10",
                                    weight="bold",
                                    color="#FF6B35",
                                    align="end"
                                )
                            ]
                        )
                    ]
                )
            )
            bubbles.append(player_bubble)
        
        # 顯示群組成員
        for i, player in enumerate(member_players[:5]):
            player_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"👤 {player.name}",
                            weight="bold",
                            size="md",
                            color="#4A90E2"
                        ),
                        TextComponent(
                            text="群組成員",
                            size="sm",
                            color="#666666",
                            margin="sm"
                        ),
                        self._create_spacer(size="sm"),
                        self._create_mini_skill_display(player),
                        self._create_spacer(size="sm"),
                        TextComponent(
                            text="使用預設技能值",
                            size="xs",
                            color="#999999",
                            align="center"
                        )
                    ]
                )
            )
            bubbles.append(player_bubble)

        # 添加統計總結卡片
        summary_bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="📊 群組統計",
                        weight="bold",
                        size="md",
                        color="#6F42C1"
                    ),
                    SeparatorComponent(margin="sm"),
                    self._create_spacer(size="sm"),
                    TextComponent(
                        text=f"總成員數：{len(players)} 人",
                        size="sm",
                        color="#333333"
                    ),
                    self._create_spacer(size="xs"),
                    TextComponent(
                        text=f"已註冊：{len(registered_players)} 人",
                        size="sm",
                        color="#28A745"
                    ),
                    self._create_spacer(size="xs"),
                    TextComponent(
                        text=f"群組成員：{len(member_players)} 人",
                        size="sm",
                        color="#4A90E2"
                    ),
                    self._create_spacer(size="sm"),
                    TextComponent(
                        text=f"平均評分：{sum(p.overall_rating for p in players)/len(players):.1f}",
                        size="sm",
                        color="#666666"
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="🏀 開始分隊",
                            data=f"action=group_team&group_id={group_id}"
                        ),
                        style="primary",
                        color="#FF6B35"
                    )
                ]
            ) if len(players) >= 2 else None
        )
        bubbles.append(summary_bubble)

        return CarouselContainer(contents=bubbles)
    
    def _create_group_team_result_flex(self, teams: List[List[Player]], group_id: str):
        """創建群組分隊結果 Flex Message"""
        if not teams:
            return BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="❌ 群組分隊失敗",
                            weight="bold",
                            size="xl",
                            align="center",
                            color="#DC3545"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text="目前群組成員不足進行分隊",
                            align="center",
                            wrap=True,
                            color="#666666"
                        )
                    ]
                )
            )

        bubbles = []
        stats = self.team_generator.get_team_stats(teams)
        
        # 為每個隊伍創建卡片
        team_colors = ["#FF6B35", "#4A90E2", "#28A745", "#FD7E14", "#6F42C1"]
        
        for i, (team, stat) in enumerate(zip(teams, stats)):
            color = team_colors[i % len(team_colors)]
            
            team_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"🏀 群組第 {i+1} 隊",
                            weight="bold",
                            size="lg",
                            align="center",
                            color=color
                        ),
                        TextComponent(
                            text=f"平均評分：{stat['avg_rating']:.1f}",
                            size="sm",
                            align="center",
                            color="#666666",
                            margin="sm"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="sm"),
                        *self._create_group_team_players_list(team),
                        self._create_spacer(size="md"),
                        self._create_team_stats_display(stat, color)
                    ]
                )
            )
            bubbles.append(team_bubble)
        
        # 添加群組分隊總結
        if len(stats) >= 2:
            ratings = [s['avg_rating'] for s in stats if s['player_count'] > 0]
            balance_score = 10 - (max(ratings) - min(ratings)) if ratings else 0
            
            summary_bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text="⚖️ 群組分隊總結",
                            weight="bold",
                            size="lg",
                            align="center",
                            color="#6F42C1"
                        ),
                        SeparatorComponent(margin="md"),
                        self._create_spacer(size="md"),
                        BoxComponent(
                            layout="baseline",
                            contents=[
                                TextComponent(
                                    text="隊伍平衡度：",
                                    size="sm",
                                    color="#666666",
                                    flex=0
                                ),
                                TextComponent(
                                    text=f"{balance_score:.1f}/10",
                                    weight="bold",
                                    size="md",
                                    color="#FF6B35",
                                    align="end"
                                )
                            ]
                        ),
                        self._create_spacer(size="sm"),
                        TextComponent(
                            text=self._get_balance_comment(balance_score),
                            size="sm",
                            wrap=True,
                            align="center",
                            color="#666666"
                        ),
                        self._create_spacer(size="md"),
                        TextComponent(
                            text=f"群組總共 {sum(len(team) for team in teams)} 位成員參與",
                            size="xs",
                            align="center",
                            color="#999999"
                        )
                    ]
                ),
                footer=BoxComponent(
                    layout="vertical",
                    contents=[
                        ButtonComponent(
                            action=PostbackAction(
                                label="🔄 重新分隊",
                                data=f"action=group_reteam&group_id={group_id}"
                            ),
                            style="secondary"
                        )
                    ]
                )
            )
            bubbles.append(summary_bubble)

        return CarouselContainer(contents=bubbles)
    
    def _create_group_team_players_list(self, team: List[Player]):
        """創建群組隊伍球員列表"""
        if not team:
            return [TextComponent(text="⚠️ 無成員", size="sm", color="#999999", align="center")]
        
        player_components = []
        for j, player in enumerate(team, 1):
            status_icon = "✅" if player.is_registered else "👤"
            
            player_components.append(
                BoxComponent(
                    layout="baseline",
                    contents=[
                        TextComponent(
                            text=f"{j}.",
                            size="sm",
                            color="#666666",
                            flex=0
                        ),
                        self._create_spacer(size="sm"),
                        TextComponent(
                            text=f"{status_icon} {player.name}",
                            size="sm",
                            color="#333333",
                            flex=1
                        ),
                        TextComponent(
                            text=f"{player.overall_rating:.1f}",
                            weight="bold",
                            size="sm",
                            color="#FF6B35",
                            align="end",
                            flex=0
                        )
                    ],
                    margin="xs"
                )
            )
        return player_components

# 測試功能
if __name__ == "__main__":
    # 這裡可以加入單元測試
    print("LINE Bot 訊息處理器已準備就緒")