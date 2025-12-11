#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 LINE Bot 自定義分隊完整流程
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

# 模擬 LineMessageHandler 的核心方法
class MockLineMessageHandler:
    def __init__(self):
        self.alias_repo = MockAliasMapRepository()
    
    def _log_info(self, message):
        print(f"[INFO] {message}")
    
    def _is_custom_team_message(self, message_text):
        """檢查是否為自定義分隊訊息"""
        import re
        
        # 檢查是否包含多個成員名稱（以分隔符分隔）
        # 支援的分隔符：、，,
        separators = r'[、，,]'
        
        # 移除可能的前綴（如 "日："）
        clean_text = re.sub(r'^[^：:]*[：:]', '', message_text).strip()
        
        # 檢查是否包含分隔符且有多個元素
        if re.search(separators, clean_text):
            parts = re.split(separators, clean_text)
            # 過濾掉空字符串和長度小於1的元素
            valid_parts = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 1]
            
            # 至少需要2個有效成員名稱
            if len(valid_parts) >= 2:
                self._log_info(f"[CUSTOM_TEAM] Detected custom team message with {len(valid_parts)} members")
                return True
        
        return False
    
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
    
    def handle_custom_team_message(self, message_text, use_flex=False):
        """模擬處理自定義分隊訊息的完整流程"""
        print(f"🤖 收到訊息: '{message_text}'\n")
        
        # 1. 檢查是否為自定義分隊訊息
        is_custom = self._is_custom_team_message(message_text)
        if not is_custom:
            return "❌ 這不是有效的自定義分隊訊息"
        
        # 2. 解析成員名稱
        member_names = self._parse_member_names(message_text)
        if len(member_names) < 1:
            return "❌ 請至少輸入 1 位成員名稱"
        
        # 3. 通過別名映射創建球員列表
        players, mapping_info = self._create_players_from_names(member_names)
        if len(players) < 1:
            return "❌ 無法創建球員列表"
        
        # 4. 使用智能分隊邏輯
        teams = self._generate_simple_teams(players)
        
        # 5. 創建分隊結果
        if use_flex:
            # 模擬 Flex UI 結構
            return self._create_flex_structure_summary(teams, mapping_info)
        else:
            # 文字版本
            result_message = self._create_custom_team_result_message(teams, mapping_info)
            return result_message
    
    def _create_flex_structure_summary(self, teams, mapping_info):
        """創建 Flex UI 結構摘要（模擬）"""
        total_players = sum(len(team) for team in teams)
        
        summary = "📱 Flex UI 結構預覽:\n\n"
        summary += "🎨 Header: '🏀 自定義分隊結果' (橙色主題)\n\n"
        
        # 成員映射區塊
        if mapping_info['identified'] or mapping_info['strangers']:
            summary += "📋 成員映射區塊:\n"
            if mapping_info['identified']:
                summary += f"  ✅ 已識別成員: {len(mapping_info['identified'])} 位\n"
                for item in mapping_info['identified'][:3]:  # 只顯示前3個
                    summary += f"    • {item['input']} → {item['mapped']}\n"
                if len(mapping_info['identified']) > 3:
                    summary += f"    ... 還有 {len(mapping_info['identified']) - 3} 位\n"
            
            if mapping_info['strangers']:
                summary += f"  👤 新增路人: {len(mapping_info['strangers'])} 位\n"
                for item in mapping_info['strangers'][:3]:  # 只顯示前3個
                    summary += f"    • {item['input']} → {item['stranger']}\n"
                if len(mapping_info['strangers']) > 3:
                    summary += f"    ... 還有 {len(mapping_info['strangers']) - 3} 位\n"
            summary += "\n"
        
        # 分隊說明區塊
        summary += "ℹ️ 分隊說明區塊: (藍色背景卡片)\n"
        if total_players <= 4:
            summary += f"  • 總人數 {total_players} 人 ≤ 4 人，不進行分隊\n"
        else:
            summary += f"  • 總人數 {total_players} 人，採用智能分隊\n"
            summary += "  • 每隊最多 3 人，確保比賽平衡\n"
        summary += "\n"
        
        # 分隊結果區塊
        summary += "🏆 分隊結果區塊:\n"
        team_colors = ["藍色", "綠色", "紅色", "紫色", "橙色", "青色"]
        
        if len(teams) == 1:
            summary += f"  📋 全體成員卡片 (橙色背景)\n"
            summary += f"    {len(teams[0])} 人: {[p['name'] for p in teams[0]]}\n"
        else:
            for i, team in enumerate(teams):
                color = team_colors[i % len(team_colors)]
                summary += f"  🎨 隊伍 {i+1} 卡片 ({color}背景)\n"
                summary += f"    {len(team)} 人: {[p['name'] for p in team]}\n"
        
        summary += "\n🎛️ 互動按鈕:\n"
        summary += "  🔄 重新分隊 (主要按鈕)\n"
        summary += "  ❓ 分隊說明 (連結按鈕)\n"
        
        return summary

def test_line_bot_integration():
    """測試 LINE Bot 完整流程"""
    print("🤖 LINE Bot 自定義分隊整合測試")
    print("=" * 60)
    
    handler = MockLineMessageHandler()
    
    # 測試案例
    test_cases = [
        "日：沒復發就全力🥛、凱、豪",  # 用戶要求的案例 (3人)
        "🥛,凱,豪,金,kin,勇,阿華",        # 7人案例
        "奶、Akin、金毛、張律、路人甲、路人乙、小明、小華、小李、小王",  # 10人案例
        "小組：金毛、豪",               # 2人案例
        "只有我一個人",                 # 非分隊訊息
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n🧪 測試案例 {i}: {message}")
        print("-" * 50)
        
        # 文字版本
        print("📝 文字版本回應:")
        result = handler.handle_custom_team_message(message, use_flex=False)
        print(result)
        print()
        
        # Flex UI 版本  
        if "❌" not in result:  # 只有在成功的案例才顯示 Flex UI
            print("📱 Flex UI 版本回應:")
            flex_result = handler.handle_custom_team_message(message, use_flex=True)
            print(flex_result)
        print()

if __name__ == "__main__":
    test_line_bot_integration()