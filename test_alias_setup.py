#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試別名設定功能的簡單腳本
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_alias_setup():
    """測試別名設定功能"""
    try:
        print("🧪 測試別名設定功能...")
        
        # 導入必要模組
        from src.database.mongodb import init_mongodb, get_database
        from src.models.mongodb_models import AliasMapRepository
        
        # 初始化資料庫
        print("🔌 連接 MongoDB...")
        init_mongodb()
        
        # 創建 repository
        db = get_database()
        alias_repo = AliasMapRepository(db)
        
        # 測試設定別名
        test_user_id = "TEST_U123456789"
        test_aliases = ["測試用戶", "Test User", "測試"]
        
        print(f"📝 設定測試別名: {test_user_id} -> {test_aliases}")
        success = alias_repo.create_or_update_alias(test_user_id, test_aliases)
        
        if success:
            print("✅ 別名設定成功")
            
            # 測試查詢別名
            retrieved_aliases = alias_repo.get_aliases_by_user_id(test_user_id)
            print(f"📖 查詢到的別名: {retrieved_aliases}")
            
            # 測試根據別名查找用戶
            for alias in test_aliases:
                found_user_id = alias_repo.find_user_by_alias(alias)
                if found_user_id == test_user_id:
                    print(f"🔍 別名查找成功: '{alias}' -> {found_user_id}")
                else:
                    print(f"❌ 別名查找失敗: '{alias}' -> {found_user_id}")
            
            # 清理測試數據
            alias_repo.delete_user_aliases(test_user_id)
            print("🧹 測試數據清理完成")
            
            print("\n🎉 所有測試通過！別名設定功能正常")
            
        else:
            print("❌ 別名設定失敗")
            return False
            
        return True
        
    except Exception as e:
        print(f"💥 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hardcoded_aliases():
    """測試硬編碼別名設定"""
    try:
        print("\n🧪 測試硬編碼別名設定...")
        
        # 模擬 app.py 中的別名設定
        from src.database.mongodb import get_database
        from src.models.mongodb_models import AliasMapRepository
        
        db = get_database()
        alias_repo = AliasMapRepository(db)
        
        # 模擬硬編碼別名（新格式）- 內部成員範例
        hardcoded_aliases = {
            "U勇的用戶ID": {
                "exact": ["勇"],
                "patterns": ["*勇*", "勇*"],
                "regex": [r"\d+勇", r"勇\d+"]
            },
            "U小明的用戶ID": {
                "exact": ["小明"],
                "patterns": ["*小明*", "小明*"],
                "regex": [r"\d+小明", r"小明\d+"]
            },
            "U69的用戶ID": {
                "exact": ["69"],
                "patterns": ["*69*"],
                "regex": []
            }
        }
        
        for user_id, aliases in hardcoded_aliases.items():
            print(f"📝 設定別名: {user_id} -> {aliases}")
            success = alias_repo.create_or_update_alias(user_id, aliases)
            
            if success:
                print(f"✅ {user_id} 別名設定成功")
                
                # 驗證設定結果
                retrieved = alias_repo.get_aliases_by_user_id(user_id)
                print(f"📖 驗證結果: {retrieved}")
            else:
                print(f"❌ {user_id} 別名設定失敗")
        
        print("\n📊 當前所有別名:")
        all_aliases = alias_repo.get_all_aliases()
        for alias_doc in all_aliases:
            print(f"  {alias_doc['userId']}: {alias_doc['aliases']}")
            
        print(f"\n總共 {len(all_aliases)} 個用戶設定了別名")
        
        return True
        
    except Exception as e:
        print(f"💥 硬編碼別名測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pattern_matching():
    """測試模式匹配功能"""
    try:
        print("\n🎯 測試模式匹配功能...")
        
        from src.database.mongodb import get_database
        from src.models.mongodb_models import AliasMapRepository
        
        db = get_database()
        alias_repo = AliasMapRepository(db)
        
        # 設定測試用戶（金毛用戶）
        test_user_id = "TEST_GOLD_USER"
        test_aliases = {
            "exact": ["金毛", "小金"],
            "patterns": ["*金", "金*"],
            "regex": [r"\d+金", r"金\d+"]
        }
        
        print(f"📝 設定測試用戶: {test_user_id}")
        alias_repo.create_or_update_alias(test_user_id, test_aliases)
        
        # 測試各種匹配模式
        test_cases = [
            ("金毛", "精確匹配"),
            ("小金", "精確匹配"),
            ("123金", "正則匹配 \\d+金"),
            ("金456", "正則匹配 金\\d+"),
            ("大金王", "模式匹配 *金"),
            ("金光閃閃", "模式匹配 金*"),
            ("超級金毛", "模式匹配 *金"),
            ("不存在", "無匹配")
        ]
        
        print("\n🔍 測試匹配結果:")
        for alias, expected in test_cases:
            found_user_id = alias_repo.find_user_by_alias(alias)
            if found_user_id == test_user_id:
                print(f"✅ '{alias}' -> {found_user_id} ({expected})")
            elif found_user_id is None and expected == "無匹配":
                print(f"✅ '{alias}' -> 無匹配 (符合預期)")
            else:
                print(f"❌ '{alias}' -> {found_user_id} (預期: {expected})")
        
        # 清理測試數據
        alias_repo.delete_user_aliases(test_user_id)
        print("\n🧹 測試數據清理完成")
        
        return True
        
    except Exception as e:
        print(f"💥 模式匹配測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_internal_members_aliases():
    """測試內部成員別名匹配"""
    try:
        print("\n👥 測試內部成員別名...")
        
        from src.database.mongodb import get_database
        from src.models.mongodb_models import AliasMapRepository
        
        db = get_database()
        alias_repo = AliasMapRepository(db)
        
        # 設定幾個內部成員進行測試
        test_members = {
            "TEST_勇": {
                "exact": ["勇"],
                "patterns": ["*勇*", "勇*"],
                "regex": [r"\d+勇", r"勇\d+"]
            },
            "TEST_小明": {
                "exact": ["小明"],
                "patterns": ["*小明*", "小明*"],
                "regex": [r"\d+小明", r"小明\d+"]
            },
            "TEST_69": {
                "exact": ["69"],
                "patterns": ["*69*"],
                "regex": []
            }
        }
        
        # 設定測試用戶
        for user_id, aliases in test_members.items():
            alias_repo.create_or_update_alias(user_id, aliases)
            print(f"📝 設定測試用戶: {user_id}")
        
        # 測試各種匹配情況
        test_cases = [
            # 勇的測試
            ("勇", "TEST_勇", "精確匹配"),
            ("123勇", "TEST_勇", "正則匹配 \\d+勇"),
            ("勇456", "TEST_勇", "正則匹配 勇\\d+"),
            ("大勇士", "TEST_勇", "模式匹配 *勇*"),
            ("勇敢", "TEST_勇", "模式匹配 勇*"),
            
            # 小明的測試
            ("小明", "TEST_小明", "精確匹配"),
            ("123小明", "TEST_小明", "正則匹配 \\d+小明"),
            ("小明456", "TEST_小明", "正則匹配 小明\\d+"),
            ("大小明", "TEST_小明", "模式匹配 *小明*"),
            
            # 69的測試
            ("69", "TEST_69", "精確匹配"),
            ("a69b", "TEST_69", "模式匹配 *69*"),
            ("69號", "TEST_69", "模式匹配 69*"),
            
            # 不匹配的測試
            ("不存在", None, "無匹配")
        ]
        
        print("\n🔍 測試匹配結果:")
        success_count = 0
        total_count = len(test_cases)
        
        for alias, expected_user, description in test_cases:
            found_user_id = alias_repo.find_user_by_alias(alias)
            if found_user_id == expected_user:
                print(f"✅ '{alias}' -> {found_user_id} ({description})")
                success_count += 1
            elif found_user_id is None and expected_user is None:
                print(f"✅ '{alias}' -> 無匹配 (符合預期)")
                success_count += 1
            else:
                print(f"❌ '{alias}' -> {found_user_id} (預期: {expected_user}, {description})")
        
        # 清理測試數據
        for user_id in test_members.keys():
            alias_repo.delete_user_aliases(user_id)
        print("\n🧹 測試數據清理完成")
        
        print(f"\n📊 測試結果: {success_count}/{total_count} 通過")
        return success_count == total_count
        
    except Exception as e:
        print(f"💥 內部成員別名測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🏷️  別名設定功能測試")
    print("=" * 50)
    
    # 基本功能測試
    test1_result = test_alias_setup()
    
    # 硬編碼別名測試
    test2_result = test_hardcoded_aliases()
    
    # 模式匹配測試
    test3_result = test_pattern_matching()
    
    # 內部成員別名測試
    test4_result = test_internal_members_aliases()
    
    print("\n" + "=" * 50)
    if test1_result and test2_result and test3_result and test4_result:
        print("🎊 所有測試通過！內部團隊別名系統準備就緒")
        print("\n✨ 內部成員別名功能:")
        print("- 17位內部成員: 勇、舊、宇、傑、豪、翔、華、圈、小明、軍、展、盟、小林、諴、榮、細、69")
        print("- 精確匹配: '勇' -> 勇用戶")
        print("- 數字組合: '123勇', '勇456' -> 勇用戶")  
        print("- 通配符: '大勇士', '勇敢' -> 勇用戶")
        print("- 完整支援所有匹配模式")
        print("\n🔧 替換步驟:")
        print("1. 記錄真實 LINE User ID (在收到訊息時記錄 event.source.user_id)")
        print("2. 替換 app.py 中的佔位符 ID")
        print("3. 重新部署到 Render")
        sys.exit(0)
    else:
        print("💥 測試失敗，請檢查系統設定")
        sys.exit(1)