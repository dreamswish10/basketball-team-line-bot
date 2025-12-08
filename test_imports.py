#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速驗證 LINE Bot SDK 導入是否正常
"""

def test_imports():
    print("🔍 測試 LINE Bot SDK 導入...")
    
    # 測試基本導入
    try:
        from linebot.models import TextSendMessage, FlexSendMessage
        print("✅ 基本 LINE Bot 組件導入成功")
    except ImportError as e:
        print(f"❌ 基本組件導入失敗: {e}")
        return False
    
    # 測試 Flex Message 組件
    try:
        from linebot.models import BubbleContainer, BoxComponent, TextComponent
        print("✅ Flex Message 基本組件導入成功")
    except ImportError as e:
        print(f"❌ Flex Message 組件導入失敗: {e}")
        return False
    
    # 測試 SpacerComponent（可能有問題的組件）
    spacer_available = False
    try:
        from linebot.models import SpacerComponent
        print("✅ SpacerComponent 導入成功")
        spacer_available = True
    except ImportError:
        try:
            from linebot.models.flex_message import SpacerComponent
            print("✅ SpacerComponent 從子模組導入成功")
            spacer_available = True
        except ImportError:
            try:
                from linebot.models import Spacer as SpacerComponent
                print("✅ Spacer 作為 SpacerComponent 導入成功")
                spacer_available = True
            except ImportError:
                print("⚠️ SpacerComponent 不可用，將使用替代方案")
    
    # 測試我們的修復後的導入
    try:
        from line_handler import LineMessageHandler
        print("✅ line_handler 導入成功")
    except ImportError as e:
        print(f"❌ line_handler 導入失敗: {e}")
        return False
    
    # 測試創建 Flex Message
    try:
        handler = LineMessageHandler(None)
        welcome_flex = handler._create_welcome_flex()
        print("✅ Flex Message 創建成功")
        
        # 測試 JSON 轉換
        json_dict = welcome_flex.as_json_dict()
        print("✅ JSON 轉換成功")
        
        return True
    except Exception as e:
        print(f"❌ Flex Message 創建或轉換失敗: {e}")
        return False

def test_version_info():
    print("\n📦 版本資訊:")
    
    try:
        import linebot
        print(f"line-bot-sdk: {linebot.__version__}")
    except:
        print("line-bot-sdk: 無法獲取版本")
    
    try:
        import aiohttp
        print(f"aiohttp: {aiohttp.__version__}")
    except:
        print("aiohttp: 未安裝")
    
    import sys
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

if __name__ == "__main__":
    print("🧪 LINE Bot SDK 導入測試\n")
    
    test_version_info()
    print()
    
    if test_imports():
        print("\n🎉 所有導入測試通過！")
        print("現在可以運行 test_flex_messages.py")
    else:
        print("\n❌ 測試失敗，請檢查錯誤訊息")
        print("\n可能的解決方案:")
        print("1. 重新安裝: pip install --force-reinstall line-bot-sdk==3.8.0")
        print("2. 檢查虛擬環境: which python")
        print("3. 清理快取: pip cache purge")