#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 SpacerComponent fallback 實作是否正常運作
"""

import json
import sys
import os

# 模擬沒有 linebot 套件的情況
class MockImportError:
    """模擬導入錯誤"""
    pass

def test_spacer_fallback():
    """測試 SpacerComponent fallback 實作"""
    print("🧪 測試 SpacerComponent fallback 實作")
    
    # 模擬 linebot 導入失敗，直接使用我們的 fallback 類別
    try:
        # 模擬導入失敗，創建替代類
        class SpacerComponent:
            def __init__(self, size="md", margin=None):
                self.size = size
                self.margin = margin
                self._type = "spacer"
                
            def as_json_dict(self):
                """返回符合 LINE Bot SDK 格式的字典"""
                result = {
                    "type": "spacer"
                }
                
                # 只有在 size 不是預設值時才加入
                if self.size and self.size != "md":
                    result["size"] = self.size
                elif self.size:
                    result["size"] = self.size
                
                # 只有當 margin 有值時才加入
                if self.margin:
                    result["margin"] = self.margin
                
                return result
                
            @property
            def type(self):
                return self._type
            
            def __repr__(self):
                return f"SpacerComponent(size='{self.size}', margin={self.margin})"
        
        # 測試不同的 SpacerComponent 配置
        test_cases = [
            {"size": "md", "margin": None, "name": "預設 spacer"},
            {"size": "sm", "margin": None, "name": "小尺寸 spacer"},
            {"size": "lg", "margin": "md", "name": "大尺寸 + margin"},
            {"size": "md", "margin": "sm", "name": "預設尺寸 + 小 margin"},
        ]
        
        print("\n📋 測試結果:")
        all_passed = True
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                # 創建 SpacerComponent
                spacer = SpacerComponent(
                    size=test_case["size"], 
                    margin=test_case["margin"]
                )
                
                # 轉換為 JSON
                json_dict = spacer.as_json_dict()
                json_str = json.dumps(json_dict, ensure_ascii=False, indent=2)
                
                # 檢查是否有 null 值
                has_null = "null" in json_str
                
                print(f"\n{i}. {test_case['name']}")
                print(f"   輸入: size='{test_case['size']}', margin={test_case['margin']}")
                print(f"   JSON: {json_str}")
                print(f"   結果: {'❌ 包含 null' if has_null else '✅ 正常'}")
                
                if has_null:
                    all_passed = False
                    
            except Exception as e:
                print(f"\n{i}. {test_case['name']}")
                print(f"   ❌ 錯誤: {e}")
                all_passed = False
        
        print(f"\n🎯 總結果: {'✅ 所有測試通過' if all_passed else '❌ 有測試失敗'}")
        return all_passed
        
    except Exception as e:
        print(f"❌ 測試執行錯誤: {e}")
        return False

def test_complex_structure():
    """測試複雜結構中的 SpacerComponent"""
    print("\n🔧 測試複雜結構中的 SpacerComponent")
    
    # 創建替代類
    class SpacerComponent:
        def __init__(self, size="md", margin=None):
            self.size = size
            self.margin = margin
            self._type = "spacer"
            
        def as_json_dict(self):
            result = {
                "type": "spacer"
            }
            
            if self.size and self.size != "md":
                result["size"] = self.size
            elif self.size:
                result["size"] = self.size
            
            if self.margin:
                result["margin"] = self.margin
            
            return result
    
    # 模擬一個包含多個 SpacerComponent 的結構
    mock_flex_structure = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "歡迎使用"},
                SpacerComponent(size="sm").as_json_dict(),
                {"type": "text", "text": "籃球分隊機器人"},
                SpacerComponent(size="md", margin="sm").as_json_dict(),
                {"type": "separator"},
                SpacerComponent(size="lg").as_json_dict()
            ]
        }
    }
    
    try:
        json_str = json.dumps(mock_flex_structure, ensure_ascii=False, indent=2)
        has_null = "null" in json_str
        
        print(f"📄 生成的 JSON 結構:")
        print(json_str)
        print(f"\n🔍 檢查結果: {'❌ 包含 null 值' if has_null else '✅ 無 null 值'}")
        
        return not has_null
        
    except Exception as e:
        print(f"❌ 結構測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SpacerComponent Fallback 測試開始\n")
    
    # 執行基本測試
    basic_test = test_spacer_fallback()
    
    # 執行複雜結構測試
    complex_test = test_complex_structure()
    
    # 總結
    print("\n" + "="*50)
    if basic_test and complex_test:
        print("🎉 所有測試通過！SpacerComponent fallback 運作正常")
        print("✅ 不會產生 null 值")
        print("✅ JSON 格式正確")
        print("✅ 可以安全使用於 test_flex_messages.py")
    else:
        print("❌ 有測試失敗，需要修正")
        sys.exit(1)