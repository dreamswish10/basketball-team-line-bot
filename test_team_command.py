#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試新的 /分隊 指令機制
"""

import random
import sys
import os

# 模擬 AliasMapRepository 類
class MockAliasMapRepository:
    def __init__(self):
        # 模擬別名映射數據
        self.aliases = {
            "奶": "🥛",
            "🥛": "奶", 
            "凱": "凱",
            "豪": "豪",
            "金": "金毛",
            "金毛": "金毛",
            "kin": "Akin",
            "Akin": "Akin",
            "勇": "勇"
        }
    
    def find_user_by_alias(self, alias):
        """模擬別名查找"""
        return self.aliases.get(alias)

# 模擬 Event 類
class MockEvent:
    def __init__(self, message_text, reply_token="mock_token", has_reply=False, reply_content=None):
        self.reply_token = reply_token
        self.message = MockMessage(message_text, has_reply, reply_content)
        self.source = MockSource()

class MockMessage:
    def __init__(self, text, has_reply=False, reply_content=None):
        self.text = text
        if has_reply:
            self.quoted_message_id = "mock_reply_id"
            self._reply_content = reply_content
        else:
            self.quoted_message_id = None
            self._reply_content = None

class MockSource:
    def __init__(self):
        self.user_id = "mock_user"

# 模擬 LineMessageHandler 的核心方法
class MockLineMessageHandler:
    def __init__(self):
        self.alias_repo = MockAliasMapRepository()
    
    def _log_info(self, message):
        print(f"[INFO] {message}")
    
    def _log_warning(self, message):
        print(f"[WARNING] {message}")
    
    def _log_error(self, message):
        print(f"[ERROR] {message}")
    
    def _send_message(self, reply_token, message):
        print(f"📱 Bot 回應: {message}")
    
    def _send_flex_message(self, reply_token, alt_text, flex_content):
        print(f"📱 Bot Flex 回應: {alt_text}")
        print(f"   Flex 內容: [Flex Message Object]")
    
    def _extract_reply_content(self, event):
        """提取回覆訊息的內容（模擬版本）"""
        try:
            # 檢查是否有回覆訊息
            if hasattr(event.message, 'quoted_message_id') and event.message.quoted_message_id:
                self._log_info(f"[REPLY] Detected reply to message: {event.message.quoted_message_id}")
                
                # 模擬回覆內容
                if hasattr(event.message, '_reply_content'):
                    return event.message._reply_content
                
                self._log_warning(f"[REPLY] Cannot fetch replied message content")
                return None
            
            return None
            
        except Exception as e:
            self._log_error(f"Error extracting reply content: {e}")
            return None
    
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
            
            # 創建簡單的球員字典
            player = {
                "user_id": user_id,
                "name": display_name,
                "input_name": name
            }
            players.append(player)
        
        self._log_info(f"[PLAYERS] Created {len(players)} players for team generation")
        return players, mapping_info
    
    def _generate_simple_teams(self, players):
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
            return [3, 2]
        elif total_players == 6:
            return [3, 3]
        elif total_players == 7:
            return [3, 2, 2]
        elif total_players == 8:
            return [3, 3, 2]
        elif total_players == 9:
            return [3, 3, 3]
        elif total_players == 10:
            return [3, 3, 2, 2]
        elif total_players == 11:
            return [3, 3, 3, 2]
        elif total_players == 12:
            return [3, 3, 3, 3]
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
            
            return distribution
    
    def _create_custom_team_result_flex(self, teams, mapping_info):
        """模擬創建 Flex Message"""
        return "Mock Flex Message Object"
    
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
            
            # 使用智能分隊邏輯（自動決定隊伍數量）
            teams = self._generate_simple_teams(players)
            
            # 創建分隊結果 Flex Message
            result_flex = self._create_custom_team_result_flex(teams, mapping_info)
            
            self._send_flex_message(event.reply_token, "自定義分隊結果", result_flex)
            
        except Exception as e:
            self._log_error(f"Error in custom team command: {e}")
            self._send_message(event.reply_token, "❌ 分隊處理失敗，請稍後再試")

def test_team_command():
    """測試新的 /分隊 指令機制"""
    print("🤖 /分隊 指令機制測試")
    print("=" * 60)
    
    handler = MockLineMessageHandler()
    
    # 測試案例
    test_cases = [
        {
            "name": "直接指令 + 成員名單",
            "message": "/分隊 🥛、凱、豪、金、kin、勇",
            "has_reply": False
        },
        {
            "name": "無斜線指令 + 成員名單",
            "message": "分隊 奶、凱、豪",
            "has_reply": False
        },
        {
            "name": "僅指令無內容",
            "message": "/分隊",
            "has_reply": False
        },
        {
            "name": "回覆訊息 + 指令",
            "message": "/分隊",
            "has_reply": True,
            "reply_content": "今天打球：🥛、凱、豪、金、kin、勇、阿華"
        },
        {
            "name": "指令 + 無效內容",
            "message": "/分隊 只有我一個人沒有分隔符",
            "has_reply": False
        },
        {
            "name": "指令 + 單人（特殊情況）",
            "message": "/分隊 豪",
            "has_reply": False
        },
        {
            "name": "回覆無效內容",
            "message": "/分隊",
            "has_reply": True,
            "reply_content": "這裡沒有成員名單"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 測試案例 {i}: {test_case['name']}")
        print("-" * 50)
        print(f"💬 用戶輸入: '{test_case['message']}'")
        
        if test_case['has_reply']:
            print(f"↩️ 回覆內容: '{test_case.get('reply_content', '')}'")
        
        # 創建模擬事件
        event = MockEvent(
            test_case['message'], 
            has_reply=test_case['has_reply'],
            reply_content=test_case.get('reply_content')
        )
        
        # 處理指令
        handler._handle_custom_team_command(event, test_case['message'])
        print()

if __name__ == "__main__":
    test_team_command()