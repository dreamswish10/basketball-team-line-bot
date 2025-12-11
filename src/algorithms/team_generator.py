#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TeamGenerator - 已棄用

注意：此模組已被簡化的分隊功能取代。
新的自定義分隊功能直接在 LineMessageHandler 中實現。
"""

import random
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TeamGenerator:
    """已棄用的 TeamGenerator 類"""
    
    def __init__(self):
        self.teams = []
        logger.warning("TeamGenerator is deprecated. Use LineMessageHandler._generate_simple_teams() instead.")
    
    def generate_teams(self, players: List, num_teams: int = 2) -> List[List]:
        """已棄用的分隊方法"""
        logger.warning("generate_teams() is deprecated. Use _generate_simple_teams() instead.")
        
        # 簡單的回退實現
        if len(players) < num_teams:
            return [players]
        
        # 隨機分配
        random.shuffle(players)
        teams = [[] for _ in range(num_teams)]
        
        for i, player in enumerate(players):
            team_index = i % num_teams
            teams[team_index].append(player)
        
        return teams