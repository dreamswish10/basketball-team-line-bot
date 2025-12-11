#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試新的分隊邏輯 - 不依賴 MongoDB
"""

import random

def calculate_optimal_team_distribution(total_players):
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

def generate_simple_teams(players, num_teams=2):
    """智能分隊方法：考慮人數限制和隊伍大小"""
    total_players = len(players)
    
    # 人數小於等於4時不分隊
    if total_players <= 4:
        print(f"[TEAMS] {total_players} players <= 4, keeping all in one team")
        return [players]
    
    # 計算最佳隊伍數量和分配方式
    optimal_teams = calculate_optimal_team_distribution(total_players)
    
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
    
    print(f"[TEAMS] Generated {len(teams)} teams with sizes {[len(team) for team in teams]} from {total_players} players")
    return teams

def test_team_distribution():
    """測試各種人數的分隊邏輯"""
    print("🏀 分隊邏輯測試")
    print("=" * 50)
    
    # 測試各種人數情況
    test_cases = [
        (2, "2人：不分隊"),
        (3, "3人：不分隊"),
        (4, "4人：不分隊"),
        (5, "5人：應該分成 [3,2]"),
        (6, "6人：應該分成 [3,3]"),
        (7, "7人：應該分成 [3,2,2]"),
        (8, "8人：應該分成 [3,3,2]"),
        (9, "9人：應該分成 [3,3,3]"),
        (10, "10人：應該分成 [3,3,2,2]"),
        (11, "11人：應該分成 [3,3,3,2]"),
        (12, "12人：應該分成 [3,3,3,3]"),
        (13, "13人：應該分成 [3,3,3,2,2]"),
        (15, "15人：應該分成 [3,3,3,3,3]"),
    ]
    
    for total_players, description in test_cases:
        print(f"\n📊 測試 {description}")
        
        # 創建模擬玩家
        players = [{"name": f"玩家{i+1}", "user_id": f"user_{i+1}"} for i in range(total_players)]
        
        # 計算分配
        distribution = calculate_optimal_team_distribution(total_players)
        print(f"   計算分配：{distribution}")
        
        # 實際分隊
        teams = generate_simple_teams(players)
        actual_sizes = [len(team) for team in teams]
        print(f"   實際結果：{actual_sizes}")
        
        # 驗證結果
        if actual_sizes == distribution:
            print("   ✅ 測試通過")
        else:
            print(f"   ❌ 測試失敗：期望 {distribution}，實際 {actual_sizes}")

def test_specific_cases():
    """測試特定案例"""
    print(f"\n🎯 特定案例測試")
    print("-" * 30)
    
    # 測試7人分隊（用戶特別要求的案例）
    players_7 = [{"name": f"成員{i+1}", "user_id": f"user_{i+1}"} for i in range(7)]
    print(f"\n📝 7人分隊測試：")
    for i in range(3):  # 測試3次確保隨機性
        teams = generate_simple_teams(players_7)
        sizes = [len(team) for team in teams]
        print(f"   第{i+1}次：{sizes} - {'✅' if sizes == [3,2,2] else '❌'}")
        
        # 顯示詳細分隊結果
        for j, team in enumerate(teams, 1):
            names = [p['name'] for p in team]
            print(f"     隊伍{j}：{names}")
        print()

if __name__ == "__main__":
    test_team_distribution()
    test_specific_cases()