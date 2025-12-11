#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試自定義分隊功能
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_custom_team_parsing():
    """測試自定義分隊解析功能"""
    try:
        from src.handlers.line_handler import LineMessageHandler
        
        # 創建測試實例（不需要真實的 LINE Bot API）
        handler = LineMessageHandler(None, None)
        
        # 測試範例字串
        test_message = "日：沒復發就全力🥛、凱、豪、金、kin、勇"
        
        print(f"🧪 測試字串: {test_message}")
        print("=" * 50)
        
        # 測試是否能識別為自定義分隊訊息
        is_custom = handler._is_custom_team_message(test_message)
        print(f"✅ 識別為自定義分隊: {is_custom}")
        
        if is_custom:
            # 測試解析成員名稱
            member_names = handler._parse_member_names(test_message)
            print(f"📝 解析到的成員: {member_names}")
            
            # 測試創建球員（模擬別名映射）
            players, mapping_info = handler._create_players_from_names(member_names)
            print(f"👥 創建球員數量: {len(players)}")
            print(f"📊 映射資訊:")
            print(f"  - 已識別: {len(mapping_info['identified'])} 位")
            print(f"  - 路人: {len(mapping_info['strangers'])} 位")
            
            print(f"\n🔍 詳細映射:")
            for item in mapping_info['identified']:
                print(f"  ✅ {item['input']} → {item['mapped']}")
            for item in mapping_info['strangers']:
                print(f"  👤 {item['input']} → {item['stranger']}")
            
            print(f"\n🏀 球員列表:")
            for i, player in enumerate(players, 1):
                print(f"  {i}. {player.name} (ID: {player.user_id})")
        
        print("\n🎉 測試完成！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_custom_team_parsing()