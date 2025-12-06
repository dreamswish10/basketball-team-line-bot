#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
籃球分隊系統測試腳本
運行此腳本來測試系統的基本功能
"""

import os
import sys
from models import init_db, Player, PlayerDatabase
from team_algorithm import TeamGenerator

def test_database():
    """測試資料庫功能"""
    print("=== 測試資料庫功能 ===")
    
    # 初始化資料庫
    init_db()
    print("✓ 資料庫初始化成功")
    
    # 測試創建球員
    test_players = [
        Player("test1", "Kobe Bryant", 10, 8, 7),
        Player("test2", "LeBron James", 9, 9, 9),
        Player("test3", "Stephen Curry", 10, 6, 8),
        Player("test4", "Kevin Durant", 10, 7, 8),
    ]
    
    for player in test_players:
        if PlayerDatabase.create_player(player):
            print(f"✓ 創建球員成功: {player.name}")
        else:
            print(f"✗ 創建球員失敗: {player.name}")
    
    # 測試查詢功能
    all_players = PlayerDatabase.get_all_players()
    print(f"✓ 查詢到 {len(all_players)} 位球員")
    
    # 測試個別查詢
    player = PlayerDatabase.get_player("test1")
    if player:
        print(f"✓ 個別查詢成功: {player}")
    else:
        print("✗ 個別查詢失敗")
    
    return all_players

def test_team_algorithm(players):
    """測試分隊演算法"""
    print("\n=== 測試分隊演算法 ===")
    
    generator = TeamGenerator()
    
    # 測試 2 隊分組
    try:
        teams = generator.generate_teams(players, 2)
        print("✓ 2 隊分組成功")
        print("\n分隊結果:")
        print(generator.format_teams_message(teams))
        
        # 測試統計資料
        stats = generator.get_team_stats(teams)
        print(f"✓ 統計資料計算成功，共 {len(stats)} 隊")
        
    except Exception as e:
        print(f"✗ 分隊演算法錯誤: {e}")
        return False
    
    return True

def test_suggestions():
    """測試分隊建議"""
    print("\n=== 測試分隊建議 ===")
    
    generator = TeamGenerator()
    
    for player_count in [4, 6, 8, 10, 12]:
        suggestions = generator.suggest_optimal_teams(player_count)
        print(f"{player_count} 位球員的建議:")
        for num_teams, desc in suggestions:
            print(f"  - {desc}")

def cleanup_test_data():
    """清理測試資料"""
    print("\n=== 清理測試資料 ===")
    
    test_users = ["test1", "test2", "test3", "test4"]
    for user_id in test_users:
        if PlayerDatabase.delete_player(user_id):
            print(f"✓ 刪除測試球員: {user_id}")

def main():
    """主測試函數"""
    print("🏀 籃球分隊系統測試開始\n")
    
    try:
        # 測試資料庫
        players = test_database()
        
        if len(players) >= 2:
            # 測試分隊演算法
            test_team_algorithm(players)
        else:
            print("⚠️ 球員數量不足，跳過分隊測試")
        
        # 測試建議功能
        test_suggestions()
        
    except Exception as e:
        print(f"✗ 測試過程中發生錯誤: {e}")
        return False
    
    finally:
        # 清理測試資料
        cleanup_test_data()
    
    print("\n🎉 所有測試完成！")
    return True

def check_environment():
    """檢查環境設定"""
    print("=== 檢查環境設定 ===")
    
    required_files = [
        'app.py',
        'models.py',
        'team_algorithm.py',
        'line_handler.py',
        'config.py',
        'requirements.txt'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} 存在")
        else:
            print(f"✗ {file} 遺失")
            return False
    
    # 檢查 Python 版本
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python 版本: {version.major}.{version.minor}")
    else:
        print(f"⚠️ Python 版本可能過舊: {version.major}.{version.minor}")
    
    return True

if __name__ == "__main__":
    print("🔍 檢查系統環境...")
    if not check_environment():
        print("❌ 環境檢查失敗，請確認所有檔案都存在")
        sys.exit(1)
    
    print("\n🧪 開始功能測試...")
    success = main()
    
    if success:
        print("✅ 系統測試通過！可以開始使用 LINE Bot")
    else:
        print("❌ 系統測試失敗，請檢查錯誤訊息")
        sys.exit(1)