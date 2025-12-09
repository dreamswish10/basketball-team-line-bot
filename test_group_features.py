#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
群組功能測試腳本
測試群組成員管理和分隊功能
"""

import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_models():
    """測試資料庫模型"""
    print("🧪 測試資料庫模型...")
    
    try:
        from models import init_db, Player, Group, GroupMember, PlayerDatabase, GroupDatabase
        
        # 初始化資料庫
        init_db()
        print("✅ 資料庫初始化成功")
        
        # 測試群組創建
        test_group = Group("test_group_123", "測試群組")
        if GroupDatabase.create_group(test_group):
            print("✅ 群組創建成功")
        
        # 測試群組成員添加
        test_member = GroupMember("test_group_123", "user123", "測試成員")
        if GroupDatabase.add_group_member(test_member):
            print("✅ 群組成員添加成功")
        
        # 測試球員創建（群組來源）
        test_player = Player("user123", "測試球員", 6, 7, 8, 
                           source_group="test_group_123", is_registered=False)
        if PlayerDatabase.create_player(test_player):
            print("✅ 群組球員創建成功")
        
        # 測試群組球員查詢
        group_players = PlayerDatabase.get_group_players("test_group_123")
        print(f"✅ 查詢到 {len(group_players)} 位群組球員")
        
        return True
        
    except ImportError as e:
        print(f"❌ 導入錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 資料庫測試失敗: {e}")
        return False

def test_group_manager():
    """測試群組管理器"""
    print("\n🧪 測試群組管理器...")
    
    try:
        from group_manager import GroupManager, suggest_group_team_sizes
        
        # 測試分隊建議
        suggestions = suggest_group_team_sizes(8)
        print(f"✅ 8人群組分隊建議: {len(suggestions)} 個方案")
        for num_teams, description in suggestions:
            print(f"   • {description}")
        
        # 模擬群組管理器（無實際 LINE API）
        class MockLineBotApi:
            def get_group_member_ids(self, group_id):
                return ["user1", "user2", "user3", "user4", "user5", "user6"]
            
            def get_group_member_profile(self, group_id, user_id):
                class MockProfile:
                    def __init__(self, user_id):
                        self.display_name = f"測試用戶_{user_id[-1]}"
                return MockProfile(user_id)
        
        manager = GroupManager(MockLineBotApi())
        
        # 測試群組成員創建
        players = manager.create_group_players("test_group_123")
        print(f"✅ 創建 {len(players)} 位群組球員")
        
        return True
        
    except ImportError as e:
        print(f"❌ 導入錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 群組管理器測試失敗: {e}")
        return False

def test_team_algorithm():
    """測試分隊算法與群組球員"""
    print("\n🧪 測試分隊算法...")
    
    try:
        from models import Player
        from team_algorithm import TeamGenerator
        
        # 創建混合球員清單（註冊+群組成員）
        players = [
            Player("user1", "Kobe Bryant", 10, 8, 7, is_registered=True),      # 註冊球員
            Player("user2", "LeBron James", 9, 9, 9, is_registered=True),     # 註冊球員
            Player("user3", "群組成員A", 5, 5, 5, source_group="test_group", is_registered=False),  # 群組成員
            Player("user4", "群組成員B", 5, 5, 5, source_group="test_group", is_registered=False),  # 群組成員
            Player("user5", "群組成員C", 5, 5, 5, source_group="test_group", is_registered=False),  # 群組成員
            Player("user6", "群組成員D", 5, 5, 5, source_group="test_group", is_registered=False),  # 群組成員
        ]
        
        generator = TeamGenerator()
        
        # 測試 2 隊分隊
        teams = generator.generate_teams(players, 2)
        print(f"✅ 成功分成 {len(teams)} 隊")
        
        # 顯示分隊結果
        for i, team in enumerate(teams, 1):
            print(f"   第 {i} 隊:")
            for player in team:
                status = "已註冊" if player.is_registered else "群組成員"
                print(f"     • {player.name} ({status}, 評分:{player.overall_rating:.1f})")
        
        # 測試隊伍統計
        stats = generator.get_team_stats(teams)
        for i, stat in enumerate(stats, 1):
            print(f"   第 {i} 隊統計: 平均評分 {stat['avg_rating']:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 分隊算法測試失敗: {e}")
        return False

def test_line_handler_integration():
    """測試 LINE Handler 整合"""
    print("\n🧪 測試 LINE Handler 整合...")
    
    try:
        from line_handler import LineMessageHandler
        
        # 模擬 LINE Bot API
        class MockLineBotApi:
            def reply_message(self, token, message):
                print(f"   📤 模擬回覆: {type(message).__name__}")
        
        handler = LineMessageHandler(MockLineBotApi())
        
        # 測試 spacer 創建
        spacer = handler._create_spacer("md")
        print(f"✅ Spacer 創建成功: {type(spacer).__name__}")
        
        # 測試群組 Flex Message 創建
        from models import Player
        test_players = [
            Player("user1", "測試球員1", 8, 7, 6, is_registered=True),
            Player("user2", "測試球員2", 5, 5, 5, source_group="test", is_registered=False),
        ]
        
        group_list_flex = handler._create_group_player_list_flex(test_players, "test_group")
        print(f"✅ 群組成員列表 Flex Message 創建成功")
        
        # 測試 JSON 轉換
        json_dict = group_list_flex.as_json_dict()
        print(f"✅ JSON 序列化成功，包含 {len(str(json_dict))} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ LINE Handler 測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 群組功能測試開始\n")
    
    test_results = []
    
    # 執行所有測試
    test_results.append(("資料庫模型", test_database_models()))
    test_results.append(("群組管理器", test_group_manager()))
    test_results.append(("分隊算法", test_team_algorithm()))
    test_results.append(("LINE Handler", test_line_handler_integration()))
    
    # 顯示測試結果
    print("\n" + "="*50)
    print("📋 測試結果總結:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    
    if all_passed:
        print("🎉 所有測試通過！群組功能已準備就緒")
        print("\n📝 下一步:")
        print("1. 設定 LINE Developers Console 權限")
        print("2. 部署到 Render")
        print("3. 將機器人加入測試群組")
        print("4. 測試群組分隊功能")
    else:
        print("❌ 有測試失敗，請檢查錯誤訊息")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)