#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
互動式自定義分隊測試工具
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def interactive_test():
    """互動式測試自定義分隊功能"""
    try:
        print("🏀 互動式自定義分隊測試工具")
        print("=" * 50)
        
        # 初始化
        from src.database.mongodb import init_mongodb, get_database
        from src.handlers.line_handler import LineMessageHandler
        from src.models.mongodb_models import AliasMapRepository
        
        print("🔌 正在連接 MongoDB...")
        init_mongodb()
        db = get_database()
        print("✅ 連接成功！")
        
        handler = LineMessageHandler(None, None)
        alias_repo = AliasMapRepository(db)
        
        print(f"\n📚 可用的內部成員別名:")
        print("🥛/奶, 凱, 豪, 金/金毛, kin/Akin, 勇, 舊, 宇, 傑, 翔")
        print("華, 圈, 小明, 軍, 展, 盟, 小林, 諴, 榮, 細, 69, 張律")
        print(f"\n💡 新的指令格式:")
        print("- /分隊 🥛、凱、豪、金、kin、勇")
        print("- /分隊 🥛,凱,豪,金,kin,勇,阿華")
        print("- /分隊 奶、Akin、金毛、張律、路人甲")
        print("- 分隊 豪、凱  (可省略斜線)")
        
        while True:
            print(f"\n" + "="*50)
            user_input = input("📝 請輸入 /分隊 指令 (或輸入 'quit' 退出): ").strip()
            
            if user_input.lower() == 'quit':
                print("👋 再見！")
                break
                
            if not user_input:
                print("❌ 請輸入有效的訊息")
                continue
            
            print(f"\n🔍 處理訊息: {user_input}")
            print("-" * 40)
            
            # 檢查是否為 /分隊 指令
            is_team_command = user_input.startswith('/分隊') or user_input.startswith('分隊')
            print(f"指令識別: {'✅ 分隊指令' if is_team_command else '❌ 非分隊指令'}")
            
            if not is_team_command:
                print("💡 提示: 請以 '/分隊' 開頭，例如: /分隊 🥛、凱、豪")
                continue
            
            # 提取指令內容
            import re
            clean_command = re.sub(r'^/?分隊\s*', '', user_input).strip()
            print(f"📝 提取內容: '{clean_command}'")
            
            if not clean_command:
                print("❌ 無內容可處理，請提供成員名單")
                continue
            
            # 檢查是否為有效內容
            if not handler._is_valid_team_content(clean_command):
                print("❌ 無效的成員名單格式，請使用逗號、頓號分隔")
                continue
            
            # 解析成員名稱
            member_names = handler._parse_member_names(clean_command)
            print(f"解析成員: {member_names} (共 {len(member_names)} 位)")
            
            if len(member_names) < 1:
                print("❌ 請至少輸入1位成員")
                continue
            
            # 別名映射
            print(f"\n🔗 別名映射結果:")
            for name in member_names:
                mapped_id = alias_repo.find_user_by_alias(name)
                if mapped_id:
                    print(f"  ✅ '{name}' → '{mapped_id}'")
                else:
                    print(f"  👤 '{name}' → 將建立為路人")
            
            # 創建球員並分隊
            players, mapping_info = handler._create_players_from_names(member_names)
            
            if len(players) >= 1:
                teams = handler._generate_simple_teams(players)
                
                print(f"\n🏆 分隊結果:")
                for i, team in enumerate(teams, 1):
                    print(f"\n隊伍 {i} ({len(team)} 人):")
                    for j, player in enumerate(team, 1):
                        print(f"  {j}. {player['name']}")
                
                # 詳細結果
                print(f"\n📱 完整訊息預覽:")
                result_message = handler._create_custom_team_result_message(teams, mapping_info)
                print(result_message)
            else:
                print("❌ 無法創建足夠的球員")
                
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，再見！")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

def quick_test():
    """快速測試預定義案例"""
    try:
        print("⚡ 快速測試模式")
        print("=" * 30)
        
        from src.database.mongodb import init_mongodb, get_database
        from src.handlers.line_handler import LineMessageHandler
        
        init_mongodb()
        handler = LineMessageHandler(None, None)
        
        # 預定義測試案例（使用新的 /分隊 格式）
        test_cases = [
            "/分隊 日：沒復發就全力🥛、凱、豪、金、kin、勇",
            "/分隊 🥛,凱,豪,金,kin,勇,阿華,小李",
            "/分隊 奶、Akin、金毛、張律、路人甲、路人乙",
            "/分隊 豪、凱",  # 測試小隊情況
            "/分隊",  # 測試無內容
        ]
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n測試 {i}: {test}")
            print("-" * 30)
            
            # 檢查是否為 /分隊 指令
            is_team_command = test.startswith('/分隊') or test.startswith('分隊')
            if is_team_command:
                import re
                clean_command = re.sub(r'^/?分隊\s*', '', test).strip()
                
                if not clean_command:
                    print("❌ 無內容可處理")
                    continue
                
                if not handler._is_valid_team_content(clean_command):
                    print("❌ 無效的成員名單格式")
                    continue
                
                member_names = handler._parse_member_names(clean_command)
                players, mapping_info = handler._create_players_from_names(member_names)
                
                if len(players) >= 1:
                    teams = handler._generate_simple_teams(players)
                    
                    for j, team in enumerate(teams, 1):
                        print(f"隊伍 {j}: {[p['name'] for p in team]}")
                else:
                    print("無球員可分隊")
            else:
                print("未識別為分隊指令")
                
    except Exception as e:
        print(f"快速測試失敗: {e}")

if __name__ == "__main__":
    # 選擇測試模式
    print("選擇測試模式:")
    print("1. 互動式測試 (推薦)")
    print("2. 快速測試")
    
    try:
        choice = input("請選擇 (1 或 2): ").strip()
        if choice == "2":
            quick_test()
        else:
            interactive_test()
    except:
        interactive_test()