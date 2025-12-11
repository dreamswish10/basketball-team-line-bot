#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 Carousel 樣式的 Flex Message 結構
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_carousel_structure():
    """測試 Carousel 結構"""
    try:
        print("🧪 測試 Carousel Flex Message 結構")
        print("=" * 50)
        
        # 模擬 LineMessageHandler 但不依賴 MongoDB
        from linebot.models import CarouselContainer, BubbleContainer
        
        class MockLineHandler:
            def __init__(self):
                pass
                
            def _create_spacer(self, size="md", margin=None):
                """簡化版間距組件"""
                from linebot.models import TextComponent
                return TextComponent(text=" ", size="xs", color="#FFFFFF00")
            
            def _create_member_mapping_section(self, mapping_info):
                """模擬成員映射區塊"""
                from linebot.models import TextComponent
                return [
                    TextComponent(text="✅ 已識別成員", weight="bold", size="md", color="#28A745"),
                    TextComponent(text="👤 新增路人", weight="bold", size="md", color="#6C757D")
                ]
            
            def _create_team_info_section(self, total_players):
                """模擬分隊說明區塊"""
                from linebot.models import TextComponent, BoxComponent
                return [
                    BoxComponent(
                        layout="vertical",
                        contents=[
                            TextComponent(text="ℹ️ 分隊說明", weight="bold", size="md", color="#4A90E2"),
                            TextComponent(text=f"總人數 {total_players} 人", size="sm", wrap=True, margin="sm", color="#666666")
                        ],
                        backgroundColor="#F8F9FA",
                        paddingAll="md",
                        cornerRadius="8px"
                    )
                ]
            
            def _create_team_result_footer(self):
                """模擬 Footer"""
                from linebot.models import BoxComponent, ButtonComponent, PostbackAction
                return BoxComponent(
                    layout="vertical",
                    contents=[
                        ButtonComponent(
                            action=PostbackAction(label="🔄 重新分隊", data="action=reteam"),
                            style="primary",
                            color="#FF6B35"
                        )
                    ]
                )
            
            def _create_main_info_bubble(self, teams, mapping_info):
                """創建主要資訊 Bubble"""
                from linebot.models import BubbleContainer, BoxComponent, TextComponent, SeparatorComponent
                
                total_players = sum(len(team) for team in teams)
                
                body_contents = [
                    TextComponent(
                        text="🏀 自定義分隊結果",
                        weight="bold",
                        size="xl",
                        align="center",
                        color="#FF6B35"
                    ),
                    SeparatorComponent(margin="md"),
                    self._create_spacer(size="md")
                ]
                
                # 添加分隊說明
                info_section = self._create_team_info_section(total_players)
                body_contents.extend(info_section)
                
                # 添加分隊總覽
                body_contents.append(self._create_spacer(size="md"))
                body_contents.append(
                    TextComponent(
                        text=f"🏆 共分成 {len(teams)} 隊",
                        weight="bold",
                        size="lg",
                        align="center",
                        color="#FF6B35"
                    )
                )
                
                return BubbleContainer(
                    direction="ltr",
                    body=BoxComponent(
                        layout="vertical",
                        contents=body_contents,
                        spacing="sm"
                    ),
                    footer=self._create_team_result_footer()
                )
            
            def _create_team_bubbles(self, teams):
                """為每個隊伍創建專屬 Bubble"""
                from linebot.models import BubbleContainer, BoxComponent, TextComponent, SeparatorComponent
                
                team_bubbles = []
                team_colors = ["#007BFF", "#28A745", "#DC3545", "#6F42C1"]
                
                # 如果只有一隊且人數少於等於4人，不創建額外的隊伍 bubble
                if len(teams) == 1 and len(teams[0]) <= 4:
                    return team_bubbles
                
                for i, team in enumerate(teams):
                    color = team_colors[i % len(team_colors)]
                    team_name = f"隊伍 {i+1}"
                    
                    # 創建隊員列表
                    member_contents = []
                    for j, player in enumerate(team, 1):
                        member_contents.append(
                            TextComponent(
                                text=f"{j}. {player['name']}",
                                size="md",
                                color="#FFFFFF",
                                weight="bold",
                                margin="sm"
                            )
                        )
                    
                    # 創建隊伍 Bubble
                    team_bubble = BubbleContainer(
                        direction="ltr",
                        body=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(
                                    text=team_name,
                                    weight="bold",
                                    size="xl",
                                    align="center",
                                    color="#FFFFFF"
                                ),
                                TextComponent(
                                    text=f"({len(team)} 人)",
                                    size="md",
                                    align="center",
                                    color="#FFFFFF",
                                    margin="sm"
                                ),
                                SeparatorComponent(margin="md", color="#FFFFFF66"),
                                BoxComponent(
                                    layout="vertical",
                                    contents=member_contents,
                                    spacing="xs",
                                    margin="md"
                                )
                            ],
                            backgroundColor=color,
                            paddingAll="lg",
                            spacing="sm"
                        )
                    )
                    
                    team_bubbles.append(team_bubble)
                
                return team_bubbles
            
            def _create_custom_team_result_flex(self, teams, mapping_info):
                """創建自定義分隊結果 Flex Message (Carousel 樣式)"""
                bubbles = []
                
                # 第一個 Bubble：主要資訊
                main_bubble = self._create_main_info_bubble(teams, mapping_info)
                bubbles.append(main_bubble)
                
                # 為每個隊伍創建專屬 Bubble
                team_bubbles = self._create_team_bubbles(teams)
                bubbles.extend(team_bubbles)
                
                # 如果只有一個 bubble，直接返回該 bubble
                if len(bubbles) == 1:
                    return bubbles[0]
                
                # 創建 Carousel
                carousel = CarouselContainer(contents=bubbles)
                return carousel
        
        # 創建測試數據
        handler = MockLineHandler()
        
        # 測試案例 1：多隊情況
        print("\n🧪 測試案例 1: 6人分3隊")
        teams_case1 = [
            [
                {"user_id": "user1", "name": "奶", "input_name": "🥛"},
                {"user_id": "user2", "name": "凱", "input_name": "凱"}
            ],
            [
                {"user_id": "user3", "name": "豪", "input_name": "豪"},
                {"user_id": "user4", "name": "金毛", "input_name": "金"}
            ],
            [
                {"user_id": "user5", "name": "Akin", "input_name": "kin"},
                {"user_id": "user6", "name": "勇", "input_name": "勇"}
            ]
        ]
        
        mapping_info_case1 = {
            'identified': [
                {'input': '🥛', 'mapped': '奶'},
                {'input': '凱', 'mapped': '凱'},
                {'input': '豪', 'mapped': '豪'},
                {'input': '金', 'mapped': '金毛'}
            ],
            'strangers': [
                {'input': 'kin', 'stranger': '路人1'},
                {'input': '勇', 'stranger': '路人2'}
            ]
        }
        
        result_flex1 = handler._create_custom_team_result_flex(teams_case1, mapping_info_case1)
        
        if isinstance(result_flex1, CarouselContainer):
            print(f"✅ 成功創建 Carousel，包含 {len(result_flex1.contents)} 個 Bubble")
            print(f"   - 主要資訊 Bubble: 1 個")
            print(f"   - 隊伍 Bubbles: {len(result_flex1.contents) - 1} 個")
            print(f"   - 總 Bubbles: {len(result_flex1.contents)} 個")
        elif isinstance(result_flex1, BubbleContainer):
            print("✅ 創建單一 Bubble (適用於簡單情況)")
        else:
            print(f"❌ 未知的 Flex 類型: {type(result_flex1)}")
        
        # 測試案例 2：少人數情況（不分隊）
        print("\n🧪 測試案例 2: 3人不分隊")
        teams_case2 = [
            [
                {"user_id": "user1", "name": "奶", "input_name": "🥛"},
                {"user_id": "user2", "name": "凱", "input_name": "凱"},
                {"user_id": "user3", "name": "豪", "input_name": "豪"}
            ]
        ]
        
        mapping_info_case2 = {
            'identified': [],
            'strangers': []
        }
        
        result_flex2 = handler._create_custom_team_result_flex(teams_case2, mapping_info_case2)
        
        if isinstance(result_flex2, CarouselContainer):
            print(f"✅ Carousel: {len(result_flex2.contents)} 個 Bubble")
        elif isinstance(result_flex2, BubbleContainer):
            print("✅ 單一 Bubble (人數 ≤ 4，不分隊)")
        else:
            print(f"❌ 未知的 Flex 類型: {type(result_flex2)}")
        
        print("\n🎉 Carousel 結構測試完成！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_carousel_structure()