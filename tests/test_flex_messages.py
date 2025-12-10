#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flex Message UI 測試腳本
生成各種 Flex Message 的 JSON 用於在 LINE Flex Message Simulator 中預覽
"""

import json
import sys

# 添加錯誤處理的導入
try:
    from src.handlers.line_handler import LineMessageHandler
    from src.models.player import Player
    from src.algorithms.team_generator import TeamGenerator
except ImportError as e:
    print(f"❌ 導入錯誤: {e}")
    print("\n可能的解決方案:")
    print("1. 確認您在正確的虛擬環境中")
    print("2. 安裝所需依賴: pip install line-bot-sdk==3.8.0")
    print("3. 檢查檔案路徑是否正確")
    sys.exit(1)

class FlexMessageTester:
    def __init__(self):
        # 創建一個虛擬的 line_bot_api（實際不會被使用）
        self.handler = LineMessageHandler(None)
        self.team_generator = TeamGenerator()
        
    def generate_test_players(self):
        """生成測試球員資料"""
        return [
            Player("user1", "Kobe Bryant", 10, 8, 7),
            Player("user2", "LeBron James", 9, 9, 9),
            Player("user3", "Stephen Curry", 10, 6, 8),
            Player("user4", "Kevin Durant", 10, 7, 8),
            Player("user5", "Giannis", 7, 9, 10),
            Player("user6", "Chris Paul", 7, 8, 9),
        ]
    
    def flex_to_json(self, flex_content):
        """將 Flex Message 轉換為 JSON 字串"""
        try:
            # 使用 LINE Bot SDK 的內建序列化方法
            return json.dumps(flex_content.as_json_dict(), ensure_ascii=False, indent=2)
        except AttributeError as e:
            print(f"❌ JSON 轉換錯誤: {e}")
            print("這可能是 LINE Bot SDK 版本兼容問題")
            return json.dumps({"error": "無法轉換 Flex Message"}, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 未預期的錯誤: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    def test_welcome_message(self):
        """測試歡迎訊息"""
        print("🏀 === 歡迎訊息 Flex Message ===")
        welcome_flex = self.handler._create_welcome_flex()
        json_str = self.flex_to_json(welcome_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def test_register_success_message(self):
        """測試註冊成功訊息"""
        print("✅ === 球員註冊成功 Flex Message ===")
        test_player = Player("test123", "小明", 8, 7, 9)
        register_flex = self.handler._create_register_success_flex(test_player)
        json_str = self.flex_to_json(register_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def test_player_list_message(self):
        """測試球員列表訊息"""
        print("📋 === 球員列表 Flex Message ===")
        test_players = self.generate_test_players()
        list_flex = self.handler._create_player_list_flex(test_players)
        json_str = self.flex_to_json(list_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def test_empty_player_list_message(self):
        """測試空球員列表訊息"""
        print("📋 === 空球員列表 Flex Message ===")
        empty_list_flex = self.handler._create_player_list_flex([])
        json_str = self.flex_to_json(empty_list_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def test_team_result_message(self):
        """測試分隊結果訊息"""
        print("🔥 === 分隊結果 Flex Message ===")
        test_players = self.generate_test_players()
        teams = self.team_generator.generate_teams(test_players, 2)
        team_flex = self.handler._create_team_result_flex(teams)
        json_str = self.flex_to_json(team_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def test_profile_message(self):
        """測試個人資料訊息"""
        print("👤 === 個人資料 Flex Message ===")
        test_player = Player("user123", "Stephen Curry", 10, 6, 8, "2023-12-08T10:30:00")
        profile_flex = self.handler._create_profile_flex(test_player)
        json_str = self.flex_to_json(profile_flex)
        print(json_str)
        print("\n" + "="*50 + "\n")
        return json_str
    
    def save_all_to_files(self):
        """將所有 Flex Message JSON 保存到檔案"""
        import os
        
        # 創建測試輸出目錄
        output_dir = "flex_message_tests"
        os.makedirs(output_dir, exist_ok=True)
        
        test_cases = [
            ("welcome", self.test_welcome_message),
            ("register_success", self.test_register_success_message),
            ("player_list", self.test_player_list_message),
            ("empty_player_list", self.test_empty_player_list_message),
            ("team_result", self.test_team_result_message),
            ("profile", self.test_profile_message),
        ]
        
        for name, test_func in test_cases:
            try:
                # 執行測試並獲取 JSON
                json_str = test_func()
                
                # 保存到檔案
                filename = f"{output_dir}/{name}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                
                print(f"✅ 已保存 {name} 到 {filename}")
                
            except Exception as e:
                print(f"❌ 測試 {name} 時發生錯誤: {e}")
        
        print(f"\n🎉 所有 Flex Message JSON 已保存到 {output_dir}/ 目錄")

def check_dependencies():
    """檢查依賴版本"""
    print("🔍 檢查依賴版本...")
    
    try:
        import linebot
        print(f"✅ line-bot-sdk 版本: {linebot.__version__}")
    except ImportError:
        print("❌ line-bot-sdk 未安裝")
        return False
    except AttributeError:
        print("⚠️ 無法獲取 line-bot-sdk 版本")
    
    try:
        from linebot.models import SpacerComponent
        print("✅ SpacerComponent 可用")
    except ImportError:
        print("⚠️ SpacerComponent 不可用，使用替代方案")
    
    return True

def main():
    """主測試函數"""
    print("🧪 Flex Message UI 測試開始...\n")
    
    # 檢查依賴
    if not check_dependencies():
        print("\n❌ 依賴檢查失敗，請先安裝必要套件")
        return
    
    print()  # 空行分隔
    tester = FlexMessageTester()
    
    print("選擇測試選項:")
    print("1. 歡迎訊息")
    print("2. 球員註冊成功")
    print("3. 球員列表") 
    print("4. 空球員列表")
    print("5. 分隊結果")
    print("6. 個人資料")
    print("7. 全部測試並保存到檔案")
    print("8. 僅保存到檔案（不印出）")
    
    choice = input("\n請輸入選項 (1-8): ").strip()
    
    if choice == "1":
        tester.test_welcome_message()
    elif choice == "2":
        tester.test_register_success_message()
    elif choice == "3":
        tester.test_player_list_message()
    elif choice == "4":
        tester.test_empty_player_list_message()
    elif choice == "5":
        tester.test_team_result_message()
    elif choice == "6":
        tester.test_profile_message()
    elif choice == "7":
        tester.save_all_to_files()
    elif choice == "8":
        # 靜默模式 - 只保存檔案
        import sys
        from contextlib import redirect_stdout
        import io
        
        f = io.StringIO()
        with redirect_stdout(f):
            tester.save_all_to_files()
        print("🎉 所有檔案已靜默保存完成")
    else:
        print("❌ 無效選項")
    
    print("\n📖 使用說明:")
    print("1. 複製上方的 JSON 內容")
    print("2. 前往 LINE Flex Message Simulator:")
    print("   https://developers.line.biz/flex-simulator/")
    print("3. 貼上 JSON 並預覽效果")

if __name__ == "__main__":
    main()