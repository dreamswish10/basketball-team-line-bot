#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from typing import List, Dict, Tuple
from models import Player

class TeamGenerator:
    def __init__(self):
        self.teams = []
    
    def generate_teams(self, players: List[Player], num_teams: int = 2) -> List[List[Player]]:
        """
        根據球員技能生成平衡的隊伍
        使用貪心演算法 + 隨機因子確保公平性
        """
        if len(players) < num_teams:
            raise ValueError(f"球員數量 ({len(players)}) 不能少於隊伍數量 ({num_teams})")
        
        # 根據總體評分排序球員（降序）
        sorted_players = sorted(players, key=lambda p: p.overall_rating, reverse=True)
        
        # 初始化隊伍
        teams = [[] for _ in range(num_teams)]
        team_ratings = [0.0] * num_teams
        
        # 分配球員到隊伍
        for player in sorted_players:
            # 找到目前總評分最低的隊伍
            min_team_idx = team_ratings.index(min(team_ratings))
            
            # 加入隨機因子：有 20% 機會選擇次低的隊伍（避免過度固定分組）
            if len(teams[min_team_idx]) > 0 and random.random() < 0.2:
                team_ratings_copy = team_ratings.copy()
                team_ratings_copy[min_team_idx] = float('inf')  # 排除最低的
                if min(team_ratings_copy) != float('inf'):
                    min_team_idx = team_ratings_copy.index(min(team_ratings_copy))
            
            # 將球員加入選中的隊伍
            teams[min_team_idx].append(player)
            team_ratings[min_team_idx] += player.overall_rating
        
        self.teams = teams
        return teams
    
    def get_team_stats(self, teams: List[List[Player]]) -> List[Dict]:
        """計算每隊的統計資料"""
        stats = []
        
        for i, team in enumerate(teams):
            if not team:
                stats.append({
                    'team_number': i + 1,
                    'player_count': 0,
                    'avg_shooting': 0,
                    'avg_defense': 0,
                    'avg_stamina': 0,
                    'total_rating': 0,
                    'avg_rating': 0
                })
                continue
            
            total_shooting = sum(p.shooting_skill for p in team)
            total_defense = sum(p.defense_skill for p in team)
            total_stamina = sum(p.stamina for p in team)
            total_rating = sum(p.overall_rating for p in team)
            
            stats.append({
                'team_number': i + 1,
                'player_count': len(team),
                'avg_shooting': total_shooting / len(team),
                'avg_defense': total_defense / len(team),
                'avg_stamina': total_stamina / len(team),
                'total_rating': total_rating,
                'avg_rating': total_rating / len(team)
            })
        
        return stats
    
    def format_teams_message(self, teams: List[List[Player]]) -> str:
        """格式化隊伍訊息用於 LINE Bot 回覆"""
        if not teams:
            return "❌ 目前沒有分隊資料"
        
        message_lines = ["🏀 籃球分隊結果 🏀\n"]
        
        stats = self.get_team_stats(teams)
        
        for i, (team, stat) in enumerate(zip(teams, stats)):
            team_num = i + 1
            message_lines.append(f"🔥 第 {team_num} 隊 (平均評分: {stat['avg_rating']:.1f})")
            
            if not team:
                message_lines.append("  ⚠️ 無球員")
            else:
                for j, player in enumerate(team, 1):
                    message_lines.append(f"  {j}. {player.name} ({player.overall_rating:.1f})")
            
            # 顯示隊伍統計
            message_lines.append(f"  📊 投籃:{stat['avg_shooting']:.1f} | 防守:{stat['avg_defense']:.1f} | 體力:{stat['avg_stamina']:.1f}")
            message_lines.append("")  # 空行分隔
        
        # 計算平衡度
        if len(stats) >= 2:
            ratings = [s['avg_rating'] for s in stats if s['player_count'] > 0]
            if ratings:
                balance_score = (max(ratings) - min(ratings))
                message_lines.append(f"⚖️ 隊伍平衡度: {10 - balance_score:.1f}/10")
                message_lines.append("(數值越高表示隊伍越平衡)")
        
        return "\n".join(message_lines)
    
    def suggest_optimal_teams(self, total_players: int) -> List[Tuple[int, str]]:
        """建議最佳分隊數量"""
        suggestions = []
        
        if total_players >= 10:
            suggestions.append((2, f"2隊 (每隊約{total_players//2}人) - 5v5 全場"))
        if total_players >= 6:
            suggestions.append((2, f"2隊 (每隊約{total_players//2}人) - 3v3 半場"))
        if total_players >= 9:
            suggestions.append((3, f"3隊 (每隊約{total_players//3}人) - 輪替對戰"))
        if total_players >= 12:
            suggestions.append((4, f"4隊 (每隊約{total_players//4}人) - 小組賽"))
        
        return suggestions[:3]  # 最多顯示 3 個建議

# 測試功能
if __name__ == "__main__":
    from models import Player
    
    # 創建測試球員
    test_players = [
        Player("user1", "Kobe Bryant", 10, 8, 7),
        Player("user2", "LeBron James", 9, 9, 9),
        Player("user3", "Stephen Curry", 10, 6, 8),
        Player("user4", "Kawhi Leonard", 8, 10, 7),
        Player("user5", "Kevin Durant", 10, 7, 8),
        Player("user6", "Giannis", 7, 9, 10),
        Player("user7", "Chris Paul", 7, 8, 9),
        Player("user8", "Anthony Davis", 8, 9, 7),
    ]
    
    # 測試分隊
    generator = TeamGenerator()
    teams = generator.generate_teams(test_players, 2)
    
    print("=== 測試分隊結果 ===")
    print(generator.format_teams_message(teams))
    
    print("\n=== 分隊建議 ===")
    suggestions = generator.suggest_optimal_teams(len(test_players))
    for num_teams, description in suggestions:
        print(f"{num_teams} 隊: {description}")