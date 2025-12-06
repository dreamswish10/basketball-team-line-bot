#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# 嘗試載入 .env 檔案（如果 python-dotenv 可用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果沒有安裝 python-dotenv，直接使用系統環境變數
    pass

class Config:
    """應用程式配置類"""
    
    # LINE Bot 設定
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    
    # Flask 設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 資料庫設定
    DATABASE_NAME = 'basketball_teams.db'
    
    # 分隊設定
    DEFAULT_SKILL_VALUE = 5
    MIN_SKILL_VALUE = 1
    MAX_SKILL_VALUE = 10
    MIN_PLAYERS_FOR_TEAM = 2
    MAX_TEAMS = 10
    
    # 演算法參數
    RANDOM_FACTOR = 0.2  # 20% 機會選擇次優隊伍（避免固定分組）
    
    # 驗證設定
    @classmethod
    def validate_config(cls):
        """驗證必要的配置是否存在"""
        errors = []
        
        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKEN 未設定")
        
        if not cls.LINE_CHANNEL_SECRET:
            errors.append("LINE_CHANNEL_SECRET 未設定")
        
        if errors:
            raise ValueError(f"配置錯誤: {', '.join(errors)}")
        
        return True

class DevelopmentConfig(Config):
    """開發環境配置"""
    DEBUG = True
    DATABASE_NAME = 'basketball_teams_dev.db'

class ProductionConfig(Config):
    """生產環境配置"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')  # 生產環境必須設定
    
    @classmethod
    def validate_config(cls):
        super().validate_config()
        
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("生產環境必須設定安全的 SECRET_KEY")

class TestingConfig(Config):
    """測試環境配置"""
    TESTING = True
    DATABASE_NAME = ':memory:'  # 使用記憶體資料庫進行測試

# 根據環境變數選擇配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """獲取指定的配置類"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)