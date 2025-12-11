#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
別名設定工具腳本
用於在服務啟動時手動建立別名映射
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.services.alias_management import AliasManagementService
from src.database.mongodb import init_mongodb
import logging

def main():
    """主程序入口"""
    print("🏷️  別名設定工具")
    print("=" * 50)
    
    try:
        # 初始化 MongoDB
        print("🔌 正在連接 MongoDB...")
        init_mongodb()
        print("✅ MongoDB 連接成功\n")
        
        # 創建別名管理服務
        alias_service = AliasManagementService()
        
        # 檢查命令行參數
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "interactive":
                print("🎯 啟動互動式別名管理")
                alias_service.interactive_setup()
                
            elif command == "setup-defaults":
                print("🔧 設定預設別名")
                alias_service.add_default_aliases()
                
            elif command == "list":
                print("📋 列出所有別名")
                alias_service._list_all_aliases()
                
            elif command == "export":
                print("📤 導出別名數據")
                alias_service._export_aliases()
                
            elif command == "help":
                show_help()
                
            else:
                print(f"❌ 未知命令：{command}")
                show_help()
        else:
            # 預設啟動互動式模式
            print("🎯 啟動互動式別名管理")
            print("（提示：可使用 'python setup_aliases.py help' 查看所有命令）\n")
            alias_service.interactive_setup()
            
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，退出程序")
        
    except Exception as e:
        logging.error(f"設定別名時發生錯誤：{e}")
        print(f"❌ 發生錯誤：{e}")
        print("請檢查 MongoDB 連接和配置")


def show_help():
    """顯示使用說明"""
    print("""
📖 使用說明
-" * 30

命令格式：
  python setup_aliases.py [命令]

可用命令：
  interactive     啟動互動式別名管理（預設）
  setup-defaults  設定預設別名數據
  list           列出所有現有別名
  export         導出別名數據為 JSON
  help           顯示此說明

範例：
  python setup_aliases.py                    # 互動式管理
  python setup_aliases.py setup-defaults     # 設定預設別名  
  python setup_aliases.py list              # 列出所有別名
  python setup_aliases.py export            # 導出別名

互動式模式功能：
  - 添加/修改用戶別名
  - 查看用戶別名
  - 搜索別名
  - 刪除別名
  - 批量導入/導出
  - 列出所有別名

注意事項：
  1. 確保 MongoDB 服務正在運行
  2. 確保配置文件中的 MongoDB 連接字符串正確
  3. 每個用戶ID只能有一組別名
  4. 別名支援中文和英文
  5. 別名搜索支援模糊匹配
""")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()