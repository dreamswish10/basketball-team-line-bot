#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生成 Flex Message JSON 用於 LINE Flex Simulator 測試
使用純字典格式，不依賴 LINE Bot SDK
"""

import json

class MockLineHandler:
    """模擬的 LineMessageHandler，使用字典格式生成 Flex JSON"""
    
    def _create_spacer(self, size="md", margin=None):
        """創建間距組件"""
        spacer = {
            "type": "text",
            "text": " ",
            "size": "xs",
            "color": "#FFFFFF00"
        }
        if margin:
            spacer["margin"] = margin
        return spacer
    
    def _create_member_mapping_section(self, mapping_info):
        """創建成員映射區塊"""
        contents = []
        
        if mapping_info['identified']:
            contents.append({
                "type": "text",
                "text": "✅ 已識別成員",
                "weight": "bold",
                "size": "md",
                "color": "#28A745"
            })
            
            for item in mapping_info['identified']:
                contents.append({
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"• {item['input']}",
                            "size": "sm",
                            "color": "#333333",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": "→",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0,
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": item['mapped'],
                            "size": "sm",
                            "color": "#28A745",
                            "weight": "bold",
                            "margin": "sm"
                        }
                    ],
                    "margin": "xs"
                })
        
        if mapping_info['strangers']:
            if mapping_info['identified']:
                contents.append(self._create_spacer(size="sm"))
            
            contents.append({
                "type": "text",
                "text": "👤 新增路人",
                "weight": "bold",
                "size": "md",
                "color": "#6C757D"
            })
            
            for item in mapping_info['strangers']:
                contents.append({
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"• {item['input']}",
                            "size": "sm",
                            "color": "#333333",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": "→",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0,
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": item['stranger'],
                            "size": "sm",
                            "color": "#6C757D",
                            "weight": "bold",
                            "margin": "sm"
                        }
                    ],
                    "margin": "xs"
                })
        
        return contents
    
    def _create_team_info_section(self, total_players):
        """創建分隊說明區塊"""
        if total_players <= 4:
            description = f"總人數 {total_players} 人 ≤ 4 人，不進行分隊\n所有成員在同一隊，適合小組活動"
        else:
            description = f"總人數 {total_players} 人，採用智能分隊\n每隊最多 3 人，確保比賽平衡"
        
        return [{
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "ℹ️ 分隊說明",
                    "weight": "bold",
                    "size": "md",
                    "color": "#4A90E2"
                },
                {
                    "type": "text",
                    "text": description,
                    "size": "sm",
                    "wrap": True,
                    "margin": "sm",
                    "color": "#666666"
                }
            ],
            "backgroundColor": "#F8F9FA",
            "paddingAll": "md",
            "cornerRadius": "8px"
        }]
    
    def _create_team_result_footer(self):
        """創建分隊結果 Footer"""
        return {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "🔄 重新分隊",
                        "data": "action=reteam"
                    },
                    "style": "primary",
                    "color": "#FF6B35"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "❓ 分隊說明",
                        "data": "action=team_help"
                    },
                    "style": "link"
                }
            ],
            "spacing": "sm"
        }
    
    def _create_nano_team_bubble(self, team, team_number, color):
        """創建 nano 尺寸的隊伍 Bubble"""
        return {
            "type": "bubble",
            "size": "nano",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"隊伍 {team_number}",
                        "color": "#ffffff",
                        "align": "start",
                        "size": "md",
                        "gravity": "center",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": f"{len(team)} 人",
                        "color": "#ffffff",
                        "align": "start",
                        "size": "xs",
                        "gravity": "center",
                        "margin": "lg"
                    }
                ],
                "backgroundColor": color,
                "paddingTop": "19px",
                "paddingAll": "12px",
                "paddingBottom": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": self._format_team_members(team),
                                "color": "#8C8C8C",
                                "size": "sm",
                                "wrap": True
                            }
                        ],
                        "flex": 1
                    }
                ],
                "spacing": "md",
                "paddingAll": "12px"
            },
            "styles": {
                "footer": {
                    "separator": False
                }
            }
        }
    
    def _create_info_nano_bubble(self, mapping_info, team_count):
        """創建資訊 nano bubble"""
        # 計算已識別和路人的數量
        identified_count = len(mapping_info.get('identified', []))
        strangers_count = len(mapping_info.get('strangers', []))
        total_count = identified_count + strangers_count
        
        # 創建進度條效果
        identified_percentage = int((identified_count / total_count * 100)) if total_count > 0 else 0
        
        return {
            "type": "bubble",
            "size": "nano",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "分隊資訊",
                        "color": "#ffffff",
                        "align": "start",
                        "size": "md",
                        "gravity": "center",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": f"已識別 {identified_percentage}%",
                        "color": "#ffffff",
                        "align": "start",
                        "size": "xs",
                        "gravity": "center",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": " ",
                                        "size": "xxs"
                                    }
                                ],
                                "width": f"{identified_percentage}%",
                                "backgroundColor": "#0D8186",
                                "height": "6px"
                            }
                        ],
                        "backgroundColor": "#9FD8E36E",
                        "height": "6px",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#4ECDC4",
                "paddingTop": "19px",
                "paddingAll": "12px",
                "paddingBottom": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"共分成 {team_count} 隊\n已識別 {identified_count} 人，新增 {strangers_count} 人",
                                "color": "#8C8C8C",
                                "size": "sm",
                                "wrap": True
                            }
                        ],
                        "flex": 1
                    }
                ],
                "spacing": "md",
                "paddingAll": "12px"
            },
            "styles": {
                "footer": {
                    "separator": False
                }
            }
        }
    
    def _create_simple_team_bubble(self, team, mapping_info):
        """為 ≤4 人創建簡單 bubble"""
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "👥 人數太少，不需分隊",
                        "weight": "bold",
                        "size": "lg",
                        "align": "center",
                        "color": "#FF6B35"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"成員名單 ({len(team)}人):",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333",
                                "margin": "md"
                            }
                        ] + [
                            {
                                "type": "text",
                                "text": f"{i+1}. {player['name']}",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "sm"
                            } for i, player in enumerate(team)
                        ] + [
                            {
                                "type": "text",
                                "text": "💡 建議直接一起打球！",
                                "size": "sm",
                                "color": "#28A745",
                                "margin": "md",
                                "weight": "bold"
                            }
                        ]
                    }
                ],
                "spacing": "sm",
                "paddingAll": "16px"
            },
            "footer": self._create_team_result_footer()
        }
    
    def _format_team_members(self, team):
        """格式化隊伍成員為字串"""
        member_names = [player['name'] for player in team]
        if len(member_names) <= 3:
            return "、".join(member_names)
        else:
            return "、".join(member_names[:3]) + f"等{len(member_names)}人"
    
    
    def _create_custom_team_result_flex(self, teams, mapping_info):
        """創建自定義分隊結果 Flex Message (官方 Carousel 樣式)"""
        bubbles = []
        team_colors = ["#27ACB2", "#FF6B6E", "#A17DF5", "#4ECDC4", "#45B7D1", "#96CEB4"]
        
        # 如果只有一隊且人數 <= 4，返回簡單 bubble
        if len(teams) == 1 and len(teams[0]) <= 4:
            return self._create_simple_team_bubble(teams[0], mapping_info)
        
        # 為每個隊伍創建 nano bubble
        for i, team in enumerate(teams):
            color = team_colors[i % len(team_colors)]
            team_bubble = self._create_nano_team_bubble(team, i + 1, color)
            bubbles.append(team_bubble)
        
        # 如果有映射資訊，添加資訊 bubble
        if mapping_info['identified'] or mapping_info['strangers']:
            info_bubble = self._create_info_nano_bubble(mapping_info, len(teams))
            bubbles.insert(0, info_bubble)  # 放在第一位
        
        # 創建 Carousel
        carousel = {
            "type": "carousel",
            "contents": bubbles
        }
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
            
            # 輸出格式化的 JSON
            json_output = json.dumps(flex_message, ensure_ascii=False, indent=2)
            
            print(f"📱 Flex Message 類型: {flex_message.get('type', 'unknown')}")
            if flex_message.get('type') == 'carousel':
                print(f"🎠 Carousel 包含 {len(flex_message['contents'])} 個 Bubble")
            
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