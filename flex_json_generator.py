#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生成 Flex Message JSON 用於 LINE Flex Simulator 測試
"""

import json
from linebot.models import (
    BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    PostbackAction
)

class MockLineHandler:
    """模擬的 LineMessageHandler，專門用於生成 Flex JSON"""
    
    def _create_spacer(self, size="md", margin=None):
        """創建間距組件"""
        return TextComponent(
            text=" ",
            size="xs",
            color="#FFFFFF00",  # 透明色
            margin=margin
        )
    
    def _create_member_mapping_section(self, mapping_info):
        """創建成員映射區塊"""
        contents = []
        
        if mapping_info['identified']:
            contents.append(
                TextComponent(
                    text="✅ 已識別成員",
                    weight="bold", 
                    size="md",
                    color="#28A745"
                )
            )
            
            for item in mapping_info['identified']:
                contents.append(
                    BoxComponent(
                        layout="baseline",
                        contents=[
                            TextComponent(
                                text=f"• {item['input']}",
                                size="sm",
                                color="#333333",
                                flex=0
                            ),
                            TextComponent(
                                text="→",
                                size="sm", 
                                color="#999999",
                                flex=0,
                                margin="sm"
                            ),
                            TextComponent(
                                text=item['mapped'],
                                size="sm",
                                color="#28A745",
                                weight="bold",
                                margin="sm"
                            )
                        ],
                        margin="xs"
                    )
                )
        
        if mapping_info['strangers']:
            if mapping_info['identified']:
                contents.append(self._create_spacer(size="sm"))
            
            contents.append(
                TextComponent(
                    text="👤 新增路人",
                    weight="bold",
                    size="md", 
                    color="#6C757D"
                )
            )
            
            for item in mapping_info['strangers']:
                contents.append(
                    BoxComponent(
                        layout="baseline",
                        contents=[
                            TextComponent(
                                text=f"• {item['input']}",
                                size="sm",
                                color="#333333",
                                flex=0
                            ),
                            TextComponent(
                                text="→", 
                                size="sm",
                                color="#999999",
                                flex=0,
                                margin="sm"
                            ),
                            TextComponent(
                                text=item['stranger'],
                                size="sm",
                                color="#6C757D",
                                weight="bold",
                                margin="sm"
                            )
                        ],
                        margin="xs"
                    )
                )
        
        return contents
    
    def _create_team_info_section(self, total_players):
        """創建分隊說明區塊"""
        if total_players <= 4:
            description = f"總人數 {total_players} 人 ≤ 4 人，不進行分隊\n所有成員在同一隊，適合小組活動"
        else:
            description = f"總人數 {total_players} 人，採用智能分隊\n每隊最多 3 人，確保比賽平衡"
        
        return [
            BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="ℹ️ 分隊說明",
                        weight="bold",
                        size="md",
                        color="#4A90E2"
                    ),
                    TextComponent(
                        text=description,
                        size="sm",
                        wrap=True,
                        margin="sm",
                        color="#666666"
                    )
                ],
                backgroundColor="#F8F9FA",
                paddingAll="md",
                cornerRadius="8px"
            )
        ]
    
    def _create_team_result_footer(self):
        """創建分隊結果 Footer"""
        return BoxComponent(
            layout="vertical",
            contents=[
                ButtonComponent(
                    action=PostbackAction(
                        label="🔄 重新分隊",
                        data="action=reteam"
                    ),
                    style="primary",
                    color="#FF6B35"
                ),
                ButtonComponent(
                    action=PostbackAction(
                        label="❓ 分隊說明",
                        data="action=team_help"
                    ),
                    style="link"
                )
            ],
            spacing="sm"
        )
    
    def _create_main_info_bubble(self, teams, mapping_info):
        """創建主要資訊 Bubble"""
        total_players = sum(len(team) for team in teams)
        
        body_contents = [
            # 標題
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
        
        # 添加成員映射區塊
        if mapping_info['identified'] or mapping_info['strangers']:
            mapping_section = self._create_member_mapping_section(mapping_info)
            body_contents.extend(mapping_section)
            body_contents.append(self._create_spacer(size="md"))
        
        # 添加分隊說明區塊  
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
        
        # 簡要隊伍資訊
        for i, team in enumerate(teams, 1):
            body_contents.append(
                TextComponent(
                    text=f"隊伍 {i}: {len(team)} 人",
                    size="sm",
                    align="center",
                    color="#666666",
                    margin="xs"
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
        team_bubbles = []
        team_colors = ["#007BFF", "#28A745", "#DC3545", "#6F42C1", "#FD7E14", "#20C997"]
        
        # 如果只有一隊且人數少於等於4人，不創建額外的隊伍 bubble
        if len(teams) == 1 and len(teams[0]) <= 4:
            return team_bubbles
        
        for i, team in enumerate(teams):
            color = team_colors[i % len(team_colors)]
            team_name = "全體成員" if len(teams) == 1 else f"隊伍 {i+1}"
            
            # 創建隊員列表
            member_contents = []
            for j, player in enumerate(team, 1):
                member_contents.append(
                    BoxComponent(
                        layout="baseline",
                        contents=[
                            TextComponent(
                                text=f"{j}.",
                                size="sm",
                                color="#FFFFFF",
                                flex=0,
                                margin="none"
                            ),
                            TextComponent(
                                text=player['name'],
                                size="md",
                                color="#FFFFFF",
                                weight="bold",
                                margin="sm"
                            )
                        ],
                        margin="sm"
                    )
                )
            
            # 創建隊伍 Bubble
            team_bubble = BubbleContainer(
                direction="ltr",
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        # 隊伍標題
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
                        self._create_spacer(size="md"),
                        
                        # 隊員列表
                        BoxComponent(
                            layout="vertical",
                            contents=member_contents,
                            spacing="xs"
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

def generate_test_data():
    """生成測試數據"""
    # 測試案例 1：多隊情況（6人分3隊）
    teams_multi = [
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
    
    mapping_info_multi = {
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
    
    # 測試案例 2：單隊情況（3人不分隊）
    teams_single = [
        [
            {"user_id": "user1", "name": "奶", "input_name": "🥛"},
            {"user_id": "user2", "name": "凱", "input_name": "凱"},
            {"user_id": "user3", "name": "豪", "input_name": "豪"}
        ]
    ]
    
    mapping_info_single = {
        'identified': [
            {'input': '🥛', 'mapped': '奶'},
            {'input': '凱', 'mapped': '凱'},
            {'input': '豪', 'mapped': '豪'}
        ],
        'strangers': []
    }
    
    return [
        (teams_multi, mapping_info_multi, "多隊情況 (Carousel)"),
        (teams_single, mapping_info_single, "單隊情況 (Single Bubble)")
    ]

def main():
    print("🎨 生成 LINE Flex Simulator JSON")
    print("=" * 60)
    
    handler = MockLineHandler()
    test_data = generate_test_data()
    
    for i, (teams, mapping_info, description) in enumerate(test_data, 1):
        print(f"\n📋 測試案例 {i}: {description}")
        print("-" * 40)
        
        try:
            # 生成 Flex Message
            flex_message = handler._create_custom_team_result_flex(teams, mapping_info)
            
            # 轉換為 JSON
            if hasattr(flex_message, 'to_dict'):
                flex_json = flex_message.to_dict()
            else:
                # 如果沒有 to_dict 方法，使用其他方式
                flex_json = flex_message.__dict__
            
            # 輸出格式化的 JSON
            json_output = json.dumps(flex_json, ensure_ascii=False, indent=2)
            
            print(f"📱 Flex Message 類型: {type(flex_message).__name__}")
            if isinstance(flex_message, CarouselContainer):
                print(f"🎠 Carousel 包含 {len(flex_message.contents)} 個 Bubble")
            
            print(f"\n📄 JSON 輸出 (複製到 LINE Flex Simulator):")
            print("```json")
            print(json_output)
            print("```")
            
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎉 完成！請複製上面的 JSON 到 LINE Flex Simulator 測試")
    print(f"🔗 LINE Flex Simulator: https://developers.line.biz/flex-simulator/")

if __name__ == "__main__":
    main()