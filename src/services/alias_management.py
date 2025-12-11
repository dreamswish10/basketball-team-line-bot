#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
別名管理服務
提供互動式命令行界面來管理用戶別名
"""

import sys
import json
from typing import List, Dict, Optional
from src.database.mongodb import get_database, init_mongodb
from src.models.mongodb_models import AliasMapRepository
import logging

logger = logging.getLogger(__name__)


class AliasManagementService:
    """別名管理服務類"""

    def __init__(self):
        self.db = get_database()
        self.alias_repo = AliasMapRepository(self.db)

    def interactive_setup(self):
        """互動式設定別名"""
        print("\n🏷️  別名管理系統")
        print("=" * 40)
        
        while True:
            print("\n選擇操作：")
            print("1. 添加用戶別名")
            print("2. 查看用戶別名")
            print("3. 搜索別名")
            print("4. 刪除用戶別名")
            print("5. 批量導入別名")
            print("6. 導出別名")
            print("7. 列出所有別名")
            print("0. 退出")
            
            choice = input("\n請輸入選項 (0-7): ").strip()
            
            if choice == "0":
                print("👋 退出別名管理系統")
                break
            elif choice == "1":
                self._add_user_alias()
            elif choice == "2":
                self._view_user_aliases()
            elif choice == "3":
                self._search_aliases()
            elif choice == "4":
                self._delete_user_aliases()
            elif choice == "5":
                self._batch_import()
            elif choice == "6":
                self._export_aliases()
            elif choice == "7":
                self._list_all_aliases()
            else:
                print("❌ 無效選項，請重新選擇")

    def _add_user_alias(self):
        """添加用戶別名"""
        print("\n➕ 添加用戶別名")
        print("-" * 20)
        
        user_id = input("請輸入用戶ID: ").strip()
        if not user_id:
            print("❌ 用戶ID不能為空")
            return
        
        # 顯示現有別名
        existing_aliases = self.alias_repo.get_aliases_by_user_id(user_id)
        if existing_aliases:
            print(f"現有別名：{', '.join(existing_aliases)}")
        
        aliases_input = input("請輸入別名（多個別名用逗號分隔）: ").strip()
        if not aliases_input:
            print("❌ 別名不能為空")
            return
        
        new_aliases = [alias.strip() for alias in aliases_input.split(",") if alias.strip()]
        if not new_aliases:
            print("❌ 沒有有效的別名")
            return
        
        # 合併新舊別名
        all_aliases = list(set(existing_aliases + new_aliases))
        
        if self.alias_repo.create_or_update_alias(user_id, all_aliases):
            print(f"✅ 成功為用戶 {user_id} 設定別名：{', '.join(all_aliases)}")
        else:
            print("❌ 設定別名失敗")

    def _view_user_aliases(self):
        """查看用戶別名"""
        print("\n👀 查看用戶別名")
        print("-" * 20)
        
        user_id = input("請輸入用戶ID: ").strip()
        if not user_id:
            print("❌ 用戶ID不能為空")
            return
        
        aliases = self.alias_repo.get_aliases_by_user_id(user_id)
        if aliases:
            print(f"用戶 {user_id} 的別名：{', '.join(aliases)}")
        else:
            print(f"用戶 {user_id} 沒有設定別名")

    def _search_aliases(self):
        """搜索別名"""
        print("\n🔍 搜索別名")
        print("-" * 20)
        
        search_term = input("請輸入搜索詞：").strip()
        if not search_term:
            print("❌ 搜索詞不能為空")
            return
        
        results = self.alias_repo.search_aliases(search_term)
        if results:
            print(f"搜索結果：")
            for result in results:
                user_id = result["userId"]
                aliases = result["aliases"]
                matching_aliases = [alias for alias in aliases if search_term.lower() in alias.lower()]
                print(f"  用戶 {user_id}: {', '.join(matching_aliases)}")
        else:
            print("沒有找到匹配的別名")

    def _delete_user_aliases(self):
        """刪除用戶別名"""
        print("\n🗑️  刪除用戶別名")
        print("-" * 20)
        
        user_id = input("請輸入用戶ID: ").strip()
        if not user_id:
            print("❌ 用戶ID不能為空")
            return
        
        # 顯示現有別名
        existing_aliases = self.alias_repo.get_aliases_by_user_id(user_id)
        if not existing_aliases:
            print(f"用戶 {user_id} 沒有別名")
            return
        
        print(f"現有別名：{', '.join(existing_aliases)}")
        print("選擇操作：")
        print("1. 刪除特定別名")
        print("2. 刪除所有別名")
        
        choice = input("請輸入選項 (1-2): ").strip()
        
        if choice == "1":
            alias_to_remove = input("請輸入要刪除的別名: ").strip()
            if alias_to_remove in existing_aliases:
                if self.alias_repo.remove_alias_from_user(user_id, alias_to_remove):
                    print(f"✅ 成功刪除別名：{alias_to_remove}")
                else:
                    print("❌ 刪除別名失敗")
            else:
                print("❌ 該別名不存在")
        elif choice == "2":
            confirm = input("確定要刪除所有別名嗎？(y/N): ").strip().lower()
            if confirm == "y":
                if self.alias_repo.delete_user_aliases(user_id):
                    print("✅ 成功刪除所有別名")
                else:
                    print("❌ 刪除別名失敗")
            else:
                print("取消操作")
        else:
            print("❌ 無效選項")

    def _batch_import(self):
        """批量導入別名"""
        print("\n📥 批量導入別名")
        print("-" * 20)
        print("請輸入JSON格式的別名數據，格式如下：")
        print('[{"userId": "U123", "aliases": ["別名1", "別名2"]}, ...]')
        print("輸入完成後按Enter，輸入空行結束：")
        
        lines = []
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        
        if not lines:
            print("❌ 沒有輸入數據")
            return
        
        try:
            data = json.loads("".join(lines))
            if not isinstance(data, list):
                print("❌ 數據格式錯誤，需要是數組")
                return
            
            success_count = 0
            for item in data:
                if not isinstance(item, dict) or "userId" not in item or "aliases" not in item:
                    print(f"❌ 跳過無效項目：{item}")
                    continue
                
                user_id = item["userId"]
                aliases = item["aliases"]
                
                if self.alias_repo.create_or_update_alias(user_id, aliases):
                    print(f"✅ 成功導入用戶 {user_id} 的別名")
                    success_count += 1
                else:
                    print(f"❌ 導入用戶 {user_id} 的別名失敗")
            
            print(f"\n📊 導入完成：成功 {success_count} 項")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON格式錯誤：{e}")

    def _export_aliases(self):
        """導出別名"""
        print("\n📤 導出別名")
        print("-" * 20)
        
        all_aliases = self.alias_repo.get_all_aliases()
        if not all_aliases:
            print("沒有別名數據可導出")
            return
        
        # 轉換格式
        export_data = []
        for alias_doc in all_aliases:
            export_data.append({
                "userId": alias_doc["userId"],
                "aliases": alias_doc["aliases"]
            })
        
        json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
        print("別名數據（JSON格式）：")
        print(json_output)
        
        # 選項：保存到文件
        save_to_file = input("\n是否保存到文件？(y/N): ").strip().lower()
        if save_to_file == "y":
            filename = input("請輸入文件名（默認：aliases_export.json）: ").strip()
            if not filename:
                filename = "aliases_export.json"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"✅ 別名數據已保存到 {filename}")
            except Exception as e:
                print(f"❌ 保存文件失敗：{e}")

    def _list_all_aliases(self):
        """列出所有別名"""
        print("\n📋 所有用戶別名")
        print("-" * 20)
        
        all_aliases = self.alias_repo.get_all_aliases()
        if not all_aliases:
            print("沒有別名數據")
            return
        
        for alias_doc in all_aliases:
            user_id = alias_doc["userId"]
            aliases = alias_doc["aliases"]
            print(f"用戶 {user_id}: {', '.join(aliases)}")
        
        print(f"\n總共 {len(all_aliases)} 位用戶設定了別名")

    def add_default_aliases(self):
        """添加預設別名（示例）"""
        default_aliases = [
            {"userId": "U123", "aliases": ["大漢堡", "Jed小隊長"]},
            {"userId": "U234", "aliases": ["Alice", "小愛"]},
            {"userId": "U345", "aliases": ["Bob", "阿波"]},
        ]
        
        print("\n🔧 添加預設別名...")
        success_count = 0
        
        for alias_data in default_aliases:
            user_id = alias_data["userId"]
            aliases = alias_data["aliases"]
            
            if self.alias_repo.create_or_update_alias(user_id, aliases):
                print(f"✅ 成功設定用戶 {user_id} 的別名：{', '.join(aliases)}")
                success_count += 1
            else:
                print(f"❌ 設定用戶 {user_id} 的別名失敗")
        
        print(f"\n📊 預設別名設定完成：成功 {success_count}/{len(default_aliases)} 項")


def main():
    """主程序"""
    try:
        # 初始化 MongoDB
        print("🔌 連接到 MongoDB...")
        init_mongodb()
        print("✅ MongoDB 連接成功")
        
        # 創建別名管理服務
        alias_service = AliasManagementService()
        
        # 如果有命令行參數，執行對應操作
        if len(sys.argv) > 1:
            if sys.argv[1] == "setup-defaults":
                alias_service.add_default_aliases()
            else:
                print(f"❌ 未知參數：{sys.argv[1]}")
                print("使用方法：")
                print("  python alias_management.py           # 互動式管理")
                print("  python alias_management.py setup-defaults  # 設定預設別名")
        else:
            # 互動式管理
            alias_service.interactive_setup()
            
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，退出程序")
    except Exception as e:
        logger.error(f"別名管理服務錯誤：{e}")
        print(f"❌ 發生錯誤：{e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()