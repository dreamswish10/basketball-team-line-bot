#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試方括號分隊功能
"""

import re

# 直接測試解析邏輯，不依賴完整的 LineMessageHandler
def test_bracket_validation(text):
    """測試方括號驗證邏輯"""
    if not text:
        return False
    
    # 檢查是否包含方括號（預定義分隊）
    if '[' in text and ']' in text:
        return True
    
    # 檢查是否包含分隔符
    separators = r'[、，,]'
    if re.search(separators, text):
        return True
    
    # 如果沒有分隔符，檢查是否至少有一個字符（單人也可以）
    clean_text = re.sub(r'^[^：:]*[：:]', '', text).strip()
    return len(clean_text) > 0

def test_bracket_parsing_logic(message_text):
    """測試方括號解析邏輯"""
    # 移除前綴（如 "日："）
    clean_text = re.sub(r'^[^：:]*[：:]', '', message_text).strip()
    
    # 查找所有方括號內容：[成員1,成員2,成員3]
    bracket_pattern = r'\[([^\]]+)\]'
    bracket_matches = re.findall(bracket_pattern, clean_text)
    
    if not bracket_matches:
        print("[BRACKET_PARSE] No valid bracket patterns found")
        return []
    
    predefined_teams = []
    team_counter = 1
    
    for bracket_content in bracket_matches:
        # 解析方括號內的成員名稱
        separators = r'[、，,]'
        member_parts = re.split(separators, bracket_content.strip())
        
        team_members = []
        for part in member_parts:
            name = part.strip()
            if name and len(name) >= 1:
                team_members.append(name)
        
        # 限制每隊最多3人（3vs3）
        if len(team_members) > 3:
            print(f"[BRACKET_PARSE] Team {team_counter} has {len(team_members)} members, limiting to 3")
            team_members = team_members[:3]
        
        if team_members:
            predefined_teams.append({
                'team_name': f'隊伍{team_counter}',
                'members': team_members
            })
            team_counter += 1
    
    print(f"[BRACKET_PARSE] Extracted {len(predefined_teams)} predefined teams")
    for i, team in enumerate(predefined_teams):
        print(f"[BRACKET_PARSE] Team {i+1}: {team['members']}")
    
    return predefined_teams

def test_bracket_parsing():
    """測試方括號解析功能"""
    
    print("=== 測試方括號分隊功能 ===\n")
    
    # 測試案例1: 標準格式
    test_text_1 = "[小明,小華,小李] [阿強,阿勇,阿豪]"
    print(f"測試案例1: {test_text_1}")
    print(f"驗證結果: {test_bracket_validation(test_text_1)}")
    
    teams_1 = test_bracket_parsing_logic(test_text_1)
    print(f"解析結果: {teams_1}")
    print()
    
    # 測試案例2: 中文逗號分隔
    test_text_2 = "[🥛、凱、豪] [金、kin、勇]"
    print(f"測試案例2: {test_text_2}")
    print(f"驗證結果: {test_bracket_validation(test_text_2)}")
    
    teams_2 = test_bracket_parsing_logic(test_text_2)
    print(f"解析結果: {teams_2}")
    print()
    
    # 測試案例3: 混合格式
    test_text_3 = "[玩家1,玩家2] [玩家3、玩家4]"
    print(f"測試案例3: {test_text_3}")
    print(f"驗證結果: {test_bracket_validation(test_text_3)}")
    
    teams_3 = test_bracket_parsing_logic(test_text_3)
    print(f"解析結果: {teams_3}")
    print()
    
    # 測試案例4: 超過3人的隊伍（應該被截斷）
    test_text_4 = "[A,B,C,D,E] [X,Y,Z]"
    print(f"測試案例4: {test_text_4}")
    print(f"驗證結果: {test_bracket_validation(test_text_4)}")
    
    teams_4 = test_bracket_parsing_logic(test_text_4)
    print(f"解析結果: {teams_4}")
    print()
    
    # 測試案例5: 錯誤格式（沒有方括號）
    test_text_5 = "A,B,C,D"
    print(f"測試案例5: {test_text_5}")
    print(f"驗證結果: {test_bracket_validation(test_text_5)}")
    
    teams_5 = test_bracket_parsing_logic(test_text_5)
    print(f"解析結果: {teams_5}")
    print()
    
    # 測試案例6: 單隊伍
    test_text_6 = "[隊長,隊員1,隊員2]"
    print(f"測試案例6: {test_text_6}")
    print(f"驗證結果: {test_bracket_validation(test_text_6)}")
    
    teams_6 = test_bracket_parsing_logic(test_text_6)
    print(f"解析結果: {teams_6}")
    print()

if __name__ == "__main__":
    test_bracket_parsing()