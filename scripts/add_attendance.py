#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手動新增 attendances 記錄的工具
使用 AttendancesRepository 來新增組隊記錄

使用方式:
1. 互動模式: python scripts/add_attendance.py
2. 快速模式: python scripts/add_attendance.py --date 2025-12-12 --teams "勇,傑,豪|凱,奶,金毛"
3. 範例模式: python scripts/add_attendance.py --sample
"""

import sys
import os
import argparse
from datetime import datetime

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb import init_mongodb, get_database
from src.models.mongodb_models import AttendancesRepository, AliasMapRepository

class AttendanceManager:
    def __init__(self):
        """初始化 AttendanceManager"""
        init_mongodb()
        db = get_database()
        self.attendances_repo = AttendancesRepository(db)
        self.alias_repo = AliasMapRepository(db)
        self.stranger_count = 0
    
    def resolve_member_alias(self, input_name):
        """
        解析成員別名為真實 userId
        
        Args:
            input_name: 輸入的名稱（可能是別名）
            
        Returns:
            Dict: {userId: str, name: str, input: str, is_stranger: bool}
        """
        # 嘗試通過別名系統查找
        user_id = self.alias_repo.find_user_by_alias(input_name)
        
        if user_id:
            # 找到對應的用戶
            return {
                "userId": user_id,
                "name": user_id,  # 在別名系統中，userId 就是顯示名稱
                "input": input_name,
                "is_stranger": False
            }
        else:
            # 沒有找到，創建 stranger
            self.stranger_count += 1
            return {
                "userId": f"STRANGER_{self.stranger_count}",
                "name": f"路人{self.stranger_count}",
                "input": input_name,
                "is_stranger": True
            }
    
    def parse_teams_string(self, teams_string):
        """
        解析隊伍字串格式: "team1_member1,member2|team2_member1,member2"
        
        Args:
            teams_string: 隊伍字串，例如 "勇,傑,豪|凱,奶,金毛"
            
        Returns:
            List[Dict]: 格式化的隊伍列表
        """
        teams = []
        team_strings = teams_string.split('|')
        all_mappings = []  # 記錄所有別名映射結果
        
        for i, team_string in enumerate(team_strings, 1):
            input_names = [name.strip() for name in team_string.split(',') if name.strip()]
            
            if len(input_names) > 3:
                print(f"⚠️ 警告: 第{i}隊有 {len(input_names)} 位成員，超過3人限制")
                input_names = input_names[:3]
                print(f"   自動調整為前3位: {', '.join(input_names)}")
            
            if input_names:
                members = []
                team_mappings = []
                
                for input_name in input_names:
                    # 使用別名解析
                    resolved = self.resolve_member_alias(input_name)
                    
                    members.append({
                        "userId": resolved["userId"],
                        "name": resolved["name"]
                    })
                    
                    team_mappings.append(resolved)
                    all_mappings.append(resolved)
                
                teams.append({
                    "teamId": f"team_{i}",
                    "members": members,
                    "_mappings": team_mappings  # 臨時保存映射信息供顯示使用
                })
        
        # 顯示別名映射結果
        self.display_alias_mappings(all_mappings)
        
        return teams
    
    def display_alias_mappings(self, mappings):
        """顯示別名映射結果"""
        if not mappings:
            return
            
        identified = [m for m in mappings if not m["is_stranger"]]
        strangers = [m for m in mappings if m["is_stranger"]]
        
        if identified or strangers:
            print("\n🔍 別名映射結果:")
            
            if identified:
                identified_strs = []
                for m in identified:
                    if m["input"] != m["name"]:
                        identified_strs.append(f"{m['input']}→{m['name']}")
                    else:
                        identified_strs.append(m["name"])
                
                if identified_strs:
                    print(f"✅ 已識別: {', '.join(identified_strs)}")
            
            if strangers:
                stranger_strs = [f"{m['input']}→{m['name']}" for m in strangers]
                print(f"❓ 未識別: {', '.join(stranger_strs)}")
    
    def validate_date(self, date_string):
        """
        驗證日期格式
        
        Args:
            date_string: 日期字串，格式 YYYY-MM-DD
            
        Returns:
            bool: 是否為有效日期
        """
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def display_teams_preview(self, teams):
        """顯示隊伍預覽"""
        print("\n📋 隊伍預覽:")
        for i, team in enumerate(teams, 1):
            member_names = [member['name'] for member in team['members']]
            print(f"  第{i}隊 ({len(member_names)}人): {', '.join(member_names)}")
    
    def add_attendance(self, date, teams):
        """
        新增出席記錄
        
        Args:
            date: 日期字串 (YYYY-MM-DD)
            teams: 隊伍列表
            
        Returns:
            bool: 是否成功
        """
        # 清理 teams 資料，移除臨時的 _mappings 欄位
        cleaned_teams = []
        for team in teams:
            clean_team = {
                "teamId": team["teamId"],
                "members": team["members"]
            }
            cleaned_teams.append(clean_team)
        
        # 檢查是否已有該日期的記錄
        existing = self.attendances_repo.get_attendance_by_date(date)
        if existing:
            print(f"⚠️ 注意: {date} 已有記錄，將會覆蓋現有資料")
            confirm = input("   繼續嗎? (y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ 已取消")
                return False
        
        # 新增記錄
        success = self.attendances_repo.create_or_update_attendance(date, cleaned_teams)
        
        if success:
            print("✅ 記錄新增成功！")
            
            # 驗證記錄
            saved_record = self.attendances_repo.get_attendance_by_date(date)
            if saved_record:
                total_members = sum(len(team['members']) for team in cleaned_teams)
                print(f"✅ 驗證成功: {len(cleaned_teams)} 隊，共 {total_members} 人")
                print(f"   記錄ID: {saved_record.get('_id')}")
            return True
        else:
            print("❌ 新增失敗")
            return False
    
    def interactive_mode(self):
        """互動式輸入模式"""
        print("🏀 互動式新增 Attendance 記錄")
        print("=" * 40)
        
        # 輸入日期
        date_input = input("請輸入日期 (YYYY-MM-DD) [預設: 今天]: ").strip()
        if not date_input:
            date_input = datetime.now().strftime("%Y-%m-%d")
        
        if not self.validate_date(date_input):
            print("❌ 無效的日期格式")
            return False
        
        print(f"📅 日期: {date_input}")
        
        # 輸入隊伍
        print("\n請輸入隊伍成員 (可使用兩種方式):")
        print("方式1 - 快速格式: 勇,傑,豪|凱,奶,金毛")
        print("方式2 - 逐隊輸入: 按 Enter 進入逐隊輸入模式")
        
        teams_input = input("\n隊伍資料: ").strip()
        
        if teams_input:
            # 快速格式
            teams = self.parse_teams_string(teams_input)
        else:
            # 逐隊輸入
            teams = self._input_teams_step_by_step()
        
        if not teams:
            print("❌ 沒有有效的隊伍資料")
            return False
        
        # 顯示預覽並確認
        self.display_teams_preview(teams)
        
        confirm = input(f"\n確定要新增 {date_input} 的記錄嗎? (y/N): ").strip().lower()
        
        if confirm == 'y':
            return self.add_attendance(date_input, teams)
        else:
            print("❌ 已取消")
            return False
    
    def _input_teams_step_by_step(self):
        """逐隊輸入模式"""
        teams = []
        team_count = int(input("\n隊伍數量: ") or "2")
        
        for i in range(1, team_count + 1):
            print(f"\n--- 第{i}隊 ---")
            members_input = input(f"成員名稱 (用逗號分隔，最多3人): ").strip()
            
            if members_input:
                member_names = [name.strip() for name in members_input.split(',') if name.strip()]
                
                if len(member_names) > 3:
                    print(f"⚠️ 超過3人限制，只取前3位: {', '.join(member_names[:3])}")
                    member_names = member_names[:3]
                
                members = []
                team_mappings = []
                
                for name in member_names:
                    # 使用別名解析
                    resolved = self.resolve_member_alias(name)
                    
                    members.append({
                        "userId": resolved["userId"],
                        "name": resolved["name"]
                    })
                    
                    team_mappings.append(resolved)
                
                teams.append({
                    "teamId": f"team_{i}",
                    "members": members,
                    "_mappings": team_mappings
                })
        
        # 顯示別名映射結果
        all_mappings = []
        for team in teams:
            all_mappings.extend(team.get("_mappings", []))
        
        if all_mappings:
            self.display_alias_mappings(all_mappings)
        
        return teams
    
    def quick_mode(self, date, teams_string):
        """快速模式"""
        print("🚀 快速新增模式")
        print("=" * 20)
        
        if not self.validate_date(date):
            print("❌ 無效的日期格式")
            return False
        
        teams = self.parse_teams_string(teams_string)
        
        if not teams:
            print("❌ 無法解析隊伍資料")
            return False
        
        print(f"📅 日期: {date}")
        self.display_teams_preview(teams)
        
        return self.add_attendance(date, teams)
    
    def sample_mode(self):
        """範例模式 - 快速新增測試資料"""
        print("📝 範例資料模式")
        print("=" * 20)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 範例隊伍
        teams = [
            {
                "teamId": "team_1",
                "members": [
                    {"userId": "勇", "name": "勇"},
                    {"userId": "傑", "name": "傑"}, 
                    {"userId": "豪", "name": "豪"}
                ]
            },
            {
                "teamId": "team_2",
                "members": [
                    {"userId": "凱", "name": "凱"},
                    {"userId": "奶", "name": "奶"},
                    {"userId": "金毛", "name": "金毛"}
                ]
            }
        ]
        
        print(f"📅 日期: {today}")
        self.display_teams_preview(teams)
        
        confirm = input("\n確定要新增這筆範例記錄嗎? (y/N): ").strip().lower()
        
        if confirm == 'y':
            return self.add_attendance(today, teams)
        else:
            print("❌ 已取消")
            return False

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='手動新增 Attendances 記錄')
    parser.add_argument('--date', help='日期 (YYYY-MM-DD)')
    parser.add_argument('--teams', help='隊伍資料 (格式: "team1_member1,member2|team2_member1,member2")')
    parser.add_argument('--sample', action='store_true', help='新增範例資料')
    
    args = parser.parse_args()
    
    try:
        manager = AttendanceManager()
        
        if args.sample:
            # 範例模式
            success = manager.sample_mode()
        elif args.date and args.teams:
            # 快速模式
            success = manager.quick_mode(args.date, args.teams)
        else:
            # 互動模式
            success = manager.interactive_mode()
        
        if success:
            print("\n🎉 操作完成！")
        else:
            print("\n💥 操作失敗或已取消")
            
    except KeyboardInterrupt:
        print("\n\n👋 程式被中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()