#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試修復 null elements 問題
"""

import json
import sys

def test_line_handler_spacer_fix():
    """測試 LineMessageHandler 的間距修復"""
    print("🧪 測試 LineMessageHandler 間距修復")
    
    try:
        # 模擬沒有 SpacerComponent 的環境
        import line_handler
        
        # 創建一個模擬的 line_bot_api
        class MockLineBotApi:
            pass
        
        # 創建 handler
        handler = line_handler.LineMessageHandler(MockLineBotApi())
        
        # 測試 _create_spacer 方法
        print("\n📋 測試 _create_spacer 方法:")
        
        test_cases = [
            {"size": "sm", "margin": None},
            {"size": "md", "margin": "sm"}, 
            {"size": "lg", "margin": "md"},
        ]
        
        all_passed = True
        for i, case in enumerate(test_cases, 1):
            try:
                spacer = handler._create_spacer(size=case["size"], margin=case["margin"])
                
                # 檢查是否是有效的組件
                has_as_json_dict = hasattr(spacer, 'as_json_dict')
                
                if has_as_json_dict:
                    json_dict = spacer.as_json_dict()
                    json_str = json.dumps(json_dict, ensure_ascii=False, indent=2)
                    has_null = "null" in json_str
                    
                    print(f"  {i}. size='{case['size']}', margin={case['margin']}")
                    print(f"     類型: {type(spacer).__name__}")
                    print(f"     JSON: {json_str}")
                    print(f"     結果: {'❌ 包含 null' if has_null else '✅ 正常'}")
                    
                    if has_null:
                        all_passed = False
                else:
                    print(f"  {i}. size='{case['size']}', margin={case['margin']}")
                    print(f"     類型: {type(spacer).__name__}")
                    print(f"     結果: ❌ 無法序列化")
                    all_passed = False
                    
            except Exception as e:
                print(f"  {i}. 測試失敗: {e}")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
        return False

def test_welcome_flex_generation():
    """測試歡迎 Flex Message 生成"""
    print("\n🎉 測試歡迎 Flex Message 生成:")
    
    try:
        import line_handler
        
        class MockLineBotApi:
            pass
        
        handler = line_handler.LineMessageHandler(MockLineBotApi())
        
        # 生成歡迎 Flex Message
        welcome_flex = handler._create_welcome_flex()
        
        # 嘗試序列化
        json_dict = welcome_flex.as_json_dict()
        json_str = json.dumps(json_dict, ensure_ascii=False, indent=2)
        
        # 檢查是否有 null 值
        has_null = "null" in json_str
        
        print(f"  生成成功: ✅")
        print(f"  JSON 大小: {len(json_str)} 字符")
        print(f"  包含 null: {'❌ 是' if has_null else '✅ 否'}")
        
        # 如果有 null，顯示問題位置
        if has_null:
            lines = json_str.split('\n')
            for i, line in enumerate(lines, 1):
                if 'null' in line:
                    print(f"    第 {i} 行: {line.strip()}")
        
        return not has_null
        
    except Exception as e:
        print(f"  ❌ 生成失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 測試 null elements 修復方案\n")
    
    spacer_test = test_line_handler_spacer_fix()
    flex_test = test_welcome_flex_generation()
    
    print("\n" + "="*50)
    
    if spacer_test and flex_test:
        print("🎉 所有測試通過！")
        print("✅ 不會產生 null 值")
        print("✅ SpacerComponent 替代方案正常運作")
        print("✅ Flex Message 可以安全部署")
    else:
        print("❌ 有測試失敗")
        if not spacer_test:
            print("  - _create_spacer 方法有問題")
        if not flex_test:
            print("  - Flex Message 生成有問題")
        sys.exit(1)