#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完整測試自定義分隊功能 - 包含別名映射和隨機分隊
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_full_custom_team():
    """完整測試自定義分隊功能"""
    try:
        print("🏀 完整自定義分隊功能測試")
        print("=" * 60)
        
        # 初始化 MongoDB 和相關組件
        from src.database.mongodb import init_mongodb, get_database
        from src.handlers.line_handler import LineMessageHandler
        from src.models.mongodb_models import AliasMapRepository
        
        print("🔌 初始化 MongoDB 連接...")
        init_mongodb()
        db = get_database()
        
        print("✅ MongoDB 連接成功")
        
        # 創建處理器實例
        handler = LineMessageHandler(None, None)
        alias_repo = AliasMapRepository(db)
        
        # 測試範例字串們
        test_cases = [
            "日：沒復發就全力🥛、凱、豪、金、kin、勇",
            "🥛,凱,豪,金,kin,勇,阿華,小李",
            "奶、Akin、金毛、張律、路人甲、路人乙",
            "69,小明,細,榮,未知1,未知2,未知3"
        ]
        
        for i, test_message in enumerate(test_cases, 1):
            print(f"\n🧪 測試案例 {i}: {test_message}")
            print("-" * 50)
            
            # 1. 檢測是否為自定義分隊訊息
            is_custom = handler._is_custom_team_message(test_message)
            print(f"🔍 識別結果: {is_custom}")
            
            if not is_custom:
                print("❌ 未識別為自定義分隊訊息")
                continue
            
            # 2. 解析成員名稱
            member_names = handler._parse_member_names(test_message)
            print(f"📝 解析成員: {member_names}")
            print(f"📊 成員數量: {len(member_names)}")
            
            # 3. 別名映射測試
            print(f"\n🔗 別名映射測試:")
            for name in member_names:
                mapped_id = alias_repo.find_user_by_alias(name)
                if mapped_id:
                    print(f"  ✅ '{name}' → '{mapped_id}' (已識別)")
                else:
                    print(f"  ❓ '{name}' → 未找到，將建立為路人")
            
            # 4. 創建球員列表
            print(f"\n👥 創建球員列表:")
            players, mapping_info = handler._create_players_from_names(member_names)
            print(f"  總球員數: {len(players)}")
            print(f"  已識別: {len(mapping_info['identified'])} 位")
            print(f"  路人: {len(mapping_info['strangers'])} 位")
            
            print(f"\n📋 詳細映射:")
            for item in mapping_info['identified']:
                print(f"  ✅ {item['input']} → {item['mapped']}")
            for item in mapping_info['strangers']:
                print(f"  👤 {item['input']} → {item['stranger']}")
            
            # 5. 進行分隊
            if len(players) >= 2:
                print(f"\n⚽ 進行分隊:")
                teams = handler._generate_simple_teams(players, num_teams=2)
                
                print(f"  生成隊伍數: {len(teams)}")
                for j, team in enumerate(teams, 1):
                    print(f"\n  🏆 隊伍 {j} ({len(team)} 人):")
                    for k, player in enumerate(team, 1):
                        print(f"    {k}. {player['name']}")
                
                # 6. 生成完整結果訊息
                print(f"\n📱 完整結果訊息:")
                result_message = handler._create_custom_team_result_message(teams, mapping_info)
                print(result_message)
            else:
                print("❌ 球員數量不足，無法分隊")
        
        print("\n🎉 所有測試完成！")
        
        # 額外測試：顯示當前所有別名
        print(f"\n📚 當前系統中的所有別名:")
        all_aliases = alias_repo.get_all_aliases()
        if all_aliases:
            for alias_doc in all_aliases[:10]:  # 只顯示前10個
                user_id = alias_doc.get('userId')
                aliases = alias_doc.get('aliases', {})
                if isinstance(aliases, dict):
                    exact = aliases.get('exact', [])
                    patterns = aliases.get('patterns', [])
                    print(f"  👤 {user_id}: 精確={exact}, 模式={patterns}")
                else:
                    print(f"  👤 {user_id}: {aliases}")
        else:
            print("  ❓ 沒有找到別名記錄")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

def test_alias_patterns():
    """測試別名模式匹配"""
    try:
        print(f"\n🎯 別名模式匹配專項測試")
        print("-" * 40)
        
        from src.database.mongodb import get_database
        from src.models.mongodb_models import AliasMapRepository
        
        db = get_database()
        alias_repo = AliasMapRepository(db)
        
        # 測試各種別名變化
        test_aliases = [
            "🥛", "奶", "123奶", "奶456", "大奶王",  # 奶的變化
            "凱", "123凱", "凱哥", "小凱",           # 凱的變化
            "金", "金毛", "123金", "金456",         # 金毛的變化
            "kin", "Akin", "123Akin", "Akin哥",   # Akin的變化
            "勇", "123勇", "勇士", "大勇",          # 勇的變化
            "69", "a69b", "69號",                  # 69的變化
            "不存在", "未知用戶", "abc123"          # 不存在的
        ]
        
        print("測試別名匹配:")
        for alias in test_aliases:
            result = alias_repo.find_user_by_alias(alias)
            if result:
                print(f"  ✅ '{alias}' → '{result}'")
            else:
                print(f"  ❌ '{alias}' → 無匹配")
                
    except Exception as e:
        print(f"❌ 別名測試失敗: {e}")

if __name__ == "__main__":
    test_full_custom_team()
    test_alias_patterns()